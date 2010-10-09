'''
Functions cribbed and modified from GVR's article

Python Patterns -- An Optimization Anecdote
http://www.python.org/doc/essays/list2str.html
'''

__all__ = ['timing', 'timing2', 'fcompare', 'fcompare2', 'code_timer']

import time

# Guido's timing function
def timing(f, n, a):
    '''timing(f, n, a) runs function, f, 10*n times using args, a'''
    print(f.__name__)
    r = range(n)
    t1 = time.clock()
    for i in r:
        f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a); f(a)
    t2 = time.clock()
    print(round(t2-t1, 3))
    return  (f.__name__, round(t2-t1, 3))

def timing2(f, n, a):
    r = range(n)
    t1 = time.clock()
    for i in r:
        f(*a); f(*a); f(*a); f(*a); f(*a); f(*a); f(*a); f(*a); f(*a); f(*a)
    t2 = time.clock()
    return  (f.__name__, round(t2-t1, 3))
    
def fcompare2(f1, f2, n, a):
    '''fcompare2(f1, f2, n, a) -> comparison'''
    timef1 = timing(f1,n,a)
    timef2 = timing(f2,n,a)
    print("%s:  %s secs"%timef1)
    print("%s:  %s secs"%timef2)
    print("%s vs %s %.3f%%" % (timef2[0], timef1[0], timef2[1]/timef1[1]))

def fcompare(flist, n , arg):
    '''
    fcompare(flist, n , arg) -> comparison
    '''
    import operator
    times = []
    for f in flist:
        times.append((f.__name__, timing2(f,n,arg)[1]))
    times.sort(key=operator.itemgetter(1))
    for f in times:
        print("%s:   %s seconds" % (f[0], f[1]))
    return times


def code_timer(code1, code2, n):
    
    r = range(n)
    t1 = time.clock()
    exec(code1)
    t2 = time.clock()
    elapsed1 = round(t2-t1, 3)

    t1 = time.clock()
    exec(code2)
    t2 = time.clock()
    elapsed2 = round(t2-t1,3)

    diagnostic = "code1: %.3f, code2: %.3f" %(elapsed1, elapsed2)

    return diagnostic

if __name__ == "__main__":
    import random

    #code_timer example

    c1 = ";".join(["TList = [random.random() for i in range(10000)]",
                   "TList.sort(reverse = True)", 
                   "new1 = TList", 
                   "l1 = len(new1)"])
    
    c2 = ";".join(["TList2 = [random.random() for i in range(10000)]",
                   "new2 = sorted(TList2, reverse = True)", 
                   "l2 = len(new2)"])
        
    # timings example
    # some functions to check if an object is a sequence
    def isit(obj):
        try:
            it = iter(obj)
            return True
        except TypeError:
            return False

    isit2 = lambda obj: isinstance(obj,basestring) or getattr(obj,'__iter__',False)

    def isit3(obj):
        return (isinstance(obj,basestring) or getattr(obj,'__iter__',False))

    #...then:
    '''
    >>> timing(isit3, 100000, [])
    isit3 0.99
    >>> timing(isit2, 100000, [])
    <lambda> 0.99

    >>> timing(isit, 100000, [])
    isit 0.53
    '''
