'''
module creates QuantLib environment based on platform: Python (CPython) or
IronPython

Not meant to be used directly, though it could be.  Best use is via
bgpy.QL

Assumes QuantLib bindings for Python and IronPython are in different
directories, neither of which is on the PATH or PYTHONPATH.

'''
import sys
import os

# set environment configuration for QuantLib
try:
    import clr
    QL_LIB = os.environ.get('IPYONLY',
             'C:\\Users\\Public\\Libraries\\Python\\IPY\\Quantlib\\lib')
    
    if QL_LIB not in sys.path:
        sys.path.append(QL_LIB)
    clr.AddReference('NQuantLib')
    CONFIG_NAME = 'IPY'        
    from QuantLib import *
        
except:
    QL_LIB = os.environ.get('PYONLY',
             'C:\\Users\\Public\\Libraries\\Python\\NOIPY')

    if QL_LIB not in sys.path:
        sys.path.append(QL_LIB)
    
    CONFIG_NAME = 'PY'
    from QuantLib import *




def freqValue(freq_):
    '''
    deals with different treatments of enumerations in C++/C# bindings
    '''
    return getattr(freq_, "value__", freq_)

def _aliasReferences(namespc, oldspace=None, ignorePrivate=True):
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


# Create aliases to allow consistent use of c++ & c# bindings
if CONFIG_NAME == 'IPY':
    USGovernmentBond = UnitedStates(UnitedStates.Market.GovernmentBond)
    USGovernmentNYSE = UnitedStates(UnitedStates.Market.NYSE)
    USGovernmentSettlement = UnitedStates(UnitedStates.Market.Settlement)
    USGovernmentNERC = UnitedStates(UnitedStates.Market.NERC)
    ActualActualBond = ActualActual(ActualActual.Convention.Bond)
    ActualActualISDA = ActualActual(ActualActual.Convention.ISDA)
    Thirty360Bond = Thirty360(Thirty360.Convention.BondBasis)
    Thirty360EuroBond = Thirty360(Thirty360.Convention.EurobondBasis)
     
    # Import various sub-namespaces
    vars().update(_aliasReferences(Frequency, vars()))
    vars().update(_aliasReferences(Compounding, vars()))
    vars().update(_aliasReferences(BusinessDayConvention, vars()))
    vars().update(_aliasReferences(TimeUnit, vars()))
    vars().update(_aliasReferences(DateGeneration.Rule, vars()))

    def bermudanExercise(sched_):
        dates = [sched_.date(n) for n in range(sched_.size())]
        
        return BermudanExercise( DateVector(dates) )
        
else:
    # Matching c-sharp QuantLib bindings on Vectors / Schedule
    # because you can't go the other way (c++ to c#)
    for x in dir(QuantLib): 
        if x.find("Vector") >=0 and x.find("swigregister") < 0:
            vars()[x].Clear = getattr(vars()[x], 'clear', lambda x: None)
            vars()[x].Add = getattr(vars()[x], 'append', lambda x: None)
#    RateHelperVector.Clear = RateHelperVector.clear
#    RateHelperVector.Add = RateHelperVector.append
    Schedule.date = lambda self, n: self.__getitem__(n)
        
    USGovernmentBond = UnitedStates(UnitedStates.GovernmentBond)
    USNYSE = UnitedStates(UnitedStates.NYSE)
    USSettlement = UnitedStates(UnitedStates.Settlement)
    USNERC = UnitedStates(UnitedStates.NERC)
    ActualActualBond = ActualActual(ActualActual.Bond)
    ActualActualISDA = ActualActual(ActualActual.ISDA)
    Thirty360Bond = Thirty360(Thirty360.BondBasis)
    Thirty360EuroBond = Thirty360(Thirty360.EurobondBasis)
    vars().update(_aliasReferences(DateGeneration, vars()))
        
    def bermudanExercise(sched_):
        return BermudanExercise( sched_ )
