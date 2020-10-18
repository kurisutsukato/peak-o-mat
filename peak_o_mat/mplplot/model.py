from copy import copy, deepcopy

import wx.dataview as dv
import uuid
import types
import hashlib
import gc

from matplotlib.markers import MarkerStyle
import matplotlib._color_data as mcd

textbool = lambda x: x == 'True'
string = lambda x: str(x) if x is not None else ''

def s2f(arg):
    try:
        return float(arg)
    except:
        return None

class KeyList(list):
    #TODO: remove oldkeys, used only in old project file versions
    oldkeys = ['xpri','ypri','xsec','ysec']
    keys = ['x','y','twinx','twiny','insetx','insety']
    def __contains__(self, item):
        for i in self:
            if i.type == item:
                return True
        return False
    def append(self, item):
        if item.type not in self.keys:
            item.type = dict([*zip(self.oldkeys,self.keys)])[item.type]
        assert item.type in self.keys
        super(KeyList, self).append(item)
    def __getitem__(self, item):
        if type(item) == str:
            assert item in self.keys
            for l in self:
                if l.type == item:
                    return l
            raise KeyError(item)
        else:
            return super(KeyList, self).__getitem__(item)

    @classmethod
    def fromlist(cls, data):
        return cls([(cls.keys[n], data[n]) for n in range(len(data))])

class DoubleList(list):
    def __init__(self, ld_primary=[], ld_secondary=[]):
        self.pri = ld_primary
        self.sec = ld_secondary

    def __iter__(self):
        for n in self.pri+self.sec:
            yield n

    def __getitem__(self, item):
        return (self.pri+self.sec)[item]

    def add_second(self, data):
        self.sec = data

class Box:
    def __init__(self, *args):
        if len(args) == 4:
            self.left, self.bottom, self.width, self.height = args
        else:
            self.left, self.bottom, self.width, self.height = 60, 60, 35, 35

    def to_xml(self):
        return ','.join([str(q) for q in [self.left, self.bottom, self.width, self.height]])

    @classmethod
    def from_xml(cls, xmlattr):
        try:
            return cls(*[int(q) for q in xmlattr.split(',')])
        except AttributeError:
            return cls()

    def bnds(self):
        return [self.left/100, self.bottom/100, self.width/100, self.height/100]

class PlotData(object):
    _attrs = ['legend_show', 'legend_fontsize', 'legend_position', 'fontsize', 'label_title', 'legend_frameon', 'box']

    _types = [textbool, int, int, int, string, textbool, Box.from_xml]

    _defaults = [False, 12, 0, 10, '', True, None]

    def release(self):
        self.project[self.plot_ref].del_ref(self.uuid)
        if self.plot_ref_secondary is not None:
            self.project[self.plot_ref_secondary].del_ref(self.uuid)

    def __deepcopy__(self, memo):
        #print('deepcopy', self.project, self.plot_ref, self.plot_ref_secondary, self.plot_hash)
        obj = PlotData(self.project, self.plot_ref, self.plot_ref_secondary, plot_hash=self.plot_hash,
                       linedata=deepcopy(self.line_data, memo),
                       axesdata=deepcopy(self.axes_data, memo))
        for attr in self._attrs:
            setattr(obj, attr, getattr(self, attr))
        return obj

    def equals(self, other):
        #TODO: scheint nicht gebraucht zu werden
        '''
        not used
        '''
        if other is None:
            return False
        for attr in self._attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __init__(self, project, plot, plot_secondary=None, linedata=None, axesdata=None, plot_hash=None, plot_hash_secondary=None):
        self.plot_hash = project[plot].hash if plot_hash is None else plot_hash
        self.plot_hash_secondary = project[plot_secondary].hash if plot_secondary is not None and plot_hash_secondary is None else plot_hash_secondary
        print('pd init hahes:',self.plot_hash, self.plot_hash_secondary)
        self.uuid = uuid.uuid4().hex
        self.project = project

        self.plot_ref = project[plot].uuid
        self.plot_ref_secondary = plot_secondary

        self.project[self.plot_ref].add_ref(self.uuid)
        if self.plot_ref_secondary is not None:
            self.project[self.plot_ref_secondary].add_ref(self.uuid)

        name = project[plot].name
        self.name = name if name != '' else 'p{}'.format(project.index(plot))

        if linedata is None:
            # init line data for primary axis
            self.line_data = DoubleList(self.init_line_data(self.plot_ref, linedata))
        else:
            # lineadata is a DoubleList
            self.line_data = linedata

        # init standard axes
        self.axes_data = self.init_axes_data(axesdata)

        for attr, default in zip(self._attrs, self._defaults):
            setattr(self, attr, default)
        self.box = Box()

    def add_secondary(self, plot):
        self.project[plot].add_ref(self.uuid)
        self.plot_ref_secondary = self.project[plot].uuid
        self.line_data.add_second(self.init_line_data(self.plot_ref_secondary))

    def del_secondary(self):
        self.project[self.plot_ref_secondary].del_ref(self.uuid)
        self.plot_ref_secondary = None
        self.line_data.sec = []

    @property
    def figsize(self):
        return (self.width, self.height)
    @figsize.setter
    def figsize(self, size):
        self.width, self.height = size

    @classmethod
    def from_xml(cls, project, uid, uid_secondary, xmlattrs, linedata, axesdata):
        ld = None
        ad = None
        if linedata is not None:
            ldpri = [LineData(*[tp(q) for q,tp in zip(line.split('|'), LineData._in_types)]) for line in linedata[0].strip().split('\n')]
            try:
                ldsec = [LineData(*[tp(q) for q,tp in zip(line.split('|'), LineData._in_types)]) for line in linedata[1].strip().split('\n')]
            except IndexError:
                ldsec = []
            ld = DoubleList(ldpri, ldsec)
        if axesdata is not None:
            ad = [AxesData(*[tp(q) for q,tp in zip(line.split('|'),AxesData._in_types)]) for line in axesdata.strip().split('\n')]
        pd = cls(project, uid, uid_secondary, ld, ad)
        for tp,attr,default in zip(cls._types, cls._attrs, cls._defaults):
            setattr(pd, attr, tp(xmlattrs.get(attr, default)))
        return pd

    def to_xml(self):
        settings = {}
        for attr in self._attrs:
            if attr == 'box':
                if len(self.axes_data) == 4:
                    settings[attr] = getattr(self, attr).to_xml()
            else:
                settings[attr] = str(getattr(self, attr))
        ldpri = ['|'.join([str(q) for q in line]) for line in self.line_data.pri]
        ldsec = ['|'.join([str(q) for q in line]) for line in self.line_data.sec]
        ad = ['|'.join([str(q) for q in ax]) for ax in self.axes_data]
        return self.plot_ref, self.plot_ref_secondary, settings, ldpri, ldsec, ad

    @property
    def plot_modified(self):
        return self.plot_hash == self.project[self.plot_ref].hash

    @property
    def plot_exists(self):
        return self.plot_ref in self.project

    def init_axes_data(self, data=None):
        if data is None:
            data = KeyList()
            data.append(AxesData('x', 'x label', 'bottom', '', '', 'linear', False, 3, '', '', 'in', '0, 0, 0'))
            data.append(AxesData('y', 'y label', 'left', '', '', 'linear', False, -1, '', '', 'in', '0, 0, 0'))
            #data.append(AxesData('twinx', 'y label', 'left', '', '', 'linear', False, -1, '', '', 'in'))
        else:
            data = KeyList(data)
        return data

    def init_line_data(self, plot_ref, data=None):
        if data is None:
            data = []
            df = LineDataFactory()
            for s in self.project[plot_ref]:
                data.append(df.next_with_name(s.name))
        return data

    @property
    def modified(self):
        if self.plot_hash != self.project[self.plot_ref].hash or (self.plot_ref_secondary is not None and \
                        self.plot_hash_secondary != self.project[self.plot_ref_secondary].hash):
            self.sync_with_plot()
            return True
        return False

    def sync_with_plot(self):

        nlines = len(self.line_data.pri)
        diff = len(self.project[self.plot_ref])-nlines
        df = LineDataFactory()
        for n,s in zip(list(range(diff)), self.project[self.plot_ref][nlines:]):
            self.line_data.pri.append(df.next_with_name(s.name))
        self.line_data.pri = self.line_data.pri[:len(self.project[self.plot_ref])]
        self.plot_hash = self.project[self.plot_ref].hash

        nlines = len(self.line_data.sec)
        if self.plot_ref_secondary is not None:
            diff = len(self.project[self.plot_ref_secondary])-nlines
            df = LineDataFactory()
            for n,s in zip(list(range(diff)), self.project[self.plot_ref_secondary][nlines:]):
                self.line_data.sec.append(df.next_with_name(s.name))
            self.line_data.sec = self.line_data.sec[:len(self.project[self.plot_ref])]
            self.plot_hash_secondary = self.project[self.plot_ref_secondary].hash

    def hash(self):
        return ''.join([repr(getattr(self, q)) for q in self._attrs])

    def update_from_view(self, view):
        hash = self.hash()
        self.identifier = view.txt_identifier.Value

        self.legend_show = view.chk_legend.Value
        self.legend_fontsize = int(view.spn_legend_fontsize.Value)
        self.legend_position = int(view.spn_legend_position.Value)
        self.legend_frameon = bool(view.chk_legend_frameon.Value)
        self.label_title = str(view.txt_title.Value)

        self.fontsize = int(view.spn_fontsize.Value)

        self.figsize = view.plot_view.canvas.GetSize()
        return hash != self.hash()

    def get_range(self):
        xrng, yrng = self.project[self.plot_ref].rng
        xrng = xrng or (None,None)
        yrng = yrng or (None,None)

        return (s2f(self.min_x),s2f(self.max_x)), (s2f(self.min_y),s2f(self.max_y))

    @property
    def xrng(self):
        return self.get_range()[0]
    @property
    def yrng(self):
        return self.get_range()[1]

    def primary(self):
        for p,q in zip(self.project[self.plot_ref],self.line_data.pri):
            if not p.hide and q.show:
                yield p,q

    def secondary(self):
        for p,q in zip(self.project[self.plot_ref_secondary],self.line_data.sec):
            if not p.hide and q.show:
                yield p,q

    def human_readable(self):
        return '\n'.join([str((k,v)) for k,v in self.__dict__.items()])

class LineDataFactory:
    def __init__(self):
        self.index = [0,0]

    def next_with_name(self, name):
        d = LineData(LineData.styles[self.index[0]],'','1','8',LineData.colors[self.index[1]],'1.0',name,True)
        self.index[1] += 1
        if self.index[1] == len(LineData.colors):
            self.index[0] += 1
            self.index[1] = 0
            if self.index[0] == len(LineData.styles):
                self.index[0] = 0
        return d

import re

def color2str(arg):
    assert len(arg) == 3
    return '{:.2f},{:.2f},{:.2f}'.format(*arg)

def str2color(arg):
    items = re.findall(r'(?:^|,)([^,]*)(?=,|$)',arg)
    if len(items) in [3,4]:
        return tuple([float(q) for q in items])
    else:
        return 0,0,0

def str2tupleorNone(arg):
    items = re.findall(r'(?:^|,)([^,]*)(?=,|$)',arg)
    if len(items) > 1:
        return tuple([float(q) for q in items])
    else:
        return None

class AxesData:
    # ex_types are the kwargs understood by figure.plot
    _ex_types = [str, str, str, float, float, str, bool,
                 int, str, str, str,
                 str2color]

    # in types are used to parse the xml data
    _in_types = [str, str, str, str, str, str, textbool,
                 int, str, str, str,
                 str]

    _attrs = ['type', 'label', 'labelpos', 'min', 'max', 'scale',
              'ticks_hide', 'ticks_prec',
              'ticks_major', 'ticks_minor', 'tdir',
              'color'
              ]

    def __init__(self, *args):
        for n,arg in enumerate(args):
            setattr(self, self._attrs[n], arg)

    def __getitem__(self, item):
        return getattr(self, self._attrs[item])
    def __setitem__(self, key, value):
        setattr(self, self._attrs[key], value)

    def __str__(self):
        return str([getattr(self, q) for q in self._attrs])

class LineData:
    # ex_types are the kwargs understood by figure.plot
    _plt_types = [str, str, float, float, str2color, float, str, bool]

    # in types are used to parse the xml data
    _in_types = [str, str, str, str, str, str, str, textbool]
    _attrs = ['linestyle','marker','linewidth','markersize','color','alpha','label','show']

    styles = ['-','--','-.',':']
    #markers = ['.',',','o','v','^','<','>','1','2','3','4','8','s','p','*','h','H','+','x','D','d','|','_']
    markers = list(MarkerStyle.filled_markers)
    colors = ['0,0,0',
              '1,0,0',
              '0,1,0',
              '0,0,1',
              '1,1,0',
              '0,1,1',
              '1,0,1',
              '0.5,0,0',
              '0.5,0.5,0',
              '0,0.5,0',
              '0.5,0,0.5',
              '0,0.5,0.5',
              '0,0,0.5']

    def __init__(self, *args):
        for n,arg in enumerate(args):
            setattr(self, self._attrs[n], arg)
    def __getitem__(self, item):
        return getattr(self, self._attrs[item])
    def __setitem__(self, key, value):
        setattr(self, self._attrs[key], value)

    def kwargs(self):
        kw = dict([(q,p(getattr(self,q))) for q,p in zip(self._attrs[:-1], self._plt_types[:-1])])
        #if not self.show:
        #    kw['label'] = '_nolegend_'
        return kw

    def __str__(self):
        return str([getattr(self, q) for q in self._attrs])

class MultiPlotModel(dict):
    attrs = ['identifier',
             'bottom','top','left','right',
             'wspace','hspace',
             'width','height']
    types = [string, float, float, float, float, float, float, float, float]

    defaults = ['untitled', 0.1, 0.9, 0.1, 0.9, 0.1, 0.1, 5, 4]

    def __init__(self, project, data={}):
        self.project = project
        self.__shape = None
        self.__order = {}
        self.selected = None
        super(MultiPlotModel, self).__init__(data)

        for attr, default in zip(self.attrs, self.defaults):
            setattr(self, attr, default)

    def orderediteritems(self):
        for k,v in self.__order.items():
            yield k,self[v]

    def pop(self, k, d=None):
        if type(k) == tuple:
            return super(MultiPlotModel,self).pop(k,d)
        else:
            for pos,v in list(self.items()):
                if v.name == k:
                    return self.pop(pos)
        return d

    def __del__(self):
        vals = self.values()
        for v in vals:
            v.release()

    def __deepcopy__(self, memo):
        mpm = copy(self)
        mpm.selected = None

        pd = {}
        for k,v in self.items():
            pd[k] = deepcopy(v, memo)
        mpm = MultiPlotModel(self.project, pd)
        for attr in self.attrs:
            setattr(mpm, attr, getattr(self, attr))
        mpm.__order = dict(self.__order)
        mpm.__shape = self.shape
        return mpm

    def __getitem__(self, item):
        if type(item) == bytes:
            for k,v in self.items():
                if v.name == item:
                    return self[k]
            raise KeyError(item)
        else:
            if item in self.keys():
                return super(MultiPlotModel, self).__getitem__(item)
            else:
                return None

    def add(self, plotdata, pos):
        #plotdata = PlotData(self.project, plot)
        #if plotdata is None:
        #    plotdata = PlotData(self.project, 0)

        if pos in self:
            #TODO:wieso wird nur die plot_Ref ausgetauscht? das gibt doch Aerger mit den referenzen
            #self[pos].plot_ref = plotdata.plot_ref

            self[pos] = plotdata
        else:
            self.update({pos: plotdata})
        self.__order.update({pos:plotdata.name})
        self.select(pos)

    def remove(self, pos):
        item = self[pos]
        self[pos] = None
        try:
            item.release()
        except AttributeError:
            # happens if item is empty (= None)
            pass


    def select(self, pos):
        if pos in self:
            self.selected = self[pos]
            return True
        else:
            self.selected = None
            return False

    @property
    def order(self):
        return self.__order

    def swap(self, frm, to):
        if frm in list(self.keys()) and to in list(self.keys()):
            self[frm], self[to] = self[to], self[frm]
        elif frm in list(self.keys()):
            self[to] = self[frm]
            self.pop(frm)
        elif to in list(self.keys()):
            self[frm] = self[to]
            self.pop(to)

    def equals(self, other):
        if other is None:
            return False
        for attr in self.attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    @classmethod
    def from_xml(cls, project, xmlattrs):
        mpm = cls(project)
        for tp,attr,default in zip(cls.types, cls.attrs, cls.defaults):
            setattr(mpm, attr, tp(xmlattrs.get(attr, default)))
        return mpm

    def to_xml(self):
        settings = {}
        for attr in self.attrs:
            settings[attr] = str(getattr(self, attr))
        return settings

    @property
    def shape(self):
        if self.__shape is None:
            try:
                r,c = list(zip(*list(self.__order.keys())))
            except ValueError:
                return 0,0
            else:
                return max([q+1 for q in r]),max([q+1 for q in c])
        else:
            return self.__shape

    @shape.setter
    def shape(self, shape):
        for k in list(self.keys()):
            if k[0] >= shape[0] or k[1] >= shape[1]:
                self.remove(k)
        self.__shape = shape
        print('newshape',shape,self.keys())

    @property
    def modified(self):
        for pd in list(self.values()):
            if pd.modified:
                return True
        return False

    def hash(self):
        return ''.join([str(getattr(self, q)) for q in self.attrs])

    def update_from_view(self, view):
        #print 'mpmodel.update_from_view'
        modified = False
        hash = self.hash()
        if self.selected is not None:
            modified = self.selected.update_from_view(view)
        self.identifier = view.txt_identifier.Value
        for q in ['bottom','top','left','right','wspace','hspace','width','height']:
            try:
                setattr(self, q, getattr(view,'spn_{}'.format(q)).Value)
            except ValueError:
                pass
        return modified or hash != self.hash()

    @property
    def adjust(self):
        ret = {}
        for margin in ['top','bottom','left','right','hspace','wspace']:
            ret[margin] = getattr(self, margin)
        return ret

if __name__ == '__main__':
    from peak_o_mat.project import Project
    p = Project()
    p.load('../../tata.lpj')






