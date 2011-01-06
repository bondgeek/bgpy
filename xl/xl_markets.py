from pyxll import xl_func

from bgpy.QL import SimpleCurve

# global dictionary to 
_TermStructures = {}


@xl_func("string[] tenors, float[] curve, string id :str", category="bgpy")
def curve(tenors, curve, id="crv"):
    """Assign yield curve values. """
    
    global _TermStructures
    
    if id not in _TermStructures:
        _TermStructures[id] = SimpleCurve()
    
    if len(tenors) != len(curve):
        return None
    
    tlist = tuple([t[0] for t in tenors])
    clist = tuple([c[0] for c in curve])
    
    curvedata = dict(zip(tlist, clist))
    
    _TermStructures[id].update(curvedata)
    
    return id

@xl_func("string id, string tenor :float", category="bgpy")
def tenorpar(id, tenor):
    """tenorpar"""
    
    if id in _TermStructures:
        return _TermStructures[id].tenorpar(tenor)
    
    return -1
    
    
    