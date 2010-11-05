'''
Date functions

Use toDate to avoid problems with Resolvers .NET date class
'''
import re
from datetime import date as pyDate

from bgpy.QL import Date as qlDate

try:
    # CSharp QuantLib bindings
    from bgpy.QL import Month
    def GetMonth(m):
        return getattr(Month, Month.GetName(Month, m))
except:
    #posix C++ QuantLib bindings
    def GetMonth(m):
        return m
                
stddate_re = re.compile("[-//]".join(("([1-9]{1}|[0][1-9]|[1][0-2])", #regex month
                                   "([1-9]{1}|[0][1-9]|[1-3][0-9])", #regex day
                                   "([1-9][0-9]{3}|[0-9][0-9])")   #regex year
                                  ))
                                  
isodate_re = re.compile("[-//]".join(("([1-9][0-9]{3}|[0-9][0-9])",   #regex year
                                   "([1-9]{1}|[0][1-9]|[1][0-2])", #regex month
                                   "([1-9]{1}|[0][1-9]|[1-3][0-9])") #regex day
                                  ))

longdate_re = re.compile("(?P<Y>[1-9][0-9]{3})(?P<M>[0-1][0-9])(?P<D>[0-3][0-9])")                                  

def ccyymmdd(date_long):
    "returns m, d, y for ccyymmdd date (either integer or string)"
    m = re.match(longdate_re, str(date_long))
    if m is None:
        return None
    
    return map(int, (m.group('M'), m.group('D'), m.group('Y')))
    
def strDateTuple(sdate, twodigitlag=40):
    '''
    Given a date in string format return month, day, year tuple
    - year is in ccyy format
    - date string may use either "-" or "/" separators
    - date string may be mm/dd/ccyy, mm/dd/yy, ccyy-mm-dd, yy-mm-dd 
      or ccyymmdd formats
    - an integer ccyymmdd also works (but not yymmdd).
    '''
    sdate = str(sdate) # incase int is given
    stdgrp = re.match(stddate_re, sdate)
    isogrp = re.match(isodate_re, sdate)
    if stdgrp:
        m, d, y = map(int, stdgrp.groups())
    elif isogrp:
        y, m, d = map(int, isogrp.groups())
    else:
        return ccyymmdd(sdate)
        
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
        elif type(dateObject) in [str, int]:
            dtobj = strDateTuple(dateObject)
            if dtobj:
                m, d, y = dtobj
            else:
                return None 
        elif type(dateObject) == pyDate:
            y, m, d = dateObject.timetuple()[:3]
        elif type(dateObject) == qlDate or hasattr(dateObject, "dayOfMonth"):
                if dateObject == qlDate():
                    return None
                    
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
    
    if nargs == 0 or (not args[0]):
        qDate = None
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
            qDate = None
    else:
        qDate = None
        
    return qDate

def toPyDate(*args):
    '''
    Returns an instance of python's date class.
    - allows passing in a wide range of date objects:
      .Net Date, python date, QuantLib Date, date string or day, month, year
    - Can pass month either as an integer or QuantLib Month.
    '''
    nargs = len(args)
    try:
        assert nargs <= 1 or nargs == 3
    except AssertionError:
        raise StandardError("Date class expects 0, 1 or 3 arguments")
    
    if nargs == 0 or (not args[0]):
        qDate = None
    elif nargs == 3:
        y, m, d = args
        m = getattr(m, "value__", m)
        qDate = pyDate(y, m, d)
    elif nargs ==1:
        dtuple = dateTuple(args[0])
        if dtuple:
            m, d, y = dtuple
            m = getattr(m, "value__", m)
            qDate = pyDate(y, m, d)
        else:
            qDate = None
    else:
        qDate = None
        
    return qDate
    
def dateFirstOfMonth(date_):
    m, d, y = dateTuple(toDate(date_))
    return toDate(1, m, y)

if __name__ == "__main__":
    import unittest
        
    # TODO: will have to create separate test cases for c# bindings.
    
    cases_toDate = (
        (pyDate(1960, 8, 9), qlDate(9, GetMonth(8), 1960)),
        (None, None),
        ((23, 5, 1993), qlDate(23, GetMonth(5), 1993)) 
        )
        
    def testComp(thing1, thing2):
        if type(thing1) == tuple:
            v1 = toDate(*thing1)
        else:      
            v1 = toDate(thing1)
        v2 = thing2
        if hasattr(v1, "serialNumber"):
            v1 = v1.serialNumber()
        if hasattr(v2, "serialNumber"):
            v2 = v2.serialNumber()
        
        return v1==v2
        
    class TestDates(unittest.TestCase):            
        def test_toDate(self):
            for k, val in  cases_toDate:
                self.assertTrue(testComp(k,  val))
                
    unittest.main()
                