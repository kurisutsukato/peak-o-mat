__author__ = 'ck'

import wx
import wx.dataview as dv
from pubsub import pub as Publisher
from random import sample
import os
import textwrap
import _thread

from .plotlayout import EVT_RECT_SELECT, EVT_RECT_REORDER


info = '''\
If you feel too limited by the styling options offered by the GUI, \
you can refine the result by writing python code. Anything you write here is either evaluated within top level namespace or \
supposed to be a method of a matplotlib.Axes object which corresponds to the current graph. Consult the matplotlib \
API reference for valid expressions. The python code will overwrite the settings you made above.'''
info = '\n'.join(['# ' + q for q in textwrap.wrap(info, 70)])

class Interactor:
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.__cmds = []

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

        self.view.Bind(wx.EVT_UPDATE_UI, self.OnIdle)
        self.view.Bind(wx.EVT_TIMER, self.OnTimer)

        txtinput = ['txt_title','spn_legend_fontsize','spn_legend_position',
                    'spn_fontsize',
                    ]
        spins = ['spn_bottom','spn_top','spn_left','spn_right',
                 'spn_hspace','spn_wspace',
                 ]

        for ctrl in txtinput:
            if ctrl.find('spn') == 0:
                getattr(self.view, ctrl).Bind(wx.EVT_SPINCTRL, self.OnUpdateSelected)
            else:
                getattr(self.view, ctrl).Bind(wx.EVT_KILL_FOCUS, self.OnUpdateSelected)
            getattr(self.view, ctrl).Bind(wx.EVT_TEXT_ENTER, self.OnUpdateSelected)

        for ctrl in spins:
            #getattr(self.view, ctrl).Bind(wx.EVT_TEXT_ENTER, self.OnAdjustPlot)
            getattr(self.view, ctrl).Bind(wx.EVT_SPINCTRLDOUBLE, self.OnAdjustPlot)
            #getattr(self.view, ctrl).Bind(wx.EVT_MOUSEWHEEL, self.OnIgnore)


        self.view.chk_legend_frameon.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)
        self.view.chk_legend.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)
        #self.view.btn_example.Bind(wx.EVT_BUTTON, self.OnExample)

        self.view.spn_width.Bind(wx.EVT_SPINCTRLDOUBLE, self.OnChangeSize)
        self.view.spn_height.Bind(wx.EVT_SPINCTRLDOUBLE, self.OnChangeSize)

        self.view.btn_ok.Bind(wx.EVT_BUTTON, self.OnSave)
        self.view.btn_cancel.Bind(wx.EVT_BUTTON, self.OnCancel)

        self.view.plot_view.btn_export_code.Bind(wx.EVT_BUTTON, self.OnExportCode)
        self.view.plot_view.btn_export_figure.Bind(wx.EVT_BUTTON, self.OnExportFigure)

        self.view.plot_layout.ch_rows.Bind(wx.EVT_CHOICE, self.OnShape)
        self.view.plot_layout.ch_cols.Bind(wx.EVT_CHOICE, self.OnShape)

        self.view.plot_layout.Bind(wx.EVT_CHOICE, self.OnSelectPlot)

        self.view.plot_layout.pop.Bind(EVT_RECT_SELECT, self.OnSelectGridPosition)

        self.view.plot_layout.pop.Bind(EVT_RECT_REORDER, self.OnReorderPlots)

        Publisher.subscribe(self.pubOnRedraw, (self.view.instid, 'lineattrs','changed'))
        Publisher.subscribe(self.pubOnRedraw, (self.view.instid, 'axesattrs','changed'))

    def pubOnRedraw(self):
        self.controller.redraw(update_selected=True, force=True)

    def OnReorderPlots(self, evt):
        evt.Skip()
        wx.CallLater(200, self.controller.new_order, evt.swap)

    def OnSelectGridPosition(self, evt):
        evt.Skip()
        self.controller.select_gridposition(evt.pos)

    def OnSelectPlot(self, evt):
        evt.Skip()
        src = evt.GetEventObject().GetName()
        if src == 'pri':
            wx.CallLater(200, self.controller.select_plot,
                         self.view.plot_layout.ch_plot_pri.GetClientData(self.view.plot_layout.ch_plot_pri.Selection),
                         self.view.plot_layout.selection)
        elif src == 'sec':
            wx.CallLater(200, self.controller.plot_add_secondary,
                         self.view.plot_layout.ch_plot_sec.GetClientData(self.view.plot_layout.ch_plot_sec.Selection),
                         self.view.plot_layout.selection)

    def OnShape(self, evt):
        evt.Skip()
        wx.CallLater(200, self.controller.new_shape, (self.view.plot_layout.ch_rows.Selection+1,self.view.plot_layout.ch_cols.Selection+1))

    def OnIgnore(self, evt):
        pass

    def OnSave(self, evt):
        Publisher.sendMessage((self.view.instid, 'figure','save'))

    def OnCancel(self, evt):
        Publisher.sendMessage((self.view.instid, 'figure','discard'))

    def OnExportCode(self, evt):
        self.view.copy2clipboard()
        wx.MessageBox('copied to clipboard')
        #wx.MessageBox('sorry','not yet implemented')

    def OnExportFigure(self, evt):
        dlg = wx.FileDialog(self.view.plot_view, "Choose file format and path", "", "",
                                       "PDF (*.pdf)|*.pdf|PNG (*.png)|*.png", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            base,ext = os.path.splitext(dlg.GetPath())
            if ext.lower() == '.png':
                dpidlg = wx.TextEntryDialog(self.view.plot_view, 'Specify bitmap resolution in dots per inch', 'Export PNG')
                dpidlg.SetValue('90')
                #dpidlg.SetMaxLength(3)
                if dpidlg.ShowModal() == wx.ID_OK:
                    dpi = int(dpidlg.GetValue())
                    self.view.figure.savefig(dlg.GetPath(), dpi=dpi)
            else:
                self.view.figure.savefig(dlg.GetPath())

    def OnTimer(self, evt):
        self.controller.redraw(*self.view._redraw)

    def OnIdle(self, evt):
        #self.view.btn_example.Enable(len(self.view.editor.GetText().strip()) == 0)
        if self.view.plot_view.canvas.needs_update:
            self.view.plot_view.canvas.Refresh()

        if hasattr(self.view, '_redraw_requested') and self.view._redraw_requested is not None:
            update,force = self.view._redraw_requested
            self.view._redraw_requested = None
            self.controller.redraw(update,force)

    def OnChangeSize(self, evt):
        self.controller.resize_frame()
        #wx.CallLater(200, self.controller.resize_frame)

    def OnAdjustPlot(self, evt):
        name = evt.GetEventObject().GetName()
        kwargs = {name:evt.GetEventObject().GetValue()}
        self.controller.model.update_from_view(self.view)
        self.view.figure.subplots_adjust(**kwargs)
        self.controller.redraw()

    def OnUpdateSelected(self, evt):
        obj = evt.GetEventObject()

        obj.Validate()
        self.controller.update_model()
        self.controller.redraw(update_selected=True)
        #wx.CallLater(200, self.__cmds.append,('redraw', [], {'update_selected':True}))
        if evt.EventType != wx.EVT_TEXT_ENTER.typeId:
            evt.Skip()

    def OnClose(self, evt):
        dlg = wx.MessageDialog(self.view, 'All changes will be lost.','Are you sure?',wx.YES_NO|wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            Publisher.sendMessage((self.view.instid, 'figure','discard'))
