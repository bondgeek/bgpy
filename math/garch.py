import numpy as np
from scipy.optimize import fmin

from bgpy.dpatterns import Struct

def garch_var(parms, variance, observed_value):
    '''
    GARCH variance estimate
    
    parms:          GARCH parameters
    variance:       previous variance estimate
    observed_value: previous observed value.
    
    '''
    omega, alpha, beta = parms

    return omega + alpha*variance + beta*observed_value*observed_value

def loglikelihood_x(variance, observed):
    '''
    Log Likelihood of observation, for zero-mean normal probability 
    distribution function.
    
    '''
    return -(np.log(variance) + (observed * observed) / variance)

def garch_loglike(parms, ydata, V0=None):
    '''
    Log likelihood function for GARCH estimation.
    
    parms:  mu, alpha, [beta]  
            mu: long term drft
            alpha: first persistence parameter
            beta: if only two parameters are given
                  model is assumed to be EWMA, beta=(1-alpha)
            
            NOTE: model constrains gamma = (1-alpha-beta) > 0.
            
    ydata:  timeseries to be fitted via mle
    V0:     long run variance
    
    '''
    # if no long term variance estimate is given, use sample variance
    V0 = np.var(ydata) if not V0 else V0
    
    if len(parms) > 2:
        mu, alpha, beta = parms
        
        # if omega is negative, use EWMA (i.e. omega = 0.)
        omega = np.max( (0., V0 * (1.0 - beta - alpha)) )
        
    else:
        mu, alpha = parms
        
        omega = 0.0
        beta = (1. - alpha)
        
    # use estimate of drift to normalize data
    y = [u - mu for u in ydata]
    
    # create time series of variance estimates, 
    # set initial value to long term variance
    variances = [V0]
    for n in range(1, len(y)):
        variances.append( garch_var((omega, alpha, beta), variances[n-1], y[n-1]) )
         
    return -sum([loglikelihood_x(v, r) for v, r in zip(variances, y) ])
 
def garch_estimator(yseries, x0, var0=None):
    '''
    MLE estimation of GARCH parameters and drift for time series
    
    yseries:    time series vector
    x0:         mu, alpha, beta
                initial guess of parameter values
                mu: long term drft
                alpha: first persistence parameter
                beta: if only two parameters are given
                      model is assumed to be EWMA, beta=(1-alpha)
            
                NOTE: model constrains gamma = (1-alpha-beta) > 0.   
    
    returns a dictionary with keys:
    v:          time series of variance estimates
    mu:         drift estimate
    garch:      estimated GARCH parameters
    
    Uses scipy.optimize.fmin to minimize the negative of the likelihood function.
    
    '''
    # sample variance 
    var0 = np.var(yseries) if not var0 else var0
    
    # maximum likelihood estimates of GARCH parameters
    return fmin(garch_loglike, x0, args=(yseries, var0), xtol=1e-8)

def variance_estimates(mleEst, yseries):
    if len(mleEst) > 2:
        mu, alpha, beta = mleEst    
        omega = var0 * (1. - alpha - beta)
    else:
        mu, alpha = mleEst    
        omega = 0.
        beta = (1. - alpha)
    
    yseries_ = [y - mu for y in yseries]
    
    variance_est = [var0]
    for n in range(len(yseries_)):
        variance_est.append( garch_var((omega, alpha, beta), 
                                       variance_est[n-1], 
                                       yseries_[n-1]) )
    
    return variance_est

class GARCH(Struct):
    values_ = ['ydata',
             'v_estimates',
             'vol_series',
             'mu',
             'garch',
             'var0',
             'mleEst',
             'uptodate']
    
    def __init__(self):
        val_ = {}
        for key in self.values_:
            val_[key] = None
        
        dict.__init__(self, val_)

    
    def __call__(self, yseries, x0):
        '''
        MLE estimation of GARCH parameters and drift for time series
        
        yseries:    time series vector
        x0:         mu, alpha, beta
                    initial guess of parameter values
                    mu: long term drft
                    alpha: first persistence parameter
                    beta: if only two parameters are given
                          model is assumed to be EWMA, beta=(1-alpha)
                
                    NOTE: model constrains gamma = (1-alpha-beta) > 0.   
        
        returns a dictionary with keys:
        v:          time series of variance estimates
        mu:         drift estimate
        garch:      estimated GARCH parameters, alpha, beta, omega
        
        Uses scipy.optimize.fmin to minimize the negative of the likelihood function.
        
        '''
        self['ydata'] = yseries
        
        # sample variance 
        self['var0'] = np.var(yseries)
        
        # maximum likelihood estimates of GARCH parameters
        self['mleEst'] = fmin(garch_loglike, x0, args=(yseries, self.var0), 
                              xtol=1e-8)

        if len(self.mleEst) > 2:
            mu, alpha, beta = self.mleEst    
            omega = self.var0 * (1. - alpha - beta)
        else:
            mu, alpha = self.mleEst    
            omega = 0.
            beta = (1. - alpha)
        
        self['mu'] = mu
        self['garch'] = alpha, beta, omega
        
        self['uptodate'] = True
        return self.mleEst
    
    def estimate_variance(self):
        
        if not self.uptodate:
            print("Model estimates not up to date")
            return None
        
        alpha, beta, omega = self.garch
        
        yseries_ = [y - self.mu for y in self.ydata]
        
        variance_est = [self.var0]
        for n in range(len(yseries_)):
            variance_est.append( garch_var((omega, alpha, beta), 
                                           variance_est[n-1], 
                                           yseries_[n-1]) )
        
        self['v_estimates'] = variance_est
    
    def estimate_volatility(self, annualize=252):
        
        if not self.v_estimates:    
            self.estimate_variance()
        
        self['vol_series'] =  [np.sqrt(v*252) for v in self.v_estimates]
        
        return self.vol_series
        