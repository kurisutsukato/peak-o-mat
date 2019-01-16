import wx
import wx.dataview as dv

print(wx.__version__)

class Container(list):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Container {}'.format(self.name)

class Element(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Element {}'.format(self.name)

    @property
    def len(self):
        return str(len(self.name))

class MyTreeListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self.data = data

        if wx.__version__ == '3.0.2.0':
            self.objmapper.UseWeakRefs(True)

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
        if isinstance(node, Container):
            for ds in node:
                children.append(self.ObjectToItem(ds))
            return len(node)
        return 0

    def IsContainer(self, item):
        if not item:
            return True
        node = self.ItemToObject(item)
        if isinstance(node, Container):
            return True
        return False

    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem

        node = self.ItemToObject(item)
        if isinstance(node, Container):
            return dv.NullDataViewItem
        elif isinstance(node, Element):
            for g in self.data:
                try:
                    g.index(node)
                except ValueError:
                    continue
                else:
                    return self.ObjectToItem(g)

    def GetValue(self, item, col):
        node = self.ItemToObject(item)

        if isinstance(node, Container):
            mapper = { 0 : node.name,
                       1 : '',
                       }
            return mapper[col]

        elif isinstance(node, Element):
            mapper = { 0 : node.name,
                       1 : node.len
                       }
            return mapper[col]

        else:
            raise RuntimeError("unknown node type")

    def GetAttr(self, item, col, attr):
        node = self.ItemToObject(item)
        if isinstance(node, Container):
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

class MyFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Table")
        
        panel = wx.Panel(self)
                
        dvcTree = dv.DataViewCtrl(panel,style=wx.BORDER_THEME|dv.DV_MULTIPLE)
        self.model = MyTreeListModel(data)
        dvcTree.AssociateModel(self.model)

        dvcTree.AppendTextColumn("Container",   0, width=80)
        dvcTree.AppendTextColumn("Element",   1, width=80)

        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_BEGIN_DRAG, self._onDrag)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self._onEndDrag)
        dvcTree.Bind(dv.EVT_DATAVIEW_ITEM_DROP_POSSIBLE, self._onDragPossible)

        self.dvcTree = dvcTree
        dvcTree.EnableDragSource(wx.DataFormat(wx.DF_UNICODETEXT))
        dvcTree.EnableDropTarget(wx.DataFormat(wx.DF_UNICODETEXT))
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(dvcTree, 1, wx.EXPAND)
        panel.SetSizer(box)
        self.Layout()

    def _onDragPossible(self, evt):
        item = evt.GetItem()
        mod = evt.GetModel()

        if not evt.GetItem().IsOk():
            return

        try:
            if isinstance(evt.GetModel().ItemToObject(evt.GetItem()), Container):
                evt.Veto()
        except AttributeError:
            # this is for 3.0.2
            if isinstance(self.model.ItemToObject(evt.GetItem()), Container):
                evt.Veto()

    def _onEndDrag(self, evt):
        if not evt.GetItem().IsOk():
            evt.Veto()
            return
        
        try:
            mod = evt.GetModel()
            print 'dropped at', mod.ItemToObject(evt.GetItem())
            try:
                print 'parent:',mod.ItemToObject(mod.GetParent(evt.GetItem()))
            except TypeError:
                print 'parent: None'
        except AttributeError:
            # this is for 3.0.2
            mod = self.model
            print 'dropped at', mod.ItemToObject(evt.GetItem())
            print 'parent:',mod.GetParent(evt.GetItem())

    def _onDrag(self, evt):
        evt.Allow()
        mod = evt.GetModel()
        print 'from', mod.GetValue(evt.GetItem(),0)
        evt.SetDataObject(wx.TextDataObject(u'don\'t know how to retrieve that information in the drop handler'))
        evt.SetDragFlags(wx.Drag_AllowMove)      
        
data = [Container('eins'),Container('zwei'),Container('drei')]
for d in data:
    d[:] = [Element('element {}'.format('X'*q)) for q in range(5)]

if __name__ == "__main__":
    app = wx.App()
    f = MyFrame(None)
    f.Show()
    app.MainLoop()
