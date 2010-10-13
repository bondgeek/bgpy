'''
Bond math routines, 
Uses QuantLib date handling, everything takes Resolver's f%^&*(#@g Microsoft Dates

Created on Jan 24, 2010
@author: Bart Mosley
'''

import bgpy.QL as ql
from bgpy.QL import BGDate

import bgpy.QL.termstructure as ts
from bgpy.QL.irswaps import USDLiborSwap, USDLiborSwaption, BasisSwap

from math import floor, fmod

#globals
calendar = ql.TARGET()

#class definitions
class BondExceptions(Exception):
    MAX_PY_ITERATIONS = 24
    MAX_PY_ITERATIONS_MSG = "Max Iterations--%d--reached in price/yield calc" % MAX_PY_ITERATIONS
    MIN_YLD = 0.00000001
    NEG_YIELD_MSG = "Negative yield in ytmToPrice" 

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
    calendar = ql.UnitedStates(ql.UnitedStates.Market.GovernmentBond)
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

class MuniBond(BondType):
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

class BondCallFeature(object):
    def __init__(self, firstcall=None, callprice=None, parcall=None, 
                 frequency=ql.Semiannual, redvalue=100., ObjectId=None):
        '''
        Create a call feature.
        '''
        # make sure we have a QuantLib compliant set of dates
        # will return ql.Date() if None.
        firstcall, parcall = map(bgDate, [firstcall, parcall])
        self.firstcall = firstcall 
        self.callprice = callprice
        self.parcall = parcall
        self.frequency = frequency
        
    def __str__(self):
        return "@".join((str(self.firstcall), str(self.callprice)))

    def __repr__(self):
        return self.__str__()

class BGBond(object):
    """
    Bond Object: 
    coupon, maturity, issuedate, oid, callfeature, bondtype, redvalue
    """
    def __init__(self,coupon, maturity, issuedate=None, oid=None, 
                 callfeature=None, bondtype=None, redvalue=100.,
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
    
    def setSettlement(self, settledate=None):
        '''change settlement'''
        settledate = bgDate(settledate)
        if not settledate.serialNumber():
            evalDate = ql.Settings.instance().getEvaluationDate() 
            self.settle = self.calendar.advance(evalDate, self.settlementdays, 
                                                          ql.Days)
        else:
            self.settle = settledate
            
        #TODO: This maybe can be more robust for non-standard frequencies
        #      It works for annual, quarterly & semi-annual.
        #      It's inelegant to call value__ but I blame QuantLib
        freq = float(self.frequency.value__)
        self.term = freq * self.daycount.yearFraction(self.settle, 
                                                      self.maturity)
        self.nper = floor(self.term)
        self.frac = self.term - self.nper

        return self
        
    def getSettlement(self):
        return self.settle
        
    def CallList(self):
        calllist = []
        if self.callfeature:
            dtp = 0.0
            call = self.callfeature
            if ((call.parcall > call.firstcall) and 
                (call.callprice > self.face)):
                callyears = self.daycount.yearFraction(call.firstcall,
                                                       call.parcall)
                dtp = (call.callprice-self.face)/(call.frequency.value__*callyears)
            
            price = call.callprice
            calldate = call.firstcall
            
            while ql.ActualActual().dayCount(calldate, self.maturity) > 0:
                calllist.append((calldate,price))
                freq = ql.Period(call.frequency)
                calldate = calendar.advance(calldate, freq, ql.Unadjusted)
                
                if calldate >= call.parcall:
                    price = self.face if hasattr(self, 'face') else 100.0         
                else:
                    price = price - dtp
                
        return calllist

    @staticmethod
    def CallFromList(calllist):
        '''Turns call list into a QL Callability Schedule'''

        callsched = CallabilitySchedule()

        for calldate, price in calllist:
        
            callPx = CallabilityPrice(price, CallabilityPrice.Clean)
            callDt = Callability(callPx, Callability.Call, calldate)

            callsched.push_back(callDt)

        return callsched            
        
    def CallSchedule(self):
        '''Turns bond's call list into a QL Callability Schedule'''
        calllist = self.CallList()
        
        return self.CallFromList(calllist)

    def maxPrice(self):
        '''determines the price if yieldtoworst = 0 (or close to it)'''
        self.maxPrice = self.toPrice(0.000001)
        return self.maxPrice
    
    def calc(self, bondyield=None, price=None, dict_out=False):
        '''
        Calculates price/yield based on which value is passed.
        If neither is passed, uses which BGBond attribute is set.
        Error condition if neither price nor bondyield is passed.
        
        Optional argument:  dict_out=True returns {'bondyield':  yld, 
                                                   'price': prc,
                                                   'pricedTo': toDate
                                                   'toPrice': toPrice}
        '''
        errstr = "calc(): price=%s bondyield=%s exactly one must have a value"  
        # Check bond's attributes if arguments not passed.
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
                earliestcall= calendar.advance(self.settle, ql.Period(self.paytenor))
                
                for call in self.calllist:
                    calldt, callpx = call
                    
                    if all([(self.daycount.dayCount(earliestcall, calldt) >= 0),
                            (callpx <= level or not cmplevel), 
                            (calldt < todate or callpx < toprice)]):
                        
                        b = BGBond(self.coupon, calldt, 
                                   self.issuedate, 
                                   self.oid,
                                   bondtype=self.bondtype, 
                                   redvalue=callpx,
                                   settledate=self.settle)
                        
                        newval = getattr(b,ytmfunc)(level)
                        
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
                return (1.-self.frac)*self.coupon/self.frequency.value__
            
    def ytmToPrice(self, yld):
        """calculates price given yield"""    
        if(yld < 0.0):
            raise BondExceptions, BondExceptions.NEG_YIELD_MSG
        
        if(yld==self.coupon):
            price = 100.0
        else:
            #TODO:  QuantLib / C-# implimentation requires calling value__
            cpn = self.coupon/self.frequency.value__
            y = yld/self.frequency.value__
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
        return self.calc(price = _price)
        
    def toPrice(self, _yield):
        return self.calc(_yield)
       
    def toYTM(self, price):
        '''yield to maturity from price'''
        if(round(price,6)==100.0):
            yld=self.coupon
        else:
            if(self.coupon > 0.0):
                p0 = 100.0
                y0 = self.coupon
                yg = 100.*self.coupon / price
            else:
                y0 = .05
                p0 = self.ytmToPrice(y0)
                yg = .0501
            p1 = self.ytmToPrice(yg)
            pdiff = p1-price
            
            for n in range(BondExceptions.MAX_PY_ITERATIONS+1):
                try:
                    dYdP = (yg - y0) / (p1 - p0)
                    p0 = p1
                    y0 = yg
                    yg -= dYdP * pdiff
                    try:
                        p1 = self.ytmToPrice(yg)
                    except BondExceptions, e:
                        raise 
                        
                    pdiff = p1 - price
                    if abs(pdiff) <= .00000001:
                        break
                except ZeroDivisionError:
                    if abs(yg - y0) < 0.0000001:
                        break
                    else:
                        raise
                    
            if n == BondExceptions.MAX_PY_ITERATIONS:
                raise BondExceptions, BondExceptions.MAX_PY_ITERATIONS_MSG
            
            yld = yg 
        return yld
    
    def __str__(self):
        return "% ".join((str(self.coupon*100.0), str(self.maturity)))

    def __repr__(self):
        return self.__str__()
    
    def FixedRateBond(self, pricingEngine=None):
        '''Creates a QuantLib FixedRateBond object as the QLBond attribute
        '''
        cpn_sch = ql.DoubleVector((1., self.coupon))
        bnd_sched = ql.Schedule(self.issuedate, self.maturity, ql.Period(self.frequency),
                                ql.TARGET(), 
                                self.termconvention, self.termconvention, 
                                ql.DateGeneration.Rule.Backward, 
                                False)

        self.QLBond = ql.FixedRateBond(self.settlementdays, self.face, bnd_sched, cpn_sch,
                                       self.daycount,
                                       self.payconvention, self.face, self.issuedate)
        if pricingEngine:
            self.QLBond.setPricingEngine(pricingEngine)
        
        return self.QLBond
    
    def fairSwapRate(self, termstructure):
        '''
        calculate the fair swap rate matching structure of non-call portion of bond
        '''
        return USDLiborSwap(termstructure, 
                            self.settle, 
                            self.maturity, self.coupon, 
                            PayFlag=1, spread=0.0,
                            setPriceEngine=True).fairRate()

    def assetSwapSpread(self, termstructure, bondyield=None, price=None, 
                              vol=1e-7, model=ql.BlackKarasinski):
        '''
        Calculate asset swap spread
        '''
        try:
            value = self.calc(bondyield, price, True)
            bondyield, price = value['bondyield'], value['price']
        except:
            print("Problem with bondyield, price inputs: %s %s" % (bondyield, price))
            raise TypeError
        
        prm = -(price - 100.0)
        x_ = 0.0
        v_ = self.assetSwapPremium(termstructure, x_, vol, model=model)
        
        x1 = bondyield - self.fairSwapRate(termstructure)
        v1 = self.assetSwapPremium(termstructure, x1, vol, model=model)
        v_diff = v1 - prm
        ictr, maxctr = 0, BondExceptions.MAX_PY_ITERATIONS
        while abs(v_diff) > 1e-7 and abs(x1-x_) > 1e-7 and ictr < maxctr:
            delta = (v1 - v_) / (x1 - x_)
            x_ = x1
            x1 = x1 - v_diff / delta
            v_ = v1
            v1 = self.assetSwapPremium(termstructure, x1, vol, model=model)
            v_diff = v1 - prm
            ictr += 1

        assert (ictr < maxctr + 1), "Max iterations reached: %s" % x1*100.0
        return x1
        
    def assetSwapPremium(self, termstructure, spread_,
                         vol=1e-7, model=ql.BlackKarasinski):
        '''
        Calculate asset swap premium, given spread
        '''

        asw1 = USDLiborSwap(termstructure, 
                          self.settle, 
                          self.maturity, self.coupon, 
                          PayFlag=1, spread=spread_,
                          setPriceEngine=True,
                          notionalAmount = 100.0)
        prm = asw1.value()
        
        if self.calllist:
            firstcall, callprice = self.calllist[0]
            asw2 = USDLiborSwaption(termstructure, 
                                    firstcall, 
                                    self.maturity, self.coupon, 
                                    PayFlag=0, spread=spread_,
                                    notionalAmount = 100.0)
            prm += asw2.value(vol, model=model)
        
        return prm 
    settlementDate = property(getSettlement, setSettlement)
        
class BGMuniBond(MuniBond,BGBond):
    '''
    Muni Bond Object, inherits from BGBond
    Override asset swap methods to allow gross up coupon and apply leverage. (instrument based approach).
    
    '''
    def __init__(self, coupon, maturity, issuedate=None, oid=None,callfeature=None,
                       redvalue=100.0):
        BGBond.__init__(self, coupon, maturity, issuedate, oid, callfeature, MuniBond(),
                              redvalue)
        
    def qtax(self, settle=None, ptsyear=0.25):
        """Calculate de minimus cut-off for market discount bonds"""
        if settle or not self.settle:
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
    def calcAfterTax(self, price=None, bondyield=None,
                     settle=None, capgains=.15, ordinc=.35,
                     ptsyear=0.25):
        '''
        Calculate after-tax yield given price,
        sets qtax flag to True if price is outside deminimus
        '''
        
        # Check bond's attributes if arguments not passed.
        errstr = "calcAfterTax(): price=%s bondyield=%s exactly one must have a value"
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
            aty = self.calc(price=price)
            self.qtaxflag = False
            
        return aty
    
    def assetSwapHedgeRatio(self, basisTermstructure):
        baseTenor = basisTermstructure.tenorParRatio("10Y")
        basisSwap = BasisSwap(basisTermstructure.disc_termstr, basisTermstructure,
                              self.settle, self.maturity, 
                              baseTenor)
        return basisSwap.fairRatio()
    
    def fairSwapRate(self, basisTermstructure, basis=True):
        '''
        calculate the fair swap rate matching structure of non-call portion of bond
        '''
        if basis:
            termstructure = basisTermstructure
        else:
            termstructure = basisTermstructure.disc_termstr
        return USDLiborSwap(termstructure, 
                            self.settle, 
                            self.maturity, self.coupon, 
                            PayFlag=1, spread=0.0,
                            setPriceEngine=True).fairRate()
    
    def assetSwapPremium(self, basisTermstructure, spread_, 
                               vol=1e-7, ratio=None,
                               model=ql.BlackKarasinski):
        '''
        Calculate asset swap premium, given spread
        '''
        termstructure = basisTermstructure.disc_termstr
        if not ratio:
            ratio = self.assetSwapHedgeRatio(basisTermstructure)
        
        asw1 = USDLiborSwap(termstructure, 
                          self.settle, 
                          self.maturity, self.coupon/ratio, 
                          PayFlag=1, spread=spread_,
                          setPriceEngine=True,
                          notionalAmount = 100.0)
        prm = asw1.value()
        
        if self.calllist:
            firstcall, callprice = self.calllist[0]
            asw2 = USDLiborSwaption(termstructure, 
                                    firstcall, 
                                    self.maturity, self.coupon/ratio, 
                                    PayFlag=0, spread=spread_,
                                    notionalAmount = 100.0)
            prm += asw2.value(vol, model=model)
        
        return prm * ratio

    def assetSwapSpread(self, basisTermstructure, bondyield=None, price=None, 
                              vol=1e-7, ratio=None, model=ql.BlackKarasinski):
        '''
        Calculate asset swap spread
        '''
        try:
            value = self.calc(bondyield, price, True)
            bondyield, price = value['bondyield'], value['price']
        except:
            print("Problem with bondyield, price inputs: %s %s" % (bondyield, price))
            raise TypeError
            
        if not ratio:
            ratio = self.assetSwapHedgeRatio(basisTermstructure)
        
        prm = -(price - 100.0)
        x_ = 0.0
        v_ = self.assetSwapPremium(basisTermstructure, x_, vol, ratio=ratio, model=model)
        
        x1 = bondyield - self.fairSwapRate(basisTermstructure)
        v1 = self.assetSwapPremium(basisTermstructure, x1, vol, ratio=ratio, model=model)
        v_diff = v1 - prm
        ictr, maxctr = 0, BondExceptions.MAX_PY_ITERATIONS
        while abs(v_diff) > 1e-7 and abs(x1-x_) > 1e-7 and ictr < maxctr:
            delta = (v1 - v_) / (x1 - x_)
            x_ = x1
            x1 = x1 - v_diff / delta
            v_ = v1
            v1 = self.assetSwapPremium(basisTermstructure, x1, vol, ratio=ratio, model=model)
            v_diff = v1 - prm
            ictr += 1

        assert (ictr < maxctr + 1), "Max iterations reached: %s" % x1*100.0
        return x1

    def assetSwapRatio(self, basisTermstructure, bondyield=None, price=None, 
                             spread = 0.0,
                             vol=1e-7, model=ql.BlackKarasinski):
        '''
        Calculate asset swap ratio for given price and spread.  
        Spread is assumed to be zero, ability to specify spread is provided for flexibility
        '''
        try:
            value = self.calc(bondyield, price, True)
            bondyield, price = value['bondyield'], value['price']
        except:
            print("Problem with bondyield, price inputs: %s %s" % (bondyield, price))
            raise TypeError
            
        termstructure = basisTermstructure.disc_termstr
        ratio = self.assetSwapHedgeRatio(basisTermstructure)
        
        prm = -(price - 100.0)
        r_ = 1.0
        v_ = self.assetSwapPremium(basisTermstructure, spread, vol, ratio=r_, model=model)
        
        r1 = ratio
        v1 = self.assetSwapPremium(basisTermstructure, spread, vol, ratio=r1, model=model)
        v_diff = v1 - prm
        ictr, maxctr = 0, BondExceptions.MAX_PY_ITERATIONS
        while abs(v_diff) > 1e-7 and abs(r1-r_)*100.0 > 1e-7 and ictr < maxctr:
            delta = (v1 - v_) / (r1 - r_)
            r_ = r1
            r1 = r1 - v_diff / delta
            v_ = v1
            v1 = self.assetSwapPremium(basisTermstructure, spread, vol, ratio=r1, model=model)
            v_diff = v1 - prm
            ictr += 1

        assert (ictr < maxctr + 1), "Max iterations reached: %s" % r1*100.0
        return r1