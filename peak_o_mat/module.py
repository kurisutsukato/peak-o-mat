#!/usr/bin/python

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

import wx
import wx.aui as aui

from wx import xrc
from pubsub import pub
import os, sys

from . import misc
from . import misc_ui
from . import controls
from . import menu

class Module:
    last_focus = None

    # this means that the module will plot something
    # it will steal the focus from any other module
    need_attention = False


#TODO: remove similiar code from XRCModule and BaseModule

class BaseModule(Module):

    def __init__(self, controller, view):
        self.visible = False
        self._last_page = None
        self.plotme = None
        self.parent_view = view
        self.parent_controller = controller
        self.name = os.path.splitext(os.path.basename(__file__))[0]
        self.view_id = 'ID'+str(id(wx.GetTopLevelParent(view)))
        self.view = None

    def init(self):
        assert hasattr(self, 'title')
        self.view.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        pub.subscribe(self.OnSelectionChanged, (self.view_id, 'selection','changed'))
        pub.subscribe(self.focus_changed, (self.view_id, 'module', 'focuschanged'))

    def focus_changed(self, newfocus):
        pass

    def OnEnter(self, evt):
        if(self.view.HitTest(evt.Position) == wx.HT_WINDOW_INSIDE) and Module.last_focus != self:
            if self.need_attention:
                pub.sendMessage((self.view_id,'module','focuschanged'),newfocus=self)
                Module.last_focus = self
            self.show()

    def OnSelectionChanged(self, plot, dataset):
        if self.visible:
            self.selection_changed()

    def selection_changed(self):
        pass

    def show(self, state=True):
        self.visible = state
        self.focus_changed(self)

    def hide(self):
        self.show(False)

class XRCModule(Module):

    def __init__(self, module, controller, doc):
        if module is None:
            raise Exception("""
A module's constructor must look like this:

class MyModule(module.Module):
    title = 'foo'
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
        
""")
        self.controller = controller
        self.project = controller.project
        self.doc = doc
        self.plotme = None
        self.visible = False

        self.view_id = 'ID'+str(id(wx.GetTopLevelParent(self.controller.view)))

        assert hasattr(self, 'title')

        self._last_page = None
        self.visible = False

        #self.notebook = controller.view.nb_modules
        module_dir = os.path.dirname(module)
        module = os.path.splitext(os.path.basename(module))[0]

        if hasattr(sys,"frozen") and sys.frozen in ['windows_exe','console_exe']:
            xrcfile = os.path.join(misc.frozen_base, 'xrc', module+'.xrc')
        elif hasattr(sys,"frozen") and sys.platform == "darwin":
            xrcfile = os.path.join(misc.darwin_base, 'xrc', module+'.xrc')
        else:
            xrcfile = os.path.join(module_dir, module+'.xrc')

        self.name = module
        self.xmlres = xrc.XmlResource(xrcfile)

        if self.xmlres is not None:
            #self.panel = self.xmlres.LoadPanel(self.notebook, self.name)
            self.view = self.xmlres.LoadPanel(controller.view, self.name)
            controller.view._mgr.AddPane(self.view, aui.AuiPaneInfo().Float().
                                         Dockable(True).Caption(self.title).
                                         Name(self.title).Hide())

            controller.view._mgr.Update()
            if self.view is None:
                raise IOError('unable to load wx.Panel \'%s\' from %s'%(self.name,xrcfile))
            print('registering module \'%s\''%(self.name))
            #self.notebook.AddPage(self.panel, self.title, select=False)
            #pub.subscribe(self.OnPageChanged, (self.view_id, 'notebook','pagechanged'))
            #menu.add_module(controller.view.menubar, self.title)
            controller.view.menu_factory.add_module(controller.view.menubar, self.title)
            pub.subscribe(self.OnSelectionChanged, (self.view_id, 'selection','changed'))
            pub.subscribe(self.focus_changed, (self.view_id, 'module', 'focuschanged'))

            self.view.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)

            wx.CallAfter(self.init)
            wx.CallAfter(self.view.Layout)
        else:
            raise IOError(xrcfile+' not found')

        self.view.Bind(wx.EVT_BUTTON, self.OnHelp)

    def __getattr__(self, name):
        if name.find('xrc_') == 0:
            return xrc.XRCCTRL(self.view, name)
        else:
            raise AttributeError(name)

    def focus_changed(self, newfocus=None):
        pass

    def OnEnter(self, evt):
        if(self.view.HitTest(evt.Position) == wx.HT_WINDOW_INSIDE) and Module.last_focus != self:
            if self.need_attention:
                pub.sendMessage((self.view_id,'module','focuschanged'),newfocus=self)
                Module.last_focus = self
            self.show()

    def message(self, msg, target=1, blink=False):
        event = misc_ui.ShoutEvent(-1, msg=msg, target=target, blink=blink)
        wx.PostEvent(self.view, event)

    def OnHelp(self, evt):
        # hack in order to be called with evt=None arg
        try:
            btnname = evt.GetEventObject().GetName()
        except:
            btnname = 'xrc_btn_help'
        if btnname == 'xrc_btn_help':
            dlg = controls.ScrolledMessageDialog(self.view, self.doc, self.title)

            dlg.ShowModal()
        else:
            evt.Skip()

    def OnSelectionChanged(self, plot, dataset):
        self.selection_changed()

    def selection_changed(self):
        pass

    def page_changed(self, me):
        print('page_changed deprecated in module',self.title)
        pass

    def show(self, state=True):
        self.visible = state
        self.focus_changed(self)

    def hide(self):
        self.show(False)

