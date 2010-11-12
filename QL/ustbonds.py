'''
Treasury Bill, Note and Bond specific bond calculations

'''

from bgpy.QL.bonds import SimpleBond, BondType, ql

class USTBondType(BondType):
    settlementdays = 2
    daycount = ql.ActualActualBond
    paytenor = ql.Semiannual
    frequency = ql.Semiannual
    payconvention = ql.ModifiedFollowing
    termconvention = ql.Unadjusted
    face = 100.0
    
    def bondtype(self):
        d = BondType().bondtype()
        for k in d:
            d[k] = getattr(self,k)
        return d

class USTBillType(BondType):
    settlementdays = 2
    daycount = ql.Actual360()
    paytenor = ql.Semiannual
    frequency = ql.Semiannual
    payconvention = ql.ModifiedFollowing
    termconvention = ql.Unadjusted
    face = 100.0
    
    def bondtype(self):
        d = BondType().bondtype()
        for k in d:
            d[k] = getattr(self,k)
        return d
        
        
class USTBond(USTBondType, SimpleBond):
    '''
    Tsy Note & Bond Object, inherits from SimpleBond
    
    '''
    # TODO:  add 'true yield' function
    def __init__(self, coupon, maturity, callfeature=None, oid=None,  
                       issuedate=None, redvalue=100.0, settledate=None):
        SimpleBond.__init__(self, coupon, maturity, callfeature, 
                                  oid, issuedate, redvalue, settledate)

class USTBill(USTBillType, SimpleBond):
    '''T-Bills
    
    '''
    def __init__(self, maturity, oid=None,  issuedate=None,
                       redvalue=100.0, settledate=None):
        callfeature = None
        SimpleBond.__init__(self, 0.0, maturity, callfeature, 
                            oid, issuedate, redvalue, settledate)
    
    def calc(self, bondprice=None, bondyield=None, dict_out=False):
        '''bondprice is assumed to be the quoted discount.
        Output price is actual price.
        
        '''
        errstr = "calc(): bondyield=%s bondprice=%s exactly one must have a value"  
        
        price = bondprice 
        if not (bondyield or price):
            bondyield = getattr(self, "bondyield", None)
            price = getattr(self, "price", None)

            assert (not price or not bondyield), errstr % (price, bondyield)
        
        if not bondyield:  
            #toYield
            price = self.discountToPrice(price)
            calcattr = 'bondyield'
            bondyield = self.toYield(price)
            result_value = bondyield
            
        else:
            #toPrice
            price = self.toPrice(bondyield)
            calcattr = 'price'
            result_value = price
            
        if dict_out:
            result = {'bondyield': bondyield, 
                      'price': price, 
                      'toDate': self.maturity,
                      'toPrice': self.redvalue}
            result[calcattr] = result_value
        else:
            result = result_value
            
        return result
        
    def discountToPrice(self, discount):
        yFrac = self.daycount.yearFraction(self.settlementDate, self.maturity)
        return (self.redvalue - discount * yFrac)
        
    def toYield(self, price):
        yFrac = ql.ActualActual().yearFraction(self.settlementDate, self.maturity)
        return (self.redvalue - price) / (price * yFrac)
    
    def toPrice(self, bondyield):
        
        yFrac = ql.ActualActual().yearFraction(self.settlementDate, self.maturity)
        if yFrac < .5:
            price = 100. / (bondyield*yFrac + 1.0)
        
        else:
            price = self.ytmToPrice(bondyield)
        
        return price
        