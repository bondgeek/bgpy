'''
bgpyXL.py

Wraps bgpy functions for use in pyinex

'''

from bgpy.cusips import cusipcheckdigit, validate_cusip

from bgpy.QL import Date as _qDate
from bgpy.QL import toDate, Settings
from datetime import date

_qToday = None

def xlDate(xdate):
    """Convert xl Date to python date"""
    # QuantLib doesn't support dates prior to 1901
    # which saves us from dealing with the leap year problem
    if xdate < 367:
        return "#Date prior to 1901-01-01"
    
    # python dates are from year zero, excel from 1900
    return date.fromordinal(693594 + int(xdate))

def xlDateISO(xdate):
    """Convert xl Date to ISO string"""
    # QuantLib doesn't support dates prior to 1901
    # which saves us from dealing with the leap year problem
    if xdate < 367:
        return "#Date prior to 1901-01-01"
    
    # python dates are from year zero, excel from 1900
    return date.fromordinal(693594 + int(xdate)).isoformat()
            
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

def isColumn(xrange):
    flag = True
    for x in xrange:
        flag *= hasattr(x, "__iter__")
    return flag

def rowIfColumn(xrange):
    if isColumn(xrange):
        return [x[0] for x in xrange]
    return xrange
