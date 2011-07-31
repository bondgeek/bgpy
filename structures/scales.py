"""scales.py

Class for simple scales (such as MMD)

"""

import bgpy.QL as ql

def couponSoftDiscount(bondyield, tenor, mincoupon=.05, step=.0025):
    '''Returns new issue coupon level
    
    Describes the convention from the old days of dollar bonds being priced 
    at a slight discount.   Sets a floor at 5% to represent the break down after
    1996.
    
    '''
    
    return max(.05, int((bondyield-step)/step)*step)
            
class Scale(object):
    '''The Scale
    
    Represents MMD/MMA, etc generic scales.
    Allows passing a standard call feature, and function for describing couponing
    
    '''
    
    def __init__(self, curvedata=None, curvedate=None, call=("10Y", 100.0), 
                       datadivisor=1.0, coupon="par", settledays=3):
                       
        self.divisor = datadivisor
        self.callfeature_ = call
        self.coupon = (lambda x, t: x) if coupon == "par" else coupon
        self.settledays = settledays
        self.bonds = {}
        
        if curvedata:
            self.update(curvedata, curvedate)
            
    def bondCoupon(self, bondyield, tenor, default=None):
        
        if callable(self.coupon):
            coupon = self.coupon(bondyield, tenor)
        elif hasattr(self.coupon, "get"):
            coupon = self.coupon.get(tenor, default)
        else:
            coupon = self.coupon
        
        return coupon
        
    def update(self, curvedata, curvedate=None):
        '''
        curvedata should be a dict object {tenor: bondyield}
        
        '''
        
        curvedata = dict([(t, curvedata[t]) for t in curvedata 
                          if curvedata[t]])
                             
        self.updateBonds(curvedata, curvedate)
        
        self.bondyields = dict([(t, curvedata[t]/self.divisor) 
                                    for t in curvedata])
    
    def updateBonds(self, curvedata, curvedate):
        if curvedate:
            self.curvedate = curvedate
        else:
            self.curvedate = ql.Settings.instance().getEvaluationDate()
        
        self.settledate = ql.USGovernmentBond.advance(self.curvedate, 
                                                        self.settledays,
                                                        ql.Days)
        self.bonds = dict([(t, 
                            ql.MuniBond(self.bondCoupon(curvedata[t]/self.divisor, t), 
                                        self.mtyTenor(t),
                                        callfeature = self.callTenor(t),
                                        issuedate = self.mtyReference,
                                        oid = curvedata[t]/self.divisor,
                                        settledate=self.settledate)
                            )
                            for t in curvedata] )
    
    def bondPrice(self, tenor):
        if tenor in self.bonds:
            return self.bonds[tenor].toPrice(self.bondyields[tenor])

        return None

    def setSettlment(self, settlement):
        '''Set bond.settlementDate property'''
        for tenor in self.bonds:
            self.bonds[tenor].settlementDate = settlement
        
    def updateBondValues(self, termstructure, curvedata):
        self.bondvalues = {}
        for tenor in self.bonds:
            spread, ratio, vol = curvedata[tenor]
            self.bondvalues[tenor]  = self.bondValue(tenor,
                                                     termstructure,
                                                     spread,
                                                     ratio,
                                                     vol)
        return self.bondvalues
        
    def bondValue(self, tenor, termstructure, spread,
                  ratio=1.0,
                  vol = 1e-7,
                  model=ql.BlackKarasinski):
        '''run oas value'''
        if tenor in self.bonds:
            return self.bonds[tenor].assetSwap().value(termstructure,
                                                       spread,
                                                       ratio,
                                                       vol,
                                                       "S",
                                                       model)
        return None    
    
    @property
    def mtyReference(self):
        "maturities are calculated from first of current month"
        return ql.dateFirstOfMonth(self.curvedate)
    
    @property 
    def callfeature(self):
        return self.callfeature_
    
    def mtyTenor(self, tenor):
        "maturity date associated with given tenor"
        return ql.Tenor(tenor).advance(self.mtyReference)
    
    def callTenor(self, tenor):
        '''
        Call feature associated with given maturity tenor, or None if maturity is before call.
        
        '''
        if not self.callfeature:
            return None
            
        calldate = self.mtyTenor(self.callfeature[0])
        if calldate.serialNumber() >= self.mtyTenor(tenor).serialNumber():
            return None
        
        if len(self.callfeature) == 3:
            pardate = self.mtyTenor(self.callfeature[3])
        else:
            pardate = None

        return ql.Call(calldate, self.callfeature[1], pardate)

    def clear(self):
        self.bonds.clear()
        self.bondyields.clear()
    
class GovtCurve(object):
    bondheader = ('term', 'price', 'yield', 'bond')
    
    def __init__(self, curveobject=None, curvedate=None, settledays=2,
                 daycount=ql.ActualActual(),
                 calendar=ql.TARGET()
                 ):
        self.calendar=calendar
        self.daycount = daycount
        self.settledays = settledays
        
        self.termstructure_ = ql.SimpleCurve(setIborIndex=False)
        
        if curveobject:
            self.update(curveobject, curvedate)
        
    def update(self, curveobject, curvedate):
        #TODO:  add logic for handling TBills (identify by cusip)
        #       discount price input.
        self.curvedate = curvedate
        self.settle = self.calendar.advance(self.curvedate, 
                                            self.settledays,
                                            ql.Days)

        term = self.daycount.yearFraction        
        self.bonds = []
        self.curvedata_ = {}
        for tckr, c, mtystr in curveobject:
            quote = curveobject[(tckr, c, mtystr)]
            mty = ql.toDate(mtystr)

            if tckr[:5] == '91279':
                cpn = 0.0
                b = ql.USTBill(mty, settledate=self.settle)
                prc = b.discountToPrice(quote)
            else:
                cpn = c/100.0
                b = ql.USTBond(cpn, mty, settledate=self.settle)
                prc = quote
            
            yld = b.toYield(prc)
            bondterm = term(self.settle, mty)
            
            info = (bondterm, prc, yld, b)
            self.bonds.append(dict(zip(self.bondheader, info)))
            self.curvedata_[mty] = (cpn, prc)
        
        self.setTermstructure()
        
        return True
        
    def tenor(self, tnr):
    
        term = ql.Tenor(tnr).term
        self.bonds.sort(key=lambda x: x['term'])
        
        N = max([n for n in range(len(self.bonds)) 
                   if self.bonds[n]['term'] < term])
         
        return self.bonds[N]
    
    @property
    def curvedata(self):
        return self.curvedata_
    
    def setTermstructure(self):
        self.termstructure_.update(self.curvedata, self.curvedate)
    
    @property
    def termstructure(self):
        return self.termstructure_
        
