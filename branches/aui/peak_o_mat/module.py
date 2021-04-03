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

class BaseModule(misc_ui.WithMessage):

    def __init__(self, controller, view):
        self.visible = False
        self.need_attention = False
        self.plotme = None
        self._last_page = None

        self.parent_view = view
        self.parent_controller = controller
        self.project = controller.project

        self.name = os.path.splitext(os.path.basename(__file__))[0]
        self.view = None

    def init(self):
        assert hasattr(self, 'title')
        misc_ui.WithMessage.__init__(self, self.view)

        self.parent_controller.view._mgr.Update()

        pub.subscribe(self.OnSelectionChanged, (self.instid, 'selection', 'changed'))
        pub.subscribe(self.focus_changed, (self.instid, 'module', 'focuschanged'))

    def focus_changed(self, newfocus):
        pass

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

class XRCModule(misc_ui.WithMessage):
    def __init__(self, module, controller, doc):
        self.visible = False
        self.need_attention = False
        self.plotme = None
        self._last_page = None

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

        assert hasattr(self, 'title')

        module_dir = os.path.dirname(module)
        module = os.path.splitext(os.path.basename(module))[0]

        if hasattr(sys, "frozen") and sys.frozen in ['windows_exe', 'console_exe']:
            xrcfile = os.path.join(misc.frozen_base, 'xrc', module + '.xrc')
        elif hasattr(sys, "frozen") and sys.platform == "darwin":
            xrcfile = os.path.join(misc.darwin_base, 'xrc', module + '.xrc')
        else:
            xrcfile = os.path.join(module_dir, module + '.xrc')

        self.name = module
        self.xmlres = xrc.XmlResource(xrcfile)

        if self.xmlres is not None:
            self.view = self.xmlres.LoadPanel(controller.view, self.name)
            self.view.Fit()
            self.view.SetMinSize(self.view.GetSize())

            misc_ui.WithMessage.__init__(self, self.view)
            controller.view._mgr.AddPane(self.view, aui.AuiPaneInfo().Float().
                                         Dockable(True).Caption(self.title).MinSize(self.view.GetSize()).
                                         Name(self.title).Hide())
            controller.view._mgr.Update()

            if self.view is None:
                raise IOError('unable to load wx.Panel \'%s\' from %s' % (self.name, xrcfile))
            print('registering module \'%s\'' % (self.name))

            controller.view.menu_factory.add_module(controller.view.menubar, self.title)
            pub.subscribe(self.OnSelectionChanged, (self.instid, 'selection', 'changed'))
            pub.subscribe(self.focus_changed, (self.instid, 'module', 'focuschanged'))

            wx.CallAfter(self.init)
        else:
            raise IOError(xrcfile + ' not found')

        self.view.Bind(wx.EVT_BUTTON, self.OnHelp)

    def init(self):
        pass
        # should be overridden

    def __getattr__(self, name):
        if name.find('xrc_') == 0:
            ctrl = xrc.XRCCTRL(self.view, name)
            if ctrl is None:
                raise AttributeError('attribute \'{}\' not found'.format(name))
            else:
                return ctrl
        else:
            raise AttributeError(name)

    def focus_changed(self, newfocus=None):
        pass

    def message(self, msg, target=1, blink=False):
        event = misc_ui.ShoutEvent(-1, msg=msg, target=target, blink=blink, forever=False)
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
        print('page_changed deprecated in module', self.title)
        pass

    def show(self, state=True):
        print(self, 'show', state)
        self.visible = state
        self.focus_changed(self)

    def hide(self):
        self.show(False)


if __name__ == '__main__':
    class Frame(wx.Frame):
        def __init__(self):
            super(Frame, self).__init__(parent=None)

            self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)

        def OnClick(self, evt):
            print('base class evt handler')


    class MyFrame(Frame):
        def __init__(self):
            super(MyFrame, self).__init__()

        def OnClick(self, evt):
            print('derived class evt handler')


    a = wx.App()
    f = MyFrame()
    f.Show()
    a.MainLoop()
