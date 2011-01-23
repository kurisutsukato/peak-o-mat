#!/usr/bin/python

import xml.parsers.expat
import re
import gzip
import os
import copy
import shutil
import sys
from StringIO import StringIO
import traceback
import codecs

import textwrap as tw

from spec import Spec
from model import Model,Var
from weights import Weights,WeightsRegion
import misc

from numpy import array,transpose,minimum,maximum,sometrue,inf,nan

special_numbers=dict([('-1.#INF',-inf),('1.#INF',inf),
                      ('-1.#IND',nan),('-1.#IND00',nan),
                      ('1.#QNAN',-nan),('1.#QNAN0',-nan)])
def Float(x):
   if x in special_numbers:
       return special_numbers[x]
   return float(x) if ("." in x) or ("e" in x) else int(x)

chrmap = {'&':'&amp;',
          '<':'&lt;',
          '>':'&gt;',
          '\"': '&quot;',
          '\'': '&#39;'}

def slash(arg):
    for k,v in chrmap.iteritems():
        arg = arg.replace(k,v)
    return arg

def deslash(arg):
    for k,v in chrmap.iteritems():
        arg = arg.replace(v,k)
    return arg

class Queue(StringIO):
    def write(self, arg):
        StringIO.write(self,arg.encode('utf-8'))

class Message(list):
    type = 'error'
    def __init__(self, data, type='error'):
        self.type = type
        list.__init__(self, data)

class POMEx(Exception):
    pass

class LData(list):
    name = 'plot'
    def __init__(self, *args):
        list.__init__(self, *args)

    def add(self, item):
        if type(item) == list:
            self += item
        else:
            self.append(item)
        return len(self)-1

    def copy(self, item):
        if type(item) == list:
            out = []
            for i in item:
                out.append(copy.deepcopy(self[i]))
        else:
            out = copy.deepcopy(self[item])
        return out
            

    def delete(self, item):
        if type(item) == list:
            out = []
            for i in item:
                out.append(self[i])
            item.sort()
            item.reverse()
            for i in item:
                self.pop(i)
            return out
        else:
            return self.pop(item)

    def clear(self):
        while len(self) > 0:
            self.pop(0)

    def _shift(self, a, b):
        c = 0
        for i in a:
            if i < b:
                c += 1
        return c

    def move(self, a, b):
        if type(a) == list:
            mov = self.delete(a)
            self.insert(b-self._shift(a,b), mov)
        elif a < b:
            self.insert(b, self[a])
            self.pop(a)
        elif b < a:
            self.insert(b, self.pop(a))

    def insert(self, pos, item):
        if type(item) == list:
            if pos == len(self):
                self += item
            else:
                dest = self[pos]
                for i in item:
                    self.insert(self.index(dest), i)
        else:
            try:
                list.insert(self, pos, item)
            except IndexError:
                if pos == len(self):
                    self.append(item)
                else:
                    raise
        
class Plot(LData):
    type = 'plot'
    def __init__(self, *args):
        LData.__init__(self, *args)
        self.xrng,self.yrng = None,None

    def _get_range(self):
        return self.xrng, self.yrng
    
    def _set_range(self, rng):
        self.xrng, self.yrng = rng

    rng = property(_get_range, _set_range)

class Project(LData):
    name = 'nameless'
    path = None
    
    def __init__(self, *args):
        LData.__init__(self, *args)
        self.model = None
        self.fileloader = {'.lpj' : self.ReadLPJ, '.agr': self.ReadAGR}
        self.annotations = ''
        self.floating_set = None

    def all(self):
        all = []
        for p in self:
            for s in p:
                all.append(s)
        return iter(all)

    def Read(self, path, merge=False, datastore=None):
        ext = os.path.splitext(path)[1]
        
        msg = self.fileloader.get(ext.lower(), self.ReadLPJ)(path, merge=merge, datastore=datastore)
        if msg is None:
            self.path = os.path.abspath(path)
            self.name = os.path.basename(path)
        return msg

    def ReadAGR(self, path, merge=False, **kwargs):
        if not merge:
            self.data = {}
            # that means, delete all former data

        f = open(path, 'r')
                    
        data = False
        x = []
        y = []

        lastnum = 0
        graphs = []
        setnames = []
        oldplotnum = -1
        for i in f:
            mat = re.match(r'@\s+s(\d+) comment "(.+)"',i)
            if mat is not None:
                num = int(mat.groups()[0])
                comment = mat.groups()[1]
                setnames.append(comment.split('/')[-1])
                if lastnum > num:
                    graphs.append(setnames)
                    setnames = []
                lastnum = num
            graphs.append(setnames)
            
            mat = re.match('\@target G(\d+)\.S(\d+).*', i)
            if mat is not None:
                plotnum,setnum = map(int,mat.groups())
                if plotnum != oldplotnum:
                    oldplotnum = plotnum
                    lastplot = self.add(Plot())

            if i.find('&') == 0:
                try:
                    name = graphs[plotnum][setnum]
                except IndexError:
                    #print graphs, plotnum, setnum
                    name = 'NN'
                set = Spec(array(x),array(y),name)
                self[lastplot].add(set)
                x = []
                y = []
                data = False
            if data:
                xydata = map(Float,i.strip().split())
                x.append(xydata[0])
                y.append(xydata[1])
            if i.find('@type xy') == 0:
                data = True
        
    def ReadLPJ(self, path, merge=False, datastore=None):
        if not merge:
            self.clear()
        self.lastplot = None
        self.lastset = None
        self.warn = []
        self.gridname = None
        self.griddata = None
        self.rowlabels = {}
        self.collabels = {}
        self.the_grid = False
        
        def start_element(name, attrs):
            #print 'Start element:', name, attrs.keys()
            if name == 'plot':
                self.lastplot = self.add(Plot())
                #print 'added plot',self.activenum
                if 'xrng' in attrs.keys():
                    self[self.lastplot].xrng = array(map(Float,attrs['xrng'].split(',')))
                if 'yrng' in attrs.keys():
                    self[self.lastplot].yrng = array(map(Float,attrs['yrng'].split(',')))
                if 'name' in attrs.keys():
                    self[self.lastplot].name = deslash(attrs['name'])
            if name == 'set':
                if 'x' in attrs.keys():
                    reg = re.compile('[\s,]*')
                    x = array(map(Float,reg.split(attrs['x'].strip())))
                    y = array(map(Float,reg.split(attrs['y'].strip())))
                    self.lastset = self[self.lastplot].add(Spec(x,y,deslash(attrs['name'])))
                    if 'hide' in attrs.keys():
                        self[self.lastplot][self.lastset].hide = bool(attrs['hide'])
                    #print 'added set',self.active.activenum
            if name == 'trafo':
                cmt = 'no comment'
                skip = False
                if attrs.has_key('comment'):
                    cmt = deslash(attrs['comment'])
                if attrs.has_key('skip'):
                    skip = attrs['skip'] == 'True'
                trafo = (attrs['axis'],attrs['trafo'],cmt,skip)
                self[self.lastplot][self.lastset].trafo.append(trafo)
            if name == 'mask':
                mask = array([int(x) for x in attrs['data'].split()])
                self[self.lastplot][self.lastset].mask = mask
            if name in ['weights','error']:
                self.weights = Weights([])
            if name in ['weightsregion', 'errorregion']:
                self.weights.append(WeightsRegion(Float(attrs['lower']),Float(attrs['upper']),Float(attrs['rel']),Float(attrs['abs']),int(attrs['mode'])))
            if name == 'mod':
                if 'func' in attrs:
                    self.tokens = attrs['func']
                else:
                    self.tokens = attrs['tokens']
                self.components = []
            if name == 'token':
                self.vars = {}
            if name == 'limits':
                self.limits = map(Float,[attrs['lower'],attrs['upper']])
            if name == 'var':
                par = Var(Float(attrs['value']))
                if 'amin' in attrs:
                    par.amin = Float(attrs['amin'])
                    par.constr = 2
                if 'amax' in attrs:
                    par.amax = Float(attrs['amax'])
                if 'fix' in attrs:
                    par.fix = True
                    par.constr = 1
                if 'error' in attrs:
                    par.error = Float(attrs['error'])
                self.vars[attrs['name']] = par
            if name == 'griddata' and datastore is not None:
                def bla(arg):
                    a,b = arg.split(':::')
                    return int(a),b
                self.griddata = ''
                if attrs.has_key('rowlabels'):
                    try:
                        self.rowlabels = dict([bla(q) for q in attrs['rowlabels'].split(';')])
                    except:
                        self.rowlabels = dict([(n,v) for n,v in enumerate(attrs['rowlabels'].split(';'))])
                if attrs.has_key('collabels'):
                    try:
                        self.collabels = dict([bla(q) for q in attrs['collabels'].split(';')])
                    except:
                        self.collabels = dict([(n,v) for n,v in enumerate(attrs['collabels'].split(';'))])
                if attrs.has_key('name'):
                    self.gridname = attrs['name']
                self.the_grid = attrs.has_key('thegrid')                    
            if name == 'annotations':
                self.annotations = ''

        def end_element(name):
            #print 'End element:', name
            if name == 'token':
                self.components.append(self.vars)
            if name in ['weights','error']:
                self[self.lastplot][self.lastset].weights = self.weights
            if name == 'mod':
                if self.model is None:
                    try:
                        self.model = Model(self.tokens)
                        self.model.parse()
                    except KeyError,msg:
                        self.warn.append('unknown model: %s'%self.tokens)
                        return
                elif self.model.tokens != self.tokens:
                    try:
                        self.model = Model(self.tokens)
                        self.model.parse()
                    except KeyError, msg:
                        self.warn.append('unknown model: %s'%self.tokens)
                        return
                if hasattr(self, 'limits'):
                    self[self.lastplot][self.lastset].limits = self.limits
                    del self.limits
                try:
                    self.model.set_parameters(self.components)
                    self[self.lastplot][self.lastset].mod = self.model
                except IndexError:
                    pass
            if name == 'griddata' and datastore is not None:
                data = [[Float(x) for x in row.split(' ')] for row in self.griddata.strip().split('\n')]
                datastore((data, self.rowlabels, self.collabels), the_grid=self.the_grid, background=True, name=self.gridname)
                self.griddata = None
                self.gridname = None
                self.collabels = {}
                self.rowlabels = {}
                self.the_grid = False
            if name == 'annotations':
                self.annotations = deslash(self.annotations.rstrip())

        def char_data(data):
            if self.griddata is not None:
                self.griddata += data
            if self.annotations is not None:
                self.annotations += data
        p = xml.parsers.expat.ParserCreate('utf-8')

        p.StartElementHandler = start_element
        p.EndElementHandler = end_element
        p.CharacterDataHandler = char_data

        try:
            f = gzip.open(path, 'r')
            try:
                f.read(1)
            except IOError:
                f.close()
                f = open(path, 'r')
            else:
                f.rewind()
            data = f.read()
            f.close()
        except IOError, msg:
            self.warn.append(msg)
        else:
            try:
                p.Parse(data,1)
            except xml.parsers.expat.ExpatError, msg:
                self.warn.append(msg)
            
        warn = Message([])
        for e in self.warn:
            if e not in warn:
                warn.append(e)
                
        return [None, warn][int(len(warn)>0)]
    
    def Write(self, path=None, griddata=[]):
        if path is not None:
            if path.find('.lpj') == -1:
                path += '.lpj'
        if path is None:
            path = self.path
        else:
            self.path = os.path.abspath(path)
        def a2unicode(text):
            return tw.fill(' '.join(['%.15g'%x for x in text]))

        f = Queue()
        try:
            f.write('<document>\n')
            for p in range(len(self)):
                rng = ''
                if self[p].xrng is not None:
                    rng = 'xrng=\"%f,%f\" '%(self[p].xrng[0],self[p].xrng[1])
                if self[p].yrng is not None:
                    rng += 'yrng=\"%f,%f\"'%(self[p].yrng[0],self[p].yrng[1])
                f.write('<plot name=\"%s\" %s>\n'%(slash(self[p].name),rng))
                for s in range(len(self[p])):
                    f.write('<set name=\"%s\" '%(slash(self[p][s].name)))
                    if self[p][s].hide:
                        f.write(' hide=\"True\" ')
                    f.write('\nx=\"%s\" \ny=\"%s\">\n'%(a2unicode(self[p][s].data[0]), a2unicode(self[p][s].data[1])))
                    if self[p][s].weights is not None:
                        f.write('<weights>\n')
                        for w in self[p][s].weights:
                            f.write('<weightsregion lower=\"%f\" upper=\"%f\" rel=\"%s\" abs=\"%s\" mode=\"%s\" />\n'%(w.xmin,w.xmax,w.w_rel,w.w_abs,w.mode))
                        f.write('</weights>\n')
                    if len(self[p][s].trafo) > 0:
                        for axis,trafo,comment,skip in self[p][s].trafo:
                            f.write('<trafo axis=\"%s\" trafo=\"%s\" comment=\"%s\" skip=\"%s\" />\n'%(axis,trafo,slash(comment),skip))
                    if sometrue(self[p][s].mask != 0):
                        f.write('<mask data=\"%s\" />\n'%(a2unicode(self[p][s].mask)))
                    if self[p][s].limits is not None:
                        l,u = self[p][s].limits
                        f.write('<limits lower=\"%s\" upper=\"%s\" />\n'%(l,u))
                    if self[p][s].mod is not None:
                        f.write('<mod tokens=\"%s\" '%(self[p][s].mod.tokens))
                        if self[p][s].mod.tokens == 'CUSTOM':
                            f.write('func=\"%s\" '%self[p][s].mod.func)
                        f.write('>\n')
                        for feat in self[p][s].mod:
                            f.write('<token name=\"%s\">\n'%feat.name)
                            for par in feat.iterkeys():
                                tmp = '<var '
                                tmp += 'name=\"%s\" value=\"%s\" error=\"%s\" '%(par,feat[par].value,feat[par].error)
                                if feat[par].constr == 2:
                                    if feat[par].amin is not None:
                                        tmp += 'amin=\"%s\" '%(feat[par].amin)
                                    if feat[par].amax is not None:
                                        tmp += 'amax=\"%s\" '%(feat[par].amax)
                                elif feat[par].constr == 1:
                                    tmp += 'fix=\"True\"'
                                tmp += '>'
                                f.write(tmp)
                                f.write('</var>\n')
                            f.write('</token>\n')
                        f.write('</mod>\n')
                    f.write('</set>\n')
                f.write('</plot>\n')
            for d in griddata:
                attrs = ''
                if len(d.rowlabels) > 0:
                    attrs += ' rowlabels=\"%s\"'%(';'.join(['%d:::%s'%(p,q) for p,q in d.rowlabels]))
                if len(d.collabels) > 0:
                    attrs += ' collabels=\"%s\"'%(';'.join(['%d:::%s'%(p,q) for p,q in d.collabels]))
                attrs += ' name=\"%s\"'%d.name
                if d.the_grid:
                    attrs += ' thegrid=\"True\"' 
                f.write('<griddata%s>\n'%attrs)
                f.write('\n'.join([' '.join(['%.15g'%x for x in row]) for row in d.data]))
                f.write('\n</griddata>\n')
            if self.annotations is not None:
                f.write('<annotations>')
                f.write(slash(self.annotations))
                f.write('</annotations>\n')
            f.write('</document>\n')
        except:
            typ, val, trb = sys.exc_info()
            traceback.print_tb(trb)
            print typ,val
            return '%s: %s'%(typ, val)
        else:
            data = f.getvalue()
            data = data.decode("utf-8")
            if os.path.exists(path):
                try:
                    shutil.copy(path,path+'~')
                except:
                    print 'unable to create backup file'
            try:
                f = gzip.open(path.encode(sys.getfilesystemencoding()), 'w')
                encode = codecs.getencoder('utf-8')
                data, l = encode(data)
                f.write(data)
                f.close()
            except:
                typ, val, trb = sys.exc_info()
                traceback.print_tb(trb)
                print typ,val
                return '%s: %s'%(typ, val)
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        return None
        
if __name__ == '__main__':
    import unittest
    from operator import add
    
    class tests(unittest.TestCase):
        def __init__(self, *args, **kwargs):
            unittest.TestCase.__init__(self, *args, **kwargs)
            self.a = LData()
            for i in range(5):
                self.a.add(unicode(i))

        def test1(self):
            self.a.move(1,3)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '02134')
            
        def test2(self):
            self.a.move(3,1)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '03124')
            
        def test3(self):
            self.a.move(3,3)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '01234')
            
        def test4(self):
            self.a.move([0,2,4],2)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '10243')

        def test5(self):
            self.a.move([0,1,2,3,4],2)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '01234')

        def test6(self):
            out = self.a.delete([1,4])
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '023')
            
        def test7(self):
            out = self.a.delete([1,4])
            self.a.insert(-1, out)
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '02143')

        def test8(self):
            self.a.insert(2, ['8','9'])
            order = reduce(add, [unicode(x) for x in self.a])
            self.failUnless(order == '0189234')
            
    unittest.main()

