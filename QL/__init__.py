'''
QLNet
'''
import sys
import clr
QL_LIB = 'C:\\Program Files\\ResolverLib\\Quantlib\\lib'
if QL_LIB not in sys.path:
    sys.path.append(QL_LIB)
clr.AddReference('NQuantLib')

from QuantLib import *

from System.Collections.Generic import List
from bgpy import aliasReferences as _aliasReferences
from bgdate import bgDate, dateTuple, dateFirstOfMonth

_createAliases = vars().update
    
#
# Aliases 
#
#RateHelperVector = List[RateHelper]
# QuoteHandle = Handle[Quote]  #QuantLib compatibility

# Calendars
USGovernmentBond = UnitedStates(UnitedStates.Market.GovernmentBond)
USGovernmentNYSE = UnitedStates(UnitedStates.Market.NYSE)
USGovernmentSettlement = UnitedStates(UnitedStates.Market.Settlement)
USGovernmentNERC = UnitedStates(UnitedStates.Market.NERC)
 
# Import various sub-namespaces
#_createAliases(_aliasReferences(Time.DayCounters, vars()))
_createAliases(_aliasReferences(Frequency, vars()))
_createAliases(_aliasReferences(Compounding, vars()))
_createAliases(_aliasReferences(BusinessDayConvention, vars()))
_createAliases(_aliasReferences(DateGeneration.Rule, vars()))
_createAliases(_aliasReferences(TimeUnit, vars()))

ActualActualBond = ActualActual(ActualActual.Convention.Bond)
ActualActualISDA = ActualActual(ActualActual.Convention.ISDA)

#Thirty360Bond = Thirty360(Thirty360.Thirty360Convention.BondBasis)
#Thirty360EuroBond = Thirty360(Thirty360.Thirty360Convention.EurobondBasis)

Thirty360Bond = Thirty360(Thirty360.Convention.BondBasis)
Thirty360EuroBond = Thirty360(Thirty360.Convention.EurobondBasis)


class Tenor(object):
    _tenorUnits = {'D': Days,
                   'W': Weeks, 
                   'M': Months, 
                   'Y': Years}
    
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
        self.timeunit = self._tenorUnits[unit]
    
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
