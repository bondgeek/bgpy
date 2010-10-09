'''
Created on Oct 14, 2009

@author: bartmosley
'''
import bgpy.QL as ql

FixedPayer = ql.VanillaSwap.Payer
FixedReceiver = ql.VanillaSwap.Receiver

class USDLiborSwap(object):
    fixedLegFrequency = ql.Semiannual
    fixedLegAdjustment = ql.Unadjusted
    fixedLegDayCounter =  ql.Thirty360(0)
    fixedLegTenor = ql.Period(fixedLegFrequency)

    floatingLegFrequency =  ql.Quarterly
    floatingLegAdjustment =  ql.ModifiedFollowing
    floatingLegDayCounter = ql.Actual360()
    floatingLegTenor = ql.Period(3, ql.Months)
    calendar = ql.TARGET()
    
    pricingEngine = None
    
    def __init__(self, termstructure, startDate, termDate, fixedRate, PayFlag=1, 
                spread=0.0, notionalAmount=100.0,
                setPriceEngine=False):
        startDate, termDate = map(ql.bgDate, [startDate, termDate])
        self.payFlag = FixedPayer if PayFlag else FixedReceiver
        self.startDate = startDate
        self.termDate = termDate
        self.spread = spread
        self.termstructure = termstructure
        self.fixedRate = fixedRate
        
        self.floatingLegIndex_  = ql.USDLibor(self.floatingLegTenor,
                                             self.termstructure.handle)
        
        self.fixedSched_ = ql.Schedule(self.startDate, 
                                 self.termDate,  
                                 self.fixedLegTenor, 
                                 self.calendar,
                                 self.fixedLegAdjustment, 
                                 self.fixedLegAdjustment,
                                 ql.Forward, False)
                                 
        self.floatingSched_ = ql.Schedule(startDate, termDate,  
                                 self.floatingLegTenor, 
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
            self.pricingEngine = termstructure.swapEngine()
            self.swap.setPricingEngine(self.pricingEngine)
    
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
            self.swap.setPricingEngine(termstructure_.swapEngine())
        elif (not self.pricingEngine and hasattr(self, "termstructure")):
            self.swap.setPricingEngine(self.termstructure.swapEngine())
        else:
            return None
            
        return self.swap.NPV()

class USDLiborSwaption(object):
    '''
    Vanilla Libor Swaption
    '''
    calendar = ql.TARGET()
    
    def __init__(self, termstructure, firstCallDate, termDate, fixedRate, 
                PayFlag=1, spread=0.0, 
                notionalAmount=100.0,
                bermudan = False,
                callFrequency=ql.Semiannual
                ):
        firstCallDate, termDate = map(ql.bgDate, [firstCallDate, termDate])
        self.termstructure = termstructure
        swap = USDLiborSwap(self.termstructure, firstCallDate, termDate, fixedRate, 
                            PayFlag, spread, 
                            notionalAmount).swap
        
        if bermudan:
            lastCallDate = swap.fixedSched.date(swap.fixedSched.size()-2)
            schedTenor = ql.Period(callFrequency)
            
            bdatesSched = ql.Schedule(firstCallDate, lastCallDate,  
                                      schedTenor, 
                                      self.calendar,
                                      swap.fixedLegAdjustment, 
                                      swap.fixedLegAdjustment,
                                      ql.Forward, False)

            self.exercise = ql.BermudanExercise(bdatesSched.dates())
        else:
            self.exercise = ql.EuropeanExercise(firstCallDate)
        
        self.swaption = ql.Swaption(swap, self.exercise)

    
    def value(self, vol, termstructure_=None, model=ql.BlackKarasinski):
        '''
        Requires volatility input
        '''
        if termstructure_:
            engine = termstructure_.swaptionEngine(vol, termstructure_, model)
        else:
            engine = self.termstructure.swaptionEngine(vol, model=model)
        
        self.swaption.setPricingEngine(engine)
        
        return self.swaption.NPV()

class BasisSwap(ql.Swap):
    '''
    Models a swap paying/receiving a percent of libor index versus basis index plus a spread.
    '''
    calendar = ql.UnitedStates(ql.UnitedStates.Market.GovernmentBond)
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
        startDate, termDate = map(ql.bgDate, [startDate, termDate])
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
