__author__ = 'ck'

import wx
import wx.dataview as dv
from wx.lib.pubsub import pub as Publisher
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

        self.view.Bind(wx.EVT_BUTTON, self.OnUpdateSelected, self.view.btn_runcode)
        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

        self.view.Bind(wx.EVT_UPDATE_UI, self.OnIdle)
        self.view.Bind(wx.EVT_TIMER, self.OnTimer)

        self.view.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnLineStyleUpdate)

        txtinput = ['txt_xlabel','txt_ylabel','txt_title','spn_legend_fontsize','spn_legend_position',
                    'spn_fontsize',
                    'txt_xrng_min','txt_xrng_max','txt_yrng_min','txt_yrng_max',
                    #'txt_xtick_minor','txt_xtick_major','txt_ytick_minor','txt_ytick_major',
                    'txt_symlogthreshx','txt_symlogthreshy'
                    ]
        spins = ['spn_bottom','spn_top','spn_left','spn_right',
                 'spn_hspace','spn_wspace',
                 ]
        choices = ['cmb_scalex', 'cmb_scaley',
                   'cho_xtickdir','cho_ytickdir','cho_xlabel_pos','cho_ylabel_pos',
                   #'cho_xticks_prec','cho_yticks_prec'
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

        for ctrl in choices:
            getattr(self.view, ctrl).Bind(wx.EVT_CHOICE, self.OnUpdateSelected)

        #self.view.chk_xtick_custom.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)
        #self.view.chk_ytick_custom.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)

        self.view.chk_xticks_hide.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)
        self.view.chk_yticks_hide.Bind(wx.EVT_CHECKBOX, self.OnUpdateSelected)

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

        self.view.plot_layout.ch_plot.Bind(wx.EVT_CHOICE, self.OnSelectPlot)

        self.view.plot_layout.pop.Bind(EVT_RECT_SELECT, self.OnSelectGridPosition)

        self.view.plot_layout.pop.Bind(EVT_RECT_REORDER, self.OnReorderPlots)

    def OnReorderPlots(self, evt):
        evt.Skip()
        wx.CallLater(200, self.controller.new_order, evt.swap)

    def OnSelectGridPosition(self, evt):
        evt.Skip()
        self.controller.select_gridposition(evt.pos)

    def OnSelectPlot(self, evt):
        evt.Skip()
        wx.CallLater(200, self.controller.select_plot,
                     self.view.plot_layout.ch_plot.GetClientData(self.view.plot_layout.ch_plot.Selection),
                     self.view.plot_layout.selection)

    def OnShape(self, evt):
        evt.Skip()
        wx.CallLater(200, self.controller.new_shape, (self.view.plot_layout.ch_rows.Selection+1,self.view.plot_layout.ch_cols.Selection+1))

    def OnIgnore(self, evt):
        pass

    def OnSave(self, evt):
        Publisher.sendMessage((self.view.id, 'figure','save'))

    def OnCancel(self, evt):
        Publisher.sendMessage((self.view.id, 'figure','discard'))

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


    def OnExample(self, evt):
        #xlim = self.view.ax.get_xlim()
        #ylim = self.view.ax.get_ylim()
        #xpos = (xlim[1]+xlim[0])/2
        #ypos = (ylim[1]+ylim[0])/2
        #xticks = self.view.ax.get_xticks()
        #xticks = ','.join(str(q) for q in sample(xticks, len(xticks)/2))
        text = '''

# For example:

print 'peak-o-mat rocks!'
annotate('peak-o-mat rocks!', xy=({xpos:.2g},{ypos:.2g}), fontsize=10)
set_xticks([{xticks}])
annotate('look at this', color='red', xy=(0.3,0.8), xytext=(0.2,0.6), xycoords='axes fraction', arrowprops={{'arrowstyle':'->'}})
'''.format(xpos=xpos, ypos=ypos, xticks=xticks)

        self.view.editor.SetText(info + text)

    def OnTimer(self, evt):
        print(self.view._redraw)
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
        #self.view.figure.canvas.draw()
        self.controller.redraw()
        #self.controller.plot()

    def OnLineStyleUpdate(self, evt):
        self.controller.update_model()
        self.controller.redraw(update_selected=True, force=True)
        #wx.CallLater(200, self.__cmds.append, ('redraw',[],{'update_selected':True, 'force':True}))
        #wx.CallAfter(self.controller.redraw, update_selected=True, force=True)

    def OnUpdateSelected(self, evt):
        obj = evt.GetEventObject()
        if obj.Name == 'scalex':
            self.view.txt_symlogthreshx.Enable(obj.Selection == 2)
            #self.view.lab_symlogthreshx.Enable(obj.Selection == 2) # results invisible on macOS
        if obj.Name == 'scaley':
            self.view.txt_symlogthreshy.Enable(obj.Selection == 2)
            #self.view.lab_symlogthreshy.Enable(obj.Selection == 2) # results invisible on macOS

        obj.Validate()
        self.controller.update_model()
        self.controller.redraw(update_selected=True)
        #wx.CallLater(200, self.__cmds.append,('redraw', [], {'update_selected':True}))
        if evt.EventType != wx.EVT_TEXT_ENTER.typeId:
            evt.Skip()

    def OnClose(self, evt):
        dlg = wx.MessageDialog(self.view, 'All changes will be lost.','Are you sure?',wx.YES_NO|wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            Publisher.sendMessage((self.view.id, 'figure','discard'))
