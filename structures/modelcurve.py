
import bgpy.QL as ql

from scales import Scale
from volatility import VolCurve

class ModelScale(Scale):
    '''
    Inputs:
    termstructure 
    curvedata ~ {tenor: coupon, bondyield, spread, ratio, vol}
    curvedate=None
    model = ql.BlackKarasinski
    
    '''
    def __init__(self, termstructure, curvedata=None, curvedate=None,
                 call=("10Y", 100.0),
                 model=ql.BlackKarasinski):
        
        self.scalecoupons = dict([(t, curvedata[t][0]) for t in curvedata])
        
        Scale.__init__(self, self.scalecoupons, curvedate, call=call,
                       coupon="par")
            
        self.spreaddata = [(t, curvedata[t][2:]) for t in curvedata]
        self.spreaddata = dict(self.spreaddata)
        
        self.values = self.updateBondValues(termstructure, self.spreaddata)
        
        self.curvedata = {}                                
        for tenor in self.bonds:
            prc = self.values[tenor].oasPrice
            cpn = self.bonds[tenor].coupon
            mty = self.bonds[tenor].maturity
            
            self.curvedata[mty] = (cpn, prc)
        
        self.termstructure = ql.SimpleCurve(setIborIndex=False)
        self.termstructure.update(self.curvedata, self.curvedate)
        
        self.callfeature_ = call
        self.ussv = {}  
        
        for tenor in self.bonds: 
            thisbond = self.bonds[tenor] 
            prc = thisbond.toPrice(curvedata[tenor][1])
            vol = thisbond.assetSwap().solveImpliedVol(self.termstructure,
                                                       prc,
                                                       0.,
                                                       1.)
              
            self.ussv[tenor] = vol.vol
        
        self.volCurve = VolCurve(self.ussv, datadivisor=1.0)
        
        