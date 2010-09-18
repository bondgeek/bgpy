'''
Tools to facilitate development.

Created August 2010
@author: bartmosley
'''

import time  #where is all the time spent?

class timer(object):
    '''Returns how much time has elapsed since the previous call'''
    def __init__(self):
        self.initialtime = time.clock()
        self.prevtime = self.initialtime
    
    def lap(self):
        '''Returns how time has elapsed since the previous call'''
        tnow = time.clock()
        d = round(tnow - self.prevtime, 3)
        self.prevtime = tnow
        return d
