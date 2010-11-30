'''
Tools to facilitate development.

Created August 2010
@author: bartmosley
'''

import time  
import re

from bgpy import HOMEPATH

def dirpub(obj):
    '''
    List of public attributes of the given object.
    '''
    return [attr for attr in dir(obj) if not re.match("_+",attr)]

def dirpubf(obj):
    '''
    List of public methods/functions
    '''
    return [attr for attr in dirpub(obj) 
            if (type(getattr(obj, attr)).__name__ == 'function' or
                type(getattr(obj, attr)).__name__ == 'instancemethod')]

def dirpubv(obj):
    '''
    Dictionary of public attributes and their types
    '''
    mdict = {}
    for attr in dirpub(obj):
        tname = type(getattr(obj, attr)).__name__

        alist = mdict.get(tname, [])
        alist.append(attr)

        mdict[tname] = alist
    return mdict

def dirshow(obj, showdocs = True, return_dict=False):
    '''
    Displays doc strings for public attributes, a la pydoc, 
    and returns a dirpubv dictionary
    '''
    attrs = dirpubv(obj)
    for k in attrs:
        print("TYPE %s:" % k)
        for a in attrs[k]:
            inst = getattr(obj, a)
            if hasattr(inst, "__doc__") and showdocs:
                docstr = getattr(inst, "__doc__")
            else:
                docstr = "No doc string"
            print("> %s: %s" % (a, docstr))
        print("\n")
    
    attrs = attrs if return_dict else None
    
    return attrs

def f_reload(obj):
    '''
    Reloads module for passed in object, if the object has a __module__ attr.
    Deletes the previous instance of the object.
    '''
    if hasattr(obj, "__module__"):
        print("reloading %s" % obj.__module__)
        mod = __import__(obj.__module__)
        del(obj)
        return reload(mod)
    else:
        print("no __module__ for %s" % obj)
        return None

try:
    import inspect

    def fundoc(func):
        '''intropect basic function info'''

        try:        
            #(args, varargs, varkw, defaults)
            argspec = inspect.getargspec(func)

        except TypeError:
            return None

        if argspec[3]:
            dflt = len(argspec[3])
            for n in range(len(argspec[0])-1, 
                           len(argspec[0])-len(argspec[3])-1, 
                           -1):
                argspec[0][n] = "=".join((argspec[0][n], 
                                          str(argspec[3][dflt-1])))
                dflt -= 1

        f_signature = ", ".join(argspec[0])

        if argspec[1]:
            f_signature = ", ".join((f_signature,
                                     "".join(("*", argspec[1]))))
            
        if argspec[2]:
            f_signature = ", ".join((f_signature,
                                     "".join(("**", argspec[2]))))
            
        f_signature = f_signature.join(("(",")"))
        f_signature = "".join([func.func_name, f_signature])

        return f_signature
except:
    print("module inspect not available")
    