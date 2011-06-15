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
    '''
    There will only be one instance of this class, or any subclass
    
    '''
    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

class Borg(object):
    '''
    Each instance of Borg will have the same state(attributes and values),
    aka MonoState
    
    '''
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state

class Record(dict):
    '''
    General purpose structured data record.
    
    Given attribute list, insures that key for each attr exists and that only those
    attributes can be added.  
    
    WARNING: updates 'bounce off' if attr is not in defined list. No error is thrown
    if you try to update an attribute that is not defined--nothing happens.
    
    Returns True if set is successful, None otherwise.
    
    Example:  One use is to subclass Record:
    
    class MyRecord(Record):
        _attrs = ['a', 'b', 'c']
        
        def __init__(self, initValues=None):
            Record.__init__(self, self._attrs, initValues)
    
    MyRecord has a defined structure.    
        
    '''
    def __init__(self, attr_list, valueDict=None):
        dict.__init__(self)

        dict.__setattr__(self, "attrs", attr_list)
        
        if valueDict:
            self.update(valueDict)
    
    def update(self, valueDict):
        """
        If valueDict is a dict like object, gets members,
        otherwise gets attributes.
        """
        if hasattr(valueDict, "__getitem__"):
            gettr = lambda x: valueDict.__getitem__(x, None)
        else:
            gettr = lambda x: getattr(valueDict, x, None)
        
        for k in self.attrs:
            val = gettr(k)
            if val:
                self.__setitem__(k, val)
    
    def __getitem____(self, k, default=None):
        if k in self.attrs:
            return dict.__getitem__(self, k, default)
        else:
            return default
        
    def __setitem__(self, k, v):
        if k in self.attrs:
            dict.__setitem__(self, k, v)
            return True
        else:
            return None
            
    def __getattr__(self, k):
        return self.get(k, None)
            
    def __setattr__(self, k, v):
        return self.__setitem__(k, v)
                
class Struct(dict):
    '''
    Creates a static dict data structure.
      
    Updates of attributes 'bounce off' after initial set--i.e., no error 
    is returned but contents are not effected.
    
    '''
    def __getattr__(self, k):
        return self.get(k, None)
    
    def __setattr__(self, k, v):
        return None