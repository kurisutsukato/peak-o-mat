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
import re

from . import misc
from . import misc_ui
from . import images

class xrcctrl(object):
    def __getitem__(self, item):
        return self.FindWindowByName(item)

class PairValidator(wx.Validator):
    def __init__(self, pyVar=None):
        wx.Validator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def OnChar(self, evt):
        if evt.KeyCode in [32,40,41,44]+list(range(48,58))+\
                [wx.WXK_BACK,wx.WXK_LEFT,wx.WXK_RIGHT,wx.WXK_DELETE,wx.WXK_SHIFT,wx.WXK_HOME,wx.WXK_END]+\
                [wx.WXK_CONTROL_C,wx.WXK_CONTROL_V,wx.WXK_CONTROL_X]:
            evt.Skip()

    def Clone(self):
        return PairValidator()

    def Validate(self, win):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()

        if len(re.findall(r'(\(\d+,\d+\))', text)) == 0:
            textCtrl.SetBackgroundColour("pink")
            textCtrl.SetFocus()
            textCtrl.Refresh()
            return False
        else:
            textCtrl.SetBackgroundColour(
                wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
            textCtrl.Refresh()
            return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

class ColumnDialog(wx.Dialog):
    def __init__(self, parent, name=None, collabels=None, multifile=False, numcols=None):
        wx.Dialog.__init__(self, parent, title='Multicolumn file')
        self.multifile = multifile
        self.name = name

        self.controls(collabels,numcols)
        self.layout()

        self.ch.Bind(wx.EVT_CHOICE, self.OnChoice)

    def results(self):
        custom = self.txt_custom.Value
        if self.ch.Selection == 2:
            custom = [eval(q) for q in re.findall(r'(\(\d+,\d+\))', custom)]
        else:
            custom = None
        return self.ch.Selection, custom, self.chk.IsChecked()

    def Validate(self):
        if self.ch.Selection == 2:
            return super(ColumnDialog, self).Validate()
        else:
            return True

    def OnChoice(self, evt):
        self.txt_custom.Enable(evt.Selection == 2)
        self.lab_custom.Enable(evt.Selection == 2)
        if evt.Selection == 2:
            #self.txt_custom.SetInsertionPointEnd()
            self.txt_custom.SetFocus()

    def controls(self, collabels=None, numcols=None):
        if self.name is None:
            self.lab_name = wx.StaticText(self, label='')
            self.lab_name.Hide()
        else:
            self.lab_name = wx.StaticText(self, label=self.name)

        self.ch = wx.Choice(self, choices=['XYYY..', 'XYXY..','Custom'])
        self.ch.SetSelection(0)
        self.txt_collabels = wx.TextCtrl(self, value='', style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.txt_custom = wx.TextCtrl(self, value='', validator=PairValidator(), style=wx.TE_PROCESS_ENTER)
        self.txt_custom.Disable()
        self.txt_custom.SetHint('e.g. (0,1) (0,3) (0,6) ...')

        if collabels is not None:
            self.txt_collabels.SetValue('\n'.join(['{}:{}'.format(q,p) for q,p in zip(range(len(collabels)),collabels)]))
            self.txt_collabels.SetMinSize((-1,min(len(collabels)*12,400)))
            self.lab_collab = wx.StaticText(self, label='Column labels:')
        else:
            self.lab_collab = wx.StaticText(self, label='Found {} columns without labels.'.format(numcols))
            self.txt_collabels.Hide()

        self.chk = wx.CheckBox(self, label='Apply to all files with equally shaped data.')
        if not self.multifile:
            self.chk.Hide()


    def layout(self):
        lab = wx.StaticText(self, label='Select column ordering:')
        self.lab_custom = wx.StaticText(self, label='XY pairs')
        self.lab_custom.Disable()

        box = wx.BoxSizer(wx.VERTICAL)

        if self.name is not None:
            box.Add(self.lab_name, 0, wx.ALL, 10)
            box.Add(wx.StaticLine(self, style=wx.HORIZONTAL),0,wx.EXPAND|wx.BOTTOM|wx.RIGHT|wx.LEFT,5)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.lab_collab, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbox.Add(self.txt_collabels, 1, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        box.Add(hbox, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(lab, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbox.Add(self.ch, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        box.Add(hbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.lab_custom, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        hbox.Add(self.txt_custom, 1, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 5)
        box.Add(hbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.chk, 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        box.Add(hbox, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        #box.Add((-1, 20), 0)

        btn_ok = wx.Button(self, wx.ID_OK, "OK")
        btn_ok.SetDefault()
        btn_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(btn_ok)
        buttons.AddButton(btn_cancel)
        buttons.Realize()

        box.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(box)
        box.SetSizeHints(self)
        self.Fit()

        ico = wx.Icon()
        ico.CopyFromBitmap(images.get_bmp('logosmall.png'))
        self.pom_ico = ico
        self.SetIcon(ico)

class ImportDialog(wx.Dialog, xrcctrl):
    def __init__(self, parent):
        wx.Dialog.__init__(self)
        self.one_plot_each = False
        self.res = misc_ui.xrc_resource()
        self.res.LoadDialog(self, parent, 'xrc_dlg_import')

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

if __name__ == '__main__':

    app = wx.App()
    d = ColumnDialog(None, 'test.txt', collabels=['eins', 'zwei', 'drei'], multifile=True)
    if d.ShowModal() == wx.ID_OK:
        print(d.results())
    d = ColumnDialog(None, collabels=['eins', 'zwei', 'drei']*30, multifile=True)
    if d.ShowModal() == wx.ID_OK:
        print(d.results())
