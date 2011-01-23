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

from scipy.interpolate import interp1d

import copy
import re
import string
import types
import os, sys, locale
import time

import settings as config
from misc import PomError

from wx.lib.pubsub import pub as Publisher

class TrafoList(list):
    def __iter__(self):
        for x in range(len(self)):
            yield self[x]
            
    def __getitem__(self, item):
        data = list.__getitem__(self, item)
        if len(data) == 3:
            data = list(data)+[False]
        return data

    def __setitem__(self, item, value):
        list.__setitem__(self, item, value)
        Publisher.sendMessage(('changed'))

    def append(self, data):
        list.append(self, data)
        Publisher.sendMessage(('changed'))
        
class Spec(object):
    """
A class for storing spectral data. Spec arithmetics using +-/* act only on the y-values
like one expects when e.g. subtracting two spectra.  Interpolation is
done automatically if the x-values differ. 

"""
    truncated = False

    def __init__(self, *args):
        """
Spec(name)
name: load 2-column table data from file 'name'

Spec(x,y,name)
x: array/list with x-data
y: array/list with y-data
name: desired name
"""
        self.hide = False
        
        self._inverse = False
        self._mod = None
        self._weights = None
        self._limits = None
        self._trafo = TrafoList([])
        self._mask = N.zeros((0), dtype=N.int8)
        self._rawdata = N.empty((0,0),dtype=N.float64)

        self.parse_args(*args)

    def parse_args(self, *args):
        if len(args) == 3:
            x,y,name = args
            data = N.array([x,y])
            self.data = data.take(data[0].argsort(),1)
        elif len(args) == 1:
            if isinstance(args[0], Spec):
                self.data = args[0].xy.copy()
                self.mod = copy.deepcopy(args[0].mod)
                name = 'copy_of_'+args[0].name
            elif type(args[0]) in [str,unicode]:
                name = os.path.basename(args[0])
                base, suf = os.path.splitext(args[0])
                if suf == '.ms0':
                    self.data = self.read_ms0(args[0])
                else:
                    data = self.read(args[0])
                    self.data = data.take(data[0].argsort(),1)
            else:
                raise TypeError, 'wrong arguments'+self.__init__.__doc__
        else:
            raise TypeError, 'wrong arguments'+self.__init__.__doc__

        if config.truncate:
            self.truncate()
        
        self.name = name
        self.mask = N.zeros(self.data.shape[1])
        #print 'spec.x increasing', reduce(lambda x,y: y if x<= y else N.inf, self.x) != N.inf
        
    def truncate(self):
        pts = config.truncate_max_pts
        if len(self.data[0]) > pts:
            self.truncated = True
            if not hasattr(config, 'interpolate'):
                config.interpolate = False
            
            if not config.interpolate:
                l = len(self.data[0])
                if l > pts:
                    inc = float(l)/float(pts) 
                    at = N.arange(0.0, l, inc, float).astype(int)
                    self.data = self.data.take(at, 1)
            else:
                a,b = min(self.data[0])+1e-2,max(self.data[0])-1e-2
                x = N.arange(a,b,(b-a)/pts)
                interpolate = interp1d(self.data[0], self.data[1])
                y = interpolate(x)
                self.data = N.array([x,y])

    def __copy__(self):
        return Spec(self.x.copy(), self.y.copy(), 'copy_%s'%self.name)

    def write(self, path, overwrite=True):
        """
writes the current spectrum data in two columns
path : obviously, the path
"""
        try:
            exists = os.path.exists(path)
        except:
            exists = os.path.exists(path.encode('mbcs'))
            
        if exists and not overwrite:
            #print 'file \'%s\' exists and overwrite mode is False'%path
            return False
        try:
            f = open(path, 'w')
        except IOError:
            print 'unable to access %s' % (path)
            return False
        
        data = N.transpose(N.array([self.x,self.y]))
        if config.floating_point_is_comma:
            data = [[('%.15g'%x).replace('.',','),('%.15g'%y).replace('.',',')] for x,y in data]
        for x,y in data:
            f.write('%s\t%s\n'%('%.15g'%x,'%.15g'%y))
        f.close()
        return True
        
    def read_ms0(self, path):
        data = []
        try:
            f = open(path, "r")
        except IOError:
            print path, 'not found'
            return 0,0
        for line in f:
            if line.find(r'"') != 0:
                data.append(float(line))
        l = len(data)/2
        data = N.transpose(N.resize(N.array(data), (l, 2)))

        return data
            
    def read(self, path):
        data = []
        self.path = path

        try:
            f = open(path.encode(sys.getfilesystemencoding()))
        except IOError:
            raise PomError,'unable to open \'%s\''%path

        if config.floating_point_is_comma:
            delimiters = [r'\s+',';','\t']
        else:
            delimiters = [r'\s+',',',';','\t']
    
        found = False
        for i in range(20):
            # maybe there is a header, so try the first 20 lines
            line = f.readline().strip()

            # try to guess the delimiter
            for delimiter in delimiters:
                try:
                    [float(x.strip()) for x in re.split(delimiter,line)][1]
                except ValueError:
                    pass # non float data
                except IndexError:
                    pass # less than 2 columns
                else:
                    found = True
                    break
            if found:
                break
        if not found:
            raise PomError('unable to parse \'%s\''%path)

        #print 'delimiter',delimiter
        #print 'data starts at',i

        mat = re.compile(delimiter)
        while line != "":
            out = [x.strip() for x in mat.split(line.strip())]
            if len(out) >= 2:
                data.append(out)
            line = f.readline()
        f.close()

        try:
            data = [[float(x) for x in line] for line in data]
        except ValueError:
            data = [[float(x.replace(',','.')) for x in line] for line in data]
            config.floating_point_is_comma = True

        if len(data) == 0:
            raise PomError, 'unable to parse %s'%path

        return N.transpose(data)[:2] # ignore additional columns

    def __boundingBox(self):
        """\
returns boundingBox of the data as
"""
        minXY = N.minimum.reduce(N.transpose([self.x,self.y]))
        maxXY = N.maximum.reduce(N.transpose([self.x,self.y]))
        return minXY,maxXY

    def crop(self, xrng, cp=False):
        a,b = N.searchsorted(self.data[0], xrng)
        if cp:
            x,y = self.data[:,a:b+1]
            return Spec(x,y,'cropped_%s'%self.name)
        else:
            self.data = self.data[:,a:b+1]
        
    def derivate(self, cp=False):
        """\
calculates the derivative
"""
        x = (self.x[1:]+self.x[:-1])/2.0
        y = (self.y[1:]-self.y[:-1])
    
        dy = y/(self.x[1:]-self.x[:-1])
        if cp:
            return Spec(x,dy,'d_dx_%s'%self.name)
        else:
            self.data = N.array([x,dy])
            self.mask = None
            self.trafo = None
            return None
        
    def average(self, avg, cp=False):
        """
Smoothes the data by averageing neighbouring points.
avg : number of points to average
"""
        l = len(self.y)
        newy = N.zeros((0,l-avg))
        newx = []
        for i in range(avg):
            newy = N.concatenate((newy,N.reshape(self.y[i:l-avg+i], (1,l-avg))))
        newy = sum(newy)/avg
        s = avg/2
        e = avg-s
        newx = self.x[s:-e]
        if cp:
            return Spec(newx,newy, '%dpt_avg_%s'%(avg, self.name))
        else:
            self.data = N.array([newx, newy])
            return None
        
    def sg_filter(self, window, order, cp=False):
        newy = savitzky_golay(self.y, window, order)
        if cp:
            return Spec(self.x, newy, 'SGfiltered_%s'%self.name)
        else:
            self.data = N.array([self.x, newy])
            return None

    def interpolate(self, x, cp=False):
        """
returns the interpolation of the y-data at the given positions.
'x' can be either a scalar or an array.
"""
        interpolate = interp1d(self.x, self.y)
        interp = interpolate(x)
        if cp:
            return Spec(x,interp, '%dpts_interp_%s'%(len(x), self.name))
        else:
            self.data = N.array([x,interp],dtype=N.float64)
            return None

    def norm(self, cp=False):
        """
normalize the y-values to 1
"""
        y = N.array(self.y/max(self.y))
        if cp:
            return Spec(self.x,y,'norm_'+self.name)
        else:
            self.data = N.array([self.x,y])
            return None

    def delete(self, bbox):
        """
Deletes data points within bounding box.
bbox : boundingbox of points to be removed
"""
        bbx,bby = N.transpose(bbox)
        bbx = N.searchsorted(self._x, bbx)
        mask = N.zeros(self._x.shape)
        for x,y in enumerate(self._y[bbx[0]:bbx[1]]):
            if bby[0] < y < bby[1]:
                mask[x+bbx[0]] = 1
        if self._inverse:
            mask = mask[::-1]
        self.mask = N.logical_or(self.mask, mask).astype(int)
            
    def loadpeaks(self, mod=None, addbg=False):
        if mod is None:
            mod = self._mod
        peaks = mod.loadpeaks(self.x, addbg=addbg)
        return peaks

    def _getxrange(self):
        return N.minimum.reduce(self.x),N.maximum.reduce(self.x)
    xrng = property(_getxrange, doc='data\'s xrange as 2-tuple')

    def _getyrange(self):
        return N.minimum.reduce(self.y),N.maximum.reduce(self.y)
    yrng = property(_getyrange, doc='data\'s yrange as 2-tuple')

    def _getxyrange(self):
        return self.xrng, self.yrng
    rng = property(_getxyrange, doc='data\'s x/y range as 2x2-tuple')

    def _storeWeights(self, weights):
        self._weights = copy.deepcopy(weights)
    def _getWeights(self):
        return self._weights
    weights = property(_getWeights, _storeWeights, doc='y-weight')
    
    def _set_limits(self, limits=None):
        if type(limits) not in [tuple,type(None),N.ndarray,list]:
            raise TypeError, 'limits: tuple or None required'
        self._limits = limits
    def _get_limits(self):
        return self._limits
    limits = property(_get_limits, _set_limits, doc='x limits')

    def _get_trafo(self):
        return self._trafo
    def _set_trafo(self, trafo):
        if type(trafo) != list:
            self._trafo = TrafoList([])
        else:
            self._trafo = TrafoList(trafo)
    trafo = property(_get_trafo, _set_trafo, doc='list of transformations')

    def _get_mod(self):
        return self._mod
    def _set_mod(self, mod):
        self._mod = copy.deepcopy(mod)
    mod = property(_get_mod, _set_mod, doc='Model associated with the current spectrum')

    def _set_mask(self, mask):
        if mask is None:
            self._mask = N.zeros(self.data[0].shape)
        else:
            self._mask = mask
    def _get_mask(self):
        return self._mask
    mask = property(_get_mask, _set_mask, doc='mask storing deleted points')
    
    def _get_data(self, axis, unmasked=False):
        ind = ['x','y'].index(axis)
        data = self.data+0
        loc = locals()
        loc.update(N.__dict__)
        loc['x'] = data[0]
        loc['y'] = data[1]

        for type,tr,comment,skip in self.trafo:
            if skip:
                continue
            data[['x','y'].index(type),:] = eval(tr,globals(),loc)

        if unmasked:
            if self._inverse:
                return data[ind,::-1]
            else:
                return data[ind]
        else:            
            cond = N.logical_and(N.isfinite(data[0]),N.isfinite(data[1]))
            data = N.compress(cond,data,1)
            mask = N.compress(cond,self.mask)
            cond = N.logical_and(N.isreal(data[0]),N.isreal(data[1]))
            data = N.compress(cond,data,1)
            mask = N.compress(cond,mask)

            data = N.compress(mask==0,data,1)

            if axis == 'x':
                if data[ind][0] > data[ind][-1]:
                    self._inverse = True
                    data = data[:,::-1]
                else:
                    self._inverse = False
            else:
                if self._inverse:
                    data = data[:,::-1]

            return data[ind]

    def _get_rawdata(self):
        return self._rawdata
    def _set_rawdata(self, data):
        data = data.take(data[0].argsort(),1)
        self._rawdata = data
        self.mask = None
        self.trafo = None
        self._inverse = False
    data = property(_get_rawdata, _set_rawdata, doc='raw data')
	    
    def _get_x(self):
        return self._get_data('x')
    
    def _get_x_unmasked(self):
        return self._get_data('x', True)

    def _get_y(self):
        return self._get_data('y')
        
    def _get_y_unmasked(self):
        return self._get_data('y', True)

    def _get_xy(self):
        return N.array([self.x,self.y])

    def _get_x_limited(self):
        if self.limits is not None:
            limits = N.searchsorted(self.x, self.limits)
            return self.x[limits[0]:limits[1]]
        else:
            return self.x

    def _get_y_limited(self):
        if self.limits is not None:
            limits = N.searchsorted(self.x, self.limits)
            return self.y[limits[0]:limits[1]]
        else:
            return self.y

    def _get_xy_limited(self):
        if self.limits is not None:
            limits = N.searchsorted(self.x, self.limits)
            return self.xy[:,limits[0]:limits[1]]
        else:
            return self.xy

    x = property(_get_x, doc='returns masked x-data including trafos')
    y = property(_get_y, doc='returns masked y-data including trafos')
    _x = property(_get_x_unmasked, doc='returns unmasked x-data including trafos')
    _y = property(_get_y_unmasked, doc='returns unmasked y-data including trafos')
    x_limited = property(_get_x_limited, doc='returns masked x-data including trafos within limits')
    y_limited = property(_get_y_limited, doc='returns masked y-data including trafos within limits')
    xy = property(_get_xy, doc='returns masked x-y-data, shape(2,x)')
    xy_limited = property(_get_xy_limited, doc='returns masked x-y-data within limits, shape(2,x)')
    
    def __eq__(self, other):
        if not isinstance(other, Spec):
            return False

        if N.alltrue(self.x == other.x) and N.alltrue(self.y == other.y):
            return True
        else:
            return False
        
    def __ne__(self, other):
        if not isinstance(other, Spec):
            return True

        if N.alltrue(self.x != other.x) or N.alltrue(self.y != other.y):
            return True
        else:
            return False
        
    def __len__(self):
        return len(self.x)
    
    def __div__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, self.y/other, '%s/%s'%(self.name,other))
        if not N.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], N.divide(self.y[a:b],interp), '%s/%s'%(self.name,other.name))
        else:
            ret =  Spec(self.x, N.divide(self.y,other.y), '%s/%s'%(self.name,other.name))
        return ret
    
    def __rdiv__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, other/self.y, '%s/%s'%(other,self.name))
        if not N.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], N.divide(interp,self.y[a:b]), '%s/%s'%(other.name,self.name))
        else:
            ret =  Spec(self.x, N.divide(other.y,self.y), '%s/%s'%(other.name,self.name))
        return ret
    
    def __mul__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, self.y*other, '%s*%s'%(self.name,other))
        if not N.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], N.multiply(self.y[a:b],interp), '%s*%s'%(self.name,other.name))
        else:
            ret =  Spec(self.x, N.multiply(self.y,other.y), '%s*%s'%(self.name,other.name))
        return ret

    __rmul__ = __mul__

    def __add__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, self.y+other, '%s+%s'%(self.name,other))
        else:
            if not N.alltrue(self.x == other.x):
                a, b = self._overlap(self.x, other.x)
                interpolate = interp1d(other.x,other.y)
                interp = interpolate(self.x[a:b])
                ret = Spec(self.x[a:b], self.y[a:b]+interp, '%s+%s'%(self.name,other.name))
            else:
                ret = Spec(self.x, self.y+other.y, '%s+%s'%(self.name,other.name))
            return ret

    __radd__ = __add__

    def __neg__(self):
        return Spec(self.x, -self.y, "neg")
    
    def _overlap(self, a, b):
        if N.alltrue(a == b):
            return a[0],a[-1]
        mima = [max(a[0],b[0]),min(a[-1],b[-1])]
        index = N.searchsorted(a, mima)
        return index[0],index[1]

    def __sub__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, self.y-other, '%s-%s'%(self.name,other))
        if not N.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], self.y[a:b]-interp, '%s-%s'%(self.name,other.name))
        else:
            ret = Spec(self.x, self.y-other.y, '%s-%s'%(self.name,other.name))
        return ret
        
    def __rsub__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, other-self.y, '%s-%s'%(other,self.name))
        if not N.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], interp-self.y[a:b], '%s-%s'%(other.name,self.name))
        else:
            ret = Spec(self.x, other.y-self.y, '%s-%s'%(other.name,self.name))
        return ret

    def __pow__(self, expon):
        if N.isscalar(expon):
            return Spec(self.x, N.power(self.y, expon), 'sub')
        else:
            raise TypeError, 'only scalar exponents allowed'
        
    def __repr__(self):
        return 'set name: %s'%(self.name)

def savitzky_golay(y, window_size, order, deriv=0):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techhniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    """
    try:
        window_size = N.abs(N.int(window_size))
        order = N.abs(N.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = N.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = N.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - N.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + N.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = N.concatenate((firstvals, y, lastvals))
    return N.convolve( m, y, mode='valid')

    
