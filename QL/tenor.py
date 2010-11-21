'''
Tenor class

@author: Bart Mosley
'''

import bgpy.__QuantLib as ql

from bgpy.QL.bgdate import toDate

class Tenor(object):
    _tenorUnits = {'D': ql.Days,
                   'W': ql.Weeks, 
                   'M': ql.Months, 
                   'Y': ql.Years}
    _tenorLength = {'D': 365,
                   'W': 52, 
                   'M': 12, 
                   'Y': 1}  # useful for sorting
    
    def __init__(self, txt):
        firstNum = True
        firstCh = True
        numTxt = ""
        unit="Y"
        for i in str(txt).replace(' ', ''):
            if i.isalnum():
                if i.isdigit():
                    numTxt = numTxt + i
                    
                    if firstNum:
                        firstNum = False
                elif i.isalpha():
                    if firstCh and (i.upper() in self._tenorUnits):                       
                        unit = i.upper()
                        firstCh = False
            else:
                pass
                
        if(firstNum):
            numTxt="0"
        
        self.length = int(numTxt)
        self.unit = unit
        self.timeunit = self._tenorUnits.get(self.unit, ql.Days)
    
    def __str__(self):
        return str(self.length)+self.unit
    
    def __repr__(self):
        return "<Tenor:"+self.__str__()+">"
             
    def numberOfPeriods(self, frequency=ql.Semiannual):
        '''
        Returns the number of integer periods in the tenor based on the given frequency.
        '''
        return int(self.term * ql.freqValue(frequency))
    
    def advance(self, date_, convention=ql.Unadjusted, calendar=ql.TARGET(), Reverse=False):
        length_ = self.length if not Reverse else -self.length
        return calendar.advance(date_, length_, self.timeunit, convention)
    
    def schedule(self, settle_, maturity_, convention=ql.Unadjusted,
                       calendar=ql.TARGET()):
        '''
        tenor('3m').schedule(settleDate, maturityDate) or
        tenor('3m').schedule(settleDate, '10Y')
        
        gives a schedule of dates from settleDate to maturity with a short front stub.
        '''
        settle_ = toDate(settle_)
        mty_ = toDate(maturity_)
        
        sched = []
        if type(maturity_) == str and not mty_:
            maturity_ = Tenor(maturity_).advance(settle_, 
                                                 convention=convention,
                                                 calendar=calendar)
        else:
            maturity_ = mty_
            
        dt = maturity_
        while dt.serialNumber() > settle_.serialNumber():
            sched.append(calendar.adjust(dt, convention))
            dt = self.advance(dt, Reverse=True)
        else:
            sched.append(settle_)
            
        sched.sort(key=lambda dt: dt.serialNumber())
        
        return sched
                    
    @property
    def term(self):
        '''
        Length of tenor in years.
        '''
        return float(self.length) / float(self._tenorLength.get(self.unit, 1.0))
        
    @property
    def qlPeriod(self):
        return ql.Period(self.length, self.timeunit)
    
    @property
    def qlTuple(self):
        return (self.length, self.timeunit)
