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

import re
import sys
import numpy as N
from numpy.linalg import solve

class StripDict(dict):
    """\
    Special dict which strips a trailing number from the item
    name. This was added to support numbering of tokens, e.g. LO1 GA1 LO2
    """
    def __contains__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return dict.__contains__(self, name)
    def __getitem__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return dict.__getitem__(self, name)

class StripList(list):
    """\
    Special list which strips a trailing number from the item
    name. This was added to support numbering of tokens, e.g. LO1 GA1 LO2
    """
    def __contains__(self, name):
        name = re.sub(r'[0-9]*','',name,re.UNICODE)
        return list.__contains__(self, name)
    def __getitem__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return list.__getitem__(self, name)

class Cmd(list):
    def __repr__(self):
        a = self+[]
        try:
            a.remove('m')
        except:
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
    def __init__(self, component, background_cb):
        list.__init__(self, [(Cmd('xy'),self.amp_pos),(Cmd('mx'),self.sigma)])
        self.f = component
        self.background_cb = background_cb

    def amp_pos(self, xy):
        x,y = xy
        if not hasattr(self, 'bg'):
            self.bg = self.background_cb(x)
        self.f['sigma'].value = 0.05
        self.f['pos'].value = x
        self.tmp = x
        self.f['amp'].value = (y-self.bg)*2

    def sigma(self, x):
        x = N.abs(self.tmp-x)
        self.f['sigma'].value = max(0.05,x/2.0)

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
        t = (self.x1 - x2)/N.log(y2/self.y1)
        a = self.y1/N.exp(-self.x1/t)
        if not N.isnan(a):
            self.f['amp'].value = a
        if not N.isnan(t):
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
        t = (self.x1 - x2)/N.log(y2/self.y1)
        a = self.y1/N.exp(-self.x1/t)
        if not N.isnan(a):
            self.f['amp'].value = a
        if not N.isnan(t):
            self.f['tau'].value = t
        self.f['beta'].value = 1

    def c(self, x):
        self.f['beta'].value = N.exp(-abs(self.x2-x))


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
        self.f['shape'].value = (N.arctan((x-self.x)/self.f['fwhm'].value)/N.pi)**2*2

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
        self.x = N.zeros((3,),dtype=N.float32)
        self.y = N.zeros((3,),dtype=N.float32)

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
        a = N.column_stack((self.x[:2],[1,1]))
        b = self.y[:2]
        b, c = solve(a,b)
        self.f['c'].value = c
        self.f['b'].value = b
        
    def a(self, xy):
        x,y = xy
        self.x[2] = x
        self.y[2] = y
        a = N.column_stack((self.x**2,self.x,[1,1,1]))
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
            print 'zero div'
            return
        self.f['const'].value = const
        self.f['lin'].value = lin

class PeakType(list):
    def __init__(self):
        list.__init__(self, [('BACKGROUND', 0),
                             ('PEAK', 1),
                             ('EXP', 2),
                             ('MISC', 3)
                             ])

    def __getattr__(self, attr):
        for name,val in self:
            if name == attr:
                return val
        raise

ptype = PeakType()

class Function:
    picker = DummyPicker
    info = 'no description available'
    
    def __init__(self, **kwargs):
        for k,v in kwargs.iteritems():
            setattr(self, k, v)
        try:
            setattr(self, 'code', compile(self.func,'<string>','eval'))
        except:
            tp,msg,tb = sys.exc_info()
            print tp,msg,'in user func',self.func
        return
        try:
            mod = Model(kwargs['func'])
            mod.parse()
            for k,v in mod[0].iteritems():
                mod[0][k].value = 0.0
            x = N.linspace(0,1,10)
            y = mod.evaluate(x)
        except:
            tp,val,tb = sys.exc_info()
            print 'error in model \'%s\': %s'%(kwargs['func'],val)
            raise



class Functions(StripDict):
    def __init__(self, data):
        StripDict.__init__(self, data)
        self.setup()
        
    def setup(self):
        self.auto = []
        for k,v in self.iteritems():
            if v.picker is not DummyPicker and k not in self.auto:
                self.auto.append(k)
        self.auto = StripList(self.auto)
        
        self.background = []
        for k,v in self.iteritems():
            if v.ptype == ptype.BACKGROUND and k not in self.background:
                self.background.append(k)
        self.background = StripList(self.background)

        self.peak = []
        for k,v in self.iteritems():
            if v.ptype == ptype.PEAK and k not in self.peak:
                self.peak.append(k)
        self.peak = StripList(self.peak)

    def group(self, id):
        """\
        returns the list of peak symbols belonging to
        group 'id' (either ptype.BACKGROUND,PEAK,EXP,ptype.HIDDEN,SPECIAL)
        """
        out = []
        for k,v in self.iteritems():
            if v.ptype == id:
                out.append(k)
        out.sort()
        return StripList(out)

def add(name, **kwargs):
    #kwargs['ptype'] = eval('ptype.%s'%kwargs['ptype'])
    functions.update({name:Function(**kwargs)})
    functions.setup()

functions = Functions({})        
