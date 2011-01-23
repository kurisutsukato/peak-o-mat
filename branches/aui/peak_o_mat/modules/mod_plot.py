import wx
import re
import os

import numpy as N

from peak_o_mat import module, spec, calib, grace_np, misc

WORLD_VIEW = 0.15, 0.9, 0.5, 1.3

if os.name != 'posix':
    raise Exception, 'plotting via xmgrace is only available on linux'

class Module(module.Module):
    title = 'Plot'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)

    def init(self):
        self.agr = GraceComm()
        self._valid_file = False
        
        self.xrc_btn_selectfile.Bind(wx.EVT_BUTTON, self.OnSelectFile)
        self.xrc_txt_gracefile.Bind(wx.EVT_TEXT_ENTER, self.OnFileEntered)
        self.xrc_txt_gracefile.Bind(wx.EVT_KILL_FOCUS, self.OnFileEntered)
        self.xrc_btn_plot.Bind(wx.EVT_BUTTON, self.OnPlot)
        
        self.xrc_lab_fileinfo.Bind(wx.EVT_UPDATE_UI, self.OnUpdateChecked)
        self.xrc_txt_gracefile.Bind(wx.EVT_UPDATE_UI, self.OnUpdateChecked)
        self.xrc_btn_selectfile.Bind(wx.EVT_UPDATE_UI, self.OnUpdateChecked)
        self.xrc_lab_filename.Bind(wx.EVT_UPDATE_UI, self.OnUpdateChecked)
        self.xrc_btn_plot.Bind(wx.EVT_UPDATE_UI, self.OnEnablePlot)

        self.xrc_lab_linewidth.Bind(wx.EVT_UPDATE_UI, self.OnCustomChecked) 
        self.xrc_txt_linewidth.Bind(wx.EVT_UPDATE_UI, self.OnCustomChecked) 
        self.xrc_lab_charsize.Bind(wx.EVT_UPDATE_UI, self.OnCustomChecked) 
        self.xrc_txt_charsize.Bind(wx.EVT_UPDATE_UI, self.OnCustomChecked) 

    def OnCustomChecked(self, evt):
        evt.Enable(self.xrc_chk_customstyle.IsChecked())
        
    def OnUpdateChecked(self, evt):
        evt.Enable(self.xrc_chk_update.IsChecked())

    def OnEnablePlot(self, evt):
        evt.Enable(self._valid_file or (not self.xrc_chk_update.IsChecked()))

    def OnFileEntered(self, evt):
        self._valid_file = False
        self.check_file()

    def check_file(self):
        name = self.xrc_txt_gracefile.GetValue()
        if name == '':
            self.xrc_lab_fileinfo.SetLabel('file info: <nothing selected>')
            return
        try:
            f = open(name)
        except IOError:
            self.xrc_lab_fileinfo.SetLabel('unable to open file')
            self.agr.path = None
        else:
            try:
                self.agr.path = name
                self.agr.count()
            except IOError, msg:
                self.xrc_lab_fileinfo.SetLabel(str(msg))
                self.agr.path = None
            else:
                p,s = self.agr.count()
                p = ['%d graphs','%d graph'][int(p==1)]%p
                s = ['%d sets','%d set'][int(s==1)]%s
                self.xrc_lab_fileinfo.SetLabel('file info: %s in %s'%(s,p))
                self._valid_file = True
        
    def OnSelectFile(self, evt):
        dlg = wx.FileDialog(self.panel, misc.pwd(), wildcard="XMGrace Project files (*.agr)|*.agr",style=wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            dlg.Destroy()
            #self.agr.set_path(name)
            #p,s = self.agr.count()
            #p = ['%d graphs','%d graph'][int(p==1)]%p
            #s = ['%d sets','%d set'][int(s==1)]%s
            #self.xrc_lab_fileinfo.SetLabel('file info: %s in %s'%(s,p))
            self.xrc_txt_gracefile.SetValue(name)
            self.check_file()
            
    def OnPlot(self, evt):
        def custom_style():
            if self.xrc_chk_customstyle.IsChecked():
                return self.xrc_txt_linewidth.GetValue(),self.xrc_txt_charsize.GetValue()
            else:
                return None,None
        
        def all(update=False):
            if update:
                p,s = self.agr.header_from_file(*custom_style())
                             
            l = len(self.project)
            if (not update or l != p) and l>1:
                cols = 2
                rows = l/cols+l%cols
                self.agr.cmd( 'ARRANGE( %d, %d, 0.1, 0.15, 0.15)' % ( rows, cols ) )

            for p,plot in enumerate(self.project):
                s = 0
                self.agr.cmd('g%d on'%p)
                self.agr.cmd('with g%d'%p)
                self.set_styles()
                for s,set in enumerate(plot):
                    if set.hide and self.xrc_cb_onlyvisible.IsChecked():
                        continue
                    self.agr.cmd('g%d.s%d legend \"%s\"'%(p,s,set.name))
                    self.agr.data(p,s,set.xy)
                    s += 1
                self.agr.flush()
                if not update:
                    self.agr.cmd('autoscale')

        def selection(update=False):
            if update:
                self.agr.header_from_file(*custom_style())
            else:
                xmin,xmax,ymin,ymax = WORLD_VIEW
                self.agr.cmd('VIEW XMIN %f'%xmin)
                self.agr.cmd('VIEW XMAX %f'%xmax)
                self.agr.cmd('VIEW YMIN %f'%ymin)
                self.agr.cmd('VIEW YMAX %f'%ymax)
            self.set_styles()
            plot,sets = self.controller.selection
            s = 0
            for set in sets:
                if self.project[plot][set].hide and self.xrc_cb_onlyvisible.IsChecked():
                    continue
                self.agr.cmd('s%d legend \"%s\"'%(s,self.project[plot][set].name))
                self.agr.data(0,s,self.project[plot][set].xy)
                s += 1
            self.agr.flush()
            if not update:
                self.agr.cmd('autoscale')
 
        self.agr.init()
            
        mode = self.xrc_rb_plot.GetSelection()
        [selection, all][mode](self.xrc_chk_update.IsChecked())
        self.agr.redraw()
        self.agr.close()

    def set_styles(self):
        if self.xrc_chk_customstyle.IsChecked():
            lines = ['default',
                     'xaxis bar',
                     'xaxis tick minor',
                     'xaxis tick major',
                     'yaxis bar',
                     'yaxis tick minor',
                     'yaxis tick major',
                     'legend box',
                     'frame']

            text = ['default',
                    'xaxis label',
                    'xaxis ticklabel',
                    'yaxis label',
                    'yaxis ticklabel',
                    'legend']

            for item in lines[:1]:
                self.agr.cmd('%s linewidth %s'%(item,self.xrc_txt_linewidth.GetValue()))

            for item in text:
                self.agr.cmd('%s char size %s'%(item,self.xrc_txt_charsize.GetValue()))


class GraceComm(object):
    def __init__(self):
        self.gp = None
        self._file = None
        self._path = None

    def init(self):
        self.gp = grace_np.GraceProcess(fixedsize=[595,842])
        
    def cmd(self, cmd):
        if self.gp is None:
            self.init()
        self.gp(cmd)

    def close(self):
        del self.gp

    def data(self, p, s, data):
        if self.gp is None:
            self.init()
        if data.shape[0] == 2:
            data = N.transpose(data)
        for n,(x,y) in enumerate(data):
            self.gp('g%d.s%d point %s,%s'%(p,s,x,y))
        
    def flush(self):
        self.gp.flush()

    def redraw(self):
        self.flush()
        self.gp('redraw')

    def _get_path(self):
        return self._path

    def _set_path(self, path):
        self._path = path
        self._file = None

    path = property(_get_path, _set_path)

    def get_file_handle(self):
        if self._file is None:
            self._file = open(self.path, 'r')
        self._file.seek(0)
        return self._file

    file = property(get_file_handle)

    def count(self):
        if self.file.readline().strip() != "# Grace project file":
            raise IOError, 'not a grace project file'
        plots = {}
        for line in self.file:
            mat = re.match('\@target G(\d+)\.S(\d+)', line)
            if mat is not None:
                plot,set = [int(x) for x in mat.groups()]
                if plot not in plots.keys():
                    plots[plot] = 1
                else:
                    plots[plot] += 1
        self._file = None
        return len(plots), sum(plots.values())

    def get_plot(self, line):
        mat = re.match('\@target G(\d+)\.S(\d+)', line)
        if mat is not None:
            self.p,self.s = [int(x) for x in mat.groups()]
            return True
        else:
            return False

    def header_from_file(self, linewidth=None, charsize=None):
        count = self.count()
        l_reg = re.compile(r'linewidth ([\d.]+)')
        s_reg = re.compile(r'char size ([\d.]+)')
        for line in self.file:
            if self.get_plot(line):
                break
            if line[0] == '@':
                if linewidth is not None:
                    line = l_reg.sub('linewidth %s'%linewidth,line)
                if charsize is not None:
                    line = s_reg.sub('char size %s'%charsize,line)
                self.cmd(line[1:].strip())
        self._file.close()
        self._file = None
        return count
                    
        
            
