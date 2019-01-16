__author__ = 'kristukat'

import wx
import wx.dataview as dv

class Interactor:

    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        self.view.tree.Bind(dv.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.OnContextMenu)
        self.view.tree.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelectionChanged)
        self.view.tree.Bind(dv.EVT_DATAVIEW_ITEM_START_EDITING, self.OnStartEditing)
        self.view.tree.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone)

        self.view.btn_add.Bind(wx.EVT_BUTTON, self.OnAdd)
        self.view.btn_delete.Bind(wx.EVT_BUTTON, self.OnDelete)

        self.view.Bind(wx.EVT_IDLE, self.OnIdle)

    def OnEditingDone(self, evt):
        print(dir(self.view.tree.Selection))
        obj = self.controller.model.ItemToObject(self.view.tree.Selection)
        if not self.controller.ask_for_rename(obj):
            evt.Veto()
        else:
            evt.Skip()

    def OnStartEditing(self, evt):
        obj = self.controller.model.ItemToObject(self.view.tree.Selection)
        if not obj.isentry:
            evt.Veto()
        else:
            evt.Skip()

    def OnAdd(self, evt):
        self.controller.add_entry()

    def OnDelete(self, evt):
        self.controller.delete_entry()

    def OnIdle(self, evt):
        self.view.Freeze()
        sel = self.view.tree.HasSelection()
        if sel:
            obj = self.controller.model.ItemToObject(self.view.tree.Selection)
            self.view.btn_add.Enable(obj.isentry or not obj.toplevel)
            self.view.btn_delete.Enable(obj.isentry)
        else:
            self.view.btn_add.Enable(sel)
            self.view.btn_delete.Enable(sel)
        self.view.Thaw()

    def OnSelectionChanged(self, evt):
        ctrl = evt.GetEventObject()
        print(ctrl.HasSelection())

        #print self.controller.model.ItemToObject(ctrl.Selection).label

    def OnContextMenu(self, event):
        event.Skip()
        obj = self.controller.model.ItemToObject(self.view.tree.Selection)

        if not obj.isentry:
            return

        if not hasattr(self, "_id1"):
            self._id1 = wx.NewId()
            self._id2 = wx.NewId()
            self.view.Bind(wx.EVT_MENU, self.OnTransfer, id=self._id1)
            self.view.Bind(wx.EVT_MENU, self.OnRename, id=self._id2)

        islocal = obj.type[0] == 'local'

        # make a menu
        menu = wx.Menu()
        if islocal:
            menu.Append(self._id1, "Embed in project file")
        else:
            menu.Append(self._id1, "Move to local storage")
        menu.Append(self._id2, "Rename")

        self.view.split.PopupMenu(menu)
        menu.Destroy()

    def OnTransfer(self, evt):
        print(evt)

    def OnRename(self, evt):
        self.view.tree.EditItem(self.view.tree.Selection, self.view.tree.GetColumn(0))


