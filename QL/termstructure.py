'''
Term Structure Classes--a set of wrappers around QuantLib

Created on May 26, 2010
@author: bartmosley
'''
import bgpy.QL as ql
from termstructurehelpers import HelperWarehouse, SwapRate

from math import floor
        
class TermStructureModel(object):
    '''
    Constructs a quantlib termstructure 
    '''
    depo_daycount = ql.Actual360()
    term_daycount = ql.Thirty360()
    daycount = ql.ActualActualISDA
    calendar = ql.TARGET()

    def __init__(self, datadivisor=1.000, settledays=2, label=None):
        
        self.label = label
        self.datadivisor = datadivisor
        self.settledays = settledays
        
        # TODO:  need to refactor to self.curve_
        self.curve = ql.RelinkableYieldTermStructureHandle()
        self.upToDate = False
        self.discount = self.curve.discount
        self.zeroRate = self.curve.zeroRate
        self.referenceDate = self.curve.referenceDate
            
    def cleancurvedata(self, curve):
        '''
        Removes tenors with null values from curve.  Helpful if data has been read
        from, say, an Excel spreadsheet with incomplete data.
        '''
        
        # remove any null values from curve data 
        keys = curve.keys()
        self.curvedata = {}
        for k in keys:
            if (curve.get(k, None) and k):
                self.curvedata[k] = curve[k]
                
        return self.curvedata
    
    @property
    def handle(self):
        '''
        getter for handle property
        '''
        return self.curve
    
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
        
    def bondpar(self, matDate, dayCount=ql.Thirty360(), frequency=ql.Semiannual):
        '''
        Returns par rate for given maturity
        '''
        discount = self.curve.discount              #function calls
        advance = ql.TARGET().advance               #function calls
        settle = self.curve.referenceDate()
        
        freq = float(ql.freqValue(frequency))
        term = freq * dayCount.yearFraction(settle, matDate)
        
        nper = floor(term)
        frac = term - nper
        
        # second argument to discount allows extrapolation
        pvals = [discount((float(n)+frac)/freq, True) for n in range(nper+1)]
        
        t = pvals[0]
        return 2.0 * (1.0/t - pvals[-1]) / (sum(pvals[1:])-(1.0-frac)/t)
 
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
        fixedPvals = [discount(advance(settle, n, ql.Months), True)
                  for n in range(0, tnrlen, 6)]
                  
        fltlen = tnr.length * 12 + 3
        fltDates = [advance(settle, n, ql.Months) for n in range(0, fltlen, 3)]
        fltDates = zip(fltDates[:-1], fltDates[1:])
        fltPvals = [discount(d1, True)*self.forwardPayment(d0, d1) 
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
    daycount = ql.ActualActualISDA
    calendar = ql.TARGET()

    JumpQuotes = ql.QuoteHandleVector()
    JumpDates = ql.DateVector()
    accuracy = 1e-12
    
    def __init__(self, curvedata=None, curvedate=None, datadivisor=1.000,
                     settledays=2, setIborIndex=True, label=None):
        TermStructureModel.__init__(self, datadivisor, settledays, label)

        self.ratehelpers = None
        self.instruments_ = ql.RateHelperVector()
        self.setIborIndex = setIborIndex
                        
        if curvedata:
            self.update(curvedata, curvedate)
                                    
    def update(self, curvedata, curvedate=None, datadivisor=None):
        "creates ratehelpers object"
        if datadivisor:
            self.datadivisor = datadivisor
            
        curvedata = self.cleancurvedata(curvedata)
        
        if self.ratehelpers:
            self.ratehelpers.update(curvedata)
        else:
            self.ratehelpers = HelperWarehouse(curvedata.keys(), 
                                               curvedata.values(), 
                                               self.datadivisor)
        if not curvedate:
            curvedate = ql.Settings.instance().getEvaluationDate()
            
        self.curvedate = self.calendar.adjust(ql.bgDate(curvedate))
        self.settlement = self.calendar.advance(self.curvedate, 
                                                self.settledays, ql.Days)
                                                
        ql.Settings.instance().setEvaluationDate(self.curvedate)
        
        if self.setIborIndex:
            SwapRate.setLibor(self.settlement, 
                              self.curvedata[SwapRate.floatingLegIndex]/self.datadivisor)

        if not self.upToDate:
            self.curve_(self.ratehelpers.vector)

        return self

    def reset(self):
        if self.ratehelpers:
            self.ratehelpers = None
            self.curve = None
            return True
        return False
          
    def checkcurve(self):
        datakeys = self.curvedata.keys()
        datakeys.sort(key = lambda x: ql.Tenor(x).term)
        
        check_ = []
        for k in datakeys:
            check_.append((k, (self.tenorpar(k)-self.curvedata[k]/self.datadivisor)*100.0))
        return check_
      
    def curve_(self, ratehelpervector):
        "calc curve"

        PYC = ql.PiecewiseFlatForward
        curve = PYC(self.settledays, self.calendar, ratehelpervector, 
                    ql.ActualActualISDA,
                    self.JumpQuotes, self.JumpDates, self.accuracy)

        curve.enableExtrapolation()   
        self.curve.linkTo(curve)
        self.upToDate = True
    
    def __str__(self):
        if self.label:
            return self.label
        else:
            return "SimpleCurve"
    
class DiscountCurve(TermStructureModel):
    '''
    Fits a set of pure discount factors to a term structure.
    '''
    def __init__(self, curvedata=None, settledays = 2,
                 interp = ql.LogLinear(), datadivisor=1.0, label=None):
    
        TermStructureModel.__init__(self, datadivisor, settledays, label)
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

        curve = DiscountCurve(datevector, discountvector,
                              self.daycount, self.calendar, 
                              self.interp)
        curve.enableExtrapolation()   
        self.curve.linkTo(curve)

class SpreadedCurve(TermStructureModel):
    '''
    Create a termstructure object spread from a reference
    Value types:
        "F" = ForwardSpreadTermStructure
        "Z" = ZeroSpreadedTermStructure
    '''
    spreadedTermStructure_ = {"F": ql.ForwardSpreadedTermStructure,
                              "Z": ql.ZeroSpreadedTermStructure }
              
    def __init__(self, termstructure, spread=0.0, type="Z"):
    
        TermStructureModel.__init__(self, termstructure.datadivisor, 
                                          termstructure.settledays, 
                                          termstructure.label)
        self.spreadType = type                                  
        self.spread_ = ql.SimpleQuote(spread)
        curve = self.spreadedTermStructure_[type](termstructure.handle,
                                                  ql.QuoteHandle(self.spread_))
        curve.enableExtrapolation()   
        self.curve.linkTo(curve)

    def getSpread(self):
        return self.spread_.value()
    
    def setSpread(self, newvalue):
        self.spread_.setValue(newvalue)
        
    spread = property(getSpread, setSpread)    
    
        
class RatioBasisCurve(object):
    pass