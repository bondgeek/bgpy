
def join_timeseries(*args):
    '''
    Returns a time series dict object joining tg
    
    '''
    series1 = {}
    if args:  
        series1_dates = args[0].keys() 
        #series1_dates.sort()
    
        for dt in series1_dates:
            value1 = args[0][dt]            
            if not hasattr(value1, '__iter__'):
                value1 = [value1]

            for series2 in args[1:]:
                value2 = series2.get(dt, [])            
                if not hasattr(value2, '__iter__'):
                    value2 = [value2]
    
                value1 = value1+value2
            
            series1[dt] = tuple(value1)
        
    return series1
    
    
def spread_timeseries(series1, series2):
    '''
    Returns a time series dict object 
    output  {date: (value1, value2, spread=value2-value1, ratio=value2/value1)}
    
    '''
    spread_series = {}
    series1_dates = series1.keys() 
    series1_dates.sort()
    
    for dt in series1_dates:
        value2 = series2.get(dt, None)

        if value2:
            value1 = series1.get(dt, None)
            spread = value1 - value2
            ratio = value1/value2
            spread_series[dt] = (value1, value2, spread, ratio)

    return spread_series
    
