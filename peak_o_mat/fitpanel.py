
import wx
from wx import xrc
import re

from . import pargrid
from . import weightsgrid
from . import controls

from . import lineshapebase

import  wx.lib.mixins.listctrl  as  listmix
import sys

class FeatureList(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.InsertColumn(0, "Type")
        self.InsertColumn(1, "Feature")

    def populate(self, items):
        self.ClearAll()
        for data in items:
            index = self.InsertStringItem(sys.maxsize, data[0])
            self.SetStringItem(index, 1, data[1])

class FitBatchPanel(wx.Panel):
    def __init__(self, parent):
        super(FitBatchPanel, self).__init__(parent)
        self.setup_controls()
        self.layout()
        self.Fit()

    def bf_update(self, plot, keep_selection=False):
        if plot is None:
            return
        sel_item = self.ch_base.GetSelection()

        self.ch_base.Clear()
        self.ch_base.AppendItems(['s{}'.format(q) for q in range(len(plot)) if plot[q].mod is not None])
        plot_has_model = self.ch_base.GetCount() != 0

        comps = set()
        pars = set()
        for ds in plot:
            if ds.model is not None:
                comps.update([str(q.name) for q in ds.model])
                tmp = [list(c.keys()) for c in ds.model]
                pars.update([item for sublist in tmp for item in sublist])
        self.ch_component.Clear()
        self.ch_component.AppendItems(['all']+sorted(list(comps)))
        self.ch_component.SetSelection(0)

        self.ch_parameter.Clear()
        self.ch_parameter.AppendItems(sorted(list(pars)))
        self.ch_parameter.SetSelection(0)

        if keep_selection and sel_item != -1:
            self.ch_base.SetSelection(sel_item)
        else:
            self.ch_base.SetSelection(0)

        self.Freeze()
        for widget in self.GetChildren():
            widget.Enable(plot_has_model)
        self.Thaw()

    def setup_controls(self):
        self.nb_batch = wx.Notebook(self)
        self.pan_pars = wx.Panel(self.nb_batch)
        self.nb_batch.AddPage(self.pan_pars, 'Fit')

        self.ch_base = wx.Choice(self.pan_pars, choices=[])
        self.ch_initial = wx.Choice(self.pan_pars, choices=['Base model','Last result'])
        self.ch_initial.SetSelection(0)
        self.ch_order = wx.Choice(self.pan_pars, choices=['Towards lower index','Towards higher index'])
        self.ch_order.SetSelection(0)

        self.txt_log = wx.TextCtrl(self.pan_pars, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_DONTWRAP)

        self.btn_stop = wx.Button(self.pan_pars, label='Stop')
        self.btn_stop.Disable()
        self.btn_run = wx.Button(self.pan_pars, label='Start fit')

        ### page 'export'
        self.pan_export = wx.Panel(self.nb_batch)
        self.sbox1 = wx.StaticBox(self.pan_export, label='X Data')
        self.sbox2 = wx.StaticBox(self.pan_export, label='Y Data')
        self.nb_batch.AddPage(self.pan_export, 'Parameter export')

        self.ch_component = wx.Choice(self.sbox2)
        self.ch_parameter = wx.Choice(self.sbox2)
        self.txt_xexpr = wx.TextCtrl(self.sbox1)
        self.txt_xpreview = wx.TextCtrl(self.sbox1, style=wx.TE_READONLY)
        self.cb_errors = wx.CheckBox(self.pan_export, label='include errors')
        self.btn_export = wx.Button(self.pan_export, label='Export')
        self.btn_export.Disable()
        self.btn_generate = wx.Button(self.pan_export, label='Create')
        self.btn_export.Disable()
        self.ch_target = wx.Choice(self.pan_export, choices=['New'])

    def layout(self):
        ACV = wx.ALIGN_CENTER_VERTICAL

        # fit
        outer = wx.BoxSizer(wx.VERTICAL)
        inner = wx.BoxSizer(wx.HORIZONTAL)
        grid = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        grid.Add(wx.StaticText(self.pan_pars, label='Base:'), 0, ACV)
        grid.Add(self.ch_base, 0, ACV|wx.ALIGN_RIGHT)
        grid.Add(wx.StaticText(self.pan_pars, label='Initial guess:'), 0, ACV)
        grid.Add(self.ch_initial, 0, ACV|wx.ALIGN_RIGHT)
        grid.Add(wx.StaticText(self.pan_pars, label='Fit order:'), 0, ACV)
        grid.Add(self.ch_order, 0, ACV|wx.ALIGN_RIGHT)
        inner.Add(grid,0, wx.ALL, 5)
        inner.Add(self.txt_log, 1, wx.ALL|wx.EXPAND, 5)

        outer.Add(inner, 1, wx.ALL|wx.EXPAND, 5)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.Window(self.pan_pars), 1)
        row.Add(self.btn_stop, 0, wx.RIGHT, 10)
        row.Add(self.btn_run, 0)
        outer.Add(row, 0, wx.EXPAND|wx.ALL, 5)
        self.pan_pars.SetSizer(outer)
        self.pan_pars.Fit()

        # export NEW

        vert = wx.BoxSizer(wx.VERTICAL)
        outer = wx.BoxSizer(wx.HORIZONTAL)

        sbox = wx.StaticBoxSizer(self.sbox1, wx.VERTICAL)
        inner = wx.FlexGridSizer(2,2,vgap=5,hgap=5)
        inner.AddGrowableCol(1)
        inner.Add(wx.StaticText(self.sbox1, label='Value/Expr.'), 0, wx.EXPAND)
        inner.Add(self.txt_xexpr, 0, wx.EXPAND)
        inner.Add(wx.StaticText(self.sbox1, label='Preview'), 0, wx.EXPAND)
        inner.Add(self.txt_xpreview, 0, wx.EXPAND)
        sbox.Add(inner, 1, wx.EXPAND)
        outer.Add(sbox, 2, wx.EXPAND|wx.ALL, 5)

        sbox = wx.StaticBoxSizer(self.sbox2, wx.VERTICAL)
        inner = wx.FlexGridSizer(2,2,vgap=5,hgap=5)
        inner.AddGrowableCol(1)
        inner.Add(wx.StaticText(self.sbox2, label='Component'), 0, wx.EXPAND)
        inner.Add(self.ch_component, 0, wx.EXPAND)
        inner.Add(wx.StaticText(self.sbox2, label='Parameter'), 0, wx.EXPAND)
        inner.Add(self.ch_parameter, 0, wx.EXPAND)
        sbox.Add(inner)
        outer.Add(sbox, 1, wx.EXPAND|wx.ALL, 5)

        vert.Add(outer, 0, wx.EXPAND)

        cmdrow = wx.BoxSizer(wx.HORIZONTAL)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self.pan_export, label='Create Data Set'), 0, wx.ALL, 5)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self.pan_export, label='Target plot'), 0, ACV|wx.RIGHT, 2)
        row.Add(self.ch_target, 0, ACV|wx.RIGHT, 2)
        row.Add(self.btn_generate, 0, ACV|wx.LEFT, 20)
        box.Add(row, 0, wx.ALL|wx.EXPAND, 5)
        cmdrow.Add(box, wx.EXPAND)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(wx.StaticText(self.pan_export, label='Export to Grid'), 0, wx.ALL, 5)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.cb_errors, 5, ACV|wx.LEFT)
        row.Add(self.btn_export, 0, ACV|wx.LEFT, 20)
        box.Add(row, 0, wx.ALL, 5)
        cmdrow.Add(box, 0, wx.EXPAND)

        vert.Add(cmdrow, 0, wx.EXPAND|wx.TOP|wx.RIGHT|wx.LEFT, 5)

        self.pan_export.SetSizer(vert)

        # nb_batch

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.nb_batch, 1, wx.EXPAND)
        self.SetSizer(box)

class FitModelPanel(wx.Panel):
    def __init__(self, parent):
        self.parent = parent
        super(FitModelPanel, self).__init__(parent)
        self.setup_controls()
        self.layout()

    def setup_controls(self):
        self.txt_model = wx.TextCtrl(self)
        self.lab_peakinfo = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.lst_features = FeatureList(self, style=wx.LC_REPORT|wx.BORDER_NONE)
        self.btn_addfeature = wx.Button(self, label='Add')
        self.btn_addfeature.Disable()
        self.btn_modelclear = wx.Button(self, label='Clear')

    def layout(self):
        rowstyle = wx.ALIGN_CENTER_VERTICAL

        outer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Fit model'), 0, rowstyle|wx.RIGHT,5)
        row.Add(self.txt_model, 1, rowstyle|wx.RIGHT,5)
        row.Add(self.btn_modelclear, 0, rowstyle)
        outer.Add(row, 0, wx.EXPAND|wx.ALL, 5)

        row = wx.BoxSizer(wx.HORIZONTAL)
        inner = wx.BoxSizer(wx.VERTICAL)
        inner.Add(self.lst_features, 1, wx.EXPAND|wx.BOTTOM, 5)
        inner.Add(self.btn_addfeature, 0, wx.EXPAND)
        row.Add(inner, 0, wx.EXPAND|wx.RIGHT, 5)
        row.Add(self.lab_peakinfo, 1, wx.EXPAND)
        outer.Add(row, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(outer)

class dlg_set_from_model(wx.Dialog):
    def __init__(self, parent, components, rng):
        super(dlg_set_from_model, self).__init__(parent, title='Generate set',
                                                 style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)

        self.components = components
        self.rng = rng

        self.setup_controls()
        self.layout()

        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)

    def OnClose(self, evt):
        self.Destroy()

    def setup_controls(self):
        self.p = wx.Panel(self, style=wx.WS_EX_VALIDATE_RECURSIVELY)

        self.chk_comp = wx.CheckListBox(self.p, choices=self.components)
        for n in range(len(self.components)):
            self.chk_comp.Check(n, True)
        self.btn_cancel = wx.Button(self.p, label='Cancel', id=wx.ID_CANCEL)
        self.btn_loadpeaks = wx.Button(self.p, label='Create')
        self.txt_from = wx.TextCtrl(self.p, validator=controls.InputValidator(controls.FLOAT_ONLY), style=wx.TE_RIGHT)
        self.txt_to = wx.TextCtrl(self.p, validator=controls.InputValidator(controls.FLOAT_ONLY), style=wx.TE_RIGHT)
        self.txt_pts = wx.TextCtrl(self.p, validator=controls.InputValidator(controls.INT_ONLY), style=wx.TE_RIGHT)
        self.txt_from.Value = '{:.16g}'.format(self.rng[0])
        self.txt_to.Value = '{:.16g}'.format(self.rng[1])
        self.txt_pts.Value = '1000'

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.chk_comp, 1, wx.ALL|wx.EXPAND|wx.ALL, 2)

        hbox = wx.BoxSizer(wx.HORIZONTAL)

        gbox = wx.FlexGridSizer(cols=2,hgap=2,vgap=2)
        st = wx.ALIGN_CENTER_VERTICAL|wx.EXPAND
        gbox.Add(wx.StaticText(self.p, label='From'), 0, st)
        gbox.Add(self.txt_from, 0, st)
        gbox.Add(wx.StaticText(self.p, label='To'), 0, st)
        gbox.Add(self.txt_to, 0, st)
        gbox.Add(wx.StaticText(self.p, label='Points'), 0, st)
        gbox.Add(self.txt_pts, 0, st)
        hbox.Add(wx.Window(self.p), 1)
        hbox.Add(gbox)
        box.Add(hbox, 0, wx.EXPAND|wx.ALL, 2)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(self.p), 1)
        hbox.Add(self.btn_cancel, 0, wx.ALL, 2)
        hbox.Add(self.btn_loadpeaks, 0, wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND|wx.TOP, 5)
        self.p.SetSizer(box)
        self.p.Layout()
        fbox = wx.BoxSizer(wx.VERTICAL)
        fbox.Add(self.p, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(fbox)
        self.Fit()

class dlg_export_parameters(wx.Dialog):
    def __init__(self, parent, parameters):
        super(dlg_export_parameters, self).__init__(parent, title='Export parameters',
                                                 style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)

        self.parameters = parameters

        self.setup_controls()
        self.layout()

        self.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CANCEL)

    def OnClose(self, evt):
        self.Destroy()

    def setup_controls(self):
        self.p = wx.Panel(self, style=wx.WS_EX_VALIDATE_RECURSIVELY)

        self.chk_pars = wx.CheckListBox(self.p, choices=self.parameters)
        for n in range(len(self.parameters)):
            self.chk_pars.Check(n, True)
        self.btn_cancel = wx.Button(self.p, label='Cancel', id=wx.ID_CANCEL)
        self.btn_export = wx.Button(self.p, label='Create')
        self.chk_error = wx.CheckBox(self.p, label='Include errors')

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.chk_pars, 1, wx.ALL | wx.EXPAND | wx.ALL, 2)
        box.Add(self.chk_error, 0, wx.ALL | wx.EXPAND | wx.ALL, 2)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(wx.Window(self.p), 1)
        hbox.Add(self.btn_cancel, 0, wx.ALL, 2)
        hbox.Add(self.btn_export, 0, wx.ALL, 2)
        box.Add(hbox, 0, wx.EXPAND|wx.TOP, 5)
        self.p.SetSizer(box)
        self.p.Layout()
        fbox = wx.BoxSizer(wx.VERTICAL)
        fbox.Add(self.p, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(fbox)
        self.Fit()

class FitParsPanel(wx.Panel):
    def __init__(self, parent):
        super(FitParsPanel, self).__init__(parent, name='tab_parameters')
        self.setup_controls()
        self.layout()
        self.Fit()

    def setup_controls(self):
        self.pargrid = pargrid.ParGrid(self)

        self.btn_pickpars = wx.Button(self, label='Pick', style=wx.BU_EXACTFIT)
        self.ch_pickpars = wx.Choice(self, size=(70,-1))
        self.btn_guesspars = wx.Button(self, label='Guess', style=wx.BU_EXACTFIT)
        self.btn_generateset = wx.Button(self, label='Generate dataset')

        self.btn_parexport = wx.Button(self, label='Export parameters')
        #self.ch_parexport = wx.Choice(self, size=(70,-1))
        #self.cb_errors = wx.CheckBox(self, label='with errors')

        self.btn_fit_quick = wx.Button(self, label='Fit')

    def layout(self):
        rowstyle = wx.ALIGN_CENTER_VERTICAL

        outer = wx.BoxSizer(wx.HORIZONTAL)
        col = wx.BoxSizer(wx.VERTICAL)
        col.Add(wx.StaticText(self, label='Initial guess'), 0, wx.BOTTOM, 5)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.btn_pickpars, 0, rowstyle|wx.RIGHT, 5)
        row.Add(self.ch_pickpars, 0, rowstyle)
        row.Add(self.btn_guesspars, 0, rowstyle|wx.LEFT, 15)
        col.Add(row, 0, wx.EXPAND|wx.BOTTOM, 20)

        col.Add(self.btn_generateset, 0, wx.BOTTOM, 5)
        col.Add(self.btn_parexport, 0, wx.EXPAND|wx.BOTTOM, 20)

        row = wx.BoxSizer(wx.HORIZONTAL)
        #row.Add(wx.Window(self), 1)
        row.Add(self.btn_fit_quick, 0, rowstyle)
        col.Add(row, 0, wx.EXPAND)
        outer.Add(col, 0, wx.EXPAND|wx.ALL, 5)

        outer.Add(self.pargrid, 1, wx.EXPAND|wx.ALL|wx.FIXED_MINSIZE, 5)
        self.SetSizer(outer)
        self.Fit()

class FitWeightsPanel(wx.Panel):
    def __init__(self, parent):
        super(FitWeightsPanel, self).__init__(parent, name='tab_weights')
        self.setup_controls()
        self.layout()
        self.Fit()

    def setup_controls(self):
        self.btn_placehandles = wx.ToggleButton(self, label='Place region borders')
        self.btn_storeweights = wx.Button(self, label='Attach to set')
        self.btn_clearweights = wx.Button(self, label='Clear')

        self.weightsgrid = weightsgrid.WeightsGrid(self)

    def layout(self):
        outer = wx.BoxSizer(wx.HORIZONTAL)
        col = wx.BoxSizer(wx.VERTICAL)
        col.Add(self.btn_placehandles, 0, wx.EXPAND|wx.BOTTOM, 5)
        col.Add(self.btn_storeweights, 0, wx.EXPAND|wx.BOTTOM, 5)
        col.Add(self.btn_clearweights, 0, wx.EXPAND|wx.BOTTOM, 5)
        outer.Add(col, 0, wx.EXPAND|wx.ALL, 5)

        outer.Add(self.weightsgrid, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(outer)
        self.Fit()

class FitOptionsPanel(wx.Panel):
    def __init__(self, parent):
        super(FitOptionsPanel, self).__init__(parent)
        self.setup_controls()
        self.layout()
        self.Fit()

    def setup_controls(self):

        self.cb_limitfitrange = wx.CheckBox(self, label='Limit fit to visible range')
        self.cb_autostep = wx.CheckBox(self, label='Default')
        self.txt_stepsize = wx.TextCtrl(self, value='1e-10', size=(70,-1), style=wx.TE_RIGHT)
        self.cb_autostep.SetValue(True)
        self.txt_stepsize.Enable(False)

        self.txt_maxiter = wx.TextCtrl(self, value='200', validator=controls.InputValidator(controls.INT_ONLY), size=(70,-1), style=wx.TE_RIGHT)
        self.txt_fitlog = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.ch_fittype  = wx.Choice(self, choices=['LeastSQ', 'ODR'])
        self.ch_fittype.Select(0)

    def layout(self):
        rowstyle = wx.ALIGN_CENTER_VERTICAL

        outer = wx.BoxSizer(wx.HORIZONTAL)
        col = wx.BoxSizer(wx.VERTICAL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Fit type'), 0, rowstyle|wx.RIGHT, 2)
        row.Add(self.ch_fittype, 0, rowstyle)
        col.Add(row, 0, wx.EXPAND|wx.BOTTOM, 10)

        col.Add(self.cb_limitfitrange, 0, wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Max iterations'), 0, rowstyle|wx.RIGHT, 2)
        row.Add(self.txt_maxiter, 0, rowstyle)
        col.Add(row, 0, wx.EXPAND|wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Step size'), 0, rowstyle|wx.RIGHT, 2)
        row.Add(self.txt_stepsize, 0, rowstyle|wx.RIGHT, 5)
        row.Add(self.cb_autostep, 0, rowstyle)
        col.Add(row, 0, wx.EXPAND)
        outer.Add(col, 0, wx.EXPAND|wx.ALL, 5)
        outer.Add(self.txt_fitlog, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(outer)
        self.Fit()

class FitPanel(wx.Panel):
    def __init__(self, parent, canvas):
        self.canvas = canvas
        self.parent = parent
        super(FitPanel, self).__init__(parent)

        self.setup_controls()
        self.layout()
        self.Fit()

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.nb_fit)
        self.SetSizer(box)

    def setup_controls(self):
        self.id = 'ID'+str(id(wx.GetTopLevelParent(self)))

        self.nb_fit = wx.Notebook(self)
        self.pan_model = FitModelPanel(self.nb_fit)
        self.pan_pars = FitParsPanel(self.nb_fit)
        self.pan_weights = FitWeightsPanel(self.nb_fit)
        self.pan_options = FitOptionsPanel(self.nb_fit)
        self.pan_batch = FitBatchPanel(self.nb_fit)

        self.nb_fit.AddPage(self.pan_model, 'Model')
        self.nb_fit.AddPage(self.pan_pars, 'Parameters')
        self.nb_fit.AddPage(self.pan_weights, 'Weights')
        self.nb_fit.AddPage(self.pan_options, 'Options')
        self.nb_fit.AddPage(self.pan_batch, 'Batch fit')

    def progress_dialog(self, max=0, step=None):
        if step is not None:
            self.count += 1
            self.pgdlg.Update(self.count, step)
        elif max != 0:
            self.count = 0
            self.pgdlg = wx.ProgressDialog("Batch fit in progress",
                                   '',
                                   maximum = max,
                                   parent = self,
                                   style = 0)

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def _get_model(self):
        return self.pan_model.txt_model.GetValue()
    def _set_model(self, value):
        ins = self.pan_model.txt_model.GetInsertionPoint()
        self.pan_model.txt_model.ChangeValue(value)
        self.pan_model.txt_model.SetInsertionPoint(ins)
    model = property(_get_model, _set_model)

    def _set_pickwhich_choice(self, items):
        self.pan_pars.ch_pickpars.Freeze()
        self.pan_pars.ch_pickpars.Clear()
        for item in items:
            self.pan_pars.ch_pickpars.Append(str(item))
        self.pan_pars.ch_pickpars.SetSelection(0)
        self.pan_pars.ch_pickpars.Thaw()
    pickwhich_choice = property(fset=_set_pickwhich_choice)

    def _get_pickwhich(self):
        return self.pan_pars.ch_pickpars.GetSelection()
    def _set_pickwhich(self, sel):
        self.pan_pars.ch_pickpars.SetSelection(sel)
    pickwhich = property(_get_pickwhich,_set_pickwhich)

    def _get_nbpage(self):
        return self.nb_fit.GetPage()
    def _set_nbpage(self, num):
        self.nb_fit.SetSelection(num)
    nbpage = property(_get_nbpage, _set_nbpage)
    
    def _get_nbpages(self):
        return self.nb_fit.GetPageCount()
    nbpages = property(_get_nbpages)

    def _get_fittype(self):
        return self.pan_options.ch_fittype.GetSelection()
    fittype = property(_get_fittype)

    def _get_limitfitrange(self):
        return self.pan_options.cb_limitfitrange.IsChecked()
    def _set_limitfitrange(self, val):
        self.pan_options.cb_limitfitrange.SetValue(bool(val))
    limitfitrange = property(_get_limitfitrange, _set_limitfitrange)
    
    def _get_maxiter(self):
        return int(self.pan_options.txt_maxiter.GetValue())
    maxiter = property(_get_maxiter)
    
    def _get_stepsize(self):
        return float(self.pan_options.txt_stepsize.GetValue())
    stepsize = property(_get_stepsize)

    def _get_autostep(self):
        return self.pan_options.cb_autostep.GetValue()
    def _set_autostep(self, state):
        self.pan_options.txt_stepsize.Enable(state)
        self.pan_options.cb_autostep.SetValue(state)
    autostep = property(_get_autostep, _set_autostep)
                               
    def _set_fitlog(self, txt):
        self.txt_fitlog.AppendText(txt+'\n')
    log = property(fset=_set_fitlog)

    def enable_fit(self, state):
        #self.btn_fit.Enable(state)
        self.pan_pars.btn_fit_quick.Enable(state)
        self.pan_pars.btn_generateset.Enable(state)
        self.pan_pars.btn_parexport.Enable(state)

    def enable_pick(self, state):
        self.pan_pars.btn_pickpars.Enable(state)
        self.pan_pars.ch_pickpars.Enable(state)

    def drawModelButtons(self):
        for ptype in lineshapebase.lineshapes.ptypes:
            tokens = lineshapebase.lineshapes.group(ptype)

            for n,name in enumerate(tokens):
                self.pan_model.lst_features.Append((ptype.lower(),name))
                #index = self.pan_model.lst_features.AppendItem(n, ptype.lower())
                #self.pan_model.lst_features.SetStringItem(index, 1, name)

if __name__ == '__main__':

    import wx.lib.mixins.inspection as wit

    app = wit.InspectableApp()

    #pans = [FitModelPanel, FitParsPanel, FitWeightsPanel, FitPanel]
    #for p in pans:
    #    f = wx.Frame(None)
    #    p = p(f)
    #    f.Show()

    f = dlg_export_parameters(None, ['a', 'b', 'c'])
    f.Show()
    app.MainLoop()
