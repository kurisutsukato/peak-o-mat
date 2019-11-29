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
import queue

import scipy.odr.odrpack as O
    
from .model import QuickEvaluate
from .spec import Spec
from . import misc_ui
import wx

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
    def __init__(self, func, ds_lengths):
        self.func = func
        tmp = np.cumsum([0]+ds_lengths)
        self.slices = [(tmp[q],tmp[q+1],1) for q in range(len(tmp)-1)]
        O.Model.__init__(self, self.evaluate)

    def evaluate(self, a, x):
        out = self.func(x, a)
        return np.hstack([out[n][slice(*self.slices[n])] for n in range(len(out))])

class MFitData(O.Data):
    def __init__(self, pl):
        #x, y, y2 = spec.xyy2_limited
        #if spec.weights is not None:
        #    weights = spec.weights.getWeights(spec.xyy2_limited)
        #else:
        #    weights = None
        O.Data.__init__(self,
                        np.hstack([ds.x for ds in pl]),
                        np.hstack([ds.y for ds in pl]),
                        #we=weights
                        )

def pprint(result):
    out = []
    def _q(arg):
        return '[{}]'.format(' '.join([str(q) for q in arg]))

    if hasattr(result, 'info'):
        out.append('Residual Variance: {}'.format(result.res_var))
        #out.append('Inverse Condition #: {}'.format(result.inv_condnum))
        if len(result.stopreason) > 0:
            out.append('Reason(s) for Halting: ({})'.format(', '.join(result.stopreason)))

    return out

class Fit:
    def __init__(self, ds, model, fittype=0, maxiter=50, stepsize=-1, autostep=True, msgqueue=None):
        fittype = [2,0][fittype]
        self.ds = copy.deepcopy(ds)
        self.func = QuickEvaluate(copy.deepcopy(model))
        self._queue = msgqueue

        if model.coupled_model:
            ds_lengths = [len(q) for q in ds]
            fitmodel = MFitModel(self.func, ds_lengths)
            data = MFitData(self.ds)
        else:
            fitmodel = FitModel(self.func)
            data = FitData(self.ds)
        guess = list(self.func.par_fit.values())

        kwargs = {'maxit':1}
        self.maxiter = maxiter
        if not autostep:
            kwargs.update({'stpb':np.ones((len(guess)))*stepsize})

        try:
            self.odr = O.ODR(data, fitmodel, guess, **kwargs)
        except O.OdrError:
            print(data)
            print(model)
            raise

        self.odr.set_job(fit_type=fittype)
        #print 'ready to fit'

    def run(self, notify=None):
        def message(**kwargs):
            event = misc_ui.ResultEvent(notify.GetId(), **kwargs)
            wx.PostEvent(notify, event)

        out = self.odr.run()
        if True:
            for k in range(self.maxiter):
                try:
                    if self._queue.get(False):
                        return None,None,['Fit cancelled by user']
                except queue.Empty:
                    pass
                if notify is not None:
                    message(iteration=(k + 2, out.info, out.res_var))
                if out.info != 4:
                    break
                out = self.odr.restart(1)
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

    ds = []
    for n in range(2):
        x = np.linspace(0,5,50)
        y = x*3+.5+np.random.randn(*x.shape)
        ds.append(Spec(x,y,'bla'))

    from .model import Model
    from .spec import Spec
    m = Model('a*x,a*x+b*x**2+c')
    m = Model('a*x+b,a*x')
    m.parse()
    m.CUSTOM.a.value = 5.0
    m.CUSTOM.b.value = 5.0
    #m.CUSTOM.c.value = 5.0

    f = Fit(ds, m)
    res = f.run()
    m.update_from_fit(res)
    print(m.parameters_as_table())
    #o = O.ODR(d, mfm, [1.0])
    #out = o.run()
    #print(out.beta)



