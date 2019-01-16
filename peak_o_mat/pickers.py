__author__ = 'kristukat'

import numpy as np
from numpy.linalg import solve

class Cmd(list):
    def __repr__(self):
        a = self[:]
        try:
            a.remove('m')
        except ValueError:
            pass
        return ''.join(a)

    def stripm(self):
        a = self[:]
        try:
            a.remove('m')
        except ValueError:
            pass
        return ''.join(a)

class DummyPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self)
        pass

class LOPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.amp_pos),(Cmd('mx'),self.fwhm)])
        self.f = component
        self.background_cb = background_cb

    def amp_pos(self, xy):
        x, y = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x)
        self.f['pos'].value = x
        self.f['amp'].value = y-self.bg

    def fwhm(self, x):
        self.f['fwhm'].value = x-self.f['pos'].value

GAPicker = LOPicker

class STEPPicker(list):
    _sigma = 'sigma'
    _pos = 'pos'
    _amp = 'amp'

    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.amp_pos),(Cmd('mx'),self.sigma)])
        self.f = component
        self.background_cb = background_cb

    def amp_pos(self, xy):
        x,y = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x)
        self.f[self._sigma].value = 0.01
        self.f[self._pos].value = x
        self.tmp = x
        self.f[self._amp].value = (y-self.bg)*2

    def sigma(self, x):
        x = np.abs(self.tmp-x)
        self.f[self._sigma].value = max(0.01,x/2.0)

class FERMIPicker(STEPPicker):
    _sigma = 'T'
    _pos = 'energy'

    def amp_pos(self, xy):
        x,y = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x)
        self.f[self._sigma].value = 20.0
        self.f[self._pos].value = x
        self.tmp = x
        self.f[self._amp].value = (y-self.bg)*2

    def sigma(self, x):
        x = self.tmp-x
        self.f[self._sigma].value = -x*1000

class EXPPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.a),(Cmd('mxy'),self.b)])
        self.f = component
        self.background_cb = background_cb

    def a(self, xy):
        x1, y1 = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x1)
        self.x1 = x1
        self.y1 = y1-self.bg

    def b(self, xy):
        x2, y2 = xy
        y2 = y2-self.bg
        t = (self.x1 - x2)/np.log(y2/self.y1)
        a = self.y1/np.exp(-self.x1/t)
        if not np.isnan(a):
            self.f['amp'].value = a
        if not np.isnan(t):
            self.f['tau'].value = t

class SEXPPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.a),(Cmd('mxy'),self.b),(Cmd('mx'),self.c)])
        self.f = component
        self.background_cb = background_cb

    def a(self, xy):
        x1, y1 = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x1)
        self.x1 = x1
        self.y1 = y1-self.bg

    def b(self, xy):
        x2, y2 = xy
        y2 = y2-self.bg
        self.x2 = x2
        t = (self.x1 - x2)/np.log(y2/self.y1)
        a = self.y1/np.exp(-self.x1/t)
        if not np.isnan(a):
            self.f['amp'].value = a
        if not np.isnan(t):
            self.f['tau'].value = t
        self.f['beta'].value = 1

    def c(self, x):
        self.f['beta'].value = np.exp(-abs(self.x2-x))


class FANPicker(list):
    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.amp_pos),(Cmd('mx'),self.fwhm),(Cmd('mx'),self.shape)])
        self.f = component
        self.background_cb = background_cb

    def amp_pos(self, xy):
        x, y = xy
        self.f['pos'].value = x
        self.f['amp'].value = y-self.background_cb(x)

    def fwhm(self, x):
        self.f['fwhm'].value = abs(x-self.f['pos'].value)
        self.x = x
        self.f['shape'].value = 0

    def shape(self, x):
        self.f['shape'].value = (np.arctan((x-self.x)/self.f['fwhm'].value)/np.pi)**2*2

class CBPicker(list):
    def __init__(self, component, cb):
        list.__init__(self, [(Cmd('my'),self.const)])
        self.f = component

    def const(self, y):
        self.f['const'].value = y
        list.__init__(self, [(Cmd('my'),self.const)])

class QBPicker(list):
    def __init__(self, component, cb):
        list.__init__(self, [(Cmd('mxy'),self.c),(Cmd('mxy'),self.b),(Cmd('mxy'),self.a)])
        self.f = component
        self.x = np.zeros((3,),dtype=np.float32)
        self.y = np.zeros((3,),dtype=np.float32)

    def c(self, xy):
        x,y = xy
        self.x[0] = x
        self.y[0] = y
        self.f['c'].value = y
        self.f['b'].value = 0
        self.f['a'].value = 0

    def b(self, xy):
        x,y = xy
        self.x[1] = x
        self.y[1] = y
        a = np.column_stack((self.x[:2],[1,1]))
        b = self.y[:2]
        b, c = solve(a,b)
        self.f['c'].value = c
        self.f['b'].value = b

    def a(self, xy):
        x,y = xy
        self.x[2] = x
        self.y[2] = y
        a = np.column_stack((self.x**2,self.x,[1,1,1]))
        b = self.y
        a, b, c = solve(a,b)
        self.f['c'].value = c
        self.f['b'].value = b
        self.f['a'].value = a

class LBPicker(list):
    def __init__(self, component, cb):
        list.__init__(self, [(Cmd('mxy'),self.const),(Cmd('mxy'),self.slope)])
        self.f = component

    def const(self, xy):
        self.x1, self.y1 = xy
        self.f['const'].value = self.y1
        self.f['lin'].value = 0.0

    def slope(self, xy):
        x2, y2 = xy
        try:
            lin = (y2-self.y1)/(x2-self.x1)
            const = self.y1 - lin*self.x1
        except ZeroDivisionError:
            print('zero div')
            return
        self.f['const'].value = const
        self.f['lin'].value = lin
