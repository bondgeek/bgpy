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

PathJoin = os.path.join

from bgpy.xldb import XLdb, XLOut

from bgpy.cusips import cusipcheckdigit, ischeckdigit, validate_cusip
            