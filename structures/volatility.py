"""volatility.py

Structures to facilitate interpolating vol curves, surfaces, etc.

"""

import bgpy.QL as ql

from interpcurve import InterpCurve

        
class VolCurve(InterpCurve):
    '''
    Represents a volatility curve for the given expiry.
    Curve data is given for final maturity tenor--so that vol 
    is for "x tenor, non-call y" (not "x expiry into y").
    '''
    def __init__(self, curvedata=None, expiry="10Y", datadivisor=1.000):
        self.expiry = expiry
        
        InterpCurve.__init__(self, curvedata, datadivisor)