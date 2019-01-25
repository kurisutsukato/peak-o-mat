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
from wx.lib.pubsub import pub
import os, sys

from . import misc
from . import misc_ui
from . import controls
from . import menu

class BaseModule(object):
    update_in_background = True

    def __init__(self, controller, view):
        self.visible = False
        self._last_page = None
        self.plotme = None
        self.parent_view = view
        self.parent_controller = controller
        self.name = os.path.splitext(os.path.basename(__file__))[0]

    def init(self):
        assert hasattr(self, 'title')
        #pub.subscribe(self.OnPageChanged, (self.view.id, 'notebook','pagechanged'))
        self.view.Bind(wx.EVT_ENTER_WINDOW, self.OnSetFocus)
        self.view.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus)
        pub.subscribe(self.OnSelectionChanged, (self.view.id, 'selection','changed'))

    def OnSetFocus(self, evt):
        self.page_changed(True)
        self.visible = True

    def OnKillFocus(self, evt):
        self.page_changed(False)
        self.visible = False

    def OnPageChanged(self, msg):
        if self.view == msg:
            self.page_changed(True)
            self.visible = True
        elif self._last_page == self.view:
            self.page_changed(False)
            self.visible = False
        self._last_page = msg

    def OnSelectionChanged(self, plot, dataset):
        if self.update_in_background or self.view.HasFocus():
            self.selection_changed()


class Module(object):
    update_in_background = False

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
            menu.add_module(controller.view.menubar, self.title)

            pub.subscribe(self.OnSelectionChanged, (self.view_id, 'selection','changed'))
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

    def OnActivated(self, evt):
        print(evt)
        evt.Skip()

    def OnPageChanged(self, msg):
        print('page changed: {}, {}'.format(self.title, msg))
        if self.view == msg:
            self.page_changed(True)
            self.visible = True
        elif self._last_page == self.view:
            self.page_changed(False)
            self.visible = False
        self._last_page = msg

    def OnSelectionChanged(self, plot, dataset):
        if self.update_in_background or self.view.HasFocus():
            self.selection_changed()
        
    def selection_changed(self):
        pass

    def page_changed(self, me):
        pass

