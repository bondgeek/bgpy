'''
Created on Oct 14, 2009

@author: bartmosley
'''
from math import exp, log

import bgpy.__QuantLib as ql

from bgpy.QL.bgdate import toDate

FixedPayer = ql.VanillaSwap.Payer
FixedReceiver = ql.VanillaSwap.Receiver

def forwardSpreadDepo(spread_):
    '''
    Convert instantaneous forward rate spread to actual360 depo rate
    '''
    return 2.0 * (exp((91./360.) * spread_) ** (180./91.) - 1.0)

def depoSpreadforward(spread_):
    '''
    Convert actual360 depo rate to instantaneous forward rate spread
    '''
    return (-360./91.)*log( (1.+spread_/2.)**(-91./180.))
    
class USDLiborSwap(object):
    fixedLegFrequency = ql.Semiannual
    fixedLegAdjustment = ql.Unadjusted
    fixedLegDayCounter =  ql.Thirty360()
    fixedLegPeriod = ql.Period(fixedLegFrequency)

    floatingLegFrequency =  ql.Quarterly
    floatingLegAdjustment =  ql.ModifiedFollowing
    floatingLegDayCounter = ql.Actual360()
    floatingLegPeriod = ql.Period(3, ql.Months)
    calendar = ql.TARGET()
    
    def __init__(self, termstructure, startDate, termDate, fixedRate, PayFlag=1, 
                spread=0.0, notionalAmount=100.0,
                setPriceEngine=False):
        self.termstructure = termstructure
        startDate, termDate = map(toDate, [startDate, termDate])
        self.payFlag = FixedPayer if PayFlag else FixedReceiver
        self.startDate = startDate
        self.termDate = termDate
        self.fixedRate = fixedRate
        
        self.spread = spread
        
        self.floatingLegIndex_  = ql.USDLibor(self.floatingLegPeriod, 
                                              self.termstructure.handle)
        
        self.fixedSched_ = ql.Schedule(self.startDate, 
                                 self.termDate,  
                                 self.fixedLegPeriod, 
                                 self.calendar,
                                 self.fixedLegAdjustment, 
                                 self.fixedLegAdjustment,
                                 ql.Forward, False)
                                 
        self.floatingSched_ = ql.Schedule(startDate, termDate,  
                                 self.floatingLegPeriod, 
                                 self.calendar,
                                 self.floatingLegAdjustment, 
                                 self.floatingLegAdjustment,
                                 ql.Forward, False) 

        self.swap = ql.VanillaSwap(self.payFlag, notionalAmount,
                                  self.fixedSched_, self.fixedRate, 
                                  self.fixedLegDayCounter,
                                  self.floatingSched_, 
                                  self.floatingLegIndex_, self.spread,
                                  self.floatingLegDayCounter)

        if setPriceEngine:
            self.pricingEngine = self.termstructure.swapEngine()
            self.swap.setPricingEngine(self.pricingEngine)
        else:
            self.pricingEngine = None
    
    # TODO: set, get initial Libor property
    # conform value method across instruments
    # generic risk sensitivity metrics for termstructured instruments
    #
    @property
    def fixedSchedule(self):
        return self.fixedSched_
    @property
    def floatingSchedule(self):
        return self.floatingSched_
    @property
    def iborIndex(self):
        return self.floatingLegIndex_
        
    def value(self, termstructure_=None):
        if termstructure_:
            self.pricingEngine = termstructure_.swapEngine()
            self.swap.setPricingEngine(self.pricingEngine)
        elif not self.pricingEngine:
            if self.termstructure:
                self.pricingEngine = self.termstructure.swapEngine()
                self.swap.setPricingEngine(self.pricingEngine)
            else:
                return None
            
        return self.swap.NPV()

class USDLiborSwaption(object):
    '''
    Vanilla Libor Swaption
    '''
    calendar = ql.TARGET()
    fixedLegAdjustment = USDLiborSwap.fixedLegAdjustment
    
    def __init__(self, termstructure, firstCallDate, termDate, fixedRate, 
                PayFlag=1, spread=0.0, 
                notionalAmount=100.0,
                bermudan = False,
                callFrequency=ql.Annual
                ):
        self.termstructure = termstructure
        self.spread = spread
        firstCallDate, termDate = map(toDate, [firstCallDate, termDate])
        self.swap = USDLiborSwap(self.termstructure, firstCallDate, termDate, 
                            fixedRate, 
                            PayFlag, self.spread, 
                            notionalAmount).swap
        
        if bermudan:
            schedPeriod = ql.Period(callFrequency)
            lastCallDate = self.calendar.advance(self.swap.maturityDate(), 
                                                 -1,
                                                 callFrequency) 
            
            bdatesSched = ql.Schedule(firstCallDate, lastCallDate,  
                                      schedPeriod, 
                                      self.calendar,
                                      self.fixedLegAdjustment, 
                                      self.fixedLegAdjustment,
                                      ql.Forward, 
                                      False)

            self.exercise = ql.BermudanExercise(bdatesSched)
        else:
            self.exercise = ql.EuropeanExercise(firstCallDate)
        
        self.swaption = ql.Swaption(self.swap, self.exercise)
    
    def value(self, vol, termstructure_=None, model=ql.BlackKarasinski):
        '''
        Requires volatility input
        '''
        if termstructure_:
            engine = termstructure_.swaptionEngine(vol, model=model)
        else:
            engine = self.termstructure.swaptionEngine(vol, model=model)
        
        self.swaption.setPricingEngine(engine)
        
        return self.swaption.NPV()
        
class BasisSwap(ql.Swap):
    '''
    Models a swap paying/receiving a percent of libor index versus basis index plus a spread.
    '''
    calendar = ql.USGovernmentBond
    frequency =  ql.Quarterly
    adjustment =  ql.ModifiedFollowing
    
    liborLegDayCounter = ql.Actual360()
    basisLegDayCounter = ql.ActualActual()
    
    def __new__(cls, discountTermstructure, 
                     forecastTermstructure,
                     startDate, termDate, 
                     fixedRatio, PayFlag=True, 
                     spread=0.0, notionalAmount=100.0,
                     setPriceEngine=False):
        startDate, termDate = map(toDate, [startDate, termDate])
        schedule = ql.Schedule(startDate, termDate,  
                               ql.Period(cls.frequency), 
                               cls.calendar,
                               cls.adjustment, 
                               cls.adjustment,
                               ql.DateGeneration.Rule.Forward, False)
 
        liborLeg = ql.Leg()
        basisLeg = ql.Leg()
        for n in range(schedule.size()):
            payDate = schedule.date(n)
            if n > 0:
                liborLegPayment = fixedRatio * discountTermstructure.forwardPayment(prevdt, payDate) * notionalAmount
                basisLegPayment = forecastTermstructure.forwardPayment(prevdt, payDate, spread=spread) * notionalAmount + spread
            else:
                liborLegPayment, basisLegPayment = (0., 0.)
                
            liborLeg.Add(ql.SimpleCashFlow(liborLegPayment, payDate))
            basisLeg.Add(ql.SimpleCashFlow(basisLegPayment, payDate))
            
            prevdt = payDate
            
        if PayFlag:
            payleg, recleg = liborLeg, basisLeg
        else:
            recleg, payleg = liborLeg, basisLeg

        
        cls = ql.Swap.__new__(cls, payleg, recleg)
        
        cls.termstructure = discountTermstructure
        cls.forecastTermstructure = forecastTermstructure
        cls.schedule = schedule

        if setPriceEngine:
            self.setPricingEngine(discountTermstructure.swapEngine())
            
        return self
    
    def fairRatio(self):
        '''
        return fair fixed ratio
        '''
        idxcrv = self.forecastTermstructure
        lbrcrv = self.termstructure
        
        fwdratio = idxcrv.forwardPayment
        fwdlbr = lbrcrv.forwardPayment
        
        idxdisc = idxcrv.discount
        discount = lbrcrv.discount              #function calls
        
        advance = self.calendar.advance         #function calls

        paydates = [(self.schedule.date(n-1), self.schedule.date(n)) 
                    for n in range(1, self.schedule.size())]
        
        pvals = [(discount(dt, extrapolate=True), fwdratio(d0, dt), 
                  fwdlbr(d0, dt), idxdisc(dt), d0, dt)
                 for d0, dt in paydates[1:]]

        sum1 = sum([df * fwdlbr for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        sum2 = sum([df * fwdmuni for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        
        return sum2/sum1

    def value(self, termstructure_=None):
        if termstructure_:
            self.setPricingEngine(termstructure_.swapEngine())
        elif not hasattr(self, "pricingEngine"):
            self.setPricingEngine(self.termstructure.swapEngine())

        return self.NPV()
    