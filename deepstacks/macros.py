#!/usr/bin/env python
# coding:utf-8
# vi:tabstop=4:shiftwidth=4:expandtab:sts=4


def macros(l):
    res = ()
    for a in l:
        if callable(a[0]):
            res += a[0](*a[1:])
        else:
            res += (a, )
    return res


def ln(k, name=0, m=None):
    return ((k, 0, 0, 0, name, 0, m or {}), )


def push(k, name, m=None):
    return ((k, 0, 0, 0, name, 0, m or {}), )


def pop(name):
    return ((0, 0, 0, 0, 0, 0, {'pop': name}), )


def roll(f, n, d=1, inscale=1.0, outscale=1.0, w=1, h=1, m=None):
    res = ()
    first = True
    for i in range(n):
        res = (
                (0, (f, f**i, w*h) if i != n-1
                    else (int(f*inscale+0.5), f**i, w*h), 0,  0, 0, 0, {}),
                (0, f*d, 1,  1, 0, 0, {}),
                (0, f*d, 1,  1, 0, 0, {}),
                (0, int(f*outscale+0.5) if first
                    else f, 1,  1, 0, 0, (m or {}) if first else {}),
                )+res
        first = False
    res += (
        (0, (int(f**n*outscale+0.5), w, h), 0, 0, 0, 0, {}),
        )
    return res

'''
def roll2(f, n, d=1, w=1, h=1, m={}):
    res=()
    p=0
    for i in range(n):
        res=(
                (1, (f, f**i, w*h), 0,  0, 0, p, {}),
                (1, (f, f**i, w*h), 0,  0, 0, p, {}),
                ((0, 1), f*d , 1, 1, 0, p, {}),
                ((1, 2), f*d , 1, 1, 0, p, {}),
                (1, f*d   , 1,  1, 0, p, {}),
                (1, f*d   , 1,  1, 0, p, {}),
                (1, f     , 1,  1, 0, p, {}),
                (1, f     , 1,  1, 0, p, {}),
                )+res
    res=((0, 0, 0, 0, 0, 0, {}),
            )+res+(
            ((0, 1), f , 1, 1, 0, p, m),
            (0, (f**n, w, h), 0, 0, 0, p, {}),
        )
    return res

def tile(f, n, p=0, m={}, local=False):
    return (
        (0, (f, n, n), 0,  0, 0, p, {}),
        (0, f   , 1,  1, 0, p, {'local'} if local else {}),
        (0, f   , 1,  1, 0, p, {'local'} if local else {}),
        (0, f*n*n, n, n, 0, p, m),
        )

def local(f, n, p=0, m={}):
    return tile(f, n, p, m, True)
'''


def swwae_pooling(f, imagesize, poolsize, where, what, beta=3):
    sh = (f, imagesize/poolsize, poolsize, imagesize/poolsize, poolsize)
    return (
        (0, sh, 0,  0, 0, 0, {}),
        (0, 0,  0,  0, 0, 0, {'dimshuffle': (0, 1, 2, 4, 3, 5)}),
        (0, 0, 0, 0, where, 0, {'argmax': (4, 5), 'beta': 3}),
        (3, 0, poolsize, poolsize, what, 0, {'maxpool'}),
        )


def swwae_unpooling(f, imagesize, poolsize, where, what):
    sh = (None, f, imagesize/poolsize, imagesize/poolsize, poolsize, poolsize)
    return (
        (where, 0, 0,  0, 0, 0, {'unargmax': (4, 5), 'shape': sh}),
        (0, 0, 0, 0, 0, 0, {'dimshuffle': (0, 1, 2, 4, 3, 5)}),
        (0, (f, imagesize, imagesize), 0, 0, 0, 0, {}),
        (what, 0, poolsize, 1, 0, 0, {'upscale'}),
        ((0, 1), 0, 0,  0, 0, 0, {'op': lambda x, y: x*y}),
        )


def inception(nfilters, name=0):
    return (
            (0, 0, 3, 1, 0, 0, {'maxpool'}),
            (0, nfilters[0], 1, 1, 0, 0, {}),
            (2, nfilters[1], 1, 1, 0, 0, {}),
            (3, nfilters[2], 1, 1, 0, 0, {}),
            (0, nfilters[3], 3, 1, 0, 0, {}),
            (5, nfilters[4], 1, 1, 0, 0, {}),
            (0, nfilters[5], 5, 1, 0, 0, {}),
            ((4, 2, 0, 5), 0, 0, 0, name, 0, {}),
            )

share2data = {}


def share(group, l, local_vars={}, save_vars={}, noshare=False):
    if type(group) == list:
        assert len(group) == 1
        group = group[0]
        flag_const = 1
    else:
        flag_const = 0
    res = ()
    tail = ()
    for var in save_vars:
        tail += (
                (var, 0, 0, 0, save_vars[var], 0, {}),
                )
    for var in local_vars:
        res += (
                (var, 0, 0, 0, 'stack:'+var, 0, {}),
                )
        if local_vars[var]:
            res += (
                    (local_vars[var], 0, 0, 0, var, 0, {}),
                    )
        tail += (
                ('stack:'+var, 0, 0, 0, var, 0, {'pop': 'stack:'+var}),
                )
    if group in share2data:
        nowatch = True
    else:
        nowatch = False
    if l:
        l = macros(l)
        share2data[group] = l
    else:
        l = share2data[group]
    i = 0
    for a in l:
        if type(a[-1]) == dict:
            m = a[-1].copy()
        elif type(a[-1]) == set:
            m = {}
            for t in a[-1]:
                m[t] = True
        else:
            m = {}
            a = a+(m, )
        if nowatch and type(m) == dict and 'watch' in m:
            m.pop('watch')
        if flag_const:
            m['const'] = True
        if a[-2] == 0 and not noshare:
            m['sharegroup'] = group+":"+str(i)
        res += (a[:-1]+(m, ), )
        i += 1
    return res+tail


def call(group, local_vars={}, save_vars={}):
    return share(group, None, local_vars, save_vars)


def callcopy(group, local_vars={}, save_vars={}):
    return share(group, None, local_vars, save_vars, True)


runtime_loop_iterators = None


def set_runtime_loop_iterators(a):
    global runtime_loop_iterators
    runtime_loop_iterators = a
    print 'set_runtime_loop_iterators:', runtime_loop_iterators


def curr_loop_iterators(n):
    print 'curr_runtime_loop_iterators:', runtime_loop_iterators
    return runtime_loop_iterators[-n]

loop_iterators = []


def loop(n, l):
    global loop_iterators
    res = ()
    loop_iterators += [0]
    res += ((0, 0, 0, 0, 0, 0, {'eval': (
        set_runtime_loop_iterators, loop_iterators+[])}), )
    for i in range(n):
        res += macros(l)
        loop_iterators[-1] += 1
        res += ((0, 0, 0, 0, 0, 0, {'eval': (
            set_runtime_loop_iterators, loop_iterators+[])}), )
    loop_iterators = loop_iterators[:-1]
    res += ((0, 0, 0, 0, 0, 0, {'eval': (set_runtime_loop_iterators, None)}), )
    return res


def switch(cond, ltrue, lfalse):
    res = ()
    if cond:
        res += macros(ltrue)
    else:
        res += macros(lfalse)
    return res
