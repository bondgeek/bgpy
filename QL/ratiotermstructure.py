
import bgpy.QL as ql
from termstructurehelpers import HelperWarehouse, SwapRate

from math import floor

from termstructure import TermStructureModel

class RatioHelper(object):
    '''
    Used to bootstrap ratio basis curve
    '''
    calendar = ql.TARGET()
    muniLegDayCount = ql.ActualActualISDA
    
    basisTenor = ql.Tenor('3M')
    basisFrequency =  ql.Quarterly
    
    businessDayAdjustment =  ql.ModifiedFollowing
    liborLegDayCount = ql.Actual360()
    
    def __init__(self, tenor):
        self.tenor = ql.Tenor(tenor)
        
        # term in number of pay periods
        self.term = self.tenor.term
        self.nterm = self.tenor.numberOfPeriods(self.basisFrequency)
        self.tail = self.term - self.nterm
    
    def getHelper(self, parratio, divisor=1.0):
        if hasattr(parratio, "value"):  
            self.parratio_ = parratio
        else:
            self.parratio_ = ql.SimpleQuote(parratio/divisor)
        return (self.parratio_, self)
                
    @property
    def parratio(self):
        return getattr(self.parratio_, "value", lambda : self.parratio_)()
        
    def maturity(self, settlement):
        return self.tenor.advance(settlement)
    
    def schedule(self, settlement):    
        "instrument schedule for settlement"
        return self.basisTenor.schedule(settlement, self.maturity(settlement), 
                                        self.businessDayAdjustment,
                                        self.calendar)
    def qlSchedule(self, settlement):
        '''
        Deprecated.
        '''                                        
        return ql.Schedule(settlement, self.maturity(settlement), 
                            self.basisTenor.qlPeriod, 
                            self.calendar, 
                            self.businessDayAdjustment, self.businessDayAdjustment, 
                            ql.Forward, 0)
    
        
class RatioCurve(TermStructureModel):
    '''
    create a list of discount factors which replicate the input market levels.
    '''
    daycount = ql.ActualActualISDA
    
    def __init__(self, disc_termstr=None, curvedata=None, 
                     settledays=2, calendar=ql.TARGET(), frequency=ql.Quarterly, 
                     interp = ql.LogLinear(), datadivisor=1.000, label="RatioCurve"):
        
        TermStructureModel.__init__(self, datadivisor, settledays, label)
        
        self.calendar = calendar
        self.frequency = frequency
         
        self.interp = interp
        
        self.muniswap_helpers = None
        if curvedata:
            self.update(disc_termstr, curvedata)
    
    def __repr__(self): 
        return self.label.join(("<", ">"))
         
    def update(self, disc_termstr, curvedata):
        self.disc_termstr = disc_termstr

        self.curvedate_ = disc_termstr.curvedate
        self.settlement_ = disc_termstr.referenceDate()
        
        curvedata = self.cleancurvedata(curvedata)
        
        if self.muniswap_helpers:
            self.muniswap_helpers.update(curvedata)
        else:
            self.muniswap_helpers = HelperWarehouse(curvedata.keys(), 
                                                    curvedata.values(), 
                                                    self.datadivisor,
                                                    helper=RatioHelper)
                                               
        bootstrap_ = self.bootstrap(self.muniswap_helpers.list)
        
        datevector = bootstrap_.keys()
        datevector.sort(key=lambda x: x.serialNumber())
        
        self.discountvector = ql.DoubleVector([float(bootstrap_[d]) for d in datevector])        
        self.datevector = ql.DateVector(datevector)
        
        curve_ = ql.DiscountCurve(self.datevector, self.discountvector,
                                  self.daycount, self.calendar, self.interp)
                              
        curve_.enableExtrapolation()   
        self.curve.linkTo(curve_)
    
    def forwardRatio(self, begdate, enddate):
        '''
        Examples:
            ratiocurve.forwardRate(firstDate, secondDate)
            ratiocurve.forwardRate(firstDate, '3M')
        
        '''
        if type(enddate) == str:
            enddate = ql.Tenor(enddate).advance(begdate, ql.ModifiedFollowing)
            
        return self.forwardPayment(begdate, enddate)/ self.disc_termstr.forwardPayment(begdate, enddate)
                
    def parRatio(self, tenor):
        '''
        return par fixed ratio
        '''
        lbrcrv = self.disc_termstr
        fwdratio = self.forwardPayment
        fwdlbr = lbrcrv.forwardPayment
        munidisc = self.discount
        discount = lbrcrv.discount              #function calls
        advance = self.calendar.advance         #function calls
        tnr = ql.Tenor(tenor)
        if tnr.unit != 'Y':
            zeroRate = self.zeroRate
            enddt = ql.Tenor(tenor).advance(self.settlement)
            munirate =  self.forwardDepo(self.settlement, enddt, ql.Actual360())
            liborrate = lbrcrv.forwardDepo(self.settlement, enddt, ql.Actual360())
            return munirate / liborrate

        tnrlen = tnr.length * 12 + 3
        
        paydates = [advance(self.settlement, n, ql.Months, ql.ModifiedFollowing) for n in range(0, tnrlen, 3)]
        paydates = zip(paydates[:-1], paydates[1:])
        
        pvals = [(discount(dt, True), 
                  fwdratio(d0, dt), fwdlbr(d0, dt), munidisc(dt), d0, dt)
                 for d0, dt in paydates]

        sum1 = sum([df * fwdlbr for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        sum2 = sum([df * fwdmuni for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        
        return sum2/sum1
    
    def maturityRatio(self, maturity):
        maturity = ql.toDate(maturity)
        nYears = ql.ActualActual().yearFraction(self.referenceDate(), maturity)
        
        y0 = int(nYears)
        y1 = y0 + 1
        f = nYears - float(y0)
        
        r0 = self.parRatio("%s" % y0) if y0 > 0 else self.parRatio('1W')
        r1 = self.parRatio("%s" % y1)
        
        ratio = r0 * (1-f) + r1 * f
        
        return ratio
    
    def bootstrap(self, instruments):
        '''
        bootstrap ratios, assuming linear forward ratios
        r = r0 + a * t
        where 
            r is the ratio at time t
            r0 is the last know ratio, at time zero
            
        Then, if R[n] is the fixed ratio for period n,
        
            R[n] * Sum(i=1, n) f[i] * d[i] = Sum(i=1, n) r[i] * f[i] * d[i]
        
        or,
        
            R[n] * Sum(i=1, n) f[i] * d[i] = Sum(i=1, n) (r0 + a[n] * t[i]) * f[i] * d[i]
        
        This is an equation in one unknown, a[n] 
        '''
        #make sure instruments are sorted in increasing order
        #TODO: should also check that instruments are consistent, frequency, daycount, etc.
        instruments.sort(key=lambda x: x.term)
        
        sched = instruments[-1].schedule(self.settlement)

        # will contain all discount factors 
        pvalue_dict = {self.settlement: 1.0} 
        
        # initialize cummulators, etc.
        prev_disc_lbr = prev_disc_muni = ratio = prev_ratio = 0.0
        prev_n = 0
        prevInsMty = prev_mty = self.settlement
        prev_muniPvalue  = 1.0
        for instrN in instruments:
            
            if instrN.nterm <= 1:
                
                ratio = instrN.parratio
                maturity = instrN.maturity(self.settlement)
                
                lbr_fwd = self.disc_termstr.forwardPayment(self.settlement, maturity) 
      
                pvalue_dict[maturity] = 1./(1.+ ratio * lbr_fwd)
                prev_mty = maturity
                
            elif ratio == 0.0:
                # if the first instrument is longer than one period, assume  
                # flat ratio curve to the first maturity
                ratio = instrN.parratio
    
                for maturity in [sched[n+1] for n in range(instrN.nterm)]:
                    lbr_df = self.disc_termstr.discount(maturity)
                    lbr_fwd = self.disc_termstr.forwardPayment(prev_mty, maturity)
                    
                    prev_disc_lbr += lbr_df * lbr_fwd 
                    prev_disc_muni += lbr_df * lbr_fwd * ratio
                    
                    pvalue_dict[maturity] = prev_muniPvalue/(1. + lbr_fwd * ratio)
                    
                    prev_n += 1
                    
                    prev_mty = maturity
                    prev_muniPvalue = pvalue_dict[maturity]
                    
                          
            else:    
                increment_values = []
                increment_discounts = alpha_factor = 0.0
                
                # step through incremental cashflows for this instrument
                prev_mty = prevInsMty
                prev_muniPvalue = pvalue_dict.get(prev_mty, prev_muniPvalue)
                
                for maturity in [sched[n] for n in range(prev_n, instrN.nterm)]:
                    time_increment = instrN.muniLegDayCount.yearFraction(prevInsMty, 
                                                                         maturity)
                    lbr_df = self.disc_termstr.discount(maturity)
                    lbr_fwd = self.disc_termstr.forwardPayment(prev_mty, maturity) 
                    
                    increment_values.append((time_increment, lbr_df, lbr_fwd, maturity))
                    
                    prev_disc_lbr += lbr_df * lbr_fwd                         
                    increment_discounts += lbr_df * lbr_fwd
                    alpha_factor += float(time_increment)*lbr_df*lbr_fwd
                    prev_mty = maturity
    
                alpha = (instrN.parratio * prev_disc_lbr
                        - prev_ratio * increment_discounts 
                        - prev_disc_muni) / alpha_factor
                
                for t_, df, fwd, dt in increment_values:
                    ratio = prev_ratio + alpha * t_
                    prev_disc_muni += df * fwd * ratio
                    
                    prev_n += 1
                    
                    pvalue_dict[dt] = prev_muniPvalue/(1.+ fwd * ratio)                    
                    prev_muniPvalue = pvalue_dict[dt]
                    
            prev_ratio = ratio
            prevInsMty = maturity
    
        return pvalue_dict
