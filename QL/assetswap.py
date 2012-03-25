'''
Asset Swap class

Support option adjusted calculations

'''
import bgpy.__QuantLib as ql

from bgpy.QL.bgdate import toDate
from bgpy.QL.bonds import SimpleBond
from bgpy.dpatterns import Struct
from bgpy.math import Secant, SolverExceptions
from bgpy.QL.termstructure import SpreadedCurve
from bgpy.QL.irswaps import USDLiborSwap, USDLiborSwaption, BasisSwap

from math import floor, fmod

class BondValues(Struct):
    alist = ['bondyield', 'price',
              'oasYield', 'callvalue', 'oasPrice', 
              'spread', 'ratio', 'gearedSpread',
              'vol', 'spreadType', 'model', 'dv01', 'swapdv01', 'hedgeratio']
              
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
        
        Does not work for zero coupon callable bonds
        Does not work for non par calls if ratio != 1.0
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
                        
            if callprice > 100.0:
                callCpnRate = SimpleBond(self.assetSwapCoupon, 
                                   self.maturity, 
                                   settledate=firstcall).toYTM(callprice)
            else:
                callCpnRate = self.assetSwapCoupon
            
            # assuming 30days call notice as a minimum
            if ql.Thirty360().dayCount(firstcall, self.maturity) >= 30:
                self.swaption = USDLiborSwaption(termstructure, 
                                                 firstcall, 
                                                 self.maturity, 
                                                 callCpnRate, 
                                                 PayFlag=0, 
                                                 spread=spread_,
                                                 bermudan=True,
                                                 notionalAmount = 100.0)
        
        return (self.baseswap, self.swaption)
        
    def oasValue(self, termstructure, spread_, ratio_=1.0, vol=1e-7, 
                       model=ql.BlackKarasinski, solver=False):
        '''
        OAS given spread
        
        '''
        
        if (not solver) or not getattr(self, "oasCurve", None):
            self.oasCurve = SpreadedCurve(termstructure, type="Z")
        
        self.update(self.oasCurve, 0.0, ratio_)
        
        self.oasCurve.spread = spread_
        
        self.basevalue = self.baseswap.value(self.oasCurve)
        prm = self.basevalue * ratio_
        
        if self.swaption:
            self.callvalue = self.swaption.value(vol, self.oasCurve, 
                                                 model=model) * ratio_
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
        Assumes termstructure object is derived from TermStructureModel class,
        or QuantLib YieldTermStructureHandle.
        
        '''
        self.update(termstructure, spread_, ratio_)
        
        self.basevalue = self.baseswap.value(termstructure) 
        prm = self.basevalue * ratio_
        
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
                          model=ql.BlackKarasinski,
                          calc_risk = True):
        '''
        Calculate asset swap spread or ratio given price.
        
        spreadType: 
            "S" for asset swap
            "O" for oas 
        
        returns BondValues Object (repr = '<price, yield>')
        
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
            valueFunc = lambda x_: spreadFunc(termstructure, baseSpread, 
                                              x_, vol,
                                              model=model,
                                              solver=True)
            x_ = 1.0
            x1 = bondYTM / self.fairSwapRate(termstructure)
        
        # Objective function is well-behaved, so secant search is sufficient.
        value_ = Secant(x_, x1, valueFunc, objValue)
        
        if solveRatio:
            ratio, spread = value_, baseSpread
        else:
            ratio, spread = baseRatio, baseSpread + value_
        
        retval = self.value(termstructure, spread, ratio, vol, spreadType, 
                            model, calc_risk)
                            
        self.baseswap = None
        self.swaption = None
        self.oasCurve = None
        return retval
        
    def solveImpliedVol(self, termstructure, price,
                              spread = 0.0,
                              ratio = 1.0,
                              spreadType = "S",
                              model=ql.BlackKarasinski,
                              calc_risk = True):
        '''
        Calculate implied vol on asset swap.
        
        Enforces bound of 0.0% to 1000% on vol
        '''
        spreadFunc = self.spreadType.get(spreadType, self.aswValue)
            
        bondyield = self.toYield(price)
         
        # set objective value, value function and initial values
        objValue = price
        valueFunc = lambda x_: spreadFunc(termstructure, spread, ratio, 
                                          x_, model=model, solver=True)
        
        # price can't be greater that 'zero' vol price or less than MAXVOL price
        # let's assume vol <= 1000%
        if price > valueFunc(1e-7) or not self.calllist: 
            vol_ = 1e-7
        elif price < valueFunc(10.0):
            print("max vol price")
            vol_ = 10.
        else:    
            x_ = 0.09
            x1 = 0.10
            vol_ = Secant(x_, x1, valueFunc, objValue)
        
        retval = self.value(termstructure, spread, ratio, vol_, spreadType, model,
                            calc_risk)
                            
        self.baseswap = None
        self.swaption = None
        self.oasCurve = None
        
        return retval
        
    def base_dv01(self, termstructure, spread, ratio, vol, 
                        model=ql.BlackKarasinski, 
                        valueFunc=None):
        '''Z DV01
        Price sensitivity to bp change in discount rates across the term structure.
        '''
        if not valueFunc:
            valueFunc = self.oasValue
            
        crv_up = termstructure.shift_up
        crv_dn = termstructure.shift_dn
        
        p0 = valueFunc(crv_up, spread, ratio, vol, model)
        p1 = valueFunc(crv_dn, spread, ratio, vol, model)
        
        return (p0-p1) / 2.0
    
    def hedge_risk(self, termstructure, spread, ratio, vol, 
                          model=ql.BlackKarasinski, 
                          valueFunc=None):
        
        if not valueFunc:
            valueFunc = self.oasValue
            
        crv_up = termstructure.shift_up
        crv_dn = termstructure.shift_dn
        
        p0 = valueFunc(crv_up, spread, ratio, vol, model)
        s0 = self.basevalue
        p1 = valueFunc(crv_dn, spread, ratio, vol, model)
        s1 = self.basevalue
        
        dv01 = (p0-p1) / 2.0   
        swapdv01 = (s0 - s1) / 2.0
        hedgeratio = dv01 / -swapdv01

        return (hedgeratio, dv01, swapdv01) 
        
    def spread_dv01(self, termstructure, spread, ratio, vol, 
                    model, valueFunc=None):
        if not valueFunc:
            valueFunc = self.aswValue
            
        p0 = valueFunc(termstructure, spread-0.0001, ratio, vol, model)
        p1 = valueFunc(termstructure, spread+0.0001, ratio, vol, model)
        
        return (p0-p1) / 2.0
        
    def dvRatio(self, termstructure, spread, ratio, vol, 
                    model, valueFunc=None):
        if not valueFunc:
            valueFunc = self.aswValue
            
        p0 = valueFunc(termstructure, spread, ratio-.01, vol, model)
        p1 = valueFunc(termstructure, spread, ratio+.01, vol, model)
        
        return (p0-p1) / 2.0

    def vega(self, termstructure, spread, ratio, vol, 
                    model, valueFunc=None):
        if not valueFunc:
            valueFunc = self.aswValue
            
        p0 = valueFunc(termstructure, spread, ratio, vol-.01, model)
        p1 = valueFunc(termstructure, spread, ratio, vol+.01, model)
        
        return (p0-p1) / 2.0

        
    def value(self, termstructure,
                    spread = 0.0,
                    ratio = 1.0,
                    vol = 1e-12,
                    spreadType="S",
                    model = ql.BlackKarasinski,
                    calc_risk=False):
        '''
        Calculates termstructure / asset swap values -- sets "values" property.
        '''
        valueFunc = self.spreadType.get(spreadType, self.aswValue)

        value_ = valueFunc(termstructure, spread, ratio, vol, 
                           model=model, solver=True)

        risk = self.hedge_risk(termstructure, spread, ratio, vol, 
                                model, valueFunc) if calc_risk else None
        hedge, dv01, swapdv01 = risk if risk else (None, None, None)
                
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
        dvalues['hedgeratio'] = hedge
        dvalues['swapdv01'] = swapdv01
        
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
                   model = ql.BlackKarasinski,
                   calc_risk=True):
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
                                                                model,
                                                                calc_risk)
            else:
                valueFunc = lambda t, p, v, s, r: self.solveImpliedVol(t, 
                                                                    p, s, r,
                                                                    spreadType,
                                                                    model,
                                                                    calc_risk)
                
        else:   
            valueFunc = lambda t, p, v, s, r: self.value(t, s, r, v,
                                                   spreadType, model,
                                                   calc_risk)
        
        spread = spread if spread else 0.0
        ratio = ratio if ratio else 1.0
        vol = vol if vol else 1e-12
        
        retval = valueFunc(termstructure, bondprice, vol, spread, ratio)
                
        return retval
