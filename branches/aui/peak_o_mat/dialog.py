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
from . import misc
from . import misc_ui

class xrcctrl(object):
    def __getitem__(self, item):
        return self.FindWindowByName(item)

class ImportDialog(wx.Dialog, xrcctrl):
    def __init__(self, parent):
        wx.Dialog.__init__(self)
        self.one_plot_each = False
        self.res = misc_ui.xrc_resource()
        self.res.LoadDialog(self, parent, 'xrc_dlg_import')
        #self.Create(parent)

        self['xrc_btn_single'].Bind(wx.EVT_BUTTON, self.OnSingle)
        self['xrc_btn_oneeach'].Bind(wx.EVT_BUTTON, self.OnEach)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.CenterOnParent()

    def OnClose(self, evt):
        self.EndModal(wx.ID_CANCEL)
        
    def OnSingle(self, evt):
        self.one_plot_each = False
        self.EndModal(wx.ID_OK)

    def OnEach(self, evt):
        self.one_plot_each = True
        self.EndModal(wx.ID_OK)

class ExportDialog(wx.Dialog, xrcctrl):
    def __init__(self, parent):
        wx.Dialog.__init__(self)
        self.res = misc_ui.xrc_resource()
        self.res.LoadDialog(self, parent, 'xrc_dlg_export')
        #self.Create(parent)

        self['xrc_txt_ext'].Bind(wx.EVT_UPDATE_UI, self.OnEnterExt)
        self['xrc_lab_ext'].Bind(wx.EVT_UPDATE_UI, self.OnEnterExt)
        self['xrc_btn_export'].Bind(wx.EVT_UPDATE_UI, self.OnReadyToExport)

        self['xrc_btn_export'].Bind(wx.EVT_BUTTON, self.OnExport)
        self['xrc_btn_cancel'].Bind(wx.EVT_BUTTON, self.OnClose)
        self['xrc_btn_dir'].Bind(wx.EVT_BUTTON, self.OnSelectDir)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnEnterExt(self, evt):
        evt.Enable(self['xrc_chk_ext'].IsChecked())
        
    def OnReadyToExport(self, evt):
        evt.Enable(self['xrc_txt_dir'].GetValue() != '')

    def OnSelectDir(self, evt):
        dlg = wx.DirDialog(self, defaultPath=misc.cwd(), style=wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            dlg.Destroy()
            self['xrc_txt_dir'].SetValue(name)
        
    def OnClose(self, evt):
        self.EndModal(wx.ID_CANCEL)

    def OnExport(self, evt):
        self.dir = self['xrc_txt_dir'].GetValue()
        self.ext = [None, self['xrc_txt_ext'].GetValue()][self['xrc_chk_ext'].IsChecked()]
        self.onlyvisible = self['xrc_chk_visible'].IsChecked()
        self.overwrite = self['xrc_chk_overwrite'].IsChecked()
        self.EndModal(wx.ID_OK)
    
