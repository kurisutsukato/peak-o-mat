#!/usr/bin/python
# -*- coding: utf-8 -*-

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

import string
import operator
import re
try:
    from re import Scanner
except ImportError:
    from sre import Scanner

import copy as cp
from operator import mul, add

import numpy as N

import peaks

def ireduce(func, iterable, init=None):
    iterable = iter(iterable)
    if init is None:
        init = iterable.next()
        yield init
    else:
        try:
            init = func(init, iterable.next())
            yield init
        except StopIteration:
            yield init
    for item in iterable:
        init = func(init, item)
        yield init
        
class ModelTableProxy(list):
    class Constant(object):
        __const__ = True
        def __init__(self, name, area):
            self.name = name
            self.area = area

        def __getitem__(self, item):
            if item > 1:
                return 0
            elif item == 0:
                return self.name
            elif item == 1:
                return self.area()

        def __setitem__(self, item, value):
            return
        
    class Variable(object):
        attrmap = [None, 'value', 'error', 'constr', 'amin', 'amax', None]
        types = [str, float, float, int, float, float, float]
        
        def __init__(self, fname, vname, var):
            self.var = var
            self.name = '%s:%s'%(fname,vname)
            
        def __getitem__(self, item):
            if item == 0:
                return self.name
            else:
                try:
                    return getattr(self.var, self.attrmap[item])
                except:
                    print 'var getitem',item

        def __setitem__(self, item, value):
            if item in [1,3,4,5]:
                setattr(self.var, self.attrmap[item], self.types[item](value))

    def __init__(self, model):
        if model is None:
            return
        self.model = model
        a = {}
        
        counts = []
        for component in model:
            counts.append(len(component))
            for key,par in component.iteritems():
                a[par.count] = component.name,key,par

        counts = ireduce(operator.add, counts)
        
        for name,key,par in a.values():
            #if not par.hidden:
            self.append(self.Variable(name,key,par))

        for ins,component in reversed(zip(list(counts),model)):
            if component.area() == N.inf:
                continue
            self.insert(ins,self.Constant('%s:area'%(component.name),component.area))

    def _get_shape(self):
        return len(self),6
    shape = property(_get_shape)

class Model(list):
    """
    List type class to store the fit model and parameters. The list items are
    the model's 'components', e.g. CB, GA, etc.
    """

    tokens = None

    def __init__(self, tokens='', listener=None):
        """
tokens: a space separated list of valid function symbols
"""
        self.parser = None
        self.parsed = False
        self.func = None
        self.listener = listener
        
        if tokens != '':
            if tokens.isupper():
                self.tokens = tokens.strip()
                if self.check() is False:
                    raise KeyError, "token not valid"
            else:
                self.func = tokens.strip()
                self.tokens = 'CUSTOM'
        else:
            self.tokens = ''

    def __deepcopy__(self, memo):
        m = Model('')
        for f in self:
            m.append(cp.deepcopy(f))
        m.tokens = self.tokens
        m.func = self.func
        m.parsed = self.parsed
        return m

    def __setattr__(self, attr, val):
        if hasattr(self, 'tokens') and self.tokens is not None and attr in self.tokens.split(' '):
                print '%s.%s is read only'%(unicode(self), attr)
        else:
            object.__setattr__(self, attr, val)
            
    def __getattr__(self, attr):
        if hasattr(self, 'tokens') and self.tokens is not None and attr in self.tokens.split(' '):
            self.parse()
            return list.__getitem__(self,self.tokens.split(' ').index(attr))
        else:
            raise AttributeError, '%s has no Attribute \'%s\''%(self,attr)
        
    def __getitem__(self, item):
        if hasattr(self, 'tokens') and self.tokens is not None and item in self.tokens.split(' '):
            return getattr(self,item)
        else:
            try:
                ret = list.__getitem__(self, item)
            except TypeError as err:
                print item, err
                raise IndexError(item)
            else:
                return ret
            
    def __eq__(self, other):
        if not hasattr(other, 'tokens'):
            #print 'can\'t compare: empty model'
            return False
        if self.tokens == other.tokens and (self.tokens != 'CUSTOM'):
            return True
        else:
            return False

    def __ne__(self, other):
        if not hasattr(other, 'tokens'):
            #print 'can\'t compare: empty model'
            return True
        if self.tokens != other.tokens or self.tokens == 'CUSTOM':
            return True
        else:
            return False

    def get_parameter_names(self):
        out = []
        for f in self:
            for name in f.iterkeys():
                if name not in out:
                    out.append(name)
        return out

    def get_parameter_by_name(self, name):
        ret = []
        for f in self:
            for k,v in f.iteritems():
                if k == name:
                    ret.append(v.value)
        return ret

    def get_model_unicode(self):
        return [self.func, self.tokens][int(self.tokens != 'CUSTOM')]

    def parameters_as_csv(self, **args):
        tbl = self.parameters_as_table(**args)
        tbl = '\n'.join([','.join([unicode(y) for y in x]) for x in tbl])
        return tbl
    
    def parameters_as_table(self, selection='all', witherrors=False):
        """\
        Export the model parameters as table. The first columns contains the
        name, the second the value. If the 'selection' is not None, only
        parameters with names given by 'selection' will be exported, e.g. all
        peak positions, when selection = 'pos'
        
        selection: the parameter name as string according to the peak
        definition
        """
        pars = []
        for f in self:
            for name,par in f.items():
                if par.hidden:
                    continue
                if name == selection or selection == 'all':
                    if witherrors:
                        pars.append((f.name,name,par.value,par.error))
                    else:
                        pars.append((f.name,name,par.value))
            if 'area' == selection or selection == 'all':
                if f.area() != N.inf:
                    if witherrors:
                        pars.append((f.name,'area',f.area(),0.0))
                    else:
                        pars.append((f.name,'area',f.area()))

        return [list(x) for x in pars]

    def is_autopickable(self):
        if self.tokens == 'CUSTOM':
            return False
        for f in self:
            if peaks.functions[f.name].picker != peaks.DummyPicker:
                return True
        return False

    def is_empty(self):
        return self.tokens == ''

    def is_filled(self):
        if not self.parsed:
            return False
        else:
            for f in self:
                if not f.is_filled():
                    return False
            return True

    def check(self):
        """\
        Check if the tokens are valid.
        """
        for i in re.split(u'\s+|\*|\+', self.tokens):
            if i not in peaks.functions:
                return False
        return True

    def parse(self):
        """\
        Starts the parser. Needed before every other operation.
        """
        if self.parsed or self.tokens == '':
            return

        try:
            self.parser = TokParser(self, self.tokens, self.func)
            self.parsed = True
        except KeyError:
            pass

    def clear(self):
        """\
        Set all parameters to zero.
        """
        for component in self:
            for el in component.iterkeys():
                component[el].value = 'ns'    
                component[el].error = 0.0   

    def set_parameters(self, param):
        """
Use this function if you want to set the parameter values
by hand.

param: A list - one element for each component - of dictionaries whoose
       keys correspond to the parameter names used in the function
       definition.
"""
        if not self.parsed:
            self.parse()

        count = 0
        for n,component in enumerate(param):
            for key,val in component.items():
                if isinstance(val,Var):
                    self[n][key].value = val.value
                    self[n][key].constr = val.constr
                    self[n][key].amin = val.amin
                    self[n][key].amax = val.amax
                    self[n][key].error = val.error
                else:
                    self[n][key].value = val

    def _newpars(self, a, b):
        """\
        This function should not be called by the user. Use set_parameters
        instead.
        """
        for component in self:
            for key,var in component.items():
                var.value = a[var.count]
                if b is not None:
                    var.error = b[var.count]
        if self.listener is not None:
            self.listener()
                    
    def evaluate(self, x, single=False, addbg=False):
        """\
        Evaluate the current model at positions x.
        single: if True, returns a list of all peaks evaluated
                separately
        """
        
        x = N.atleast_1d(x)
            
        background = None
        
        if self.parsed is False:
            self.parsed = True
            self.parse()

        evaly = []
        newy = []

        glbs = globals().copy()
        glbs.update(N.__dict__)
        
        op = {'*':mul,'+':add,'':add}
        
        for component in self:
            locs = {'x':x}
            for key,val in component.iteritems():
                locs[key] = val.value
            locs.update(peaks.__dict__)
            try:
                if self.func is not None:
                    newy = eval(self.func,glbs,locs)
                else:
                    newy = eval(component.func,glbs,locs)
            except (ValueError, TypeError, ZeroDivisionError),msg:
                pass
            else:   
                if N.logical_not(N.isfinite(newy)).any():
                    tmpy = N.zeros(newy.shape,float)
                    N.put(tmpy, N.isfinite(newy), N.compress(N.isfinite(newy),newy))
                    newy = tmpy
                if single:
                    if component.name in peaks.functions.background:
                        background = newy
                    evaly.append(newy)
                else:
                    if len(evaly) == 0:
                        evaly = newy
                    else:
                        evaly = op[component.op](evaly, newy)   # add or multiply components

        evaly = N.array(evaly)
        if single and addbg:
            for n in range(evaly.shape[0]):
                if background is not None:
                    evaly[n] = evaly[n]+background
            if background is not None:
                evaly = evaly[1:]

        if len(evaly) == 0:
            evaly = False
        return evaly

    def background(self, x):
        out = 0.0
        peaks = self.evaluate(x, single=True)
        if peaks is not False and len(peaks) > 0:
            for p,f in zip(peaks,self):
                if f.is_filled():
                    out += p[0]
                else:
                    break
        return out

    def loadpeaks(self, x, addbg=False):
        if not self.is_filled():
            return []
        lines = []

        ys = self.evaluate(x, single=True, addbg=addbg)
        for y in ys:
            points = N.array([x,y])
            lines.append(points)

        return lines

class TokParser(object):
    tokre = re.compile(r"([+*\s]*)([A-Z]+[0-9]*)")
    
    def __init__(self, model, pstr, fstr=None):
        self.model = model
        self.pstr = pstr
        self.fstr = fstr
        self.ntok = 0
        self.parse()
        self.parsed = True
        
    def funcstr(self, scanner, name):
        mat = self.tokre.match(name)
        op,tok = mat.groups()
        if op in ['',' ']:
            op = '+'
        self.ntok += 1
        if not tok.isupper() or tok == 'CUSTOM':
            return self.fstr,op
        else:
            return tok,op

    def parse(self):
        self.function = ''
        
        scanner = Scanner([
            (r"[\+\*\s]*[A-Z]+[0-9]*", self.funcstr),
            (r"\+|\*", lambda y,x: x),
            (r"\s+", None),
            ])

        count = 0
        parsed,rubbish = scanner.scan(self.pstr)

        if rubbish != '':
            raise Exception, 'parsed: %s, rubbish %s'%(parsed, rubbish)

        for tok,op in parsed:
            comp = Component(tok, op, count)
            self.model.append(comp)
            count += len(comp)
        
class Component(dict):
    def __init__(self, tok, op, count):
        self.name = tok
        self.op = op
        try:
            self.func = peaks.functions[tok].func
        except KeyError:
            self.func = tok
            self.name = 'CUSTOM'
        self.dummy = []
        self.par_count_start = count
        self.count = count
        dict.__init__(self)
        self.parse()

    def clear(self):
        for k in self.iterkeys():
            self[k].value = 'ns'
            self[k].error = 0.0

    def var_found(self,scanner,name):
        if name in ['caller','e','pi']:
            return name
        if name not in self.keys():
            self[name] = Var('ns', count=self.count)
            self.dummy.append(name)
            ret = 'a[%d]'%self.count
            self.count += 1
        else:
            ret = 'a[%d]'%(self.dummy.index(name)+self.par_count_start)
        return ret
            
    def parse(self):
        scanner = Scanner([
            (r"x", lambda y,x: x),
            (r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?", lambda y,x: x),
            (r"[a-zA-Z]+\.", lambda y,x: x),
            (r"[a-z]+\(", lambda y,x: x),
            (r"[a-zA-Z_]\w*", self.var_found),
            #(r"\d+\.\d*", lambda y,x: x),
            (r"\d+", lambda y,x: x),
            (r"\+|-|\*|/", lambda y,x: x),
            (r"\s+", None),
            (r"\)+", lambda y,x: x),
            (r"\(+", lambda y,x: x),
            (r",", lambda y,x: x),
            ])

        parsed,rubbish = scanner.scan(self.func)
        parsed = ''.join(parsed)
        if rubbish != '':
            raise Exception, 'parsed: %s, rubbish %s'%(parsed, rubbish)

        #self.code = compile(parsed, '<string>', 'eval')
        self.code = parsed

    def __getattr__(self, attr):
        if attr in self.keys():
            return self[attr]
        else:
            raise AttributeError, '%s has no Attribute \'%s\''%(self,attr)

    def __setattr__(self, attr, value):
        if attr in self.keys():
            raise AttributeError, '''\
<Component object> does not allow to overwrite \'%s\' attribute.
Use \'%s.value\' instead.'''%(attr,attr)
        else:
            dict.__setattr__(self, attr, value)

    def is_filled(self):
        for k,v in self.items():
            if v.value == 'ns':
                return False
        return True

    def val(self, vardic):
        for k,v in vardic.iteritems():
            self[k].value = v

    def area(self):
        if self.name not in peaks.functions.peak:
            return N.inf
        locs = {}
        for key,val in self.items():
            locs[key] = val.value
        locs.update(peaks.__dict__)
        glbs = globals().copy()
        glbs.update(N.__dict__)
        try:
            x = eval('N.arange(pos-12*fwhm,pos+12*fwhm,fwhm/50.0)',glbs,locs)
        except:
            return N.inf
        else:
            locs['x'] = x
            try:
                y = eval(peaks.functions[self.name].func,glbs,locs)
            except ValueError:
                return N.inf
            else:
                dx = x[1:]-x[:-1]
                dy = (y[1:]+y[:-1])/2.0
                integ = sum(dy*dx)
                return integ

class Var(object):
    def __init__(self, value, error=0.0, count=0, constr=0, bounds=False, hidden=False):
        self.value = value
        self.error = error
        self.constr = constr
        self.count = count
        self.hidden = hidden
        if constr == 2:
            if type(bounds) not in [tuple, list]:
                raise TypeError, 'need upper and lower bounds as tuple'
            self.amin = bounds[0]
            self.amax = bounds[1]
        else:
            self.amin = 'ns'
            self.amax = 'ns'

    def _coerce(self):
        if self.constr != 2:
            return self.value
        else:
            eps = 1e-16
            t = (self.value - (self.amin+self.amax)/2.0)/((self.amax-self.amin)/2.0)
            return (-1/(t-1*(2*(t>0)-1))-1*(2*(t>0)-1))

    def _decoerce(self, arg):
        if self.constr != 2:
            self.value = arg
        else:
            t = arg/(abs(arg)+1.0)
            self.value = (self.amin+self.amax)/2.0+(self.amax-self.amin)/2.0*t
        
    value_mapped = property(_coerce, _decoerce)

class curry_var(object):
    def __init__(self, var):
        self.amin = var.amin
        self.amax = var.amax
    def __call__(self, arg):
        t = arg/(abs(arg)+1.0)
        out = (self.amin+self.amax)/2.0+(self.amax-self.amin)/2.0*t
        return out
    
class QuickEvaluate(object):
    def __init__(self, model):
        self.model = model
        self.pre_fit()
        
    def pre_fit(self):
        func = ''
        replace = re.compile(r'(c)(?=[^a-zA-Z0-9])')
        for component in self.model:
            func += component.op+component.code
        self.func = compile(func, '<string>', 'eval')

        self.par_all = {}
        self.par_fit = {}
        self.par_demap = {}

        eps = 1e-6
        for component in self.model:
            for name,var in component.items():
                self.par_all[var.count] = var.value_mapped
                if var.constr == 0:
                    self.par_fit[var.count] = var.value
                elif var.constr == 2:
                    self.par_fit[var.count] = var.value_mapped
                    self.par_demap[var.count] = curry_var(var)

    def fill(self, a, b):
        pars = N.array(self.par_all.values())
        N.put(pars, self.par_fit.keys(), a)
        for k,v in self.par_demap.iteritems():
            pars[k] = v(pars[k])

        errors = N.zeros(pars.shape)
        N.put(errors, self.par_fit.keys(), b)
        return pars, errors
                    
    def __call__(self, x, a):
        fitpars = N.array(self.par_all.values())
        N.put(fitpars, self.par_fit.keys(), a)
        for k,v in self.par_demap.iteritems():
            fitpars[k] = v(fitpars[k])
            
        locs = locals().copy()
        locs['a'] = fitpars
        locs.update(peaks.__dict__)
        glbs = globals().copy()
        glbs.update(N.__dict__)
        
        return eval(self.func, glbs, locs)

def test1():
    import numpy as N
    import pylab as P
    mod = Model('a*x**2+b*x+c')
    mod.CUSTOM.a.value = 3
    mod.CUSTOM.b.value = 2
    mod.CUSTOM.c.value = -1

    x = N.linspace(0,3,30)
    y = mod.evaluate(x)
    P.plot(x,y)
    P.show()
    
def test2():
    import pylab as P
    import numpy as N

    from spec import Spec
    from fit import Fit
    
    ruby = Spec('../data/ruby.dat')
    ruby.limits = (6932.5,6945)
    a = Model('CB GA LO')

    a.LO.val({'amp':2.0,'fwhm':1.0,'pos':6944})
    a.GA.val({'amp':1.0,'fwhm':2.0,'pos':6934})
    a.CB.val({'const':0.0})
    
    P.plot(ruby.x,ruby.y,'ro',label='data')
    xmin,xmax = ruby.xrng
    x = ruby.x_limited
    y = a.evaluate(x)
    P.plot(x,y,label='initial guess',linewidth=2)

    fitter = Fit(ruby, a)
    msg = fitter.run()
    print msg
    print a.parameters_as_csv(witherrors=True)
    
    y = a.evaluate(x)
    P.plot(x,y,label='fit',linewidth=2)
    P.legend(loc=0)
    P.show()

class Dummy:
    def run(self):
        for i in range(1000000):
            float(i)**2
        return 'finished'
        
def tester():
    from spec import Spec
    from fit import Fit
    #import pylab
    #import numpy as N
    
    guess = [-0.00223424709178,	0.399642288964,	0.7924511231,	4.98397478171,
             295.878115142,	1.39757418222,	8.43441886136,	283.22648685,
             0.367868351203,	4.98397478171,	264.057353074,	0.179183894139,
             7.28427083481,	251.405724782,	0.903054324102,	11.11809759,
             191.981410077,	0.276354863517,	4.60059210619,	182.396843189
             ]

    dic = [('LB',['lin','const'])]+[('LO%d'%(i+1),['amp','fwhm','pos']) for i in range(6)]

    mod = Model('LB LO1 LO2 LO3 LO4 LO5 LO6')
    mod.parse()
    for f,pars in dic:
        for p in pars:
            val = guess.pop(0)
            getattr(getattr(mod,f),p).value = val

    #x = N.linspace(100,400,1024)
    #y = mod.evaluate(x)
    #pylab.plot(x,y)
    set = Spec('../data/1.92RBM.dat')
    #pylab.plot(set.x,set.y)
    #pylab.show()
    return Fit(set, mod, stepsize=1e-15)

def _test4():
    import wx
    from wx.lib.evtmgr import eventManager as em
    
    import numpy as N
    import time
    from misc import WorkerThread
    
    from spec import Spec
    from fit import Fit
    import misc
    import copy

    import pylab
    
    class TestFrame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, None, -1 ,'testing')
            self.panel = wx.Panel(self, -1)
            self.btnfork = wx.Button(self.panel, -1, 'fork', pos = (100,100), size=(100,30))
            self.btnfork.Bind(wx.EVT_BUTTON, self.fork)
            self.btnrun = wx.Button(self.panel, -1, 'run', pos = (100,140), size=(100,30))
            self.btnrun.Bind(wx.EVT_BUTTON, self.run)
            em.Register(self.fertig, misc.EVT_RESULT, self)
            self.fitter = Dummy()
            self.Show()
            
        def run(self, evt):
            print 'start fit'
            self.btnfork.Disable()
            wx.Yield()
            print self.fitter.run()
            wx.Yield()
            self.btnfork.Enable()
            wx.Yield()

        def fork(self, evt):
            print 'start fit'
            self.btnfork.Disable()
            w = WorkerThread(self, self.fitter)
            w.start()

        def fertig(self, evt):
            self.btnfork.Enable()
            print evt.result

    app = wx.PySimpleApp(0)
    frame = TestFrame()
    app.MainLoop()

def test5():
    import time
    t = tester()
    start = time.time()
    t.run()
    print '%.2f seconds'%(time.time()-start)

def test6():
    a = Model('a*x+b*x**2+c')
    a.parse()
    print a
    a = Model('CB')
    a.parse()
    print a
    for i in a:
        print i
        
def prof_fit():
    import profile
    import pstats
    t = tester()
    profile.runctx('t.run()',globals(),{'t':t},'modelprof')
    p = pstats.Stats('modelprof')
    p.strip_dirs()
    p.sort_stats('cumulative')
    p.print_stats()

def mod():
    a = Model('CB GA1 LO1 FAN LO VO GA')
    a.parse()
    for c in a:
        print c.name,len(c),c.code

    #a = Model('sin(x-pos)**2')
    #a.parse()
    #print a
    #for c in a:
    #    print c.name,len(c),c.code
    
def prof_mod():
    import profile
    import pstats
    profile.run('mod()','modelprof')
    p = pstats.Stats('modelprof')
    p.strip_dirs()
    p.sort_stats('cumulative')
    #p.sort_stats('name')
    p.print_stats()
    
def sym():
    mod = []
    a = SymParser(mod, ['amp*exp(x-a)','+GA'])
    a.parse()
    print mod

def prof_sym():
    import profile
    import pstats
    profile.run('sym()','modelprof')
    p = pstats.Stats('modelprof')
    p.strip_dirs()
    p.sort_stats('cumulative')
    #p.sort_stats('name')
    p.print_stats()

def comp():
    for i in range(100):
        a = Component('GA','+',0)
    
def prof_comp():
    import profile
    import pstats
    profile.run('comp()','comp')
    p = pstats.Stats('comp')
    p.strip_dirs()
    p.sort_stats('cumulative')
    p.print_stats()

if __name__ == '__main__':
    testfit()
    
