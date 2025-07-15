import wx
import wx.dataview as dv
from uuid import uuid4
import sys
from pubsub import pub
from pickle import dumps, loads
import logging
import copy

from .project import Project, Plot, PlotData
from .misc_ui import WithMessage

logger = logging.getLogger('pom')

class TreeListModel(dv.PyDataViewModel):
    def __init__(self, data):
        dv.PyDataViewModel.__init__(self)
        self._selection = []
        self.data = data
        self.data.attach_dvmodel(self)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        setattr(result, 'data', copy.deepcopy(self.data, memo))
        return result

    @property
    def item_selection(self):
        return self._selection

    @property
    def selection(self):
        # logger.debug('dvmodel selection property')
        try:
            parent = self.GetParent(self._selection[0])
        except IndexError:
            logger.debug('dvmodel no selection')
            return None, []
        else:
            if parent == dv.NullDataViewItem:
                return None, [self.ItemToObject(q) for q in self._selection]
            else:
                return self.ItemToObject(parent), [self.ItemToObject(q) for q in self._selection]

    @selection.setter
    def selection(self, newsel):
        if type(newsel) not in [tuple, list, dv.DataViewItemArray]:
            self._selection = [newsel]
        else:
            self._selection = newsel

    @property
    def selection_indices(self):
        parent, childs = self.selection

        if parent is None:
            try:
                plotnum = self.data.index(childs[0])
            except IndexError:
                plotnum = None
            setnum = None
        else:
            plotnum = self.data.index(parent)
            setnum = [self.data[plotnum].index(q) for q in childs]
        return plotnum, setnum

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        mapper = {0: 'string',
                  1: 'string'
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
            return len(children)
        else:
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
            logger.debug('nicht auffindbar', node)
        raise Exception('should not happen', node, item)
        return dv.NullDataViewItem

    def SetValue(self, value, item, col):
        c = self.ItemToObject(item)
        c.name = value
        return True

    def GetAttr(self, item, col, attr):
        obj = self.ItemToObject(item)
        attr.SetColour(wx.BLACK) # needed on OSX

        if isinstance(obj, Plot):
            if obj.model is not None:
                attr.SetColour(wx.Colour(0,120,0))
                attr.SetBold(True)
                return True
            else:
                return False
        elif obj.hide:
            attr.SetStrikethrough(True)
            if obj.model is not None:
                attr.SetColour(wx.Colour(0, 120, 0))
                attr.SetBold(True)
            return True
        else:
            if obj.model is not None:
                attr.SetColour(wx.Colour(0, 120, 0))
                attr.SetBold(True)
                return True
        return False

    def GetValue(self, item, col):
        node = self.ItemToObject(item)

        if isinstance(node, Plot):
            num = self.data.position(node)
            mapper = {0: 'p{} {}'.format(num, node.name),
                      1: '',
                      }
            return mapper[col]
        else:
            cont, elem = self.data.find_by_uuid(node.uuid)
            num = cont.position(elem)
            # logger.debug(cont[num], id(cont[num]), elem, id(elem))
            mapper = {0: 's{} {}'.format(num, node.name),
                      1: ''
                      }
            return mapper[col]

    def __Cleared(self, dvctrl=None):
        if dvctrl is not None:
            self.save_state(dvctrl)
            super(TreeListModel, self).Cleared()
            self.restore_state(dvctrl)
        else:
            super(TreeListModel, self).Cleared()

    def save_state(self, dvctrl):
        iarr = dv.DataViewItemArray()
        self.GetChildren(None, iarr)
        self._expstate = dict([(self.ItemToObject(q).uuid, dvctrl.IsExpanded(q)) for q in iarr])

    def restore_state(self, dvctrl):
        for k, v in self._expstate.items():
            if v:
                dvctrl.Expand(self.ObjectToItem(self.data[k]))
            else:
                dvctrl.Collapse(self.ObjectToItem(self.data[k]))


class TreeCtrlPanel(wx.Panel, WithMessage):
    def __init__(self, parent):
        super(TreeCtrlPanel, self).__init__(parent)
        WithMessage.__init__(self)

        self.btn_addplot = wx.Button(self, label='Add plot')
        self.tree = TreeCtrl(self)

        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.tree, 1, wx.EXPAND)
        box.Add(self.btn_addplot, 0, wx.EXPAND)
        self.SetSizer(box)
        self.Bind(wx.EVT_BUTTON, self.onaddplot)
        self.Bind(wx.EVT_KEY_DOWN, self.onkey)

    def onaddplot(self, evt):
        pub.sendMessage((self.instid, 'tree', 'addplot'))

    def onkey(self, evt):
        logger.debug('panel_list key down')


class TreeCtrl(dv.DataViewCtrl, WithMessage):
    def __init__(self, parent, standalone=False):
        dv.DataViewCtrl.__init__(self, parent, style=wx.BORDER_THEME | dv.DV_MULTIPLE | dv.DV_NO_HEADER)
        if standalone:
            self.instid = 'ID' + str(id(self))  # needed for the message system
        else:
            WithMessage.__init__(self)

        self._dragging = False
        self._draglevel = 0
        self._items_dragged = []
        self._timer = wx.Timer(self)
        self._scrolllines = 0

        self.AppendTextColumn("Container", 0)  # , width=400)
        self.AppendTextColumn("Element",   1, width=0)
        # the second column is needed to prevent a bug on OSX

        self.Bind(dv.EVT_DATAVIEW_ITEM_BEGIN_DRAG, self.on_drag)
        if sys.platform == 'darwin':
            self.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddragosx)
        elif sys.platform == 'linux':
            self.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddraglinux)
        else:
            self.Bind(dv.EVT_DATAVIEW_ITEM_DROP, self.on_enddrag)
        self.Bind(dv.EVT_DATAVIEW_ITEM_DROP_POSSIBLE, self.on_droppossible)
        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.on_select)
        if sys.platform != 'linux':
            self.Bind(dv.EVT_DATAVIEW_ITEM_EXPANDED, self.on_expand)
        self.Bind(dv.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_menu)

        self.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_activated)

        # needed on windows to scroll while dragging
        self.Bind(wx.EVT_TIMER, self.on_timer)

        self.init_menus()

        parent.Bind(wx.EVT_ENTER_WINDOW, self.on_mouseenter)

        wx.CallAfter(self.GetColumn(0).SetWidth, wx.COL_WIDTH_AUTOSIZE)

    def update_item(self, item):
        dvm = self.dataviewmodel
        dvm.ItemChanged(dvm.ObjectToItem(item))

    def update_attributes(self, full=False):
        if full:
            self.dataviewmodel.Cleared()
            logger.debug('update full not implemented yet')
        sel = self.dataviewmodel.item_selection
        if len(sel) == 1:
            if self.dataviewmodel.IsContainer(sel[0]):
                childs = dv.DataViewItemArray()
                self.dataviewmodel.GetChildren(sel[0], childs)
                sel = childs
        self.dataviewmodel.ItemsChanged(sel)

    def AssociateModel(self, model):
        self.dataviewmodel = model
        dv.DataViewCtrl.AssociateModel(self, model)
        if sys.platform != 'darwin':
            self.EnableDragSource(wx.DataFormat('pom.treeitem'))
            self.EnableDropTarget(wx.DataFormat('pom.treeitem'))

    def init_menus(self):
        self.menumap = [  # (-1, 'Rename', self.on_),
            (-1, 'Delete\tDEL', self.on_menudelete),
            (-1, 'Duplicate\td', self.on_menuduplicate),
            (-1, 'New sets from visible area', self.on_menucrop),
            (-1, 'Copy to data grid', self.on_menuto_spreadsheat),
            (wx.ID_SEPARATOR, '', None),
            (-1, 'Toggle visibility\tSPACE', self.on_menuhide),
            (wx.ID_SEPARATOR, '', None),
            (-1, 'Remove mask', self.on_menuremmask),
            (-1, 'Remove trafos', self.on_menuremtrafo),
            (-1, 'Remove model', self.on_menuremfit),
            (-1, 'Remove weights', self.on_menuremweights),
            # (wx.ID_SEPARATOR, '', None),
            (-1, 'Insert plot', self.on_menuinsertplot),
            (-1, 'Copy\tCTRL-c', self.on_menucopy),
            (-1, 'Paste\tCTRL-v', self.on_menupaste)
        ]

        self.menu = wx.Menu()
        # self.minimal_menu = wx.Menu()

        class StripDic(dict):
            def __setitem__(self, key, val):
                key = key.split('\t')[0]
                return super().__setitem__(key, val)
        idmap = StripDic()

        for id, text, act in self.menumap:
            item = wx.MenuItem(self.menu, id=id, text=text)
            item = self.menu.Append(item)
            idmap[text] = item.GetId()
            if act is not None:
                self.Bind(wx.EVT_MENU, act, item)
                if text.find('plot') != -1:
                    self.Bind(wx.EVT_UPDATE_UI, self.on_uimenu, item)

        entries = []
        entries.append(wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_DELETE, idmap['Delete']))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('c'), idmap['Copy']))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_CTRL, ord('v'), idmap['Paste']))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_NORMAL, ord('d'), idmap['Duplicate']))
        entries.append(wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_SPACE, idmap['Toggle visibility']))

        self.accel = wx.AcceleratorTable(entries)
        self.SetAcceleratorTable(self.accel)

        # item = wx.MenuItem(self.minimal_menu, id=-1, text='paste')
        # item = self.minimal_menu.Append(item)
        # self.Bind(wx.EVT_MENU, self.OnPaste, item)
        # item = wx.MenuItem(self.minimal_menu, id=-1, text='add_plot')
        # item = self.minimal_menu.Append(item)
        # self.Bind(wx.EVT_MENU, self.OnAddPlot, item)

    def on_uimenu(self, evt):
        evt.Enable(self.dataviewmodel.selection[0] is None)

    def on_menuhide(self, evt):
        pub.sendMessage((self.instid, 'tree', 'hide'))
        self.update_attributes()

    def on_menuremmask(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'unmask'))

    def on_menuremfit(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remfit'))
        self.update_attributes()

    def on_menuremweights(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remerror'))

    def on_menuremtrafo(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remtrafo'))

    def on_menuinsertplot(self, evt):
        try:
            if self.dataviewmodel.selection[1][0] is not None:
                pub.sendMessage((self.instid, 'tree', 'insert'), msg=self.dataviewmodel.selection[1][0])
        except IndexError:
            logger.warning('insert at 0')
            pub.sendMessage((self.instid, 'tree', 'insert'), msg=0)

    def on_menuto_spreadsheat(self, evt):
        pub.sendMessage((self.instid, 'tree', 'togrid'))

    def on_menucrop(self, evt):
        pub.sendMessage((self.instid, 'tree', 'newfromvisarea'), msg=self.dataviewmodel.selection[0] is None)

    def on_menucopy(self, evt):
        pub.sendMessage((self.instid, 'tree', 'copy'))

    def on_menupaste(self, evt):
        pub.sendMessage((self.instid, 'tree', 'paste'))

    def on_menudelete(self, evt):
        pub.sendMessage((self.instid, 'tree', 'delete'))

    def on_menuduplicate(self, evt):
        pub.sendMessage((self.instid, 'tree', 'duplicate'))

    def on_menu(self, evt):
        self.PopupMenu(self.menu)
        # menu.Destroy()

    def on_mouseenter(self, evt):
        logger.debug('dvctree mouse enter')
        if wx.GetTopLevelParent(self).IsActive():
            self.SetFocus()

    def on_endedit(self, evt):
        obj = evt.GetEventObject()
        obj.Unbind(wx.EVT_TEXT_ENTER)
        obj.Unbind(wx.EVT_KILL_FOCUS)
        data = self.GetModel().data
        par, node = data.find_by_uuid(self._obj_edited)
        node.name = obj.GetValue()
        self.SetFocus()
        self.GetParent().Bind(wx.EVT_ENTER_WINDOW, self.on_mouseenter)

        wx.CallAfter(obj.Destroy)
        self.SetAcceleratorTable(self.accel)

    def on_activated(self, evt):
        self.SetAcceleratorTable(wx.NullAcceleratorTable)
        self.GetParent().Unbind(wx.EVT_ENTER_WINDOW)

        rect = self.GetItemRect(evt.GetItem(), self.GetColumn(0))
        x, y, w, h = rect
        parent = self
        W, H = self.GetVirtualSize()
        w = W - x - 2
        if sys.platform == 'darwin':
            y -= 0
            h += 3
        elif sys.platform == 'linux':
            X, Y = self.GetPosition()
            h += 2
            x += X
            y += Y
            parent = self.GetParent()
        txt = wx.TextCtrl(parent, pos=(x, y), size=(w, h), style=wx.TE_PROCESS_ENTER)
        obj = evt.GetModel().ItemToObject(evt.GetItem())
        lab = obj.name
        txt.SetValue(lab)
        # self.dvcTree.Refresh(True, rect)
        txt.SetFocus()
        txt.SelectAll()
        txt.Bind(wx.EVT_TEXT_ENTER, self.on_endedit)
        txt.Bind(wx.EVT_KILL_FOCUS, self.on_endedit)
        self._obj_edited = obj.uuid

    def _set_selection(self, sel):
        mod = self.dataviewmodel
        item = None
        if type(sel) == tuple:
            p, s = sel
            try:
                item = mod.ObjectToItem(mod.data[p][s])
            except IndexError:
                mod.selection = []
            else:
                mod.selection = [item]
        else:
            try:
                item = mod.ObjectToItem(mod.data[sel])
            except IndexError:
                mod.selection = []
            else:
                mod.selection = [item]
        dvia = dv.DataViewItemArray()
        if item is not None:
            dvia.append(item)
        self._select(dvia, False)

    selection = property(fset=_set_selection)

    def _select(self, dvia, silent=False):
        self.SetEvtHandlerEnabled(False)
        self.SetSelections(dv.DataViewItemArray())
        self.SetEvtHandlerEnabled(True)

        if silent:
            self.SetEvtHandlerEnabled(False)
            self.SetSelections(dvia)
            self.SetEvtHandlerEnabled(True)
        else:
            self.SetSelections(dvia)
            if sys.platform == 'win32':
                self.on_select(None)

    def on_expand(self, evt):
        mod = evt.GetModel()
        par = mod.ItemToObject(evt.GetItem())
        selpar, childs = mod.selection

        if par != selpar:
            return

        try:
            if par is not None and len(childs) > 0 and mod.ItemToObject(
                    mod.GetParent(mod.ObjectToItem(childs[0]))) == par:
                dvia = dv.DataViewItemArray()
                if self.GetSelections() != mod._selection:
                    for i in mod._selection:
                        dvia.append(i)
                    self._select(dvia, False)
        except:
            raise

    def on_select(self, evt):
        # logger.debug('dvctree onselect')
        # mod = evt.GetModel()
        mod = self.dataviewmodel
        selection = self.GetSelections()
        parents = [mod.GetParent(q) if mod.GetParent(q) != dv.NullDataViewItem else 0 for q in selection]

        if len(set(parents)) > 1 or (len(selection) > 1 and 0 in parents) or len(selection) == 0:
            darr = dv.DataViewItemArray()
            for i in mod._selection:
                darr.append(i)
            self._select(darr, True)
        else:
            if len(selection) > 0:
                mod.selection = selection
                pub.sendMessage((self.instid, 'tree', 'select'), selection=mod.selection_indices)

    def on_timer(self, evt):
        self.ScrollLines(self._scrolllines)

    def on_droppossible(self, evt):
        mod = evt.GetModel()
        targetitem = evt.GetItem()

        mod = evt.GetModel()
        if evt.GetDataFormat() != wx.DataFormat('pom.treeitem'):
            logger.debug('draged object has invalid data format')
        else:
            pass
            # evt.SetDropEffect(wx.DragMove)

        if sys.platform != 'win32':  # on win32 evt.GetDataBuffer() seems to be empty or invalid
            do = wx.TextDataObject()
            do.SetData(wx.DataFormat(wx.DF_UNICODETEXT), evt.GetDataBuffer())
            instid, itemid, isplot, obj = loads(bytearray.fromhex(do.GetText()))

            if instid != self.instid:
                pass
                # logger.debug('drop from other instance')
            else:
                if not self._dragging or self._draglevel == 0 and mod.GetParent(targetitem) != dv.NullDataViewItem:
                    # does not have consequences on linux
                    evt.Veto()

        if sys.platform not in ['darwin', 'linux']:
            mposx, mposy = wx.GetMousePosition()
            cposx, cposy = self.ScreenToClient((mposx, mposy))

            item, col = self.HitTest((cposx, cposy))
            if item == self.GetTopItem() and \
                    self.GetScrollPos(wx.VERTICAL) != 0:
                self._scrolllines = -1
                self._timer.Start(30, wx.TIMER_ONE_SHOT)
            elif self.GetScrollPos(wx.VERTICAL) + self.GetScrollThumb(wx.VERTICAL) != self.GetScrollRange(wx.VERTICAL) \
                    and self.ClientSize[1] - cposy < 10:
                self._scrolllines = +1
                self._timer.Start(30, wx.TIMER_ONE_SHOT)

    def on_enddrag(self, evt):
        self._dragging -= 1
        # do = wx.TextDataObject()
        # do.SetData(wx.DataFormat(wx.DF_UNICODETEXT), evt.GetDataBuffer())
        do = wx.CustomDataObject('pom.treeitem')
        do.SetData(evt.GetDataBuffer())
        # instid, itemid, isplot, obj = loads(bytearray.fromhex(do.GetData()))
        instid, itemid, isplot, obj = loads(do.GetData())

        mod = evt.GetModel()
        if instid != self.instid:
            logger.debug('drag to other instance')
            paritem = mod.GetParent(evt.GetItem())
            if paritem == dv.NullDataViewItem and isplot:
                if evt.GetItem().IsOk():
                    target = mod.ItemToObject(evt.GetItem())
                    n = mod.data.index(target)
                    mod.data.insert(n, obj)
                else:
                    mod.data.append(obj)
            elif not (paritem == dv.NullDataViewItem or isplot):
                if evt.GetItem().IsOk():
                    target = mod.ItemToObject(evt.GetItem())
                    targetpar = mod.ItemToObject(mod.GetParent(evt.GetItem()))
                    n = targetpar.index(target)
                    targetpar.insert(n, obj)
            return

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

        logger.debug('targetobj is {}'.format(targetobj.__class__))
        if targetobj is None and sourceparent is None:
            # container dropped on root --> move to last position
            logger.debug('container on root {}->{}'.format(sourceobjects, targetobj))
            # dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                mod.data.remove(c)
                mod.data.append(c)
                # dvia.append(mod.ObjectToItem(c))
            parent = mod.GetParent(mod.ObjectToItem(c))
            # mod.ItemsDeleted(parent, dvia)
            # mod.ItemsAdded(parent, dvia)
            # mod.Cleared(self)
        elif targetobj is None:
            logger.debug('child on root {}->{}'.format(sourceobjects, targetobj))
            # drop child on root --> add to last container
            # dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                sourceparent.remove(c)
                mod.data[-1].append(c)
                # dvia.append(mod.ObjectToItem(c))
            # self.Expand(mod.ObjectToItem(data[-1]))
            # mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
            # mod.ItemsAdded(mod.ObjectToItem(data[-1]), dvia)
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if sourceparent is None:
                # tried to drop plot on item
                pass
            elif targetparent != sourceparent:
                logger.debug('drop child on child {}->{}'.format(sourceobjects, targetobj))
                # dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    sourceparent.remove(c)
                    # logger.debug('sourceparent has notifier {}'.format(sourceparent.has_notifier))
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    # dvia.append(mod.ObjectToItem(c))
                # mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                # mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
            else:
                logger.debug('drop child on child {}->{}'.format(sourceobjects, targetobj))
                # dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    # dvia.append(mod.ObjectToItem(c))
                # mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                # mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
        else:
            # dropping containers on containers
            # sourceobjects should be a list with a single item, but, well...
            if sourceparent is None:
                logger.debug('container on container {}->{}'.format(sourceobjects, targetobj))
                # dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    mod.data.remove(c)
                    n = mod.data.index(targetobj)
                    mod.data.insert(n, c)
                    # item = mod.ObjectToItem(c)
                    # dvia.append(item)
                # mod.ItemsDeleted(dv.NullDataViewItem, dvia)
                # mod.ItemsAdded(dv.NullDataViewItem, dvia)
            else:
                # dropping childs on containers
                # dvia = dv.DataViewItemArray()
                logger.debug('child on container {}->{}'.format(sourceobjects, targetobj))
                for c in sourceobjects:
                    sourceparent.remove(c)
                    targetobj.append(c)
                    # item = mod.ObjectToItem(c)
                    # dvia.append(item)
                # mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                # mod.ItemsAdded(mod.ObjectToItem(targetobj), dvia)

        darr = dv.DataViewItemArray()
        for i in [mod.ObjectToItem(q) for q in mod.selection[1]]:
            darr.append(i)
        self._select(darr)

    def on_enddraglinux(self, evt):
        logger.debug('end drag')
        self._dragging -= 1

        obj = wx.DataObjectSimple()
        obj.SetData(evt.GetDataBuffer())

        item = evt.GetItem()
        mod = evt.GetModel()

        selection = mod.selection[1]

        if self._draglevel == 0 and mod.GetParent(item) != dv.NullDataViewItem:
            # dropped container on child --> forbidden
            return

        mod.save_state(self)

        if not evt.GetItem().IsOk():
            # happens when dropping on root
            targetobj = None
            logger.debug('   targetobj None')
        else:
            targetobj = mod.ItemToObject(evt.GetItem())

        sourceparent, sourceobjects = self._items_dragged
        self._items_dragged = None

        try:
            targetparent = mod.ItemToObject(mod.GetParent(evt.GetItem()))
        except:
            targetparent = None

        logger.debug('targetobj is {}'.format(targetobj.__class__))
        if targetobj is None and sourceparent is None:
            # container dropped on root --> move to last position
            logger.debug('container on root {}->{}'.format(sourceobjects, targetobj))
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                mod.data.remove(c)
                mod.data.append(c)
                dvia.append(mod.ObjectToItem(c))
            parent = mod.GetParent(mod.ObjectToItem(c))
            mod.ItemsDeleted(parent, dvia)
            mod.ItemsAdded(parent, dvia)
            mod.Cleared(self)
        elif targetobj is None:
            logger.debug('child on root {}->{}'.format(sourceobjects, targetobj))
            # drop child on root --> add to last container
            dvia = dv.DataViewItemArray()
            for c in sourceobjects:
                sourceparent.remove(c)
                data[-1].append(c)
                dvia.append(mod.ObjectToItem(c))
            self.Expand(mod.ObjectToItem(data[-1]))
            mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
            mod.ItemsAdded(mod.ObjectToItem(data[-1]), dvia)
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if targetparent != sourceparent:
                logger.debug('drop child on child {}->{}'.format(sourceobjects, targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    sourceparent.remove(c)
                    n = targetparent.index(targetobj)
                    targetparent.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                mod.ItemsDeleted(mod.ObjectToItem(sourceparent), dvia)
                mod.ItemsAdded(mod.ObjectToItem(targetparent), dvia)
            else:
                logger.debug('drop child on child {}->{}'.format(sourceobjects, targetobj))
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
            # self.selection = targetparent, sourceobjects
        else:
            # dropping containers on containers
            # sourceobjects should be a list with a single item, but, well...
            if sourceparent is None:
                logger.debug('container on container {}->{}'.format(sourceobjects, targetobj))
                dvia = dv.DataViewItemArray()
                for c in sourceobjects:
                    if c == targetobj:
                        continue
                    mod.data.remove(c)
                    n = mod.data.index(targetobj)
                    mod.data.insert(n, c)
                    dvia.append(mod.ObjectToItem(c))
                parent = mod.GetParent(mod.ObjectToItem(c))
                mod.ItemsDeleted(parent, dvia)
                mod.ItemsAdded(parent, dvia)
                mod.Cleared(self)
            else:
                # dropping childs on containers
                logger.debug('child on container {}->{}'.format(sourceobjects, targetobj))
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
        wx.CallAfter(self._select, darr)  # important to avoid recursion error when dropping multiple items

    def on_enddragosx(self, evt):
        self._dragging = False

        do = wx.TextDataObject()
        do.SetData(wx.DataFormat(wx.DF_UNICODETEXT), evt.GetDataBuffer())

        mod = evt.GetModel()

        instid, itemid, isplot, obj = loads(bytearray.fromhex(do.GetText()))
        if instid != self.instid:
            paritem = mod.GetParent(evt.GetItem())
            if paritem == dv.NullDataViewItem and isplot:
                if evt.GetItem().IsOk():
                    target = mod.ItemToObject(evt.GetItem())
                    n = mod.data.index(target)
                    mod.data.insert(n, obj)
                else:
                    mod.data.append(obj)
            elif not (paritem == dv.NullDataViewItem or isplot):
                if evt.GetItem().IsOk():
                    target = mod.ItemToObject(evt.GetItem())
                    targetpar = mod.ItemToObject(mod.GetParent(evt.GetItem()))
                    n = targetpar.index(target)
                    targetpar.insert(n, obj)
            return

        sourceitem = dv.DataViewItem(int(itemid))
        id = mod.ItemToObject(sourceitem).uuid

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

        # logger.debug('targetobj is',targetobj.__class__)
        if targetobj is None and sourceparent is None:
            # container dropped outside
            mod.data.remove(sourceobj)
            mod.data.append(sourceobj)
            # mod.ItemDeleted(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
            # mod.ItemAdded(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
        elif targetobj is None:
            # drop child on root --> add to last container
            sourceparent.remove(sourceobj)
            mod.data[-1].append(sourceobj)
            # mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
            # mod.ItemAdded(mod.ObjectToItem(mod.data[-1]), mod.ObjectToItem(sourceobj))
            # self.Expand(mod.ObjectToItem(mod.data[-1]))
        elif not isinstance(targetobj, Plot):
            # dropped on child
            if targetparent != sourceparent:
                # logger.debug('element moved to other container')
                sourceparent.remove(sourceobj)
                n = targetparent.index(targetobj)
                targetparent.insert(n, sourceobj)
                # mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                # mod.ItemAdded(mod.ObjectToItem(targetparent), mod.ObjectToItem(sourceobj))
            else:
                # logger.debug('element moved within same container')
                sourceparent.remove(sourceobj)
                n = targetparent.index(targetobj)
                targetparent.insert(n, sourceobj)
                # mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                # mod.ItemAdded(mod.ObjectToItem(targetparent), mod.ObjectToItem(sourceobj))
        else:
            # dropped on parent node
            if sourceparent is None:
                # logger.debug('container on container')
                # container dropped on container
                mod.data.remove(sourceobj)
                n = mod.data.index(targetobj)
                mod.data.insert(n, sourceobj)
                # mod.ItemDeleted(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
                # mod.ItemAdded(dv.NullDataViewItem, mod.ObjectToItem(sourceobj))
                # mod.ItemChanged(mod.ObjectToItem(sourceobj))
            else:
                # logger.debug('element on container')
                # element dropped on container
                sourceparent.remove(sourceobj)
                targetobj.append(sourceobj)
                # mod.ItemDeleted(mod.ObjectToItem(sourceparent), mod.ObjectToItem(sourceobj))
                # mod.ItemAdded(mod.ObjectToItem(targetobj), mod.ObjectToItem(sourceobj))

        darr = dv.DataViewItemArray()

        for i in mod._selection:
            darr.append(i)
        self._select(darr)

    def on_drag(self, evt):
        # logger.debug('begin drag')
        mod = evt.GetModel()
        obj = mod.ItemToObject(evt.GetItem())

        isplot = mod.GetParent(evt.GetItem()) == dv.NullDataViewItem
        msg = dumps((self.instid, str(int(evt.GetItem().GetID())), isplot, obj))  # .hex()

        # do = wx.TextDataObject()
        # do.SetText(msg)
        do = wx.CustomDataObject('pom.treeitem')
        do.SetData(msg)
        evt.SetDataObject(do)
        evt.SetDragFlags(wx.Drag_AllowMove)

        self._draglevel = int(mod.GetParent(evt.GetItem()) != dv.NullDataViewItem)
        self._dragging = True
        if sys.platform == 'darwin':
            return

        parent, childs = mod.selection
        if len(childs) == 0:  # happens if on linux there is no selection prior to dragging
            childs = [obj]
        # logger.debug('ondrag selection',mod.selection)
        if mod.ItemToObject(evt.GetItem()) not in childs:
            par = mod.GetParent(evt.GetItem())
            if par == dv.NullDataViewItem:
                parent = None
            else:
                parent = mod.ItemToObject(par)
            self._items_dragged = parent, [mod.ItemToObject(evt.GetItem())]
        else:
            self._items_dragged = parent, childs
        # logger.debug('items dragged',self._items_dragged)


class MyFrame(wx.Frame):
    def __init__(self, parent, prj, standalone=False):
        wx.Frame.__init__(self, parent, -1, "Table", size=(-1, 400))

        panel = wx.Panel(self)
        self.dataviewmodel = TreeListModel(prj)
        self.dvcTree = TreeCtrl(panel, standalone)
        self.dvcTree.AssociateModel(self.dataviewmodel)

        self.btn_clear = wx.Button(panel, label='Clear')
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.dvcTree, 1, wx.ALL | wx.EXPAND, 10)
        box.Add(self.btn_clear, 0, wx.EXPAND)
        panel.SetSizer(box)
        self.Layout()

        # self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)


def demo():
    prj = Project()
    import os
    logger.debug(os.path.abspath(os.curdir))
    prj.load('example.lpj')
    logger.debug(prj)
    for p in prj:
        for s in p:
            logger.debug(s)
    app = wx.App()
    f = MyFrame(None, prj, True)
    f.Show()
    app.MainLoop()


def cbm():
    import sys, types

    def callback_method(func, inst, manager):
        def notify(self, *args, **kwargs):
            for _, callback in manager._callbacks:
                callback()
            return func(inst, *args, **kwargs)

        return types.MethodType(notify, inst)

    class CallbackManager:
        def __init__(self, data):
            self._callbacks = []
            self._callback_cntr = 0
            self.attach(data)

        def attach(self, data):
            data.append = callback_method(list.append, data, self)
            # the same for all the other methods as in OP

        def register_callback(self, cb):
            self._callbacks.append((self._callback_cntr, cb))
            self._callback_cntr += 1
            return self._callback_cntr - 1

        def unregister_callback(self, cbid):
            for idx, (i, cb) in enumerate(self._callbacks):
                if i == cbid:
                    self._callbacks.pop(idx)
                    return cb
            else:
                return None

    class CustomList(list):
        pass

    class ExtraBase(list):
        def __getitem__(self, item):
            logger.debug('got ya', self.test)
            return list.__getitem__(self, item)

        def pop(self, n):
            logger.debug('pop', n)
            return list.pop(self, n)

    def enhance(obj):
        class Patched(obj.__class__, ExtraBase):
            pass

        obj.__class__ = Patched
        obj.test = False

    A = CustomList([1, 2, 3])
    enhance(A)

    A[0]
    logger.debug(A.pop(0))


if __name__ == "__main__":
    demo()
