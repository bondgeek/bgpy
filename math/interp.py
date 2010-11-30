'''
Interpolation functions

'''


def npinterp(x, xrange, yrange, leftValue=None, rightValue=None):
    '''
    Meant to mimic numpy call.
    '''
    return (zip(xrange, yrange), x, leftValue, rightValue)
    
def interp(xyTuples, x, leftValue=None, rightValue=None):
    '''
    Interpolates the value of y for given x from 
    a set of data of the form (x, y).
    '''
    if not leftValue:
        leftValue = xyTuples[0]
    if not rightValue:
        rightValue = xyTuples[-1]
        
    xy0 = [n for n in range(len(xyTuples)) if xyTuples[n][0] <= x] 
    xy1 = [n for n in range(len(xyTuples)) if xyTuples[n][0] >= x]
    
    x0, y0 = xyTuples[ max(xy0) ] if xy0 else leftValue
    x1, y1 = xyTuples[ min(xy1) ] if xy1 else rightValue

    if abs(x1 - x0) < 1e-12:    
        if x < x0:
            x1, y1 = xyTuples[1]
        else:
            x1, y1 = xyTuples[-2]
            
    m = (float(x) - float(x0))/(float(x1) - float(x0))
        
    return m * y1 + (1.0 - m) * y0
    