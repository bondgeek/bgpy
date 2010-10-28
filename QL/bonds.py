'''
Bond math routines, 
Uses QuantLib date handling, everything takes Resolver's f%^&*(#@g Microsoft Dates

Created on Jan 24, 2010
@author: Bart Mosley
'''

import bgpy.QL as ql
from bgpy.math.solvers import Secant, SolverExceptions
from bgpy.QL import bgDate
from bgpy.dpatterns import Struct

import bgpy.QL.termstructure as ts
from bgpy.QL.irswaps import USDLiborSwap, USDLiborSwaption, BasisSwap

from math import floor, fmod

#globals
calendar = ql.TARGET()

    
#class definitions
class BondExceptions(Exception):
    MAX_PY_ITERATIONS = 24
    MAX_PY_ITERATIONS_MSG = "Max Iterations--%d--reached in price/yield calc" % MAX_PY_ITERATIONS
    MIN_YLD = 1e-7
    NEG_YIELD_MSG = "Negative yield in ytmToPrice" 

class BondValues(Struct):
    alist = ['bondyield', 'price',
              'oasYield', 'callvalue', 'oasPrice', 
              'spread', 'ratio', 'vol', 'spreadType', 'model']
              
    def __init__(self, valueDict):
        val_ = {}
        for k in self.alist:
            val_[k] = valueDict.get(k, None)
        dict.__init__(self, val_)
    
    def __repr__(self):
        return "<%3.3f, %2.3f>" % (self.get("price", 0.0), 
                                   100.0*self.get("bondyield", 0.0))
        
class BondType(object):
    '''
    Do not use except as base class
    '''
    settlementdays = 3
    daycount = ql.Thirty360()
    paytenor = ql.Semiannual
    frequency = ql.Semiannual
    payconvention = ql.Unadjusted
    termconvention = ql.Unadjusted
    calendar = ql.USGovernmentBond
    face = 100.0
    
    def bondtype(self):
        attrs_ = ('settlementdays', 'daycount', 'frequency','paytenor',
                  'payconvention', 'termconvention', 'face', 'calendar')
                    
        return dict(zip(attrs_, [getattr(self, a) for a in attrs_]))
        
class USTsyBond(BondType):
    settlementdays = 2
    daycount = ql.ActualActualBond
    paytenor = ql.Semiannual
    frequency = ql.Semiannual
    payconvention = ql.ModifiedFollowing
    termconvention = ql.Unadjusted
    face = 100.0
    
    def bondtype(self):
        d = BondType().bondtype()
        for k in d:
            d[k] = getattr(self,k)
        return d

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

class Call(object):
    def __init__(self, firstcall=None, callprice=None, parcall=None, 
                 frequency=ql.Semiannual, redvalue=100., ObjectId=None):
        '''
        Create a call feature.
        '''
        # make sure we have a QuantLib compliant set of dates
        firstcall, parcall = map(bgDate, [firstcall, parcall])
        self.firstcall = firstcall 
        self.callprice = callprice
        self.parcall = parcall
        self.frequency = frequency
        
    def __str__(self):
        return "@".join((str(self.firstcall), str(self.callprice)))

    def __repr__(self):
        return self.__str__()

class SimpleBond(object):
    """
    Bond Object: 
    coupon, maturity, issuedate, oid, callfeature, bondtype, redvalue
    """
    def __init__(self, coupon, maturity, 
                 callfeature=None, oid=None, issuedate=None, 
                 bondtype=None, redvalue=100.,
                 settledate=None):
                 
        maturity, issuedate, settledate = map(bgDate, [maturity, issuedate, 
                                                       settledate])
        if bondtype is None:
            bondtype = BondType()

        self.bondtype = bondtype
        bt = bondtype.bondtype()
        for attr in bt:
            setattr(self, attr, bt[attr])
                    
        self.coupon = coupon
        self.maturity = maturity
        self.issuedate = issuedate 
        self.redvalue = redvalue
        self.oid = oid
        self.callfeature = callfeature
        
        if not self.callfeature:  
            self.calllist = []
        else: 
            self.calllist = self.CallList()

        self.setSettlement(settledate)
        
        # initialize swap structures for asset swap analysis
        self.baseswap = None
        self.swaption = None
        self.assetSwapCoupon = self.coupon    
        self.assetSwapRatio = 1.0
        self.spreadType = {"S": self.aswValue,
                           "O": self.oasValue}

    def __str__(self):
        return "% ".join((str(self.coupon*100.0), str(self.maturity)))
    
    def setSettlement(self, settledate=None):
        '''change settlement'''
        settledate = bgDate(settledate)
        if not settledate.serialNumber():
            evalDate = ql.Settings.instance().getEvaluationDate() 
            self.settle_ = self.calendar.advance(evalDate, self.settlementdays, 
                                                           ql.Days)
        else:
            self.settle_ = settledate
            
        #TODO: This maybe can be more robust for non-standard frequencies
        #      It works for annual, quarterly & semi-annual.
        freq = float(ql.freqValue(self.frequency))
        self.term = freq * self.daycount.yearFraction(self.settle_, 
                                                      self.maturity)
        self.nper = floor(self.term)
        self.frac = self.term - self.nper

        return self
   
    def getSettlement(self):
        return self.settle_
   
    settlementDate = property(getSettlement, setSettlement)
    
    def CallList(self):
        calllist = []
        if self.callfeature:
            dtp = 0.0
            call = self.callfeature
            if ((call.parcall > call.firstcall) and 
                (call.callprice > self.face)):
                callyears = self.daycount.yearFraction(call.firstcall, call.parcall)
                dtp = (call.callprice-self.face)/(ql.freqValue(call.frequency)*callyears)
            
            price = call.callprice
            calldate = call.firstcall
            
            while ql.ActualActual().dayCount(calldate, self.maturity) > 0:
                cbond = SimpleBond(self.coupon, calldate, 
                                   issuedate = self.issuedate, 
                                   oid=self.oid,
                                   bondtype=self.bondtype, 
                                   redvalue=price)
                calllist.append((calldate,price, cbond))
                freq = ql.Period(call.frequency)
                calldate = calendar.advance(calldate, freq, ql.Unadjusted)
                
                if calldate >= call.parcall:
                    price = self.face if hasattr(self, 'face') else 100.0         
                else:
                    price = price - dtp
                
        return calllist
       
    def maxPrice(self):
        '''determines the price if yieldtoworst = 0 (or close to it)'''
        self.maxPrice = self.toPrice(0.000001)
        return self.maxPrice
    
    def calc(self, bondyield=None, bondprice=None, dict_out=False):
        '''
        Calculates price/yield based on which value is passed.
        If neither is passed, uses which SimpleBond attribute is set.
        Error condition if neither price nor bondyield is passed.
        
        Optional argument:  dict_out=True returns {'bondyield':  yld, 
                                                   'price': prc,
                                                   'pricedTo': toDate
                                                   'toPrice': toPrice}
        '''
        errstr = "calc(): bondyield=%s bondprice=%s exactly one must have a value"  
        # Check bond's attributes if arguments not passed.
        price = bondprice # needed to change argument for Resolver
        if not (bondyield or price):
            bondyield = getattr(self, "bondyield", None)
            price = getattr(self, "price", None)
        
            assert (not price or not bondyield), errstr % (price, bondyield)
        
        def to_other(level, ytmfunc, cmplevel):
            '''
            calculate yield to worst, if callable, given price, 
            otherwise returns ytm or vice versa
            '''
            val = getattr(self, ytmfunc)(level)
            todate = self.maturity
            toprice = self.redvalue

            if self.calllist:
                earliestcall= calendar.advance(self.settle_, ql.Period(self.paytenor))
                
                for call in self.calllist:
                    calldt, callpx, cbond = call
                    
                    if all([(self.daycount.dayCount(earliestcall, calldt) >= 0),
                            (callpx <= level or not cmplevel), 
                            (calldt < todate or callpx < toprice)]):
                        
                        cbond.settlemenDate = self.settle_
                        newval = getattr(cbond,ytmfunc)(level)
                        
                        if newval <= val:
                            todate = calldt
                            toprice = callpx
                            val = newval
                            
            return (val, todate, toprice)
                       
        if not bondyield:  
            #toYield
            level = price
            ytmfunc = 'toYTM'
            cmplevel = True
            calcattr = 'bondyield'
        else:
            #toPrice
            level = bondyield
            ytmfunc = 'ytmToPrice'
            cmplevel = False
            calcattr = 'price'
        
        result_value = to_other(level, ytmfunc, cmplevel)
        if dict_out:
            val, todate, toprice = result_value
            result = {'bondyield': bondyield, 
                      'price': price, 
                      'toDate': todate,
                      'toPrice': toprice}
            result[calcattr] = val
        else:
            result = result_value[0]
            
        return result
              
    def ai(self):
        if (self.frac==0):
                return 0
        else:
                return (1.-self.frac)*self.coupon/ql.freqValue(self.frequency)
            
    def ytmToPrice(self, yld):
        """calculates price given yield"""    
        if(yld < 0.0):
            raise BondExceptions, BondExceptions.NEG_YIELD_MSG
        
        if(yld==self.coupon):
            price = 100.0
        else:
            freq_ = ql.freqValue(self.frequency)
            cpn = self.coupon/freq_
            y = yld/freq_
            u = cpn/y
            z = 1. / (1.+y)**self.nper
            t = 1. / (1.+y)**self.frac
            if(self.frac == 0.0):
                nxtcpn = 0.0
            else:
                nxtcpn = cpn
            prc = (t*(u*(1.0-z) + z*self.redvalue/100.0 + nxtcpn) - self.ai())*100.0
            price = round(prc,6)

        return price
    
    def toYield(self, _price):
        return self.calc(bondprice = _price)
        
    def toPrice(self, _yield):
        return self.calc(_yield)
       
    def toYTM(self, price):
        '''
        Calculate yield to maturity from price.
        Secant search is sufficient as price is generally well-behaved,
        and coupon, current yield are natural initial values.
        '''
        if(round(price,6)==100.0):
            yld=self.coupon
        else:
            if(self.coupon > 0.0):
                y0 = self.coupon
                yg = 100.*self.coupon / price
            else:
                y0 = getattr(self, "oid", .05)
                yg = 100.*y0 / price if self.oid else .0501

            try:
                yld = Secant(y0, yg, self.ytmToPrice, price)
            except:
                print "Solver error in toYTM"
                raise
                
        return yld
        
    def fairSwapRate(self, termstructure):
        '''
        calculate the fair swap rate matching structure of non-call portion of bond
        '''
        return termstructure.bondpar(self.maturity)

    def assetSwap(self, termstructure, spread_=0.0, ratio=1.0):
        '''
        Creates the swaps used to model bond as an asset swap.
        baseswap = underlying noncallable bond asset swap.
        swaption = swaption replicating call feature, if any.
        '''     
        assetSwapSettle = min(self.settle_, termstructure.referenceDate())
        self.assetSwapCoupon = self.coupon / ratio   
        self.assetSwapRatio = ratio
        self.baseswap = USDLiborSwap(termstructure, 
                            assetSwapSettle, 
                            self.maturity, self.assetSwapCoupon, 
                            PayFlag=1, spread=spread_,
                            notionalAmount = 100.0)
        
        self.swaption = None
        if self.calllist:
            firstcall, callprice, callbond = self.calllist[0]
            self.swaption = USDLiborSwaption(termstructure, 
                                    firstcall, 
                                    self.maturity, self.assetSwapCoupon, 
                                    PayFlag=0, spread=spread_,
                                    notionalAmount = 100.0)
        
        return (self.baseswap, self.swaption)
        
    def oasValue(self, termstructure, spread, ratio=1.0, vol=1e-7, 
                       model=ql.BlackKarasinski):
        '''
        OAS given spread
        '''
        self.oasCurve = ts.SpreadedCurve(termstructure, type="Z")
        
        if not self.baseswap or (abs(ratio - self.assetSwapRatio) > 1e-8):
            self.assetSwap(self.oasCurve, 0.0, ratio)
        
        self.oasCurve.spread = spread
        prm = self.baseswap.value(self.oasCurve)
        if self.swaption:
            self.callvalue = self.swaption.value(vol, self.oasCurve, model=model)
            prm += self.callvalue
        
        return 100.-prm 

    def aswValue(self, termstructure, spread_, ratio_ = 1.0,
                         vol=1e-7, model=ql.BlackKarasinski):
        '''
        Calculate asset swap premium, given spread and termstructure.
        Assumes termstructure object is derivative of TermStructureModel class,
        or QuantLib YieldTermStructureHandle.
        '''
        self.assetSwap(termstructure, spread_, ratio_)
        
        prm = self.baseswap.value(termstructure)
        if self.swaption:
            self.callvalue = self.swaption.value(vol, termstructure, model=model)
            prm += self.callvalue

        return 100.-prm 
                
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
                                              baseRatio, vol, model=model)
            x_ = 0.0
            x1 = bondYTM - self.fairSwapRate(termstructure)
                
        else:
            valueFunc = lambda x_: spreadFunc(termstructure, baseSpread, x_, vol,
                                              model=model)
            x_ = 1.0
            x1 = bondYTM / self.fairSwapRate(termstructure)
        
        value_ = Secant(x_, x1, valueFunc, objValue)
        
        if solveRatio:
            ratio, spread = value_, baseSpread
        else:
            ratio, spread = baseRatio, baseSpread + value_
            
        return self.value(termstructure, spread, ratio, vol, spreadType, model)

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
                                          x_, model=model)
        
        # price can't be greater that 'zero' vol price or less than MAXVOL price
        # let's assume vol <= 1000%
        if price > (100.0 - valueFunc(1e-7)):
            return 1e-7
        if price < (100.0 - valueFunc(10.0)):
            return 10.0
            
        x_ = 0.09
        x1 = 0.10
        vol_ = Secant(x_, x1, valueFunc, objValue)
        
        return self.value(termstructure, spread, ratio, vol_, spreadType, model)

    def value(self, termstructure,
                    spread = 0.0,
                    ratio = 1.0,
                    vol = 1e-12,
                    spreadType="S",
                    model = ql.BlackKarasinski):
        '''
        Calculates termstructure / asset swap values -- sets "values" property.
        '''
        valueFunc = self.spreadType.get(spreadType, self.aswValue)
        
        value_ = valueFunc(termstructure, spread, ratio, vol, model=model) 
        
        dvalues = self.calc(bondprice=value_, dict_out=True)
        
        dvalues['callvalue'] = getattr(self, "callvalue", 0.0)
        dvalues['oasPrice'] = value_ + dvalues['callvalue']
        dvalues['oasYield'] = self.toYTM(dvalues['oasPrice'])
        dvalues['spreadType'] = spreadType
        dvalues['spread'] = spread
        dvalues['ratio'] = ratio
        dvalues['vol'] = vol
        dvalues['model'] = model
        
        return BondValues(dvalues)
    
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
                valueFunc = lambda p, v, s, r: self.solveSpread(termstructure,
                                                                p, v, s, r,
                                                                solveRatio,
                                                                spreadType,
                                                                model)
            else:
                valueFunc = lambda p, v, s, r: self.solveImpliedVol(termstructure, 
                                                                    p, s, r,
                                                                    spreadType,
                                                                    model)
                
        else:   
            valueFunc = lambda p, v, s, r: self.value(termstructure, s, r, v,
                                                   spreadType, model)
        
        spread = spread if spread else 0.0
        ratio = ratio if ratio else 1.0
        vol = vol if vol else 1e-12
        
        return valueFunc(bondprice, vol, spread, ratio)
                
class MuniBond(MuniBondType, SimpleBond):
    '''
    Muni Bond Object, inherits from SimpleBond
    Override asset swap methods to allow gross up coupon and apply leverage. (instrument based approach).
    
    '''
    def __init__(self, coupon, maturity, callfeature=None,
                        oid=None,  issuedate=None,
                       redvalue=100.0):
        SimpleBond.__init__(self, coupon, maturity, callfeature, 
                                  oid, issuedate, MuniBondType(),
                                  redvalue)
        
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
            
        self.amddemin = float(floor(self.nper / self.frequency)) * ptsyear
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
    
    
