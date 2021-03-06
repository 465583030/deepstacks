#!/usr/bin/env python
# coding:utf-8
# vi:tabstop=4:shiftwidth=4:expandtab:sts=4

import theano
import theano.tensor as T
import lasagne
from deepstacks.lasagne import curr_batchsize

def classify(target,r=1.0):
    return (
            (0,0,0,0,0,0,{
                'equal':[target,'classify',lambda x,y:r*lasagne.objectives.categorical_crossentropy(x,y),],
                }),
            (0,0,0,0,0,0,{
                'nonlinearity':lambda x:T.argmax(x, axis=1),'shape':(curr_batchsize,),
                'watch':[target,'val:accuracy',T.eq],
                }),
            )

