import bgpy.QL as ql

import bgpy.QL.termstructure as ts
from MarketData.Bloomberg import BLPSync

BLPS = lambda x, f_: BLPSync(x, f_, timeout=5000)

class bbgblp(object):
    '''
    Executes a Bloomberg BLP call, either synchronous or straight BLP.
    
    hdrrange = range with field headers.
    '''
    def __init__(self, cusip, hdrrange, bbgkey = "Muni", 
                 bbgcall=BLPSync, timeout=5000):
        self.record = {'CUSIP': cusip}
        
        self.newrec = bbgcall(" ".join((cusip, bbgkey)), hdrrange, hdrrange, 
                         timeout=timeout)
        hdr = [fld for fld in hdrrange]
        
        self.record.update( dict(zip(hdr, 
                                     self.newrec)) )
        
    def __str__(self):
        return "".join((self.record['CUSIP'], ":"))

    def __repr__(self):
        return self.__str__()
    
    def __call__(self, key=None):
        if key:
            return self.record.get(key, None)
        else:
            return self.record


def bbg_icvs(tenor_list, settle, ticker="S0023D", key="BLC2 Curncy"):
    '''Retrieves icvs curve from bbg and returns related termstructure object'''
    datelist = [settle]
    discountlist = [1.0]
    for tenor in tenor_list:
        bbgstring = " ".join([ticker, tenor, key])
        maturity = ql.bbg_date(BLPS(bbgstring, "Maturity"))
        discount = BLPS(bbgstring, "PX_MID")
        datelist.append(maturity)
        discountlist.append(discount)
        
    curvedata = dict(zip(datelist, discountlist))
    return ts.ZCurve(curvedata)

class bbgVolSurface(object):
    '''
    Takes a range of tickers creates a dictionary keyed by expry and 'into' tenor.
    interp(expry, term) -- interpolates along the surface.
    '''
    def __init__(self, tickers, volExprys, volTenors, update=False):
        if not hasattr(self, "Surface") or update:
            self.Surface = self.update(tickers, volExprys, volTenors)

    def update(self, tickers, volExprys, volTenors):
            Surface = {}
            tnrs = [tnr for tnr in volTenors]
            vol_list = lambda col: [x for x in col]
            
            for numCol in range(len(tnrs)):
                col_dict = {}
                vols_tickers = [" ".join([x, "Curncy"]) for x in tickers[numCol+1]]
                vols = [BLPS(tkr, "PX_MID") for tkr in vols_tickers]
                for n in range(len(volExprys)):
                    if not vols[n] == "N.A.":
                        col_dict[volExprys[n+1]] = vols[n]
                Surface[tnrs[numCol]] = col_dict
            
            return Surface    
    
    def interp(self, expry, term):
        ''' expry into term'''
        tenors = self.Surface.keys()
        tenors.sort()
        
        t0 = [x for x in tenors if x <= term]
        t0 = tenors[0] if t0 is None else max(t0)
        t1 = [x for x in tenors if x >= term]
        t1 = tenors[-1:] if t1 is None else min(t1)
        tenors = [(t0, self.Surface[t0]), (t1, self.Surface[t1])]
        
        vols = {}
        
        for tnr in tenors:
            tnum, tdict = tnr
            exprys = tdict.keys()
            exprys.sort()
            e0 = [x for x in exprys if x <= expry]
            e0 = exprys[0] if t0 is None else max(e0)
            v0 = tdict[e0]
            e1 = [x for x in exprys if x >= expry]
            e1 = exprys[-1:] if t0 is None else max(e1)
            v1 = tdict[e1]
            vols[tnum] = v0 + (v1-v0)*(e1 - expry)/(e1-e0)
        
        v0 = vols[t0]
        v1 = vols[t1]
        volx = v0 + (v1-v0)*(t1 - term)/(t1-t0)
        return volx
        