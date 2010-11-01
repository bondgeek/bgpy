'''
Date functions

Use toDate to avoid problems with Resolvers .NET date class
'''
try:
    # CSharp QuantLib bindings
    from QuantLib import Month
    def GetMonth(m):
        return getattr(Month, Month.GetName(Month, m))
except:
    #posix C++ QuantLib bindings
    def GetMonth(m):
        return m
                
from QuantLib import Date as qlDate
from datetime import date as pyDate

import re

stddate_re = re.compile("[-//]".join(("([1-9]{1}|[0][1-9]|[1][0-2])", #regex month
                                   "([1-9]{1}|[0][1-9]|[1-3][0-9])", #regex day
                                   "([1-9][0-9]{3}|[0-9][0-9])")   #regex year
                                  ))
                                  
isodate_re = re.compile("[-//]".join(("([1-9][0-9]{3}|[0-9][0-9])",   #regex year
                                   "([1-9]{1}|[0][1-9]|[1][0-2])", #regex month
                                   "([1-9]{1}|[0][1-9]|[1-3][0-9])") #regex day
                                  ))


def strDateTuple(sdate, twodigitlag=40):
    '''
    Given a date in string format return month, day, year tuple
    - year is in ccyy format
    - date string may use either "-" or "/" separators
    - date string may be mm/dd/ccyy, mm/dd/yy, ccyy-mm-dd, yy-mm-dd formats
    '''
    stdgrp = re.match(stddate_re, sdate)
    isogrp = re.match(isodate_re, sdate)
    if stdgrp:
        m, d, y = map(int, stdgrp.groups())
    elif isogrp:
        y, m, d = map(int, isogrp.groups())
    else:
        return None
    if y < 100:
        thisyear = pyDate.today().year
        baseyr = (thisyear - twodigitlag) % 100
        cc = thisyear - thisyear % 100
        if y < baseyr:
            y += cc
        else:
            y += cc - 100
            
    return m, d, y

def dateTuple(dateObject):
    '''
    For a somewhat generic range of date objects, return month, day, year tuple
    '''
    if not dateObject:
        return None
        
    dateObject = getattr(dateObject, "Value", dateObject)

    try:    
        if hasattr(dateObject, "DateTime"):
            m, d, y = (dateObject.DateTime.Month,
                       dateObject.DateTime.Day,
                       dateObject.DateTime.Year)
        elif (hasattr(dateObject, "Month") and
              hasattr(dateObject, "Day") and
              hasattr(dateObject, "Year") ):
            m, d, y = (dateObject.Month,
                       dateObject.Day,
                       dateObject.Year)
        elif type(dateObject) == str:
            dtobj = strDateTuple(dateObject)
            if dtobj:
                m, d, y = dtobj
            else:
                return None 
        elif type(dateObject) == pyDate:
            y, m, d = dateObject.timetuple()[:3]
        elif type(dateObject) == qlDate or hasattr(dateObject, "dayOfMonth"):
    
                y, m, d = (dateObject.year(),
                           dateObject.month(),
                           dateObject.dayOfMonth())
        else:
            return None
    except:
        return None
    
    m = getattr(m, "value__", m)
    
    return (m, d, y)

def toDate(*args):
    '''
    Returns an instance to QuantLib's Date class.
    - allows passing in a wide range of date objects:
      .Net Date, python date, QuantLib Date, date string or day, month, year
    - Can pass month either as an integer or QuantLib Month.
    '''
    nargs = len(args)
    try:
        assert nargs <= 1 or nargs == 3
    except AssertionError:
        raise StandardError("Date class expects 0, 1 or 3 arguments")
    
    if nargs == 0 or (not args[0]) or (args[0] == qlDate()):
        # c# bindings don't treat qlDate() as Null
        qDate = qlDate()
    elif nargs == 3:
        d, m, y = args
        m_ = GetMonth(m)
        qDate = qlDate(d, m_, y)
    elif nargs ==1:
        dtuple = dateTuple(args[0])
        if dtuple:
            m, d, y = dtuple
            m_ = GetMonth(m)
            qDate = qlDate(d, m_, y)
        else:
            qDate = qlDate()
    else:
        qDate = qlDate()
        
    return qDate

def dateFirstOfMonth(date_):
    m, d, y = dateTuple(toDate(date_))
    return toDate(1, m, y)
    