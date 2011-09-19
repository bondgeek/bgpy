from datetime import date

from matplotlib.finance import quotes_historical_yahoo

from bgpy.QL import toPyDate

quote_header = ['date', 'open', 'high', 'low', 'close', 'volume']

def quotes_yahoo(ticker, begin, end=None, mode='d'):
    '''
    Gets timeseries of stock quotes from yahoo.
    
    mode:  'd' returns {date: (open, high, low, close, volume)}
           'l' list of [(date, open, high, low, close, volume)]
           otherwise numpy structured array
           
    '''
    
    # construct date range for query
    begin, end = map(toPyDate, (begin, end))
    if not end: 
        end = date.today()

    date1 = begin.year, begin.month, begin.day
    date2 = end.year, end.month, end.day
    
    # call matplotlib function, asobject=True
    # for structured numpy array
    quotes = quotes_historical_yahoo('INTC', date1, date2, asobject=True)
    
    if mode == 'd':
        vTuple = lambda x: (x['date'], 
                            tuple([x[h] for h in quote_header[1:]]))
    
    elif mode == 'l':
        vTuple = lambda x: tuple([x[h] for h in quote_hdr])
    
    else:
        return quotes
        
    quotes = [vTuple(rec) for rec in quotes]
    
    return dict(quotes) if mode=='d' else quotes
