import bgpy.QL as ql


def refBond(bond, issuedate=None, call='10Y', coupon=None):
    """
    return a MuniBond object of the bond, adjusted for reference structure.
    
    coupon = None, value
        None:  uses same coupon as bond
        value: coupon to use, e.g. 5% = .05
    
    """
    
    def refCall(settledate, maturitydate, tenor='10Y'):
        refDate0 = ql.Tenor(tenor).advance(settledate)
        
        refDate1 = ql.toDate(maturitydate.dayOfMonth(), 
                            maturitydate.month(),
                            refDate0.year())
        
        if ql.Thirty360().dayCount(refDate1, maturitydate) <= 0:
            return maturitydate
            
        diff = ql.Thirty360().dayCount(refDate0, refDate1)
        
        if abs(diff) <= 180:
            return refDate1
        elif diff > 0:
            reverseFlag = True
        else:
            reverseFlag = False
     
        return ql.Tenor('6M').advance(refDate1, reverse=reverseFlag)
        
    cpn = bond.coupon if not coupon else coupon
    mty = bond.maturity
    
    redval = bond.redvalue
    oid = bond.oid
        
    issuedate = ql.toDate(issuedate) if issuedate else bond.settlementDate
    
    calltenor = ql.Tenor(call)
    calldt = refCall(issuedate, mty)
    
    if ql.Thirty360().dayCount(calldt, mty) > 0:
        bcall = ql.Call(calldt, 100., mty)
    else:
        bcall = None
                    
    stl = bond.settlementDate
    
    return ql.MuniBond(cpn,
                       mty,
                       oid = oid,
                       callfeature=bcall,
                       redvalue=redval,
                       settledate=stl)

