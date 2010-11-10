'''
bgpy module

Generic python application facilities.

Root Module includes the two features from 'os' module that I use most often:
- HOMEPATH -- string representing the local home path
- PathJoin -- alias for os.path.join

from bgpy import HOMEPATH, PathJoin

bgpy modules:
- bloomberg
- cusips
- develtools
- dpatterns
- xldb
'''

try:
    # os should be on path
    import os
except:
    # if not, try Resolver setup, if this doesn't work--SOL
    from resolverlib import *
    import os
    
__copyright__ = 'Copyright (c) 2010 Bart Mosley, BG Research LLC'

version = (0,0,1)
version_string = "bgpy:  BG Tools version %d.%d.%d " % version

HOMEDRIVE = os.environ.get("HOMEDRIVE", None) # only for windows
HOMEPATH = os.environ.get('HOME', os.environ.get('HOMEPATH', None))
HOMEPATH = os.path.join(HOMEDRIVE, HOMEPATH)

DATADIR = os.environ.get('BGPY_DATADIR', HOMEPATH)
PathJoin = os.path.join

def aliasReferences(namespc, oldspace=None, ignorePrivate=True):
    '''
    Take a reference to a namespace and create alias dict object 
    to be passed to vars().update
    
    Optionally, provide oldspace=vars() to allow check against overwriting
    existing objects.
    '''
    newspace = {}
    if not oldspace:
        oldspace = newspace
        
    for _v in dir(namespc):
        if ignorePrivate and (_v.startswith("_") or _v.endswith("_")):
            continue
        if not oldspace.get(_v, None):
            newspace[_v] = getattr(namespc, _v, None)
    return newspace
