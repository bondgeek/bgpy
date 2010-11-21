'''
Asset Swap class

Support option adjusted calculations

'''
import bgpy.__QuantLib as ql

from bgpy.QL import toDate
from bgpy.dpatterns import Struct
from bgpy.math.solvers import Secant, SolverExceptions
from bgpy.QL.termstructure import SpreadedCurve
from bgpy.QL.irswaps import USDLiborSwap, USDLiborSwaption, BasisSwap

from math import floor, fmod

class BondValues(Struct):
    alist = ['bondyield', 'price',
              'oasYield', 'callvalue', 'oasPrice', 
              'spread', 'ratio', 'gearedSpread',
              'vol', 'spreadType', 'model', 'dv01']
              
    def __init__(self, valueDict):
        val_ = {}
        for k in self.alist:
            val_[k] = valueDict.get(k, None)
        dict.__init__(self, val_)
    
    def __repr__(self):
        return "<%3.3f, %2.3f>" % (self.get("price", 0.0), 
                                   100.0*self.get("bondyield", 0.0))
        
class AssetSwap(object):
    
    def __init__(self, bond, termstructure=None, spread=0.0, ratio=1.0):
        
        self.calllist = bond.calllist
        self.coupon = bond.coupon
        self.maturity = bond.maturity
        self.calc = bond.calc
        self.toYTM = bond.toYTM
        self.toYield = bond.toYield
        
        # initialize swap structures for asset swap analysis
        self.baseswap = None
        self.swaption = None
        self.assetSwapCoupon = self.coupon    
        self.assetSwapRatio = 1.0
        self.spreadType = {"S": self.aswValue,
                           "O": self.oasValue}
        
        if termstructure:
            self.update(termstructure, spread, ratio)
    
    def __str__(self):
        return "<AssetSwap>"
        
    def fairSwapRate(self, termstructure):
        '''
        calculate the fair swap rate matching maturity of the bond
        '''
        return termstructure.bondpar(self.maturity)

    def update(self, termstructure, spread_=0.0, ratio=1.0):
        '''
        Creates the swaps used to model bond as an asset swap.
        baseswap = underlying noncallable bond asset swap.
        swaption = swaption replicating call feature, if any.
        '''     
        assetSwapSettle = termstructure.referenceDate()
        self.assetSwapCoupon = self.coupon / ratio   
        self.assetSwapRatio = ratio
        self.baseswap = USDLiborSwap(termstructure, 
                                     assetSwapSettle, 
                                     self.maturity, 
                                     self.assetSwapCoupon, 
                                     PayFlag=1, 
                                     spread=spread_,
                                     notionalAmount = 100.0)
        
        self.swaption = None
        if self.calllist:
            firstcall, callprice, callbond = self.calllist[0]
            self.swaption = USDLiborSwaption(termstructure, 
                                             firstcall, 
                                             self.maturity, 
                                             self.assetSwapCoupon, 
                                             PayFlag=0, 
                                             spread=spread_,
                                             bermudan=True,
                                             notionalAmount = 100.0)
        
        return (self.baseswap, self.swaption)
        
    def oasValue(self, termstructure, spread, ratio=1.0, vol=1e-7, 
                       model=ql.BlackKarasinski, solver=False):
        '''
        OAS given spread
        '''
        if (not solver) or not (self.oasCurve and self.baseswap):
            self.oasCurve = SpreadedCurve(termstructure, type="Z")
            self.update(self.oasCurve, 0.0, ratio)
        
        self.oasCurve.spread = spread
        prm = self.baseswap.value(self.oasCurve)
        if self.swaption:
            self.callvalue = self.swaption.value(vol, self.oasCurve, model=model)
            prm += self.callvalue
        
        if not solver:
            self.baseswap = None
            self.swaption = None
            self.oasCurve = None
        
        return 100.-prm 

    def aswValue(self, termstructure, spread_, ratio_ = 1.0,
                       vol=1e-7, model=ql.BlackKarasinski, solver=False):
        '''
        Calculate asset swap premium, given spread and termstructure.
        Assumes termstructure object is derivative of TermStructureModel class,
        or QuantLib YieldTermStructureHandle.
        '''
        self.update(termstructure, spread_, ratio_)
        
        prm = self.baseswap.value(termstructure) * ratio_
        if self.swaption:
            self.callvalue = self.swaption.value(vol, 
                                                 termstructure, 
                                                 model=model) * ratio_
            prm += self.callvalue

        if not solver:
            self.baseswap = None
            self.swaption = None
            self.oasCurve = None
            
        return 100. - prm 
                
    def solveSpread(self, termstructure, price, vol=1e-7, 
                          baseSpread = 0.0,
                          baseRatio = 1.0,
                          solveRatio = False,
                          spreadType = "S",
                          model=ql.BlackKarasinski):
        '''
        Calculate asset swap spread or ratio given price.
        
        spreadType: 
            "S" for asset swap
            "O" for oas 
        
        Objective function is well-behaved, so secant search is sufficient.
        
        '''
        spreadFunc = self.spreadType.get(spreadType, self.aswValue)
        bondYTM = self.toYTM(price)
         
        # set objective value, value function and initial values
        objValue = price
        
        if not solveRatio:
            valueFunc = lambda x_: spreadFunc(termstructure, baseSpread+x_, 
                                              baseRatio, vol, model=model,
                                              solver=True)
            x_ = 0.0
            x1 = bondYTM - self.fairSwapRate(termstructure)
                
        else:
            valueFunc = lambda x_: spreadFunc(termstructure, baseSpread, x_, vol,
                                              model=model,
                                              solver=True)
            x_ = 1.0
            x1 = bondYTM / self.fairSwapRate(termstructure)
        
        value_ = Secant(x_, x1, valueFunc, objValue)
        
        if solveRatio:
            ratio, spread = value_, baseSpread
        else:
            ratio, spread = baseRatio, baseSpread + value_
        
        retval = self.value(termstructure, spread, ratio, vol, spreadType, model)
        self.baseswap = None
        self.swaption = None
        self.oasCurve = None
        return retval
        
    def solveImpliedVol(self, termstructure, price,
                              spread = 0.0,
                              ratio = 1.0,
                              spreadType = "S",
                              model=ql.BlackKarasinski):
        '''
        Calculate implied vol on asset swap.
        
        Enforces bound of 0.0% to 1000% on vol
        '''
        spreadFunc = self.spreadType.get(spreadType, self.aswValue)
        
        if not self.calllist:
            # bond is not callable
            return 1e-7
            
        bondyield = self.toYield(price)
         
        # set objective value, value function and initial values
        objValue = -(price - 100.0) 
        
        valueFunc = lambda x_: spreadFunc(termstructure, spread, ratio, 
                                          x_, model=model,
                                              solver=True)
        
        # price can't be greater that 'zero' vol price or less than MAXVOL price
        # let's assume vol <= 1000%
        if price > (100.0 - valueFunc(1e-7)):
            return 1e-7
        if price < (100.0 - valueFunc(10.0)):
            return 10.0
            
        x_ = 0.09
        x1 = 0.10
        vol_ = Secant(x_, x1, valueFunc, objValue)
        
        retval = self.value(termstructure, spread, ratio, vol_, spreadType, model)
        self.baseswap = None
        self.swaption = None
        self.oasCurve = None
        return retval
        
    def sensitivity(self, termstructure, spread, ratio, vol, 
                    model, valueFunc):
        crv_up = termstructure.shift_up
        crv_dn = termstructure.shift_dn
        
        p0 = valueFunc(crv_up, spread, ratio, vol, model)
        p1 = valueFunc(crv_dn, spread, ratio, vol, model)
        
        return (p0-p1) / 2.0
        
    def value(self, termstructure,
                    spread = 0.0,
                    ratio = 1.0,
                    vol = 1e-12,
                    spreadType="S",
                    model = ql.BlackKarasinski,
                    calcDV01=True):
        '''
        Calculates termstructure / asset swap values -- sets "values" property.
        '''
        valueFunc = self.spreadType.get(spreadType, self.aswValue)
        
        value_ = valueFunc(termstructure, spread, ratio, vol, model=model) 
        
        dv01 = self.sensitivity(termstructure, spread, ratio, vol, 
                                model, valueFunc) if calcDV01 else None
                                      
        dvalues = self.calc(bondprice=value_, dict_out=True)
        
        dvalues['callvalue'] = getattr(self, "callvalue", 0.0)
        dvalues['oasPrice'] = value_ + dvalues['callvalue']
        dvalues['oasYield'] = self.toYTM(dvalues['oasPrice'])
        dvalues['spreadType'] = spreadType
        dvalues['spread'] = spread
        dvalues['ratio'] = ratio
        dvalues['gearedSpread'] = spread * ratio
        dvalues['vol'] = vol
        dvalues['model'] = model
        dvalues['dv01'] = dv01
        
        retval = BondValues(dvalues)
        self.baseswap = None
        self.swaption = None
        self.oasCurve = None
        
        return retval

    def oas1(self, termstructure, 
                   bondprice=None, bondyield=None,
                   spread=None, ratio=None,
                   vol = 1e-12,
                   spreadType="S",
                   model = ql.BlackKarasinski):
        '''
        Requires two of three inputs:
            1) price or yield
            2) spread or ratio
            3) vol
        '''
        if bondprice or bondyield:
            py = self.calc(bondyield, bondprice, True)
            bondprice = py['price']
            bondyield = py['bondyield']
            
            if vol is not None:
                solveRatio = True if not ratio and spread is not None else False
                valueFunc = lambda t, p, v, s, r: self.solveSpread(t,
                                                                p, v, s, r,
                                                                solveRatio,
                                                                spreadType,
                                                                model)
            else:
                valueFunc = lambda t, p, v, s, r: self.solveImpliedVol(t, 
                                                                    p, s, r,
                                                                    spreadType,
                                                                    model)
                
        else:   
            valueFunc = lambda t, p, v, s, r: self.value(t, s, r, v,
                                                   spreadType, model)
        
        spread = spread if spread else 0.0
        ratio = ratio if ratio else 1.0
        vol = vol if vol else 1e-12
        
        retval = valueFunc(termstructure, bondprice, vol, spread, ratio)
                
        return retval
