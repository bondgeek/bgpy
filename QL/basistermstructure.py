
import bgpy.QL as ql
from termstructurehelpers import HelperWarehouse, SwapRate

from math import floor

from termstructure import *


class basishelper(object):
    calendar = ql.TARGET()
    muniLegDayCount = ql.ActualActualISDA
    
    basisFrequency =  ql.Quarterly
    basisTenor = ql.Period(ql.Quarterly)
    businessDayAdjustment =  ql.ModifiedFollowing
    liborLegDayCount = ql.Actual360()
    
    def __init__(self, tenor, parratio, divisor=1.000):
        self.tenor = tenor  # maturity as tenorstring
        self.parratio = parratio / divisor
    
        self.length, self.units = ql.Tenor(self.tenor)
        
        #term in number of pay periods
        self.term = ql.Tenor(self.tenor).numberOfPeriods(self.basisFrequency)
        self.nterm = int(self.term)
        self.tail = self.term - self.nterm
        if self.nterm >= 1:
            assert self.tail < 1e-7, "helper tenor must be integer number of periods"
        else:
            self.ratio = self.parratio 
        
class munibasistermstructure(TermStructureModel):
    '''
    create a list of discount factors which replicate the input market levels.
    '''
    calendar = ql.TARGET()
    depo_daycount = ql.ActualActualISDA
    term_daycount = ql.Thirty360()
    daycount = ql.ActualActualISDA
    
    def __init__(self, disc_termstr, curvedata, 
                     settledays=2, calendar=TARGET(), frequency=Quarterly, 
                     interp = LogLinear(), datadivisor=100.0, label=None):
        
        TermStructureModel.__init__(self, datadivisor, settledays, label)
        
        self.curvedate = disc_termstr.curvedate
        self.settlement = disc_termstr.referenceDate()
        
        self.interp = interp
        self.disc_termstr = disc_termstr
        
        curvedata = self.cleancurvedata(curvedata)
        
        cdata = [(k, curvedata[k]) for k in curvedata]

        muniswap_helpers = [basishelper(tnr, ratio/100.0) for tnr, ratio in cdata]

        bootstrap = RatioBootstrap(muniswap_helpers, disc_termstr, 
                                   self.settlement, self.calendar)
        
        datevector = bootstrap.keys()
        datevector.sort(key=lambda x: x.serialNumber())
        
        discountvector = DoubleVector([float(bootstrap[d]) for d in datevector])        
        datevector = DateVector(datevector)
        
        self.curve = DiscountCurve(datevector, discountvector,
                              self.daycount, self.calendar, self.interp)
                              
        self.curve.enableExtrapolation()   
        
            
    def tenorParRatio(self, tenor):
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
        
        paydates = [advance(self.settlement, n, Months) for n in range(0, tnrlen, 3)]
        paydates = zip(paydates[:-1], paydates[1:])
        
        pvals = [(discount(dt, True), 
                  fwdratio(d0, dt), fwdlbr(d0, dt), munidisc(dt), d0, dt)
                 for d0, dt in paydates]

        sum1 = sum([df * fwdlbr for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        sum2 = sum([df * fwdmuni for df, fwdmuni, fwdlbr, mdf, d0, dt in pvals])
        
        return sum2/sum1

def RatioBootstrap(instruments, disc_termstr, settlement, calendar=ql.TARGET()):
    #make sure instruments are sorted in increasing order
    #TODO: should also check that instruments are consistent, frequency, daycount, etc.

    instruments.sort(key=lambda x: x.term)
    longestIns = instruments[-1]
    maturity = calendar.adjust(calendar.advance(settlement, 
                                                longestIns.length, 
                                                longestIns.units))
    # TODO: don't use Schedule unless you have to  
    sched = Schedule(settlement, maturity, 
                    longestIns.basisTenor, 
                    calendar, 
                    ql.ModifiedFollowing, ql.ModifiedFollowing, 
                    ql.Forward, 0)
    
    pvalue_dict = {settlement: 1.0} # will contain all discount factors for passing to termstructure
    prev_disc_lbr = 0.0
    prev_disc_muni = 0.0
    prevInsMty = settlement
    prev_mty = settlement
    prev_n = 0
    prev_ratio = 0.0
    prev_muniPvalue  = 1.0
    for instrN in instruments:
        
        if instrN.nterm < 1:
            maturity = calendar.advance(settlement, 
                                             instrN.length, instrN.units)
            lbr_df = disc_termstr.discount(maturity)
            lbr_fwd = disc_termstr.forwardPayment(settlement, 
                                                  maturity)
            munidays = instrN.muniLegDayCount.yearFraction(settlement, 
                                                           maturity)                                           
            muni_Pvalue = 1./(1.+lbr_df * lbr_fwd * munidays)
            pvalue_dict[maturity] = muni_Pvalue
            continue
        else:
            thissched = [sched.date(n+1) for n in range(prev_n, instrN.nterm)]

            increment_values = []
            increment_discounts = 0.0
            alpha_factor = 0.0
            for maturity in thissched:
                time_increment = instrN.muniLegDayCount.yearFraction(prevInsMty, 
                                                                maturity)
                lbr_df = disc_termstr.discount(maturity)
                lbr_fwd = disc_termstr.forwardPayment(prev_mty, 
                                                      maturity) 
                increment_values.append((time_increment,
                                         lbr_df,
                                         lbr_fwd, maturity))
                                         
                increment_discounts += lbr_df * lbr_fwd                        
                prev_disc_lbr += lbr_df * lbr_fwd
                alpha_factor += float(time_increment)*lbr_df*lbr_fwd
                
                prev_mty = maturity

            alpha = (instrN.parratio * prev_disc_lbr
                    - prev_ratio * increment_discounts 
                    - prev_disc_muni) / alpha_factor
            
            prev_dt = prevInsMty
            for t_, df, fwd, dt in increment_values:
                ratio = prev_ratio + alpha * t_
                prev_disc_muni += df *fwd * ratio
                prev_n += 1
                munifrac = instrN.muniLegDayCount.yearFraction(prev_dt, dt)
                liborfrac = instrN.liborLegDayCount.yearFraction(prev_dt, dt)
                muni_Pvalue = prev_muniPvalue/(1.+ fwd * ratio)
                pvalue_dict[dt] = muni_Pvalue
                prev_muniPvalue = muni_Pvalue
                
        prev_ratio = ratio
        prevInsMty = maturity
    
    return pvalue_dict
