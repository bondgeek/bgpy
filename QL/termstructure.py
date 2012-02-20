'''
Term Structure Classes--a set of wrappers around QuantLib

Created on May 26, 2010
@author: bartmosley
'''
import bgpy.__QuantLib as ql

from bgpy.QL.bgdate import toDate
from bgpy.QL.tenor import Tenor
from bgpy.math.solvers import Secant
from termstructurehelpers import HelperWarehouse, SwapRate
        
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
        self.discount = self.curve.discount
        self.zeroRate = self.curve.zeroRate
        self.referenceDate = self.curve.referenceDate
            
    def setDates(self, curvedate=None):
        '''Set curvedate and settlement date.
        If no curvedate is passed in, used QuantLib Settings
        
        '''
        adjust = ql.TARGET().adjust

        if not curvedate:
            if not self.curvedate:
                self.curvedate_ = ql.Settings.instance().getEvaluationDate()  
        else:
            self.curvedate_ = toDate(curvedate)
            ql.Settings.instance().setEvaluationDate(adjust(self.curvedate))
        
        self.settlement_ = self.calendar.advance(adjust(self.curvedate), 
                                                self.settledays, 
                                                ql.Days)
        return self.settlement_

    @property
    def curvedate(self):
        return getattr(self, "curvedate_", None)
    
    @property
    def settlement(self):
        return self.settlement_
                
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
        begDate, endDate = toDate(begDate), toDate(endDate)
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
        begDate, endDate = toDate(begDate), toDate(endDate)
        yfrac = dc.yearFraction(begDate, endDate)
        return (self.forwardDepo(begDate, endDate, dc) + spread) * yfrac
        
    def bondpar(self, matDate, dayCount=ql.Thirty360(), frequency=ql.Semiannual):
        '''
        Returns par rate for given maturity
        '''
        matDate = toDate(matDate)
        
        discount = self.curve.discount              #function calls
        advance = ql.TARGET().advance               #function calls
        settle = self.curve.referenceDate()
        
        freq = float(ql.freqValue(frequency))
        term = freq * dayCount.yearFraction(settle, matDate)
        
        nper = int(term)
        frac = term - nper
        
        n0 = 1 if abs(frac) < 1e-12 else 0
        
        # second argument to discount allows extrapolation
        pvals = [discount((float(n)+frac)/freq, True) for n in range(n0, nper+1)]
        
        c = 2.0 * (1.0 - pvals[-1]) / sum(pvals)
        ai = lambda f, c: (1.-frac) * c if frac > 0.0 else 0.0
        value = lambda x: ((1. + ai(frac, x)) - pvals[-1]) / sum(pvals) - x
        
        return Secant(c, c + .001, value, 0.0) * 2.0
        
    def tenorpar(self, tenor):
        '''
        Returns par rate for given tenor -- e.g., termstr.tenorpar('10Y') 
        '''
        discount = self.curve.discount              #function calls
        advance = ql.TARGET().advance         #function calls
        tnr = Tenor(tenor)
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
    
    def pfile(self, num=360, timeunit=ql.Months):
        discount = self.curve.discount
        advance = lambda x: ql.TARGET().advance(self.curve.referenceDate(), 
                                                x, timeunit)
        return dict([(n, discount(advance(n))) for n in range(num+1)])
    
    def scenarios(self, shock=0.0001, spreadType="Z"):
        self._shift_up = SpreadedCurve(self, -1.*shock, spreadType)
        self._shift_dn = SpreadedCurve(self, shock, spreadType)
        return True
    
    def clear_scenarios(self):
        if hasattr(self, "_shift_up"):
            delattr(self, "_shift_up")
        if hasattr(self, "_shift_dn"):
            delattr(self, "_shift_dn")
    
    @property
    def shift_up(self):
        if not hasattr(self, "_shift_up"):
            self.scenarios()
        return self._shift_up

    @property
    def shift_dn(self):
        if not hasattr(self, "_shift_dn"):
            self.scenarios()
        return self._shift_dn

    def parsensitivity(self, term):
        '''What is the par shift for a 1bp z-shift for a given term?
        Takes either tenor, e.g. '10Y', or maturity date
        '''
        if type(term) == str:  # must be a tenor
            func = "tenorpar"
        else:
            func = "bondpar"
        
        v_dn = getattr(self.shift_dn, func)(term)
        v_up = getattr(self.shift_up, func)(term)
        
        return 10000.*(v_dn - v_up) / 2.
            
    def update(*args):
        '''
        Must be over-loaded in sub-classes.
        '''
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
        else:
            self.setDates(curvedate)

    def update(self, curvedata, curvedate=None, datadivisor=None):
        "creates ratehelpers object"
        if datadivisor:
            self.datadivisor = datadivisor

        self.setDates(curvedate)
            
        curvedata = self.cleancurvedata(curvedata)
        if self.setIborIndex:
            SwapRate.setLibor(self.settlement, 
                              self.curvedata[SwapRate.floatingLegIndex]/self.datadivisor)

        if self.ratehelpers:
            self.ratehelpers.update(curvedata)
        else:
            self.ratehelpers = HelperWarehouse(curvedata.keys(), 
                                               curvedata.values(), 
                                               self.datadivisor)                                       
        self.curve_(self.ratehelpers.vector)

        self.clear_scenarios()

        return self
  
    def curve_(self, ratehelpervector):
        "calc curve"

        curve = ql.PiecewiseFlatForward(
                    self.settlement, ratehelpervector, 
                    ql.ActualActualISDA,
                    self.JumpQuotes, self.JumpDates, self.accuracy)

        curve.enableExtrapolation()   
        self.curve.linkTo(curve)    
        
    def reset(self):
        '''
        Returns True if existing curve is reset, otherwise False
        '''
        if self.ratehelpers:
            SwapRate.clearIndex()
            self.ratehelpers = None
            self.curve = None
            return True
        return False

    def __str__(self):
        if self.label:
            return self.label
        else:
            return "<SimpleCurve>"
    
class ZCurve(TermStructureModel):
    '''
    Fits a set of pure discount factors to a term structure.
    '''
    def __init__(self, curvedata=None, settledays = 2,
                 interp = ql.LogLinear(), datadivisor=1.0, label=None):
        TermStructureModel.__init__(self, datadivisor, settledays, label)
        self.interp = interp
        
        if curvedata:
            self.update(curvedata, datadivisor)
    
    def setDates(self, settle):
        '''Set curve evaluation and settlement dates.
        Overides base class
        
        '''
        self.settlement_ = settle
        self.curvedate_ = ql.TARGET().advance(self.settlement_, 
                                              -1*self.settledays, 
                                              ql.Days)
                                              
        ql.Settings.instance().setEvaluationDate(self.curvedate)
        
        return self.settlement_
        
    def update(self, curvedata, datadivisor=1.0):
        curvedata = self.cleancurvedata(curvedata)

        datevector = curvedata.keys()
        datevector.sort(key=lambda x: x.serialNumber())
        
        self.setDates( datevector[0] )
                                 
        discountvector = ql.DoubleVector([float(curvedata[d]) for d in datevector])        

        curve = ql.DiscountCurve(ql.DateVector(datevector), discountvector,
                                 self.daycount, self.calendar, self.interp)
        curve.enableExtrapolation()
        
        self.curve.linkTo(curve)
    
    def from_pfile(self, settle, curvedata, timeunit=ql.Months, datadivisor=1.0):
        advance = lambda x: self.calendar.advance(settle, x, timeunit)
        pfile_ = dict( [(advance(k), curvedata[k]) for k in curvedata] )
        
        self.update(pfile_, datadivisor)
        
    def __str__(self):
        if self.label:
            return self.label.join(("<", ">"))
        else:
            return "<ZCurve>"

class SpreadedCurve(TermStructureModel):
    '''SpreadedCurve(termstructure, spread=0.0, type="Z")
    
    Create a termstructure object spread from a reference
    Value types:
        "F" = ForwardSpreadTermStructure
        "Z" = ZeroSpreadedTermStructure
        
    '''

    def __init__(self, termstructure, spread=0.0, type="Z"):
        self.spreadedTermStructure_ = {"F": ql.ForwardSpreadedTermStructure,
                                       "Z": ql.ZeroSpreadedTermStructure }
                      
        TermStructureModel.__init__(self, termstructure.datadivisor, 
                                          termstructure.settledays, 
                                          termstructure.label)
                                          
        # use curve/settle date properties from origin termstructure
        self.curvedate_ = termstructure.curvedate
        self.settlement_ = termstructure.settlement
        
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
    
    def __str__(self):
        if self.label:
            return self.label.join(("<", ">"))
        else:
            return "<SimpleCurve>"
            
    spread = property(getSpread, setSpread)    
