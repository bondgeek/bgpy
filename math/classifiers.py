'''
functions used in classifying data
'''


def flatn(obj, levels=None, _ltypes = (list, tuple), _counter=0):
    '''flatten a list or tuple specified levels'''
    if isinstance(obj, _ltypes):
        objtype = type(obj)

        if not levels or _counter < levels:
            _counter += 1

            objl = []
            for n in obj:
                objl.extend(flatn(n,
                                  levels=levels, _counter=_counter))
        else:
            objl = list(obj)

        return objtype(objl)
    else:
        return [obj]


def get_values(inlist, sort=True):
    '''
    (iterable, sort=True) -> discrete values in list, sorted by default
    '''
    values = [obj for n, obj in enumerate(inlist) 
            if obj not in inlist[n+1:]]

    if sort:
        values.sort()
    
    return values

def levels(inlist):
    '''
    takes a string or list and returns a frequency table: (freq, values)
    '''
            
    values = get_values(inlist)

    H = []
    for x in values:
        H.append(list(inlist).count(x))
        
    return (H, values)

