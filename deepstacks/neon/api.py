#!/usr/bin/env python
# coding:utf-8
# vi:tabstop=4:shiftwidth=4:expandtab:sts=4

from ..stacked import curr_layer,curr_stacks,curr_flags,curr_model

def query_batchsize_fn(curr_layer):
    return curr_layer.be.bsz

curr_batchsize=(query_batchsize_fn,curr_layer,{})