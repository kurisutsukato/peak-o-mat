import wx
import wx.html as html
import wx.adv as adv

import sys

from . import misc
from . import plotcanvas
from . import controls
from . import tree
from .menu import menu_ids
from . import images
from .misc_ui import xrc_resource
from .dialog import ImportDialog, ExportDialog

from peak_o_mat import __version__

class Splash(adv.SplashScreen):
    def __init__(self, parent):
        self.parent = parent
        bmp = images.get_bmp('logo.png')
        if __version__ != 'svn':
            ver = 'version %s'%__version__
            memoryDC = wx.MemoryDC()
            memoryDC.SelectObject(bmp)
            memoryDC.SetFont(wx.Font(10,wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            (verWidth, verHeight) = memoryDC.GetTextExtent(ver)

            memoryDC.DrawText(ver, 400 - verWidth -5 , 230 - verHeight - 5)
            memoryDC.SelectObject(wx.Bitmap(10, 10))
        adv.SplashScreen.__init__(self, bmp,
                                 adv.SPLASH_CENTRE_ON_SCREEN|adv.SPLASH_NO_TIMEOUT, -1, None)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def Close(self):
        try:
            adv.SplashScreen.Close(self)
        except RuntimeError:
            pass

    def OnClose(self, evt):
        evt.Skip()
        self.Hide()

class App(wx.App):
    def OnInit(self):
        self.Init()
        return True

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???"""
        self.GetTopWindow().Raise()

class MainFrame(wx.Frame):
    _import_filetype = 0


    def __init__(self, silent=False, plotserver=False):
        super(MainFrame, self).__init__(None)

        #self.app = wx.GetApp()
        if not silent:
            self.splash = Splash(self)

        self.setup_controls()
        self.layout()

    def layout(self):
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.splitwin,1,wx.EXPAND)
        self.SetSizer(box)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.EXPAND)
        vbox.Add(self.nb_modules, 0, wx.EXPAND)
        hbox.Add(vbox, 1, wx.EXPAND|wx.BOTTOM, 4)
        hbox.Add(self.tb_canvas, 0, wx.EXPAND)
        self.pan_plot.SetSizer(hbox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(wx.StaticText(self.pan_tree, label='Project structure'), 0, wx.EXPAND)
        vbox.Add(self.tree, 1, wx.EXPAND)
        vbox.Add(wx.StaticText(self.pan_tree, label='Figures'), 0, wx.EXPAND)
        self.pan_tree.SetSizer(vbox)

    def setup_controls(self):
        self.id = 'ID'+str(id(self))

        self.statusbar = controls.Status(self)
        self.SetStatusBar(self.statusbar)

        self.create_menus(plotserver=False)

        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(self.menubar.GetMenu(0))

        self.splitwin = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE|wx.SP_THIN_SASH)

        self.pan_plot = wx.Panel(self.splitwin)
        self.pan_tree = wx.Panel(self.splitwin)

        self.tb_canvas = controls.Toolbar(self.pan_plot)
        self.canvas = plotcanvas.Canvas(self.pan_plot, name='canvas')
        self.nb_modules = wx.Notebook(self.pan_plot)
        self.tree = tree.TreeCtrl(self.pan_tree)

        self.splitwin.SetMinimumPaneSize(20)
        self.splitwin.SplitVertically(self.pan_plot, self.pan_tree, -100)

        self.res = xrc_resource()
        self.frame_annotations = self.res.LoadFrame(self, 'frame_annotations')
        self.frame_annotations = Annotations(self)
        #self.pan_annotations = wx.FindWindowByName('pan_annotations', self.frame_annotations)
        self.txt_annotations = wx.FindWindowByName('txt_annotations', self.frame_annotations)
        self.txt_annotations = self.frame_annotations.txt_annotations

        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)
        self.frame_annotations.SetIcon(ico)

    def create_menus(self, plotserver=False):
        mb = wx.MenuBar()
        self.menubar = mb

        def _q(arg):
            mid = arg.split('\t')[0]
            return menu_ids[mid], arg

        file_menu = wx.Menu()
        file_menu.Append(*_q('New'))
        file_menu.Append(*_q('Open project...'))
        file_menu.Append(*_q('Save as...'))
        file_menu.Append(*_q('Save\tCTRL-s'))
        file_menu.AppendSeparator()
        file_menu.Append(*_q('Quit\tCTRL-q'))

        data_menu = wx.Menu()
        data_menu.Append(*_q('Import...'))
        data_menu.Append(*_q('Export...'))

        extras_menu = wx.Menu()
        extras_menu.AppendCheckItem(*_q('Code Editor\tCTRL-e'))
        extras_menu.AppendCheckItem(*_q('Data Grid\tCTRL-d'))
        extras_menu.AppendCheckItem(*_q('Notepad\tCTRL-i'))

        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About peak-o-mat")

        mb.Append(file_menu, 'File')
        mb.Append(data_menu, 'Data')
        mb.Append(extras_menu, 'View')
        if plotserver:
            tools_menu = wx.Menu()
            tools_menu.Append(*_q('Start plot server'))
            mb.Append(tools_menu, 'Tools')
        mb.Append(help_menu, "&Help")

        self.SetMenuBar(mb)

    def check_menu(self, item, state):
        self.menubar.Check(menu_ids[item], state)
        
    def get_filehistory(self):
        return [self.filehistory.GetHistoryFile(n) for n in reversed(list(range(self.filehistory.GetCount())))]

    def _set_silent(self, state):
        self.SetEvtHandlerEnabled(not state)
    silent = property(fset=_set_silent)

    def _get_title(self):
        return self.GetTitle()
    def _set_title(self, title):
        self.SetTitle(title)
    title = property(_get_title,_set_title)
        
    def _get_annotations(self):
        return self.txt_annotations.GetValue()
    def _set_annotations(self, txt):
        self.silent = True
        self.txt_annotations.SetValue(txt)
        self.txt_annotations.SetInsertionPointEnd()
        self.silent = False
    annotations = property(_get_annotations,_set_annotations)

    def close_splash(self):
        try:
            self.splash.Close()
        except wx._core.PyDeadObjectError:
            pass
        
    def start(self, startapp=False):
        self.SetSize((1024,720))
        self.CenterOnScreen()
        self.Layout()
        self.Show()

        if hasattr(self, 'splash'):
            self.splash.Raise()
            wx.CallLater(1000, self.splash.Close)
        self.splitwin.SetSashPosition(760, True)

        if startapp:
            if sys.platform == 'darwin':
                self.tbicon = TaskBarIcon(self)
            wx.GetApp().MainLoop()

    def load_file_dialog(self, path):
        wc = "peak-o-mat Project files (*.lpj)|*.lpj"
        dlg = wx.FileDialog(self, defaultDir=path, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            dlg.Destroy()
            return None
                
    def save_file_dialog(self, path):
        dlg = wx.FileDialog(self, defaultFile="", defaultDir=path, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT, wildcard="peak-o-mat Project files (*.lpj)|*.lpj")
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            dlg.Destroy()
            return None

    def error_dialog(self, msg):
        self.close_splash()
        self.Raise()
        dlg = wx.MessageDialog(self,str(msg),'Error',style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()

    def msg_dialog(self, msg, title='Notice', yesno=False):
        try:
            # to avoid that the message dialog is hidden by the splash screen
            self.close_splash()
        except AttributeError:
            pass
        self.Raise()
        style = wx.ICON_INFORMATION
        if yesno:
            style |= wx.YES_NO|wx.NO_DEFAULT
        else:
            style |= wx.OK
        dlg = wx.MessageDialog(self,str(msg),title,style)
        return dlg.ShowModal()

    def close_project_dialog(self, name):
        self.Raise()
        dlg = wx.MessageDialog(self,'Project has been modified. Really close \'%s\'?'%name,'Warning',style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            return True
        else:
            dlg.Destroy()
            return False

    def export_excel_dialog(self, def_dir, name=''):
        wc = "Excel files (*.xls)|*.xls"
        dlg = wx.FileDialog(self, defaultDir=def_dir, defaultFile=name,
                            style=wx.SAVE|wx.OVERWRITE_PROMPT, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            return None

    def export_dialog_multi(self, def_dir):
        dlg = ExportDialog(self)
        wx.FindWindowByName('xrc_txt_dir', dlg).SetValue(str(misc.cwd()))
        if dlg.ShowModal() == wx.ID_OK:
            out = dlg.dir, dlg.ext, dlg.onlyvisible, dlg.overwrite
            dlg.Destroy()
            return out
        else:
            return None

    def export_dialog_single(self, def_dir, name=''):
        dlg = wx.FileDialog(self, defaultDir=def_dir, defaultFile=name, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            return None

    def import_dialog(self, def_dir,wildcards='All files (*.*)|*.*'):
        #dlg = wx.FileDialog(self, defaultDir=def_dir, wildcard="data files (*.dat,*.txt,*.csv)|*.dat;*.txt;*.csv|All files (*)|*", style=wx.OPEN|wx.MULTIPLE)
        dlg = wx.FileDialog(self, defaultDir=def_dir, wildcard=wildcards, style=wx.FD_OPEN|wx.FD_MULTIPLE)
        dlg.SetFilterIndex(self._import_filetype)
        if dlg.ShowModal() == wx.ID_OK:
            one_plot_each = False
            path = dlg.GetPaths()
            if len(path) > 1:
                ask = ImportDialog(self)
                if ask.ShowModal() == wx.ID_OK:
                    one_plot_each = ask.one_plot_each
                    ask.Destroy()
            self._import_filetype = dlg.GetFilterIndex()
            dlg.Destroy()
            return path, one_plot_each
        return None

    def about_dialog(self):
        About(self)


license = """\
<body bgcolor='%s'>
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.<br /><br />

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.<br /><br />

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
</body>
"""

about = """
<body bgcolor='%s'>
<table width='100%%'>
<tr><td width='10'></td>
<td>
<b>peak-o-mat</b><br /><br />
A multi purpose curve fitting program written in python.<br /><br />
(c) 2003-2016 Christian Kristukat (ckkart@hoc.net)<br /><br />
http://lorentz.sf.net
</td><td width='10'></td></tr>
</table>
</body>
"""
        
class About(wx.Dialog):    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, title='peak-o-mat')
        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.SetIcon(ico)

        logo = wx.StaticBitmap(self, -1)
        logo.SetBitmap(images.get_bmp('logosmall.png'))
        title = wx.StaticText(self, -1, 'peak-o-mat %s'%__version__)
        nb = wx.Notebook(self, -1)

        pan_about = html.HtmlWindow(nb, -1)
        pan_license = html.HtmlWindow(nb, -1)

        bgcolor = '#'+''.join(['%02x'%c for c in wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)])
        pan_about.SetPage(about%bgcolor)
        pan_license.SetPage(license%bgcolor)

        nb.AddPage(pan_about, 'About')
        nb.AddPage(pan_license, 'License')
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        hbox.Add(logo, 0, wx.ALL, 5)
        hbox.Add(title, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 10)

        vbox.Add(nb, 1, wx.EXPAND|wx.ALL, 10)

        self.SetSizer(vbox)

        self.CenterOnParent()
        self.ShowModal()
        
class TaskBarIcon(adv.TaskBarIcon):
    TBMENU_RESTORE = wx.NewId()
    TBMENU_CLOSE   = wx.NewId()
    TBMENU_CHANGE  = wx.NewId()
    TBMENU_REMOVE  = wx.NewId()

    def __init__(self, frame):
        try:
            adv.TaskBarIcon.__init__(self, iconType=adv.TBI_DOCK)
        except AttributeError:
            adv.TaskBarIcon.__init__(self)
        self.frame = frame

        # Set the image
        icon = self.MakeIcon()

        self.SetIcon(icon, "peak-o-mat")
        self.imgidx = 1

        # bind some events
        self.Bind(adv.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=self.TBMENU_RESTORE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)


    def CreatePopupMenu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        menu = wx.Menu()
        menu.Append(self.TBMENU_RESTORE, "Restore peak-o-mat")
        menu.Append(self.TBMENU_CLOSE,   "Close peak-o-mat")
        return menu


    def MakeIcon(self):
        if 'wxMSW' in wx.PlatformInfo or 'wxGTK' in wx.PlatformInfo:
            img = images.get_img('logosmall.png')
        else:
            img = images.get_img('logo_taskbar.png')
        bmp = img.ConvertToBitmap()
        icon = wx.Icon(bmp)
        return icon


    def OnTaskBarActivate(self, evt):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()

    def OnTaskBarClose(self, evt):
        wx.CallAfter(self.frame.Close)

class Annotations(wx.Frame):
    def __init__(self, *args):
        super(Annotations, self).__init__(*args)
        p = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)
        self.txt_annotations = wx.TextCtrl(p, style=wx.TE_MULTILINE)
        fnt = wx.Font(10, wx.TELETYPE, wx.NORMAL, wx.NORMAL)
        self.txt_annotations.SetFont(fnt)

        box.Add(self.txt_annotations, 1, wx.EXPAND|wx.ALL, 5)
        p.SetSizer(box)

if __name__ == '__main__':
    import wx.xrc as xrc

    class Frame(wx.Frame):

        def __init__(self, silent=False):
            wx.Frame.__init__(self)

            #self.app = wx.GetApp()
            #if not silent:
            #    self.splash = Splash(self)

            res = xrc.XmlResource('peak-o-mat.xrc')

            res.LoadFrame(self, None, "frame_annotations")

            #self.Create(None)
            #self.SetTitle('test')
            print(wx.FindWindowByName('canvas',self))
            return

    app = wx.App()
    f = Frame()
    f.Show()
    app.MainLoop()
