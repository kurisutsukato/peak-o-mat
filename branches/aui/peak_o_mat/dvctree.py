import wx
import wx.dataview as dv
from uuid import uuid4
import sys

from . project import Project, Plot, PlotData

class TreeListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self.data = data
        self._selection = []

    @property
    def selection(self):
        try:
            item = self.ObjectToItem(self._selection[0])
        except IndexError:
            print('index error')
            return None, []
        else:
            parent = self.GetParent(item)
            if parent == dv.NullDataViewItem:
                return None, self._selection
            else:
                return self.ItemToObject(parent), self._selection

    @selection.setter
    def selection(self, newsel):
        self._selection = newsel

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        mapper = { 0 : 'string',
                   1 : 'string'
                   }
        return mapper[col]

    def GetChildren(self, parent, children):
        #try:
        #    print('requesting children of {}'.format(self.ItemToObject(parent)))
        #except TypeError:
        #    print('requesting children of root')
        if not parent:
            for cont in self.data:
                children.append(self.ObjectToItem(cont))
            return len(self.data)

        node = self.ItemToObject(parent)
        if isinstance(node, Plot):
            for ds in node:
                children.append(self.ObjectToItem(ds))
            return len(children)
        raise Exception('should not happen')
        return 0

    def IsContainer(self, item):
        try:
            node = self.ItemToObject(item)
        except TypeError:
            return True
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
                if node in g:
                    return self.ObjectToItem(g)
            print('nicht auffindbar', node)
        raise Exception('should not happen', node, item)
        return dv.NullDataViewItem

    def SetValue(self, value, item, col):
        c = self.ItemToObject(item)
        c.name = value
        return True

    def GetAttr(self, item, col, attr):
        return False

        if self.ItemToObject(item).modified:
            attr.SetColour(wx.RED)
            return True
        else:
            return False

    def GetValue(self, item, col):
        node = self.ItemToObject(item)

        if isinstance(node, Plot):
            num = self.data.index(node)
            mapper = { 0 : 'p{} {}'.format(num, node.name),
                       1 : 'test',
                       }
            return mapper[col]
        else:
            cont, elem = self.data.find_by_uuid(node.uuid)
            num = cont.index(elem)
            mapper = { 0 : 's{} {}'.format(num, node.name),
                       1 : 'test'
                       }
            return mapper[col]

    def Cleared(self, dvctrl=None):
        if dvctrl is not None:
            self.save_state(dvctrl)
            super(TreeListModel,self).Cleared()
            self.restore_state(dvctrl)
        else:
            super(TreeListModel,self).Cleared()

    def save_state(self, dvctrl):
        iarr = dv.DataViewItemArray()
        self.GetChildren(None, iarr)
        self._expstate = dict([(self.ItemToObject(q).uuid,dvctrl.IsExpanded(q)) for q in iarr])

    def restore_state(self, dvctrl):
        for k,v in self._expstate.items():
            if v:
                dvctrl.Expand(self.ObjectToItem(self.data[k]))
            else:
                dvctrl.Collapse(self.ObjectToItem(self.data[k]))

class MyFrame(wx.Frame):
    def __init__(self, parent, prj):
        wx.Frame.__init__(self, parent, -1, "Table", size=(-1,400))
        self.selection = [None, []]
        self._dragging = False
        self._draglevel = 0
        self._items_dragged = []
        self._timer = wx.Timer(self)
        self._scrolllines = 0

        panel = wx.Panel(self)
        dvcTree = dv.DataViewCtrl(panel,style=wx.BORDER_THEME|dv.DV_MULTIPLE|dv.DV_NO_HEADER)
        self.model = TreeListModel(prj)
        dvcTree.AssociateModel(self.model)

        dvcTree.AppendTextColumn("Container",   0, width=400)
        dvcTree.AppendTextColumn("Element",   1, width=0, mode=dv.DATAVIEW_CELL_EDITABLE)

        dvcTree.Bind(wx.EVT_KILL_FOCUS, self.on_focuskill)

        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_BEGIN_DRAG, self.on_drag)
        if sys.platform == 'darwin':
            dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddragosx)
        elif sys.platform == 'linux':
            dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddraglinux)
        else:
            dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddrag)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP_POSSIBLE, self.on_droppossible)
        dvcTree.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.on_select)
        if sys.platform != 'linux':
            dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_EXPANDED, self.on_expand)
        panel.Bind(dv.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_menu, dvcTree)

        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_activated)

        self.Bind(wx.EVT_TIMER, self.on_timer)

        dvcTree.EnableDragSource(wx.DataFormat(wx.DF_UNICODETEXT))
        dvcTree.EnableDropTarget(wx.DataFormat(wx.DF_UNICODETEXT))

        self.dvcTree = dvcTree
        self.btn_clear = wx.Button(panel, label='Clear')
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(dvcTree, 1, wx.ALL|wx.EXPAND,10)
        box.Add(self.btn_clear, 0, wx.EXPAND)
        panel.SetSizer(box)
        self.Layout()

        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.panel = panel

    def on_menu(self, evt):
        print(evt.GetEventObject(),evt.GetModel())
        print('menu')
        menu = wx.Menu()
        # Show how to put an icon in the menu
        menu.Append(-1, 'Remove trafo')
        menu.Append(-1, 'Remove model')
        self.PopupMenu(menu)
        menu.Destroy()

    def on_endedit(self, evt):
        obj = evt.GetEventObject()
        obj.Unbind(wx.EVT_TEXT_ENTER)
        obj.Unbind(wx.EVT_KILL_FOCUS)
        node = self.model.data[self._obj_edited]
        node.name = obj.GetValue()
        self.dvcTree.SetFocus()
        wx.CallAfter(obj.Destroy)

    def on_activated(self, evt):
        rect = self.dvcTree.GetItemRect(evt.GetItem(), self.dvcTree.GetColumn(0))
        x, y, w, h = rect
        parent = self.dvcTree
        W, H = self.dvcTree.GetVirtualSize()
        w = W - x-2
        if sys.platform == 'darwin':
            y -= 0
            h += 4
        elif sys.platform == 'linux':
            X,Y = self.dvcTree.GetPosition()
            h += 2
            x += X
            y += Y
            parent = self.panel
        txt = wx.TextCtrl(parent, pos=(x,y), size=(w,h), style=wx.TE_PROCESS_ENTER)
        obj = evt.GetModel().ItemToObject(evt.GetItem())
        lab = obj.name
        txt.SetValue(lab)
        #self.dvcTree.Refresh(True, rect)
        txt.SetFocus()
        txt.SelectAll()
        txt.Bind(wx.EVT_TEXT_ENTER, self.on_endedit)
        txt.Bind(wx.EVT_KILL_FOCUS, self.on_endedit)
        self._obj_edited = obj.uuid

    def on_clear(self, evt):
        mod = self.dvcTree.GetModel()
        mod.Cleared()

    def _select(self, dvia, silent=False):
        if silent:
            self.dvcTree.SetEvtHandlerEnabled(False)
            self.dvcTree.SetSelections(dvia)
            self.dvcTree.SetEvtHandlerEnabled(True)
        else:
            self.dvcTree.SetSelections(dvia)

    def on_focuskill(self, evt):
        print('focus lost')
        evt.Skip()
        self._dragging = 0


    def on_expand(self, evt):
        mod = evt.GetModel()
        par = mod.ItemToObject(evt.GetItem())
        selpar, childs = mod.selection
        if par != selpar:
            return
        print('on expand selection',par,mod.selection)
        try:
            if par is not None and len(childs) > 0 and mod.ItemToObject(mod.GetParent(mod.ObjectToItem(childs[0]))) == par:
                dvia = dv.DataViewItemArray()
                if [mod.ItemToObject(q) for q in self.dvcTree.GetSelections()] != mod.selection[1]:
                    for o in mod.selection[1]:
                        dvia.append(evt.GetModel().ObjectToItem(o))
                    self._select(dvia, True)
        except:
            raise

    def on_select(self, evt):
        #print('select',len(self.dvcTree.GetSelections()))
        mod = evt.GetModel()
        selection = [mod.ItemToObject(q) for q in self.dvcTree.GetSelections()]
        parents = [mod.ItemToObject(mod.GetParent(q)).uuid if mod.GetParent(q) != dv.NullDataViewItem else 0 for q in self.dvcTree.GetSelections()]
        if len(set(parents)) > 1 or (len(selection) > 1 and 0 in parents):
            darr = dv.DataViewItemArray()
            for i in [mod.ObjectToItem(q) for q in mod.selection[1]]:
                darr.append(i)
            self._select(darr, False)
        else:
            if len(selection) > 0:
                mod.selection = selection

    def on_timer(self, evt):
        self.dvcTree.ScrollLines(self._scrolllines)

    def on_droppossible(self, evt):
        mod = evt.GetModel()
        targetitem = evt.GetItem()

        if not self._dragging or self._draglevel == 0 and mod.GetParent(targetitem) != dv.NullDataViewItem:
            # does not have consequences on linux
            evt.Veto()

        if sys.platform not in ['darwin','linux']:
            mposx, mposy = wx.GetMousePosition()
            cposx, cposy = self.dvcTree.ScreenToClient((mposx, mposy))

            item, col = self.dvcTree.HitTest((cposx,cposy))
            if item == self.dvcTree.GetTopItem() and \
                    self.dvcTree.GetScrollPos(wx.VERTICAL) != 0:
                self._scrolllines = -1
                self._timer.Start(30, wx.TIMERon_e_shot)
            elif self.dvcTree.GetScrollPos(wx.VERTICAL) + self.dvcTree.GetScrollThumb(wx.VERTICAL) != self.dvcTree.GetScrollRange(wx.VERTICAL) \
                    and self.dvcTree.ClientSize[1] - cposy < 10:
                self._scrolllines = +1
                self._timer.Start(30, wx.TIMERon_e_shot)

    def on_enddrag(self, evt):
        print('end drag')
        self._dragging -= 1
        obj = wx.TextDataObject()
        obj.SetData(wx.DataFormat(wx.DF_UNICODETEXT), evt.GetDataBuffer())

        mod = evt.GetModel()
        if not evt.GetItem().IsOk():
            # happens when dropping on root
            targetobj = None
        else:
            targetobj = mod.ItemToObject(evt.GetItem())

        sourceparent, sourceobjects = self._items_dragged
        self._items_dragged = None

        try:
            targetparent = mod.ItemToObject(mod.GetParent(evt.GetItem()))
        except:
            targetparent = None

        print('targetobj is',targetobj.__class__)
        if targetobj is None and sourceparent is None:
            # container dropped on root --> move to last position
            print('container on root {}->{}'.format(sourceobjects,targetobj))
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                data.remove(c)
                data.append(c)
                dvia.append(mod.ObjectToItem(c))
            parent = mod.GetParent(mod.ObjectToItem(c))
            mod.ItemsDeleted(parent, dvia)
            mod.ItemsAdded(parent, dvia)
            mod.Cleared(self.dvcTree)
        elif targetobj is None:
            print('child on root {}->{}'.format(sourceobjects,targetobj))
            # drop child on root --> add to last container
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                sourceparent.remove(c)
                data[-1].append(c)
                dvia.append(mod.ObjectToItem(c))
            self.dvcTree.Expand(mod.ObjectToItem(data[-1]))
            mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
            mod.ItemsAdded(mod.ObjectToItem(data[-1]), dvia)
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if targetparent != sourceparent:
                print('drop child on child {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
            else:
                print('drop child on child {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
        else:
            # dropping containers on containers
            # sourceobjects should be a list with a single item, but, well...
            if sourceparent is None:
                print('container on container {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    data.remove(c)
                    n = data.index(targetobj)
                    data.insert(n, c)
                    item = mod.ObjectToItem(c)
                    dvia.append(item)
                mod.ItemsDeleted(dv.NullDataViewItem, dvia)
                mod.ItemsAdded(dv.NullDataViewItem, dvia)
            else:
                # dropping childs on containers
                dvia = dv.DataViewItemArray()
                print('child on container {}->{}'.format(sourceobjects,targetobj))
                for c in sourceobjects:
                    sourceparent.remove(c)
                    targetobj.append(c)
                    item = mod.ObjectToItem(c)
                    dvia.append(item)
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetobj), dvia)

        darr = dv.DataViewItemArray()
        for i in [mod.ObjectToItem(q) for q in mod.selection[1]]:
            darr.append(i)
        self._select(darr)

    def on_enddraglinux(self, evt):
        print('end drag')
        self._dragging -= 1

        obj = wx.DataObjectSimple()
        obj.SetData(evt.GetDataBuffer())

        item = evt.GetItem()
        mod = evt.GetModel()

        selection = mod.selection[1]

        if self._draglevel == 0 and mod.GetParent(item) != dv.NullDataViewItem:
            #dropped container on child --> forbidden
            return

        mod.save_state(self.dvcTree)

        if not evt.GetItem().IsOk():
            # happens when dropping on root
            targetobj = None
            print('   targetobj None')
        else:
            targetobj = mod.ItemToObject(evt.GetItem())

        sourceparent, sourceobjects = self._items_dragged
        self._items_dragged = None

        try:
            targetparent = mod.ItemToObject(mod.GetParent(evt.GetItem()))
        except:
            targetparent = None

        print('targetobj is',targetobj.__class__)
        if targetobj is None and sourceparent is None:
            # container dropped on root --> move to last position
            print('container on root {}->{}'.format(sourceobjects,targetobj))
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                data.remove(c)
                data.append(c)
                dvia.append(mod.ObjectToItem(c))
            parent = mod.GetParent(mod.ObjectToItem(c))
            mod.ItemsDeleted(parent, dvia)
            mod.ItemsAdded(parent, dvia)
            mod.Cleared(self.dvcTree)
        elif targetobj is None:
            print('child on root {}->{}'.format(sourceobjects,targetobj))
            # drop child on root --> add to last container
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                sourceparent.remove(c)
                data[-1].append(c)
                dvia.append(mod.ObjectToItem(c))
            self.dvcTree.Expand(mod.ObjectToItem(data[-1]))
            mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
            mod.ItemsAdded(mod.ObjectToItem(data[-1]), dvia)
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if targetparent != sourceparent:
                print('drop child on child {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
            else:
                print('drop child on child {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
            #self.selection = targetparent, sourceobjects
        else:
            # dropping containers on containers
            # sourceobjects should be a list with a single item, but, well...
            if sourceparent is None:
                print('container on container {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    data.remove(c)
                    n = data.index(targetobj)
                    data.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                parent = mod.GetParent(mod.ObjectToItem(c))
                mod.ItemsDeleted(parent, dvia)
                mod.ItemsAdded(parent, dvia)
                mod.Cleared(self.dvcTree)
            else:
                # dropping childs on containers
                print('child on container {}->{}'.format(sourceobjects,targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    sourceparent.remove(c)
                    targetobj.append(c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetobj), dvia)

        darr = dv.DataViewItemArray()
        for i in [mod.ObjectToItem(q) for q in selection]:
            darr.append(i)
        self._select(darr)

    def on_enddragosx(self, evt):
        self._dragging = False
        obj = wx.TextDataObject()
        obj.SetData(wx.DataFormat(wx.DF_UNICODETEXT), evt.GetDataBuffer())
        #obj = DataObject()
        #print(evt.GetDataBuffer())
        #obj.SetData(evt.GetDataBuffer())

        id = obj.GetText()

        mod = evt.GetModel()
        if not evt.GetItem().IsOk():
            # happens when dropping on root
            targetobj = None
        else:
            targetobj = mod.ItemToObject(evt.GetItem())
        sourceparent, sourceobj = mod.data.find_by_uuid(id)
        try:
            targetparent = mod.ItemToObject(mod.GetParent(evt.GetItem()))
        except:
            targetparent = None

        print('targetobj is',targetobj.__class__)
        if targetobj is None and sourceparent is None:
            # container dropped outside
            mod.data.remove(sourceobj)
            mod.data.append(sourceobj)
            mod.ItemDeleted(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
            mod.ItemAdded(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
        elif targetobj is None:
            # drop child on root --> add to last container
            sourceparent.remove(sourceobj)
            mod.data[-1].append(sourceobj)
            mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
            mod.ItemAdded(mod.ObjectToItem(mod.data[-1]), mod.ObjectToItem(sourceobj))
            #self.dvcTree.Expand(mod.ObjectToItem(mod.data[-1]))
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if targetparent != sourceparent:
                print('element moved to other container')
                sourceparent.remove(sourceobj)
                n = targetparent.index(targetobj)
                targetparent.insert(n, sourceobj)
                mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                mod.ItemAdded(mod.ObjectToItem(targetparent), mod.ObjectToItem(sourceobj))
            else:
                print('element moved within same container')
                sourceparent.remove(sourceobj)
                n = targetparent.index(targetobj)
                targetparent.insert(n, sourceobj)
                mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                mod.ItemAdded(mod.ObjectToItem(targetparent), mod.ObjectToItem(sourceobj))
        else:
            # dropped on parent node
            if sourceparent is None:
                print('container on container')
                # container dropped on container
                mod.data.remove(sourceobj)
                n = mod.data.index(targetobj)
                mod.data.insert(n, sourceobj)
                mod.ItemDeleted(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
                mod.ItemAdded(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
                #mod.ItemChanged(mod.ObjectToItem(sourceobj))
            else:
                print('element on container')
                # element dropped on container
                sourceparent.remove(sourceobj)
                targetobj.append(sourceobj)
                mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                mod.ItemAdded(mod.ObjectToItem(targetobj), mod.ObjectToItem(sourceobj))

        def delayed():
            #wx.CallAfter(mod.Cleared) # craches if called directly from event handler
            wx.CallAfter(self._select, darr, True)

        darr = dv.DataViewItemArray()
        for i in [mod.ObjectToItem(q) for q in mod.selection[1]]:
            darr.append(i)

        delayed()

    def on_drag(self, evt):
        #print('begin drag')
        obj = evt.GetModel().ItemToObject(evt.GetItem())
        evt.SetDataObject(wx.TextDataObject(obj.uuid))

        mod = evt.GetModel()
        self._draglevel = int(mod.GetParent(evt.GetItem()) != dv.NullDataViewItem)
        self._dragging = True
        if sys.platform == 'darwin':
            return

        parent, childs = mod.selection
        if len(childs) == 0: # happens if on linux there is no selection prior to dragging
            childs = [obj]
        print('ondrag selection',self.selection)
        if len(childs) == 0:
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
        print('items dragged', self._items_dragged)


if __name__ == "__main__":
    prj = Project()
    import os
    print(os.path.abspath(os.curdir))
    prj.load('example.lpj')
    print(prj)
    for p in prj:
        for s in p:
            print(s)
    app = wx.App()
    f = MyFrame(None, prj)
    f.Show()
    app.MainLoop()
