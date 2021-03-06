#!/usr/bin/env python
# coding:utf-8
# vi:tabstop=4:shiftwidth=4:expandtab:sts=4

verbose=False
def set_verbose(val):
    global verbose
    verbose=val

class Layers(object):
    def __init__(self, network, stacks):
        self.layers = [network]
        self.stacks = stacks
        self.future = {}

    def add(self, network):
        self.layers += [network]

    def get_layer(self, k):
        if type(k) == list and len(k) == 1:
            k = k[0]
        if type(k) == int:
            return self.layers[::-1][k]
        if type(k) == list and len(k) > 1:
            assert len(k) == 3
            raise NotImplementedError
        return self.stacks[k][-1]

    def finish(self):
        pass


def deep_eval(a, m):
    # print 'de:',a
    if type(a) == tuple or type(a) == list:
        if type(a) == tuple and len(a) and callable(a[0]):
            # (type(a[0])==type(lambda:0) or type(a[0])==type):
            # print 'de:','callable'
            #print type(a[-1])
            if type(a[-1]) != dict:
                a += ({},)
            #print a
            args = [(m[x] if type(x) != list and type(x) != tuple  and x in m else deep_eval(x, m))
                    for x in a[1:-1]]
            kwargs = a[-1]
            for k in kwargs:
                if type(kwargs[k]) != list and kwargs[k] in m:
                    kwargs[k] = m[kwargs[k]]
            kwargs = deep_eval(kwargs, m)
            # print 'de:',a[0],args,kwargs
            a = a[0](*args, **kwargs)
        else:
            a = type(a)(map(lambda x: deep_eval(x, m), a))
        # a=type(a)(map(lambda x: x(*args,**kwargs)
        # if type(x)==type(lambda:0) else deep_eval(x,*args,**kwargs),a))
    elif type(a) == dict:
        out = {}
        for k in a:
            out[k] = deep_eval(a[k], m)
        a = out
    return a


def curr_layer():
    pass


def curr_stacks():
    pass


def curr_flags():
    pass


def curr_model():
    pass


def softmax():
    pass


def rectify():
    pass


def sigmoid():
    pass


def tanh():
    pass


def linear():
    pass


flag_list = []
flag_handler = {}
flag_excluding = {}
flag_handler_closer = {}


def register_flag_handler(flag, handler, excluding=()):
    global flag_list
    if flag not in flag_list:
        flag_list = [flag]+flag_list
    assert flag not in flag_handler
    flag_handler[flag] = handler
    flag_excluding[flag] = set(excluding)


def register_flag_handler_closer(handler, closer):
    global flag_list
    if handler not in flag_list:
        flag_list = [handler]+flag_list
    flag_handler_closer[handler] = closer

inputs_handler = {}


def register_inputs_handler(flag, handler):
    assert flag not in inputs_handler
    inputs_handler[flag] = handler
concat_handler = None


def register_concat_handler(handler):
    global concat_handler
    concat_handler = handler


def layer_handler(network, flags, stacks, this_model):
    return flags['layer'], {}


def push_handler(network, flags, stacks, this_model):
    keys = flags['push']
    if type(keys) != tuple and type(keys) != list:
        keys = [keys]
    for key in keys:
        assert type(key) == str
        if key not in stacks:
            stacks[key] = []
        stacks[key] += [network]
    return network, ()


def pop_handler(network, flags, stacks, this_model):
    key = flags['pop']
    assert key in stacks
    stacks[key] = stacks[key][:-1]
    if len(stacks[key]) == 0:
        stacks.pop(key)
    return network, ()

register_flag_handler('push', push_handler)
register_flag_handler('pop', pop_handler)
register_flag_handler('layer', layer_handler)

macros = []


def register_macro_handler(handler):
    global macros
    macros = [handler]+macros

layers_class = Layers


def register_layers_class(l):
    global layers_class
    layers_class = l

network_wrapper = None


def register_network_wrapper(f):
    global network_wrapper
    network_wrapper = f

layer_handler = None


def register_layer_handler(f):
    global layer_handler
    layer_handler = f

nonlinearities = None


def register_nonlinearities(m):
    global nonlinearities
    nonlinearities = m

def build_network(network, a, m={}, **kwargs):
    if callable(a):
        a=a()
    # a=((INPUTS,flags),)*N

    this_model = kwargs
    this_model['errors'] = {}
    this_model['watchpoints'] = {}

    for h in macros:
        a = h(a)

    paramlayers = []

    stacks = {}
    for key in m:
        stacks[key] = [m[key]]
    stacks['input'] = [network]

    all_layers = layers_class(network, stacks)

    this_model['get_layer'] = all_layers.get_layer

    def get_layer(k):
        return all_layers.get_layer(k)

    count = 0
    for info in a:
        if verbose:
            print count, info
        count += 1

        inputs = info[0]
        if type(info[-1]) == set or type(info[-1]) == dict:
            pass
        else:
            info = info+({},)

        flags = info[-1]
        if type(inputs) == list and len(inputs) == 1 and type(inputs[0]) == tuple:
            inputs = tuple(map(lambda x: [x], inputs[0]))

        if type(inputs) == int or type(inputs) == str or type(inputs) == list:
            network = get_layer(inputs)
        elif type(inputs) == tuple:
            layers = map(get_layer, inputs)
            network = None
            for flag in inputs_handler:
                if flag in flags:
                    network = inputs_handler[flag](
                            layers, info[-1], stacks, this_model)
                    break
            if network is None:
                network = concat_handler(layers, info[-1], stacks, this_model)
        else:
            print type(inputs)
            raise Exception

        info = info[0:1]+deep_eval(info[1:], {
            curr_stacks: stacks,
            curr_layer: network,
            curr_flags: info[-1],
            curr_model: this_model,
            softmax: nonlinearities['softmax'],
            rectify: nonlinearities['rectify'],
            sigmoid: nonlinearities['sigmoid'],
            tanh: nonlinearities['tanh'],
            linear: nonlinearities['linear'],
            })
        flags = info[-1]

        if verbose:
            print info

        active_handlers = set()

        for flag in flag_list:
            if flag in flags:
                if len(flag_excluding[flag] & set(flags)) == 0:
                    h = flag_handler[flag]
                    active_handlers.add(h)
                    network, layers = h(network, info[-1], stacks, this_model)
                    paramlayers += layers
            elif flag in active_handlers:
                h = flag_handler_closer[flag]
                active_handlers.add(h)
                network, layers = h(network, info[-1], stacks, this_model)
                paramlayers += layers
        if verbose:
            print network
        all_layers.add(network)

        if layer_handler:
            layer_handler(network)

    stacks['output'] = [network]
    if 'finish' in kwargs:
        kwargs['finish'](stacks,this_model['errors'],this_model['watchpoints'])
    all_layers.finish()

    if verbose:
        print 'network before wrapper:', network
    if network_wrapper:
        network = network_wrapper(network, stacks, this_model)

    errors = this_model['errors']
    watchpoints = this_model['watchpoints']
    return network, stacks, paramlayers, errors, watchpoints
