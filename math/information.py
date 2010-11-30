from math import log
from bondgeek.inference.classifiers import levels

log2 = lambda x: log(x,2)

def hlog(p):
    if p:
        return p * log(p,2) 
    else:
        return 0.

H = lambda plist: - sum(hlog(p) for p in plist)

def valid_prob(plist):
    return (all([(x >= 0.0 and x <= 1.0) for x in plist]) and
            sum(plist) == 1.0)

def entropy(data):
    if len(data) > 1:
        lvls = levels(data)
        n = float(sum(lvls[0]))
        h = -sum(hlog(float(value)/n) for value in lvls[0] )
    else:
        h = 0.
    return h

def relentropy(data1,data2):
    ''' relative entropy of data2 given data1 '''
    pairs = zip(data1,data2)
    levels1 = levels(data1)
    n1 = float(sum(levels1[0]))
    h=[]
    for b, lev in zip(levels1[0],levels1[1]):
        p = float(b)/n1
        hx = entropy( [ x[1] for x in pairs if x[0] == lev] )
        h.append( hx*p )
    return sum(h)

def pairentropy(data, onvalue=None):
    if onvalue is None:
        d0 = [d[0] for d in data]
        d1 = [d[1] for d in data]
    else:
        d0 = [d[0] for d in data if d[0] == onvalue]
        d1 = [d[1] for d in data if d[0] == onvalue]

    e0 = entropy(d0)
    e1 = entropy(d1)
    re01 = relentropy(d0,d1)
    re10 = relentropy(d1,d0)
    return(e0,e1,re01,re10)
    

if __name__=="__main__":
    #test cases
    import random
    L=[]
    for i in range(10000):
        L.append(random.randint(0,10))

    Txt = '''Dead is she? 'Fraid so.  What a blow for her'''
    classify1 = levels[Txt]
    classify2 = levels[L]
