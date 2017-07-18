#!/usr/bin/env python
# coding:utf-8
# vi:tabstop=4:shiftwidth=4:expandtab:sts=4

import theano
import theano.tensor as T
import lasagne

from ..stacked import *

def replace_input(layer,m,done=set({})):
    if layer in m:
        return m[layer]
    if layer in done:
        return layer
    done.add(layer)
    if hasattr(layer, 'input_layer'):
        if layer.input_layer in m:
            layer.input_layer=m[layer.input_layer]
        else:
            replace_input(layer.input_layer,m,done)
    if hasattr(layer, 'input_layers'):
        for i,t in enumerate(layer.input_layers):
            if t in m:
                layer.input_layers[i]=m[t]
            else:
                replace_input(t,m,done)
    return layer

def stacks_replace_input(stacks,m):
    for k in stacks:
        a=stacks[k]
        if type(a)==list:
            for i,t in enumerate(a):
                a[i]=replace_input(t,m)
        else:
            for k in a:
                aa=a[k]
                for i,t in enumerate(aa):
                    aa[i]=replace_input(t,m)

class PlaceHolderLayer(lasagne.layers.InputLayer):
    pass
class ZeroLayer(lasagne.layers.InputLayer):
    pass

class LasagneLayers(Layers):
    def get_layer(self,k):
        if type(k)==list and len(k)==1:
            res=lasagne.layers.NonlinearityLayer(self.get_layer(k[0]),theano.gradient.disconnected_grad)
            return res
        
        if type(k)==int:
            return self.layers[::-1][k]
        if type(k)==list and len(k)>1:
            assert len(k)==3
            if not k[0] in self.future:
                batchsize=lasagne.layers.get_output_shape(self.layers[0])[0]
                self.future[k[0]]=PlaceHolderLayer(shape=(batchsize,)+k[1])
            return self.future[k[0]]
        return self.stacks[k][-1] 
    def finish(self):
        m={}
        for k in self.future:
            m[self.future[k]]=self.stacks[k][0]
        print m
        stacks_replace_input(self.stacks,m)

register_layers_class(LasagneLayers)

def concat_handler(layers,flags,stacks,this_model):
    return lasagne.layers.ConcatLayer(layers,axis=1)
def merge_handler(layers,flags,stacks,this_model):
    return lasagne.layers.ElemwiseMergeLayer(layers,flags['op'])
def add_handler(layers,flags,stacks,this_model):
    return lasagne.layers.ElemwiseMergeLayer(layers,T.add)
def sub_handler(layers,flags,stacks,this_model):
    return lasagne.layers.ElemwiseMergeLayer(layers,T.sub)

register_concat_handler(concat_handler)
register_inputs_handler('op',merge_handler)
register_inputs_handler('add',add_handler)
register_inputs_handler('sub',sub_handler)

def reshape_handler(network,flags,stacks,this_model):
    if 'raw' in flags:
        network=lasagne.layers.ReshapeLayer(network,flags['reshape'])
    else:
        network=lasagne.layers.ReshapeLayer(network,(-1,)+flags['reshape'])
    return network,()
def slice_handler(network,flags,stacks,this_model):
    if 'axis' in flags:
        axis=flags['axis']
    else:
        axis=1
    network=lasagne.layers.SliceLayer(network,flags['slice'],axis=axis)
    return network,()
def maxpool_handler(network,flags,stacks,this_model):
#    num_filters=flags['num_filters']
    conv_stride=flags['stride'] if 'stride' in flags else 0
#    if conv_stride==0 or conv_stride==1:
#        pad='same'
#    elif conv_stride>0:
#        if filter_size==conv_stride:
#            pad=0
#        else:
#            pad='same'
#    else: #conv_stride<0
#        num_filters=num_filters*(-conv_stride)*(-conv_stride)
#        if not 'nopad' in flags:
#            pad='same'
#        else:
#            pad=0

    layername=flags['layername'] if 'layername' in flags else None
    filter_size=flags['filter_size'] if 'filter_size' in flags else 0

    dim=len(lasagne.layers.get_output_shape(network))-2
    convs={
            1:lasagne.layers.Pool1DLayer,
            2:lasagne.layers.Pool2DLayer,
            3:lasagne.layers.Pool3DLayer,
            }
    assert dim in convs
    conv=convs[dim]
    assert filter_size>0
    network = conv(
        network, #num_filters=num_filters,
        pool_size=filter_size,
        stride=max(1,conv_stride),
        pad=0,
        mode='max',
        name=layername,
        )
    return network,()
def meanpool_handler(network,flags,stacks,this_model):
#    num_filters=flags['num_filters']
    conv_stride=flags['stride'] if 'stride' in flags else 0
#    if conv_stride==0 or conv_stride==1:
#        pad='same'
#    elif conv_stride>0:
#        if filter_size==conv_stride:
#            pad=0
#        else:
#            pad='same'
#    else: #conv_stride<0
#        num_filters=num_filters*(-conv_stride)*(-conv_stride)
#        if not 'nopad' in flags:
#            pad='same'
#        else:
#            pad=0

    layername=flags['layername'] if 'layername' in flags else None
    filter_size=flags['filter_size'] if 'filter_size' in flags else 0

    dim=len(lasagne.layers.get_output_shape(network))-2
    convs={
            1:lasagne.layers.Pool1DLayer,
            2:lasagne.layers.Pool2DLayer,
            3:lasagne.layers.Pool3DLayer,
            }
    assert dim in convs
    conv=convs[dim]
    assert filter_size>0
    network = conv(
        network, #num_filters=num_filters,
        pool_size=filter_size,
        stride=max(1,conv_stride),
        pad=0,
        mode='average_inc_pad',
        name=layername,
        )
    return network,()
def upscale_handler(network,flags,stacks,this_model):
#    num_filters=flags['num_filters']
    conv_stride=flags['stride'] if 'stride' in flags else 0
#    if conv_stride==0 or conv_stride==1:
#        pad='same'
#    elif conv_stride>0:
#        if filter_size==conv_stride:
#            pad=0
#        else:
#            pad='same'
#    else: #conv_stride<0
#        num_filters=num_filters*(-conv_stride)*(-conv_stride)
#        if not 'nopad' in flags:
#            pad='same'
#        else:
#            pad=0

    layername=flags['layername'] if 'layername' in flags else None
    filter_size=flags['filter_size'] if 'filter_size' in flags else 0

    dim=len(lasagne.layers.get_output_shape(network))-2
    assert filter_size>0
    convs={
            1:lasagne.layers.Upscale1DLayer,
            2:lasagne.layers.Upscale2DLayer,
            3:lasagne.layers.Upscale3DLayer,
            }
    assert dim in convs
    conv=convs[dim]
    network = conv(
        network,
        scale_factor=filter_size,
        name=layername,
        mode='repeat',
        )
    return network,()

def num_filters_handler(network,flags,stacks,this_model):
    paramlayers=[]
    if 'sharegroup2params' not in this_model:
        this_model['sharegroup2params']={}
    sharegroup2params=this_model['sharegroup2params']

    num_filters0=flags['num_filters']
    num_filters=flags['num_filters']
    conv_stride=flags['stride'] if 'stride' in flags else 0
    if conv_stride==0 or conv_stride==1:
        pad='same'
    elif conv_stride>0:
        if filter_size==conv_stride:
            pad=0
        else:
            pad='same'
    else: #conv_stride<0
        num_filters=num_filters*(-conv_stride)*(-conv_stride)
        if not 'nopad' in flags:
            pad='same'
        else:
            pad=0
    nonlinearity=None
    if 'linear' in flags:
        pass
    elif 'nonlinearity' in flags:
        nonlinearity=flags['nonlinearity']
    else:
        nonlinearity=this_model['relu'] if 'relu' in this_model else lasagne.nonlinearities.rectify

    sharegroup=flags['sharegroup'] if 'sharegroup' in flags else 0

    if sharegroup and sharegroup in sharegroup2params:
        ww=sharegroup2params[sharegroup][0]
        bb=sharegroup2params[sharegroup][1]
        if 'const' in flags:
            ww=theano.gradient.disconnected_grad(ww)
            bb=theano.gradient.disconnected_grad(bb)
    else:
        init=this_model['init'] if 'init' in this_model else lasagne.init.GlorotUniform
        if nonlinearity==lasagne.nonlinearities.leaky_rectify:
            alpha=0.01
            ww=init(gain=math.sqrt(2/(1+alpha**2)))
        elif nonlinearity==lasagne.nonlinearities.sigmoid:
            ww=init()
        else:
            ww=init(gain='relu')
        bb=lasagne.init.Constant(0.0)

    layername=flags['layername'] if 'layername' in flags else None
    filter_size=flags['filter_size'] if 'filter_size' in flags else 0

    dim=len(lasagne.layers.get_output_shape(network))-2
    if 'maxpool' in flags or 'meanpool' in flags:
        convs={
                1:lasagne.layers.Pool1DLayer,
                2:lasagne.layers.Pool2DLayer,
                3:lasagne.layers.Pool3DLayer,
                }
        assert dim in convs
        conv=convs[dim]
#    if 'maxpool' in flags:
#        assert filter_size>0
#        network = conv(
#            network, #num_filters=num_filters,
#            pool_size=filter_size,
#            stride=max(1,conv_stride),
#            pad=0,
#            mode='max',
#            name=layername,
#            )
#    elif 'meanpool' in flags:
#        assert filter_size>0
#        network = conv(
#            network, #num_filters=num_filters,
#            pool_size=filter_size,
#            stride=max(1,conv_stride),
#            pad=0,
#            mode='average_inc_pad',
#            name=layername,
#            )
#    elif 'upscale' in flags:
#        assert filter_size>0
#        convs={
#                1:lasagne.layers.Upscale1DLayer,
#                2:lasagne.layers.Upscale2DLayer,
#                3:lasagne.layers.Upscale3DLayer,
#                }
#        assert dim in convs
#        conv=convs[dim]
#        network = conv(
#            network,
#            scale_factor=filter_size,
#            name=layername,
#            mode='repeat',
#            )
#    else:

    if 'dense' in flags or dim==0:
        network = lasagne.layers.DenseLayer(network,num_units=num_filters,
            W=ww,
            b=bb,
            nonlinearity=nonlinearity,
            name=layername,
            )
    else:
        input_shape = lasagne.layers.get_output_shape(network)
        if not 'local' in flags:
            convs={
                    1:lasagne.layers.Conv1DLayer,
                    2:lasagne.layers.Conv2DLayer,
                    3:lasagne.layers.Conv3DLayer,
                    }
            assert dim in convs
            conv=convs[dim]

            assert filter_size>0
            network = conv(
                network, num_filters=num_filters,
                filter_size=filter_size,
                stride=max(1,conv_stride),
                pad=pad,
                W=ww,
                b=bb,
                nonlinearity=nonlinearity,
                name=layername,
                )
        else:
            convs={
                    1:lasagne.layers.LocallyConnected1DLayer,
                    2:lasagne.layers.LocallyConnected2DLayer,
                    3:lasagne.layers.LocallyConnected3DLayer,
                    }
            assert dim in convs
            conv=convs[dim]
            assert conv_stride==1
            assert filter_size>0
            network = conv(
                network, num_filters=num_filters,
                filter_size=filter_size,
                stride=max(1,conv_stride),
                pad=pad,
                W=ww,
                b=bb,
                nonlinearity=nonlinearity,
                name=layername,
                untie_biases=True,
                )
    paramlayers+=[network]
    if sharegroup and sharegroup not in sharegroup2params:
        sharegroup2params[sharegroup]=[network.W,network.b]
    if 'saveparamlayer' in flags and flags['saveparamlayer'] is not None:
        g=flags['saveparamlayer']
        if g not in stacks:
            stacks[g]=[]
        stacks[g]+=[network]
    if conv_stride<0:
        b,c,width,height = lasagne.layers.get_output_shape(network)
        network = lasagne.layers.ReshapeLayer(network,(b,num_filters0,-conv_stride,-conv_stride,width,height))
        network = lasagne.layers.DimshuffleLayer(network,(0,1,4,2,5,3))
        network = lasagne.layers.ReshapeLayer(network,(b,num_filters0,width*(-conv_stride),height*(-conv_stride)))
    return network,paramlayers

def dimshuffle_handler(network,flags,stacks,this_model):
    return lasagne.layers.DimshuffleLayer(network,flags['dimshuffle']),()
def noise_handler(network,flags,stacks,this_model):
    return lasagne.layers.GaussianNoiseLayer(network,flags['noise']),()

def watch_handler(network,flags,stacks,this_model):
    get_layer=this_model['get_layer']

    tmp=None
    g=None
    if type(flags['watch'])==str:
        g = flags['watch']
        tmp=network
    else:
        if len(flags['watch'])==2:
            to,g=flags['watch']
            eq=lasagne.objectives.squared_error
        else:
            to,g,eq=flags['watch']
        if type(to)==type(lambda x:x):
            tmp=lasagne.layers.ExpressionLayer(network,to,output_shape=(batchsize,))
        elif to=='zeros':
            s0=lasagne.layers.get_output_shape(network)
            target=ZeroLayer(shape=s0,input_var=T.zeros(s0,dtype=theano.config.floatX))
            #tmp=lasagne.layers.NonlinearityLayer(network,
            #        nonlinearity=lambda x:x**2.0
            #        )
            tmp=lasagne.layers.ElemwiseMergeLayer((network,target),eq)
        else:
            target=get_layer(to)
            tmp=lasagne.layers.ElemwiseMergeLayer((network,target),eq)
    if 'sum' in flags:
        if type(flags['sum'])==int:
            n=flags['sum']
        else:
            n=1
        shape=lasagne.layers.get_output_shape(tmp)[:n]
        tmp=lasagne.layers.ExpressionLayer(tmp,curry(lambda n,shape,x:x.flatten(ndim=n+1).sum(axis=n),n,shape),output_shape=shape)
    if g not in watchpoints:
        watchpoints[g]=[]
    watchpoints[g]+=[tmp]
    return network,()

def equal_handler(network,flags,stacks,this_model):
    get_layer=this_model['get_layer']

    if 'errors' not in this_model:
        this_model['errors']={}
    errors=this_model['errors']
    if len(flags['equal'])==2:
        to,g=flags['equal']
        eq=lasagne.objectives.squared_error
    else:
        to,g,eq=flags['equal']
    if g not in errors:
        errors[g]=[]
    if to=='zeros':
        s0=lasagne.layers.get_output_shape(network)
        target=ZeroLayer(shape=s0,input_var=T.zeros(s0,dtype=theano.config.floatX))
    else:
        target=get_layer(to)
    tmp=lasagne.layers.ElemwiseMergeLayer((network,target),eq)
    if 'sum' in flags:
        if type(flags['sum'])==int:
            n=flags['sum']
        else:
            n=1
        shape=lasagne.layers.get_output_shape(tmp)[:n]
        tmp=lasagne.layers.ExpressionLayer(tmp,curry(lambda n,shape,x:x.flatten(ndim=n+1).sum(axis=n),n,shape),output_shape=shape)
    errors[g]+=[ tmp ]
    return network,()

def relu_handler(network,flags,stacks,this_model):
    assert flags['relu'] is True
    nonlinearity=this_model['relu'] if 'relu' in this_model else lasagne.nonlinearities.rectify
    if 'shape' in flags:
        shape=flags['shape']
        if type(shape)==tuple:
            shape=list(shape)
        if type(shape)==list and shape[0]==None:
            shape[0]=lasagne.layers.get_output_shape(network)[0]
        network = lasagne.layers.ExpressionLayer(network,nonlinearity,output_shape=shape)
    else:
        network = lasagne.layers.NonlinearityLayer(network,nonlinearity=nonlinearity)
    return network,()
def nonlinearity_handler(network,flags,stacks,this_model):
    relu=this_model['relu'] if 'relu' in this_model else lasagne.nonlinearities.rectify
    if type(flags)==dict:
        if 'nonlinearity' in flags:
            nonlinearity=flags['nonlinearity']
        if nonlinearity==True:
            nonlinearity=relu
    else:
        nonlinearity=relu
    if 'shape' in flags:
        shape=flags['shape']
        if type(shape)==tuple:
            shape=list(shape)
        if type(shape)==list and shape[0]==None:
            shape[0]=lasagne.layers.get_output_shape(network)[0]
        network = lasagne.layers.ExpressionLayer(network,nonlinearity,output_shape=shape)
    else:
        network = lasagne.layers.NonlinearityLayer(network,nonlinearity=nonlinearity)
    return network,()

def argmax_handler(network,flags,stacks,this_model):
    if type(flags['argmax'])==tuple:
        axis=flags['argmax']
    else:
        axis=(1,)
    shape=lasagne.layers.get_output_shape(network)
    output_shape=()
    for idx,w in enumerate(shape):
        if idx not in axis:
            output_shape+=(w,)
    network = lasagne.layers.ExpressionLayer(network,curry(lambda shape,axis,beta,x: goroshin_argmax(x,shape,axis=axis,beta=beta).astype(theano.config.floatX),shape,axis,flags['beta']), output_shape=output_shape[0:1]+(len(axis),)+output_shape[1:])
    return network,()
def unargmax_handler(network,flags,stacks,this_model):
    if type(flags['unargmax'])==tuple:
        axis=flags['unargmax']
    else:
        axis=(1,)
    shape=flags['shape']
    if type(shape)==tuple:
        shape=list(shape)
    if type(shape)==list and shape[0]==None:
        shape[0]=lasagne.layers.get_output_shape(network)[0]
    network = lasagne.layers.ExpressionLayer(network,curry(lambda shape,axis,x: goroshin_unargmax(x,shape,axis=axis).astype(theano.config.floatX),shape,axis), output_shape=shape)
    return network,()

def max_handler(network,flags,stacks,this_model):
    if type(flags['max'])==tuple:
        axis=flags['max']
    else:
        axis=(1,)
    shape=list(lasagne.layers.get_output_shape(network))
    for i in axis:
        shape[i]=1
    network = lasagne.layers.ExpressionLayer(network,curry(lambda axis,beta,x: goroshin_max(x,axis=axis,beta=beta,keepdims=True).astype(theano.config.floatX),axis,flags['beta']), output_shape=shape)
    return network,()

register_flag_handler('equal',equal_handler)
register_flag_handler('watch',watch_handler)

register_flag_handler('relu',relu_handler)
register_flag_handler('nonlinearity',nonlinearity_handler,('num_filters',))
register_flag_handler('noise',noise_handler)
register_flag_handler('unargmax',unargmax_handler)
register_flag_handler('argmax',argmax_handler)
register_flag_handler('max',max_handler)
register_flag_handler('dimshuffle',dimshuffle_handler)
register_flag_handler('num_filters',num_filters_handler,('maxpool','meanpool','upscale'))
register_flag_handler('upscale',upscale_handler)
register_flag_handler('meanpool',meanpool_handler)
register_flag_handler('maxpool',maxpool_handler)
register_flag_handler('slice',slice_handler)
register_flag_handler('reshape',reshape_handler)