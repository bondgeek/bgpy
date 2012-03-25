'''
Bond math routines, 
Uses QuantLib date handling, everything takes Resolver's f%^&*(#@g Microsoft Dates

Created on Jan 24, 2010
@author: Bart Mosley
'''
import logging

from math import floor, fmod

import bgpy.__QuantLib as ql

from bgpy.QL import toDate
from bgpy.math import Secant, SolverExceptions
from bgpy.QL.assetswap import AssetSwap

#globals
calendar = ql.TARGET()
    
#class definitions
class BondException(Exception):
    MAX_PY_ITERATIONS = 24
    MAX_PY_ITERATIONS_MSG = "Max Iterations--%d--reached in price/yield calc" % MAX_PY_ITERATIONS
    MIN_YLD = 1e-7
    NEG_YIELD_MSG = "Negative yield in ytmToPrice" 

class BondType(object):
    '''
    Do not use except as base class
    '''
    
    settlementdays = 3
    daycount = ql.Thirty360()
    frequency = ql.Semiannual
    payconvention = ql.Unadjusted
    termconvention = ql.Unadjusted
    calendar = ql.USGovernmentBond
    face = 100.0
    
    def bondtype(self):
        attrs_ = ('settlementdays', 'daycount', 'frequency',
                  'payconvention', 'termconvention', 'face', 'calendar')
                    
        return dict(zip(attrs_, [getattr(self, a) for a in attrs_]))
        
class SimpleBondType(BondType):
    settlementdays = 3
    daycount = ql.Thirty360()
    frequency = ql.Semiannual
    payconvention = ql.Unadjusted
    termconvention = ql.Unadjusted
    calendar = ql.USGovernmentBond
    face = 100.0
    
    def bondtype(self):
        d = BondType().bondtype()
        for k in d:
            d[k] = getattr(self,k)
        return d

class Call(object):
    def __init__(self, firstcall=None, callprice=None, parcall=None, 
                 frequency=ql.Semiannual, redvalue=100., ObjectId=None):
        '''
        Create a call feature.
        '''
        # make sure we have a QuantLib compliant set of dates
        firstcall, parcall = map(toDate, [firstcall, parcall])
        self.firstcall = firstcall if firstcall else ql.Date()
        self.callprice = callprice
        self.parcall = parcall if parcall else ql.Date()
        self.frequency = frequency
        
    def __str__(self):
        return "@".join((str(self.firstcall), str(self.callprice)))

    def __repr__(self):
        return self.__str__()

class SimpleBond(SimpleBondType):
    '''
    Bond Object: 
    coupon, maturity, issuedate, oid, callfeature, bondtype, redvalue
    
    '''
    def __init__(self, coupon, maturity, 
                 callfeature=None, oid=None, issuedate=None, 
                 redvalue=100.,
                 settledate=None):
        '''
        Examples:
        Non Call Bond:
        > bond = bgpy.QL.SimpleBond(.05, date(2022, 3, 1))
        
        Callable Bond:
        > bond = bgpy.QL.SimpleBond(.05, 
                                    date(2022, 3, 1),
                                    oid=.055,
                                    callfeature=bgpy.QL.Call(date(2017, 3, 1)),
                                    issuedate=date(2007, 3, 1)
                                    )
                                    
        '''
        maturity, issuedate, settledate = map(toDate, [maturity, issuedate, 
                                                       settledate])

        self.coupon = coupon
        self.maturity = maturity
        self.issuedate = issuedate 
        self.redvalue = redvalue
        self.oid = oid

        self.setSettlement(settledate)
        self.setCallfeature(callfeature)
        
    def __str__(self):
        return "% ".join((str(self.coupon*100.0), str(self.maturity)))
    
    def setCallfeature(self, callfeature=None):
        if callfeature:
            if callfeature.firstcall >= self.maturity:
                callfeature = None
                
        self.callfeature = callfeature
        
        # call list contains bond objects representing each call
        # calling self.CallList sets those settlement dates.
        self.calllist = self.CallList()
        
        
    def setSettlement(self, settledate=None):
        '''
        Change settlement for bond calculations
        '''
        settledate = toDate(settledate)
        
        if not settledate:
            evalDate = ql.Settings.instance().getEvaluationDate() 
            settle_ = self.calendar.advance(evalDate,
                                            self.settlementdays, 
                                            ql.Days)
        else:
            settle_ = settledate
        
        if self.issuedate and self.daycount.dayCount(self.issuedate, settle_) < 0: 
            settle_ = self.issuedate
        self.settle_ = settle_
                
        #TODO: This maybe can be more robust for non-standard frequencies
        #      It works for annual, quarterly & semi-annual.
        freq = float(ql.freqValue(self.frequency))
        self.term = freq * self.daycount.yearFraction(self.settle_, 
                                                        self.maturity)
        
        self.nper = floor(self.term)
        self.frac = self.term - self.nper
        self.term /= freq
        
        return self
   
    def getSettlement(self):
        return getattr(self, "settle_", None)
   
    settlementDate = property(getSettlement, setSettlement)
    
    def CallList(self):
        '''
        Converts Call Feature to list of call dates and bond objects.
        
        '''
        
        calllist = []
        if self.callfeature:
            dtp = 0.0
            call = self.callfeature
            
            freq = ql.Period(call.frequency)
            
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
                                   redvalue=price,
                                   settledate=self.settlementDate)
                                   
                calllist.append((calldate,price, cbond))
                
                calldate = calendar.advance(calldate, freq, ql.Unadjusted)
                
                if calldate >= call.parcall:
                    price = getattr(self, "face", 100.0)         
                else:
                    price = price - dtp
                
        return calllist
       
    def maxPrice(self):
        '''
        Determines the price if yieldtoworst = 0 (or close to it)
        
        '''
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
        
        price = bondprice # needed to change argument for Resolver
        if not (bondyield or price):
            bondyield = getattr(self, "bondyield", None)
            price = getattr(self, "price", None)
        
            assert (not price or not bondyield), errstr % (price, bondyield)
        
        def to_other(level, ytmfunc, cmplevel):
            '''
            cmplevel:  use to calculate yield to worst from price, if callable 
                       otherwise returns ytm 
            
            '''
            val = getattr(self, ytmfunc)(level)
            todate = self.maturity
            toprice = self.redvalue

            if self.calllist:
                earliestcall= calendar.advance(self.settle_, 
                                               ql.Period(self.frequency))
                
                for call in self.calllist:
                    calldt, callpx, cbond = call
                    
                    if all([(self.daycount.dayCount(earliestcall, calldt) >= 0),
                            (callpx <= level or not cmplevel), 
                            (calldt < todate or callpx < toprice)]):
                        
                        cbond.settlemenDate = self.settle_
                        newval = getattr(cbond, ytmfunc)(level)
                        
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
        
        # TODO: should replace this functionality with a property that returns
        #       a dictionary
        if dict_out:
            val, todate, toprice = result_value
            if not bondyield:
                bondyield = val
            else:
                price = val
                
            result = {'bondyield': bondyield, 
                      'price': price, 
                      'toDate': todate,
                      'toPrice': toprice,
                      'dv01': self.dv01(bondyield),
                      'dv01YTM': self.dv01YTM(bondyield)}
            result[calcattr] = val
        else:
            result = result_value[0]
            
        return result
              
    def ai(self):
        if (self.frac==0):
                return 0
        else:
                return (1.-self.frac)*self.coupon/ql.freqValue(self.frequency)
            
    def ytmToPrice(self, yld, redemption=None):
        """calculates price given yield"""    
        if(yld < 0.0):
            logging.info("%s\nsettle: %s coupon: %s maturity: %s" % 
                            (BondException.NEG_YIELD_MSG,
                             self.settlementDate, 
                             self.coupon, 
                             self.maturity))
                            
            # yld = BondException.MIN_YLD
            
        if not redemption:
            redemption = self.redvalue
            
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
            prc = (t*(u*(1.0-z) + z*redemption/100.0 + nxtcpn) - self.ai())*100.0
            price = round(prc,6)

        return price
    
    def toYield(self, _price):
        return self.calc(bondprice = _price)
        
    def toPrice(self, _yield):
        return self.calc(_yield)
       
    def toYTM(self, price, redemption=None):
        '''
        Calculate yield to maturity from price.
        Secant search is sufficient as price is generally well-behaved,
        and coupon, current yield are natural initial values.
        
        '''
        
        if not redemption:
            redemption = self.redvalue
            
        objfunction = lambda x: self.ytmToPrice(x, redemption)
        
        if abs(price-100.0) < 1e-7:
            yld=self.coupon
        else:
            if(self.coupon > 0.0):
                y0 = self.coupon
                yg = 100.*self.coupon / price
            else:
                y0 = getattr(self, "oid", None)
                yg = 100.*y0 / price if self.oid else .04
                y0 = y0 if y0 else .05

            try:
                yld = Secant(y0, yg, objfunction, price)
            except BondException:
                logging.info("Solver error in toYTM")
                return BondException.MIN_YLD
            except:
                raise
                
        return yld
    
    def dv01(self, bondyield):
        ydelta = 0.0001
        p0 = self.toPrice(bondyield-ydelta)
        p1 = self.toPrice(bondyield+ydelta)
        
        return (p0 - p1) / 2.0
    
    
    def dv01YTM(self, bondyield):
        ytm = self.toYTM(self.toPrice(bondyield))
        ydelta = 0.0001
        p0 = self.ytmToPrice(ytm-ydelta)
        p1 = self.ytmToPrice(ytm+ydelta)
        
        return (p0 - p1) / 2.0
    
    def assetSwap(self, termstructure=None, spread_=0.0, ratio=1.0):
        '''
        links an asset swap object.
        ''' 
        self.assetswap = AssetSwap(self, termstructure, spread_, ratio)
        
        return self.assetswap
        