'''
Term Structure Classes--a set of wrappers around QuantLib

Handles Helpers.

Created on September, 2010
@author: bartmosley
'''
import bgpy.QL as ql

class BGRateHelper(object):
    '''
    Base class for QuantLib RateHelper constructors:
    
    E.g.
    rh_instance = RateHelper("10Y")   #RateHelper instance with parameters
                                        set for a 10 year tenor
    rh = rh_instance.getHelper( .05 ) #rate helper object for given rate.
    
    Sub-classes must define daycount, and any other required parameters.
    Also sub-classes MUST define member function _helper, which calls the 
    appropriate QuantLib RateHelper function.
    '''
    calendar=ql.TARGET() 
    settlementDays = 2
    
    def __init__(self, tenor):
        self.tenor = ql.Tenor(tenor).qlPeriod

    def _helper(self):
        "Must be overloaded on subclass level."
        return None
        
    def getHelper(self, level, datadivisor=1.0):
        '''
        Getter for helper property, called by SimpleHelper.__call__
        Helper property will be a tuple: (quote object, helper object)
        '''
        self.level = level / datadivisor
        self.quote = ql.SimpleQuote(self.level)
        return self._helper()
    
class DepoRate(BGRateHelper):
    "QuantLib RateHelper constructor for simple deposit rates, such as Libor"
    dayCounter = ql.Actual360()
           
    def __init__(self, tenor):
        BGRateHelper.__init__(self, tenor)
        
    def _helper(self):
        return (self.quote, 
                ql.DepositRateHelper(ql.QuoteHandle(self.quote),
                                     self.tenor, self.settlementDays,
                                     self.calendar, ql.ModifiedFollowing,
                                     False, self.dayCounter))

class SwapRate(BGRateHelper):
    '''
    QuantLib RateHelper constructor for USD swap rates, semi vs 3ML
    '''
    fixedLegFrequency = ql.Semiannual
    fixedLegAdjustment = ql.ModifiedFollowing
    fixedLegDayCounter = ql.Thirty360()
    calendar = ql.TARGET()
    floatingLegIndex = '3M'
    floatingLegTenor = ql.Period(floatingLegIndex)
    libor = ql.USDLibor(floatingLegTenor)
    
    def __init__(self, tenor):
        BGRateHelper.__init__(self, tenor)
            
    @classmethod
    def setLibor(cls, settlementDate, fixingRate=None):
        '''
        Add a fixing for the appropriate date corresponding to a given settlement date.
        If no fixing rate is given, returns the fixing for the given date, 
        or None if does not exist--avoiding RuntimeError thrown by QuantLib
        '''
        fixingDate = cls.libor.fixingDate(ql.toDate(settlementDate))
        
        if not fixingRate:
            try:
                fixingRate = cls.libor.fixing(fixingDate)
            except:
                fixingRate = None
        else:
            try:
                cls.libor.addFixing(fixingDate, fixingRate)
            except:
                try:
                    fixingRate = cls.libor.fixing(fixingDate)
                except:
                    # to hell with it...this won't be necessary in QuantLib1.0
                    # TODO: use forceoverwrite in QL version 1.0
                    pass
                
        return (fixingDate, fixingRate)
    
    def _helper(self):        
        return (self.quote, 
                ql.SwapRateHelper(ql.QuoteHandle(self.quote),
                                  self.tenor, self.calendar,
                                  self.fixedLegFrequency,
                                  self.fixedLegAdjustment,
                                  self.fixedLegDayCounter, self.libor))             

class BondHelper(object):
    '''
    Uses the same interface as RateHelper objects.
    '''
    settledays=2
    issueDate=None 
    daycount = ql.Thirty360(0)
    calendar = ql.TARGET()
    
    def __init__(self, maturity, todaysDate=None,
                 issueDate=None):
        '''create QuantLib FixedRateBondHelper object'''            
        if todaysDate:
            self.todaysDate = ql.toDate(todaysDate)
        else:
            self.todaysDate = ql.Settings.instance().getEvaluationDate()

        if issueDate:
            self.issueDate = ql.toDate(issueDate) 
        else:
            # just a kluge to insure that a semi-annual coupon has occured
            # before evaluationDate
            self.issueDate = self.calendar.advance(self.todaysDate, 
                                                   -12, ql.Months)
        if type(maturity) is str:
            tenor = ql.Tenor(maturity)            
            maturity = self.calendar.advance(self.todaysDate,
                                             tenor.length,
                                             tenor.timeunit)
            if tenor.unit == 'Y':
                y = maturity.year()
                m = maturity.month()
                maturity = ql.toDate(1, m, y)
            
            self.maturity = maturity
        
        else:
            self.maturity = ql.toDate(maturity)
            
    def getHelper(self, level, datadivisor=1.0):
        self.coupon, self.dollarprice = level
        cpn = ql.DoubleVector([1.0, self.coupon/datadivisor])

        sched =ql.Schedule(self.issueDate, self.maturity, 
                           ql.Period(ql.Semiannual), self.calendar, 
                           ql.ModifiedFollowing, ql.ModifiedFollowing, 
                           ql.Backward, 0)

        self.quote = ql.SimpleQuote(self.dollarprice)
        return  (self.quote,
                 ql.FixedRateBondHelper(ql.QuoteHandle(self.quote), 
                                        self.settledays, 100.0, sched, cpn,
                                        self.daycount,
                                        ql.ModifiedFollowing, 100.0))

class SimpleHelper(dict):
    '''
    Factory Class. Handles the most generic helper calls--i.e. those where the default
    values on optional arguments are used.
    
    E.g.,
    RateHelper = SimpleHelper()  # default instance of SimpleHelper, or
    RateHelper = SimpleHelper( {'s': myswapratehelper} ) #runs with a custom swap rate helper 
    helper = ratehelper('10Y', .03) # a SwapRateHelper for a 10 year tenor
    helper = ratehelper(ql.Date(1, 11, 2040), (.03, 100)) # a FixedRateBondHelper
                                                
    '''
    helpers = {'d': DepoRate, 's': SwapRate, 'b': BondHelper}
    def __init__(self, datadivisor, **kwargs):
        self.datadivisor = datadivisor
        if kwargs:
            self.helpers.update(**kwargs) #TODO: add check to see if valid helper
        dict.__init__(self, self.helpers)
        
    def __call__(self, tenor, level, today=None, use=None):

        if use:
            ratehelper = use(tenor)  
        elif type(tenor) is str:
            tnr = ql.Tenor(tenor)
        
            #TODO:  this logic needs to be more generic
            helpertype = 's' if tnr.unit == 'Y' else 'd'
            ratehelper = self.helpers[helpertype](tenor)
  
        else:
            helpertype = 'b'
            ratehelper = self.helpers[helpertype](tenor, today)
        
        return ratehelper.getHelper(level, self.datadivisor)

class HelperWarehouse(object):
    '''
    Create a container for QuantLib TermStructure RateHelpers.
    '''

    def __init__(self, swaptenors, levels_=None, datadivisor=1.0, helper=None):
        self.ratehelpers = {}
        self.ratehelpervector = ql.RateHelperVector()
        if not levels_:
            levels_ = [0 for tenor in swaptenors]
        else:
            assert len(swaptenors) == len(levels_), "levels and tenor list should be same length"
        
        self.specialhelper = helper
        self.datadivisor = datadivisor
        
        swaplevels = zip(swaptenors, levels_)
        getratehelper = SimpleHelper(self.datadivisor)
        
        for tenor, level in swaplevels:
            quote, helper = getratehelper(tenor, level, use=self.specialhelper)            
            self.ratehelpers[tenor] = {'quote': quote, 
                                       'helper': helper}
        
        # tenorlist will serve to track which tenors were updated on
        # the last update.
        self.tenorlist = self.ratehelpers.keys()
                   
    def update(self, curvedata):
        '''
        Update from dictionary of levels.
        '''
        self.tenorlist = curvedata.keys()
        for tenor in self.tenorlist:
            level = curvedata[tenor]/self.datadivisor
            self.ratehelpers[tenor]['quote'].setValue(level)
    
    @property
    def vector(self):
        '''
        Return RateHelperVector object.  List includes only latest update.
        '''
        self.ratehelpervector.Clear()

        if self.ratehelpers:
            for tenor in self.tenorlist:
                helper = self.ratehelpers[tenor]
                self.ratehelpervector.Add(helper['helper'])

        return self.ratehelpervector
    
    @property
    def list(self):
        return [self.ratehelpers[tenor]['helper'] for tenor in self.tenorlist]
        