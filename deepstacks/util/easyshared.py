import theano
import os
from floatXconst import * 

file2shared={}

def add(filename,value):
    global file2shared
    file2shared[filename]=theano.shared(floatXconst(value))
    return file2shared[filename]

def update():
    global file2shared
    for filename in file2shared.keys():
        if os.path.exists(filename):
            f=open(filename)
            t=f.read()
            f.close()
            print 'read value from',filename,', got',float(t)
            file2shared[filename].set_value(floatXconst(float(t)))
