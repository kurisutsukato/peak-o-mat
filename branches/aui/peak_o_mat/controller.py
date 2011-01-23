#!/usr/bin/env python

##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     
##     This program is free software; you can redistribute it and modify
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


from wx.lib.pubsub import setuparg1            # important for freezing with py2exe
from wx.lib.pubsub import pub as Publisher

import wx
from wx import xrc

import numpy as N
from scipy.interpolate import interp1d

import sys
from operator import add
import os
import subprocess
import copy
import glob
import re
import imp
import traceback
import codecs

import cPickle

import io
import misc
from misc import PomError
from peaks import functions
import plotcanvas
import settings as config
import fitpanel
import fitcontroller
import datagrid
import spec
import project
import model
from fit import Fit

import modules

if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
    # in case peak-o-mat has been compiled with py2exe
    from modules import mod_op, mod_eval, mod_setinfo, mod_calib, \
                        mod_shell, mod_ruby

class out:
    def __init__(self, forward):
        self.forward = forward
        try:
            open('peak-o-mat.log','w')
        except IOError:
            pass
    def write(self, txt):
        try:
            open('peak-o-mat.log','a').write(txt)
        except IOError:
            pass
        self.forward.write(txt)
	self.forward.flush()
    def flush(self):
        self.forward.flush()
        
#sys.stdout = out(sys.stdout)
#sys.stderr = out(sys.stderr)

class Interactor(object):
    def Install(self, controller, view):
        self.controller = controller
        self.view = view

        def menuitem(name):
           return self.view.GetMenuBar().FindItemById(xrc.XRCID(name))

        self.view.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChanged)

        self.view.Bind(wx.EVT_MENU, self.OnNew, menuitem('men_new'))
        self.view.Bind(wx.EVT_MENU, self.OnOpen, menuitem('men_open'))
        self.view.Bind(wx.EVT_MENU, self.OnSaveAs, menuitem('men_saveas'))
        self.view.Bind(wx.EVT_MENU, self.OnSave, menuitem('men_save'))
        self.view.Bind(wx.EVT_MENU, self.OnPgSetup, menuitem('men_pgsetup'))
        self.view.Bind(wx.EVT_MENU, self.OnPrint, menuitem('men_print'))
        self.view.Bind(wx.EVT_MENU, self.OnExportBmp, menuitem('men_exportbmp'))
        self.view.Bind(wx.EVT_MENU, self.OnClose, menuitem('men_quit'))
        self.view.Bind(wx.EVT_MENU, self.OnImport, menuitem('men_import'))
        self.view.Bind(wx.EVT_MENU, self.OnExport, menuitem('men_export'))
        self.view.Bind(wx.EVT_MENU, self.OnShowDatagrid, menuitem('men_datagrid'))
        self.view.Bind(wx.EVT_MENU, self.OnShowNotes, menuitem('men_notes'))
        self.view.Bind(wx.EVT_MENU, self.OnAbout, menuitem('men_about'))

        self.view.frame_annotations.Bind(wx.EVT_CLOSE, self.OnNotesClose)
        
        self.view.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        self.view.canvas.Bind(misc.EVT_RANGE, self.OnCanvasNewRange)
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonPeaks, self.view.tb_canvas.FindWindowByName('btn_peaks'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonLogX, self.view.tb_canvas.FindWindowByName('btn_logx'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonLogY, self.view.tb_canvas.FindWindowByName('btn_logy'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonStyle, self.view.tb_canvas.FindWindowByName('btn_style'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonZoom, self.view.tb_canvas.FindWindowByName('btn_zoom'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonDrag, self.view.tb_canvas.FindWindowByName('btn_drag'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonErase, self.view.tb_canvas.FindWindowByName('btn_erase'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonAuto, self.view.tb_canvas.FindWindowByName('btn_auto'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonAutoX, self.view.tb_canvas.FindWindowByName('btn_autox'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonAutoY, self.view.tb_canvas.FindWindowByName('btn_autoy'))
        self.view.Bind(wx.EVT_BUTTON, self.OnCanvasButtonAuto2Fit, self.view.tb_canvas.FindWindowByName('btn_auto2fit'))

        #self.view.Bind(wx.EVT_BUTTON, self.OnAddPlot, self.view.btn_tree_addplot)

        self.view.Bind(wx.EVT_TEXT, self.OnEditAnnotations, self.view.txt_annotations)

        Publisher.subscribe(self.OnTreeSelect, ('tree','select'))
        Publisher.subscribe(self.OnTreeDelete, ('tree','delete'))
        Publisher.subscribe(self.OnTreeRename, ('tree','rename'))
        Publisher.subscribe(self.OnTreeMove, ('tree','move'))
        Publisher.subscribe(self.OnTreeHide, ('tree','hide'))
        Publisher.subscribe(self.OnTreeDuplicate, ('tree','duplicate'))
        Publisher.subscribe(self.OnTreeNewFromVisArea, ('tree','newfromvisarea'))
        Publisher.subscribe(self.OnTreeInsert, ('tree','insert'))
        Publisher.subscribe(self.OnTreeCopyToGrid, ('tree','togrid'))
        Publisher.subscribe(self.OnTreeRemFit, ('tree','remfit'))
        Publisher.subscribe(self.OnTreeRemTrafo, ('tree','remtrafo'))
        Publisher.subscribe(self.OnTreeRemWeights, ('tree','remerror'))
        Publisher.subscribe(self.OnTreeUnmask, ('tree','unmask'))
        Publisher.subscribe(self.OnAddPlot, ('tree','addplot'))
        Publisher.subscribe(self.OnTreeCopy, ('tree','copy'))
        Publisher.subscribe(self.OnTreePaste, ('tree','paste'))
        
        Publisher.subscribe(self.OnSetFromGrid, ('grid','newset'))

        Publisher.subscribe(self.OnCanvasErase, ('canvas','erase'))
        #em.eventManager.Register(self.OnGotPars, misc.EVT_GOTPARS, self.view.canvas)
        self.view.canvas.Bind(misc.EVT_GOTPARS, self.OnGotPars)
        
        Publisher.subscribe(self.OnLoadSetFromModel, ('fitctrl','loadset'))
        Publisher.subscribe(self.OnFitPars2DataGrid, ('fitctrl','parexport'))
        Publisher.subscribe(self.OnStartFit, ('fitctrl','fit'))
        Publisher.subscribe(self.OnStartPickPars, ('fitctrl','pickpars'))
        Publisher.subscribe(self.OnEditPars, ('fitctrl','editpars'))
        Publisher.subscribe(self.OnAttachWeights, ('fitctrl','attachweights'))
        Publisher.subscribe(self.OnLimitFitRange, ('fitctrl','limitfitrange'))
        Publisher.subscribe(self.OnPlot, ('fitctrl','plot'))

        Publisher.subscribe(self.OnPageChanged, ('notebook','pagechanged'))

        Publisher.subscribe(self.OnProjectModified, ('changed'))

        self.view.Bind(misc.EVT_RESULT, self.OnFitResult)

        self.view.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnTreeCopy(self, msg):
        self.controller.set2clipboard()

    def OnTreePaste(self, msg):
        self.controller.clipboard2set()

    def OnProjectModified(self, msg):
        self.controller.project_modified = True

    def OnAbout(self, evt):
        self.view.about_dialog()

    def OnFileHistory(self, evt):
        filenum = evt.GetId() - wx.ID_FILE1
        self.controller.open_recent(filenum)

    def OnNotebookPageChanged(self, evt):
        Publisher.sendMessage(('notebook','pagechanged'), evt.GetEventObject().GetCurrentPage())

    def OnPageChanged(self, msg):
        self.controller.page_changed(msg.data.GetName())

    def OnEditAnnotations(self, evt):
        self.controller.annotations_changed(self.view.annotations)

    def OnCanvasErase(self, msg):
        self.controller.delete_points(msg.data)

    def OnPlot(self, msg):
        self.controller.update_plot()

    def OnLimitFitRange(self, msg):
        self.controller.set_limit_fitrange(msg.data)

    def OnAttachWeights(self, msg):
        self.controller.attach_weights_to_set(msg.data)

    def OnStartFit(self, msg):
        self.controller.start_fit(*msg.data)

    def OnFitResult(self, evt):
        self.controller.fit_finished(evt.result)
        
    def OnAddPlot(self, evt):
        self.controller.add_plot()
        
    def OnTreeUnmask(self, msg):
        self.controller.rem_attr('mask', only_sel=True)

    def OnTreeRemWeights(self, msg):
        self.controller.rem_attr('weights', only_sel=True)

    def OnTreeRemFit(self, msg):
        self.controller.rem_attr('mod', only_sel=True)

    def OnTreeRemTrafo(self, msg):
        self.controller.rem_attr('trafo', only_sel=True)

    def OnFitPars2DataGrid(self, msg):
        self.controller.datagrid_append(msg.data)

    def OnLoadSetFromModel(self, msg):
        model, which, xr, pts = msg.data
        self.controller.load_set_from_model(model, which, xr, pts)

    def OnGotPars(self, evt):
        mapping = {misc.GOTPARS_MOVE: 'edit',
                   misc.GOTPARS_MOVE: 'move',
                   misc.GOTPARS_DOWN: 'down',
                   misc.GOTPARS_END: 'end'}
        
        self.controller.model_updated(action = mapping[evt.cmd])
        evt.Skip()

    def OnEditPars(self, msg):
        self.controller.model_updated()
        
    def OnStartPickPars(self, msg):
        self.controller.start_pick_pars(*msg.data)

    def OnSetFromGrid(self, msg):
        self.controller.new_sets_from_grid(msg.data)

    def OnTreeCopyToGrid(self, msg):
        self.controller.selection_to_grid()
        
    def OnTreeSelect(self, msg):
        self.controller.selection = msg.data
        
    def OnTreeDelete(self, msg):
        self.controller.delete_selection(msg.data)

    def OnTreeRename(self, msg):
        plot, set, name = msg.data
        wx.CallAfter(self.controller.rename_set, name, (plot, set))

    def OnTreeMove(self, msg):
        self.controller.move_set(*msg.data)

    def OnTreeHide(self, msg):
        self.controller.hide_selection()

    def OnTreeDuplicate(self, msg):
        self.controller.duplicate_selection(msg.data)

    def OnTreeNewFromVisArea(self, msg):
        self.controller.crop_selection(msg.data)

    def OnTreeInsert(self, msg):
        self.controller.insert_plot(msg.data)

    def OnCanvasNewRange(self, evt):
        xr, yr = evt.range
        self.controller.set_plot_range(xr,yr)

    def OnCanvasButtonAuto(self, evt):
        self.controller.autoscale()

    def OnCanvasButtonAutoX(self, evt):
        self.controller.autoscale(X=True)

    def OnCanvasButtonAutoY(self, evt):
        self.controller.autoscale(Y=True)

    def OnCanvasButtonAuto2Fit(self, evt):
        self.controller.autoscale(fit=True)
        
    def OnCanvasButtonPeaks(self, evt):
        state = evt.GetEventObject().GetToggle() == 1
        self.controller.app_state.show_peaks = state
        self.controller.update_plot()
        
    def OnCanvasButtonLogY(self, evt):
        state = evt.GetEventObject().GetToggle() == 1
        self.controller.autoscale()
        self.controller.set_logscale(None,state)
        self.controller.update_plot()
        
    def OnCanvasButtonLogX(self, evt):
        state = evt.GetEventObject().GetToggle() == 1
        self.controller.autoscale()
        self.controller.set_logscale(state, None)
        self.controller.update_plot()
        
    def OnCanvasButtonStyle(self, evt):
        state = evt.GetEventObject().GetToggle() == 1
        self.controller.app_state.line_style = state
        self.controller.update_plot()
        
    def OnCanvasButtonZoom(self, evt):
        state = evt.GetEventObject().GetToggle()
        mode = [None,'zoom'][state]
        self.controller.set_canvas_mode(mode)
        
    def OnCanvasButtonDrag(self, evt):
        state = evt.GetEventObject().GetToggle()
        mode = [None,'drag'][state]
        self.controller.set_canvas_mode(mode)
                
    def OnCanvasButtonErase(self, evt):
        state = evt.GetEventObject().GetToggle()
        mode = [None,'erase'][state]
        self.controller.set_canvas_mode(mode)

    def OnImport(self, evt):
        res = self.view.import_dialog(misc.cwd())
        if res is not None:
            path,one_plot_each = res
            self.controller.import_data(path, one_plot_each)

    def OnExport(self, evt):
        self.controller.show_export_dialog()

    def OnShowDatagrid(self, evt):
        self.controller.show_datagrid(evt.IsChecked())
                
    def OnShowNotes(self, evt):
        self.controller.show_notes(evt.IsChecked())

    def OnClose(self, evt):
        self.controller.close()
        
    def OnNotesClose(self, evt):
        self.controller.notes_close()
        
    def OnNew(self, evt):
        self.controller.new_project()

    def OnOpen(self,evt):
        path = self.view.load_file_dialog(misc.cwd())
        if path is not None:
            self.controller.open_project(path)

    def OnSave(self, evt):
        if self.controller.project.path is None:
            self.OnSaveAs(None)
        else:
            self.controller.save_project()

    def OnSaveAs(self, evt):
        path = self.view.save_file_dialog(misc.cwd())
        if path is not None:
            self.controller.save_project(path)

    def OnPgSetup(self, evt):
        self.view.canvas.PageSetup()

    def OnPrint(self, evt):
        self.view.canvas.Printout()

    def OnExportBmp(self, evt):
        self.view.canvas.SaveFile()


class State:
    active_plot = None
    active_set = None
    line_style = 0
    working = False
    show_peaks = False

class Controller(object):
    def __init__(self, proj, view, interactor):
        self.datagrid = None
        self.app_path = os.path.abspath(sys.argv[0])

        self.project = proj
        self.view = view
        self.app_state = State()
        self.data_grids = []
        self._freeze = False
        self._selection = None
        self._fthreads = {}
        self._updating = False
        self._modified = False
        self.pp_notify = []
        
        if view is not None:
            interactor.Install(self, self.view)
            fitview = fitpanel.FitPanel(self.view.nb_modules)
            self.fit_controller = fitcontroller.FitController(fitview, fitcontroller.FitInteractor())

            self.view.SetTitle(self.project.name)
            self.load_filehistory()
            self.load_modules()
            self.parse_sysargs()

            self.update_plot()
            self.view.start()

    def message(self, msg, blink=False, forever=False):
        event = misc.ShoutEvent(self.view.GetId(), msg=msg, target=1, blink=blink, time=5000, forever=forever)
        wx.PostEvent(self.view, event)

    def load_filehistory(self):
        home = os.path.expanduser("~")
        recent = os.path.join(home,'.peak-o-mat','filehistory')
        if os.path.exists(recent):
            for path in codecs.open(recent, 'r', 'utf-8'):
                self.view.filehistory.AddFileToHistory(path.strip())

    def save_filehistory(self):
        hist = self.view.get_filehistory()
            
        pom = os.path.join(os.path.expanduser("~"),'.peak-o-mat')
        recent = os.path.join(pom,'filehistory')
        if not os.path.exists(pom):
            try:
                os.mkdir(pom)
            except: return

        f = codecs.open(recent, 'w', 'utf-8')
        f.write(os.linesep.join(hist))
        f.close()
        
    def parse_sysargs(self):
        self.view.canvas.antialias = config.options.antialias
        
        if len(config.sysargs) > 0:
            if len(config.sysargs) > 1:
                print 'skipping additional arguments'
            wx.CallAfter(self.open_project, config.sysargs[0])

    def _set_modified(self, arg):
        title = self.view.title
        if title[-1] == '*':
            title = title[:-1]
        if arg:
            self.view.title = title+'*'
        else:
            self.view.title = title
        self._modified = arg
    def _get_modified(self):
        return self._modified
    project_modified = property(_get_modified, _set_modified)
        
    def new_project(self):
        """\
        Create a new instance of peak-o-mat if the current project is not empty.
        """
        if len(self.project) > 0:
            if sys.platform == 'win32':
                if hasattr(sys, 'frozen'):
                    subprocess.Popen([sys.executable])
                else:
                    subprocess.Popen([sys.executable, self.app_path])
            else:
                subprocess.Popen([self.app_path])

    def open_project(self, path):
        """\
        Open project given by 'path'. If the current project is not empty create a new
        instance.
        """
        if len(self.project) == 0 and (self.datagrid is None or len(self.datagrid.gridcontrollers) == 0):
            msg = self.project.Read(path, datastore=self.new_datagrid)
            if msg is not None:
                if msg.type == 'warn':
                    wx.CallAfter(self.view.msg_dialog, '\n'.join([unicode(q) for q in msg]))
                else:
                    wx.CallAfter(self.view.error_dialog, '\n'.join([unicode(q) for q in msg]))
                    return
            self.app_state.active_plot = 0
            self.app_state.active_set = [0]
            self.view.title = self.project.name
            self.view.annotations = self.project.annotations
            self.view.tree.build(self.project)
            if self.project.path is not None:
                self.view.filehistory.AddFileToHistory(os.path.abspath(path))
                self.save_filehistory()
            self.project_modified = False
        else:
            if sys.platform == 'win32':
                if hasattr(sys, 'frozen'):
                    os.startfile(os.path.abspath(path))
                else:
                    subprocess.Popen([sys.executable, self.app_path, path])
            else:
                subprocess.Popen([self.app_path, path])
        misc.set_cwd(path)
        
    def open_recent(self, num):
        path = self.view.filehistory.GetHistoryFile(num)
        self.open_project(path)
        self.view.filehistory.AddFileToHistory(self.project.path)
        
    def save_project(self, path=None):
        """\
        Save the current project to a file given by either the project's name or
        by the arg 'name'.
        """
        if self.datagrid is not None:
            msg = self.project.Write(path, griddata=self.datagrid.gridcontrollers)
        else:
            msg = self.project.Write(path)
        if msg is not None:
            self.view.error_dialog(msg)
        else:
            self.view.SetTitle(self.project.name)
            self.view.msg_dialog('Project saved as \'%s\''%(self.project.path))
            self.view.filehistory.AddFileToHistory(self.project.path)
            self.save_filehistory()
        self.project_modified = False
        misc.set_cwd(path)
        
    def notes_close(self):
        self.view.frame_annotations.Show(False)
        self.view.GetMenuBar().Check(xrc.XRCID('men_notes'), False)       
        
    def close(self):
        if not self.project_modified or self.view.close_project_dialog(self.project.name):
            Publisher.unsubAll()
            self.view.Freeze()
            if self.datagrid is not None:
                self.datagrid.view.Destroy()
                del self.datagrid
            self.view.frame_annotations.Destroy()
            self.view.Thaw()
            self.view.Destroy()

    def import_data(self, path, one_plot_each=False):
        plot_created = False
        if type(path) != list:
            path = [path]
        for p in path:
            if not plot_created or one_plot_each:
                plot = self.add_plot()
                plot_created = True
            try:
                labels, data = io.read_txt(p)
                for lab,y in zip(labels[1:],data[1:]):
                    if lab is None:
                        name = os.path.basename(p)
                    else:
                        name = '%s_%s'%(os.path.basename(p),lab)
                    s = spec.Spec(data[0],y,name)
                    set = self.project[plot].add(s)
            except PomError, e:
                self.message(e.value)
                return
            if s.truncated:
                self.message('data has been truncated')
        misc.set_cwd(p)
            
        self.update_tree()
        self.update_plot()
        self.view.tree.selection = (plot,set)

    def show_export_dialog(self):
        if self.active_set is None: # multiple selections
            res = self.view.export_dialog_multi(misc.cwd())
            if res is not None:
                path, ext, only_vis, overwrite = res
                self.export_data(path, options=(ext, only_vis,overwrite))
        else:
            path = self.view.export_dialog_single(misc.cwd(), self.active_set.name)
            if path is not None:
                self.export_data(path)
                
    def export_data(self, path, options=False):
        nall = 0
        nwritten = 0
        if self.active_set is None:
            p,s = self.selection
            sets = iter([self.project[p][q] for q in s])
            ext, only_vis, overwrite = options
            for set in sets:
                nall += 1
                if set.hide and only_vis:
                    continue
                name = set.name
                if ext is not None:
                    if name.find('.') == -1:
                        name = name+'.'+ext
                    else:
                        name = re.sub(r'\.(\w*$)', '.'+ext, name)
                nwritten += int(set.write(os.path.join(path, name),overwrite))
            misc.set_cwd(path)
            self.message('saved %d of %d set(s)'%(nwritten,nall))
        else:
            if self.active_set.write(path):
                misc.set_cwd(path)
                self.message('saved as %s'%(path))
        
    def reload_modules(self):
        self.view.silent = True
        for n in range(self.view.nb_modules.GetPageCount())[::-1]:
            if self.view.nb_modules.GetPageText(n) not in ['Fit','Annotations']:
                p = self.view.nb_modules.GetPage(n)
                self.view.nb_modules.DeletePage(n)
        self.load_modules()
        self.view.silent = False
        
    def load_modules(self):
        print 'loading system modules'
        if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
            # in case peak-o-mat has been compiled with py2exe
            for name in modules.__all__:
                try:
                    mod = globals()[name]
                except KeyError:
                    continue
                mod.Module(self, mod.__doc__)
        else:
            for mod in modules.__all__:
                try:
                    __import__('modules',globals(),locals(),[mod])
                except:
                    tp,val,tb = sys.exc_info()
                    print mod,tp,val
                    if config.options.debug:
                        traceback.print_tb(tb)
                    else:
                        print 'start peak-o-mat with option --debug to get the traceback'
                else:
                    getattr(modules, mod).Module(self, getattr(modules, mod).__doc__)

        #user modules 
        moddir = os.path.join(os.path.expanduser('~'),'.peak-o-mat','modules')
        print 'loading user modules from',moddir
        mods = [os.path.basename(x).split('.')[0] for x in glob.glob(os.path.join(moddir,'*.py'))]
        sys.path.append(moddir)

        for name in mods:
            try:
                f,fname,descr = imp.find_module(name)
                mod = imp.load_module(name, f, fname, descr)
            except Exception,msg:
                print 'user module %s import error: %s'%(name, msg)
            else:
                try:
                    mod.Module(self, mod.__doc__)
                except Exception, msg:
                    print 'user module %s import error: %s'%(name, msg)

    def page_changed(self, name):
        pass
            
    def annotations_changed(self, txt):
        self.project.annotations = txt
        Publisher.sendMessage(('changed'))
        
    def set2clipboard(self):
        if wx.TheClipboard.Open():
            do = wx.CustomDataObject('selection')
            if self.selection.plot:
                data = cPickle.dumps(self.active_plot,1)
            else:
                plot, sel = self.selection
                data = cPickle.dumps([self.project[plot][q] for q in sel], 1)
            do.SetData(data)
            wx.TheClipboard.SetData(do)
            wx.TheClipboard.Close()
            self.message('copied current selection to clipboard', blink=True)
    
    def clipboard2set(self):
        if wx.TheClipboard.Open():
            do = wx.CustomDataObject('selection')
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()
            if success:
                data = do.GetData()
                data = cPickle.loads(data)
                if type(data) == spec.Spec:
                    self.add_set(data)
                elif type(data) == project.Plot:
                    self.project.add(data)
                elif type(data) == list:
                    for s in data:
                        self.add_set(s)
        self.update_tree()

    def move_set(self, s_plot, s_sets, t_plot, t_set):
        """\
        Move a list of sets 's_sets' or a single set from source plot 's_plot' to
        target plot 't_plot' inserting them before set 't_set'.
        If 's_sets' and 't_set' are None, insert plot 's_plot' before 't_plot'.
        """
        self.view.tree.Freeze()
        if s_sets is None:
            # move plot
            self.project.move(s_plot, t_plot)
            self.update_tree()
            sel = t_plot
        else:
            # move set
            if s_plot == t_plot:
                self.project[s_plot].move(s_sets, t_set)
                self.update_tree(s_plot)
            else:
                move = self.project[s_plot].delete(s_sets)
                if t_set is None:
                    t_set = 0
                self.project[t_plot].insert(t_set, move)
                self.update_tree(t_plot)
                self.update_tree(s_plot)
            sel = (t_plot, t_set)
        self.view.tree.Thaw()
        self.view.tree.selection = sel
        self.project_modified = True

    def rename_set(self, name, item):
        """\
        Rename a plot or set. 'item' is a tuple containing plot and set number. If the set
        number is None, rename the plot.
        """
        plot,set = item
        if set is not None:
            self.project[plot][set].name = name
            self.update_tree(plot)
        else:
            self.project[plot].name = name
            self.update_tree()
        self.update_setinfo()
        self.project_modified = True
        
    def insert_plot(self, ind):
        """\
        Insert an empty plot at index 'ind'.
        """
        self.project.insert(ind, project.Plot())
        self.update_tree()
        self.project_modified = True
        
    def add_plot(self):
        """\
        Add an empty plot.
        """
        added = self.project.add(project.Plot())
        self.update_tree()
        self.view.tree.selection = added
        self.project_modified = True
        return added
        
    def add_set(self, data, plot=None):
        """\
        Add a set to the current plot.
        """
        if plot is None:
            if self.active_plot is None:
                plot = self.add_plot()
                added = self.project[plot].add(data)
            else:
                added = self.active_plot.add(data)
                plot = self.project.index(self.active_plot)
        else:
            added = self.project[plot].add(data)
        self.update_tree()
        self.view.tree.selection = plot,added
        self.project_modified = True
        return added

    def rem_attr(self, attr, only_sel=False):
        if attr not in ['weights','trafo','mod','mask']:
            raise ValueError, 'unkown set attribute'
        if only_sel:
            p,sel = self.selection
            for s in sel:
                setattr(self.project[p][s], attr,None)
        else:
            for p in self.project:
                for s in p:
                    setattr(s, attr, None)
        self.update_plot()
        self.project_modified = True
        Publisher.sendMessage(('setattrchanged'))

    def set_limit_fitrange(self, state):
        if state:
            self.active_set.limits = self.view.canvas.GetXCurrentRange()
        else:
            self.active_set.limits = None

    def start_fit(self, mod, limit, fittype=1, maxiter=50, stepsize=1e-13):
        p,sel = self.selection
        set = self.active_set
        if limit:
            xr = self.view.canvas.GetXCurrentRange()
            set.limits = xr
        fitter = Fit(set, mod, fittype, maxiter, stepsize)

        self.fit_controller.sync_gui(fit_in_progress=True) 
        self._fthread = misc.WorkerThread(self.view, fitter)
        self._fthread.setDaemon(True)
        self._fthread.start()
        self._fdata = set,mod

        self.message('fitting....',blink=True,forever=True)

    def fit_finished(self, result):
        self.message('')
        
        pars,errors,msgs = result
        set,mod = self._fdata
        del self._fthread
        self.fit_controller.sync_gui(fit_in_progress=False) 
        
        set.mod = mod
        set.mod._newpars(pars,errors)
        if self.active_set == set:
            set.mod.listener = None
            self.fit_controller.model = set.mod
            self.update_plot()
        self.message('%s: fit finshed'%set.name)
        self.fit_controller.log('%s\n%s\n---'%(set.name,'\n'.join(msgs)))
        Publisher.sendMessage(('fitfinished'))

    def new_sets_from_grid(self, source):
        plot = self.add_plot()
        gridname, data = source()
        self.project[plot].name = gridname
        for (x,y),name in data:
            sp = spec.Spec(x,y,'%s_%s'%(gridname,name))
            added = self.project[plot].add(sp)
        self.update_tree()
        self.view.tree.selection = plot,added
        self.message('created sets from grid data',blink=True)
        self.project_modified = True
        
    def update_tree(self, plot=None):
        """\
        Synchronize the tree with the project data. If 'plot' is not None, update only
        the nodes contained in 'plot'.
        """
        if plot is None:
            self.view.tree.update_node(-1, [x.name for x in self.project])
            for n in range(len(self.project)):
                self.update_tree(n)
        else:
            names = []
            hides = []
            if len(self.project[plot]) > 0:
                names, hides = zip(*[(x.name,x.hide) for x in self.project[plot]])
            self.view.tree.update_node(plot, names, hides)

    def hide_selection(self):
        """\
        Toggle the visibility of the current selection.
        """
        plot, sel = self.selection
        for n,set in enumerate(self.project[plot]):
            if n in sel:
                set.hide = not set.hide
        self.update_tree(plot)
        self.update_plot()
        self.project_modified = True
        
    def delete_selection(self, wholeplot=False):
        """\
        Delete the current selection. If 'wholeplot' is True, delete the whole plot
        including all sets.
        """
        plot, sel = self.selection
        if wholeplot:
            self.project.delete(plot)
            self.update_tree()
            if len(self.project) > 0:
                self.view.tree.selection = min(len(self.project)-1,plot)
            else:
                self._selection = None
                self.update_plot()
        else:
            self.project[plot].delete(sel)
            self.update_tree(plot)
            if len(self.project[plot]) > 0:
                set = max( min(max(sel)-len(sel)+1, len(self.project[plot])-1) , 0)
                self.view.tree.selection = (plot, set)
            else:
                self.view.tree.selection = plot
        self.project_modified = True

    def duplicate_selection(self, wholeplot=False):
        """\
        Duplicate the current selection. If 'wholeplot' is True, duplicate and append the
        whole plot rather than duplicating only the sets of a plot.
        """
        plot, sel = self.selection
        if wholeplot:
            dupl = self.project.copy(plot)
            plot = self.project.add(dupl)
            self.update_tree()
            self.view.tree.selection = plot
        else:
            dupl = self.project[plot].copy(sel)
            set = self.project[plot].add(dupl)
            self.update_tree(plot)
            self.view.tree.selection = (plot, set)
        self.project_modified = True

    def crop_selection(self, wholeplot=False):
        """\
        Creates new sets from the current selection, cropped to the visible area.
        Useful if dealing with very large spectra.
        """
        plot, sel = self.selection
        xrng = self.project[plot].xrng
        if wholeplot:
            newplot = self.project.add(project.Plot())
        else:
            newplot = plot
        for set in sel:
            self.project[newplot].add(self.project[plot][set].crop(xrng, cp=True))
        self.update_tree()
        self.view.tree.selection = (newplot, set)
        self.project_modified = True
                
    def selection_to_grid(self):
        plot, sel = self.selection
        for set in sel:
            self.new_datagrid((N.transpose(self.project[plot][set].xy), [], []), name=self.project[plot][set].name)
        self.project_modified = True

    def _get_selection(self):
        return self._selection
    def _set_selection(self, selection):
        class Selection(tuple):
            plot = False
        plot, sel = selection
        if sel is None:
            sel = range(len(self.project[plot]))
            self._selection = Selection((plot, sel))
            self._selection.plot = True
        else:
            self._selection = Selection((plot, sel))
        if len(sel) == 1:
            wx.CallAfter(Publisher.sendMessage,('selection','changed'),self.project[plot][sel[0]])
        else:
            wx.CallAfter(Publisher.sendMessage,('selection','changed'),None)
        self.update_plot()
    selection = property(_get_selection, _set_selection, doc="the current tree selection")

    def update(self):
        print 'called controller.update'
        self.update_tree()
        self.update_plot()

    def update_plot(self, *args, **kwargs):
        if not self._updating:
            self.view.Bind(wx.EVT_IDLE, lambda x: self._update(x, *args, **kwargs))
            self._updating = True

    def _update(self, evt, *args, **kwargs):
        self._updating = False
        self.view.Unbind(wx.EVT_IDLE)
        self.plot(*args, **kwargs)
        wx.CallAfter(self.update_setinfo)

    def update_setinfo(self):
        Publisher.sendMessage(('setinfo','update'), None)

    def _get_active_set(self):
        try:
            p,s = self.selection
        except:
            return None
        else:
            if len(s) == 1:
                return self.project[p][s[0]]
            else:
                return None
    active_set = property(_get_active_set)

    def _get_active_plot(self):
        try:
            p,s = self.selection
        except:
            return None
        else:
            return self.project[p]
    active_plot = property(_get_active_plot)

    def set_logscale(self, xlog, ylog):
        self.view.canvas.setLogScale([xlog, ylog])

    def set_canvas_mode(self, mode):
        #if mode is None:
        #    self.view.canvas.RestoreLastMode()
        #else:
        self.view.canvas.SetMode(mode)

    def set_plot_range(self, *args, **kwargs):
        """\
        Set the visible area of the current plot. Arguments equal to 'None'
        adjust the corresponding axis to the data range of the current set.
        Can be called either as set_plot_range(xr, yr) or
        set_plot_range(xr=xr), set_plot_range(yr=yr).
        """
        if len(args) == 2:
            xr, yr = args
            self.project[self.selection[0]].rng = xr,yr
        else:
            if 'xr' in kwargs.keys():
                self.project[self.selection[0]].xrng = kwargs['xr']
            if 'yr' in kwargs.keys():
                self.project[self.selection[0]].yrng = kwargs['yr']

    def autoscale(self, **kwargs):
        p,s = self.selection
        if len(kwargs) == 0:
            self.project[self.selection[0]].rng = None,None
        else:
            if 'X' in kwargs.keys() and kwargs['X']:
                self.set_plot_range(xr=None)
            if 'Y' in kwargs.keys() and kwargs['Y']:
                self.set_plot_range(yr=None)
            if 'fit' in kwargs.keys() and kwargs['fit']:
                self.set_plot_range(xr=self.project[p][s[0]].limits)
                
        self.update_plot()

    def delete_points(self, bbox):
        plot,sets = self.selection
        for set in sets:
            self.project[plot][set].delete(bbox)
        self.update_plot()
        self.project_modified = True

    def start_pick_pars(self, ind, pickers):
        self.pp_notify = [[self.fit_controller.model[i].name, ind[i]] for i in range(len(ind))]
        self.update_plot(fit=self.fit_controller.model)
        self.freeze_canvas = True
        name,count = self.pp_notify[0]
        self.message('pick %s'%name)
        self.view.canvas.report(pickers)

    def attach_weights_to_set(self, weights):
        self.active_set.weights = weights
        self.update_plot()
        wx.CallAfter(Publisher.sendMessage,('selection','changed'),self.active_set)

    def model_updated(self, action=None):
        self.plot(fit=self.fit_controller.model)
        if action != 'move' and len(self.pp_notify) > 0:
            name,count = self.pp_notify[0]
            if count-1 == 0:
                self.pp_notify.pop(0)
                if len(self.pp_notify) > 0:
                    name,count = self.pp_notify[0]
                    self.message('pick %s'%name)
            else:
                self.pp_notify[0][1] -= 1
        if action == 'end':
            self.active_set.mod = self.fit_controller.model
            self.freeze_canvas = False
            
    def load_set_from_model(self, model, which, xr, pts):
        x = N.linspace(xr[0],xr[1],pts)
        if which > 0:
            y = model.evaluate(x, single=True)[which-1]
            name = model.tokens.split(' ')[which-1]
        else:
            y = model.evaluate(x)
            name = model.tokens
        plot,sel = self.selection
        self.project[plot].add(spec.Spec(x,y,name))
        self.update_tree(plot)
        self.update_plot()
        self.project_modified = True

    def show_notes(self, show=False):
        self.view.frame_annotations.Show(show)
        self.view.GetMenuBar().Check(xrc.XRCID('men_notes'), show)
        
    def show_datagrid(self, show=False):
        if show:
            if self.datagrid is None:
                self.datagrid = datagrid.new_datagrid(self, self.view)
                self.datagrid.view.SetIcon(self.view.pom_ico)
            self.datagrid.view.Show()
            self.view.GetMenuBar().Check(xrc.XRCID('men_datagrid'), True)
        else:
            if self.datagrid is not None:
                self.datagrid.view.Hide()
            self.view.GetMenuBar().Check(xrc.XRCID('men_datagrid'), False)
                
    def new_datagrid(self, data=None, the_grid=False, background=False, name=None):
        if self.datagrid is None:
            self.datagrid = datagrid.new_datagrid(self, self.view)
            self.datagrid.view.SetIcon(self.view.pom_ico)
            
        if the_grid:
            name = 'exported fit parameters'

        grid = self.datagrid.new(data, name, the_grid)
        self.show_datagrid(True)
        self.project_modified = True
            
    def datagrid_append(self, data):
        if self.datagrid is None or self.datagrid.the_grid is None:
            self.new_datagrid(the_grid=True)
        
        plot,sel = self.selection
        self.datagrid.the_grid.add_par_row(data, self.project[plot][sel[0]].name)
        self.message('exported parameters to data grid',blink=True)
        self.project_modified = True

    def _set_freeze_canvas(self, state):
        self._freeze = state
    def _get_freeze_canvas(self):
        return self._freeze
    freeze_canvas = property(_get_freeze_canvas, _set_freeze_canvas)
        
    def plot(self, fit = None, floating = None):
        if self.app_state.working:
            return
        xr,yr = None,None
        
        self.view.canvas.SetXSpec('min')
        self.view.canvas.SetYSpec('min')

        lines = []
        set = None

        def Line(data, colour, skipbb=False):
            if self.app_state.line_style == 0:
                return plotcanvas.Line(data, colour=colour, skipbb=skipbb)
            else:
                return plotcanvas.Marker(data, colour=colour, fillcolour=colour, marker='square', size=0.7, skipbb=skipbb)

        if self.freeze_canvas and fit is not None:
            xr = self.view.canvas.GetXCurrentRange()
            yr = self.view.canvas.GetYCurrentRange()
            set = self.active_set
            lines = []
            y = fit.evaluate(set.x)
            if y is not False:
                lines.append(Line(set.xy,colour='red'))
                lines.append(plotcanvas.Line([set.x,y], colour=wx.Colour(0,200,50), width=2, skipbb=True))
                self.view.canvas.Draw(plotcanvas.Graphics(lines),xr,yr)
            return
        else:
            # parameter picking was cancelled by the user
            #print 'parameter picking cancelled'
            self.freeze_canvas = False
            self.view.canvas.MouseReset()

        if self.selection is not None:
            plot,sel = self.selection
            if floating is not None:
                lines.append(plotcanvas.Line([floating.x,floating.y], colour='blue', width=1, skipbb=True))
            for sig,set in enumerate(self.project[plot]):
                if set.hide and sig not in sel:
                    continue
                if sig in sel:
                    lines.append(Line(set.xy, 'red'))
                    if set.weights is not None:
                        bounds = set.weights.getBounds(set.xy)
                        lines.append(plotcanvas.Line([set.x,bounds[0]], colour='blue', width=2, skipbb=True))
                        lines.append(plotcanvas.Line([set.x,bounds[1]], colour='blue', width=2, skipbb=True))
                    elif self.fit_controller.weights is not None:
                        bounds = self.fit_controller.weights.getBounds(set.xy)
                        lines.append(plotcanvas.Line([set.x,bounds[0]], colour='blue', width=1, skipbb=True))
                        lines.append(plotcanvas.Line([set.x,bounds[1]], colour='blue', width=1, skipbb=True))
                    if fit is not None:
                        x = set.x_limited
                        y = fit.evaluate(x)
                        if y is not False:
                            lines.append(plotcanvas.Line([x,y], colour=wx.Colour(0,200,50), width=2, skipbb=True))
                    elif set.mod is not None:
                        x = set.x_limited
                        y = set.mod.evaluate(x)
                        if y is not False:
                            lines.append(plotcanvas.Line([x,y], colour=wx.Colour(0,200,50), width=2, skipbb=True))
                    if self.app_state.show_peaks:
                        if fit is not None:
                            for i in set.loadpeaks(fit, addbg=True):
                                lines.append(plotcanvas.Line(i, colour='blue', skipbb=True))
                        elif set.mod is not None:
                            for i in set.loadpeaks(set.mod, addbg=True):
                                lines.append(plotcanvas.Line(i, colour='blue', skipbb=True))
                else:
                    if config.fast_display:
                        skip = max(1,int(len(set.x)/config.fast_max_pts+.5))
                    else:                        skip = 1
                    lines.append(Line(set.xy[:,::skip], colour='black'))
            xr, yr = self.project[plot].rng
        graphics = plotcanvas.Graphics(lines)

        try:
            1 == 1
        except:
            tp,val,tb = sys.exc_info()
            print 'plotting'
            traceback.print_tb(tb)
            traceback.print_stack()
            
        self.view.canvas.Draw(graphics,xr,yr)

if __name__ == '__main__':
    p = project.Project()
    p.Read('../example.lpj')
    c=Controller(p)

    
