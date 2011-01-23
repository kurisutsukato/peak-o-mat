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
import string
import re
import types
import cPickle
import os

from wx.lib.pubsub import pub as Publisher
from wx.lib.customtreectrl import CustomTreeCtrl

import spec, project

if os.name == 'posix':
    CustomTreeCtrl = wx.TreeCtrl

class TreeCtrl(CustomTreeCtrl):
    def __init__(self, parent):
        style = wx.TR_EDIT_LABELS|wx.TR_HAS_BUTTONS|wx.TR_MULTIPLE|wx.TR_HIDE_ROOT
        CustomTreeCtrl.__init__(self, parent, style=style)
        self.item = None
        self.root = None

        self._drag = False
        self._update = False
        
        self.root = self.AddRoot('project tree')
        
        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.icon_plot = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz))
        self.icon_set = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self.icon_hide = il.Add(wx.ArtProvider_GetBitmap(wx.ART_CROSS_MARK, wx.ART_OTHER, isz))

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
                self.SetPyData(p_item, -1)
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
                    self.SetPyData(s_item, -1)
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
            if self.GetItemParent(self.GetSelections()[0]) != self.GetItemParent(item):
                evt.Veto()
            if self.isPlot(self.GetSelections()[0]):
                evt.Veto()
        else:
            evt.Skip()

    def OnEdit(self, evt):
        self.EditLabel(self.item)

    def OnBeginEdit(self,evt):
        if self.item == self.root:
            evt.Veto()
            return
        name = self.GetItemText(evt.GetItem())
        self.item_old_name = name
        name = re.match(r'[sp]\d+\s(.+)',name).groups()[0]
        self.SetItemText(evt.GetItem(), name)
        
    def OnEndEdit(self, evt):
        name = evt.GetLabel()
        item = evt.GetItem()
        set = None
        
        if name != '':
            parent = self.GetItemParent(self.item)
            if parent == self.root:
                plot = self.GetPyData(self.item)
            else:
                plot = self.GetPyData(parent)
                set = self.GetPyData(self.item)
            Publisher.sendMessage(('tree','rename'),(plot,set,name))
        else:
            self.SetItemText(item, self.item_old_name)
        
    def PASS(self):
        pass

    def initMenus(self):
        self.menumap = [(-1,'edit label',self.OnEdit),
                           (-1,'delete',self.OnRemItem),
                           (-1,'duplicate',self.OnDuplicate),
                           (-1,'new sets from visible area',self.OnNewSetsFromVisArea),
                           (-1,'copy to data grid',self.OnSpreadsheet),
                           (wx.ID_SEPARATOR, '', self.PASS),
                           (-1,'toggle visibility',self.OnHide),
                           (wx.ID_SEPARATOR, '', self.PASS),
                           (-1,'remove mask',self.OnUnmask),
                           (-1,'remove trafos',self.OnRemTrafo),
                           (-1,'remove fit',self.OnRemFit),
                           (-1,'remove weights',self.OnRemError),
                           (wx.ID_SEPARATOR, '', self.PASS),
                           (-1,'insert plot',self.OnInsertPlot),
                           (-1,'copy',self.OnCopy),
                           (-1,'paste',self.OnPaste)]

        self.menu = wx.Menu()
        self.minimal_menu = wx.Menu()
        
        for id,text,act in self.menumap:
            item = wx.MenuItem(self.menu, id=id, text=text)
            item = self.menu.AppendItem(item)
            self.Bind(wx.EVT_MENU, act, item)
            if text.find('plot') != -1:
                self.Bind(wx.EVT_UPDATE_UI, self.OnUIMenu, item)
                
        item = wx.MenuItem(self.minimal_menu, id=-1, text='paste')
        item = self.minimal_menu.AppendItem(item)
        self.Bind(wx.EVT_MENU, self.OnPaste, item)
        item = wx.MenuItem(self.minimal_menu, id=-1, text='add_plot')
        item = self.minimal_menu.AppendItem(item)
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
            paste = self.menu.FindItemById(self.menu.FindItem('paste'))
            paste.Enable(self.check_clipboard())
            self.PopupMenu(self.menu, evt.GetPosition())

    def OnAddPlot(self, evt):
        Publisher.sendMessage(('tree','addplot'))

    def OnCopy(self, evt):
        Publisher.sendMessage(('tree','copy'))

    def OnPaste(self, evt):
        Publisher.sendMessage(('tree','paste'))

    def OnHide(self, evt):
        Publisher.sendMessage(('tree','hide'))

    def OnDuplicate(self, evt):
        Publisher.sendMessage(('tree','duplicate'),self.isPlot(self.item))

    def OnNewSetsFromVisArea(self, evt):
        Publisher.sendMessage(('tree','newfromvisarea'),self.isPlot(self.item))

    def OnSpreadsheet(self, evt):
        Publisher.sendMessage(('tree','togrid'))

    def OnNewFrame(self, evt):
        return
        num = self.GetPyData(self.item)
        Publisher.sendMessage(('tree','insert'), count)

    def OnInsertPlot(self, evt):
        loc = self.GetPyData(self.item)
        Publisher.sendMessage(('tree','insert'), loc)
    
    def OnRemFit(self, evt=None):
        Publisher.sendMessage(('tree','remfit'))

    def OnRemError(self, evt=None):
        Publisher.sendMessage(('tree','remerror'))

    def OnRemTrafo(self, evt=None):
        Publisher.sendMessage(('tree','remtrafo'))
            
    def OnUnmask(self, evt=None):
        Publisher.sendMessage(('tree','unmask'))
            
    def OnRemItem(self, evt):
        Publisher.sendMessage(('tree','delete'),self.isPlot(self.item))

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
                s_plot, t_plot = [self.GetPyData(x) for x in [source, target]]
                s_sets = None
                t_set = None
        else:
            s_sets = [self.GetPyData(x) for x in self.dragitem]

            if self.GetItemParent(target) != self.root:
                t_set = self.GetPyData(target)
                target = self.GetItemParent(target)
            else:
                t_set = 0
                
            s_plot = self.GetPyData(self.GetItemParent(self.dragitem[0]))
            t_plot = self.GetPyData(target)

        self._drag = False
        
        Publisher.sendMessage(('tree','move'),(s_plot, s_sets, t_plot, t_set))

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
            plotnum = self.GetPyData(evt.GetItem())
        else:
            plotnum = self.GetPyData(self.GetItemParent(item))
            if len(self.GetSelections()) > 1:
                setnum = []
                for sel in self.GetSelections():
                    setnum.append(self.GetPyData(sel))
            else:
                setnum = [self.GetPyData(evt.GetItem())]
        evt.Skip()
        Publisher.sendMessage(('tree','select'),(plotnum,setnum))

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
                data = cPickle.loads(data)
                return type(data) == spec.Spec or type(data) == project.Plot or type(data) == list
        return False
    
    def isPlot(self, item):
        return self.GetItemParent(item) == self.root

    def set_item(self, parent, child, name, hide=False):
        item = self[[child,(parent,child)][int(parent != -1)]]
        
        self.SetPyData(item, child)
        if parent == -1:
            self.SetItemImage(item, self.icon_plot, wx.TreeItemIcon_Normal)
            self.SetItemText(item, 'p%d %s'%(child,name))
        elif hide:
            self.SetItemImage(item, self.icon_hide, wx.TreeItemIcon_Normal)
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

    def update_node(self, node, names, hides=False):
        """\
        Updates the content of a plot node. Adds/removes child nodes automatically.
        nodes: tuple of (plot, names)
               plot: plot id
               names: list of names of the set names
        """

        deleted = 0 
        for n in range(max(len(names),self.child_count(node))):
            hide = False
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
                try:
                    hide = hides[n]
                except TypeError:
                    pass
                self.set_item(node, n, name, hide)
    
    def build(self, project):
        """\
        Builds the tree accordings to the structure stored in plots.
        """
        self.remove_all()

        if self.root is None:
            self.root = self.AddRoot('project')

        if len(project) == 0:
            self.item = None
            return
        
        pcount = 0
        self._update = True
        for psig,plot in enumerate(project):
            lastplot = self.set_item(-1, psig, plot.name)
            for ssig,set in enumerate(plot):
                lastset = self.set_item(psig, ssig, set.name)
            pcount += 1
        self._update = False
        self.SelectItem(lastset)
        self.EnsureVisible(lastset)

    ### next part is the 'scrolling while dragging' code
        
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
                # drill down to find last expanded child
                while self.IsExpanded(prev):
                    prev = self.GetLastChild(prev)
            else:
                # if no previous sub then try the parent
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

        
