#!/usr/bin/python

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
import gzip
import os
import copy
import shutil
import sys
from io import BytesIO
import traceback
import codecs

import uuid as UUID
from functools import reduce

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import textwrap as tw

from numpy import array, sometrue, inf, nan, ndarray, take, searchsorted

from .spec import Spec
from .model import Model,Var
from .weights import Weights,WeightsRegion

from .mplplot.model import MultiPlotModel, PlotData

special_numbers=dict([('-1.#INF',-inf),('1.#INF',inf),
                      ('-1.#IND',nan),('-1.#IND00',nan),
                      ('1.#QNAN',-nan),('1.#QNAN0',-nan)])
def Float(x):
   if x in list(special_numbers.keys()):
       return special_numbers[x]
   try:
       return float(x)
   except ValueError:
       return 0.0

chrmap = {'&':'&amp;',
          '<':'&lt;',
          '>':'&gt;',
          '\"': '&quot;',
          '\'': '&#39;'}

def ptake(arr, ind):
    return [arr[q] for q in ind]

def slash(arg): # elementtree takes care of that
    return arg

def deslash(arg): # assure backwards compatibility
    for k,v in chrmap.items():
        arg = arg.replace(v,k)
    return arg

class Queue(BytesIO):
    def write(self, arg):
        BytesIO.write(self, arg)

class Message(list):
    def append(self, data, type='warn'):
        print('msg appended: {}'.format(data))
        lead = {'warn':'Warning','error':'Error'}
        super(Message, self).append('{}: {}'.format(lead[type],data))

from .misc import PomError

def dict2xmlattrs(data):
    xml = []
    for k,v in data.items():
        xml.append('{}="{}"'.format(k,v))
    return ' '.join(xml)

def dict2xmlelements(data):
    xml = []
    for k,v in data.items():
        if '\n' in v:
            xml.append('<{0}>\n{1}\n</{0}>'.format(k,v.strip()))
        else:
            xml.append('<{0}>{1}</{0}>'.format(k,v))
    return '\n'.join(xml)

class LData(list):
    def __init__(self, *args):
        list.__init__(self, *args)
        self.name = ''

    def add(self, item):
        if type(item) == list:
            self.extend(item)
        else:
            self.append(item)
        return len(self)-1

    def copy(self, item):
        if type(item) == list:
            out = []
            for i in item:
                out.append(copy.deepcopy(self[i]))
                if type(out[-1]) == PlotItem:
                    out[-1].uuid = UUID.uuid4().hex
        else:
            out = copy.deepcopy(self[item])
            if type(out) == PlotItem:
                out.uuid = UUID.uuid4().hex
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
        del self[:]

    def _shift(self, a, b):
        c = 0
        for i in a:
            if i < b:
                c += 1
        return c

    def move(self, frm, to):
        if type(frm) == list:
            mv = set(frm)
            all = set(range(len(self)))
            remain = sorted(list(all-mv))
            ins = searchsorted(remain, to)
            mv = sorted(list(mv))
            self[:] = ptake(self, remain[:ins]+mv+remain[ins:])
        elif frm < to:
            self[:] = ptake(self,list(range(frm))+list(range(frm+1,to))+[frm]+list(range(to,len(self))))
        elif to < frm:
            self[:] = ptake(self,list(range(to))+[frm]+list(range(to,frm))+list(range(frm+1,len(self))))

    def insert(self, pos, item):
        if type(item) == list:
            if pos == len(self):
                self.extend(item)
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

class Dataset(object):
    type = 'dataset'
    def __init__(self):
        self.uuid = UUID.uuid4().hex

class PlotItem(Spec, Dataset):
    def __init__(self, *args):
        Dataset.__init__(self)
        Spec.__init__(self, *args)

class Plot(LData):
    type = 'plot'
    def __init__(self, uuid=None, name=None):
        LData.__init__(self)
        self.xrng,self.yrng = None,None
        self._references = []
        self.uuid = uuid or UUID.uuid4().hex
        if name is not None:
            self.name = name

    def __repr__(self):
        return 'plot \'{}\' with {} set(s)'.format(self.name,len(self))

    def __getstate__(self):
        dict = self.__dict__.copy()
        dict['uuid'] = UUID.uuid4().hex
        dict['_references'] = []
        return dict

    def __getitem__(self, item):
        if type(item) in [int,slice]:
            return super(Plot, self).__getitem__(item)
        for p in self:
            if p.uuid == item:
                return p
        raise KeyError('no dataset with uuid "{}"'.format(item))

    def _get_range(self):
        if type(self.xrng) == ndarray:
            self.xrng = self.xrng.tolist()
        if type(self.yrng) == ndarray:
            self.yrng = self.yrng.tolist()
        return self.xrng, self.yrng
    
    def _set_range(self, rng):
        self.xrng, self.yrng = rng

    rng = property(_get_range, _set_range)

    def add_ref(self, ref):
        self._references.append(ref)
    def del_ref(self, ref):
        self._references.remove(ref)

    @property
    def has_ref(self):
        return len(self._references) != 0

    @property
    def hash(self):
        m = str(len(self))
        for s in self:
            m = m+s.name
        return m

    def import_data(self, data, basename, collabels=None, order='xyyy'):
        """import multicolumn data

        data: numeric 2D data
        collabels: list of str or None
        order: one of 'xyyy', 'xyxy' or a list of tuples indicating x and y column

        """

        if order == 'xyyy':
            for n in range(1,data.shape[1]):
                if data.shape[1] == 2:
                    lab = basename
                elif collabels is not None:
                    lab = collabels[n]
                else:
                    lab = '{} - col {}'.format(basename, n)
                s = PlotItem(data[:,0], data[:,n], lab)
                self.add(s)
        elif order == 'xyxy':
            for n in range(0,data.shape[1],2):
                if collabels is not None:
                    try:
                        lab = collabels[n+1]
                    except IndexError:
                        lab = basename
                elif data.shape[1] == 2:
                    lab = basename
                else:
                    lab = '{} - col {}'.format(basename, n+1)
                try:
                    s = PlotItem(data[:,n], data[:,n+1], lab)
                    self.add(s)
                except IndexError: # impair number of columns
                    print('impair number of columns - skipped last column')
                    break
        elif type(order) == list:
            for x,y in order:
                if len(order) == 1:
                    lab = basename
                elif collabels is not None:
                    try:
                        lab = collabels[y]
                    except IndexError:
                        lab = basename
                else:
                    lab = '{} - col {}'.format(basename, y)
                try:
                    s = PlotItem(data[:,x], data[:,y], lab)
                except IndexError:
                    raise PomError('Column indices {},{} exceed available number of columns'.format(x,y))
                    continue
                else:
                    self.add(s)

def xmlset2set(element):
    name, attrs = element.tag, element.attrib
    reg = re.compile(r'[\s,]+')
    x = array([Float(q) for q in reg.split(attrs['x'].strip())])
    y = array([Float(q) for q in reg.split(attrs['y'].strip())])
    if 'y2' in attrs.keys():
        y2 = array([Float(q) for q in reg.split(attrs['y2'].strip())])
        s = PlotItem(x,y,y2,deslash(attrs['name']))
    else:
        s = PlotItem(x,y,deslash(attrs['name']))
    s.hide = attrs.get('hide', False) ==  'True'

    for limits_elem in element.findall('limits'):
        name, attrs = limits_elem.tag, limits_elem.attrib
        limits = list(map(Float,[attrs['lower'],attrs['upper']]))
        s.limits = limits
    return s

def xmlweights2weights(element):
    weights = Weights([])
    for region in element.findall('weightsregion'):
        name, attrs = region.tag, region.attrib
        weights.append(WeightsRegion(Float(attrs['lower']),Float(attrs['upper']),Float(attrs['rel']),Float(attrs['abs']),int(attrs['mode'])))
    return weights

def xmlmod2mod(element, lastmod=None):
    name, attrs = element.tag, element.attrib
    tokens = attrs.get('func', False) or attrs.get('tokens')
    components = []

    for token_elem in element.findall('token'):
        vars = {}
        for var_elem in token_elem.findall('var'):
            name, attrs = var_elem.tag, var_elem.attrib
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
            vars[attrs['name']] = par
        components.append(vars)

    #TODO: ist lastmod wirklich nötig? Dauert das so lange?
    warn = []
    if lastmod is None or lastmod.tokens != tokens:
        try:
            model = Model(tokens)
            model.parse()
            model.evaluate([-1,1])
        except (KeyError, NameError) as err:
            warn.append('Unknown symbol encountered: {}'.format(err))
            model = None
            return model, warn
    else:
        model = lastmod.copy()

    try:
        model.set_parameters(components)
    except KeyError as err:
        warn.append('Unknown parameter encountered: {}'.format(err))
        return None, warn

    return model, warn

class Project(LData):
    def __init__(self, *args):
        LData.__init__(self, *args)

        self.name = 'nameless'
        self.path = None

        self.model = None
        self.annotations = ''
        self.code = ''
        self.figure_list = []
        self.floating_set = None

        self._figure_data = ''
        self._figure_uuid = None
        self._figure_settings = None
        self._settings_element = None

    def find_by_uuid(self, uuid):
        for p in self:
            for s in p:
                if s.uuid == uuid:
                    return s
        return None

    def append_plot(self, name=None):
        return self.add(Plot(name=name))

    def index(self, value):
        for n,p in enumerate(self):
            if p.uuid == value:
                return n
        return super(Project, self).index(value)

    def __getitem__(self, item):
        if type(item) in [int,slice]:
            return super(Project, self).__getitem__(item)
        for p in self:
            if p.uuid == item:
                return p
        raise KeyError('no plot with uuid "{}"'.format(item))

    def __contains__(self, item):
        for p in self:
            if p.uuid == item:
                return True
        return False

    def pop(self, index=None):
        if index is None:
            index = len(self)-1
        if not self[index].has_ref:
            return super(Project, self).pop(index)
        else:
            return None

    def all(self):
        all = []
        for p in self:
            for s in p:
                all.append(s)
        return iter(all)

    def clear(self):
        del self.figure_list[:]
        super(Project, self).clear()
        self.name = 'nameless'
        self.annotations = ''
        self.code = []
        self.path = None

    def load(self, path, datastore=None):
        self.lastplot = None
        self.lastset = None
        self.lastmod = None
        self.warn = Message()
        self.gridname = None
        self.griddata = None
        self.rowlabels = {}
        self.collabels = {}
        self.the_grid = False

        try:
            f = gzip.open(path, 'rb')
            try:
                f.read(1)
            except IOError:
                f.close()
                f = open(path, 'rb')
            else:
                f.rewind()
            tree = ET.ElementTree(file=f)
            f.close()
        except IOError as msg:
            self.warn.append(msg, 'error')
        else:

            if datastore is not None:
                datastore.clear()

            self.clear()

            for elem in tree.iter(tag='plot'):
                name, attrs, data = elem.tag, elem.attrib, elem.text
                if name == 'plot':
                    self.lastplot = self.add(Plot(uuid=attrs.get('uuid',None)))
                    #print 'added plot',self.activenum
                    if 'xrng' in list(attrs.keys()):
                        self[self.lastplot].xrng = array(list(map(Float,attrs['xrng'].split(','))))
                    if 'yrng' in list(attrs.keys()):
                        self[self.lastplot].yrng = array(list(map(Float,attrs['yrng'].split(','))))
                    if 'name' in list(attrs.keys()):
                        self[self.lastplot].name = deslash(attrs['name'])
                    for set_elem in elem.findall('set'):
                        self.lastset = self[self.lastplot].add(xmlset2set(set_elem))

                        for trafo_elem in set_elem.findall('trafo'):
                            name, attrs = trafo_elem.tag, trafo_elem.attrib
                            cmt = deslash(attrs.get('comment',''))
                            skip = attrs.get('skip',False) is True
                            trafo = (attrs['axis'],attrs['trafo'],cmt,skip)
                            self[self.lastplot][self.lastset].trafo.append(trafo)

                        for mask_elem in set_elem.findall('mask'):
                            name, attrs = mask_elem.tag, mask_elem.attrib
                            mask = array([int(x) for x in attrs['data'].split()])
                            self[self.lastplot][self.lastset].mask = mask

                        for weights_elem in set_elem.findall('weights'):
                            self[self.lastplot][self.lastset].weights = xmlweights2weights(weights_elem)

                        if 'limits' in list(set_elem.attrib.keys()):
                            self[self.lastplot][self.lastset].limits = [float(q) for q in set_elem.attrib['limits'].split()]

                        for mod_elem in set_elem.findall('mod'):
                            mod, warn = xmlmod2mod(mod_elem, self.lastmod)
                            if mod is None:
                                for w in warn:
                                    self.warn.append(w)
                            else:
                                self.lastmod = mod
                                self[self.lastplot][self.lastset].mod = mod

            for mpm_elem in tree.findall('mpmodel'):
                sett_elem = mpm_elem.find('settings')
                settings = {}
                if sett_elem is not None:
                    for elem in sett_elem.iter():
                        settings[elem.tag] = elem.text
                try:
                    self.figure_list.append(MultiPlotModel.from_xml(self, settings))
                except KeyError as msg:
                    self.warn.append(msg)
                for fig_elem in mpm_elem.findall('figure'):
                    plotref = fig_elem.attrib.get('plotref')
                    gridpos = tuple([int(fig_elem.attrib.get(q)) for q in ['row','col']])
                    sett_elem = fig_elem.find('settings')
                    settings = {}
                    for elem in sett_elem.iter():
                        settings[elem.tag] = elem.text
                    data = fig_elem.find('linedata').text
                    try:
                        self.figure_list[-1].add(PlotData.from_xml(self, plotref, settings, data), gridpos)
                    except KeyError as msg:
                        self.warn.append(msg)

            for elem in tree.findall('griddata'):
                name, attrs, data = elem.tag, elem.attrib, elem.text
                def bla(arg):
                    a,b = arg.split(':::')
                    return int(a),b
                if 'rowlabels' in attrs:
                    try:
                        self.rowlabels = dict([bla(q) for q in attrs['rowlabels'].split(';')])
                    except:
                        self.rowlabels = dict([(n,v) for n,v in enumerate(attrs['rowlabels'].split(';'))])
                else:
                    self.rowlabels = {}
                if 'collabels' in attrs:
                    try:
                        self.collabels = dict([bla(q) for q in attrs['collabels'].split(';')])
                    except:
                        self.collabels = dict([(n,v) for n,v in enumerate(attrs['collabels'].split(';'))])
                else:
                    self.collabels = {}
                if 'name' in attrs:
                    self.gridname = attrs['name']
                self.the_grid = 'thegrid' in attrs
                data = [[Float(x) for x in row.split(' ')] for row in data.strip().split('\n')]
                if datastore is not None:
                    datastore.new((data, self.rowlabels, self.collabels), the_grid=self.the_grid, name=self.gridname)

            for elem in tree.findall('annotations'):
                name, attrs, data = elem.tag, elem.attrib, elem.text
                self.annotations = deslash(data) if data is not None else ''

            self.code = []
            for elem in tree.findall('code'):
                name, attrs, data = elem.tag, elem.attrib, elem.text
                self.code.append((attrs.get('name', 'new'), deslash(data) if data is not None else ''))

        #TODO: warning/error message system is buggy

        #for e in self.warn:
        #    if e not in warn:
        #        warn.append(e, type='warn')
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)

        return self.warn if len(self.warn) > 0 else None

    def save(self, path=None, griddata=[], compress=False):
        if path is not None:
            if path.find('.lpj') == -1:
                path += '.lpj'
        if path is None:
            path = self.path
        else:
            self.path = os.path.abspath(path)

        def a2unicode(text):
            return tw.fill(' '.join(['%.15g'%x for x in text]))

        root = ET.Element('root')
        for p in range(len(self)):
            plot_elem = ET.SubElement(root, 'plot')
            if self[p].xrng is not None:
                plot_elem.attrib['xrng'] = '{:.16g},{:.16g}'.format(self[p].xrng[0],self[p].xrng[1])
            if self[p].yrng is not None:
                plot_elem.attrib['yrng'] = '{:.16g},{:.16g}'.format(self[p].yrng[0],self[p].yrng[1])
            plot_elem.attrib['uuid'] = self[p].uuid
            plot_elem.attrib['name'] = self[p].name

            for s in range(len(self[p])):
                set_elem = ET.SubElement(plot_elem, 'set')
                if self[p][s].hide:
                    set_elem.attrib['hide'] = 'True'
                set_elem.attrib['x'] = ' '.join(['{:.16g}'.format(q) for q in self[p][s].data[0]])
                set_elem.attrib['y'] = ' '.join(['{:.16g}'.format(q) for q in self[p][s].data[1]])
                if self[p][s].has_second_y:
                    set_elem.attrib['y2'] = ' '.join(['{:.16g}'.format(q) for q in self[p][s].data[2]])
                set_elem.attrib['name'] = slash(self[p][s].name)

                if self[p][s].limits is not None:
                    set_elem.attrib['limits'] = ' '.join(['{:.16g}'.format(q) for q in self[p][s].limits])

                if self[p][s].mod is not None:
                    mod_elem = ET.SubElement(set_elem, 'mod')
                    mod_elem.attrib['tokens'] = self[p][s].mod.tokens
                    if self[p][s].mod.tokens == 'CUSTOM':
                        mod_elem.attrib['func'] = self[p][s].mod.func
                    for feat in self[p][s].mod:
                        token_elem = ET.SubElement(mod_elem, 'token')
                        token_elem.attrib['name'] = feat.name
                        for par in feat.keys():
                            par_elem = ET.SubElement(token_elem, 'var')
                            tmp = {'name':par,'value':str(feat[par].value),'error':str(feat[par].error)}
                            if feat[par].constr == 2:
                                if feat[par].amin is not None:
                                    tmp['amin'] = str(feat[par].amin)
                                if feat[par].amax is not None:
                                    tmp['amax'] = str(feat[par].amax)
                            elif feat[par].constr == 1:
                                tmp['fix'] = 'True'
                            par_elem.attrib.update(tmp)

                if self[p][s].weights is not None:
                    weights_elem = ET.SubElement(set_elem, 'weights')
                    for w in self[p][s].weights:
                        wreg_elem = ET.SubElement(weights_elem, 'weightsregion')
                        wreg_elem.attrib = {'lower':str(w.xmin),'upper':str(w.xmax),'rel':str(w.w_rel),'abs':str(w.w_abs),'mode':str(w.mode)}

                if len(self[p][s].trafo) > 0:
                    for axis,trafo,comment,skip in self[p][s].trafo:
                        trafo_elem = ET.SubElement(set_elem, 'trafo')
                        trafo_elem.attrib = {'axis':axis, 'trafo':trafo,'comment':slash(comment),'skip':str(skip)}

                if sometrue(self[p][s].mask != 0):
                    mask_elem = ET.SubElement(set_elem, 'mask')
                    mask_elem.attrib = {'data':a2unicode(self[p][s].mask)}

        for mpmodel in self.figure_list:
            mpm_elem = ET.SubElement(root, 'mpmodel')
            settings = mpmodel.to_xml()
            sett_elem = ET.SubElement(mpm_elem, 'settings')
            for k,v in settings.items():
                elem = ET.SubElement(sett_elem,k)
                elem.text = v
            for pos,pd in mpmodel.items():
                fig_elem = ET.SubElement(mpm_elem, 'figure')
                fig_elem.attrib = {'row':str(pos[0]), 'col':str(pos[1])}

                #fig_elem = ET.SubElement(root, 'figure')
                ref, settings, data = pd.to_xml()
                fig_elem.attrib['plotref'] = ref
                sett_elem = ET.SubElement(fig_elem, 'settings')
                for k,v in settings.items():
                    elem = ET.SubElement(sett_elem,k)
                    elem.text = v
                data_elem = ET.SubElement(fig_elem, 'linedata')
                data_elem.text = '\n'.join(data)

        for d in griddata:
            grid_elem = ET.SubElement(root, 'griddata')
            tmp = {'name':slash(d.name)}

            if len(d.table.rowlabels) > 0:
                tmp['rowlabels'] = ';'.join(['%d:::%s'%(p,q) for p,q in d.table.rowlabels])
            if len(d.table.collabels) > 0:
                tmp['collabels'] = ';'.join(['%d:::%s'%(p,q) for p,q in d.table.collabels])
            if d.the_grid:
                tmp['thegrid'] = 'True'
            grid_elem.attrib = tmp
            grid_elem.text = '\n'.join([' '.join(['%.15g'%x for x in row]) for row in d.table.data])

        if self.annotations is not None:
            an_elem = ET.SubElement(root, 'annotations')
            an_elem.text = slash(self.annotations)

        if self.code is not None:
            for name,data in self.code:
                if data.strip() != '':
                    code_elem = ET.SubElement(root, 'code')
                    code_elem.attrib = {'name':name}
                    code_elem.text = slash(data)

        tree = ET.ElementTree(root)

        f = Queue()
        try:
            tree.write(f)
        except:
            typ, val, trb = sys.exc_info()
            traceback.print_tb(trb)
            print(typ,val)
            return '%s: %s'%(typ, val)
        else:
            data = f.getvalue()
            #data = data.decode("utf-8")
            if os.path.exists(path):
                try:
                    shutil.copy(path,path+'~')
                except:
                    traceback.print_exc()
                    print('unable to create backup file')
            try:
                if compress:
                    f = gzip.open(path.encode(sys.getfilesystemencoding()), 'wb')
                else:
                    f = open(path.encode(sys.getfilesystemencoding()), 'wb')
                #encode = codecs.getencoder('utf-8')
                #data, l = encode(data)
                f.write(data)
                f.close()
            except:
                typ, val, trb = sys.exc_info()
                traceback.print_tb(trb)
                print(typ,val)
                return '%s: %s'%(typ, val)
        self.path = os.path.abspath(path)
        self.name = os.path.basename(path)
        return None
    Write = save

if __name__ == '__main__':
    import unittest
    from operator import add
    
    class tests(unittest.TestCase):
        def __init__(self, *args, **kwargs):
            unittest.TestCase.__init__(self, *args, **kwargs)
            self.a = LData()
            for i in range(5):
                self.a.add(str(i))

        def test1(self):
            self.a.move(1,3)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '02134')
            
        def test2(self):
            self.a.move(3,1)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '03124')
            
        def test3(self):
            self.a.move(3,3)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '01234')
            
        def test4(self):
            self.a.move([0,2,4],2)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '10243')

        def test5(self):
            print('tedst5')
            print(self.a)
            self.a.move([0,1,2,3,4],2)
            print(self.a)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '01234')

        def test6(self):
            self.a.delete([1,4])
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '023')
            
        def test7(self):
            out = self.a.delete([1,4])
            self.a.insert(-1, out)
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '02143')

        def test8(self):
            self.a.insert(2, ['8','9'])
            order = reduce(add, [str(x) for x in self.a])
            self.assertTrue(order == '0189234')
            
    unittest.main()

