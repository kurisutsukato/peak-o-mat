__author__ = 'ck'

import wx
import wx.dataview as dv
import wx.stc as stc
import matplotlib as mpl
mpl.use('Agg')

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
from matplotlib.patches import Rectangle
from matplotlib.axes import Axes
from matplotlib.axis import Axis, XAxis

from .. import images
from ..controls import PythonSTC, FormatValidator

from .plotlayout import PlotLayout

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

class CHRenderer(dv.DataViewChoiceRenderer):
    def ActivateCell(self, *args, **kwargs):
        print('activate cell', args, kwargs)
        super(CHRenderer, self).ActivateCell(*args, **kwargs)

class LineControlPanel(wx.Panel):
    def __init__(self, parent, data=[]):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.dvc = dv.DataViewCtrl(self,
                                   style=wx.BORDER_THEME
                                   #| dv.DV_ROW_LINES # nice alternating bg colors
                                   | dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )
        renderer = dv.DataViewChoiceRenderer(choices=('','-','--','-.',':'))
        c0 = dv.DataViewColumn("Linestyle",
                               renderer,
                               0,
                               width=80)
        self.dvc.AppendColumn(c0)

        renderer = dv.DataViewChoiceRenderer(choices=('','.',',','o','v','^','<','>','1','2','3','4','8','s','p','*','h','H','+','x','D','d','|','_'))
        c0 = dv.DataViewColumn("Markerstyle",
                               renderer,
                               1,
                               width=80)
        self.dvc.AppendColumn(c0)

        c2 = self.dvc.AppendTextColumn("Linewidth",   2, width=50, mode=dv.DATAVIEW_CELL_EDITABLE)
        c2 = self.dvc.AppendTextColumn("Markersize",   3, width=50, mode=dv.DATAVIEW_CELL_EDITABLE)
        c3 = self.dvc.AppendTextColumn("Color",    4, width=70, mode=dv.DATAVIEW_CELL_EDITABLE)
        c4 = self.dvc.AppendTextColumn('Alpha', 5, width=50, mode=dv.DATAVIEW_CELL_EDITABLE)
        c5 = self.dvc.AppendTextColumn('Label',   6, width=140, mode=dv.DATAVIEW_CELL_EDITABLE)
        c6 = self.dvc.AppendToggleColumn('Legend',   7, width=80, mode=dv.DATAVIEW_CELL_ACTIVATABLE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.dvc, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.dvc.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnActivate)
        self.dvc.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEndEdit)

    def OnEndEdit(self, evt):
        print('endedit')

    def OnActivate(self, evt):
        self.dvc.EditItem(evt.GetItem(), self.dvc.GetColumn(evt.GetColumn()))

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
    def __init__(self, parent, figure, xpos=None):
        style =  wx.FRAME_FLOAT_ON_PARENT | wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER|wx.MAXIMIZE_BOX | wx.MAXIMIZE_BOX | wx.CLOSE_BOX)
        super(MPLFrame, self).__init__(parent, style= style, pos=_pos[1])
        if xpos is not None :
            self.SetPosition((xpos,-1))

        self.init_controls(figure)
        self.layout()

    def init_controls(self, figure):
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

class ControlFrame(wx.Frame):
    def __init__(self, parent):
        style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT
        super(ControlFrame, self).__init__(parent, style=style, pos=_pos[0])

        self.id = parent.id

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
        FigureCanvas(self.figure)
        self.plot_view = MPLFrame(self, self.figure, xpos=rborder)

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

    def associate_model(self, line_data):
        self.line_control.dvc.AssociateModel(line_data)

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
            self.enable_edit(False)
        else:
            self.enable_edit(True)

            self.plot_layout.update_from_model(mpmodel)
            self.associate_model(mpmodel.selected.line_data)

            self.txt_xlabel.Value = mpmodel.selected.label_x
            self.txt_ylabel.Value = mpmodel.selected.label_y
            self.txt_title.Value = mpmodel.selected.label_title

            self.txt_xrng_min.Value = mpmodel.selected.min_x
            self.txt_yrng_min.Value = mpmodel.selected.min_y
            self.txt_xrng_max.Value = mpmodel.selected.max_x
            self.txt_yrng_max.Value = mpmodel.selected.max_y

            self.chk_xticks_hide.Value = mpmodel.selected.xticks_hide
            self.chk_yticks_hide.Value = mpmodel.selected.yticks_hide

            self.cho_xlabel_pos.Selection = self.cho_xlabel_pos.FindString(mpmodel.selected.tlabel_pos_x)
            self.cho_ylabel_pos.Selection = self.cho_ylabel_pos.FindString(mpmodel.selected.tlabel_pos_y)

            self.cho_xtickdir.Selection = self.cho_xtickdir.FindString(mpmodel.selected.tdir_x)
            self.cho_ytickdir.Selection = self.cho_ytickdir.FindString(mpmodel.selected.tdir_y)

            self.chk_legend.Value = mpmodel.selected.legend_show
            self.spn_legend_fontsize.Value = mpmodel.selected.legend_fontsize
            self.spn_legend_position.Value = mpmodel.selected.legend_position

            self.spn_fontsize.Value = mpmodel.selected.fontsize

            self.cmb_scalex.Selection = int(mpmodel.selected.xscale)
            self.cmb_scaley.Selection = int(mpmodel.selected.yscale)

            self.txt_symlogthreshx.Value = str(mpmodel.selected.symlogthreshx)
            self.txt_symlogthreshy.Value = str(mpmodel.selected.symlogthreshy)

            self.txt_symlogthreshx.Enable(self.cmb_scalex.Selection == 2)
            self.txt_symlogthreshy.Enable(self.cmb_scaley.Selection == 2)

            self.editor.SetValue(mpmodel.selected.code)

    def resize_canvas(self, w, h, dpi):
        self.figure.set_size_inches(w,h,True)
        self.plot_view.canvas.SetMinSize((dpi*w,dpi*h))
        self.plot_view.SetClientSize(self.plot_view.panel.GetBestSize())
        self.figure.canvas.draw()

    def init_pop(self, mpmodel):
        self.plot_layout.pop.update_from_model(mpmodel)
        try:
            sel = mpmodel[self.plot_layout.selection].uuid
            self.enable_edit(True)
        except KeyError:
            sel = ''
            self.enable_edit(False)

        names = [p.name if p.name != '' else 'p{}'.format(n) for n,p in enumerate(mpmodel.project)]
        self.plot_layout.set_plot_choices(['<none>']+names,
                                          [-1]+[p.uuid for p in mpmodel.project],
                                          sel)

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
        self.panel_axis = wx.Panel(self.nb)
        self.panel_axis.InitDialog()
        self.panel_code = wx.Panel(self.nb)

        self.nb.AddPage(self.panel_basic, 'Basic')
        self.nb.AddPage(self.line_control, 'Styles')
        self.nb.AddPage(self.panel_axis, 'Axis')
        self.nb.AddPage(self.panel_code, 'Code')

        self.txt_identifier = wx.TextCtrl(self.panel)

        self.editor = CodeEditor(self.panel_code)
        self.btn_runcode = wx.Button(self.panel_code, label='Run code')
        #self.btn_example = wx.Button(self.panel_code, label='Show me some example')
        self.txt_result = wx.TextCtrl(self.panel_code, style=wx.TE_MULTILINE)

        self.txt_title = wx.TextCtrl(self.panel_basic, value='title', style=wx.TE_PROCESS_ENTER, name='plotlabel')

        self.chk_legend = wx.CheckBox(self.panel_basic)
        self.spn_legend_fontsize = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=4, max=30, initial=12, value='12', style=wx.TE_PROCESS_ENTER)
        self.spn_legend_position = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=0, max=10, initial=0, value='0', style=wx.TE_PROCESS_ENTER)

        self.spn_fontsize = wx.SpinCtrl(self.panel_basic, size=(80,-1), min=0, max=20, initial=10, value='10', style=wx.TE_PROCESS_ENTER)

        # axis
        self.txt_xlabel = wx.TextCtrl(self.panel_axis, value='x label', style=wx.TE_PROCESS_ENTER)
        self.cmb_scalex = wx.Choice(self.panel_axis, choices=('Linear','Log10', 'SymLog10'), name='scalex')
        self.txt_symlogthreshx = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_symlogthreshx.SetValidator(FormatValidator(validfloat))
        self.txt_xrng_min = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_xrng_max = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_xrng_min.SetValidator(FormatValidator(validfloat))
        self.txt_xrng_max.SetValidator(FormatValidator(validfloat))
        #self.cho_xticks_prec = wx.Choice(self.panel_axis, choices=['Default','0','1','2','3','4'])
        self.chk_xticks_hide = wx.CheckBox(self.panel_axis, -1, 'Hide ticks')
        #self.chk_xtick_custom = wx.CheckBox(self.panel_axis, -1, 'Custom ticks')
        #self.txt_xtick_major = wx.TextCtrl(self.panel_axis, style=wx.TE_PROCESS_ENTER)
        #self.txt_xtick_minor = wx.TextCtrl(self.panel_axis, style=wx.TE_PROCESS_ENTER)
        #self.txt_xtick_major.SetValidator(FormatValidator(validticks))
        #self.txt_xtick_minor.SetValidator(FormatValidator(validticks))

        self.cho_xlabel_pos = wx.Choice(self.panel_axis, choices=['bottom','top'])
        self.cho_xlabel_pos.SetSelection(0)

        self.cho_xtickdir = wx.Choice(self.panel_axis, choices=['in','out'])
        self.cho_xtickdir.SetSelection(0)

        self.txt_ylabel = wx.TextCtrl(self.panel_axis, value='y label', style=wx.TE_PROCESS_ENTER)
        self.cmb_scaley = wx.Choice(self.panel_axis, choices=('Linear','Log10', 'SymLog10'), name='scaley')

        self.txt_symlogthreshy = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_symlogthreshy.SetValidator(FormatValidator(validfloat))

        self.txt_yrng_min = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_yrng_max = wx.TextCtrl(self.panel_axis, value='', style=wx.TE_PROCESS_ENTER)
        self.txt_yrng_min.SetValidator(FormatValidator(validfloat))
        self.txt_yrng_max.SetValidator(FormatValidator(validfloat))

        #self.cho_yticks_prec = wx.Choice(self.panel_axis, choices=['Default','0','1','2','3','4'])
        self.chk_yticks_hide = wx.CheckBox(self.panel_axis, -1, 'Hide ticks')

        #self.chk_ytick_custom = wx.CheckBox(self.panel_axis, -1, 'Custom ticks')

        #self.txt_ytick_major = wx.TextCtrl(self.panel_axis, style=wx.TE_PROCESS_ENTER)
        #self.txt_ytick_minor = wx.TextCtrl(self.panel_axis, style=wx.TE_PROCESS_ENTER)
        #self.txt_ytick_major.SetValidator(FormatValidator(validticks))
        #self.txt_ytick_minor.SetValidator(FormatValidator(validticks))

        self.cho_ylabel_pos = wx.Choice(self.panel_axis, choices=['left','right'])
        self.cho_ylabel_pos.SetSelection(0)

        self.cho_ytickdir = wx.Choice(self.panel_axis, choices=['in','out'])
        self.cho_ytickdir.SetSelection(0)

        self.spn_bottom = wx.SpinCtrlDouble(self.panel, size=(80,-1), min=0, max=0.4, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='bottom')
        self.spn_top = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.6, max=1.0, inc=0.05, value='0.9', style=wx.TE_PROCESS_ENTER, name='top')
        self.spn_left = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0, max=0.4, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='left')
        self.spn_right = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.6, max=1.0, inc=0.05, value='0.9', style=wx.TE_PROCESS_ENTER, name='right')
        self.spn_hspace = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.0, max=1.0, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='hspace')
        self.spn_wspace = wx.SpinCtrlDouble(self.panel, size=(80,-1),min=0.0, max=1.0, inc=0.05, value='0.1', style=wx.TE_PROCESS_ENTER, name='wspace')

        self.spn_width = wx.SpinCtrlDouble(self.panel, size=(60,-1), min=1, max=10, inc=1, value='5', style=wx.TE_PROCESS_ENTER, name='width')
        self.spn_height = wx.SpinCtrlDouble(self.panel, size=(60,-1), min=1, max=10, inc=1, value='4', style=wx.TE_PROCESS_ENTER, name='height')

        self.btn_ok = wx.Button(self.panel, label='Save and close')
        self.btn_cancel = wx.Button(self. panel, label='Discard')

    def set_tooltips(self):
        self.txt_identifier.SetToolTip('Choose a name for the figure object')

        self.spn_legend_position.SetToolTip('0 = auto position, 1-10: try it out')
        self.spn_legend_fontsize.SetToolTip('Font size in points')
        self.chk_legend.SetToolTip('Check to show a legend')

        self.spn_bottom.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_top.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_left.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')
        self.spn_right.SetToolTip('The plot margins are specified as fraction of the total plot size. Valid values are in the range between 0 and 1')

        self.editor.SetToolTip('Python code.')

        #self.btn_example.SetToolTip('Click to fill the window above with some example code')

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
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        bx = wx.StaticBox(self.panel_basic, label='Text')
        hbox = wx.StaticBoxSizer(bx, wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_basic, label='Font size'), 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.spn_fontsize, 0, wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 20)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 5)

        self.panel_basic.SetSizer(vbox)
        vbox.SetSizeHints(self.panel_basic)

        #axis
        ovbox = wx.BoxSizer(wx.VERTICAL)

        # x
        bx = wx.StaticBox(self.panel_axis, label='X Axis')
        vbox = wx.StaticBoxSizer(bx, wx.VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_axis, label='Label'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        hbox.Add(self.txt_xlabel, 1, wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 10)
        hbox.Add(wx.StaticText(self.panel_axis, label='Position'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        hbox.Add(self.cho_xlabel_pos, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)

        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_axis, label='Scale'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(self.cmb_scalex, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.lab_symlogthreshx = wx.StaticText(self.panel_axis, label='Symlog thresh.')
        hbox.Add(self.lab_symlogthreshx, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.txt_symlogthreshx, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='Range min.'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.txt_xrng_min, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='max.'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(self.txt_xrng_max, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        #hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(self.chk_xtick_custom, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        #hbox.Add(wx.StaticText(self.panel_axis, label='Major'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,25)
        #hbox.Add(self.txt_xtick_major, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #hbox.Add(wx.StaticText(self.panel_axis, label='Minor'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,15)
        #hbox.Add(self.txt_xtick_minor, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(wx.StaticText(self.panel_axis, -1, 'Ticklabel precision'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #hbox.Add(self.cho_xticks_prec, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.chk_xticks_hide, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='Tick direction'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,10)
        hbox.Add(self.cho_xtickdir, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        ovbox.Add(vbox, 0, wx.EXPAND)

        # y
        bx = wx.StaticBox(self.panel_axis, label='Y Axis')
        vbox = wx.StaticBoxSizer(bx, wx.VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_axis, label='Label'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        hbox.Add(self.txt_ylabel, 1, wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 10)
        hbox.Add(wx.StaticText(self.panel_axis, label='Label position'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        hbox.Add(self.cho_ylabel_pos, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.StaticText(self.panel_axis, label='Scale'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(self.cmb_scaley, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        self.lab_symlogthreshy = wx.StaticText(self.panel_axis, label='Symlog thresh.')
        hbox.Add(self.lab_symlogthreshy, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.txt_symlogthreshy, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='Range min.'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.txt_yrng_min, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='max.'), 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(self.txt_yrng_max, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        #hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(self.chk_ytick_custom, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        #hbox.Add(wx.StaticText(self.panel_axis, label='Major'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,25)
        #hbox.Add(self.txt_ytick_major, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #hbox.Add(wx.StaticText(self.panel_axis, label='Minor'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,15)
        #hbox.Add(self.txt_ytick_minor, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(wx.StaticText(self.panel_axis, -1, 'Ticklabel precision'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,5)
        #hbox.Add(self.cho_yticks_prec, 0, wx.RIGHT|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 10)
        hbox.Add(self.chk_yticks_hide, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        hbox.Add(wx.StaticText(self.panel_axis, label='Tick direction'),0,wx.LEFT|wx.ALIGN_CENTER_VERTICAL,25)
        hbox.Add(self.cho_ytickdir, 0, wx.EXPAND|wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(hbox, 0, wx.EXPAND|wx.BOTTOM, 5)

        ovbox.Add(vbox, 0, wx.EXPAND)

        self.panel_axis.SetSizer(ovbox)
        ovbox.SetSizeHints(self.panel_axis)

        # panel code
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.editor, 1, wx.EXPAND|wx.ALL, 2)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        #hbox.Add(self.btn_example, 0)
        hbox.Add(wx.Window(self.panel_code, size=(1,1)), 1)
        hbox.Add(self.btn_runcode, 0)

        vbox.Add(hbox, 0, wx.EXPAND|wx.RIGHT|wx.LEFT|wx.BOTTOM, 2)
        vbox.Add(self.txt_result, 1, wx.EXPAND|wx.RIGHT|wx.LEFT|wx.BOTTOM, 2)

        self.panel_code.SetSizer(vbox)
        vbox.SetSizeHints(self.panel_code)

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

import io
import ctypes

