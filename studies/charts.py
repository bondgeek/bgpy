import os

from tempfile import mkstemp
from datetime import date

def timeseries_chart(tsdata, filename=None, fdir=None, **kwgs):
    '''
    >timeseries_chart(tsdata, 
                      "chart.png", 
                      fdir="/static", 
                      dpi=150, 
                      title="timeseries chart", 
                      ylabel='yields', 
                      xlabel='dates', 
                      axis_bgcolor='w', 
                      edgecolor='w',
                      facecolor='w')
                      
    Returns full path name of png file for chart.

    colors:
     =====   =======
      Alias   Color
      =====   =======
      'b'     blue
      'g'     green
      'r'     red
      'c'     cyan
      'm'     magenta
      'y'     yellow
      'k'     black
      'w'     white
      =====   =======
       For a greater range of colors, you have two options.  You can
    specify the color using an html hex string, as in::
    
      color = '#eeefff'
    
    or you can pass an R,G,B tuple, where each of R,G,B are in the
    range [0,1].
    
    You can also use any legal html name for a color, for example::
    
      color = 'red',
      color = 'burlywood'
      color = 'chartreuse'
    
    The example below creates a subplot with a dark
    slate gray background
    
       subplot(111, axisbg=(0.1843, 0.3098, 0.3098))


    '''
    import matplotlib
    matplotlib.use('Agg')  # force the antigrain backend

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter

    if not fdir:
        fdir = os.getcwd()
    
    # create tempfile if no filename provided
    if not filename:
        fd, fpath = mkstemp(dir=fdir, suffix=".png")
        os.close(fd)
        
    else:
        # make sure file ends with .png extension
        fname = '.'.join((filename.split('.')[0], "png"))
        fpath = os.path.join(fdir if fdir else '', filename)

    fig=Figure()
    fig.set_edgecolor(kwgs.get('edgecolor', 'w'))
    fig.set_facecolor(kwgs.get('facecolor', 'w'))
    
    pltkwgs = {}
    for key in ['title', 'ylabel', 'xlabel', 'axis_bgcolor']:
        v = kwgs.get(key, None)
        if v:
            pltkwgs[key] = v
    
    ax=fig.add_subplot(111, **pltkwgs)

    x = tsdata.keys()
    x.sort()
    y = [tsdata[dt] for dt in x]
    
    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    canvas=FigureCanvasAgg(fig)
    
    dpi = kwgs.get('dpi', 150)
    
    canvas.print_png(fpath, dpi=dpi)
    
    return fpath
    