'''
bgpyXL.py

Wraps bgpy functions for use in pyinex

'''
# not necessary, but here for documentation
# import pyinex


from bgpy.xl.xl_markets import curve, tenorpar, listTermStructures, xlDate

from bgpy.cusips import cusipcheckdigit, validate_cusip

from bgpy.QL import Date as _qDate
from bgpy.QL import toDate, Settings
from datetime import date

_qToday = None
        
def HasVarArgs(*args):

    r2 = str(len(args)) + ' varargs'
    r3 = 'Varargs: ' + ','.join([str(x) for x in args]) + ')'
    
    return r3
    
def qToday():
    """returns today's date in ISO format"""
    
    return _qDate.todaysDate().ISO()

def setEvaluationDate(cell):
    """set global value for _qToday"""
    global _qToday
    
    _qToday = toDate(cell.value)
    if not to_date:
        _qToday = Settings.instance().getEvaluationDate()
    else:
        Settings.instance().setEvaluationDate(_qToday)
    
    return _qToday.ISO()
    
def setEvaluationDate():
    """get QuantLib today"""
    
    if hasattr(_qToday, "ISO"):
        return _qToday.ISO()
    else:
        return None
