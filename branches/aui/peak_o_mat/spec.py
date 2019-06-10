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

import numpy as np

from scipy.interpolate import interp1d

import copy
import re
import os, sys

from . import config
from .misc import PomError

from .symbols import pom_globals

class TrafoList(list):
    def __iter__(self):
        for x in range(len(self)):
            yield self[x]
            
    def __getitem__(self, item):
        data = list.__getitem__(self, item)
        if len(data) == 3:
            data = list(data)+[False] # das hier scheint fuer backward compatibility zu sein
        return data


class Spec(object):
    """
A class for storing spectral data. Spec arithmetics using +-/* act only on the y-values
like one expects when e.g. subtracting two spectra.  Interpolation is
done automatically if the x-values differ. 

"""
    truncated = False

    def __init__(self, *args):
        """
Spec(filename)
filename: load 2-column table data from file 'name'

Spec(x,y,name)
x : array/list holding the x-values
y : array/list holding the y-values
name : short description of the data
"""
        self.hide = False
        # TODO:
        # 1) accept lists as x- and y-input .... war glaube ich ein Irrtum
        # 2) crop nan values from input
        self._inverse = False
        self._unsorted = False
        self._mod = None
        self._weights = None
        self._limits = None
        self._trafo = TrafoList([])
        self._mask = np.zeros((0), dtype=np.int8)
        self._rawdata = np.empty((3,0),dtype=np.float64)

        self.parse_args(*args)

    def parse_args(self, *args):
        if len(args) == 3:
            x,y,name = args
            data = np.asarray([x,y])
            self.data = data
        elif len(args) == 4:
            x,y,y2,name = args
            data = np.asarray([x,y,y2])
            self.data = data
        elif len(args) == 1:
            if isinstance(args[0], Spec):
                self.data = args[0].xy.copy()
                self.mod = copy.deepcopy(args[0].mod)
                name = 'copy_of_'+args[0].name
            elif type(args[0]) in [str,str]:
                name = os.path.basename(args[0])
                base, suf = os.path.splitext(args[0])
                if suf == '.ms0':
                    self.data = self.read_ms0(args[0])
                else:
                    data = self.read(args[0])
                    self.data = data
            else:
                raise TypeError('wrong arguments'+self.__init__.__doc__)
        else:
            raise TypeError('wrong arguments'+self.__init__.__doc__)

#TODO: obsolete: truncating of spectra
    #     if config.truncate:
    #         self.truncate(config.truncate_max_pts, config.truncate_interpolate)
        self.name = name
        self.mask = np.zeros(self.data.shape[1])
    #
    # def truncate(self, pts, interpolate=True):
    #     if len(self.data[0]) > pts:
    #         self.truncated = True
    #         if not hasattr(config, 'interpolate'):
    #             config.interpolate = False
    #
    #         if not config.interpolate:
    #             l = len(self.data[0])
    #             if l > pts:
    #                 inc = float(l)/float(pts)
    #                 at = np.arange(0.0, l, inc, float).astype(int)
    #                 self.data = self.data.take(at, 1)
    #         else:
    #             a,b = min(self.data[0])+1e-2,max(self.data[0])-1e-2
    #             x = np.arange(a,b,(b-a)/pts)
    #             interpolate = interp1d(self.data[0], self.data[1])
    #             y = interpolate(x)
    #             self.data = np.array([x,y])

    def __copy__(self):
        return Spec(self.x.copy(), self.y.copy(), 'copy_%s'%self.name)

    def write(self, path, overwrite=False):
        """
writes the current spectrum data in two columns
path : obviously, the path
"""

        if os.path.exists(path) and not overwrite:
            # print 'file \'%s\' exists and overwrite mode is False'%path
            return False

        try:
            f = open(path, 'w')
        except IOError:
            print('IOError: cannot write to %s' % (path))
            return False
        
        data = np.transpose(np.array([self.x,self.y]))
        if config.getboolean('general','floating_point_is_comma'):
            f.write('\n'.join(['{:.15g}\t{:.15g}'.format(x,y).replace('.',',') for x,y in data]))
        else:
            f.write('\n'.join(['{:.15g}\t{:.15g}'.format(x,y) for x,y in data]))
        f.close()
        return True
        
    def read_ms0(self, path):
        data = []
        try:
            f = open(path, "r")
        except IOError:
            print(path, 'not found')
            return 0,0
        for line in f:
            if line.find(r'"') != 0:
                data.append(float(line))
        l = len(data)/2
        data = np.transpose(np.resize(np.array(data), (l, 2)))

        return data
            
    def read(self, path):
        data = []
        self.path = path

        try:
            f = open(path.encode(sys.getfilesystemencoding()))
        except IOError:
            raise PomError('unable to open \'%s\''%path)

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
            #config.floating_point_is_comma = True

        if len(data) == 0:
            raise PomError('unable to parse %s'%path)

        return np.transpose(data)[:2] # ignore additional columns

    def __boundingBox(self):
        """\
returns boundingBox of the data as
"""
        minXY = np.minimum.reduce(np.transpose([self.x,self.y]))
        maxXY = np.maximum.reduce(np.transpose([self.x,self.y]))
        return minXY,maxXY

    def crop(self, xrng, cp=False):
        a,b = np.searchsorted(self.data[0], xrng)
        if cp:
            x,y = self.data[:,a:b+1]
            return Spec(x,y,'cropped_%s'%self.name)
        else:
            self.data = self.data[:,a:b+1]

    def make_mask_permanent(self):
        tmp = self.trafo[:]
        self.data = self.data[:,self.mask == 0]
        self.trafo = tmp # assignment to self.data deletes the trafo list... I am not sure if this is really necessary

    def make_trafo_permanent(self):
        tmp = self.mask
        self.data = [self._x, self._y]
        self.mask = tmp
        
    def mrproper(self):
        data = self.data
        cond = np.logical_and(np.isfinite(data[0]),np.isfinite(data[1]))
        data = np.compress(cond,data,1)
        cond = np.logical_and(np.isreal(data[0]),np.isreal(data[1]))
        data = np.compress(cond,data,1)
        cond = 1-np.logical_or(np.isnan(data[0]),np.isnan(data[1]))
        data = np.compress(cond,data,1)
        self.data = data

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
            self.data = np.array([x,dy])
            self.mask = None
            self.trafo = None
            return None
        
    def average(self, avg, cp=False):
        """
moving average with 'avg' points
avg : number of points to average
"""
        l = len(self.y)
        newy = np.zeros((0,l-avg))
        newx = []
        for i in range(avg):
            newy = np.concatenate((newy,np.reshape(self.y[i:l-avg+i], (1,l-avg))))
        newy = sum(newy)/avg
        s = avg/2
        e = avg-s
        newx = self.x[s:-e]
        if cp:
            return Spec(newx,newy, '%dpt_avg_%s'%(avg, self.name))
        else:
            self.data = np.array([newx, newy])
            return None

    def weighted_average(self, step_size=0.05, width=1, cp=False):
        bin_centers  = np.arange(np.min(self.x),np.max(self.x)-0.5*step_size,step_size)+0.5*step_size
        bin_avg = np.zeros(len(bin_centers))

        #We're going to weight with a Gaussian function
        def gaussian(x,amp=1,mean=0,sigma=1):
            return amp*np.exp(-(x-mean)**2/(2*sigma**2))

        for index in range(0,len(bin_centers)):
            bin_center = bin_centers[index]
            weights = gaussian(self.x,mean=bin_center,sigma=width)
            bin_avg[index] = np.average(self.y,weights=weights)

        if cp:
            return Spec(bin_centers,bin_avg, 'wavg_%s'%(self.name))
        else:
            self.data = np.array([bin_centers,bin_avg])
            return None

    def sg_filter(self, window, order, cp=False):
        newy = savitzky_golay(self.y, window, order)
        if cp:
            return Spec(self.x, newy, 'SGfiltered_%s'%self.name)
        else:
            self.data = np.array([self.x, newy])
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
            self.data = np.array([x,interp],dtype=np.float64)
            return None

    def norm(self, cp=False):
        """
normalize the y-values to 1
"""
        y = np.array(self.y/max(self.y))
        if cp:
            return Spec(self.x,y,'norm_'+self.name)
        else:
            self.data = np.array([self.x,y])
            return None

    def delete(self, bbox):
        """
Deletes data points within bounding box.
bbox : boundingbox of points to be removed
"""
        sortindex = np.argsort(self._x)
        xsorted = np.take(self._x, sortindex)
        ysorted = np.take(self._y, sortindex)
        bbx,bby = np.transpose(bbox)
        bbx = np.searchsorted(xsorted, bbx)
        mask = np.zeros(xsorted.shape)
        for x,y in enumerate(ysorted[bbx[0]:bbx[1]]):
            if bby[0] < y < bby[1]:
                mask[x+bbx[0]] = 1
        mask = np.take(mask, np.argsort(sortindex))

        if self._inverse:
            mask = mask[::-1]
        self.mask = np.logical_or(self.mask, mask).astype(int)
            
    def loadpeaks(self, mod=None, addbg=False):
        if mod is None:
            mod = self._mod
        peaks = mod.loadpeaks(self.x, addbg=addbg)
        return peaks

    def _getxrange(self):
        return np.minimum.reduce(self.x),np.maximum.reduce(self.x)
    xrng = property(_getxrange, doc='data\'s xrange as 2-tuple')

    def _getyrange(self):
        return np.minimum.reduce(self.y),np.maximum.reduce(self.y)
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
        if type(limits) not in [tuple,type(None),np.ndarray,list]:
            raise TypeError('limits: tuple or None required')
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
    model = property(_get_mod, _set_mod, doc='Model associated with the current spectrum')
    mod = model

    def _set_mask(self, mask):
        if mask is None:
            self._mask = np.zeros(self.data[0].shape)
        else:
            self._mask = mask
    def _get_mask(self):
        return self._mask
    mask = property(_get_mask, _set_mask, doc='mask storing deleted points')
    
    def _get_data(self, axis, unmasked=False, limited=False):
        ind = ['x','y','y2'].index(axis)
        data = np.copy(self.data)

        try:
            locs = {'x': data[0], 'y': data[1], 'y2': data[2]}
        except IndexError:
            locs = {'x': data[0], 'y': data[1]}

        for type,tr,comment,skip in self.trafo:
            if skip:
                continue
            data[['x','y','y2'].index(type),:] = eval(tr, pom_globals, locs)

        if unmasked:
            if self._inverse:
                return data[ind,::-1]
            else:
                return data[ind]
        else:
            cond = np.logical_and(np.isfinite(data[0]),np.isfinite(data[1]))
            data = np.compress(cond,data,1)
            mask = np.compress(cond,self.mask)

            cond = np.logical_and(np.isreal(data[0]),np.isreal(data[1]))
            data = np.compress(cond,data,1)
            mask = np.compress(cond,mask)

            data = np.compress(mask==0,data,1)

            if axis == 'x':
                if (np.take(data[ind],np.argsort(data[ind])) != data[ind]).any():
                    self._unsorted = True
                    self._inverse = False
                else:
                    self._unsorted = False
                    if data[ind,0] > data[ind,-1]:
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
        data = np.asarray(data)
        #data = data.take(data[0].argsort(),1)
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

    def _get_y2(self):
        return self._get_data('y2')

    def _get_y2_unmasked(self):
        return self._get_data('y2', True)

    def _get_xy(self):
        return np.array([self.x,self.y])

    def _get_xyy2(self):
        return np.array([self.x,self.y,self.y2])

    def _get_x_limited(self):
        if self.limits is not None:
            si = np.argsort(self.x)
            xs = np.take(self.x, si)
            low,up = np.searchsorted(xs, self.limits)
            idx = np.sort(si[low:up])
            return np.take(self.x, idx)
        else:
            return self.x

    def _get_y_limited(self):
        if self.limits is not None:
            si = np.argsort(self.x)
            xs = np.take(self.x, si)
            low,up = np.searchsorted(xs, self.limits)
            idx = np.sort(si[low:up])
            return np.take(self.y, idx)
        else:
            return self.y

    def _get_xy_limited(self):
        if self.limits is not None:
            si = np.argsort(self.x)
            xs = np.take(self.x, si)
            low,up = np.searchsorted(xs, self.limits)
            idx = np.sort(si[low:up])
            res = np.take(self.xy, idx, axis = 1)
            return res
        else:
            return self.xy

    def _get_xyy2_limited(self):
        if self.limits is not None:
            si = np.argsort(self.x)
            xs = np.take(self.x, si)
            low,up = np.searchsorted(xs, self.limits)
            idx = np.sort(si[low:up])
            res = np.take(self.xyy2, idx, axis = 1)
            return res
        else:
            return self.xyy2

    x = property(_get_x, doc='returns masked x-data including trafos')
    y = property(_get_y, doc='returns masked y-data including trafos')
    y2 = property(_get_y2, doc='returns masked y2-data including trafos')
    _x = property(_get_x_unmasked, doc='returns unmasked x-data including trafos')
    _y = property(_get_y_unmasked, doc='returns unmasked y-data including trafos')
    x_limited = property(_get_x_limited, doc='returns masked x-data including trafos within limits')
    y_limited = property(_get_y_limited, doc='returns masked y-data including trafos within limits')
    xy = property(_get_xy, doc='returns masked x-y-data, shape(2,x)')
    xyy2 = property(_get_xyy2, doc='returns masked x-y-y2-data, shape(3,x)')
    xy_limited = property(_get_xy_limited, doc='returns masked x-y-data within limits, shape(2,x)')
    xyy2_limited = property(_get_xyy2_limited, doc='returns masked x-y-y2-data within limits, shape(2,x)')

    def __eq__(self, other):
        if not isinstance(other, Spec):
            return False

        if np.alltrue(self.x == other.x) and np.alltrue(self.y == other.y):
            return True
        else:
            return False
        
    def __ne__(self, other):
        if not isinstance(other, Spec):
            return True

        if np.alltrue(self.x != other.x) or np.alltrue(self.y != other.y):
            return True
        else:
            return False
        
    def __len__(self):
        return len(self.x)

    def __and__(self, other):
        if not isinstance(other, Spec):
            raise NotImplementedError('& operator used between non-Spec objects')
        res = self.join(other)
        return res
    
    def __div__(self, other):
        if not isinstance(other, Spec):
            return Spec(self.x, self.y/other, '%s/%s'%(self.name,other))
        if not np.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], np.divide(self.y[a:b],interp), '%s/%s'%(self.name,other.name))
        else:
            ret =  Spec(self.x, np.divide(self.y,other.y), '%s/%s'%(self.name,other.name))
        return ret

    __truediv__ = __div__

    def __mul__(self, other):
        if not isinstance(other, Spec):
            if np.isscalar(other):
                name = 'scalar'
            else:
                name = 'array'
            return Spec(self.x, self.y*other, '%s*%s'%(self.name,name))
        if not np.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], np.multiply(self.y[a:b],interp), '%s*%s'%(self.name,other.name))
        else:
            ret =  Spec(self.x, np.multiply(self.y,other.y), '%s*%s'%(self.name,other.name))
        return ret

    def __add__(self, other):
        if not isinstance(other, Spec):
            if np.isscalar(other):
                name = 'scalar'
            else:
                name = 'array'
            return Spec(self.x, self.y+other, '%s+%s'%(self.name,name))
        else:
            if not np.alltrue(self.x == other.x):
                a, b = self._overlap(self.x, other.x)
                interpolate = interp1d(other.x,other.y)
                interp = interpolate(self.x[a:b])
                ret = Spec(self.x[a:b], self.y[a:b]+interp, '%s+%s'%(self.name,other.name))
            else:
                ret = Spec(self.x, self.y+other.y, '%s+%s'%(self.name,other.name))
            return ret

    def __neg__(self):
        return Spec(self.x, -self.y, '-%s'%self.name)

    def join(self, other):
        if self.x[0] < other.x[0] and self.x[-1] < other.x[0]:
            res = Spec(np.concatenate((self.x,other.x)),np.concatenate((self.y,other.y)),self.name+'&'+other.name)
            return res
        elif self.x[0] > other.x[0] and self.x[0] > other.x[-1]:
            res = Spec(np.concatenate((other.x,self.x)),np.concatenate((other.y,self.y)),self.name+'&'+other.name)
            return res
        else:
            raise Exception('Sets cannot be joined because of overlapping x-values.')

    def _overlap(self, a, b):
        if np.alltrue(a == b):
            return a[0],a[-1]
        min_x, max_x = [max(a.min(),b.min()),min(a.max(),b.max())]

        sortindex = np.argsort(a)
        asorted = np.take(a, sortindex)
        lower, upper = np.searchsorted(asorted, [min_x,max_x])
        if max_x in self.x:
            upper += 1

        return lower,upper

    def __isub__(self, other):
        if not isinstance(other, Spec):
            if np.isscalar(other):
                name = 'scalar'
            else:
                name = 'array'
            self._rawdata[1] -= other
            return self
        if not np.alltrue(self.x == other.x):
            raise NotImplementedError('infix operation not possible between datasets with non equal x-axis')
        else:
            self._rawdata[1] -= other.y
            return self

    def __sub__(self, other):
        if not isinstance(other, Spec):
            if np.isscalar(other):
                name = 'scalar'
            else:
                name = 'array'
            return Spec(self.x, self.y-other, '%s-%s'%(self.name,name))
        if not np.alltrue(self.x == other.x):
            a, b = self._overlap(self.x, other.x)
            interpolate = interp1d(other.x,other.y)
            interp = interpolate(self.x[a:b])
            ret = Spec(self.x[a:b], self.y[a:b]-interp, '%s-%s'%(self.name,other.name))
        else:
            ret = Spec(self.x, self.y-other.y, '%s-%s'%(self.name,other.name))
        return ret
        
    def __pow__(self, expon):
        if np.isscalar(expon):
            return Spec(self.x, np.power(self.y, expon), 'power(%s,%s)'%(self.name,expon))
        else:
            raise TypeError('only scalar exponents allowed')
        
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
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError as msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = list(range(order+1))
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv]
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m, y, mode='valid')

import unittest

class SpecTests(unittest.TestCase):
    def setUp(self):
        x = np.array([2,5,8,10],dtype=float)
        y = np.sin(x)
        self.s = Spec(x,y,'sin')

    def test_limit_reverse(self):
        self.s.trafo.append(('x','1/x','inverse'))
        self.s.limits = (3.0,8.0)
        self.assertEqual(self.s.x.tolist(),[0.5,0.2,0.125,0.1])
        self.assertEqual(self.s.x_limited.tolist(),[0.2,0.125,0.1])

    def test_mask_reverse(self):
        self.s.mask = [1,1,0,0]
        self.assertEqual(self.s.x.tolist(),[8,10])
        self.s.trafo.append(('x','1/x','inverse'))
        self.assertEqual(self.s.x.tolist(),[0.125,0.1])
        self.assertEqual(self.s._get_x_unmasked().tolist(),[0.5,0.2,0.125,0.1])

    def test_y2(self):
        x = np.array([2,5,8,10],dtype=float)
        y = np.sin(x)
        y2 = np.cos(x)
        s = Spec(x,y,y2,'unittest')

if __name__ == '__main__':
    unittest.main()