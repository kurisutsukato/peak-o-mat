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
from .model import MultiPlotModel, PlotData, LineData

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

        self.view.update_from_model(self.model)
        self.view.init_pop(self.model)

        Interactor().Install(self, view)

        if modified:
            self.view.show_model_changed()

    def close(self):
        self.model.update_from_view(self.view)
        self.view.save_pos()
        self.view.Destroy()
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
        self.model[pos].add_secondary(plot)

    def select_plot(self, plot, pos):
        if plot == -1:
            self.model.remove(pos)
            #TODO: deselect secondary plot
            self.view.enable_edit(False)
        else:
            pd =  PlotData(self.model.project,plot)
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
        #print 'redraw', update_selected
        self.__needs_update = force
        #if not force and not self.model.update_from_view(self.view):
        #    print 'not modified'
        #    return
        rows,cols = self.model.shape
        if self.__needs_update:
            self.view.figure.clf()
        self.view.figure.subplots_adjust(**self.model.adjust)

        #__plt_cmds = []
        #ax_new_scale = False
        plotcount = 0
        for row in range(rows):
            for col in range(cols):
                try:
                    pm = self.model[(row,col)]
                except KeyError:
                    continue
                else:
                    ax = self.view.figure.add_subplot(rows, cols, row*cols+col+1)
                    #plotfunc = ['plot','semilogx','semilogy','loglog'][1*pm.logx+2*pm.logy]
                    #__plt_cmds.append(plotfunc)
                    #if len(self.__plt_cmds) == len(self.view.figure.axes):
                    #    if self.__plt_cmds[plotcount] != plotfunc or pm.code.strip() != '':
                    #        ax_new_scale = True
                    #        ax.cla()
                    if len(ax.lines) == 0 or self.__needs_update: # or ax_new_scale:
                        #print 'clean draw of',pm.name
                        for s,style in pm:
                            ax.plot(s.x, s.y, **style.kwargs())
                            #getattr(ax, plotfunc)
                        set_plot_attributes(ax, pm)
                    else:
                        if update_selected and pm != self.model.selected:
                            continue
                        #print 'redrawing',pm.name
                        for line,(s,style) in zip(ax.lines,pm):
                            for attr,value in style.kwargs().items():
                                getattr(line, 'set_{}'.format(attr))(value)
                        set_plot_attributes(ax, pm)

                    #ax_new_scale = False
                    plotcount += 1
        #self.__plt_cmds = __plt_cmds
        self.__needs_update = False

        self.view.figure.canvas.draw()

        l,b,w,h = self.view.figure.bbox.bounds
        w, h = int(w), int(h)
        buf = self.view.figure.canvas.tostring_rgb()
        bmp = Bitmap.FromBuffer(w, h, buf)
        self.view.plot_view.canvas._bmp = bmp
        self.view.plot_view.canvas.needs_update = True

def set_plot_attributes(ax, pm):

    scales = ['linear','log']

    for ad in pm.axes_data:
        axis = ad.type[0]
        level = ad.type[1:]
        if level == 'pri':
            getattr(ax, 'set_{}label'.format(axis))(ad.label)
            getattr(ax, 'set_{}scale'.format(axis))(ad.scale)

            if axis == 'x':
                ax.tick_params(axis='x', which='both', direction=ad.tdir,
                               bottom=True if ad.labelpos=='bottom' and not ad.ticks_hide else False,
                               labelbottom=True if ad.labelpos=='bottom' and not ad.ticks_hide else False,
                               top=True if ad.labelpos=='top' and not ad.ticks_hide else False,
                               labeltop=True if ad.labelpos=='top' and not ad.ticks_hide else False)
                ax.xaxis.set_label_position(ad.labelpos)
            if axis == 'y':
                ax.tick_params(axis='y', which='both', direction=ad.tdir,
                               right=True if ad.labelpos == 'right' and not ad.ticks_hide else False,
                               labelright=True if ad.labelpos == 'right' and not ad.ticks_hide else False,
                               left=True if ad.labelpos == 'left' and not ad.ticks_hide else False,
                               labelleft=True if ad.labelpos == 'left' and not ad.ticks_hide else False)
                ax.yaxis.set_label_position(ad.labelpos)

    if pm.legend_show:
        ax.legend(loc=pm.legend_position, fontsize=pm.legend_fontsize)
    else:
        ax.legend_ = None

    def floatOrNone(arg):
        try:
            return None if arg == '' else float(arg)
        except ValueError:
            return None

    for ad,setrng in zip(*(pm.axes_data, [ax.set_xlim, ax.set_ylim])):
        if ad.min != ad.max:
            setrng(floatOrNone(ad.min), floatOrNone(ad.max), auto=True)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]+ ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(pm.fontsize)

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
