__author__ = 'ck'

import wx
import wx.adv
import wx.dataview as dv
import wx.stc as stc
import matplotlib as mpl
import matplotlib.colorbar as colorbar
from matplotlib import pyplot as plt

import matplotlib._color_data as mcd
import io

mpl.use('Agg')

import numpy as np
from pubsub import pub

from matplotlib.backends.backend_agg import FigureCanvasAgg

from .. import images
from ..controls import PythonSTC, FormatValidator
from ..misc_ui import WithMessage
from ..images import get_bmp
auto = get_bmp('auto.png')

from .plotlayout import PlotLayout
from .model import LineData, color2str, str2color, AxesData

def validfloat(arg):
    if arg == '':
        return True
    try:
        return float(arg)
    except ValueError:
        return None

def validticks(arg):
    if arg == '':
        return True
    try:
        [float(q.strip()) for q in arg.split(',')]
    except (TypeError, ValueError):
        try:
            mi,ma,stp = [float(q.strip()) for q in arg.split(':')]
        except (TypeError, ValueError):
            return False
    return True

_pos = [(-1,-1)]*2

class CmpDlg(wx.MiniFrame):
    def __init__(self, parent):
        super(CmpDlg, self).__init__(parent, size=(180,400))#, style=wx.DEFAULT_FRAME_STYLE|wx.CLOSE_BOX)

        dpi = (90, 90)
        fig = mpl.figure.Figure((1, 0.15), dpi=dpi[0])
        ax = fig.add_axes((0, 0, 1, 1))
        FigureCanvasAgg(fig)
        ax.cla()

        l, b, w, h = fig.bbox.bounds
        w, h = int(w), int(h)

        self.il = wx.ImageList(w, h)

        ids = []
        for n,cmap_id in enumerate(plt.colormaps()[:50:2]):
            col_map = mpl.cm.get_cmap(cmap_id)
            if np.alltrue(np.asarray(col_map(1)) > 0.7) or np.alltrue(np.asarray(col_map(0)) > 0.7):
                continue
            mpl.colorbar.ColorbarBase(ax, cmap=col_map, orientation='horizontal')
            fig.canvas.draw()
            buf = fig.canvas.tostring_rgb()
            bmp = wx.Bitmap.FromBuffer(w, h, buf)
            ids.append((self.il.Add(bmp),cmap_id))
            ax.cla()

        self.list = wx.ListCtrl(self, style=wx.LC_REPORT| wx.BORDER_NONE | wx.LC_NO_HEADER)

        self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        info = wx.ListItem()
        info.Mask = wx.LIST_MASK_IMAGE | wx.LIST_MASK_FORMAT
        info.Image = -1
        info.Align = 0
        info.Text = "cmap"
        self.list.InsertColumn(0, info)

        for k in range(len(ids)):
            index = self.list.InsertItem(self.list.GetItemCount(), ids[k][1], ids[k][0])

        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 1, wx.LEFT, 5)
        self.SetSizer(sizer)
        self.Layout()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        self.Hide()

class AxesControlPanel(WithMessage, wx.Panel):
    def __setattr__(self, attr, val):
        # generate list with all controls
        if issubclass(val.__class__, wx.Window) and val.__class__ != wx.Button and val.Name != 'ignore':
            self.__ctrls.append(val)
        return super(AxesControlPanel, self).__setattr__(attr, val)

    def __init__(self, parent, data=[]):
        self.__ctrls = []
        self.selection = []
        self.__process_queue = []
        self.__axes_data = []

        wx.Panel.__init__(self, parent, -1)
        WithMessage.__init__(self)
        self.setup_controls()
        self.layout()
        self.setup_events()
        self.enable()

    def setup_controls(self):
        self.axes_list = wx.ListCtrl(self, style=wx.LC_LIST|wx.LC_HRULES|wx.LC_SINGLE_SEL, size=(100,-1), name='ignore')

        self.txt_label = wx.TextCtrl(self, value='x label', size=(220,-1), style=wx.TE_PROCESS_ENTER, name='label')
        self.cho_scale = wx.Choice(self, choices=('linear','log'), size=(80,-1), name='scale')
        self.txt_rng_min = wx.TextCtrl(self, value='', size=(60,-1), style=wx.TE_PROCESS_ENTER, name='min')
        self.txt_rng_max = wx.TextCtrl(self, value='', size=(60,-1), style=wx.TE_PROCESS_ENTER, name='max')
        self.txt_rng_min.Hint = 'min.'
        self.txt_rng_max.Hint = 'max.'
        self.txt_rng_min.SetValidator(FormatValidator(validfloat))
        self.txt_rng_max.SetValidator(FormatValidator(validfloat))
        self.chk_ticks_hide = wx.CheckBox(self, -1, name='ticks_hide')
        self.cho_labelpos = wx.Choice(self, size=(80,-1), choices=['bottom', 'top'], name='labelpos')
        self.cho_labelpos.SetSelection(0)
        self.cho_tdir = wx.Choice(self, choices=['in', 'out'], name='tdir')
        self.cho_tdir.SetSelection(0)
        self.bmp_axiscolor = wx.StaticBitmap(self, bitmap=wx.Bitmap(15, 15), size=(15, 15), style=wx.NO_BORDER)
        self.btn_axiscolorchooser = wx.Button(self, label='Select')

        self.btn_add_twinx = wx.Button(self, label='Add twin x', name='twinx')
        self.btn_add_twiny = wx.Button(self, label='Add twin y', name='twiny')
        self.btn_add_inset = wx.Button(self, label='Add inset', name='inset')
        self.btn_remove = wx.Button(self, label='Remove axis', name='remove')

        self.pan_box = wx.Panel(self)

        self.spn_left = wx.SpinCtrl(self.pan_box, value='', min=0, max=100, size=(50,-1), name='left')
        self.spn_bottom = wx.SpinCtrl(self.pan_box, value='', min=0, max=100, size=(50,-1), name='bottom')
        self.spn_width = wx.SpinCtrl(self.pan_box, value='', min=10, max=100, size=(50,-1), name='width')
        self.spn_height = wx.SpinCtrl(self.pan_box, value='', min=10, max=100, size=(50,-1), name='height')

    def layout(self):
        outer = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.axes_list, 1)
        vbox.Add(self.btn_add_twinx, 0, wx.EXPAND|wx.TOP, 5)
        vbox.Add(self.btn_add_twiny, 0, wx.EXPAND | wx.TOP, 5)
        vbox.Add(self.btn_add_inset, 0, wx.EXPAND | wx.TOP, 5)
        vbox.Add(self.btn_remove, 0, wx.EXPAND | wx.TOP, 5)

        outer.Add(vbox, 0, wx.ALL | wx.EXPAND, 5)

        fb = wx.GridBagSizer(hgap=10, vgap=5)
        def Add(*args, **kwargs):
            fb.Add(*args, **kwargs, flag=wx.ALIGN_CENTER_VERTICAL)

        Add(wx.StaticText(self, label='Label'), (0,0))
        Add(self.txt_label, (0,1), (1,2))
        Add(wx.StaticText(self, label='Position'), (1,0))
        Add(self.cho_labelpos, (1, 1))

        Add(wx.StaticText(self, label='Scale'), (2,0))
        Add(self.cho_scale, (2,1))

        Add(wx.StaticText(self, label='Range'), (3,0))
        Add(self.txt_rng_min, (3,1))
        Add(self.txt_rng_max, (3,2))

        #Add(wx.StaticText(self, -1, 'Ticklabel precision'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #Add(self.cho_xticks_prec, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)

        Add(wx.StaticText(self, label='Hide ticks'), (4,0))
        Add(self.chk_ticks_hide, (4,1))
        Add(wx.StaticText(self, label='Tick direction'), (5,0))
        Add(self.cho_tdir, (5, 1))

        Add(wx.StaticText(self, label='Line color'), (6,0))
        Add(self.bmp_axiscolor, (6, 1))
        Add(self.btn_axiscolorchooser, (6, 2))

        outer.Add(fb, 0, wx.TOP|wx.LEFT|wx.EXPAND, 5)

        fb = wx.GridBagSizer(hgap=10, vgap=5)
        Add(wx.StaticText(self.pan_box, label='Inset geometry'), (0,0))
        Add(wx.StaticText(self.pan_box, label='Left (%)'), (1,0))
        Add(self.spn_left, (1,1))
        Add(wx.StaticText(self.pan_box, label='Bottom (%)'), (2,0))
        Add(self.spn_bottom, (2,1))
        Add(wx.StaticText(self.pan_box, label='Width (%)'), (3,0))
        Add(self.spn_width, (3,1))
        Add(wx.StaticText(self.pan_box, label='Height (%)'), (4,0))
        Add(self.spn_height, (4,1))
        self.pan_box.SetSizer(fb)
        outer.Add(self.pan_box, 0, wx.TOP|wx.LEFT|wx.EXPAND, 5)

        self.SetSizer(outer)
        self.Layout()

    def setup_events(self):
        self.Bind(wx.EVT_CHECKBOX, self.OnCheck)
        self.Bind(wx.EVT_CHOICE, self.OnAxesAttrChoice)
        self.Bind(wx.EVT_TEXT, self.OnAxesAttrText)
        self.axes_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.axes_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnDeSelect)
        self.Bind(wx.EVT_IDLE, self.OnProcess)
        self.btn_axiscolorchooser.Bind(wx.EVT_BUTTON, self.OnShowColorDlg)

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def associate_model(self, axes_data, has_second=False, box=None):
        assert box is not None
        self.__axes_data = axes_data
        self.__box = box
        self.selection = []
        self.axes_list.ClearAll()
        for ax in axes_data:
            self.axes_list.Append([ax.type])
        if self.axes_list.ItemCount > 0:
            self.axes_list.Select(0)

        self.btn_add_inset.Enable(has_second and len(self.__axes_data) == 2)
        self.btn_add_twinx.Enable(has_second and len(self.__axes_data) == 2)
        self.btn_add_twiny.Enable(has_second and len(self.__axes_data) == 2)

    def gen_bitmap(self, color=None):
        size = self.bmp_axiscolor.GetSize()
        w, h = size
        bmp = wx.Bitmap(*size)
        temp_dc = wx.MemoryDC()
        temp_dc.SelectObject(bmp)
        if color is None:
            temp_dc.SetPen(wx.Pen(wx.WHITE))
            temp_dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            temp_dc.DrawRectangle(0, 0, w, h)
            temp_dc.SetPen(wx.Pen(wx.LIGHT_GREY))
            temp_dc.DrawLine(0, 0, w, h)
            temp_dc.DrawLine(0, h, w, 0)
        else:
            temp_dc.SetPen(wx.Pen(wx.Colour(*color)))
            temp_dc.SetBrush(wx.Brush(wx.Colour(*color), wx.SOLID))
            temp_dc.DrawRectangle(0, 0, w, h)
        temp_dc.SelectObject(wx.NullBitmap)
        return bmp

    def OnShowColorDlg(self, evt):
        cd = wx.ColourData()
        c = (np.asarray(str2color(self.__axes_data[self.selection[0]].color))*255).astype(int)
        cd.SetColour(wx.Colour(c))
        dlg  = wx.ColourDialog(self, cd)

        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            colormpl = np.around(np.asarray(color, dtype=float)/255, 2).tolist()

            ld = self.__axes_data
            for s in self.selection:
                setattr(ld[s], 'color', color2str(colormpl[:3]))
            self.bmp_axiscolor.SetBitmap(self.gen_bitmap(color))
        pub.sendMessage((self.instid, 'axesattrs', 'changed'))

    def OnCheck(self, evt):
        obj = evt.GetEventObject()
        item = obj.Name

        ad = self.__axes_data
        s = self.selection[0]
        setattr(ad[s], item, obj.Value)
        pub.sendMessage((self.instid, 'axesattrs', 'changed'))

    def OnAxesAttrText(self, evt):
        obj = evt.GetEventObject()
        item = obj.Name

        ad = self.__axes_data
        s = self.selection[0]
        if item in ['left','bottom','width','height']:
            setattr(self.__box, item, obj.Value)
            pub.sendMessage((self.instid, 'plotattrs', 'changed'))
        else:
            setattr(ad[s], item, obj.Value)
            pub.sendMessage((self.instid, 'axesattrs', 'changed'))

    def OnAxesAttrChoice(self, evt):
        obj = evt.GetEventObject()
        item = obj.Name

        ad = self.__axes_data
        s = self.selection[0]
        ctrl = getattr(self,'cho_{}'.format(item))
        val = ctrl.GetString(ctrl.GetSelection())
        setattr(ad[s], item, val)
        pub.sendMessage((self.instid, 'axesattrs', 'changed'))

    def OnProcess(self, evt):
        if len(self.__process_queue) > 0:
            self.btn_remove.Enable(len(self.selection) > 0 and self.selection not in [[0],[1]])
            self.pan_box.Show(self.axes_list.ItemCount == 4)

            self.__process_queue[0]()
            self.__process_queue.clear()

    def OnDeSelect(self, evt):
        self.selection.remove(evt.Index)
        self.__process_queue.append(self.enable)

    def OnSelect(self, evt):
        self.selection.append(evt.Index)
        self.__process_queue.append(self.enable)

    def enable(self):
        for c in self.__ctrls:
            if c.Name != 'ignore':
                wx.CallAfter(c.Enable, len(self.selection) > 0)
        if len(self.selection) == 0:
            return

        self.silent = True

        labelpos = {'x': ['bottom','top'],
                    'y': ['left','right'],
                    'twinx':['left','right'],
                    'twiny': ['bottom','top'],
                    'insety': ['left','right'],
                    'insetx': ['bottom','top'],
                    }

        self.cho_labelpos.Clear()
        self.cho_labelpos.AppendItems(labelpos[self.__axes_data[self.selection[0]].type])

        self.txt_rng_min.ChangeValue(self.__axes_data[self.selection[0]].min)
        self.txt_rng_max.ChangeValue(self.__axes_data[self.selection[0]].max)

        self.txt_label.ChangeValue(self.__axes_data[self.selection[0]].label)

        for attr in ['scale','labelpos']:
            ctrl = getattr(self,'cho_{}'.format(attr))
            val = getattr(self.__axes_data[self.selection[0]],attr)
            ctrl.SetSelection(ctrl.FindString(val))

        self.cho_tdir.SetSelection(self.cho_tdir.FindString(self.__axes_data[self.selection[0]].tdir))
        self.chk_ticks_hide.SetValue(self.__axes_data[self.selection[0]].ticks_hide)

        color = str2color(self.__axes_data[self.selection[0]].color)
        color = (np.asarray(color)*255).astype(int)
        self.bmp_axiscolor.SetBitmap(self.gen_bitmap(color))

        for dim in ['left','bottom','width','height']:
            getattr(self, 'spn_{}'.format(dim)).Value = str(getattr(self.__box, dim))
        self.Refresh()

        self.silent = False

class LineControlPanel(WithMessage, wx.Panel):
    def __setattr__(self, attr, val):
        if issubclass(val.__class__, wx.Window) and val.Name != 'ignore':
            self.__ctrls.append(val)
        return super(LineControlPanel, self).__setattr__(attr, val)

    def __init__(self, parent, data=[]):
        self.__ctrls = []
        self.selection = []
        self.__process_queue = []

        wx.Panel.__init__(self, parent, -1)
        WithMessage.__init__(self)

        self.dataset_list = wx.ListCtrl(self, style=wx.LC_LIST|wx.LC_HRULES, size=(200,-1), name='ignore')
        self.txt_label = wx.TextCtrl(self, size=(120,-1), name='label')
        self.cho_linestyle = wx.Choice(self, size=(100,-1), name='linestyle')
        self.spn_linewidth = wx.SpinCtrlDouble(self, min=0.5, initial=1, max=50, inc=0.5, size=(100,-1), name='linewidth')
        self.cho_marker = wx.Choice(self, size=(100,-1), name='marker')
        self.spn_markersize = wx.SpinCtrl(self, min=2, initial=8, max=50, size=(100,-1), name='markersize')
        self.chk_show = wx.CheckBox(self, label='', name='show')
        self.chk_show.SetValue(True)

        self.spn_alpha = wx.SpinCtrlDouble(self, min=0.1, initial=1, max=1, inc=0.1, name='alpha', size=(100, -1))
        self.bmp_linecolor = wx.StaticBitmap(self, bitmap=wx.Bitmap(15,15), size=(15,15), style=wx.NO_BORDER)
        self.btn_linecolorchooser = wx.Button(self, label='Select')
        #self.btn_linecolorchooser = PenStyleComboBox(self, choices=penStyles, style=wx.CB_READONLY)
        self.btn_linecolorrange = wx.Button(self, label='Waterfall')
        self.dlg_colorrange = CmpDlg(self)

        outer = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.dataset_list, 1)

        outer.Add(vbox, 0, wx.ALL|wx.EXPAND, 5)

        grd = wx.FlexGridSizer(cols=2, hgap=2, vgap=5)

        grd.Add(wx.StaticText(self, label='Label'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.txt_label, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Show'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.chk_show, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Line style'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.cho_linestyle, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Line width'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.spn_linewidth, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Line color'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        hb = wx.BoxSizer(wx.HORIZONTAL)
        hb.Add(self.bmp_linecolor, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        hb.Add(self.btn_linecolorchooser, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        hb.Add(self.btn_linecolorrange, 0, wx.ALIGN_CENTER_VERTICAL)
        grd.Add(hb, 1, wx.ALIGN_CENTER_VERTICAL)

        grd.Add(wx.StaticText(self, label='Marker style'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.cho_marker, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Marker size'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.spn_markersize, 1, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)

        grd.Add(wx.StaticText(self, label='Alpha'), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        grd.Add(self.spn_alpha, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        outer.Add(grd, 0, wx.ALL|wx.LEFT|wx.EXPAND, 5)
        self.SetSizer(outer)
        self.Layout()

        self.dlg_colorrange.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnColorRangeSelect)

        self.btn_linecolorchooser.Bind(wx.EVT_BUTTON, self.OnShowColorDlg)
        self.btn_linecolorrange.Bind(wx.EVT_BUTTON, self.OnShowRangeDlg)
        self.Bind(wx.EVT_CHOICE, self.OnLineAttrChoice)
        self.Bind(wx.EVT_TEXT, self.OnLineAttrText)
        self.Bind(wx.EVT_CHECKBOX, self.OnLineAttrText)
        self.dataset_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.dataset_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnDeSelect)
        self.Bind(wx.EVT_IDLE, self.OnProcess)

        self.enable()

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def associate_model(self, line_data, ds_names):
        self.__line_data = line_data
        self.selection = []
        self.dataset_list.ClearAll()
        for ld in ds_names:
            self.dataset_list.Append([ld])
        if self.dataset_list.ItemCount > 0:
            self.dataset_list.Select(0)

        self.cho_linestyle.Clear()
        self.cho_linestyle.AppendItems(['None']+LineData.styles)

        self.cho_marker.Clear()
        self.cho_marker.AppendItems(['None']+LineData.markers)

    def gen_bitmap(self, color=None):
        size = self.bmp_linecolor.GetSize()
        w, h = size
        bmp = wx.Bitmap(*size)
        temp_dc = wx.MemoryDC()
        temp_dc.SelectObject(bmp)
        if color is None:
            temp_dc.SetPen(wx.Pen(wx.WHITE))
            temp_dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            temp_dc.DrawRectangle(0, 0, w, h)
            temp_dc.SetPen(wx.Pen(wx.LIGHT_GREY))
            temp_dc.DrawLine(0, 0, w, h)
            temp_dc.DrawLine(0, h, w, 0)
        else:
            temp_dc.SetPen(wx.Pen(wx.Colour(*color)))
            temp_dc.SetBrush(wx.Brush(wx.Colour(*color), wx.SOLID))
            temp_dc.DrawRectangle(0, 0, w, h)
        temp_dc.SelectObject(wx.NullBitmap)
        return bmp

    def OnColorRangeSelect(self, evt):
        self.dlg_colorrange.Hide()
        self.dlg_colorrange.list.Select(evt.Index, 0)
        cmap_id = self.dlg_colorrange.list.GetItemText(evt.Index,0)

        ld = self.__line_data

        for n,(sel, ci) in enumerate(zip(*(sorted(self.selection), np.linspace(0,1,len(self.selection))))):
            color = mpl.cm.get_cmap(cmap_id)(ci)
            setattr(ld[sel], 'color', color2str(color[:-1]))

        pub.sendMessage((self.instid, 'lineattrs', 'changed'))
        self.bmp_linecolor.SetBitmap(self.gen_bitmap(None))
        pub.sendMessage((self.instid, 'lineattrs', 'changed'))

    def OnShowRangeDlg(self, evt):
        self.dlg_colorrange.Show()

    def OnShowColorDlg(self, evt):
        cd = wx.ColourData()
        c = (np.asarray(str2color(self.__line_data[self.selection[0]].color))*255).astype(int)
        cd.SetColour(wx.Colour(c))
        dlg  = wx.ColourDialog(self, cd)

        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            colormpl = np.around(np.asarray(color, dtype=float)/255, 2).tolist()
            self.spn_alpha.SetValue(round(colormpl[3],1))

            ld = self.__line_data
            for s in self.selection:
                setattr(ld[s], 'color', color2str(colormpl[:3]))
                setattr(ld[s], 'alpha', '{:.2f}'.format(colormpl[3]))
            self.bmp_linecolor.SetBitmap(self.gen_bitmap(color))
        pub.sendMessage((self.instid, 'lineattrs', 'changed'))

    def OnLineAttrChoice(self, evt):
        obj = evt.GetEventObject()
        item = obj.Name

        ld = self.__line_data
        for s in self.selection:
            ctrl = getattr(self,'cho_{}'.format(item))
            val = ctrl.GetString(ctrl.GetSelection())
            setattr(ld[s], item, val)
        pub.sendMessage((self.instid, 'lineattrs', 'changed'))

    def OnLineAttrText(self, evt):
        obj = evt.GetEventObject()
        item = obj.Name

        ld = self.__line_data
        for s in self.selection:
            setattr(ld[s], item, obj.Value)
        pub.sendMessage((self.instid, 'lineattrs', 'changed'))

    def OnProcess(self, evt):
        if len(self.__process_queue) > 0:
            self.__process_queue[0]()
            self.__process_queue.clear()

    def OnDeSelect(self, evt):
        self.selection.remove(evt.Index)
        self.__process_queue.append(self.enable)
        #pub.sendMessage((self.id, 'plotitem', 'selectionchanged'))

    def OnSelect(self, evt):
        self.selection.append(evt.Index)
        self.__process_queue.append(self.enable)
        #pub.sendMessage((self.id, 'plotitem', 'selectionchanged'))

    def enable(self):
        for c in self.__ctrls:
            if c.Name != 'ignore':
                wx.CallAfter(c.Enable, len(self.selection) > 0)

        self.silent = True
        if len(set([self.__line_data[q].label for q in self.selection])) == 1:
            self.txt_label.ChangeValue(self.__line_data[self.selection[0]].label)
        else:
            self.txt_label.ChangeValue('')

        if len(set([self.__line_data[q].linestyle for q in self.selection])) == 1:
            item = self.cho_linestyle.FindString(self.__line_data[self.selection[0]].linestyle)
            self.cho_linestyle.SetSelection(item)
        else:
            self.cho_linestyle.SetSelection(-1)

        if len(set([self.__line_data[q].color for q in self.selection])) == 1:
            color = str2color(self.__line_data[self.selection[0]].color)
            color = (np.asarray(color)*255).astype(int)
            self.bmp_linecolor.SetBitmap(self.gen_bitmap(color))
            self.Refresh()
        else:
            self.bmp_linecolor.SetBitmap(self.gen_bitmap(None))

        if len(set([self.__line_data[q].marker for q in self.selection])) == 1:
            item = self.cho_marker.FindString(self.__line_data[self.selection[0]].marker)
            self.cho_marker.SetSelection(item)
        else:
            self.cho_marker.SetSelection(-1)

        if len(set([self.__line_data[q].alpha for q in self.selection])) == 1:
            self.spn_alpha.SetValue(self.__line_data[self.selection[0]].alpha)
        else:
            self.spn_alpha.SetValue('')

        if len(set([self.__line_data[q].markersize for q in self.selection])) == 1:
            self.spn_markersize.SetValue(self.__line_data[self.selection[0]].markersize)
        else:
            self.spn_markersize.SetValue('')

        if len(set([self.__line_data[q].linewidth for q in self.selection])) == 1:
            self.spn_linewidth.SetValue(self.__line_data[self.selection[0]].linewidth)
        else:
            self.spn_linewidth.SetValue('')

        if len(set([self.__line_data[q].show for q in self.selection])) == 1:
            self.chk_show.SetValue(self.__line_data[self.selection[0]].show)
        else:
            self.chk_show.SetValue(False)

        self.silent = False

class BlitCanvas(wx.Window):
    def __init__(self, parent):
        self._bmp = wx.Bitmap(1,1)
        self.needs_update = False
        super(BlitCanvas, self).__init__(parent, style=wx.FULL_REPAINT_ON_RESIZE)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, evt):
        self.needs_update = False
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self._bmp, 0, 0)

class MPLFrame(wx.Frame):
    def __init__(self, parent, xpos=None):
        style =  wx.FRAME_FLOAT_ON_PARENT | wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER|wx.MAXIMIZE_BOX | wx.MAXIMIZE_BOX | wx.CLOSE_BOX)
        super(MPLFrame, self).__init__(parent, style= style, pos=_pos[1])
        if xpos is not None :
            self.SetPosition((xpos,-1))

        self.init_controls()
        self.layout()

    def init_controls(self):
        self.panel = wx.Panel(self)

        self.canvas = BlitCanvas(self.panel)
        self.btn_export_figure = wx.Button(self.panel, label='Export figure')
        self.btn_export_code = wx.Button(self.panel, label='Copy to clipboard')

    def layout(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.EXPAND)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(self.panel, size=(1,1)), 1)
        hbox.Add(self.btn_export_code, 0, wx.EXPAND|wx.ALL, 5)
        hbox.Add(self.btn_export_figure, 0, wx.EXPAND|wx.ALL, 5)
        vbox.Add(hbox, 0, wx.EXPAND)
        fbox = wx.BoxSizer(wx.HORIZONTAL)
        fbox.Add(self.panel, 1, wx.EXPAND)
        self.panel.SetSizer(vbox)
        self.panel.Layout()
        self.SetSizer(fbox)
        self.Fit()

class ControlFrame(WithMessage,wx.Frame):
    def __init__(self, parent):
        style = wx.DEFAULT_FRAME_STYLE
        if parent is not None:
            style |= wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, style=style, pos=_pos[0])
        WithMessage.__init__(self)

        self.setup_controls()
        self.set_tooltips()
        self.layout()

        self.SetTitle('Plot Editor')

        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)

        if _pos[0][0] == -1:
            x1,y1,x2,y2 = wx.Display().ClientArea
            w,h = self.GetSize()
            self.SetPosition((x1+10,y1+10))
            rborder = x1+20+w
        else:
            rborder = None

        dpi = wx.ScreenDC().GetPPI()
        self.figure = mpl.figure.Figure((1,1), dpi=dpi[0], facecolor='w')
        FigureCanvasAgg(self.figure)
        self.plot_view = MPLFrame(self, xpos=rborder)

        self.timer = wx.Timer(self)

    def redraw_later(self, *args):
        self._redraw = args
        self.timer.Start(200)

    def copy2clipboard(self):
        l,b,w,h = self.figure.bbox.bounds
        w, h = int(w), int(h)
        buf = self.figure.canvas.tostring_rgb()

        if wx.TheClipboard.Open():
            bmp = wx.Bitmap.FromBuffer(w, h, buf)
            wx.TheClipboard.SetData(wx.BitmapDataObject(bmp))
            wx.TheClipboard.Close()

    def update_from_model(self, mpmodel):
        if mpmodel is None:
            return

        self.txt_identifier.Value = mpmodel.identifier
        self.spn_bottom.Value = mpmodel.bottom
        self.spn_top.Value = mpmodel.top
        self.spn_left.Value = mpmodel.left
        self.spn_right.Value = mpmodel.right
        self.spn_hspace.Value = mpmodel.hspace
        self.spn_wspace.Value = mpmodel.wspace

        self.spn_width.Value = mpmodel.width
        self.spn_height.Value = mpmodel.height

        if mpmodel.selected is None:
            print('controlframe update_from_model no selection model.shape', mpmodel.shape)
            self.plot_layout.update_from_model(mpmodel)
            self.enable_edit(False)
            self.line_control.associate_model([], [])
            self.axes_control.associate_model([], box=[])

        else:
            self.enable_edit(True)
            print('controlframe update_from_model model.shape', mpmodel.shape)
            self.plot_layout.update_from_model(mpmodel)
            ds_names = ['s{:d} {}'.format(n, q.name) for n,q in enumerate(mpmodel.project[mpmodel.selected.plot_ref])]
            if mpmodel.selected.plot_ref_secondary is not None:
                ds_names.extend(['s{:d} {}'.format(n, q.name) for n,q in enumerate(mpmodel.project[mpmodel.selected.plot_ref_secondary])])
            self.line_control.associate_model(mpmodel.selected.line_data, ds_names)
            self.axes_control.associate_model(mpmodel.selected.axes_data,
                                              has_second=mpmodel.selected.plot_ref_secondary is not None, box=mpmodel.selected.box)

            self.chk_legend.Value = mpmodel.selected.legend_show
            self.spn_legend_fontsize.Value = mpmodel.selected.legend_fontsize
            self.spn_legend_position.Value = mpmodel.selected.legend_position

            self.spn_fontsize.Value = mpmodel.selected.fontsize
            self.chk_legend_frameon.Value = mpmodel.selected.legend_frameon

    def resize_canvas(self, w, h, dpi):
        self.figure.set_size_inches(w,h,True)
        self.plot_view.canvas.SetMinSize((dpi*w,dpi*h))
        self.plot_view.SetClientSize(self.plot_view.panel.GetBestSize())
        self.figure.canvas.draw()

    def init_pop(self, mpmodel):
        self.plot_layout.pop.update_from_model(mpmodel)
        # try:
        #     pd = mpmodel[self.plot_layout.selection]
        # except KeyError:
        #     sel = (-1, -1)
        #     self.enable_edit(False)
        # else:
        #     sel = (pd.plot_ref, pd.plot_ref_secondary)
        #     self.enable_edit(True)

        names = [p.name if p.name != '' else 'p{}'.format(n) for n,p in enumerate(mpmodel.project)]
        self.plot_layout.set_plot_choices(['<none>']+names,
                                          [-1]+[p.uuid for p in mpmodel.project])

    def Show(self, state):
        super(ControlFrame, self).Show(state)
        self.plot_view.Show(state)

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def setup_controls(self):
        self.panel = wx.Panel(self)
        self.pan_nb = wx.Panel(self.panel)
        self.nb = wx.Notebook(self.pan_nb)

        self.plot_layout = PlotLayout(self.panel)

        self.panel_basic = wx.Panel(self.nb)
        self.line_control = LineControlPanel(self.nb)
        self.axes_control = AxesControlPanel(self.nb)

        self.nb.AddPage(self.panel_basic, 'Basic')
        self.nb.AddPage(self.line_control, 'Styles')
        self.nb.AddPage(self.axes_control, 'Axis')

        self.txt_identifier = wx.TextCtrl(self.panel)

        self.txt_title = wx.TextCtrl(self.panel_basic, value='title', style=wx.TE_PROCESS_ENTER, name='plotlabel')

        self.chk_legend = wx.CheckBox(self.panel_basic)
        self.spn_legend_fontsize = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=4, max=30, initial=12, value='12', style=wx.TE_PROCESS_ENTER)
        self.spn_legend_position = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=0, max=10, initial=0, value='0', style=wx.TE_PROCESS_ENTER)
        self.chk_legend_frameon = wx.CheckBox(self.panel_basic, label='')
        self.chk_legend_frameon.SetValue(True)

        self.spn_fontsize = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=0, max=20, initial=10, value='10', style=wx.TE_PROCESS_ENTER)

        self.spn_bottom = wx.SpinCtrlDouble(self.panel, size=(80,-1), min=0, max=0.4, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='bottom')
        self.spn_top = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.6, max=1.0, inc=0.05, value='0.9', style=wx.TE_PROCESS_ENTER, name='top')
        self.spn_left = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0, max=0.4, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='left')
        self.spn_right = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.6, max=1.0, inc=0.05, value='0.9', style=wx.TE_PROCESS_ENTER, name='right')
        self.spn_hspace = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.0, max=1.0, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='hspace')
        self.spn_wspace = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.0, max=1.0, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='wspace')

        self.spn_width = wx.SpinCtrlDouble(self.panel, size=(100,-1), min=1, max=10, inc=1, value='5', style=wx.TE_PROCESS_ENTER, name='width')
        self.spn_height = wx.SpinCtrlDouble(self.panel, size=(100,-1), min=1, max=10, inc=1, value='4', style=wx.TE_PROCESS_ENTER, name='height')

        self.btn_ok = wx.Button(self.panel, label='Save and close')
        self.btn_cancel = wx.Button(self. panel, label='Discard')

    def set_tooltips(self):
        self.txt_identifier.SetToolTip('Choose a name for the figure object')

        self.spn_legend_position.SetToolTip('0 = auto position, 1-10: try it out')
        self.spn_legend_fontsize.SetToolTip('Font size in points')
        self.chk_legend.SetToolTip('Check to show a legend')
        self.chk_legend_frameon.SetToolTip('Uncheck to hide the frame around the legend box')

        self.spn_bottom.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_top.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_left.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_right.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')

    def enable_edit(self, state=True):
        def enable(obj, state=True):
            obj.Enable(state)
            for c in obj.GetChildren():
                enable(c, state)
        enable(self.pan_nb, state)

    def layout(self):
        # panel_basic
        vbox = wx.BoxSizer(wx.VERTICAL)
        bx = wx.StaticBox(self.panel_basic, label='Labels')
        hbox = wx.StaticBoxSizer(bx, wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_basic, label='Title'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.txt_title, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 20)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        bx = wx.StaticBox(self.panel_basic, label='Legend')
        hbox = wx.StaticBoxSizer(bx, wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_basic, label='Show legend'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.chk_legend, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        hbox.Add(wx.StaticText(self.panel_basic, label='Font size'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_legend_fontsize, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        hbox.Add(wx.StaticText(self.panel_basic, label='Position'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_legend_position, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        hbox.Add(wx.StaticText(self.panel_basic, label='Show frame'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.chk_legend_frameon, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        bx = wx.StaticBox(self.panel_basic, label='Text')
        hbox = wx.StaticBoxSizer(bx, wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_basic, label='Font size'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_fontsize, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        self.panel_basic.SetSizer(vbox)
        vbox.SetSizeHints(self.panel_basic)

        #main panel
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.plot_layout, 0, wx.EXPAND|wx.ALL, 2)
        vbox.Add(self.pan_nb, 1, wx.EXPAND|wx.ALL, 2)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.nb, 1, wx.EXPAND)
        self.pan_nb.SetSizer(box)

        bx = wx.StaticBox(self.panel, label='Plot margins')
        hbox = wx.StaticBoxSizer(bx, wx.HORIZONTAL)
        ivbox = wx.BoxSizer(wx.VERTICAL)
        ihbox = wx.BoxSizer(wx.HORIZONTAL)
        ihbox.Add(wx.StaticText(self.panel, label='Bottom'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_bottom, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        ihbox.Add(wx.StaticText(self.panel, label='Top'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_top, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        ihbox.Add(wx.StaticText(self.panel, label='Left'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_left, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        ihbox.Add(wx.StaticText(self.panel, label='Right'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_right, 1, wx.ALIGN_CENTER_VERTICAL)
        ivbox.Add(ihbox, 0, wx.EXPAND)
        ihbox = wx.BoxSizer(wx.HORIZONTAL)
        ihbox.Add(wx.StaticText(self.panel, label='Vertical space'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_hspace, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        ihbox.Add(wx.StaticText(self.panel, label='Horizontal space'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)
        ihbox.Add(self.spn_wspace, 1, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        ivbox.Add(ihbox, 0, wx.TOP, 5)
        hbox.Add(ivbox, 1, wx.EXPAND)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel, label='Width'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_width, 0, wx.EXPAND|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        hbox.Add(wx.StaticText(self.panel, label='Height'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_height, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        hbox.Add(wx.Window(self.panel, size=(1,1)), 1)
        hbox.Add(wx.StaticText(self.panel, label='Identifier'),0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        hbox.Add(self.txt_identifier, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,10)
        hbox.Add(self.btn_ok, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT,5)
        hbox.Add(self.btn_cancel, 0, wx.ALIGN_CENTER_VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        self.panel.SetSizer(vbox)
        vbox.SetSizeHints(self.panel)
        #self.Layout()
        self.Fit()

    def warn_not_unique_plot_names(self):
        wx.MessageBox('Only plots with unique names are accessible here.\nClose the window, change the plot names and come back.')

    def show_model_changed(self):
        wx.MessageBox('The plot object referenced by this figure has changed.\n'+\
                      'The figure might not look like what you would expect.','Warning')

    def save_pos(self):
        global _pos
        _pos[0] = self.GetPosition()
        _pos[1] = self.plot_view.GetPosition()

class CodeEditor(PythonSTC):
    def __init__(self, parent, style=wx.BORDER_NONE):
        PythonSTC.__init__(self, parent, -1, style=style)

    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        #if wx.USE_UNICODE:
        #    value = value.decode('iso8859_1')
        val = self.GetReadOnly()
        self.SetReadOnly(False)
        self.SetText(value)
        self.EmptyUndoBuffer()
        self.SetSavePoint()
        self.SetReadOnly(val)

    def SetEditable(self, val):
        self.SetReadOnly(not val)

    def IsModified(self):
        return self.GetModify()

    def Clear(self):
        self.ClearAll()

    def SetInsertionPoint(self, pos):
        self.SetCurrentPos(pos)
        self.SetAnchor(pos)

    def ShowPosition(self, pos):
        line = self.LineFromPosition(pos)
        #self.EnsureVisible(line)
        self.GotoLine(line)

    def GetLastPosition(self):
        return self.GetLength()

    def GetPositionFromLine(self, line):
        return self.PositionFromLine(line)

    def GetRange(self, start, end):
        return self.GetTextRange(start, end)

    def GetSelection(self):
        return self.GetAnchor(), self.GetCurrentPos()

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)

    def SelectLine(self, line):
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        self.SetSelection(start, end)

    def RegisterModifiedEvent(self, eventHandler):
        self.Bind(wx.stc.EVT_STC_CHANGE, eventHandler)

from PIL import Image

def imagetopil(image):
    """Convert wx.Image to PIL Image."""
    w, h = image.GetSize()
    data = image.GetData()

    redImage = Image.new("L", (w, h))
    redImage.fromstring(data[0::3])
    greenImage = Image.new("L", (w, h))
    greenImage.fromstring(data[1::3])
    blueImage = Image.new("L", (w, h))
    blueImage.fromstring(data[2::3])

    if image.HasAlpha():
        alphaImage = Image.new("L", (w, h))
        alphaImage.fromstring(image.GetAlphaData())
        pil = Image.merge('RGBA', (redImage, greenImage, blueImage, alphaImage))
    else:
        pil = Image.merge('RGB', (redImage, greenImage, blueImage))
    return pil

