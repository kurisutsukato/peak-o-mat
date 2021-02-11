##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later versionp.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""\
Setinfo module
"""

import sys
import wx
import  wx.lib.mixins.listctrl  as  listmix
from pubsub import pub

import numpy as np

from .. import module

class EditMixin(listmix.TextEditMixin):
    def __init__(self, *args, **kwargs):
        listmix.TextEditMixin.__init__(self, *args, **kwargs)
        self.Unbind(wx.EVT_LEFT_DOWN)

class TrafoListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, EditMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.init_ctrl()
        EditMixin.__init__(self)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEdit)
        self.EnableCheckBoxes(True)

    def init_ctrl(self):
        self.InsertColumn(0, "")
        self.InsertColumn(1, "Axis")
        self.InsertColumn(2, "Transformation")
        self.InsertColumn(3, "Comment")

        self.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.SetColumnWidth(1, 50)
        self.SetColumnWidth(2, 300)
        self.SetColumnWidth(3, wx.LIST_AUTOSIZE)

    def Insert(self, data):
        #TODO: sys.maxsize is zu gross, daher 20000

        index = self.InsertItem(20000, data[0])
        for col in range(3):
            self.SetItem(index, col+1, data[col])
        self.SetItemData(index, index)
        self.CheckItem(index, not data[3])

    def OnBeginEdit(self, evt):
        if evt.GetColumn() in [0, 1]:
            evt.Veto()

class XRCModule(module.XRCModule):
    title = 'Set info'
    update_in_background = True

    def __init__(self, *args):
        module.XRCModule.__init__(self, __file__, *args)

    def init(self):
        self._current_selection = 0
        self._updating = False
        self.xmlres.AttachUnknownControl('xrc_lc_trafo', TrafoListCtrl(self.view, -1,
                                                                       style=wx.LC_REPORT))
        self.view.Bind(wx.EVT_BUTTON, self.OnRemoveTrafo, self.xrc_btn_trafo_remove)
        self.view.Bind(wx.EVT_BUTTON, self.OnRemoveAllTrafos, self.xrc_btn_trafo_remove_all)
        self.view.Bind(wx.EVT_BUTTON, self.OnTrafosMakePermanent, self.xrc_btn_trafo_permanent)
        self.view.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndEdit)
        self.view.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda evt: self.OnItemSelected(evt, True))
        self.view.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda evt: self.OnItemSelected(evt, False))
        self.view.Bind(wx.EVT_LIST_ITEM_CHECKED, lambda evt: self.OnItemChecked(evt, True))
        self.view.Bind(wx.EVT_LIST_ITEM_UNCHECKED, lambda evt: self.OnItemChecked(evt, False))

        self.view.Bind(wx.EVT_BUTTON, self.OnRemoveMask, self.xrc_btn_mask_remove)
        self.view.Bind(wx.EVT_BUTTON, self.OnMaskMakePermanent, self.xrc_btn_mask_permanent)
        
        self.xrc_btn_trafo_remove.Enable(False)
        pub.subscribe(self.OnSetinfoUpdate, (self.instid, 'setattrchanged'))

    def OnSetinfoUpdate(self):
        if not self._updating:
            self.update()

    def OnItemChecked(self, evt, state):
        if not self._updating:
            idx = evt.GetIndex()
            ds = self.controller.active_set
            trafo = list(ds.trafo[idx])
            trafo[3] = not state
            ds.trafo[idx] = tuple(trafo)
            #TODO: replace by message
            wx.CallAfter(self.controller.plot)

    def OnMaskMakePermanent(self, evt):
        self.controller.active_set.make_mask_permanent()
        self.controller.update_plot()
            
    def OnRemoveMask(self, evt):
        self.controller.active_set.mask = None
        self.controller.update_plot()
        
    def OnItemSelected(self, evt, selected):
        evt.Skip()
        self._current_selection = evt.GetIndex()
        set = self.controller.active_set
        self.xrc_btn_trafo_remove.Enable(set is not None and selected)

    def OnEndEdit(self, evt):
        col,idx = evt.GetColumn(),evt.GetIndex()
        label = evt.GetLabel()
        ds = self.controller.active_set
        trafo = list(ds.trafo[idx])
        trafo[col-1] = label
        ds.trafo[idx] = tuple(trafo)
        #TODO: replace by msg
        self.controller.update_plot()

    def OnTrafosMakePermanent(self, evt):
        self.controller.active_set.make_trafo_permanent()
        self.controller.update_plot()

    def OnRemoveAllTrafos(self, evt):
        ds = self.controller.active_set
        if ds is not None:
            ds.trafo[:] = []
            self.update()
            self.controller.update_plot()
        
    def OnRemoveTrafo(self, evt):
        ds = self.controller.active_set
        if ds is not None:
            ds.trafo.pop(self._current_selection)
            self.update()
            self.controller.update_plot()

    def selection_changed(self):
        set = self.controller.active_set
        if set is not None:
            self.view.Enable()
            self.update()
        else:
            self.view.Disable()
            self.update()

    def update(self):
        self._updating = True
        ds = self.controller.active_set
        if ds is not None:
            self._current_selection = 0
            self.xrc_lc_trafo.DeleteAllItems()

            self.xrc_btn_trafo_remove.Enable(False)

            self.xrc_btn_trafo_remove_all.Enable(len(ds.trafo) > 0)
            self.xrc_btn_trafo_permanent.Enable(len(ds.trafo) > 0)
            
            self.xrc_btn_mask_remove.Enable(np.sometrue(ds.mask))
            self.xrc_btn_mask_permanent.Enable(np.sometrue(ds.mask))
            
            for data in ds.trafo:
                self.xrc_lc_trafo.Insert(data)
            self.xrc_lab_points.SetLabel('%d points, %d masked'%(len(ds.data[0]), len(np.compress(ds.mask == 1, ds.mask))))
        else:
            self.xrc_lc_trafo.DeleteAllItems()

            self.xrc_btn_trafo_remove.Enable(False)

            self.xrc_btn_trafo_remove_all.Enable(False)
            self.xrc_btn_trafo_permanent.Enable(False)

            self.xrc_btn_mask_remove.Enable(False)
            self.xrc_btn_mask_permanent.Enable(False)

            self.xrc_lab_points.SetLabel('')

        self._updating = False

class MayBeCalled(object):
    def __call__(self, *args, **kwargs):
        return None

class Dummy(object):
    def __init__(self, view):
        super(Dummy, self).__init__()
        self.view = view

    def __getattr__(self, attr):
        return MayBeCalled()

    def __setattr__(self, attr, val):
        pass

if __name__ == '__main__':
    app = wx.App()
    f = wx.Frame(None)
    p = wx.Panel(f)
    c = Dummy(f)
    XRCModule(c, '')
    app.MainLoop()