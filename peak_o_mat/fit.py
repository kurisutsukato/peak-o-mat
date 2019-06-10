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

import numpy as np
import copy

import scipy.odr.odrpack as O
    
from .model import QuickEvaluate
from .spec import Spec

class BatchComponent(object):
    def __init__(self):
        self.index = []
        self.values = []

    def append(self, n, val):
        self.index.append(n)
        self.values.append(val)

class BatchParameters(dict):
    def __init__(self, name, par):
        self.name = name
        self.par = par
        self.x = []

    def __getitem__(self, item):
        if item not in list(self.keys()):
            self[item] = BatchComponent()
        return super(BatchParameters, self).__getitem__(item)

    @property
    def is_multi(self):
        return len(list(self.keys())) > 1

    def as_table(self, errors=False):
        ncols = len(list(self.keys()))*(int(errors)+1)
        cl = ['x']*(ncols+1)
        data = np.zeros((len(self.x),ncols+1), dtype=float)*np.nan
        for compcount,comp in enumerate(sorted(self.keys())):
            for n,idx in enumerate(self[comp].index):
                cl[compcount*(int(errors)+1)+1] = '{}:{}'.format(comp,self.par)
                data[idx,compcount*(int(errors)+1)+1] = self[comp].values[n].value
            if errors:
                for n,idx in enumerate(self[comp].index):
                    cl[compcount*(int(errors)+1)+int(errors)+1] = 'err. {}:{}'.format(comp,self.par)
                    data[idx,compcount*(int(errors)+1)+int(errors)+1] = self[comp].values[n].error
        data[:,0] = self.x
        return data,[],cl

    def as_spec(self, item):
        xvalues = list(range(len(self[item].values)))
        for n,idx in enumerate(self[item].index):
            xvalues[n] = self.x[idx]
        #print(len(xvalues),xvalues)
        #print(len([q.value for q in self[item].values]), [q.value for q in self[item].values])
        return Spec(xvalues, [q.value for q in self[item].values], '{}:{}:{}'.format(self.name,item,self.par))

    def __str__(self):
        return '\n'.join([str(q) for q in self.items()])

class FitModel(O.Model):
    def __init__(self, func):
        self.func = func
        O.Model.__init__(self, self.evaluate)

    def evaluate(self, a, x):
        y = self.func(x, a)
        return y

class FitData(O.Data):
    def __init__(self, spec):
        x, y = spec.xy_limited
        if spec.weights is not None:
            weights = spec.weights.getWeights(spec.xy_limited)
        else:
            weights = None
        O.Data.__init__(self, x, y, we=weights)

class MFitModel(O.Model):
    def __init__(self, func):
        self.func = func
        O.Model.__init__(self, self.evaluate)

    def evaluate(self, a, x):
        y1,y2 = self.func(x.T[0], a)
        return np.vstack([y1,y2]).T

class MFitData(O.Data):
    def __init__(self, spec):
        x, y, y2 = spec.xyy2_limited
        if spec.weights is not None:
            weights = spec.weights.getWeights(spec.xyy2_limited)
        else:
            weights = None
        O.Data.__init__(self, np.vstack((x,x)).T, np.vstack((y,y2)).T, we=weights)

def pprint(result):
    out = []
    def _q(arg):
        return '[{}]'.format(' '.join([str(q) for q in arg]))

    if hasattr(result, 'info'):
        out.append('Residual Variance: {}'.format(result.res_var))
        out.append('Inverse Condition #: {}'.format(result.inv_condnum))
        if len(result.stopreason) > 0:
            out.append('Reason(s) for Halting:')
            for r in result.stopreason:
                out.append('  {}'.format(r))
    out.append('_'*60+'\n')
    return out

class Fit:
    def __init__(self, ds, model, fittype=1, maxiter=50, stepsize=-1, autostep=True):
        fittype = [0,2][fittype]
        self.ds = copy.deepcopy(ds)
        self.func = QuickEvaluate(copy.deepcopy(model))

        if ',' in m.func:
            fitmodel = MFitModel(self.func)
            data = MFitData(self.ds)
        else:
            fitmodel = FitModel(self.func)
            data = FitData(self.ds)
        guess = list(self.func.par_fit.values())

        if not autostep:
            self.odr = O.ODR(data, fitmodel, beta0=guess, maxit=maxiter, stpb=np.ones((len(guess)))*stepsize)
        else:
            self.odr = O.ODR(data, fitmodel, beta0=guess, maxit=maxiter)

        self.odr.set_job(fit_type=fittype)
        #print 'ready to fit'

    def run(self):
        out = self.odr.run()
        pars, errors = self.func.fill(out.beta,out.sd_beta)
        msg = pprint(out)


        return pars,errors,msg

def test1():
    bp = BatchParameters(name='test', par='amp')
    bp['LO1'].append(1,45.6)
    bp['LO1'].append(2,40)
    bp['LO1'].append(3,38.4)
    bp['LO2'].append(0,23)
    bp['LO2'].append(1,21)
    bp['LO2'].append(2,17)
    for x in range(5):
        bp.x.append(x)

    tab = bp.as_table()
    #cw = CSVWriter(open('test.csv','wbituit'))
    #cw.writerows(tab)
    print(tab)

if __name__ == '__main__':
    import numpy as np
    x = np.vstack((np.linspace(0,5,3),np.linspace(0,5,3))).T

    y = x*3+.5
    print(x.shape)

    from .model import Model
    m = Model('a*x+b,a*x-b')
    m.parse()
    #m.CUSTOM.a.value = 2
    #m.CUSTOM.b.value = 1
    func = QuickEvaluate(m)

    mfm = MFitModel(func)
    d = O.Data(x,y)
    o = O.ODR(d, mfm, [1.0,1])
    out = o.run()
    print(out.beta)



