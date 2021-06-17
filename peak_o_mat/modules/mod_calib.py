import wx
from pubsub import pub
import wx.dataview as dv
import wx.aui as aui

import numpy as np
from wx.lib.scrolledpanel import ScrolledPanel

from peak_o_mat import module, spec, calib, controls, misc_ui, menu


class Panel(ScrolledPanel):
    def __init__(self, parent, model):
        super(Panel, self).__init__(parent)
        self.calib = model
        self.setup_controls()
        self.layout()

        self.SetupScrolling(scrollToTop=False, scrollIntoView=False)

    def setup_controls(self):
        self.grid = CalibGrid(self, self.calib, size=(200, -1))
        self.btn_elem = wx.Button(self)
        self.ch_unit = wx.Choice(self)
        self.chk_speclines = wx.CheckBox(self)
        self.txt_tol = wx.TextCtrl(self, value='2.0', style=wx.TE_RIGHT)
        self.txt_offset = wx.TextCtrl(self, value='0.0', style=wx.TE_RIGHT)
        self.spin_order = wx.SpinCtrl(self, size=(60, -1), value='0', min=0, max=2)
        self.btn_dispersion = wx.Button(self, label='Plot dispersion')
        self.btn_storesearch = wx.Button(self, label='Store')
        self.btn_restoresearch = wx.Button(self, label='Restore')
        self.txt_calibration = wx.TextCtrl(self, value='<empty>', style=wx.TE_READONLY)
        self.btn_storecalibration = wx.Button(self, label='Store')
        self.btn_calibrate = wx.Button(self, label='Calibrate')

    def layout(self):
        outer = wx.BoxSizer(wx.VERTICAL)
        inner = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(self.grid, 1, flag=wx.ALL | wx.EXPAND, border=5)

        row = wx.BoxSizer(wx.HORIZONTAL)

        row.Add(wx.StaticText(self, label='Tolerance '), 0, wx.RIGHT | wx.EXPAND, 5)
        row.Add(self.txt_tol, 1, wx.RIGHT | wx.EXPAND, 10)
        row.Add(wx.StaticText(self, label='Offset'), 0, wx.RIGHT | wx.EXPAND, 5)
        row.Add(self.txt_offset, 1, wx.ALL | wx.EXPAND)
        left.Add(row, 0, wx.EXPAND | wx.ALL, 5)

        inner.Add(left, 1, wx.EXPAND)

        col = wx.BoxSizer(wx.VERTICAL)
        grd = wx.FlexGridSizer(cols=2, hgap=15, vgap=5)
        grd.Add(wx.StaticText(self, label='Element'), 1, flag=wx.ALL | wx.EXPAND)
        grd.Add(self.btn_elem, 1, flag=wx.ALL | wx.EXPAND)
        grd.Add(wx.StaticText(self, label='Unit'), 1, flag=wx.ALL | wx.EXPAND)
        grd.Add(self.ch_unit, 1, flag=wx.ALL | wx.EXPAND)
        grd.Add(wx.StaticText(self, label='Show lines'), 1, flag=wx.ALL | wx.EXPAND)
        grd.Add(self.chk_speclines, 1, flag=wx.ALL | wx.EXPAND)
        col.Add(grd, 1, wx.EXPAND | wx.ALL, 5)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Order of regression'), 0, flag=wx.ALL | wx.EXPAND, border=5)
        row.Add(self.spin_order, 0, flag=wx.ALL | wx.EXPAND, border=5)
        row.Add(wx.Window(self), 1, wx.LEFT, 20)
        row.Add(self.btn_dispersion, 0, flag=wx.ALL | wx.EXPAND, border=5)
        col.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(self, label='Search pattern'), 1, flag=wx.ALL | wx.EXPAND, border=5)
        row.Add(self.btn_storesearch, 1, flag=wx.ALL | wx.EXPAND, border=5)
        row.Add(self.btn_restoresearch, 1, flag=wx.ALL | wx.EXPAND, border=5)
        col.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        # row.Add(self.chk_applytogroup, 1, flag=wx.ALL|wx.EXPAND, border=5)
        row.Add(wx.StaticText(self, label='Calibration'), 0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        row.Add(self.btn_storecalibration, 0, flag=wx.ALL, border=5)
        row.Add(self.txt_calibration, 1, flag=wx.ALL, border=5)
        col.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.Window(self), 1)
        row.Add(self.btn_calibrate, 0, flag=wx.ALL | wx.EXPAND, border=5)
        col.Add(row, 0, wx.EXPAND)

        inner.Add(col, 0, wx.EXPAND)
        outer.Add(inner, 1, wx.EXPAND)
        self.SetSizer(outer)
        self.Fit()

        # fsizer = wx.BoxSizer(wx.HORIZONTAL)
        # fsizer.Add(self, 1, wx.EXPAND)
        # self.GetParent().SetSizer(fsizer)
        # fsizer.SetSizeHints(self.GetParent())

    def message(self, msg, target=1, blink=False):
        event = misc_ui.ShoutEvent(-1, msg=msg, target=target, blink=blink)
        wx.PostEvent(self, event)


class Module(module.BaseModule):
    title = 'Calibration'
    lastsearch = None
    calibration = None
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
        # menu.add_module(self.parent_controller.view.menubar, self.title)

        pub.subscribe(self.OnSelectionChanged, (self.instid, 'selection', 'changed'))

    def init(self):
        self.calib = CalibrationModel([])
        self.view = Panel(self.parent_view, self.calib)
        super(Module, self).init()

        self.init_ctrls()

        self.view.Bind(wx.EVT_TEXT, self.OnTol, self.view.txt_tol)
        self.view.Bind(wx.EVT_TEXT, self.OnOffset, self.view.txt_offset)

        self.view.Bind(wx.EVT_BUTTON, self.OnElement, self.view.btn_elem)

        self.view.Bind(wx.EVT_CHOICE, self.OnUnit, self.view.ch_unit)
        self.view.Bind(wx.EVT_BUTTON, self.OnApply, self.view.btn_calibrate)
        self.view.Bind(wx.EVT_BUTTON, self.OnStore, self.view.btn_storesearch)
        self.view.Bind(wx.EVT_BUTTON, self.OnRestore, self.view.btn_restoresearch)
        self.view.Bind(wx.EVT_BUTTON, self.OnDispersion, self.view.btn_dispersion)

        # self.panel_list.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChanged, self.panel_list.grid)
        self.view.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnDataChanged, self.view.grid)
        self.view.Bind(wx.EVT_CHECKBOX, self.OnShow, self.view.chk_speclines)
        self.view.Bind(wx.EVT_BUTTON, self.OnStoreCalibration, self.view.btn_storecalibration)

        # self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToImport, self.view.ch_unit)

        self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToCalibrate, self.view.btn_calibrate)
        self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.view.btn_storesearch)
        self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.view.btn_dispersion)
        self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToApply, self.view.btn_storecalibration)
        self.view.Bind(wx.EVT_UPDATE_UI, self.OnReadyToRestoreSearch, self.view.btn_restoresearch)

        pub.subscribe(self.update, (self.instid, 'setattrchanged'))

    def update_from_model(self):
        # it = self.panel_list.ch_unit.FindString(self.calib.unit)
        # self.panel_list.ch_unit.SetSelection(it)
        self.view.SetEvtHandlerEnabled(False)
        self.view.txt_tol.Value = str(self.calib.tol)
        self.view.txt_offset.Value = str(self.calib.offset)
        self.view.SetEvtHandlerEnabled(True)

    def OnShow(self, evt):
        if evt.IsChecked():
            self.plotme = 'Spikes', spec.Dataset(*self.calib.spectrum)
        else:
            self.plotme = None
        pub.sendMessage((self.instid, 'updateplot'))

    def OnReadyToImport(self, evt):
        set = self.parent_controller.active_set
        if not (set is not None and set.mod is not None and set.mod.is_filled()):
            self.view.chk_speclines.Value = False
            self.plotme = None
        evt.Enable(set is not None and set.mod is not None and set.mod.is_filled())

    def OnReadyToCalibrate(self, evt):
        evt.Enable(self.calibration is not None)

    def OnReadyToApply(self, evt):
        evt.Enable(len(self.calib.selection) > 0)

    def OnReadyToRestoreSearch(self, evt):
        evt.Enable(self.lastsearch is not None)

    def OnStoreCalibration(self, evt):
        self.calibration = self.calib.trafo(self.calib.selection, int(self.view.spin_order.Value))
        n = len(self.calib.selection)
        regrtypes = {0: 'zero-order', 1: '1st order', 2: '2nd order'}
        if n == 1:
            lab = '1 line, zero-order'
        else:
            lab = '{} lines, {}'.format(n, regrtypes[self.view.spin_order.Value])
        self.view.txt_calibration.Value = lab
        self.view.message('Calibration has been stored for later use')

    def init_ctrls(self):
        label = '/'.join(self.calib.element)
        self.view.btn_elem.SetLabel(label)
        self.view.spin_order.SetRange(0, 0)

        # for e in self.calib.element_list():
        #    self.panel_list.ch_elem.Append(e)
        # self.panel_list.ch_elem.SetStringSelection(self.calib.element)
        for u in self.calib.unit_list():
            self.view.ch_unit.Append(u)
        self.view.ch_unit.SetStringSelection(self.calib.unit)
        self.view.txt_tol.Value = str(self.calib.tol)
        self.view.txt_offset.Value = str(self.calib.offset)

    def selection_changed(self):
        self.update()
        # self.panel_list.btn_update.Enable(self.parent_controller.active_set is not None)

    def focus_changed(self, newfocus=None):
        if newfocus != self.title:
            self.plotme = None
            # self.view.chk_speclines.Value = False
            pub.sendMessage((self.instid, 'updateplot'))
            self.visible = False
        else:
            self.visible = True
            if self.view.chk_speclines.Value:
                self.plotme = 'Spikes', spec.Dataset(*self.calib.spectrum)
            self.update()

    def OnDispersion(self, evt):
        trafo = self.calib.trafo(self.calib.selection, int(self.view.spin_order.Value))
        x, y = np.transpose(np.take(np.atleast_2d(self.calib.data), self.calib.selection, axis=0)[:, 2:4]).astype(float)
        data = spec.Dataset(x, y, 'data')
        a = x[0] - x[0] / 1000.0
        b = x[-1] + x[-1] / 1000.0
        x = np.linspace(a, b, 100)
        y = eval(trafo)
        regr = spec.Dataset(x, y, 'regression')
        plot = self.parent_controller.add_plot()
        self.parent_controller.add_set(data, plot)
        self.parent_controller.add_set(regr, plot)

    def OnUnit(self, evt):
        self.calib.unit = self.view.ch_unit.GetStringSelection()
        self.update()
        self.lastsearch = None

        if self.view.chk_speclines.Value:
            self.plotme = 'Spikes', spec.Dataset(*self.calib.spectrum)
            pub.sendMessage((self.instid, 'updateplot'))

    def OnElement(self, evt):
        dlg = controls.MultipleChoice(self.view, 'Select elements', choices=list(calib.elements.keys()))
        dlg.SetSelections(self.calib.element)

        if dlg.ShowModal() == wx.ID_OK:
            self.calib.element = dlg.selection
            label = '/'.join(self.calib.element)
            self.view.btn_elem.SetLabel(label)

            # self.calib.element = self.panel_list.ch_elem.GetStringSelection()
            self.view.grid.enable_edit(self.calib.element == ['Custom'])

            aset = self.parent_controller.active_set
            if aset is not None and aset.mod is not None:
                # meas = np.array(aset.mod.get_parameter_by_name('pos'))
                meas = []
                for f in aset.mod:
                    if hasattr(f, 'pos'):
                        meas.append([f.name, f.pos.value])
                self.calib.findmatch(meas)
            else:
                self.calib.findmatch(np.empty((0, 2)))
            self.calib.update()

            if self.view.chk_speclines.Value:
                self.plotme = 'Spikes', spec.Dataset(*self.calib.spectrum)
                pub.sendMessage((self.instid, 'updateplot'))

            self.lastsearch = None

    def OnTol(self, evt):
        try:
            self.calib.tol = abs(float(self.view.txt_tol.GetValue()))
        except:
            return
        else:
            self.update()

    def OnOffset(self, evt):
        try:
            self.calib.offset = float(self.view.txt_offset.GetValue())
        except:
            return
        else:
            self.update()

    def OnDataChanged(self, evt):
        if evt.GetColumn() == 3:
            aset = self.parent_controller.active_set
            if aset is not None and aset.mod is not None:
                # meas = np.array(aset.mod.get_parameter_by_name('pos'))
                meas = []
                for f in aset.mod:
                    if hasattr(f, 'pos'):
                        meas.append([f.name, f.pos.value])
                self.calib.findmatch(meas, recalc=True)

            if self.view.chk_speclines.Value:
                self.plotme = 'Spikes', spec.Dataset(*self.calib.spectrum)

                pub.sendMessage((self.instid, 'updateplot'))

        if evt.GetColumn() == 0:
            coerced = min(int(self.view.spin_order.Value), max(0, len(self.calib.selection) - 1))
            self.view.spin_order.SetValue(coerced)
            self.view.spin_order.SetRange(0, max(0, min(len(self.calib.selection) - 1, 2)))

    def update(self):
        # if len(self.calib.selection) > 0:
        #    selected = np.take(self.calib.data, self.calib.selection, axis=0)[:,2]
        # else:
        #    selected = []

        aset = self.parent_controller.active_set

        if aset is not None and aset.mod is not None:
            # meas = np.array(aset.mod.get_parameter_by_name('pos'))
            meas = []
            for f in aset.mod:
                if hasattr(f, 'pos'):
                    meas.append([f.name, f.pos.value])
            self.calib.findmatch(meas)
        else:
            self.calib.findmatch(np.empty((0, 2)))
        self.calib.selection = []

        # for s in selected:
        #    if len(self.calib.data) > 0 and s in np.array(self.calib.data)[:,2]:
        #        self.calib.selection.append(np.array(self.calib.data)[:,2].tolist().index(s))

        self.calib.update()

    def OnApply(self, evt):
        # if np.sometrue(np.isnan(np.take(self.calib.data, self.calib.selection, axis=0).astype(float))):
        #    self.message('NaN found in custom calibration data')
        if 1:
            ### TODO: remplace by message
            # trafo = self.calib.trafo(self.calib.selection, int(self.view.spin_order.Value))
            trafo = self.calibration

            plot, sets = self.parent_controller.selection

            for ds in sets:
                self.parent_controller.project[plot][ds].trafo.append(
                    ('x', trafo, 'calib, %d lines' % len(self.calib.selection)))
            pub.sendMessage((self.instid, 'updateplot'))

    def OnStore(self, evt):
        if self.calib.element != ['Custom']:
            labels, lines = self.calib.match
            self.lastsearch = [labels[q] for q in self.calib.selection], [lines[q] for q in self.calib.selection]
        else:
            labels, lines = self.calib.match
            self.lastsearch = self.calib.selection, [lines[q] for q in self.calib.selection]
        self.view.message('Current match pattern has been stored for later use')

    def OnRestore(self, evt):
        if self.lastsearch is not None:
            if self.calib.element != ['Custom']:
                labels, lines = self.lastsearch
                aset = self.parent_controller.active_set
                # TODO
                # need to catch exception in case the model has fewer features than the las one
                measured = np.asarray([aset.mod[q].pos.value for q in labels])
                fwhm = np.asarray([aset.mod[q].fwhm.value for q in labels])
                off = -(measured - lines).mean()
                tol = max((measured - lines).std() * 6, fwhm.mean() * 0.1)
                self.calib.tol = tol
                self.calib.offset = off
                self.update()
                self.calib.selection = lines
                self.update_from_model()
            else:
                selection, lines = self.lastsearch
                self.update()
                self.calib.selection = selection
                for n, s in enumerate(selection):
                    self.calib.data[s][3] = lines[n]
                self.calib.update()


class dic(list):
    """\
    Class which behaves like a python dict but preserves the natural order of
    its elements. Feed with a list of 2-tuples
    """

    def __init__(self, data):
        self._keys = []
        self._vals = []
        for k, v in data:
            self._keys.append(k)
            self._vals.append(v)

    def keys(self):
        return self._keys

    def values(self):
        return self._vals

    def __getitem__(self, item):
        return self._vals[self._keys.index(item)]


# class Calibration(list):
#     unit = u"\u212B"
#     element = 'Ne'
#     tol = 2.0
#     offset = -4.0
#
#     element_map = dic([('Ne','neon'), ('Ar','argon'), ('Ne/Ar','near'), ('Hg','mercury'), ('Cd','cadmium'), ('Hg/Cad','merccad'), ('Custom',None)])
#
#     conversion_map = dic([('eV','12398.52/standard'),('nm','standard/10.0'),(u"\u212B",'standard'),('cm-1','1.0/standard*1e8')])
#
#     def unit_list(self):
#         return self.conversion_map.keys()
#
#     def element_list(self):
#         return self.element_map.keys()
#
#     def convert(self):
#         standard = getattr(calib,self.element_map[self.element])[:,0]
#         #inten = getattr(calib,self.element_map[self.element])[:,1]
#         standard = eval(self.conversion_map[self.unit])   # ugly, picks up 'standard' as local variable
#         return standard
#
#     standard = property(convert)
#
#     def findmatch(self, measured, recalc=False):
#         if self.element != ['Custom']:
#             match_meas, match_std =  np.where((abs((self.standard-self.offset)-measured[:,np.newaxis])) < self.tol)
#             measured, match = measured[match_meas], self.standard[match_std]
#
#             if recalc:
#                 for n,l in enumerate(self):
#                     l[1:] = [list(m) for m in np.transpose([measured, match, measured-match])]
#             else:
#                 self.data[:] = [['False']+list(m) for m in np.transpose([measured, match, measured-match])]
#         else:
#             for n,l in enumerate(self):
#                 l[3] = measured[n] - l[2]
#
#     def regression(self, selection):
#         meas, std = np.transpose(np.take(np.atleast_2d(self), selection, 0)[:,1:3])
#
#         if len(std) == 1:
#             return [std-meas]
#         else:
#             a = np.transpose([std,np.ones(std.shape)])
#             b = np.transpose(meas)
#
#             coeff = linalg.lstsq(a,b)[0]
#             return coeff
#
#     def trafo(self, selection):
#         coeff = self.regression(selection)
#
#         if len(coeff) == 1:
#             trafo = 'x+%.10e'%(coeff[0])
#         else:
#             trafo = '(x-(%.10e))/%.10e'%(coeff[1],coeff[0])
#         return trafo

class CalibrationModel(dv.DataViewIndexListModel):
    unit = "\u212B"
    element = ['Ne']
    tol = 0.5
    offset = 0.0

    # element_map = dic([('Ne','neon'), ('Ar','argon'), ('Ne/Ar','near'), ('Hg','mercury'), ('Cd','cadmium'), ('Hg/Cad','merccad'), ('Custom',None)])
    conversion_map = dic(
        [('eV', '12398.52/standard'), ('nm', 'standard/10.0'), ("\u212B", 'standard'), ('cm-1', '1.0/standard*1e8')])

    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self, len(data))
        self.data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self.Reset(len(data))

    # data = property(getdata, setdata)

    def GetValueByRow(self, row, col):
        try:
            return str(self._data[row][col]) if col > 0 else self._data[row][col]
        except IndexError:
            print('getvaluebyrow index error row {}, col {}'.format(row, col))
            return 0

    def SetValueByRow(self, value, row, col):
        if col == 0:
            self._data[row][col] = bool(value)
        else:
            self._data[row][col] = float(value)
        return True

    def GetAttrByRow(self, row, col, attr):
        if col == 3 and self.element == ['Custom']:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

    def unit_list(self):
        return list(self.conversion_map.keys())

    def element_list(self):
        return list(self.element_map.keys())

    def convert(self):
        choice = [calib.elements[q] for q in self.element]
        standard = np.take(np.vstack((choice)), np.argsort(np.vstack(choice)[:, 0], 0), 0)[:, 0]

        # standard = getattr(calib,self.element_map[self.element])[:,0]

        # inten = getattr(calib,self.element_map[self.element])[:,1]
        standard = eval(self.conversion_map[self.unit])  # ugly, picks up 'standard' as local variable
        return standard

    standard = property(convert)

    @property
    def spectrum(self):
        if self.element == ['Custom']:
            tmp = np.asarray(self.data)[:, 3:]
            tmp[:, 1] = 1.0
            tmp = np.asarray(tmp, dtype=float)
        else:
            choice = [calib.elements[q] for q in self.element]
            tmp = np.take(np.vstack((choice)), np.argsort(np.vstack(choice)[:, 0], 0), 0)
            standard = tmp[:, 0]
            standard = eval(self.conversion_map[self.unit])  # ugly, picks up 'standard' as local variable
            tmp[:, 0] = standard
        return tmp.T[0], tmp.T[1], 'speclines'

    def findmatch(self, measured, recalc=False):
        try:
            labels, measured = list(zip(*measured))
        except ValueError:
            labels = []
            measured = []
        measured = np.asarray(measured)
        if self.element != ['Custom']:
            match_meas, match_std = np.where((abs((self.standard - self.offset) - measured[:, np.newaxis])) < self.tol)
            measured, standard = measured[match_meas], self.standard[match_std]
            self.match = np.take(labels, match_meas).tolist(), standard  # to be used for storage of search
            # if recalc:
            #    for n,l in enumerate(self.data):
            #        l[2:] = [list(m) for m in np.transpose([measured, standard, measured-standard])]
            # else:
            self.data = [[False] + list(m) for m in zip(self.match[0], measured, standard, measured - standard)]
        else:
            ndiff = len(self.data) - len(measured)
            if ndiff != 0:
                self.data = [[False] + [labels[q], measured[q], measured[q], 0] for q in range(len(measured))]
            if recalc:
                for n, l in enumerate(self.data):
                    l[4] = l[2] - l[3]
            self.match = labels, [self.data[q][3] for q in range(len(labels))]  # to be used for storage of search

    def regression(self, selection, degree=0):
        meas, std = np.transpose(np.take(np.atleast_2d(self.data), selection, 0)[:, 2:4].astype(float))

        if degree == 0:
            return (std - meas).mean()
        else:
            # print 'polyfit degree',degree,
            coeff = np.polyfit(np.atleast_1d(meas), np.atleast_1d(std), degree)
            return coeff

    def trafo(self, selection, order):
        coeff = self.regression(selection, order)
        if np.isscalar(coeff):
            trafo = 'x+{:.16e}'.format(coeff)
        elif len(coeff) == 2:
            trafo = 'x*{:.16f}+{:.16f}'.format(*coeff)
        elif len(coeff) == 3:
            trafo = 'x**2*{:.16f}+x*{:.16f}+{:.16f}'.format(*coeff)
        else:
            trafo = 'x'
        return trafo

    def update(self):
        self.Reset(len(self.data))

    @property
    def selection(self):
        return [i for i in range(len(self.data)) if self.data[i][0]]

    @selection.setter
    def selection(self, selection):
        selection = np.asarray(selection)
        if len(selection) == 0 or selection.dtype == int:
            for n in range(len(self.data)):
                self.data[n][0] = True if n in selection else False
        elif selection.dtype == float:
            for n in range(len(self.data)):
                self.data[n][0] = True if np.isclose(self.data[n][3] - selection, 0).any() else False
        self.Reset(len(self.data))

    def GetColumnCount(self):
        return 3

    def GetColumnType(self, col):
        return ['bool', 'string', 'float', 'float', 'float'][col]


class CalibGrid(dv.DataViewCtrl):
    def __init__(self, parent, model, **kwargs):
        super(CalibGrid, self).__init__(parent, style=wx.BORDER_THEME
                                                      | dv.DV_ROW_LINES  # nice alternating bg colors
                                                      | dv.DV_VERT_RULES
                                                      | dv.DV_MULTIPLE, **kwargs)

        self.AssociateModel(model)

        col_chk = self.AppendToggleColumn('Match', 0, width=40, mode=dv.DATAVIEW_CELL_ACTIVATABLE)
        self.AppendTextColumn('Peak', 1, width=40)
        self.AppendTextColumn('Measured', 2, width=120)
        self.col_standard = dv.DataViewColumn('standard', dv.DataViewTextRenderer(mode=dv.DATAVIEW_CELL_EDITABLE), 3,
                                              width=120)
        self.AppendColumn(self.col_standard)
        self.AppendTextColumn('Difference', 4, width=120)

        self.enable_edit(False)

        ### TODO on OSX this fires when double clicking, not slow clicking but the evt memebers are nonsense
        ### so better delete
        self.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnActivate, self)

    def OnActivate(self, evt):
        try:
            self.EditItem(evt.GetItem(), self.GetColumn(evt.GetColumn()))
        except:
            print('double click on column generates silly event')

    def enable_edit(self, state):
        pass
        # self.col_standard.GetRenderer().SetMode(dv.DATAVIEW_CELL_EDITABLE if state else 0)


if __name__ == '__main__':
    app = wx.App(None)
    f = wx.Frame(None)
    p = Panel(f)
    f.Show()
    app.MainLoop()
