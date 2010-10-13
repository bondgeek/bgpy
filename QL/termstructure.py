'''
Term Structure Classes--a set of wrappers around QuantLib

Created on May 26, 2010
@author: bartmosley
'''
import bgpy.QL as ql
from termstructurehelpers import HelperWarehouse, SwapRate
        
class TermStructureModel(object):
    '''
    Constructs a quantlib termstructure 
    '''
    depo_daycount = ql.Actual360()
    term_daycount = ql.Thirty360()
    daycount = ql.ActualActualISDA
    calendar = ql.TARGET()

    def __init__(self, curvedata=None, curvedate=None, datadivisor=1.000,
                     settledays=2):
        
        self.settledays = settledays
        
        if curvedata:
            self.update(curvedata, curvedate, datadivisor)
            
    def cleancurvedata(self, curve):
        '''
        Removes tenors with null values from curve.  Helpful if data has been read
        from, say, an Excel spreadsheet with incomplete data.
        '''
        
        # remove any null values from curve data 
        keys = curve.keys()
        for k in keys:
            if not curve.get(k, None):
                curve.pop(k)
                
        self.curvedata = curve
    
        return self.curvedata

    def setcurvedates(curvedate=None, settledays=2, calendar=ql.TARGET()):
        '''
        Set curve dates.
        '''
        if curvedate:
            curvedate = ql.bgDate(curvedate)
            curvedate = calendar.adjust(curvedate)
            ql.Settings.instance().setEvaluationDate(curvedate)
        else:
            curvedate = ql.Settings.instance().getEvaluationDate()
         
        settlement = calendar.advance(curvedate, settledays, ql.Days)
        
        self.curvedate = curvedate
        self.settlement = settlement
        
        return curvedate, settlement
    
    @property
    def handle(self):
        '''
        getter for handle property
        '''
        return ql.YieldTermStructureHandle(self.curve)
    
    def swapEngine(self):
        return ql.DiscountingSwapEngine(self.handle)

    def swaptionEngine(self, vol, 
                             alpha=1e-7, timeSteps=50, 
                             model=ql.BlackKarasinski): 
        '''
        models supported: BlackKarasinski, HullWhite
        '''
        return ql.TreeSwaptionEngine(model(self.handle, alpha, vol), 
                                     timeSteps, self.handle)

    def forwardDepo(self, begDate, endDate, dc=depo_daycount):
        '''
        Return forward deposit rate: (discount_beg/discount_end -1)/yearFrac
        '''
        begDate, endDate = ql.bgDate(begDate), ql.bgDate(endDate)
        discount = self.curve.discount
        yearFrac = dc.yearFraction(begDate, endDate)
        if yearFrac > 0.0:
            return (discount(begDate)/discount(endDate)-1.0)/yearFrac
        else:
            return 0.0
            
    def forwardPayment(self, begDate, endDate, dc=depo_daycount, spread = 0.0):
        '''
        Returns floating leg  payment amount.
        '''
        begDate, endDate = ql.bgDate(begDate), ql.bgDate(endDate)
        yfrac = dc.yearFraction(begDate, endDate)
        return (self.forwardDepo(begDate, endDate, dc) + spread) * yfrac
        
    def tenorpar(self, tenor):
        '''
        Returns par rate for given tenor -- e.g., termstr.tenorpar('10Y') 
        '''
        discount = self.curve.discount              #function calls
        advance = ql.TARGET().advance         #function calls
        tnr = ql.Tenor(tenor)
        settle = self.curve.referenceDate()
        
        if tnr.unit != 'Y':
            zeroRate = self.curve.zeroRate
            enddt = advance(settle, tnr.length, tnr.timeunit)
            return self.forwardDepo(settle, enddt, self.depo_daycount)

        tnrlen = tnr.length * 12 + 6
        pvals = [discount(advance(settle, n, ql.Months), extrapolate=True)
                  for n in range(0, tnrlen, 6)]
        
        return 2.0 * (1.0 - pvals[-1]/pvals[0]) * pvals[0] / sum(pvals[1:])
 
    def swappar(self, tenor):
        '''
        Returns par rate for given tenor -- e.g., termstr.tenorpar('10Y') 
        '''
        discount = self.curve.discount              #function calls
        advance = ql.TARGET().advance         #function calls
        tnr = ql.Tenor(tenor)
        settle = self.curve.referenceDate()
        
        if tnr.unit != 'Y':
            zeroRate = self.curve.zeroRate
            enddt = advance(settle, tnr.length, tnr.timeunit)
            return self.forwardDepo(settle, enddt, self.depo_daycount)

        tnrlen = tnr.length * 12 + 6
        fixedPvals = [discount(advance(settle, n, ql.Months), extrapolate=True)
                  for n in range(0, tnrlen, 6)]
                  
        fltlen = tnr.length * 12 + 3
        fltDates = [advance(settle, n, ql.Months) for n in range(0, fltlen, 3)]
        fltDates = zip(fltDates[:-1], fltDates[1:])
        fltPvals = [discount(d1)*self.forwardPayment(d0, d1) 
                    for d0, d1 in fltDates]
        
        return 2.0 * sum(fltPvals) / sum(fixedPvals[1:])
    
    def update(*args):
        pass
  
class SimpleCurve(TermStructureModel):
    '''
    SimpleCurve(curvedata, curvedate)
    
    curvedata must be a dictionary of the form {'10Y': rate}
    assumes that rates are in form 5.00% = 5.00
    use keyword datadivisor = 1.0, if rates are in decimal.
    '''
    ratehelpers = None
    curve = None
    instruments_ = ql.RateHelperVector()
    daycount = ql.ActualActualISDA
    calendar = ql.TARGET()

    JumpQuotes = ql.QuoteHandleVector()
    JumpDates = ql.DateVector()
    accuracy = 1e-12
    
    def __init__(self, curvedata=None, curvedate=None, datadivisor=1.000,
                     settledays=2, setIborIndex=True):
      
        self.setIborIndex = setIborIndex
        TermStructureModel.__init__(self, curvedata, curvedate, datadivisor,
                                    settledays)
                                    
    def update(self, curvedata, curvedate=None, datadivisor=1.0):
        "creates ratehelpers object"
        curvedata = self.cleancurvedata(curvedata)
        
        if self.ratehelpers:
            self.ratehelpers.update(curvedata, datadivisor)
        else:
            self.ratehelpers = HelperWarehouse(curvedata.keys(), 
                                               curvedata.values(), 
                                               datadivisor)
        if not curvedate:
            curvedate = ql.Settings.instance().getEvaluationDate()
            
        self.curvedate = self.calendar.adjust(curvedate)
        self.settlement = self.calendar.advance(curvedate, 
                                                self.settledays, ql.Days)
                                                
        ql.Settings.instance().setEvaluationDate(self.curvedate)
        
        if self.setIborIndex:
            SwapRate.setLibor(self.settlement, 
                              self.curvedata[SwapRate.floatingLegIndex]/datadivisor)

        if not self.curve:
            self.curve_(self.ratehelpers.vector)
        
    def curve_(self, ratehelpervector):
        "calc curve"

        PYC = ql.PiecewiseFlatForward
        self.curve = PYC(self.settledays, self.calendar, ratehelpervector, 
                         ql.ActualActualISDA,
                         self.JumpQuotes, self.JumpDates, self.accuracy)

        self.curve.enableExtrapolation()
        self.discount = self.curve.discount
        self.zeroRate = self.curve.zeroRate
        self.referenceDate = self.curve.referenceDate
    
class DiscountCurve(TermStructureModel):
    '''
    Fits a set of pure discount factors to a term structure.
    '''
    def __init__(self, curvedata=None, settledays = 2,
                 interp = ql.LogLinear()):
    
        self.settledays = settledays
        self.interp = interp
        
        if curvedata:
            self.update(curvedata, datadivisor)

    def update(self, curvedata, datadivisor=1.0):
    
        curvedata = self.cleancurvedata(curvedata)

        datevector = curvedata.keys()
        self.settlement = datevector[0]
        self.curvedate = ql.TARGET().advance(self.settlement, -1*self.settledays, 
                                             ql.Days)
        datevector.sort(key=lambda x: x.serialNumber())
        
        discountvector = DoubleVector([float(curvedata[d]) for d in datevector])        
        datevector = DateVector(datevector)

        self.curve = DiscountCurve(datevector, discountvector,
                                   self.daycount, self.calendar, 
                                   self.interp)
                                   
        self.curve.enableExtrapolation()
        self.discount = self.curve.discount
        self.zeroRate = self.curve.zeroRate
        self.referenceDate = self.curve.referenceDate


class RatioBasisCurve(object):
    pass