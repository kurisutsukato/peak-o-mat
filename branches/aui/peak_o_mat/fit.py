##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import numpy as N
import copy
import sys

import scipy.odr.odrpack as O
    
from model import QuickEvaluate

class FitModel(O.Model):
    def __init__(self, func):
        self.func = func
        O.Model.__init__(self, self.evaluate)

    def evaluate(self, a, x):
        y = self.func(x,a)
        return y

class FitData(O.Data):
    def __init__(self, spec):
        x, y = spec.xy_limited
        if spec.weights is not None:
            weights = spec.weights.getWeights(spec.xy_limited)
        else:
            weights = None
        O.Data.__init__(self, x, y, we=weights)

class Fit:
    def __init__(self, set, model, fittype=1, maxiter=50, stepsize=1e-13):
        fittype = [0,2][fittype]
        self.set = copy.deepcopy(set)
        self.func = QuickEvaluate(copy.deepcopy(model))
       
        #self.model = model
        model = FitModel(self.func)
        
        data = FitData(set)
        guess = self.func.par_fit.values()
        self.odr = O.ODR(data, model, beta0=guess, maxit=maxiter, stpb=N.ones((len(guess)))*stepsize)
        self.odr.set_job(fit_type=fittype)
    
    def run(self):
        out = self.odr.run()
        pars, errors = self.func.fill(out.beta,out.sd_beta)
        #self.model._newpars(pars, errors)
        msg = ['reason for halting: %s'%(', '.join(out.stopreason)), 'residual variance: %g'%out.res_var]
        return pars,errors,msg

