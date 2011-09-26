
class StudySeries(object):
    def __init__(self, study_object, study_data=None):
        '''
        Takes study object
        
        '''
        assert hasattr(study_object, "__call__"), "invalid study object"
        
        self.study = study_object
        
        if study_data:
            self.update(study_data)

    def update(self, study_data, nLimit):
        
        self.series = []
        dtlist = [dt for dt in study_data[:nLimit] if study_data[dt]]
        dtlist.sort(Reverse=True)
        
        for dt in dtlist:
            val = self.study(study_data[dt])
            self.series.append((dt, val))
        
        return self.series

class ExpMA(object):
    def __init__(self, n, seed=None):
        self.length_ = n 
        self.factor = 2. / (float(n) + 1.) 
        self.value_ = seed
    
    def __call__(self, observation):
        if self.value_ is None:
            self.value_ = observation
        else:
            prv = self.value_
            self.value_ = (observation - prv) * self.factor + prv 
    
        return self.value_
