##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

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
from wx.lib.pubsub import pub as Publisher

import numpy as N

from peak_o_mat import module

class EditMixin(listmix.TextEditMixin):
    def __init__(self, *args, **kwargs):
        listmix.TextEditMixin.__init__(self, *args, **kwargs)
        self.Unbind(wx.EVT_LEFT_DOWN)

class TrafoListCtrl(wx.ListCtrl,
                    listmix.ListCtrlAutoWidthMixin,
                    EditMixin,
                    listmix.CheckListCtrlMixin):

    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.Populate()
        EditMixin.__init__(self)
        listmix.CheckListCtrlMixin.__init__(self)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEdit)
        
    def OnBeginEdit(self, evt):
        if evt.GetColumn() == 0:
            evt.Veto()
        
    def Populate(self):
        self.InsertColumn(0, "axis")
        self.InsertColumn(1, "trafo")
        self.InsertColumn(2, "comment")

        self.SetColumnWidth(0, 50)
        self.SetColumnWidth(1, 300)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE)

    def Insert(self, data):
        index = self.InsertStringItem(sys.maxint, data[0])
        for col in range(3):
            self.SetStringItem(index, col, data[col])
        self.SetItemData(index, index)
        if not data[3]:
            self.CheckItem(index)

class Module(module.Module):
    title = 'Set info'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)

    def init(self):
        self._current_selection = 0
        self._updating = False
        self._selected = False
        self.xmlres.AttachUnknownControl('xrc_lc_trafo', TrafoListCtrl(self.panel, -1,
                                                                       style=wx.LC_REPORT))
        self.Bind(wx.EVT_BUTTON, self.OnRemoveTrafo, self.xrc_btn_trafo_remove)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndEdit)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.Bind(wx.EVT_BUTTON, self.OnRemoveMask, self.xrc_btn_mask_remove)
        self.xrc_lc_trafo.OnCheckItem = self.OnCheckItem
        
        Publisher.subscribe(self.OnSetinfoUpdate, ('setinfo','update'))

    def OnSetinfoUpdate(self, msg):
        if self._selected and not self._updating:
            self.update()

    def OnCheckItem(self, idx, state):
        if not self._updating:
            set = self.controller.active_set
            trafo = list(set.trafo[idx])
            trafo[3] = not state
            set.trafo[idx] = tuple(trafo)
            wx.CallAfter(self.controller.plot)
    
    def OnRemoveMask(self, evt):
        self.controller.active_set.mask = None
        self.controller.update_plot()
        
    def OnItemSelected(self, evt):
        self._current_selection = evt.GetIndex()
        set = self.controller.active_set
        if set is not None:
            self.xrc_btn_trafo_remove.Enable(len(set.trafo) > 0)

    def OnEndEdit(self, evt):
        col,idx = evt.GetColumn(),evt.GetIndex()
        label = evt.GetLabel()
        set = self.controller.active_set
        trafo = list(set.trafo[idx])
        trafo[col] = label
        set.trafo[idx] = tuple(trafo)
        wx.CallAfter(self.controller.plot)
        
    def OnRemoveTrafo(self, evt):
        set = self.controller.active_set
        if set is not None:
            set.trafo.pop(self._current_selection)
            self.update()
            wx.CallAfter(self.controller.plot)

    def page_changed(self, state):
        self._selected = state
        if state:
            self.update()

    def selection_changed(self):
        set = self.controller.active_set
        if self._selected:
            if set is not None:
                self.panel.Enable()
                self.update()
            else:
                self.panel.Disable()

    def update(self):
        self._updating = True
        set = self.controller.active_set
        if set is not None:
            self._current_selection = 0
            self.xrc_lc_trafo.DeleteAllItems()
            self.xrc_btn_trafo_remove.Enable(len(set.trafo) > 0)
            for data in set.trafo:
                self.xrc_lc_trafo.Insert(data)
            self.xrc_lab_name.SetLabel('set name: %s'%(set.name))
            self.xrc_lab_points.SetLabel('%d points, %d masked'%(len(set.data[0]), len(N.compress(set.mask == 1, set.mask))))
        self._updating = False

