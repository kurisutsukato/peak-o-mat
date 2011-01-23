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

import numpy as N
from scipy import special
from scipy.integrate import trapz

from peaksupport import *

def lbstep(x,amp,pos,sigma,sigmap=100.0):
    """\
lorentian broadened step function

caution: this function implies numerical convolution which is
computationally intensive
    """ 
    if len(x) == 1:
        dx = x[0]*0.1
    else:
        dx = x[-1]-x[0]
    up = x[-1]+5*dx
    lo = x[0]-5*dx
    f = amp/N.pi
    xp = N.linspace(lo,up,1000.0)[:,N.newaxis]
    s2 = N.power(sigma,2)
    i = trapz(sigma/(N.power(x-xp,2)+s2)/(1+N.exp(-sigmap*(xp-pos))), xp, axis=0)
    return f*i

def gbstep(x,amp,pos,sigma,sigmap=100.0):
    """\
gaussian broadened step function

caution: this function implies numerical convolution which is
computationally intensive
    """
    f = amp/N.sqrt(2*N.pi)/sigma
    s2 = 2*N.power(sigma,2)
    if len(x) == 1:
        dx = x[0]*0.1
    else:
        dx = x[-1]-x[0]
    up = x[-1]+5*dx
    lo = x[0]-5*dx
    xp = N.linspace(lo,up,1000.0)[:,N.newaxis]
    i = trapz(N.exp(-N.power(x-xp,2)/s2)/(1+N.exp(-sigmap*(xp-pos))), xp, axis=0)
    return f*i

def voigt(x,amp,pos,fwhm,shape):
    """\
voigt profile

V(x,sig,gam) = Re(w(z))/(sig*sqrt(2*pi))
z = (x+i*gam)/(sig*sqrt(2))
    """
    tmp = 1/special.wofz(N.zeros((len(x))) +1j*N.sqrt(N.log(2.0))*shape).real
    return tmp*amp*special.wofz(2*N.sqrt(N.log(2.0))*(x-pos)/fwhm+1j*N.sqrt(N.log(2.0))*shape).real

def sdec(x, amp, tau, beta):
    """\
stretched exponential decay
    """
    y = amp*N.exp(-N.power(x/tau,beta))*(x>=0)
    tmp = N.zeros(x.shape,dtype=float)
    mask = N.compress(N.isfinite(y),N.arange(len(y),dtype=int))
    N.put(tmp, mask, N.compress(N.isfinite(y),y))
    return tmp

add('CB',
    func='const+0*x',
    info='constant background', 
    picker=CBPicker, 
    ptype=ptype.BACKGROUND)

add('LB',
    func='const+lin*x',
    info='linear background', 
    picker=LBPicker, 
    ptype=ptype.BACKGROUND)

add('QB',
    func='a*x**2+b*x+c',
    info='quadratic background', 
    picker=QBPicker, 
    ptype=ptype.BACKGROUND)

add('GA',
    func='amp*N.exp(-(N.power(x-pos,2)/(fwhm*fwhm/4.0/N.log(2.0))))',
    info='symmetric gaussian', 
    picker=LOPicker,
    ptype=ptype.PEAK)

add('LO',
    func='amp/(1+N.power((x-pos)/(fwhm/2.0),2))',
    info='symmetric lorentzian', 
    picker=LOPicker, 
    ptype=ptype.PEAK)

add('FAN',
    func='amp*N.power((1+(x-pos)/(fwhm/2)*shape),2)/(1+N.power((x-pos)/(fwhm/2),2))',
    info='fano lineshape', 
    picker=FANPicker, 
    ptype=ptype.PEAK)

add('VO',
    func='voigt(x,amp,pos,fwhm,shape)',
    info=voigt.__doc__, 
    picker=FANPicker, 
    ptype=ptype.PEAK)

add('PSV',
    func='amp*(shape*N.exp(-2/N.pi*N.power((x-pos)/(fwhm/2),2))+(1-shape)/(1+N.power((x-pos)/(fwhm/2),2)))',
    info='pseudo voigt profile', 
    picker=FANPicker, 
    ptype=ptype.PEAK)

add('DEC',
    func='amp*N.exp(-x/tau)',
    info='exponential decay',
    ptype=ptype.EXP,
    picker=EXPPicker)

add('RISE',
    func='1.0-N.exp(-x/tau)',
    info='exponential rise', 
    ptype=ptype.EXP)

add('SDEC',
    func='sdec(x,amp,tau,beta)',
    info='stretched exponential decay', 
    ptype=ptype.EXP,
    picker=SEXPPicker)

add('RRP',
    func='c/((N.power(x-Eii,2)+N.power(g,2)/4)*(N.power(x-EPhonon-Eii,2)+N.power(g,2)/4))',
    info='resonant Raman profile. Phonon energy in eV',
    ptype=ptype.MISC)

add('RRPO',
    func='c/((N.power(x-Eii,2)+N.power(g,2)/4)*(N.power(x-1.2398418573430596e-6*Omega*1e2-Eii,2)+N.power(g,2)/4))',
    info='resonant Raman profile. Phonon energy in cm^-1', 
    ptype=ptype.MISC)

add('LBSTP',
    info=lbstep.__doc__,
    func='lbstep(x, amp, pos, sigma)',
    picker=STEPPicker,
    ptype=ptype.MISC)

add('GBSTP',
    info=gbstep.__doc__,
    func='gbstep(x, amp, pos, sigma)',
    picker=STEPPicker,
    ptype=ptype.MISC)

