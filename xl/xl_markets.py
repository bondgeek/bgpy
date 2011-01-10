'''
xl_markets.py


'''
from bgpy.cusips import validate_cusip

from datetime import date
from bgpy.QL import SimpleCurve, SimpleBond, toDate, Call

# global dictionary to 
_TermStructures = {}
_Portfolio = {}

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

def listTermStructures():
    return ": ".join([str(id) for id in _TermStructures])

def isColumn(xrange):
    flag = True
    for x in xrange:
        flag *= hasattr(x, "__iter__")
    return flag

def rowIfColumn(xrange):
    if isColumn(xrange):
        return [x[0] for x in xrange]
    return xrange

def curve(tenors, curve, id, curvedate):
    """Assign yield curve values. """
    
    global _TermStructures
    
    if id not in _TermStructures:
        _TermStructures[id] = SimpleCurve()
    
    if len(tenors) != len(curve):
        return None
    
    tlist = tuple(rowIfColumn(tenors))
    clist = tuple(rowIfColumn(curve))

    curvedata = dict(zip(tlist, clist))
    
    _TermStructures[id].update(curvedata)
    
    return id

def bondpar(id, maturity):
    """bond par"""

    mty = toDate(xlDate(maturity))    
    if id in _TermStructures:
        return _TermStructures[id].bondpar(mty)
    
    return "Not Found"

def tenorpar(id, tenor):
    """tenorpar"""
    
    if id in _TermStructures:
        return _TermStructures[id].tenorpar(tenor)
    
    return -1
    
def addPortfolioBond(cusip, coupon, maturity, callable, firstCall, callPrice, parCall):
    
    global _Portfolio

    callfeature = None
    if callable.upper() == "Y":
        callfeature = Call(toDate(xlDate(firstCall)),
                           callPrice,
                           toDate(xlDate(parCall)))
        
    _Portfolio[cusip] = SimpleBond(coupon, toDate(xlDate(maturity)))
    
    return cusip

def bondCalc(cusip, calcFrom, level):
    global _Portfolio

    calFrom = calcFrom.upper()
    bond = _Portfolio.get(cusip, None)
    
    if not bond:
        return "Not Found"

    if calcFrom not in ["P", "Y"]:
        return "Invalid Calc"
    else:
        if calcFrom == "P":
            output = bond.calc(bondprice=level)
        elif calcFrom == "Y":
            output = bond.calc(bondyield=level)

    return output

def toPrice(cusip, bondyield):
    return bondCalc(cusip, "Y", bondyield)

def toYield(cusip, bondprice):
    return bondCalc(cusip, "P", bondprice)

def oasCalc(cusip, curve, price, vol, attr):
    global _Portfolio

    bond = _Portfolio.get(cusip, None)
    termstr = _TermStructures.get(curve, None)
    if not bond:
        return "Bond Not Found"
    if not termstr:
        return "Curve Not Found"
    
    asw = bond.assetSwap()
    sprx = asw.solveSpread(termstr, price, vol)

    return sprx.get(attr, None)
