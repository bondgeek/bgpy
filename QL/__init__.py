'''
QLNet
'''
import sys

try:
    import clr
    QL_LIB = 'C:\\Program Files\\Resolver One\\site-packages\\Quantlib\\lib'
    if QL_LIB not in sys.path:
        sys.path.append(QL_LIB)
    clr.AddReference('NQuantLib')
    CONFIG_NAME = 'IPY'
except:
    CONFIG_NAME = 'PY'
    
    
from QuantLib import *

from bgpy import aliasReferences as _aliasReferences
from bgdate import bgDate, dateTuple, dateFirstOfMonth

_createAliases = vars().update

def freqValue(freq_):
    '''
    deals with different treatments of enumerations in C++/C# bindings
    '''
    return getattr(freq_, "value__", freq_)

if CONFIG_NAME == 'PY':
    # Matching c-sharp QuantLib bindings
    # because you can't go the other way (c++ to c#)
    RateHelperVector.Clear = RateHelperVector.clear
    RateHelperVector.Add = RateHelperVector.append
    
#
# Aliases 
#
# Calendars & DayCounters

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
    _createAliases(_aliasReferences(Frequency, vars()))
    _createAliases(_aliasReferences(Compounding, vars()))
    _createAliases(_aliasReferences(BusinessDayConvention, vars()))
    _createAliases(_aliasReferences(TimeUnit, vars()))
    _createAliases(_aliasReferences(DateGeneration.Rule, vars()))

    
else:
    USGovernmentBond = UnitedStates(UnitedStates.GovernmentBond)
    USNYSE = UnitedStates(UnitedStates.NYSE)
    USSettlement = UnitedStates(UnitedStates.Settlement)
    USNERC = UnitedStates(UnitedStates.NERC)
    ActualActualBond = ActualActual(ActualActual.Bond)
    ActualActualISDA = ActualActual(ActualActual.ISDA)
    Thirty360Bond = Thirty360(Thirty360.BondBasis)
    Thirty360EuroBond = Thirty360(Thirty360.EurobondBasis)
    _createAliases(_aliasReferences(DateGeneration, vars()))

class Tenor(object):
    _tenorUnits = {'D': Days,
                   'W': Weeks, 
                   'M': Months, 
                   'Y': Years}
    _tenorLength = {'D': 365,
                   'W':52, 
                   'M': 12, 
                   'Y': 1}  # useful for sorting
    
    def __init__(self, txt):
        firstNum = True
        firstCh = True
        numTxt = ""
        unit="Y"
        for i in txt.strip().replace(' ',''):
            if(i.isalnum()):
                if(i.isdigit()):
                    if(firstCh):
                        numTxt=numTxt+i
                        if(firstNum):
                            firstNum = False
                elif(i.isalpha()):
                    if(firstCh):                            
                        unit = i.upper()
            else:
                pass
        if(firstNum):
            numTxt="0"
        
        self.length = int(numTxt)
        self.unit = unit
        self.timeunit = self._tenorUnits.get(self.unit, Days)
    
    def numberOfPeriods(self, frequency=Semiannual):
        '''
        Returns the number of integer periods in the tenor based on the given frequency.
        '''
        return int(self.term * freqValue(frequency))
    
    def advance(self, date_, adjustType=Unadjusted, calendar=TARGET(),):
        return calendar.advance(date_, self.length, self.timeunit, adjustType)
        
    @property
    def term(self):
        '''
        Length of tenor in years.
        '''
        return float(self.length) / float(self._tenorLength.get(self.unit, 1.0))
        
    @property
    def qlPeriod(self):
        return Period(self.length, self.timeunit)
    
    @property
    def qlTuple(self):
        return (self.length, self.timeunit)
        
def setLiborIndex(libor=None, settlementDate=None, fixingRate=None, liborTenor='3M'):
    '''
    Add a fixing for the appropriate date corresponding to a given settlement date.
    If no fixing rate is given, returns the fixing for the given date, 
    or None if does not exist--avoiding RuntimeError thrown by QuantLib
    '''
    if not libor:
        libor = USDLibor(Tenor(liborTenor).qlPeriod)

    if settlementDate:
        assert settlementDate and fixingRate, "Must supply both settlementDate and fixingRate"
        
        fixingDate = libor.fixingDate(settlementDate)    
        if fixingRate:
            try:
                libor.addFixing(fixingDate, fixingRate)
            except:
                return libor
        else:
            try:
                fixing = libor.fixing(fixingDate)
            except:
                return libor

    return libor
