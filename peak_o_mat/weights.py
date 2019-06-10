import numpy as N
    
from .spec import Spec
import copy

class WeightsRegion(object):
    """\
    This object defines a weights region.

    self.range   : upper and lower bounds of the region as 2-tuple
    self.w_abs : absolute weight
    self.w_rel : relative weight
    self.mode : 0 : use relative weight
                1 : use absolute weight
                2 : use both relative and absolute weights

    To be used as table data in a PyGridTableBase it behaves like a list
    containing [err_rel, err_abs, mode]
    """
    
    def __init__(self, xmin=-N.inf, xmax=N.inf, w_rel=0.1, w_abs=0.5, mode=1):
        self.w_rel = w_rel
        self.w_abs = w_abs
        self.xmin = xmin
        self.xmax = xmax
        
        if mode not in [0,1,2]:
            raise TypeError('\'mode\' has to be one of 0,1,2')
        else:
            self.mode = mode

    def __getitem__(self, item):
        attrs = ['xmin','xmax','w_rel','w_abs','mode']
        return self.__getattribute__(attrs[item])

    def __setitem__(self, item, value):
        attrs = ['xmin','xmax','w_rel','w_abs','mode']
        self.__setattr__(attrs[item], value)

    def __str__(self):
        return '(%f:%f) rel:%f abs:%f mode:%d'%(self.xmin,self.xmax,self.w_rel, self.w_abs, self.mode)

    def getWeights(self, data):
        """\
        Returns the weights calculated from the weightss self.w_rel and
        self.w_abs as a (len(x)) array. The weight outside self.range is set
        to 1.

        data: set xy data
        """
        x,y = data
        w = N.ones(x.shape, float)
        
        if self.mode == 1:
            tmp = N.ones(x.shape, float)*abs(self.w_abs)
        if self.mode == 0:
            tmp = abs(y*self.w_rel)
        if self.mode == 2:
            tmp = N.zeros(x.shape, float)*abs(self.w_abs)+abs(y*self.w_rel)

        N.put(w, N.where(N.logical_and(self.xmin<x,x<self.xmax)), N.take(tmp, N.where(N.logical_and(self.xmin<x,x<self.xmax))))
        w = 1/w
        return w

    def getBounds(self, data):
        """\
        returns the upper and lower bounds of the y-data calculated from the
        weightss self.w_rel and self.w_abs as a (len(x)) array. The bounds
        outside self.range are set to 0.

        data: set xy data
        """
        x, y = data
            
        if self.mode == 1:
            tmp = abs(y*0+self.w_abs)
        if self.mode == 0:
            tmp = abs(y*self.w_rel)
        if self.mode == 2:
            tmp = abs(y*0+self.w_abs)+abs(y*self.w_rel)
        tmp *= N.logical_and(self.xmin<x,x<self.xmax)
        return tmp

class Weights(list):
    def isNone(self):
        return len(self) <= 1

    def clear(self):
        while len(self) > 1:
            self.pop(-1)

    def getWeights(self, data):
        """\
        returns the weights by evaluating all WeightsRegions stored in this list
        as a (len(x)) array.

        data: set xy data
        """

        x, y = data
        
        w = N.ones(x.shape, float)
        for r in self:
            w *= r.getWeights(data)
        return w

    def getBounds(self, data):
        """\
        returns the upper and lower weights bounds as a (2,len(x))
        array by evaluating all WeightsRegions stored in this list.

        data: set xy data
        """

        tmp = N.zeros(data.shape[1], float)
        for r in self:
            tmp += r.getBounds(data)
        bounds = N.array([data[1]-tmp,data[1]+tmp])
        return bounds

    def getBorders(self):
        """\
        return a list of x-values containing the borders of the WeightsRegions
        """
        borders = []
        for r in self:
            borders.append(r.xmin)
        if len(borders) > 0:
            return borders[1:]
        else:
            return []

    def newRegions(self, regions):
        """\
        Append, pop or update the borders of the WeightsRegions.

        regions: a list of 2-tuples defining adjacent weights regions
        """

        #TODO: einfach neu anlegen ist einfacher
        diff = len(regions)-len(self)
        if diff > 0:
            self += [WeightsRegion()]*diff
        elif diff < 0:
            for n in range(abs(diff)):
                self.pop(-1)

        for r,rng in zip(self,regions):
            r.xmin, r.xmax = rng
