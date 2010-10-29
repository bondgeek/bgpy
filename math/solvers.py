'''
Solvers for bgpy

'''

#class definitions
class SolverExceptions(Exception):
    MAX_ITERATIONS = 24
    MIN_VALUE = 1e-12

def interp(xyTuples, x):
    '''
    Interpolates the value of y for given x from 
    a set of data of the form (x, y).
    '''
    xy0 = [n for n in range(len(xyTuples)) if xyTuples[n][0] <= x] 
    xy1 = [n for n in range(len(xyTuples)) if xyTuples[n][0] >= x]
    
    x0, y0 = xyTuples[ max(xy0) ] if xy0 else xyTuples[0]
    x1, y1 = xyTuples[ min(xy1) ] if xy1 else xyTuples[-1]

    if abs(x1 - x0) < 1e-12:    
        if x < x0:
            x1, y1 = xyTuples[1]
        else:
            x1, y1 = xyTuples[-2]
            
    m = (float(x) - float(x0))/(float(x1) - float(x0))
        
    return m * y1 + (1.0 - m) * y0
    
def Secant(x0, x1, valueFunc, objectiveValue):
        '''
        value function must be of one variable
        '''
        MAXITER, MINVAL = SolverExceptions.MAX_ITERATIONS, SolverExceptions.MIN_VALUE
        
        #make sure x0 & x1 are different
        if abs(x1 - x0) <= MINVAL:
            x1 = x0 + 0.001
            
        v_ = valueFunc(x0)
        
        ictr = 0
        delta = 1.0
        v_diff = 0.0
        ok_go = True
        while ok_go:
            x1 = x1 - v_diff / delta
            v1 = valueFunc(x1)
            v_diff = v1 - objectiveValue
            delta = (v1 - v_) / (x1 - x0)
            x0, v_ = x1, v1
            ictr += 1
            # check at end to ensure at least one pass
            ok_go = abs(v_diff) > MINVAL and abs(delta) > MINVAL  and ictr < MAXITER

        assert (ictr < MAXITER+1), "Secant: Max iterations reached: %s" % x1*100.0
        return x1
        