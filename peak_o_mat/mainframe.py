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
import wx.html as html

import numpy as N

import os
import sys

import misc
import plotcanvas
import misc
import project
import spec
import dialog
import controls
import tree


from peak_o_mat import __version__

import settings as config

class POM(wx.App):
    def OnInit(self):
        return True
    
class Splash(wx.SplashScreen):
    def __init__(self, parent):
        self.parent = parent
        bmp = misc.get_bmp('logo.png')
        if __version__ != 'svn':
            ver = 'version %s'%__version__
            memoryDC = wx.MemoryDC()
            memoryDC.SelectObject(bmp)
            memoryDC.SetFont(wx.Font(10,wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            (verWidth, verHeight) = memoryDC.GetTextExtent(ver)

            memoryDC.DrawText(ver, 400 - verWidth -5 , 230 - verHeight - 5)
            memoryDC.SelectObject(wx.EmptyBitmap(10, 10))
        wx.SplashScreen.__init__(self, bmp,
                                 wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_NO_TIMEOUT, -1, None)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        evt.Skip()
        self.Hide()


class MainFrame(wx.Frame):
    _import_filetype = 0
    
    def __init__(self):
        self.app = wx.App(0)
        self.splash = Splash(self)

        pre = wx.PreFrame()
        self.res = misc.xrc_resource()
        self.res.LoadOnFrame(pre, None, "mainframe")
        self.PostCreate(pre)

        self.statusbar = controls.Status(self)
        self.SetStatusBar(self.statusbar)

        self.menubar = self.GetMenuBar()
        self.filehistory = wx.FileHistory()
        self.filehistory.UseMenu(self.menubar.GetMenu(0))
        
        self.canvas = plotcanvas.Canvas(self)
        self.res.AttachUnknownControl('canvas', self.canvas)

        self.tb_canvas = controls.Toolbar(wx.FindWindowByName('pan_plot'))
        self.res.AttachUnknownControl('buttonbar', self.tb_canvas)

        self.tree = tree.TreeCtrl(wx.FindWindowByName('pan_tree'))
        self.res.AttachUnknownControl('tree', self.tree)

        self.nb_modules = wx.FindWindowByName('nb_modules')
        #self.btn_tree_addplot = wx.FindWindowByName('btn_tree_addplot')
        #self.btn_tree_remfits = wx.FindWindowByName('btn_tree_remfits')
        #self.btn_tree_remtrafos = wx.FindWindowByName('btn_tree_remtrafos')
        #self.btn_tree_unmask = wx.FindWindowByName('btn_tree_unmask')

        self.pan_plot = wx.FindWindowByName('pan_plot')
        
        self.frame_annotations = self.res.LoadFrame(self, 'frame_annotations')
        self.pan_annotations = self.frame_annotations.FindWindowByName('pan_annotations')
        self.txt_annotations = self.frame_annotations.FindWindowByName('txt_annotations')
        #self.frame_annotations.Show()
        
        #self.nb_main = wx.FindWindowByName('nb_main')
        
        self.splitwin = wx.FindWindowByName('splitwin')
        self.splitwin.SetSashGravity(1.0)
        
        ico = wx.EmptyIcon()
        ico.CopyFromBitmap(misc.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)
        self.frame_annotations.SetIcon(ico)

    def get_filehistory(self):
        return [self.filehistory.GetHistoryFile(n) for n in reversed(range(self.filehistory.GetCount()))]

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
        
    def start(self):
        self.SetSize((1024,700))
        self.Show()
        self.splash.Raise()
        wx.FutureCall(1000, self.splash.Close)
        self.splitwin.SetSashPosition(824, True)
        self.app.MainLoop()

    def load_file_dialog(self, path):
        wc = "peak-o-mat Project files (*.lpj)|*.lpj|XMGrace Project files (*.agr)|*.agr"
        dlg = wx.FileDialog(self, defaultDir=path, wildcard=wc)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            dlg.Destroy()
            return None
                
    def save_file_dialog(self, path):
        dlg = wx.FileDialog(self, defaultFile="", defaultDir=path, style=wx.SAVE|wx.OVERWRITE_PROMPT, wildcard="peak-o-mat Project files (*.lpj)|*.lpj")
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            dlg.Destroy()
            return None

    def error_dialog(self, msg):
        self.Raise()
        dlg = wx.MessageDialog(self,unicode(msg),'Error',style=wx.OK|wx.ICON_ERROR)
        dlg.ShowModal()

    def msg_dialog(self, msg):
        self.Raise()
        dlg = wx.MessageDialog(self,unicode(msg),'Notice',style=wx.OK|wx.ICON_INFORMATION)
        dlg.ShowModal()

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
        dlg = self.res.LoadDialog(self, 'xrc_dlg_export')
        dlg.FindWindowByName('xrc_txt_dir').SetValue(unicode(misc.cwd()))
        if dlg.ShowModal() == wx.ID_OK:
            out = dlg.dir, dlg.ext, dlg.onlyvisible, dlg.overwrite
            dlg.Destroy()
            return out
        else:
            return None

    def export_dialog_single(self, def_dir, name=''):
        dlg = wx.FileDialog(self, defaultDir=def_dir, defaultFile=name, style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            dlg.Destroy()
            return path
        else:
            return None

    def import_dialog(self, def_dir):
        dlg = wx.FileDialog(self, defaultDir=def_dir, wildcard="plain data (*.dat)|*.dat|text (*.txt)|*.txt;*.TXT|Dilor (*.ms0)|*.ms0|All files (*)|*", style=wx.OPEN|wx.MULTIPLE)
        dlg.SetFilterIndex(self._import_filetype)
        if dlg.ShowModal() == wx.ID_OK:
            one_plot_each = False
            path = dlg.GetPaths()
            if len(path) > 1:
                ask = self.res.LoadDialog(self,'xrc_dlg_import')
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
(c) 2003-2007 Christian Kristukat (ckkart@hoc.net)<br /><br />
http://lorentz.sf.net
</td><td width='10'></td></tr>
</table>
</body>
"""
        
class About(wx.Dialog):    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, title='peak-o-mat')
        ico = wx.EmptyIcon()
        ico.CopyFromBitmap(misc.get_bmp('logosmall.png'))
        self.SetIcon(ico)

        logo = wx.StaticBitmap(self, -1)
        logo.SetBitmap(misc.get_bmp('logosmall.png'))
        title = wx.StaticText(self, -1, 'peak-o-mat %s'%__version__)
        nb = wx.Notebook(self, -1)

        pan_about = html.HtmlWindow(nb, -1)
        pan_license = html.HtmlWindow(nb, -1)

        bgcolor = '#'+''.join(['%02x'%c for c in wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)])
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

        self.ShowModal()
        
if __name__ == '__main__':
    app = wx.PySimpleApp(0)
    f = wx.Frame(None, -1)
    f.Show()
    dlg = About(f)
    app.MainLoop()
