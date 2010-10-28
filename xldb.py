'''
Created on Apr 17, 2010

@author: bartmosley
'''
import os
import xlrd
import xlwt

from datetime import date

def xl_to_date(xdate, _datemode = 1):
    yyyy, mm, dd, h, m, s =xlrd.xldate_as_tuple(xdate.value, _datemode)
    return date(yyyy, mm, dd)

def xlValue(x, datemode=1, hash_comments=1):
    try:
        if(x.ctype == 0):
            return ""
        if(x.ctype == 1):
            t = x.value.encode()
            if hash_comments and t[0] == '#':
                return None
            else:
                return t
        if(x.ctype == 3):
            yyyy, mm, dd, h, m, s = xlrd.xldate_as_tuple(x.value,
                                                         datemode)
            return date(yyyy,mm,dd)
        else:
            return x.value
    except:
        return None 

class XLdb(object):
    '''
    Container class for loading an Excel Database
    
    Class creates member dictionary with data from the specified 
    spreadsheet.
        - hash_comments=True returns 'None' if cell string starts with "#', ala Bloomberg data.
        - idx_column determines which column to serve as the key 
          for the qdata dictionary.  '-1' uses the row number as key.
    '''
    def __init__(self, filepath, startrow=0, sheet_index=0,
                 sheet_name=None, header=True,
                 idx_column=0, hash_comments=1):

        self.filepath = filepath
        self.book = xlrd.open_workbook(filepath)
        self.datemode = self.book.datemode
        if sheet_name:
            self.sh = self.book.sheet_by_name(sheet_name)
        else:
            self.sh = self.book.sheet_by_index(sheet_index)
        self.ncolumns = self.sh.ncols
        self.nrows = self.sh.nrows
        self.hash_comments = hash_comments
        
        cleanrow_ = lambda row_: [x for x in row_ if x is not '']
        def getvalue(h_):
            if hasattr(h_.value, "encode"):
                return h_.value.encode()
            else:
                return h_.value
            
        if header:
            self.hdr = [getvalue(h) for h in self.sh.row(startrow)]
            rowValues = lambda row_, loc: dict(zip(self.hdr[loc:],
                                                   cleanrow_(row_[loc:])))
        else:
            rowValues = lambda row_, loc: cleanrow_(row_[loc:])

        self.refcolumn = []
        self.qdata = {}
        if header:
            startatrow = startrow + 1 
        else: 
            startatrow = startrow
        
        if idx_column == 0:    
            startloc = 1  
        else:
            startloc = 0
            
        for xrow in range(startatrow, self.nrows):
            try:
                xr = map(self.xlCellValue, self.sh.row(xrow))
            except:
                print("problem with row %s" % xrow)
                continue #skips a row if there's a problem
            else:
                xrvalues = rowValues(xr, startloc)
                
                if header and (xr[0] not in self.refcolumn):
                    self.refcolumn.append(xr[0])
                
                if idx_column >= 0:    
                    dkey = xr[idx_column] 
                else: 
                    dkey = xrow
                    
                self.qdata[dkey] = xrvalues
    
    def __getitem__(self, key):
        if self.qdata:
            return self.qdata.get(key, None)
        else:
            return None
            
    def xlCellValue(self, x):
        return xlValue(x, self.datemode, self.hash_comments)

class XLOut(object):
    datestyle = xlwt.XFStyle()
    datestyle.num_format_str='MM/DD/YYYY'
    defaultstyle = xlwt.XFStyle()
    styles = {"date": datestyle}
    
    def __init__(self, fname, sheets=1):
        self.filename = fname
        
        self.wkb = xlwt.Workbook()                

        self.sheet = {}
        for n in range(sheets):
            sheetname = "Sheet"+str(n+1)
            self.sheet[n] = self.wkb.add_sheet(sheetname)
    
    def write(self, value_, row_, col_, sheet=1, format=None):
        style = self.styles.get(format, self.defaultstyle)
        
        ws = self.sheet[sheet-1]
        ws.write(row_, col_, value_, style)
        
    def close(self):
        self.wkb.save(self.filename)
        