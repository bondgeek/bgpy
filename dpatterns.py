'''
Design Patterns
===============

Borg and Singleton adapted from:

* http://code.activestate.com/recipes/66531/

with clarifications from:

* http://snippets.dzone.com/posts/show/651

It is hard to quantify which approach is better.  For an object like the 
following:

    class Today(Singleton):
        def __init__(self):
            from datetime import date
            self.date = date.today()
        def __repr__(self):
            return str(self.date)

which could see several calls--maybe Singleton is better.  

Created on Jul 10, 2009

@author: bartmosley
'''


class Singleton(object):
    '''There will only be one instance of this class, or any subclass'''
    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

class Borg(object):
    '''Each instance of Borg will have the same state(attributes and values),
    aka MonoState'''
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state
