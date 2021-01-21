##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)
##     This program is free software; you can redistribute it and modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later versionp.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import numpy as np
np.seterr(over='ignore')

import wx
from pubsub import pub
import wx.aui as aui

import os
import glob
import re
import imp
from importlib import import_module
import logging
import codecs
import inspect

import pickle, json
import sys
from copy import deepcopy

from . import fio
from . import misc
from . import misc_ui

from . import plotcanvas
from . import config

from . import fitpanel
from . import fitcontroller
from . import fitinteractor

from . import datagrid
from . import spec
from . import project
from . import module
from . import codeeditor
from .mplplot import controller as mplcontroller
from .mplplot import model as mplmodel
from .controls import FigureListController
from .dvctree import TreeListModel

from .main import new_controller

from .appdata import configdir, logfile

if hasattr(sys, 'frozen') and sys.frozen == 'windows_exe':
    # in case peak-o-mat has been compiled with py2exe
    from .modules import mod_op, mod_eval, mod_setinfo, mod_calib, \
                        mod_shell, mod_ruby, mod_map, mod_background

def split(path):
    rs = os.path.normpath(path).split(os.path.sep)
    if rs[0] == '':
        rs.pop(0)
    return rs

class State:
    active_plot = None
    active_set = None
    line_style = 0
    working = False
    show_peaks = False
    fast_display = False

class ModulesContainer(dict):
    def append(self, item):
        self[item.title] = item

    def get_plot_objects(self):
        for m in self.values():
            try:
                if m.plotme is not None:
                    yield(m.plotme)
            except AttributeError:
                pass

class Controller(object):
    def __init__(self, proj, view, interactor, lpj_path):
        self.datagrid = None
        #self.app_path = os.path.abspath(sys.argv[0])

        self.project = proj
        self.view = view

        self.app_state = State()

        self.data_grids = []
        self._freeze = False
        self._selection = None

        self._updating = False
        self._modified = False
        self.virgin = True

        self.__figure_backup = None

        self.pp_notify = []

        self._modules = ModulesContainer()

        if view is not None:
            self.load_modules()
            fitview = fitpanel.FitPanel(self.view, self.view.canvas)

            self.view._mgr.AddPane(fitview, aui.AuiPaneInfo().Name('fit').
                              Caption('Fit').
                              Bottom().MinSize(500, 250).
                              CloseButton(False).MaximizeButton(False))
            self.view._mgr.Update()

            self.fit_controller = fitcontroller.FitController(self.selection_callback, fitview, fitinteractor.FitInteractor())
            self.codeeditor = codeeditor.new(self, view)

            self.datagrid = datagrid.create(self, self.view)
            self.datagrid.view.SetIcon(self.view.pom_ico)

            self.figure_list_controller = FigureListController(self.view, self.project.figure_list)
            self.view.SetTitle(self.project.name)
            self.load_filehistory()

            self.open_project(lpj_path)
            self.datagrid.new()
            self.update_plot()

            pfile = os.path.join(configdir(), 'perspective')
            try:
                with open(pfile) as f:
                    perspective = f.read()
            except EnvironmentError:
                print('unable to read perspective')
            except:
                pass
            else:
                wx.CallAfter(self.view._mgr.LoadPerspective, perspective, True)

            sfile = os.path.join(configdir(), 'geom')
            try:
                with open(sfile, 'rb') as f:
                    size = pickle.load(f)
            except EnvironmentError:
                print('unable to read geometry')
            except:
                pass
            else:
                wx.CallAfter(self.view.SetSize, size)
            interactor.Install(self, self.view)

    def message(self, msg, blink=False, forever=False):
        event = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=1, blink=blink, time=5000, forever=forever)
        wx.PostEvent(self.view, event)

    def load_filehistory(self):
        recent = os.path.join(configdir(), 'filehistory')
        if os.path.exists(recent):
            for path in codecs.open(recent, 'r', 'utf-8'):
                self.view.filehistory.AddFileToHistory(path.strip())

    def save_filehistory(self):
        hist = self.view.get_filehistory()
            
        recent = os.path.join(configdir(), 'filehistory')
        if not os.path.exists(configdir()):
            try:
                os.mkdir(configdir())
            except: return

        f = codecs.open(recent, 'w', 'utf-8')
        f.write(os.linesep.join(hist))
        f.close()
        
    def _set_modified(self, arg):
        title = self.view.title
        if title[-1] == '*':
            title = title[:-1]
        if arg:
            self.view.title = title+'*'
        else:
            self.view.title = title
        self._modified = arg
        self.virgin = False

    def _get_modified(self):
        return self._modified
    project_modified = property(_get_modified, _set_modified)
        
    def new_project(self, path=None):
        print('new_project',path)
        new_controller(path)

    def open_project(self, path):
        self.view.tree.AssociateModel(TreeListModel(self.project))

        if path is not None:
            msg = self.project.load(path, datastore=self.datagrid)

            if msg is not None:
                wx.CallAfter(self.view.msg_dialog, '\n'.join(msg))

            self.view.title = self.project.name
            self.view.annotations = self.project.annotations

            self.codeeditor.data = self.project.code

            if self.project.path is not None:
                self.view.filehistory.AddFileToHistory(os.path.abspath(path))
                self.save_filehistory()
            self.project_modified = False
            misc.set_cwd(path)
            #self.selection = (0,None) # needed because if loading a project on the ecommand line, nothing will be selected
            self.view.tree.selection = 0,0

            pub.sendMessage((self.view.instid, 'figurelist','needsupdate'))

    def open_recent(self, num):
        path = self.view.filehistory.GetHistoryFile(num)
        return path

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
        # wozu war denn das hier??
        #self.view.tree.build(self.project)
        if path is not None:
            misc.set_cwd(path)
        
    def notes_close(self):
        self.view.frame_annotations.Show(False)
        self.view.check_menu('Notepad', False)
        
    def close(self):
        if not self.project_modified or self.view.close_project_dialog(self.project.name):
            perspective = self.view._mgr.SavePerspective()
            pfile = os.path.join(configdir(), 'perspective')
            try:
                with open(pfile, 'w') as f:
                    f.write(perspective)
            except IOError:
                print('unable to save perspective')

            try:
                sfile = os.path.join(configdir(), 'geom')
                with open(sfile, 'wb') as f:
                    pickle.dump(self.view.GetSize(), f)
            except IOError:
                print('unable to save geometry')

            pub.sendMessage((self.view.instid, 'stop_all'))
            return True
        return False

    def import_data(self, path, one_plot_each=False):
        added_plot = False

        self._multicolumn_config = False
        plot_created = False
        if type(path) != list:
            path = [path]
        for p in path:
            try:
                _,ext = os.path.splitext(p)
                labels,data = fio.loaders.get(ext)(p)
            except (misc.PomError) as e:
                self.view.msg_dialog('{}\n\n{}'.format(p, e.value))
                continue
            else:
                if data.shape[1] > 2:
                    plotname = os.path.basename(p)
                    if not self._multicolumn_config:
                        if labels is not None:
                            res = self.view.multicolumn_import_dialog(p, collabels=labels, multiple=len(path) > 1)
                        else:
                            res = self.view.multicolumn_import_dialog(p, multiple=len(path) > 1, numcols=data.shape[1])
                        if res is not None:
                            ordering, custom, apply_to_all = res
                            if apply_to_all:
                                self._multicolumn_config = True
                        else:
                            continue
                        order = {1:'xyxy',0:'xyyy',2:custom}.get(ordering)
                else:
                    plotname = None
                    order = 'xyyy'
                if not plot_created or one_plot_each:
                    if not one_plot_each and len(path) > 1:
                        plotname = split(os.path.dirname(p))[-1]
                    plot = self.project.append_plot(name=plotname)
                    plot_created = True
                try:
                    self.project[plot].import_data(data, os.path.basename(p), labels, order)
                except (misc.PomError) as e:
                    self.view.msg_dialog('{}\n\n{}'.format(p, e.value))
                    continue
            added_plot = True
        misc.set_cwd(p)

        if added_plot:
            #self.update_tree()
            self.view.tree.selection = (plot,0)

    def show_export_dialog(self):
        if self.active_set is None: # multiple selections
            res = self.view.export_dialog_multi(misc.cwd())
            if res is not None:
                path, ext, only_vis, overwrite = res
                self.export_data(path, options=(ext, only_vis, overwrite))
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
            for dataset in sets:
                nall += 1
                if dataset.hide and only_vis:
                    continue
                name = dataset.name
                if ext is not None:
                    if name.find('.') == -1:
                        name = name+'.'+ext
                    else:
                        name = re.sub(r'\.(\w*$)', '.'+ext, name)
                nwritten += int(dataset.write(os.path.join(path, name),overwrite))
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
        from . import modules
        print('loading system modules')
        if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
            # in case peak-o-mat has been compiled with py2exe
            for name in modules.__all__:
                try:
                    mod = globals()[name]
                except KeyError:
                    continue
                for name, obj in inspect.getmembers(mod):
                    if inspect.isclass(obj):
                        if hasattr(obj, '__base__') and obj.__base__ == module.XRCModule:
                            m = obj(self, mod.__doc__)
                            self._modules.append(m)
                        elif hasattr(obj, '__base__') and obj.__base__ == module.BaseModule:
                            m = obj(self, self.view)
                            self._modules.append(m)

        else:
            for mod in modules.__all__:
                try:
                    mod = import_module('.'+mod,'peak_o_mat.modules')
                except Exception as _e:
                    print('unable to load module \'{}\''.format(mod))
                    logging.error(logging.traceback.format_exc())
                else:
                    for name, obj in inspect.getmembers(mod):
                        if inspect.isclass(obj):
                            if hasattr(obj, '__base__') and obj.__base__ == module.XRCModule:
                                m = obj(self, mod.__doc__)
                                self._modules.append(m)
                            elif hasattr(obj, '__base__') and obj.__base__ == module.BaseModule:
                                m = obj(self, self.view)
                                self._modules.append(m)
        #user modules 
        moddir = os.path.join(configdir(),'modules')
        print('loading user modules from',moddir)
        mods = [os.path.basename(x).split('.')[0] for x in glob.glob(os.path.join(moddir,'*.py'))]
        sys.path.append(moddir)

        for name in mods:
            try:
                #f,fname,descr = imp.find_module(name)
                #mod = imp.load_module(name, f, fname, descr)
                mod = import_module(name)
            except Exception as _e:
                logging.error('unable to load module \'{}\''.format(name))
                logging.error(logging.traceback.format_exc())
            else:
                for name, obj in inspect.getmembers(mod):
                    if inspect.isclass(obj):
                        if hasattr(obj, '__base__') and obj.__base__ == module.XRCModule:
                            m = obj(self, mod.__doc__)
                            self._modules.append(m)
                        elif hasattr(obj, '__base__') and obj.__base__ == module.BaseModule:
                            m = obj(self, self.view)
                            self._modules.append(m)

        #print(self._modules)

    def annotations_changed(self, txt):
        self.project.annotations = txt
        pub.sendMessage((self.view.instid, 'changed'))
        
    def set2clipboard(self):
        if wx.TheClipboard.Open():
            do = wx.CustomDataObject('selection')
            if self.selection.isplot:
                data = pickle.dumps(self.active_plot,1)
            else:
                plot, sel = self.selection
                data = pickle.dumps([self.project[plot][q] for q in sel], 1)
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
                data = pickle.loads(data)
                if type(data) in [project.PlotItem, spec.Spec]:
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
            #self.update_tree(plot)
        else:
            self.project[plot].name = name
            #self.update_tree()
        pub.sendMessage((self.view.instid, 'setattrchanged'))
        self.project_modified = True
        
    def insert_plot(self, ind):
        """\
        Insert an empty plot at index 'ind'.
        """
        self.project.insert(ind, project.Plot())
        self.update_tree()
        self.project_modified = True
        
    def add_plot(self, name=None):
        """\
        Add an empty plot.
        """
        added = self.project.add(project.Plot(name=name))
        #self.update_tree()
        self.view.tree.selection = added
        self.project_modified = True
        pub.sendMessage((self.view.instid, 'plot_added'), plotlist=['p{}'.format(n) for n in range(len(self.project))])
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
        #self.update_tree()
        self.view.tree.selection = plot, added
        self.project_modified = True

        #TODO: no receivers
        #pub.sendMessage((self.view.instid, 'dataset_added'), datasetlist=[q.name for q in self.project[plot]])
        #self.update_plot()
        return added

    def rem_attr(self, attr, only_sel=False):
        if attr not in ['weights','trafo','mod','mask']:
            raise ValueError('unkown set attribute')
        if only_sel:
            p,sel = self.selection
            for s in sel:
                setattr(self.project[p][s], attr, None)
            #if attr == 'mod':
            #    self.update_tree(p)
        else:
            for p in self.project:
                for s in p:
                    setattr(s, attr, None)
        self.update_plot()
        self.project_modified = True
        pub.sendMessage((self.view.instid, 'setattrchanged'))

    def set_limit_fitrange(self, state):
        if state:
            self.active_set.limits = self.view.canvas.GetXCurrentRange()
        else:
            self.active_set.limits = None

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
        #TODO: should not be necesary anymore
        return


        if plot is None:
            self.view.tree.update_node(-1, [x.name for x in self.project])
            for n in range(len(self.project)):
                self.update_tree(n)
        else:
            names = []
            hides = []
            models = []
            if len(self.project[plot]) > 0:
                names, hides, models = list(zip(*[(x.name,x.hide,x.model is not None) for x in self.project[plot]]))
            self.view.tree.update_node(plot, names, hides, models)

    def hide_selection(self):
        """\
        Toggle the visibility of the current selectionp.
        """
        plot, sel = self.selection
        for n,set in enumerate(self.project[plot]):
            if n in sel:
                set.hide = not set.hide
        self.update_tree(plot)
        self.update_plot()
        self.project_modified = True
        
    def delete_selection(self): # wholeplot=False)
        #TODO wholeplot sollte man cniht mehr brauchen.
        """\
        Delete the current selection. If 'wholeplot' is True, delete the whole plot
        including all sets.
        """
        plot, sel = self.selection
        if self.selection.isplot:
            if self.project.delete(plot) is None:
                self.view.msg_dialog('Plot cannot be deleted. It is referenced by a figure object.')
            else:
                #self.update_tree()
                if len(self.project) > 0:
                    self.view.tree.selection = min(len(self.project)-1,plot)
                else:
                    self._selection = None
                    #self.update_plot()
        else:
            self.project[plot].delete(sel)
            self.update_tree(plot)
            if len(self.project[plot]) > 0:
                set = max( min(max(sel)-len(sel)+1, len(self.project[plot])-1) , 0)
                self.view.tree.selection = (plot, set)
            else:
                self.view.tree.selection = plot
        self.project_modified = True

    def duplicate_selection(self):
        plot, sel = self.selection
        if self.selection.isplot:
            dupl = self.project.copy(plot)
            plot = self.project.add(dupl)
            #self.update_tree()
            self.view.tree.selection = plot
        else:
            dupl = self.project[plot].copy(sel)
            set = self.project[plot].add(dupl)
            #self.update_tree(plot)
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
        if len(sel) > 1:
            name = 'from plot {}'.format(plot)
        else:
            name = 'p{}s{}'.format(plot,sel[0],self.project[plot][sel[0]].name)

        m = max([len(self.project[plot][s]) for s in sel])
        data = np.zeros((len(sel)*2,m))

        for n,s in enumerate(sel):
            data[n*2:n*2+2,:len(self.project[plot][s])] = self.project[plot][s].xy
        self.new_datagrid((data.T, [], []), name=name)
        self.project_modified = True
        self.message('Copied {} set{} to datagrid. Press CTRL-D to open the datagrid.'.format(len(sel),'s' if len(sel) > 1 else ''))

    def xrng_callback(self):
        xr = self.view.canvas.GetXCurrentRange()
        return xr

    def selection_callback(self):
        plot, sel = self.selection
        if sel is None:
            sel = list(range(len(self.project[plot])))
        plot_sel = self.project[plot]
        dataset_sel = [self.project[plot][s] for s in sel]
        return plot_sel, dataset_sel

    def _get_selection(self):
        return self._selection
    def _set_selection(self, selection):
        class Selection(tuple):
            isplot = False
        plot, ds = selection
        if ds is None:
            ds = list(range(len(self.project[plot])))
            self._selection = Selection((plot, ds))
            self._selection.isplot = True
        else:
            self._selection = Selection((plot, ds))
        plot_sel = self.project[plot]
        dataset_sel = [self.project[plot][s] for s in ds]
        wx.CallAfter(pub.sendMessage,(self.view.instid, 'selection', 'changed'),
                     plot=plot_sel, dataset=dataset_sel)
        self.update_plot()
    selection = property(_get_selection, _set_selection, doc="the current tree selection")

    def update_plot(self, *args, **kwargs):
        #print('update plot')
        if not self._updating:
            self.view.Bind(wx.EVT_IDLE, lambda x: self._update(x, *args, **kwargs))
            self._updating = True
        else:
            pass
            #still updating

    def _update(self, evt, *args, **kwargs):
        self._updating = False
        self.view.Unbind(wx.EVT_IDLE)
        self.plot(*args, **kwargs)
        pub.sendMessage((self.view.instid, 'setattrchanged'))

        #wx.CallAfter(self.update_setinfo)

    def a_update_setinfo(self):
        pub.sendMessage((self.view.instid, 'setinfo', 'update'))

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

    def set_canvas_mode(self, mode):
        #if mode is None:
        #    self.view.canvas.RestoreLastMode()
        #else:
        self.view.canvas.state.set(mode)

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
            if 'xr' in list(kwargs.keys()):
                self.project[self.selection[0]].xrng = kwargs['xr']
            if 'yr' in list(kwargs.keys()):
                self.project[self.selection[0]].yrng = kwargs['yr']

    def autoscale(self, **kwargs):
        p,s = self.selection
        if len(kwargs) == 0:
            self.project[self.selection[0]].rng = None,None
        else:
            if 'X' in list(kwargs.keys()) and kwargs['X']:
                self.set_plot_range(xr=None)
            if 'Y' in list(kwargs.keys()) and kwargs['Y']:
                self.set_plot_range(yr=None)
            if 'fit' in list(kwargs.keys()) and kwargs['fit']:
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
        wx.CallAfter(pub.sendMessage,(self.view.instid, 'selection', 'changed'),
                     plot=self.active_plot, dataset=[self.active_set])
        #msg=self.active_set)

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
            self.active_set.model = self.fit_controller.model
            self.freeze_canvas = False
            
    def load_set_from_model(self, model, which, xr, pts):
        x = np.linspace(xr[0],xr[1],pts)

        y = model.evaluate(x, restrict=which)
        name = ' '.join(which)
        plot,sel = self.selection

        if type(y) is tuple:
            for n,yn in enumerate(y):
                self.project[plot].add(spec.Spec(x,yn,'{}_{}'.format(name,n+1)))
        else:
            self.project[plot].add(spec.Spec(x, y, name))
        self.update_tree(plot)
        self.update_plot()
        self.project_modified = True

    def show_notes(self, show=False):
        #import constgrid
        #constgrid.show_globals_frame()
        self.view.frame_annotations.Show(show)
        self.view.frame_annotations.CenterOnParent()
        self.view.check_menu('Notepad', show)

    def code_changed(self):
        self.project.code = self.codeeditor.data
        pub.sendMessage((self.view.instid, 'changed'))

    def show_codeeditor(self, show=False):
        self.view.check_menu('Code Editor', show)
        #import constgrid
        #constgrid.show_globals_frame()
        self.codeeditor.view.Show(show)

    def delete_figure(self, fig):
        item = self.project.figure_list.pop(self.project.figure_list.index(fig))
        for pd in item.values():
            pd.release()
        pub.sendMessage((self.view.instid, 'figurelist', 'needsupdate'))

    def clone_figure(self, fig):
        clone = deepcopy(fig)
        self.figure_list_controller.model.data.append(clone)
        pub.sendMessage((self.view.instid, 'figurelist', 'needsupdate'))

    def create_or_show_figure(self, show=False, model=None, discard=False):
        print('create or show', show, model, discard)
        if show:
            if model is not None:
                self.__mpm_edit_combo = model, deepcopy(model)
            else:
                self.__mpm_edit_combo = None, mplmodel.MultiPlotModel(self.project)
            #TODO: nicht jedesmal neu erzeugen!
            self.mplplot = mplcontroller.new(self, self.view, self.__mpm_edit_combo[1])

            self.mplplot.view.Show(show)
            self.mplplot.draw()
        else:
            self.mplplot.close()
            if not discard:
                if self.__mpm_edit_combo[0] in self.project.figure_list:
                    self.figure_list_controller.model.update(*self.__mpm_edit_combo)
                    #morig, mcopy = self.__mpm_edit_combo
                    #del mcopy
                else:
                    self.figure_list_controller.model.data.append(self.__mpm_edit_combo[1])
            self.__mpm_edit_combo = None

            pub.sendMessage((self.view.instid, 'figurelist', 'needsupdate'))

    def show_datagrid(self, show=False):
        self.view.check_menu('Data Grid', show)
        if show:
            self.datagrid.view.Show()
        else:
            if self.datagrid is not None:
                self.datagrid.view.Hide()

    def new_datagrid(self, data=None, the_grid=False, name=None):
        if the_grid:
            name = 'exported fit parameters'

        grid = self.datagrid.new(data, name, the_grid)

        #self.show_datagrid(True)
        self.project_modified = True
            
    def datagrid_append(self, data):
        if self.datagrid is None or self.datagrid.the_grid is None:
            self.new_datagrid(the_grid=True)
        
        plot,sel = self.selection
        self.datagrid.the_grid.add_par_row(data, self.project[plot][sel[0]].name)
        ctrl = 'CMD' if sys.platform == 'darwin' else 'CTRL'
        self.message('Selected parameters have been appended to the data grid. Press {}-d to show the data grid.'.format(ctrl),blink=False)
        self.project_modified = True

    def _set_freeze_canvas(self, state):
        self._freeze = state
    def _get_freeze_canvas(self):
        return self._freeze
    freeze_canvas = property(_get_freeze_canvas, _set_freeze_canvas)
        
    def plot(self, fit = None, floating = None, speclines = None):
        if self.app_state.working:
            return
        xr,yr = None,None
        
        self.view.canvas.SetXSpec('min')
        self.view.canvas.SetYSpec('min')

        lines = []
        ds = None

        def Line(data, colour, skipbb=False):
            if self.app_state.line_style == 0:
                return plotcanvas.Line(data, colour=colour, skipbb=skipbb)
            return plotcanvas.Marker(data, colour=colour, fillcolour=colour, marker='square', size=0.7, skipbb=skipbb)

        if self.freeze_canvas and fit is not None:
            xr = self.view.canvas.GetXCurrentRange()
            yr = self.view.canvas.GetYCurrentRange()
            ds = self.active_set
            lines = []
            y = fit.evaluate(ds.x)
            if y is not False:
                lines.append(Line(ds.xy,colour='red'))
                lines.append(plotcanvas.Line([ds.x,y], colour=wx.Colour(0,200,50), width=2, skipbb=True))
                self.view.canvas.Draw(plotcanvas.Graphics(lines),xr,yr)
            return
        else:
            self.freeze_canvas = False

        if self.selection is not None:
            plot,sel = self.selection
            if floating is not None:
                lines.append(plotcanvas.Line([floating.x,floating.y], colour=wx.Colour(0,0,255,130), width=1, skipbb=True))
            for sig,ds in enumerate(self.project[plot]):
                if ds.hide and sig not in sel:
                    continue
                if sig in sel:
                    lines.append(Line(ds.xy, 'red'))
                    if ds.weights is not None:
                        bounds_cb = ds.weights.getBounds
                        lines.append(plotcanvas.VSpan(ds.xy,bounds_cb,colour=wx.Colour(0,0,255,80)))
                    elif self.fit_controller.weights is not None:
                        bounds_cb = self.fit_controller.weights.getBounds
                        lines.append(plotcanvas.VSpan(ds.xy,bounds_cb,colour=wx.Colour(0,0,255,30)))

                    # coupled model
                    if len(sel) == len(self.project[plot]) and len(self.project[plot]) > 1:
                        y = None
                        if fit is not None:
                            y = fit.evaluate(ds.x)[sig]
                        elif self.project[plot].model is not None:
                            y = self.project[plot].model.evaluate(ds.x)[sig]
                        if y is not None:
                            lines.append(plotcanvas.Line([ds.x, y], colour=wx.Colour(0, 50, 200, 200), width=2,
                                                         skipbb=True))

                    else:
                        if fit is not None:
                            x = ds.x_limited
                            if len(x) > 0:
                                y = fit.evaluate(x)
                                #print('check y', y is False, y is None)
                                if y is not None:
                                    if len(sel) == len(self.project[plot]) and len(self.project[plot]) > 1:
                                        y = y[sig]
                                    lines.append(plotcanvas.Line([x, y], colour=wx.Colour(0, 200, 50, 200), width=2,
                                                                 skipbb=True))
                        elif ds.model is not None:
                            x = ds.x_limited
                            if len(x) > 0:
                                y = ds.mod.evaluate(x)
                                #print('check y', y is False, y is None)
                                if y is not None:
                                    if self.project[plot].model is not None and len(sel) == len(self.project[plot]) and len(self.project[plot]) > 1:
                                        y = y[sig]
                                    lines.append(plotcanvas.Line([x, y], colour=wx.Colour(0, 200, 50, 200), width=2,
                                                                 skipbb=True))
                    if self.app_state.show_peaks:
                        if fit is not None:
                            for i in ds.loadpeaks(fit, addbg=True):
                                lines.append(plotcanvas.Line(i, colour='blue', skipbb=True))
                        elif ds.model is not None:
                            for i in ds.loadpeaks(ds.model, addbg=True):
                                lines.append(plotcanvas.Line(i, colour='blue', skipbb=True))
                else:
                    if self.app_state.fast_display:
                        skip = max(1,int(len(ds.x)/config.getint('display', 'fast_max_pts', fallback=200)+.5))
                    else:
                        skip = 1
                    lines.append(Line(ds.xy[:,::skip], colour='black'))
            xr, yr = self.project[plot].rng
        for ptype, spec in self._modules.get_plot_objects():
            lines.append(getattr(plotcanvas,ptype)([spec.x,spec.y], colour=wx.Colour(0,0,250,180), width=2))

        graphics = plotcanvas.Graphics(lines)

        self.view.canvas.Draw(graphics,xr,yr)

if __name__ == '__main__':
    p = project.Project()
    p.load('../example.lpj')
    c=Controller(p)

    
