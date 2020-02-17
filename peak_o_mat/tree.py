#!/usr/bin/python


##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     
##     This program is free software; you can redistribute it and modify
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

import wx
import re
import pickle
import os

from pubsub import pub
from wx.lib.agw.customtreectrl import CustomTreeCtrl

from . import spec, project, images
from .misc_ui import WithMessage

if os.name == 'posix':
    CustomTreeCtrl = wx.TreeCtrl

class TreeCtrl(CustomTreeCtrl, WithMessage):
    def __init__(self, parent):

        style = wx.TR_EDIT_LABELS|wx.TR_HAS_BUTTONS|wx.TR_MULTIPLE|wx.TR_HIDE_ROOT
        if os.name == 'posix':
            CustomTreeCtrl.__init__(self, parent, style=style)
        else:
            CustomTreeCtrl.__init__(self, parent, style=wx.SIMPLE_BORDER, agwStyle=style)
            self.SetBackgroundColour(wx.WHITE)
        WithMessage.__init__(self)

        self.item = None
        self.root = None

        self._drag = False
        self._update = False
        
        self.root = self.AddRoot('project tree')
        
        isz = (16,16)
        il = wx.ImageList(*isz)
        self.icon_set = il.Add(images.get_bmp('dataset.png'))
        self.icon_hide = il.Add(images.get_bmp('dataset_hide.png'))
        self.icon_set_model = il.Add(images.get_bmp('dataset_model.png'))
        self.icon_hide_model = il.Add(images.get_bmp('dataset_model_hide.png'))

        self.icon_plot = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz))
        #self.icon_set = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        #self.icon_hide = il.Add(wx.ArtProvider_GetBitmap(wx.ART_DELETE, wx.ART_OTHER, isz))

        self.SetImageList(il)
        self.il = il

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)
        self.Bind(wx.EVT_TREE_SEL_CHANGING, self.OnChanging)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnDragBegin)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnDragEnd)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.OnKey)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMenu)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit)

        self.Bind(wx.EVT_TIMER, self.OnTime)

        self.Bind(wx.EVT_CHAR, self.OnChar)
        
        self.initMenus()

        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)

    def OnMouseEnter(self, evt):
        if wx.GetTopLevelParent(self).IsActive():
            self.SetFocus()

    def __getitem__(self, item):
        """\
        The tree items can be accessed like self[plot] or self[plot,set].
        If the indexed item does not yet exist it will be created along with
        all items with smaller indices.
        """
        if type(item) == tuple:
            p,s = item
        else:
            p,s = item,None
        
        nc = self.GetChildrenCount(self.root, False)
        if p >= nc:
            for i in range(p-nc+1):
                p_item = self.AppendItem(self.root, '....')
                self.SetItemData(p_item, -1)
        else:
            for n,p_item in enumerate(self.walk()):
                if n == p:
                    break
        if s is None:
            return p_item
        else:
            nc = self.GetChildrenCount(p_item, False)
            if s >= nc:
                for i in range(s-nc+1):
                    s_item = self.AppendItem(p_item, '....')
                    self.SetItemData(s_item, -1)
            else:
                for n,s_item in enumerate(self.walk(p_item)):
                    if n == s:
                        break
            return s_item
        
    def OnChanging(self, evt):
        item = evt.GetItem()
        if item == self.root or self._drag:
            evt.Veto()
            return
        if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT):
            if len(self.GetSelections()) == 0:
                evt.Veto()
                return
            if self.GetItemParent(self.GetSelections()[0]) != self.GetItemParent(item):
                evt.Veto()
            if self.isPlot(self.GetSelections()[0]):
                evt.Veto()
        else:
            evt.Skip()

    def OnEdit(self, evt):
        self.EditLabel(self.item)

    def OnBeginEdit(self,evt):
        self.Unbind(wx.EVT_ENTER_WINDOW)
        if self.item == self.root:
            evt.Veto()
            return
        self.edit_item = evt.GetItem()
        name = self.GetItemText(self.edit_item)

        self.item_old_name = name
        try:
            name = re.match(r'[sp]\d+\s*(.+)',name).groups()[0]
        except AttributeError:
            pass
        self.SetItemText(self.edit_item, name)

    def OnEndEdit(self, evt):
        name = evt.GetLabel().strip()

        set = None

        if not evt.IsEditCancelled():
            parent = self.GetItemParent(self.edit_item)
            if parent == self.root:
                plot = self.GetItemData(self.edit_item)
            else:
                plot = self.GetItemData(parent)
                set = self.GetItemData(self.edit_item)
            pub.sendMessage((self.instid, 'tree', 'rename'), msg=(plot, set, name))
        else:
            evt.Veto()
            self.SetItemText(self.edit_item, self.item_old_name)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)

    def initMenus(self):
        self.menumap = [(-1,'Edit label',self.OnEdit),
                           (-1,'Delete',self.OnRemItem),
                           (-1,'Duplicate',self.OnDuplicate),
                           (-1,'New sets from visible area',self.OnNewSetsFromVisArea),
                           (-1,'Copy to data grid',self.OnSpreadsheet),
                           (wx.ID_SEPARATOR, '', None),
                           (-1,'Toggle visibility',self.OnHide),
                           (wx.ID_SEPARATOR, '', None),
                           (-1,'Remove mask',self.OnUnmask),
                           (-1,'Remove trafos',self.OnRemTrafo),
                           (-1,'Remove model',self.OnRemFit),
                           (-1,'Remove weights',self.OnRemError),
                           (wx.ID_SEPARATOR, '', None),
                           (-1,'Insert plot',self.OnInsertPlot),
                           (-1,'Copy',self.OnCopy),
                           (-1,'Paste',self.OnPaste)]

        self.menu = wx.Menu()
        self.minimal_menu = wx.Menu()
        
        for id,text,act in self.menumap:
            item = wx.MenuItem(self.menu, id=id, text=text)
            item = self.menu.Append(item)
            if act is not None:
                self.Bind(wx.EVT_MENU, act, item)
                if text.find('Plot') != -1:
                    self.Bind(wx.EVT_UPDATE_UI, self.OnUIMenu, item)
                
        item = wx.MenuItem(self.minimal_menu, id=-1, text='paste')
        item = self.minimal_menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnPaste, item)
        item = wx.MenuItem(self.minimal_menu, id=-1, text='add_plot')
        item = self.minimal_menu.Append(item)
        self.Bind(wx.EVT_MENU, self.OnAddPlot, item)

    def OnUIMenu(self, evt):
        evt.Enable(self.isPlot(self.item))
        
    def OnMenu(self, evt=None):
        item, flag = self.HitTest(evt.GetPosition())
        if item is None or not item.IsOk() or item == self.root:
            paste = self.minimal_menu.FindItemByPosition(0)
            paste.Enable(self.check_clipboard())
            self.PopupMenu(self.minimal_menu, evt.GetPosition())
        elif self.item is not None or item.IsOk():
            paste = self.menu.FindItemById(self.menu.FindItem('Paste'))
            paste.Enable(self.check_clipboard())
            self.PopupMenu(self.menu, evt.GetPosition())

    def OnAddPlot(self, evt):
        pub.sendMessage((self.instid, 'tree', 'addplot'), msg=None)

    def OnCopy(self, evt):
        pub.sendMessage((self.instid, 'tree', 'copy'), msg=None)

    def OnPaste(self, evt):
        pub.sendMessage((self.instid, 'tree', 'paste'), msg=None)

    def OnHide(self, evt):
        pub.sendMessage((self.instid, 'tree', 'hide'), msg=None)

    def OnDuplicate(self, evt):
        pub.sendMessage((self.instid, 'tree', 'duplicate'), msg=self.isPlot(self.item))

    def OnNewSetsFromVisArea(self, evt):
        pub.sendMessage((self.instid, 'tree', 'newfromvisarea'), msg=self.isPlot(self.item))

    def OnSpreadsheet(self, evt):
        pub.sendMessage((self.instid, 'tree', 'togrid'), msg=None)

    def OnNewFrame(self, evt):
        print('tree: on new frame - obsolete')
        return

    def OnInsertPlot(self, evt):
        loc = self.GetItemData(self.item)
        pub.sendMessage((self.instid, 'tree', 'insert'), msg=loc)
    
    def OnRemFit(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remfit'), msg=None)

    def OnRemError(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remerror'), msg=None)

    def OnRemTrafo(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'remtrafo'), msg=None)
            
    def OnUnmask(self, evt=None):
        pub.sendMessage((self.instid, 'tree', 'unmask'), msg=None)
            
    def OnRemItem(self, evt):
        pub.sendMessage((self.instid, 'tree', 'delete'), msg=self.isPlot(self.item))

    def OnChar(self, evt):
        if evt.KeyCode == 3:
            self.OnCopy(None)
        elif evt.KeyCode == 22:
            self.OnPaste(None)
        evt.Skip()

    def OnKey(self, evt):
        kc = evt.GetKeyCode()
        if kc == 127:
            if self.item is None:
                return
            self.OnRemItem(evt=None)
        if kc == 13:
            self.OnEdit(None)
        evt.Skip()

    def OnDragBegin(self, evt):
        self._drag = True
        item = evt.GetItem()
        #if self.root in [self.GetItemParent(item), item]:
        if item == self.root:
            evt.Veto()
            self.dragitem = None
            self._drag = False
            return

        self.dragitem = self.GetSelections()
        evt.Allow()
        
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
        
    def OnDragEnd(self, evt):
        t_set = None
        target = evt.GetItem()
        source = self.dragitem[0]
        
        if not target.IsOk() or target == self.root:
            #drag ends on forbidden region
            self._drag = False
            return

        if self.GetItemParent(self.dragitem[0]) == self.root:
            #drag a plot
            if self.GetItemParent(target) != self.root:
                self._drag = False
                return
            else:
                s_plot, t_plot = [self.GetItemData(x) for x in [source, target]]
                s_sets = None
                t_set = None
        else:
            s_sets = [self.GetItemData(x) for x in self.dragitem]

            if self.GetItemParent(target) != self.root:
                t_set = self.GetItemData(target)
                target = self.GetItemParent(target)
            else:
                t_set = 0
                
            s_plot = self.GetItemData(self.GetItemParent(self.dragitem[0]))
            t_plot = self.GetItemData(target)

        self._drag = False
        
        pub.sendMessage((self.instid, 'tree', 'move'), msg=(s_plot, s_sets, t_plot, t_set))

    def OnSelChanged(self, evt):
        item = evt.GetItem()
        plotnum = None
        setnum = None

        if self._drag or self._update or not item.IsOk():
            evt.Skip()
            return

        self.item = item
        
        if self.item == self.root:
            plotnum = None
        elif self.isPlot(item):
            plotnum = self.GetItemData(evt.GetItem())
        else:
            plotnum = self.GetItemData(self.GetItemParent(item))
            if len(self.GetSelections()) > 1:
                setnum = []
                for sel in self.GetSelections():
                    setnum.append(self.GetItemData(sel))
            else:
                setnum = [self.GetItemData(evt.GetItem())]
        evt.Skip()
        pub.sendMessage((self.instid, 'tree', 'select'), selection=(plotnum, setnum))

    def GetFirstChild(self, *args):
        return CustomTreeCtrl.GetFirstChild(self, args[0])
        
    def Delete(self, item):
        if self.ItemHasChildren(item):
            self.DeleteChildren(item)
        parent = self.GetItemParent(item)
        CustomTreeCtrl.Delete(self, item)

    def SelectItem(self, item):
        self.UnselectAll()
        CustomTreeCtrl.SelectItem(self, item)

    def check_clipboard(self):
        if wx.TheClipboard.Open():
            do = wx.CustomDataObject('selection')
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()
            if success:
                data = do.GetData()
                try:
                    data = pickle.loads(data)
                except AttributeError:
                    return False
                return type(data) == spec.Spec or type(data) == project.Plot or type(data) == list
        return False
    
    def isPlot(self, item):
        return self.GetItemParent(item) == self.root

    def set_item(self, parent, child, name, hide=False, model=False):
        item = self[[child,(parent,child)][int(parent != -1)]]
        
        self.SetItemData(item, child)
        if parent == -1:
            self.SetItemImage(item, self.icon_plot, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 'p%d %s'%(child,name))
        elif hide and not model:
            self.SetItemImage(item, self.icon_hide, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 's%d %s'%(child,name))
        elif model and not hide:
            self.SetItemImage(item, self.icon_set_model, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 's%d %s'%(child,name))
        elif model and hide:
            self.SetItemImage(item, self.icon_hide_model, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 's%d %s'%(child,name))
        else:
            self.SetItemImage(item, self.icon_set, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 's%d %s'%(child,name))
            
        return item
        
    def walk(self, parent=None):
        if parent is None:
            parent = self.root
        cookie = 1
        nc = self.GetChildrenCount(parent, False)
        GetChild = self.GetFirstChild
        for i in range(nc):
            child, cookie = GetChild(parent, cookie)
            GetChild = self.GetNextChild
            yield child

    def child_count(self, parent):
        if parent == -1:
            parent = self.root
        else:
            parent = self[parent]
        nc = self.GetChildrenCount(parent, False)
        return nc

    def _set_selection(self, item):
        self.SelectItem(self[item])
    selection = property(fset=_set_selection)
    
    def remove_all(self):
        if self.root is None:
            return
        self.DeleteAllItems()
        self.root = None

    def get_collapse(self):
        if self.root is None:
            return None
        tmp = []
        for item in self.walk():
            tmp.append(item.IsExpanded())
        return tmp, self.item

    def update_node(self, node, names, hides=None, models=None):
        """\
        Updates the content of a plot node. Adds/removes child nodes automatically.
        nodes: tuple of (plot, names)
               plot: plot id
               names: list of names of the set names
        """

        deleted = 0 
        for n in range(max(len(names),self.child_count(node))):
            hide = False
            model = False
            try:
                name = names[n]
            except IndexError:
                if node == -1:
                    self.Delete(self[n-deleted])
                    #print 'deleting node',n-deleted
                else:
                    self.Delete(self[node,n-deleted])
                    #print 'deleting node',node,n-deleted
                deleted += 1
            else:
                if hides is not None:
                    hide = hides[n]
                if models is not None:
                    model = models[n]
                self.set_item(node, n, name, hide, model)
    
    def build(self, project):
        """\
        Builds the tree according to the structure stored in plots.
        """

        self.remove_all()

        if self.root is None:
            self.root = self.AddRoot(project.name)

        if len(project) == 0:
            self.item = None
            return
        
        pcount = 0
        self._update = True
        select = None
        for psig,plot in enumerate(project):
            lastplot = self.set_item(-1, psig, plot.name)
            if psig == 0:
                select = lastplot
            for ssig,set in enumerate(plot):
                lastset = self.set_item(psig, ssig, set.name, set.hide, set.model is not None)
            pcount += 1
        self._update = False

        self.SelectItem(select)
        self.EnsureVisible(select)

    ### scrolling while dragging
        
    def OnMouseLeftUp(self, evt):
        self.Unbind(wx.EVT_MOTION)
        self.Unbind(wx.EVT_LEFT_UP)
        evt.Skip()
        
    def OnMotion(self, evt):
        size = self.GetSize()
        x,y = evt.GetPosition()
        
        if y < 0 or y > size[1] and not hasattr(self, 'timer'):
            self.timer = wx.Timer(self)
            self.timer.Start(70)
        evt.Skip()
        
    def OnTime(self, evt):
        x,y = self.ScreenToClient(wx.GetMousePosition())
        size = self.GetSize()

        if y < 0:
            self.ScrollUp()
        elif y > size[1]:
            self.ScrollDown()
        else:
            del self.timer
            return
        self.timer.Start(70)
        
    def ScrollUp(self):
        if "wxMSW" in wx.PlatformInfo:
            self.ScrollLines(-1)
        else:
            first = self.GetFirstVisibleItem()
            prev = self.GetPrevSibling(first)
            if prev:
                while self.IsExpanded(prev):
                    prev = self.GetLastChild(prev)
            else:
                prev = self.GetItemParent(first)

            if prev:
                self.ScrollTo(prev)
            else:
                self.EnsureVisible(first)

    def ScrollDown(self):
        if "wxMSW" in wx.PlatformInfo:
            self.ScrollLines(1)
        else:
            # first find last visible item by starting with the first
            next = None
            last = None
            item = self.GetFirstVisibleItem()
            while item:
                if not self.IsVisible(item): break
                last = item
                item = self.GetNextVisible(item)

            # figure out what the next visible item should be,
            # either the first child, the next sibling, or the
            # parent's sibling
            if last:
                if self.IsExpanded(last):
                    next = self.GetFirstChild(last)[0]
                else:
                    next = self.GetNextSibling(last)
                    if not next:
                        prnt = self.GetItemParent(last)
                        if prnt:
                            next = self.GetNextSibling(prnt)

            if next:
                self.ScrollTo(next)
            elif last:
                self.EnsureVisible(last)

        
