'''
Municipal bond specific bond calculations

'''

from bgpy.QL.bonds import SimpleBond, BondType, ql
from math import floor

class MuniBondType(BondType):
    settlementdays = 3
    daycount = ql.Thirty360()
    frequency = ql.Semiannual
    payconvention = ql.Following
    termconvention = ql.Unadjusted
    face = 100.0
    
    def bondtype(self):
        d = BondType().bondtype()
        for k in d:
            d[k] = getattr(self, k)
        return d
        
class MuniBond(MuniBondType, SimpleBond):
    '''
    Muni Bond Object, inherits from SimpleBond
    
    '''
    def __init__(self, coupon, maturity, callfeature=None,
                       oid=None,  issuedate=None,
                       redvalue=100.0, settledate=None):
        SimpleBond.__init__(self, coupon, maturity, callfeature, 
                                  oid, issuedate, 
                                  redvalue, settledate)
        
    def qtax(self, settle=None, ptsyear=0.25):
        """Calculate de minimus cut-off for market discount bonds"""
        if settle or not self.settle_:
            self.setSettlement(settle)
            
        if self.oid and self.oid > self.coupon:
            self.qtaxoid = self.oid
            self.qtaxrval = self.ytmToPrice(self.oid)
        else:
            self.qtaxoid = self.coupon
            self.qtaxrval = 100.0
        
        q = ql.freqValue(self.frequency)
        self.amddemin = float(floor(self.nper / q)) * ptsyear
        try:
            self.qtaxyield = self.toYTM(self.qtaxrval - self.amddemin)
        except:
            self.qtaxyield = self.coupon
            
        return self.qtaxyield
    
    # TODO: allow after-tax yield to be passed in to get price.
    def calcAfterTax(self, bondprice=None, bondyield=None,
                     settle=None, capgains=.15, ordinc=.35,
                     ptsyear=0.25):
        '''
        Calculate after-tax yield given price,
        sets qtax flag to True if price is outside deminimus
        '''
        
        # Check bond's attributes if arguments not passed.
        errstr = "calcAfterTax(): price=%s bondyield=%s exactly one must have a value"
        price = bondprice
        if not (bondyield or price):
            bondyield = getattr(self, "bondyield", None)
            price = getattr(self, "price", None)
            assert (not price or not bondyield), errstr % (price, bondyield)
        else:
            if bondyield:
                price = self.calc(bondyield=bondyield)
        self.qtax(settle, ptsyear)
        
        if price <= self.qtaxrval:
            amd = max(self.qtaxrval - price, 0)
            taxRate = capgains if amd < self.amddemin else ordinc
            rval = 100 - amd * taxRate
            aty = self.toYTM(price, redemption=rval)
            self.qtaxflag = True
        else:
            aty = self.toYield(price)
            self.qtaxflag = False
            
        return aty

    def solveRatio(self, termstructure, price, vol=1e-7, 
                         baseSpread = 0.0,
                         spreadType = "S",
                         model=ql.BlackKarasinski):
        'shortcut for solveSpread, solveRatio=True, defaults to zero-spread ratio'
        return self.solveSpread(termstructure, price, vol, 
                                baseSpread, 1.0, True,
                                spreadType,
                                model)
    
    def basisSwapSpread(self, ratioTermstructure, price, vol=1e-7,
                              baseSpread=0.0,
                              spreadType = "S",
                              model=ql.BlackKarasinski):
        '''Returns asset swap spread relative to given ratio basis curve.
        
        '''
        msg = "Termstructure in basisSwapSpread must be RatioCurve"
        assert hasattr(ratioTermstructure, "maturityRatio"), msg
        
        termstructure = ratioTermstructure.disc_termstr        
        solveRatio = False
        baseRatio = ratioTermstructure.maturityRatio(self.maturity)

        return self.solveSpread(termstructure, price, vol, 
                                baseSpread, 
                                baseRatio, 
                                solveRatio,
                                spreadType,
                                model)        
                                  
if __name__ == "__main__":
    
    testcases = {'1': 
                 {'settle': (17, 11, 2010),
                  'coupon': .05,
                  'maturity': (1, 10, 2022),
                  'price2yield': (110.604, .03876),
                  'yield2price': (.03015, 119.683),
                  'qtax': .05315
                  }
                 }
                 