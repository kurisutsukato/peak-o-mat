import wx
import wx.dataview as dv
from uuid import uuid4

from . project import Project, Plot, PlotData

class TreeListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self.data = data

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        mapper = { 0 : 'string',
                   1 : 'string'
                   }
        return mapper[col]

    def GetChildren(self, parent, children):
        if not parent:
            for cont in self.data:
                children.append(self.ObjectToItem(cont))
            return len(self.data)

        node = self.ItemToObject(parent)

        if isinstance(node, Plot):
            for ds in node:
                children.append(self.ObjectToItem(ds))
            return len(node)
        return 0

    def IsContainer(self, item):
        if not item:
            return True
        node = self.ItemToObject(item)
        if isinstance(node, Plot):
            return True
        return False

    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem

        node = self.ItemToObject(item)
        if isinstance(node, Plot):
            return dv.NullDataViewItem
        else:
            for g in self.data:
                try:
                    g.index(node)
                except ValueError:
                    continue
                else:
                    return self.ObjectToItem(g)

    def SetValue(self, value, item, col):
        c = self.ItemToObject(item)
        c.name = value
        return True

    def GetValue(self, item, col):
        node = self.ItemToObject(item)
        if isinstance(node, Plot):
            mapper = { 0 : node.name,
                       1 : '',
                       }
            return mapper[col]

        else:
            mapper = { 0 : node.name,
                       1 : '23'
                       }
            return mapper[col]

class MyFrame(wx.Frame):
    def __init__(self, parent, data):
        wx.Frame.__init__(self, parent, -1, "Table")
        self.selection = None, []
        self._items_dragged = []
        self.current = None

        panel = wx.Panel(self)
                
        dvcTree = dv.DataViewCtrl(panel,style=wx.BORDER_THEME|dv.DV_MULTIPLE)
        self.model = TreeListModel(data)
        dvcTree.AssociateModel(self.model)

        dvcTree.AppendTextColumn("Container",   0, width=130, mode=dv.DATAVIEW_CELL_EDITABLE)
        dvcTree.AppendTextColumn("Element",   1, width=80)

        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_BEGIN_DRAG, self._onDrag)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self._onEndDrag)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP_POSSIBLE, self._onDropPossible)
        dvcTree.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self._onSelect)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_EXPANDED, self._onExpand)
        dvcTree.EnableDragSource(wx.DataFormat(wx.DF_UNICODETEXT))
        dvcTree.EnableDropTarget(wx.DataFormat(wx.DF_UNICODETEXT))
        self.dvcTree = dvcTree

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(dvcTree, 1, wx.EXPAND)
        panel.SetSizer(box)
        self.Layout()

    def _onExpand(self, evt):
        mod = evt.GetModel()
        par = mod.ItemToObject(evt.GetItem())
        par, childs = self.selection
        if par is not None and len(childs) > 0 and mod.ItemToObject(mod.GetParent(mod.ObjectToItem(childs[0]))) == par:
            da = dv.DataViewItemArray()
            if [mod.ItemToObject(q) for q in self.dvcTree.GetSelections()] != self.selection[1]:
                for o in self.selection[1]:
                    da.append(evt.GetModel().ObjectToItem(o))
                self.dvcTree.SetSelections(da)

    def _onSelect(self, evt):
        mod = evt.GetModel()
        selection = [mod.ItemToObject(q) for q in self.dvcTree.GetSelections()]
        parents = [mod.ItemToObject(mod.GetParent(q)).uuid if mod.GetParent(q) != dv.NullDataViewItem else 0 for q in self.dvcTree.GetSelections()]
        if len(set(parents)) > 1:
            darr = dv.DataViewItemArray()
            for i in [mod.ObjectToItem(q) for q in self.selection[1]]:
                darr.append(i)
            self.dvcTree.SetSelections(darr)
        else:
            if len(selection) > 0:
                p = mod.GetParent(mod.ObjectToItem(selection[0]))
                if p == dv.NullDataViewItem:
                    p = None
                else:
                    p = mod.ItemToObject(p)
                self.selection = p, selection

    def _onDropPossible(self, evt):
        item = evt.GetItem()
        mod = evt.GetModel()
        if self.draglevel == 0 and mod.GetParent(item) != dv.NullDataViewItem:
            evt.Veto()

    def _onEndDrag(self, evt):
        if not evt.GetItem().IsOk():
            evt.Veto()
            self._items_dragged = None
            return
        if self._items_dragged is None: #happens when multiple items are dragged on OSX
            return
        sourceparent, sourcechilds = self._items_dragged
        self._items_dragged = None
        mod = evt.GetModel()
        targetitem = mod.ItemToObject(evt.GetItem())
        if not isinstance(targetitem, Plot):
            # dropped on child
            targetparent = mod.ItemToObject(mod.GetParent(evt.GetItem()))
            if targetparent != sourceparent:
                self.dvcTree.SetSelections(dv.DataViewItemArray())
                for c in sourcechilds:
                    sourceparent.remove(c)
                    targetparent.append(c)
                dvia = dv.DataViewItemArray()
                for c in sourcechilds:
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
                self.dvcTree.SetSelections(dvia)
        else:
            # dropped on parent node
            self.dvcTree.SetSelections(dv.DataViewItemArray())
            if sourceparent is None:
                # dropping a parent node
                for c in sourcechilds:
                    mod.data.remove(c)
                    mod.data.append(c)
            else:
                # dropping childs
                for c in sourcechilds:
                    sourceparent.remove(c)
                    targetitem.append(c)
            dvia = dv.DataViewItemArray()
            for c in sourcechilds:
                dvia.append(mod.ObjectToItem(c))
            mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
            mod.ItemsAdded(mod.ObjectToItem(targetitem), dvia)
            self.dvcTree.SetSelections(dvia)

    def _onDrag(self, evt):
        evt.SetDataObject(wx.TextDataObject('this text will be recevied by drop targets that accept text'))
        evt.SetDragFlags(wx.Drag_AllowMove)
        mod = evt.GetModel()
        self.draglevel = int(mod.GetParent(evt.GetItem()) != dv.NullDataViewItem)
        parent, childs = self.selection
        if len(childs) is None:
            self._items_dragged = parent, mod.ItemToObject(evt.GetItem())
        elif mod.ItemToObject(evt.GetItem()) not in childs:
            par = mod.GetParent(evt.GetItem())
            if par == dv.NullDataViewItem:
                parent = None
            else:
                parent = mod.ItemToObject(par)
            self._items_dragged = parent, [mod.ItemToObject(evt.GetItem())]
        else:
            self._items_dragged = parent, childs
        
if __name__ == "__main__":
    prj = Project()
    import os
    print(os.path.abspath(os.curdir))
    prj.load('example.lpj')
    for p in prj:
        for s in p:
            print(s)
    app = wx.App()
    f = MyFrame(None, prj)
    f.Show()
    app.MainLoop()
