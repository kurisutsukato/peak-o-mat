__author__ = 'kristukat'

import wx.dataview as dv
from wx.lib.pubsub import pub

class AutoSortList(list):
    def append(self, item):
        super(AutoSortList, self).append(item)
        self[:] = sorted(self,key)
        print('sort')


class ScriptGroup(Group):
    isentry = False
    type = 'script'
    def __init__(self, parent=None, label=''):
        self.parent = parent
        self.label = label
        self._children = AutoSortList()

    def __setattribute__(self, attr, val):
        print(attr,val)
        if attr == 'children':
            for q in val:
                self._children.append(q)

    def __getattr__(self, attr):
        if attr == 'children':
            return self._children

class ModelGroup(Group):
    type = 'model'

class Entry:
    isentry = True
    def __init__(self, parent, label=''):
        self.parent = parent
        self.label = label

    @property
    def type(self):
        p = self.parent
        return p.parent.type, p.type

    @property
    def islocal(self):
        return self.parent.type == 'local'

class Group(object):
    def __init__(self, label=''):
        self.scripts = ScriptGroup(label='Scripts')
        self.models = ModelGroup(label='Models')

        self.children = []
        self.label = label

    def add_script(self, label):
        pass

    def add_model(self, model):
        pass

class LocalGroup(Group):
    type = 'local'

class EmbeddedGroup(Group):
    type = 'embedded'

class ScriptingRoot(object):
    def __init__(self):
        self.local = LocalGroup(label='Local')
        self.embedded = EmbeddedGroup(label='Embedded')

class Model(dv.PyDataViewModel):
    def __init__(self, root):
        dv.PyDataViewModel.__init__(self)
        self.root = root
        #pub.subscribe(self.OnItemAdded, 'ITEM_ADDED')
        self.objmapper.UseWeakRefs(True)

    def GetColumnType(self, col):
        return 'string'

    def GetColumnCount(self):
        return 1

    def GetChildren(self, item, children):
        if not item:
            for r in self.root:
                children.append(self.ObjectToItem(r))
            return len(self.root)
        elif isinstance(self.ItemToObject(item),Group):
            obj = self.ItemToObject(item)
            for child in obj.children:
                #print "GetChildren called. Items returned = " + str([child.label for child in objct.children])
                children.append(self.ObjectToItem(child))
            return len(obj.children)
        else:
            return 0

    def IsContainer(self, item):
        if not item:
            return True
        elif isinstance(self.ItemToObject(item), Group):
            return (len(self.ItemToObject(item).children) != 0)
        return False

    def GetParent(self, item):
        if not item:
            return dv.NullDataViewItem
        node = self.ItemToObject(item)
        if node.parent is None:
            return dv.NullDataViewItem
        else:
            return self.ObjectToItem(node.parent)

    def GetValue(self, item, col):
        if not item:
            return None
        else:
            return self.ItemToObject(item).label

    def SetValue(self, val, item, col):
        obj = self.ItemToObject(item)
        obj.label = val
        self.ItemChanged(item)

    def GetAttr(self, item, col, attr):
        node = self.ItemToObject(item)
        if isinstance(node, Group):
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

class Controller(object):
    def __init__(self, view=None, interactor=None):
        self.view = view
        if interactor is not None:
            interactor.Install(self, view)

        l = LocalGroup(label='Local')
        l.children = [ScriptGroup(l,'Scripts'),ModelGroup(l,'Custom models')]
        e = EmbeddedGroup(label='Embedded')
        e.children = [ScriptGroup(e,'Scripts'),ModelGroup(e,'Custom models')]
        c = e.children[0]
        c.children = [Entry(c,q) for q in ['1','4','3']]
        self.model = Model([l,e])
        self.view.set_tree_model(self.model)

        self.view.run()

    def delete_entry(self):
        obj = self.model.ItemToObject(self.view.tree.Selection)
        obj.parent.children.remove(obj)
        self.model.ItemDeleted(self.model.GetParent(self.view.tree.Selection), self.view.tree.Selection)

    def add_entry(self):
        obj = self.model.ItemToObject(self.view.tree.Selection)
        if obj.isentry:
            obj = obj.parent
        en = Entry(obj, 'ganz neu')
        obj.children.append(en)
        item = self.model.ObjectToItem(en)
        self.model.ItemAdded(self.model.GetParent(item),item)
        self.view.tree.EnsureVisible(item)
        self.view.tree.Select(item)

    def ask_for_rename(self, obj):
        return not obj.label == 'Depp'

if __name__ == '__main__':

    a = AutoSortList()
    a.append(1)
    a.append(3)
    a.append(2)
    print(a)


    import wx
    from .view import View
    from .interactor import Interactor

    app = wx.App()
    Controller(View(None), Interactor())