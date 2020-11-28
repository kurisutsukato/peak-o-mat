import wx
from pubsub import pub
import wx.aui as aui

import numpy as np
from wx.lib.scrolledpanel import ScrolledPanel

import string

from peak_o_mat import module, controls, spec, misc_ui

from peak_o_mat.symbols import pom_globals


class Panel(ScrolledPanel):
    def __init__(self, parent):
        super(Panel, self).__init__(parent)
        self.setup_controls()
        self.layout()

        self.SetupScrolling(scrollToTop=False, scrollIntoView=False)

    def setup_controls(self):
        self.book = wx.Choicebook(self)
        self.btn_apply = wx.Button(self, label='Apply')

    def layout(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        outer.Add(self.book, 1, wx.EXPAND|wx.ALL, 5)
        line = wx.BoxSizer(wx.HORIZONTAL)
        line.Add(wx.Window(self), 1)
        line.Add(self.btn_apply, 0)
        outer.Add(wx.StaticLine(self, style=wx.HORIZONTAL), 0, wx.EXPAND|wx.ALL, 2)
        outer.Add(line, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(outer)
        self.Fit()

    def message(self, msg, target=1, blink=False):
        event = misc_ui.ShoutEvent(-1, msg=msg, target=target, blink=blink)
        wx.PostEvent(self, event)

class Interactor:
    def install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.Bind(wx.EVT_IDLE, self.OnIdle)
        self.view.Bind(wx.EVT_BUTTON, self.OnApply)
        pub.subscribe(self.selection_changed, (self.controller.instid, 'selection','changed'))

    def OnIdle(self, evt):
        name = self.view.book.GetPageText(self.view.book.GetSelection())
        sel = self.controller.selection
        if sel is not None:
            pl, ds = sel
            state = self.controller.submodules[name].valid and len(ds) > 0
            self.view.btn_apply.Enable(state)
        else:
            self.view.btn_apply.Disable()

    def OnApply(self, evt):
        name = self.view.book.GetPageText(self.view.book.GetSelection())
        self.controller.process(name)

    def selection_changed(self, plot, dataset):
        print('modop selection changed, visible: {}'.format(self.controller.visible))

class Module(module.BaseModule):
    title = 'Toolbox'
    _busy = False
    need_attention = True

    def __init__(self, *args):
        module.BaseModule.__init__(self, *args)
        self.init()

        self.parent_view._mgr.AddPane(self.view, aui.AuiPaneInfo().
                                      Float().Dockable(True).Hide().
                                      Caption(self.title).Name(self.title))
        self.parent_view._mgr.Update()
        self.parent_controller.view.menu_factory.add_module(self.parent_controller.view.menubar, self.title)
        #menu.add_module(self.parent_controller.view.menubar, self.title)

        pub.subscribe(self.OnSelectionChanged, (self.instid, 'selection','changed'))

    @property
    def selection(self):
        return self.parent_controller.selection

    def init(self):
        self.view = Panel(self.parent_view)
        super(Module, self).init()

        Interactor().install(self, self.view)
        self.submodules = {0: SG, 1: MAVG, 2: ACORR, 3: FFT, 4: SPLINE}

        for n in list(self.submodules.keys()):
            cls = self.submodules.pop(n)
            self.submodules[cls.name] = cls(self.view.book)

        #self.calib = Calibration()
        #self.xmlres.AttachUnknownControl('xrc_grid', CalibGrid(self.panel, self.calib))
        #self.grid.GetParent().SetMinSize(self.grid.GetMinSize())
        #self.grid.GetParent().Refresh()
        #self.panel.Layout()

        #self.view.txt_op.Bind(wx.EVT_TEXT_ENTER, self.OnTrafo)
        #self.view.btn_repeat.Bind(wx.EVT_BUTTON, self.OnRepeat)

    def process(self, name):
        sel = self.selection
        if sel is not None:
            plot, ds = sel
            for s in ds:
                res = self.submodules[name].process(self.project[plot][s])
                if type(res) != tuple:
                    res = [res]
                for sp in res:
                    self.parent_controller.add_set(sp)

    def selection_changed(self):
        print('selection changed: {}'.format(self.selection))

class SubModule:
    def __init__(self, view):
        self.valid = True
        self.parent_view = view
        self.view = wx.Panel(view)
        self.init_gui()
        view.AddPage(self.view, self.name)

    def init_gui(self):
        pass

    def layout(self):
        pv = self.view.GetParent().GetParent()
        pv.GetSizer().FitInside(pv)
        self.view.Layout()

    def process(self, spec):
        print('process -- override')
        pass

from peak_o_mat import filters

class SG(SubModule):
    name = 'Savitzky Golay'

    def init_gui(self):
        self.txt_length = wx.TextCtrl(self.view, value='9', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.DIGIT_ONLY))
        self.ch_order = wx.SpinCtrl(self.view, min=1, max=20, initial=5, size=(50,-1), style=wx.TE_PROCESS_ENTER)
        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')

        box = wx.GridBagSizer(vgap=5, hgap=5)
        box.SetFlexibleDirection(wx.HORIZONTAL)

        box.Add(self.lab_error, (0,0), span=(1,2))
        box.Add(wx.StaticText(self.view, label='Length (impair)'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_length, (1,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.Add(wx.StaticText(self.view, label='Order (< length)'), (2,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.ch_order, (2,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        self.view.SetSizer(box)
        self.view.Fit()

        self.view.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        length = self.txt_length.Value
        if length.strip() == '':
            self.valid = False
            return

        if int(length)%2 == 0:
            self.lab_error.SetLabel('Length must be impair')
            self.valid = False
            return
        else:
            self.valid = True
            self.lab_error.SetLabel('')

        if int(self.ch_order.Value) >= int(length):
            self.valid = False
            self.lab_error.SetLabel('order must be less than length')

    def process(self, sp):
        wl = int(self.txt_length.Value)
        order = int(self.ch_order.Value)
        return filters.sg_filter(sp, wl, order)

class MAVG(SubModule):
    name = 'Moving average'

    def init_gui(self):
        self.txt_length = wx.TextCtrl(self.view, value='5', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.DIGIT_ONLY))
        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')

        box = wx.GridBagSizer(vgap=5, hgap=5)
        box.SetFlexibleDirection(wx.HORIZONTAL)

        box.Add(self.lab_error, (0,0), span=(1,2))
        box.Add(wx.StaticText(self.view, label='Window length (pts)'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_length, (1,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        self.view.SetSizer(box)
        self.view.Fit()

        self.view.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        if self.txt_length.Value.strip() == '':
            self.lab_error.SetLabel('window length must be > 1')
            self.valid = False
        else:
            if int(self.txt_length.Value) < 2:
                self.lab_error.SetLabel('window length must be > 1')
                self.valid = False
            else:
                self.lab_error.SetLabel('')
                self.valid = True

    def process(self, sp):
        avg = int(self.txt_length.Value)
        return filters.mavg_filter(sp, avg)

class WMAVG(SubModule):
    name = 'Weighted moving average'

    def init_gui(self):
        self.txt_step = wx.TextCtrl(self.view, value='0.05', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.FLOAT_ONLY))
        self.txt_width = wx.TextCtrl(self.view, value='1.0', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.FLOAT_ONLY))
        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')

        box = wx.GridBagSizer(vgap=5, hgap=5)
        box.SetFlexibleDirection(wx.HORIZONTAL)

        box.Add(self.lab_error, (0,0), span=(1,2))
        box.Add(wx.StaticText(self.view, label='Step size'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_step, (1,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.Add(wx.StaticText(self.view, label='Width'), (2,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_width, (2,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        self.view.SetSizer(box)
        self.view.Fit()

        self.view.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        if self.txt_step.Value.strip() == '':
            self.lab_error.SetLabel('Step size must be positive')
            self.valid = False
        else:
            try:
                if float(self.txt_step.Value) <= 0.0:
                    self.lab_error.SetLabel('Step size must be positive')
                    self.valid = False
                else:
                    self.lab_error.SetLabel('')
                    self.valid = True
            except ValueError:
                self.valid = False
                self.lab_error.SetLabel('Incorrect input')

        if self.txt_width.Value.strip() == '':
            self.lab_error.SetLabel('Width must be positive')
            self.valid = False
        else:
            try:
                if float(self.txt_width.Value) <= 0.0:
                    self.lab_error.SetLabel('Width must be positive')
                    self.valid = False
                else:
                    self.lab_error.SetLabel('')
                    self.valid = True
            except ValueError:
                self.valid = False
                self.lab_error.SetLabel('Incorrect input')

    def process(self, sp):
        step = float(self.txt_step.Value)
        width = float(self.txt_width.Value)
        return filters.wmavg_filter(sp, step, width)

class EMAVG(SubModule):
    name = 'Exp. moving average'

    def init_gui(self):
        self.txt_length = wx.TextCtrl(self.view, value='5', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.DIGIT_ONLY))
        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')

        box = wx.GridBagSizer(vgap=5, hgap=5)
        box.SetFlexibleDirection(wx.HORIZONTAL)

        box.Add(self.lab_error, (0,0), span=(1,2))
        box.Add(wx.StaticText(self.view, label='Window length (pts)'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_length, (1,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        self.view.SetSizer(box)
        self.view.Fit()

        self.view.Bind(wx.EVT_TEXT, self.OnText)

    def OnText(self, evt):
        if self.txt_length.Value.strip() == '':
            self.lab_error.SetLabel('Window length must be > 1')
            self.valid = False
        else:
            if int(self.txt_length.Value) < 2:
                self.lab_error.SetLabel('Window length must be > 1')
                self.valid = False
            else:
                self.lab_error.SetLabel('')
                self.valid = True

    def process(self, sp):
        avg = int(self.txt_length.Value)
        return filters.emavg_filter(sp, avg)

class ACORR(SubModule):
    name = 'Autocorrelation'

    def init_gui(self):
        return

    def process(self, sp):
        return filters.autocorrelation_filter(sp)

class FFT(SubModule):
    name = 'Real FFT'

    def init_gui(self):
        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')


        self.ch_output = wx.Choice(self.view, choices=['Real+Imag','Amp+Phase'])
        self.txt_threshold = wx.TextCtrl(self.view, value='0.01', style=wx.TE_PROCESS_ENTER,
                                         validator=controls.InputValidator(flag=controls.FLOAT_ONLY))
        self.txt_threshold.Hide()
        self.lab_threshold = wx.StaticText(self.view, label='Noise threshold (rel.)')
        self.lab_threshold.Hide()

        box = wx.GridBagSizer(vgap=5, hgap=5)
        box.SetFlexibleDirection(wx.HORIZONTAL)
        box.Add(self.lab_error, (0,0), span=(1,2))

        box.Add(wx.StaticText(self.view, label='Output'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.ch_output, (1,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.lab_threshold, (2,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_threshold, (2,1), flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        self.view.SetSizer(box)
        self.view.Fit()
        self.view.Bind(wx.EVT_TEXT, self.OnText)
        self.view.Bind(wx.EVT_CHOICE, self.OnChoice)

    def OnChoice(self, evt):
        self.txt_threshold.Show(evt.GetEventObject().GetSelection())
        self.lab_threshold.Show(evt.GetEventObject().GetSelection())
        self.view.Layout()

    def OnText(self, evt):
        try:
            float(self.txt_threshold.Value)
        except ValueError:
            self.lab_error.SetLabel('Invalid input')
        else:
            self.lab_error.SetLabel('')

    def process(self, sp):
        if self.ch_output.GetSelection():
            return filters.fft_filter(sp, float(self.txt_threshold.Value))
        else:
            return filters.fft_filter(sp)

class SPLINE(SubModule):
    name = 'Spline smoothing'

    def init_gui(self):
        self.txt_smoothing = wx.TextCtrl(self.view, value='0.2', size=(50,-1), style=wx.TE_PROCESS_ENTER,
                                      validator=controls.InputValidator(flag=controls.FLOAT_ONLY))

        self.ch_xaxis = wx.Choice(self.view, choices=['same as original',
                                                      'interpolated'])
        self.lab_pts = wx.StaticText(self.view, label='Num. points')
        self.lab_pts.Hide()
        self.txt_pts = wx.TextCtrl(self.view, value='1000', size=(50,-1),
                                   validator=controls.InputValidator(flag=controls.DIGIT_ONLY))
        self.txt_pts.Hide()

        self.lab_error = wx.StaticText(self.view, label='')
        fnt = self.view.GetFont().MakeSmaller()
        self.lab_error.SetFont(fnt)
        self.lab_error.SetForegroundColour('red')

        box = wx.GridBagSizer(vgap=3, hgap=3)
        box.SetFlexibleDirection(wx.HORIZONTAL)

        box.Add(self.lab_error, (0,0), span=(1,2))
        box.Add(wx.StaticText(self.view, label='Smoothing'), (1,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_smoothing, (1,1), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(wx.StaticText(self.view, label='X values'), (2,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.ch_xaxis, (2,1), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.lab_pts, (3,0), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.Add(self.txt_pts, (3,1), flag=wx.ALIGN_CENTRE_VERTICAL)
        box.AddGrowableCol(1,0)
        box.AddGrowableCol(0,1)
        box.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.view.SetSizer(box)
        self.view.Fit()

        self.view.Bind(wx.EVT_TEXT, self.OnText)
        self.view.Bind(wx.EVT_CHOICE, self.OnChoice)

    def OnChoice(self, evt):
        self.txt_pts.Show(evt.GetEventObject().GetSelection())
        self.lab_pts.Show(evt.GetEventObject().GetSelection())
        self.layout()

    def OnText(self, evt):
        err = []

        try:
            if self.txt_smoothing.Value.strip() == '' or float(self.txt_smoothing.Value.strip()) < 0:
                raise ValueError
        except ValueError:
            err.append('Smoothing factor must be >= 0')

        if self.txt_pts.Value.strip() == '' and self.ch_xaxis.Selection == 1:
            err.append('Number of points must be > 1')

        if len(err) > 0:
            self.valid = False
            self.lab_error.SetLabel('\n'.join(err))
        else:
            self.valid = True
            self.lab_error.SetLabel('')
            #self.view.Layout()
        self.layout()

    def process(self, sp):
        smoothing = float(self.txt_smoothing.Value)
        if self.ch_xaxis.Selection == 1:
            sample = int(self.txt_pts.Value)
            return filters.spline_filter(sp, smoothing, sample)
        else:
            return filters.spline_filter(sp, smoothing)
