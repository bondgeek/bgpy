'''
bgpyXL.py

Wraps bgpy functions for use in PyXLL.

pyxll.cfg should look like this:

[PYXLL]
pythonpath = <other additional paths, e.g. .;.\examples;> C:\Users\Public\Libraries\Python\bgpy
modules = <worksheetfuncs>, bgpyXL


'''

from pyxll import xl_func

from bgpy.xl.xl_markets import curve, tenorpar

from bgpy.cusips import cusipcheckdigit
from bgpy.QL import Date as qDate
from bgpy.QL import toDate, Settings

gToday = None

@xl_func("string cusip: string")
def qspcheck(cusip):
    """cusip check digit"""
    return cusipcheckdigit(cusip)

    from pyxll import xl_func

@xl_func(":string", category="bgpy")
def qToday():
    """returns today's date in ISO format"""
    
    return qDate.todaysDate().ISO()

@xl_func("xl_cell cell:string", category="bgpy")
def setEvaluationDate(cell):
    """set global value for gToday"""
    global gToday
    
    gToday = toDate(cell.value)
    if not to_date:
        gToday = Settings.instance().getEvaluationDate()
    else:
        Settings.instance().setEvaluationDate(gToday)
    
    return gToday.ISO()
    
@xl_func(":string")
def getToday():
    """get QuantLib today"""
    
    if hasattr(gToday, "ISO"):
        return gToday.ISO()
    else:
        return None
