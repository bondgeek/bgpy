"""
Structures to facilitate interpolating financial curves.

"""

import bgpy.QL as ql

from bgpy.math import interp

def is_numeric(x):
    try:
        return float(x)
    except:
        return None
        
class InterpCurve(object):
    '''
    Used to interpolate a financial curve.
    
    Curve is given as a dict object:
    curvedata = {tenor: value}
    
    where tenor is, for example, '10Y' for 10 years.
    
    '''
    def __init__(self, curvedata=None, datadivisor=100.0):
        self.divisor = datadivisor
        
        if curvedata:
            self.update(curvedata)
    
    def update(self, curvedata):
        
        self.curve_ = [(ql.Tenor(tnr).term, val / self.divisor) 
                          for tnr, val in curvedata.items()
                          if is_numeric(val)]
        self.curve_.sort()
    
    def __call__(self, *args):
        '''
        Call with tenor string, e.g. 10Y or settlement, maturity.
        '''
        assert len(args) <= 2, "InterpCurve().__call__ takes either one or two args"
        
        term = None
        if len(args) == 1:
            term = args[0]
            
            if type(term) == str:
                term = ql.Tenor(term).term
                
            elif hasattr(term, "__iter__"):
                sd, mty = term
                return self.maturity(sd, mty)
        
        else:
            sd = args[0]
            mty = args[1]
            return self.maturity(sd, mty)
                
        return interp(self.curve_, term)
    
    def maturity(self, settle, maturity, daycount=ql.ActualActualISDA):
        '''
        Calls interp for given dates
        
        '''
        settle = ql.toDate(settle)
        maturity = ql.toDate(maturity)
        years_ = daycount.yearFraction(settle, maturity)
        return self(years_)
        