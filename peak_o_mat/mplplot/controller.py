__author__ = 'ck'

#from pubsub import pub as Publisher

import numpy as np
from wx import Bitmap

import code
from io import StringIO
import sys
import re
import io
import PIL

from threading import Thread
from matplotlib.ticker import FixedLocator, AutoLocator, AutoMinorLocator, LogLocator
from matplotlib.ticker import FuncFormatter, NullFormatter, ScalarFormatter, LogFormatterMathtext

from .view import ControlFrame
from .interactor import Interactor
from .model import MultiPlotModel, PlotData, LineData, AxesData, str2color

class Locals(dict):
    def __init__(self, stdout, data={}):
        super(Locals, self).__init__(data)
        self.stdout = stdout

    def __getitem__(self, name):
        try:
            return super(Locals, self).__getitem__(name)
        except KeyError:
            pass

        try:
            return getattr(self['_axes'], name)
        except AttributeError:
            # raising a KeyError will trigger lookup in the global namespace
            raise KeyError(name)

    def add(self, name, val):
        self[name] = val

class Interpreter(code.InteractiveInterpreter):
    def __init__(self, ax):

        self.errline = None
        self.out = StringIO()
        code.InteractiveInterpreter.__init__(self, {'ax':ax})

    def write(self, text):
        self.out.write(text)
        mat = re.match(r'.+, line (\d+)\D+', text)
        if mat is not None:
            self.errline = int(mat.groups()[0])-1

    def getresult(self):
        ret = self.out.getvalue(), self.errline
        self.out = StringIO()
        return ret

def loglocator(arg):
    if arg.strip() == '':
        return LogLocator()
    else:
        try:
            locs = [float(q.strip()) for q in arg.split(',')]
        except (ValueError, TypeError):
            return LogLocator()
        else:
            return FixedLocator(locs)

def locator(arg, minor=False):
    if arg.strip() == '':
        if minor:
            return AutoMinorLocator()
        else:
            return AutoLocator()
    else:
        try:
            locs = [float(q.strip()) for q in arg.split(',')]
        except (ValueError, TypeError):
            try:
                mi,ma,stp = [float(q.strip()) for q in arg.split(':')]
            except (ValueError, TypeError):
                if minor:
                    return AutoMinorLocator()
                else:
                    return AutoLocator()
            else:
                return FixedLocator(np.arange(mi,ma+stp,stp))
        else:
            return FixedLocator(locs)

class PlotController(object):
    def __init__(self, main, view, model):
        self.controller = main
        self.view = view

        self.__needs_update = None
        self.__plt_cmds = []

        self.model = model

        modified = model.modified
        print('plot controller __init__ model.shape',self.model.shape)
        self.view.update_from_model(self.model)
        self.view.init_pop(self.model)

        Interactor().Install(self, view)

        if modified:
            self.view.show_model_changed()

        if self.model.shape == (0,0):
            self.new_shape((1,1))

    def close(self):
        self.model.update_from_view(self.view)
        self.view.save_pos()
        self.view.Destroy()
        #self.view.Show(False)
        self.model = None

    def new_model(self, model):
        self.model = model
        self.__needs_update = True
        self.view.update_from_model(model)

    def new_shape(self, shape):
        self.model.shape = shape
        self.__needs_update = True
        self.redraw(force=True)

    def plot_add_secondary(self, plot, pos):
        print('controller plot_add_secondary',plot,pos)
        if plot == -1:
            if self.model[pos].plot_ref_secondary is not None:
                self.model[pos].del_secondary()
                self.model[pos].axes_data[:] = self.model[pos].axes_data[:2]
        else:
            self.model[pos].add_secondary(plot)
        self.view.update_from_model(self.model)
        self.__needs_update = True
        self.redraw(force=True)

    def add_remove_axes(self, name, selection):
        ad = self.model.selected.axes_data
        if name == 'remove':
            ad[:] = ad[:2]
        elif name in ['twinx', 'twiny']:
            tp = name[-1]
            labelpos = dict([('y', 'top'), ('x', 'right')])
            ad.append(
                AxesData('twin{}'.format(tp), 'label', labelpos[tp], '', '', 'linear', False, 3, '', '', 'in', '0, 0, 0'))
        elif name == 'inset':
            for axis in ['insetx', 'insety']:
                tp = axis[-1]
                labelpos = dict([('x', 'top'), ('y', 'right')])
                ad.append(
                    AxesData('inset{}'.format(tp), 'label', labelpos[tp], '', '', 'linear', False, 3, '', '', 'in', '0, 0, 0'))
        self.view.update_from_model(self.model)
        self.redraw(force=True)

    def select_plot(self, plot, pos):
        if plot == -1:
            self.model.remove(pos)
            #TODO: deselect secondary plot
            self.model.selected = None
            self.view.update_from_model(self.model)
            self.view.enable_edit(False)
        else:
            if self.model[pos] is not None and self.model[pos].plot_ref == plot:#
                return
            pd = PlotData(self.model.project,plot)
            print('new pd:', plot, pd.plot_ref_secondary)
            self.model.add(pd, pos)
            self.view.update_from_model(self.model)
            self.view.enable_edit(True)
        self.__needs_update = True
        self.redraw(force=True)

    def select_gridposition(self, pos):
        self.model.select(pos)
        self.view.update_from_model(self.model)

    def new_order(self, swap):
        self.model.swap(*swap)
        self.__needs_update = True
        self.redraw(force=True)

    def resize_frame(self):
        self.model.update_from_view(self.view)
        self.view.resize_canvas(self.model.width, self.model.height, self.view.figure.dpi)
        self.redraw(force=True)

    def draw(self):
        self.resize_frame()
        #self.redraw(force=True)

    def update_model(self):
        self.model.update_from_view(self.view)

    def redraw(self, update_selected=False, force=False):
        if hasattr(self, 't') and self.t.is_alive():
            self.view._redraw_requested = (update_selected, force)
        else:
            self.t = Thread(target=self._redraw, args=(update_selected, force))
            self.t.start()

    def _redraw(self, update_selected=False, force=False):
        #print('_redraw, update:{}, force:{}'.format(update_selected, force))
        #self.__needs_update = force
        #if not force and not self.model.update_from_view(self.view):
        #    print 'not modified'
        #    return

        rows,cols = self.model.shape
        self.view.figure.subplots_adjust(**self.model.adjust)
        if force:
            self.view.figure.clf()

        def getaxes(f):
            return [ax for ax in f.axes if ax._sharex is None and ax._sharey is None]

        if len(getaxes(self.view.figure)) == rows*cols:
            axes = np.reshape(np.atleast_2d(getaxes(self.view.figure)), (rows,cols))
        else:
            axes = np.atleast_2d(self.view.figure.subplots(rows, cols)).reshape(rows,cols)
        for row in range(rows):
            for col in range(cols):
                try:
                    pm = self.model[(row,col)]
                except KeyError:
                    continue
                else:
                    if pm is None:
                        continue
                    ax = axes[row,col]
                    ax.relim()
                    ax.autoscale()
                    if len(ax.lines) == 0 or self.__needs_update:
                        #print('ax fresh draw')
                        for s, style in pm.primary():
                            ax.plot(s.x, s.y, **style.kwargs())
                    else:
                        #print('ax redrawing')
                        if update_selected and pm != self.model.selected:
                            #print('skip non selected')
                            continue
                        for line,(s,style) in zip(ax.lines,pm.primary()):
                            for attr,value in style.kwargs().items():
                                getattr(line, 'set_{}'.format(attr))(value)
                    set_plot_attributes(ax, pm)
                    set_axis_attributes(ax, 'x', pm.axes_data['x'])
                    set_axis_attributes(ax, 'y', pm.axes_data['y'])
                    if 'twinx' in pm.axes_data:
                        if hasattr(ax, 'mytwinx'):
                            twinx = ax.mytwinx
                            #print('found twinx axis')
                        else:
                            twinx = ax.twinx()
                            ax.mytwinx = twinx
                        twinx.relim()
                        twinx.autoscale()
                        try:
                            if len(twinx.lines) == 0 or self.__needs_update:
                                #print('twinx fresh draw')
                                for s, style in pm.secondary():
                                    twinx.plot(s.x, s.y, **style.kwargs())
                            else:
                                #print('twinx redrawing')
                                if update_selected and pm != self.model.selected:
                                    #print('skip non selected')
                                    continue
                                for line,(s,style) in zip(twinx.lines,pm.secondary()):
                                    for attr,value in style.kwargs().items():
                                        getattr(line, 'set_{}'.format(attr))(value)
                        except (AttributeError, KeyError): #KeyError happens if second plot was not defined yet but axis exists
                            continue
                        set_axis_attributes(twinx, 'y', pm.axes_data['twinx'])
                    elif 'twiny' in pm.axes_data:
                        if hasattr(ax, 'mytwiny'):
                            twiny = ax.mytwiny
                            #print('found twiny axis')
                        else:
                            twiny = ax.twiny()
                            ax.mytwiny = twiny
                        twiny.relim()
                        twiny.autoscale()
                        try:
                            if len(twiny.lines) == 0 or self.__needs_update:
                                #print('twiny fresh draw')
                                for s, style in pm.secondary():
                                    twiny.plot(s.x, s.y, **style.kwargs())
                            else:
                                #print('twiny redrawing')
                                if update_selected and pm != self.model.selected:
                                    #print('skip non selected')
                                    continue
                                for line,(s,style) in zip(twiny.lines,pm.secondary()):
                                    for attr,value in style.kwargs().items():
                                        getattr(line, 'set_{}'.format(attr))(value)
                        except (AttributeError, KeyError): #KeyError happens if second plot was not defined yet but axis exists
                            continue
                        set_axis_attributes(twiny, 'x', pm.axes_data['twiny'])
                    elif 'insetx' in pm.axes_data:
                        if hasattr(ax, 'myinset'):
                            #print('found inset')
                            inset = ax.myinset
                            #print(pm.box.bnds())
                            inset.position = pm.box.bnds()
                        else:
                            inset = ax.inset_axes(pm.box.bnds())
                            ax.myinset = inset
                        inset.relim()
                        inset.autoscale()
                        try:
                            inset.patch.set_alpha(0.0)
                            if len(inset.lines) == 0 or self.__needs_update:
                                for s, style in pm.secondary():
                                    inset.plot(s.x, s.y, **style.kwargs())
                            else:
                                if update_selected and pm != self.model.selected:
                                    #print('skip non selected')
                                    continue
                                for line,(s,style) in zip(inset.lines,pm.secondary()):
                                    for attr,value in style.kwargs().items():
                                        getattr(line, 'set_{}'.format(attr))(value)
                        except (AttributeError, KeyError): #KeyError happens if second plot was not defined yet but axis exists
                            continue
                        set_axis_attributes(inset, 'x', pm.axes_data['insetx'])
                        set_axis_attributes(inset, 'y', pm.axes_data['insety'])

        self.__needs_update = False

        self.view.figure.canvas.draw()

        l,b,w,h = self.view.figure.bbox.bounds
        w, h = int(w), int(h)
        buf = self.view.figure.canvas.tostring_rgb()
        bmp = Bitmap.FromBuffer(w, h, buf)
        self.view.plot_view.canvas._bmp = bmp
        self.view.plot_view.canvas.needs_update = True

def set_plot_attributes(ax, pm):
    if pm.legend_show:
        ax.legend(loc=pm.legend_position, fontsize=pm.legend_fontsize, frameon=pm.legend_frameon)
    else:
        ax.legend_ = None

    if pm.label_title != '':
        ax.set_title(pm.label_title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]+ ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(pm.fontsize)

def set_axis_attributes(ax, axis, ad):
    getattr(ax, 'set_{}label'.format(axis))(ad.label)
    getattr(ax, 'set_{}scale'.format(axis))(ad.scale)

    ax.tick_params(axis=axis, which='both', direction=ad.tdir,
                   bottom=True if ad.labelpos=='bottom' and not ad.ticks_hide else False,
                   labelbottom=True if ad.labelpos=='bottom' and not ad.ticks_hide else False,
                   top=True if ad.labelpos=='top' and not ad.ticks_hide else False,
                   labeltop=True if ad.labelpos=='top' and not ad.ticks_hide else False,
                   left = True if ad.labelpos == 'left' and not ad.ticks_hide else False,
                   labelleft = True if ad.labelpos == 'left' and not ad.ticks_hide else False,
                   right = True if ad.labelpos == 'right' and not ad.ticks_hide else False,
                   labelright = True if ad.labelpos == 'right' and not ad.ticks_hide else False,
                   colors = str2color(ad.color))

    getattr(ax, '{}axis'.format(axis)).set_label_position(ad.labelpos)
    getattr(ax, '{}axis'.format(axis)).label.set_color(str2color(ad.color))

    def floatOrNone(arg):
        try:
            return None if arg == '' else float(arg)
        except ValueError:
            return None

    if floatOrNone(ad.min) is None or floatOrNone(ad.max) is None:
        if getattr(ax, '{}axis_inverted'.format(axis))():
            getattr(ax, 'invert_{}axis'.format(axis))()
    if ad.min != ad.max:
        print('set axis limits', getattr(ax, 'set_{}lim'.format(axis))(floatOrNone(ad.min), floatOrNone(ad.max)))

def new(controller, parent, plotmodel):
    return PlotController(controller, ControlFrame(parent), plotmodel)

if __name__ == '__main__':
    from ..project import Project

    p = Project()
    print(p.load('d:/dev/pom/trunk/example.lpj'))

    import wx
    app = wx.App()
    c = new(None, None, MultiPlotModel(p))
    c.draw()
    c.view.Show(True)
    app.MainLoop()
