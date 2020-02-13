from copy import copy, deepcopy

import wx.dataview as dv
import uuid
import types
import hashlib

textbool = lambda x: x == 'True'
string = lambda x: str(x) if x is not None else ''

def s2f(arg):
    try:
        return float(arg)
    except:
        return None

class PlotData(object):
    attrs = ['legend_show','legend_fontsize','legend_position','fontsize',
             'xscale','yscale','symlogthreshx','symlogthreshy',
             'label_x','label_y','label_title',
             'xticks_hide','yticks_hide',
             'xticks_prec','yticks_prec',
             'ticks_major_x', 'ticks_major_y','ticks_minor_x', 'ticks_minor_y',
             'tlabel_pos_x','tlabel_pos_y','tdir_x','tdir_y',
             'min_x', 'max_x', 'min_y', 'max_y',
             'code',
             ]

    types = [textbool, int, int, int,
             int, int,string,string,
             string, string, string,
             textbool, textbool,
             int, int,
             string, string, string, string,
             string, string, string, string,
             string, string, string, string,
             string
             ]

    defaults = [False, 12, 0, 10, 0, 0,'','',
                'x', 'y', '',
                False, False,
                -1, -1,
                '','','','',
                'bottom','left','in','in',
                '','','','',
                '']

    def release(self):
        #TODO: nicer would be to have this done in the desctructor but there is always a reference hanging around
        self.project[self.plot_ref].del_ref(self.uuid)

    def __deepcopy__(self, memo):
        obj = PlotData(self.project, self.plot_ref, plot_hash=self.plot_hash, data=deepcopy(self.line_data, memo))
        for attr in self.attrs:
            setattr(obj, attr, getattr(self, attr))
        self.project[self.plot_ref].del_ref(obj.uuid)
        return obj

    def equals(self, other):
        #TODO: scheint nicht gebraucht zu werden
        '''
        not used
        '''
        if other is None:
            return False
        for attr in self.attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __init__(self, project, plot, data=None, plot_hash=None):
        self.plot_hash = project[plot].hash if plot_hash is None else plot_hash

        name = project[plot].name

        self.name = name if name != '' else 'p{}'.format(project.index(plot))
        self.plot_uuid = project[plot].uuid
        #self.name = project[plot].uuid
        self.plot_ref = project[plot].uuid
        self.uuid = uuid.uuid4().hex
        project[plot].add_ref(self.uuid)

        self.project = project
        self.line_data = self.init_line_data(data)

        for attr, default in zip(self.attrs, self.defaults):
            setattr(self, attr, default)

    @property
    def figsize(self):
        return (self.width, self.height)
    @figsize.setter
    def figsize(self, size):
        self.width, self.height = size

    @classmethod
    def from_xml(cls, project, uid, xmlattrs, xmldata):
        data = [LineData(*[tp(q) for q,tp in zip(line.split('|'),LineData._in_types)]) for line in xmldata.strip().split('\n')]
        pd = cls(project, uid, data)
        for tp,attr,default in zip(cls.types, cls.attrs, cls.defaults):
            setattr(pd, attr, tp(xmlattrs.get(attr, default)))
        return pd

    def to_xml(self):
        settings = {}
        for attr in self.attrs:
            settings[attr] = str(getattr(self, attr))
        data = ['|'.join([str(q) for q in line]) for line in self.line_data]
        return self.plot_ref,settings, data

    @property
    def plot_modified(self):
        return self.plot_hash == self.project[self.plot_ref].hash

    @property
    def plot_exists(self):
        return self.plot_ref in self.project

    def init_line_data(self, data=None):
        if data is None:
            data = []
            df = DataFactory()
            for s in self.project[self.plot_ref]:
                data.append(df.next_with_name(s.name))

        return data
        #return ListModel(data)

    @property
    def modified(self):
        print('pd checking modified',self.plot_hash,self.project[self.plot_ref].hash)
        if self.plot_hash != self.project[self.plot_ref].hash:
            self.sync_with_plot()
            return True
        return False

    def sync_with_plot(self):
        print('syncplot')
        nlines = len(self.line_data.data)
        diff = len(self.project[self.plot_ref])-nlines
        df = DataFactory()
        for n,s in zip(list(range(diff)), self.project[self.plot_ref][nlines:]):
            self.line_data.data.append(df.next_with_name(s.name))
        self.line_data.data = self.line_data.data[:len(self.project[self.plot_ref])]
        self.plot_hash = self.project[self.plot_ref].hash

    def hash(self):
        return ''.join([repr(getattr(self, q)) for q in self.attrs])

    def update_from_view(self, view):
        hash = self.hash()
        self.identifier = view.txt_identifier.Value

        self.legend_show = view.chk_legend.Value
        self.legend_fontsize = int(view.spn_legend_fontsize.Value)
        self.legend_position = int(view.spn_legend_position.Value)
        self.fontsize = int(view.spn_fontsize.Value)
        self.label_x = view.txt_xlabel.Value
        self.label_y = view.txt_ylabel.Value
        self.label_title = view.txt_title.Value

        #self.ticks_major_x = view.txt_xtick_major.Value if view.chk_xtick_custom.Value else ''
        #self.ticks_major_y = view.txt_ytick_major.Value if view.chk_ytick_custom.Value else ''
        #self.ticks_minor_x = view.txt_xtick_minor.Value if view.chk_xtick_custom.Value else ''
        #self.ticks_minor_y = view.txt_ytick_minor.Value if view.chk_ytick_custom.Value else ''

        self.xticks_hide = view.chk_xticks_hide.Value
        self.yticks_hide = view.chk_yticks_hide.Value

        #self.xticks_prec = view.cho_xticks_prec.Selection-1
        #self.yticks_prec = view.cho_yticks_prec.Selection-1

        self.tdir_x = view.cho_xtickdir.GetStringSelection()
        self.tdir_y = view.cho_ytickdir.GetStringSelection()

        self.tlabel_pos_x = view.cho_xlabel_pos.GetStringSelection()
        self.tlabel_pos_y = view.cho_ylabel_pos.GetStringSelection()

        self.min_x = view.txt_xrng_min.Value
        self.min_y = view.txt_yrng_min.Value
        self.max_x = view.txt_xrng_max.Value
        self.max_y = view.txt_yrng_max.Value

        self.code = view.editor.Value

        self.xscale = view.cmb_scalex.Selection
        self.yscale = view.cmb_scaley.Selection

        self.symlogthreshx = view.txt_symlogthreshx.Value
        self.symlogthreshy = view.txt_symlogthreshy.Value

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

    def __iter__(self):
        for p,q in zip(self.project[self.plot_ref],self.line_data):
            if not p.hide:
                yield p,q

    def human_readable(self):
        return '\n'.join([str((k,v)) for k,v in self.__dict__.items()])

class DataFactory:
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

def color(arg):
    items = re.findall(r'(?:^|,)([^,]*)(?=,|$)',arg)
    if len(items) in [3,4]:
        return tuple([float(q) for q in items])
    elif arg in LineData.colors:
        return arg
    else:
        return 'k'

class LineData:
    # ex_types are the kwargs unterstood by figure.plot
    _ex_types = [str, str, int, int, color, float, str, bool]
    # in types are used to parse the xml data
    _in_types = [str, str, str, str, str, str, str, textbool]
    _attrs = ['linestyle','marker','linewidth','markersize','color','alpha','label','show']

    styles = ['-','--','-.',':']
    markers = ['.',',','o','v','^','<','>','1','2','3','4','8','s','p','*','h','H','+','x','D','d','|','_']
    colors = ['black','green','red','blue','magenta','cyan','yellow']

    def __init__(self, *args):
        for n,arg in enumerate(args):
            setattr(self, self._attrs[n], arg)
    def __getitem__(self, item):
        return getattr(self, self._attrs[item])
    def __setitem__(self, key, value):
        setattr(self, self._attrs[key], value)

    def kwargs(self):
        kw = dict([(q,p(getattr(self,q))) for q,p in zip(self._attrs[:-1], self._ex_types[:-1])])
        if not self.show:
            kw['label'] = '_nolegend_'
        return kw

    def __str__(self):
        return str([getattr(self, q) for q in self._attrs])

class ListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self._data = data

        #self.objmapper.UseWeakRefs(True)

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, data):
        self._data = data
        self.Cleared()

    def GetChildren(self, parent, children):
        if not parent:
            for line in self._data:
                children.append(self.ObjectToItem(line))
            return len(self._data)

    def IsContainer(self, item):
        if not item:
            return True
        else:
            return False

    def GetColumnCount(self):
        return 8

    def GetCount(self):
        return len(self.data)

    def GetColumnType(self, col):
        mapper = { 0 : 'string',
                   1 : 'string',
                   2 : 'int',
                   3 : 'int',
                   5 : 'string',
                   6 : 'float',
                   7 : 'string',
                   8 : 'bool',
                   }
        return mapper[col]

    def GetParent(self, item):
        return dv.NullDataViewItem

    def GetValue(self, item, col):
        node = self.ItemToObject(item)
        return node[col]

    def SetValue(self, value, item, col):
        print('set value')
        node = self.ItemToObject(item)
        node[col] = value

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

    #def __del__(self):
    #    print('mpm destructor')
    #    for v in self.values():
    #        v.release()

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
            return super(MultiPlotModel, self).__getitem__(item)

    def add(self, plotdata, pos):
        #plotdata = PlotData(self.project, plot)
        #if plotdata is None:
        #    plotdata = PlotData(self.project, 0)

        if pos in self:
            self[pos].plot_ref = plotdata.plot_ref
        else:
            self.update({pos: plotdata})
        self.__order.update({pos:plotdata.name})
        self.select(pos)

    def remove(self, pos):
        self.pop(pos)

    def old_select(self, pos):
        if pos in self.__order:
            self.selected = self[self.__order[pos]]
            return True
        else:
            self.selected = None
            return False

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
            print(attr, getattr(self, attr), getattr(other, attr))
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
    from copy import copy
    p = Project()
    p.load('example.lpj')
    print(p)
    m = PlotData(p,p[0].uuid)
    m2 = copy(m)
    m.margin_bottom = 0.2
    print(m2.margin_bottom)
    print(m.margin_bottom)

    mpm = MultiPlotModel(p)
    mpm.add((2,1))
    mpm.add((2,3))
    mpm.add((1,4))
    mpm.calculate_shape()
    print(mpm.shape)
