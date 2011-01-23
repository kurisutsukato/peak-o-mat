"""
the doc
"""

import wx
from wx import xrc
from wx.lib.pubsub import pub as Publisher
import os, sys

import misc
import controls

class Module(object):
    def __init__(self, module, controller, doc):
        if module is None:
            raise Exception, """
A module's constructor must look like this:

class MyModule(module.Module):
    title = 'foo'
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
        
"""
        self.controller = controller
        self.project = controller.project
        self.doc = doc
        
        if not hasattr(self, 'title'):
            self.title = 'no title'

        self._last_page = None
        self.visible = False
        
        self.notebook = controller.view.nb_modules
        module_dir = os.path.dirname(module)
        module = os.path.splitext(os.path.basename(module))[0]

        if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
            base = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding())) 
            xrcfile = os.path.join(base, 'xrc', module+'.xrc')
        else:
            xrcfile = os.path.join(module_dir, module+'.xrc')
        self.name = module
        self.xmlres = xrc.XmlResource(xrcfile)
        if self.xmlres is not None:
            self.panel = self.xmlres.LoadPanel(self.notebook, self.name)
            if self.panel is None:
                raise IOError,'unable to load wx.Panel \'%s\' from %s'%(self.name,xrcfile)
            print 'registering module \'%s\''%(self.name)
            self.notebook.AddPage(self.panel, self.title, select=False)
            Publisher.subscribe(self.OnPageChanged, ('notebook','pagechanged'))
            Publisher.subscribe(self.OnSelectionChanged, ('selection','changed'))
            wx.CallAfter(self.init)
            wx.CallAfter(self.panel.Layout)
        else:
            raise IOError, xrcfile+' not found'

        self.panel.Bind(wx.EVT_BUTTON, self.OnHelp)

    def __getattr__(self, name):
        if name.find('xrc_') == 0:
            return xrc.XRCCTRL(self.panel, name)
        else:
            raise AttributeError, name

    def message(self, msg, target=1, blink=False):
        event = misc.ShoutEvent(-1, msg=msg, target=target, blink=blink)
        wx.PostEvent(self.panel, event)

    def OnHelp(self, evt):
        # hack in order to be called with evt=None arg
        try:
            btnname = evt.GetEventObject().GetName()
        except:
            btnname = 'xrc_btn_help'
        if btnname == 'xrc_btn_help':
            dlg = controls.ScrolledMessageDialog(self.panel, self.doc, self.title)
            
            dlg.ShowModal()
        else:
            evt.Skip()
        
    def OnPageChanged(self, msg):
        if self.panel == msg.data:
            self.page_changed(True)
            self.visible = True
        elif self._last_page == self.panel:
            self.page_changed(False)
            self.visible = False
        self._last_page = msg.data
        
    def Bind(self, *args, **kwargs):
        self.panel.Bind(*args, **kwargs)

    def Unbind(self, *args, **kwargs):
        self.panel.Unbind(*args, **kwargs)

    def OnSelectionChanged(self, msg):
        if self.visible:
            self.selection_changed()
        
    def selection_changed(self):
        pass

    def page_changed(self, me):
        pass

