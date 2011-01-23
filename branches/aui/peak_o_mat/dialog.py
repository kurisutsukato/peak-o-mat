import wx
import misc
import os

class ImportDialog(wx.Dialog, misc.xrcctrl):
    def __init__(self):
        self.one_plot_each = False
        pre = wx.PreDialog()
        self.PostCreate(pre)
        if os.name == 'posix':
            self.Bind(wx.EVT_WINDOW_CREATE, self.OnCreate)
        else:
            wx.CallAfter(self._PostInit)

    def OnCreate(self, event):
        self.Unbind(wx.EVT_WINDOW_CREATE)
        wx.CallAfter(self._PostInit)
        event.Skip()
        return True

    def _PostInit(self):
        self['xrc_btn_single'].Bind(wx.EVT_BUTTON, self.OnSingle)
        self['xrc_btn_oneeach'].Bind(wx.EVT_BUTTON, self.OnEach)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        self.EndModal(wx.ID_CANCEL)
        
    def OnSingle(self, evt):
        self.one_plot_each = False
        self.EndModal(wx.ID_OK)

    def OnEach(self, evt):
        self.one_plot_each = True
        self.EndModal(wx.ID_OK)

class ExportDialog(wx.Dialog, misc.xrcctrl):
    def __init__(self):
        pre = wx.PreDialog()
        self.PostCreate(pre)
        if os.name == 'posix':
            self.Bind(wx.EVT_WINDOW_CREATE, self.OnCreate)
        else:
            wx.CallAfter(self._PostInit)

    def OnCreate(self, event):
        self.Unbind(wx.EVT_WINDOW_CREATE)
        wx.CallAfter(self._PostInit)
        event.Skip()
        return True

    def _PostInit(self):
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
    
