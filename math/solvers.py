'''
Solvers for bgpy

'''

#class definitions
class SolverExceptions(Exception):
    MAX_ITERATIONS = 24
    MIN_VALUE = 1e-12

def Secant(x0, x1, valueFunc, objectiveValue):
        '''
        value function must be of one variable
        '''
        MAXITER, MINVAL = SolverExceptions.MAX_ITERATIONS, SolverExceptions.MIN_VALUE
        
        v_ = valueFunc(x0)
        
        ictr = 0
        ok_go = True
        while ok_go:
            v1 = valueFunc(x1)
            v_diff = v1 - objectiveValue
            delta = (v1 - v_) / (x1 - x0)
            x0 = x1
            x1 = x1 - v_diff / delta
            v_ = v1
            ictr += 1
            # check at end to ensure at least one pass
            ok_go = abs(v_diff) > MINVAL and abs(x1-x0) > MINVAL and ictr < MAXITER

        assert (ictr < MAXITER+1), "Secant: Max iterations reached: %s" % x1*100.0
        return x1
        