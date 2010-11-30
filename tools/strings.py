
def commonstring(one, two):
    '''Return the common head of two strings.
    
    Example:  
        >>>commonstring("This parrot", "This parrot is a stiff")
        "This parrot"
        
    '''
    m = min(len(one), len(two))
    common = one
    for i in range(m+1):
        if(one[:i]==two[:i]):
            common=one[:i]
    return common

def segregatestring(one, two):
    ''' Return the tail portion of the longer string
    
    Example" 
        >>>segregatestring('this parrot is', 'this parrot is a stiff')
        'a stiff' 
        
    '''
    m = min(len(one), len(two))
    if(len(one) > len(two)):
        tail = one[m:]
    else:
        tail = two[m:]
    return tail.strip()

