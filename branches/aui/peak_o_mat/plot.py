import wx
from pubsub import pub

import numpy as np
from scipy.interpolate import interp1d
import time

from . import misc_ui


class Log(object):
    def __init__(self):
        self.last = ''
        self.count = 2

    def print(self, arg):
        if arg == self.last:
            print('\r{} {:d}'.format(arg, self.count), end='')
            self.count += 1
        else:
            print()
            print('\r{}'.format(arg), end='')
            self.last = arg
            self.count = 2


log = Log()


class PolyPoints:
    dataspace = 'user'

    def __init__(self, points, attr, skipbb=False):
        self.skipbb = skipbb
        points = np.array(points).astype('float')
        r, c = points.shape
        if r == 2:
            self._points = np.transpose(points)
        else:
            self._points = points
        self._logscale = [False, False]
        self.currentScale = (1, 1)
        self.currentShift = (0, 0)
        self.scaled = self.points
        self.attributes = {}
        self.attributes.update(self._attributes)
        for name, value in list(attr.items()):
            if name not in list(self._attributes.keys()):
                raise KeyError(
                    "Style '%s' attribute incorrect. Should be one of %s" % (name, list(self._attributes.keys())))
            self.attributes[name] = value

    def setLogScale(self, logscale):
        self._logscale = logscale

    @property
    def points(self):
        if len(self._points) > 0:
            data = np.array(self._points, copy=True)
            if self._logscale[0]:
                data = self.log10(data, 0)
            if self._logscale[1]:
                data = self.log10(data, 1)
            return data
        else:
            return self._points

    def log10(self, data, ind):
        data = np.compress(data[:, ind] > 0, data, 0)
        data[:, ind] = np.log10(data[:, ind])
        return data

    def boundingBox(self):
        if len(self.points) == 0:
            # no curves to draw
            # defaults to (-1,-1) and (1,1) but axis can be set in Draw
            minXY = np.array([-1.0, -1.0])
            maxXY = np.array([1.0, 1.0])
        else:
            minXY = np.minimum.reduce(self.points)
            maxXY = np.maximum.reduce(self.points)
            dx, dy = (maxXY - minXY) * 0.1
            minXY -= [dx, dy]
            maxXY += [dx, dy]
        return minXY, maxXY

    def scaleAndShift(self, scale=(1, 1), shift=(0, 0), bb=None):
        if len(self.points) == 0:
            # no curves to draw
            return
        bb = np.asarray(bb)
        # restrict to points actually visible in the current plot range
        points = self.points[np.argsort(self.points[:,0])]
        rng = np.searchsorted(points[:,0], bb[:,0])
        points = points[rng[0]:rng[1]]

        if (scale is not self.currentScale) or (shift is not self.currentShift):
            # update point scaling
            self.scaled = scale * points + shift
            self.currentScale = scale
            self.currentShift = shift
        # else unchanged use the current scaling


class PolyLine(PolyPoints):
    """Class to define line type and style
        - All methods except __init__ are private.
    """

    _attributes = {'colour': 'black',
                   'width': 1,
                   'style': wx.SOLID}

    def __init__(self, points, skipbb=False, **attr):
        """Creates PolyLine object
            points - sequence (array, tuple or list) of (x,y) points making up line
            **attr - key word attributes
                Defaults:
                    'colour'= 'black',          - wx.Pen Colour any wx.Colour
                    'width'= 1,                 - Pen width
                    'style'= wx.SOLID,          - wx.Pen style
        """

        PolyPoints.__init__(self, points, attr, skipbb=skipbb)

    def draw(self, dc):
        colour = self.attributes['colour']
        width = self.attributes['width']
        style = self.attributes['style']
        if not isinstance(colour, wx.Colour):
            colour = wx.Colour(colour)
        pen = wx.Pen(colour, width, style)
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        if len(self.scaled) > 0:
            dc.DrawLines(self.scaled.astype(int))

    def getSymExtent(self):
        """Width and Height of Marker"""
        h = self.attributes['width']
        w = 5 * h
        return (w, h)


class PolyMarker(PolyPoints):
    """Class to define marker type and style
        - All methods except __init__ are private.
    """

    _attributes = {'colour': 'black',
                   'width': 1,
                   'size': 2,
                   'fillcolour': None,
                   'fillstyle': wx.SOLID,
                   'marker': 'circle'}

    def __init__(self, points, skipbb=False, **attr):
        """Creates PolyMarker object
        points - sequence (array, tuple or list) of (x,y) points
        **attr - key word attributes
            Defaults:
                'colour'= 'black',          - wx.Pen Colour any wx.Colour
                'width'= 1,                 - Pen width
                'size'= 2,                  - Marker size
                'fillcolour'= same as colour,      - wx.Brush Colour any wx.Colour
                'fillstyle'= wx.SOLID,      - wx.Brush fill style (use wx.TRANSPARENT for no fill)
                'marker'= 'circle'          - Marker shape

            Marker Shapes:
                - 'circle'
                - 'dot'
                - 'square'
                - 'triangle'
                - 'triangle_down'
                - 'cross'
                - 'plus'
        """

        PolyPoints.__init__(self, points, attr, skipbb=skipbb)

    def draw(self, dc, coord=None):
        colour = self.attributes['colour']
        width = self.attributes['width']
        size = self.attributes['size']
        fillcolour = self.attributes['fillcolour']
        fillstyle = self.attributes['fillstyle']
        marker = self.attributes['marker']

        if colour and not isinstance(colour, wx.Colour):
            colour = wx.Colour(colour)
        if fillcolour and not isinstance(fillcolour, wx.Colour):
            fillcolour = wx.Colour(fillcolour)

        dc.SetPen(wx.Pen(colour, width))
        if fillcolour:
            dc.SetBrush(wx.Brush(fillcolour, fillstyle))
        else:
            dc.SetBrush(wx.Brush(colour, fillstyle))
        if coord == None:
            self._drawmarkers(dc, self.scaled, marker, size)
        else:
            self._drawmarkers(dc, coord, marker, size)  # draw legend marker

    def getSymExtent(self):
        """Width and Height of Marker"""
        s = 5 * self.attributes['size']
        return (s, s)

    def _drawmarkers(self, dc, coords, marker, size=1):
        f = eval('self._' + marker)
        f(dc, coords, size)

    def _dot(self, dc, coords, size=1):
        dc.DrawPointList(coords.astype(int))

    def _square(self, dc, coords, size=1):
        fact = 2.5 * size
        wh = 5.0 * size
        rect = np.zeros((len(coords), 4), dtype='float') + [0.0, 0.0, wh, wh]
        rect[:, 0:2] = coords - [fact, fact]
        dc.DrawRectangleList(rect.astype(int))


class Spikes(PolyPoints):
    dataspace = 'mixed'
    _attributes = {'colour': 'black',
                   'width': 1,
                   'style': wx.SOLID}

    def __init__(self, points, **attr):
        PolyPoints.__init__(self, np.asarray(points).T, attr)
        self.skipbb = True

    def scaleAndShift(self, scale, shift, bb, boxorigin, boxsize):
        if len(self.points) == 0:
            # no curves to draw
            pass
        elif (scale is not self.currentScale) or (shift is not self.currentShift):
            # update point scaling
            off_x, off_y = boxorigin
            width, height = boxsize

            self.scaled = (scale * self.points + shift)
            points = self.points
            xmin, xmax = bb[0][0], bb[1][0]
            yrange = np.abs(bb[0][1] - bb[1][1])
            sel = np.where(np.logical_and(points[:, 0] >= xmin, points[:, 0] <= xmax))[0]
            self.scaled = np.take(self.scaled, sel, axis=0)
            points = np.take(points, sel, axis=0)
            try:
                self.scaled[:, 1] = off_y - height * points[:, 1] / points[:, 1].max()
            except ValueError:
                print('ValueError', off_y, height, points)
                return
            self.currentScale = scale
            self.currentShift = shift
            tmp = np.array((self.scaled * np.array([1, 0]) + np.array([0, height]), self.scaled))
            tmp = tmp.transpose((1, 0, 2))
            tmp = tmp.reshape((len(self.scaled), 4))
            self.scaled = tmp

    def draw(self, dc):
        colour = self.attributes['colour']
        width = self.attributes['width']
        style = self.attributes['style']
        if not isinstance(colour, wx.Colour):
            colour = wx.Colour(colour)
        pen = wx.Pen(colour, width, style)
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        dc.DrawLineList(self.scaled.astype(int))


class VSpan(PolyLine):
    _attributes = {'colour': 'black',
                   'width': 1,
                   'style': wx.SOLID}

    def __init__(self, points, bounds_cb, **attr):
        self.skipbb = True
        PolyPoints.__init__(self, points.T, attr)
        self.bounds_cb = bounds_cb

    def scaleAndShift(self, scale=(1, 1), shift=(0, 0), bb=None):
        if (scale is not self.currentScale) or (shift is not self.currentShift):
            # update point scaling
            self.scaled = scale * self.points + shift
            self.currentScale = scale
            self.currentShift = shift

        bounds = self.bounds_cb(self.points.T).T
        bounds_low = self.currentScale * (np.take(bounds, [0, 0], axis=1) * [0, 1]) + self.currentShift
        bounds_high = self.currentScale * (np.take(bounds, [1, 1], axis=1) * [0, 1]) + self.currentShift

        x, y = self.scaled.T
        nx = np.linspace(min(x[0], x[-1]), max(x[0], x[-1]), abs(int(x[-1] - x[0])))

        ip = interp1d(x, bounds_low[:, 1])
        ylow = ip(nx)
        ip = interp1d(x, bounds_high[:, 1])
        yhigh = ip(nx)

        tmp = np.vstack((nx, ylow, nx, yhigh)).T.tolist()
        self.scaled = tmp

    def draw(self, dc):
        colour = self.attributes['colour']
        width = self.attributes['width']
        style = self.attributes['style']
        if not isinstance(colour, wx.Colour):
            colour = wx.Colour(colour)
        pen = wx.Pen(colour, width, style)
        pen.SetCap(wx.CAP_BUTT)
        dc.SetPen(pen)
        dc.DrawLineList(np.asarray(self.scaled, dtype=int))

class PlotGraphics:
    """Container to hold PolyXXX objects and graph labels
        - All methods except __init__ are private.
    """

    def __init__(self, objects, title='', xLabel='', yLabel=''):
        """Creates PlotGraphics object
        objects - list of PolyXXX objects to make graph
        title - title shown at top of graph
        xLabel - label shown on x-axis
        yLabel - label shown on y-axis
        """
        if type(objects) not in [list, tuple]:
            raise TypeError("objects argument should be list or tuple")
        self.objects = objects
        self.title = title
        self.xLabel = xLabel
        self.yLabel = yLabel

    def boundingBox(self):
        if len(self.objects) == 0:
            return np.array([-1.0, -1.0]), np.array([1.0, 1.0])
        p1, p2 = np.array([-1.0, -1.0]), np.array([1.0, 1.0])
        if len(self.objects) > 0:
            for o in self.objects:
                if not o.skipbb:
                    break
            p1, p2 = o.boundingBox()
        for o in self.objects:
            if not o.skipbb:
                p1o, p2o = o.boundingBox()
                p1 = np.minimum(p1, p1o)
                p2 = np.maximum(p2, p2o)
        for o in self.objects:
            if o.skipbb:
                o.bb = p1, p2
        return p1, p2

    def setLogScale(self, logscale):
        if type(logscale) != list:
            raise TypeError('logscale must be a tuple of bools, e.g. (False, False)')
        if len(self.objects) == 0:
            return
        for o in self.objects:
            o.setLogScale(logscale)

    def scaleAndShift(self, scale=(1, 1), shift=(0, 0), bb=None, boxorigin=None, boxsize=None):
        for o in self.objects:
            if o.dataspace == 'user':
                o.scaleAndShift(scale, shift, bb)
            elif o.dataspace in ['mixed', 'screen']:
                o.scaleAndShift(scale, shift, bb, boxorigin, boxsize)

    def setXLabel(self, xLabel=''):
        """Set the X axis label on the graph"""
        self.xLabel = xLabel

    def setYLabel(self, yLabel=''):
        """Set the Y axis label on the graph"""
        self.yLabel = yLabel

    def setTitle(self, title=''):
        """Set the title at the top of graph"""
        self.title = title

    def getXLabel(self):
        """Get x axis label string"""
        return self.xLabel

    def getYLabel(self):
        """Get y axis label string"""
        return self.yLabel

    def getTitle(self, title=''):
        """Get the title at the top of graph"""
        return self.title

    def draw(self, dc):
        for o in self.objects:
            o.draw(dc)

    def getSymExtent(self):
        """Get max width and height of lines and markers symbols for legend"""
        symExt = self.objects[0].getSymExtent()
        for o in self.objects[1:]:
            oSymExt = o.getSymExtent()
            symExt = np.maximum(symExt, oSymExt)
        return symExt

    def getLegendNames(self):
        """Returns list of legend names"""
        lst = [None] * len(self)
        for i in range(len(self)):
            lst[i] = self.objects[i].getLegend()
        return lst

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, item):
        return self.objects[item]


class Interactor:
    def __init__(self):
        # Zooming variables
        self._zoomInFactor = 1 / 1.2
        self._zoomOutFactor = 1.2
        self._zoomCorner1 = np.array([0.0, 0.0])  # left mouse down corner
        self._zoomCorner2 = np.array([0.0, 0.0])  # left mouse up corner
        self._hasDragged = False

        self._mousestart = None
        self._mousestop = None
        self._mouseClicked = False

        self._moving_handle = False

        self._adjustingSB = False

    def install(self, view):
        self.view = view

        # Create some mouse evts for zooming
        self.view.canvas.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
        self.view.canvas.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
        self.view.canvas.Bind(wx.EVT_MOTION, self.OnMotion)
        self.view.canvas.Bind(wx.EVT_LEFT_DCLICK, self.OnMouseDoubleClick)
        self.view.canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnMouseRightDown)
        self.view.canvas.Bind(wx.EVT_MIDDLE_UP, self.OnMouseMiddleUp)
        self.view.canvas.Bind(wx.EVT_MIDDLE_DOWN, self.OnMouseMiddleDown)

        # scrollbar evts
        self.view.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnScroll)
        self.view.Bind(wx.EVT_SCROLL_PAGEUP, self.OnScroll)
        self.view.Bind(wx.EVT_SCROLL_PAGEDOWN, self.OnScroll)
        self.view.Bind(wx.EVT_SCROLL_LINEUP, self.OnScroll)
        self.view.Bind(wx.EVT_SCROLL_LINEDOWN, self.OnScroll)

        self.view.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        self.view.canvas.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        self.view.canvas.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

        # OnSize called to make sure the buffer is initialized.
        # This might result in OnSize getting called twice on some
        # platforms at initialization, but little harm done.
        # wx.CallAfter(self.OnSize,None) # sets the initial size based on client size

    def OnMouseEnter(self, evt):
        if wx.GetTopLevelParent(self.view).IsActive():
            self.view.SetFocusIgnoringChildren()

    def OnMouseLeave(self, evt):
        return
        if wx.GetTopLevelParent(self.view).IsActive():
            self.view.GetParent().SetFocusIgnoringChildren()

    def Shout(self, msg, target=0):
        evt = misc_ui.ShoutEvent(self.view.GetId(), msg=msg, target=target)
        wx.PostEvent(self.view, evt)

    def updatePlot(self, msg, cmd=None):
        if cmd is not None:
            if not self.view.state.eq('getpars'):
                cmd = misc_ui.GOTPARS_END
                self.view.state.restore_last()
            evt = misc_ui.ParEvent(self.view.GetId(), cmd=cmd)
            wx.PostEvent(self.view, evt)
        if msg is not None:
            self.Shout(str(msg), 1)

    def range_changed(self):
        xr = self.view.GetXCurrentRange()
        yr = self.view.GetYCurrentRange()
        evt = misc_ui.RangeEvent(self.view.GetId(), range=(xr, yr))
        wx.PostEvent(self.view, evt)

    def handles_changed(self, data='x'):
        self.view._handles['fix'] = self.view._handles['fix'].take(np.argsort(self.view._handles['fix'], axis=0)[:, 0],
                                                                   axis=0)
        evt = misc_ui.HandlesChangedEvent(self.view.GetId(), handles=self.view._handles['fix'])
        wx.PostEvent(self.view, evt)

    # evt handlers **********************************

    def OnWheel(self, evt):
        X, Y = self.view._getXY(evt)
        if evt.GetWheelRotation() < 0:
            zoom = [1.0 if evt.ShiftDown() else self._zoomOutFactor, 1.0 if evt.ControlDown() else self._zoomOutFactor]
            self.view.Zoom((X, Y), zoom)
        else:
            zoom = [1.0 if evt.ShiftDown() else self._zoomInFactor, 1.0 if evt.ControlDown() else self._zoomInFactor]
            self.view.Zoom((X, Y), zoom)
        self.range_changed()

    def OnMotion(self, evt):
        self.Shout('X: %.5e   Y: %.5e' % self.view.GetXY(evt))
        if self.view.state.eq('getpars') and len(self.view._cmds) > 0:
            cmd, cb = self.view._cmds[0]
            if 'm' in cmd:
                x, y = self.view.GetXY(evt)
                arg = {'x': x, 'y': y, 'xy': (x, y)}[cmd.stripm()]
                cb(arg)
                self.updatePlot(None, misc_ui.GOTPARS_MOVE)
        elif self.view.state.eq('erase') and evt.LeftIsDown():
            pt = self.view.GetXY(evt)
            self.view._setRubberBand(self._mousestart, pt)  # add new
            self.view.Redraw()
        elif self.view.state.eq('handle') and self._moving_handle:
            pt = self.view.GetXY(evt)
            is_close = self.view._close_to_handle(pt)
            if is_close is not False:
                self._save = None
                self.view.SetCursor(self.view.HandCursor)
            else:
                self.view.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
                self.view._handles['moving'] = pt
            self.view.Redraw()
        elif self.view.state.eq('handle'):
            pt = self.view.GetXY(evt)
            is_close = self.view._close_to_handle(pt)
            if is_close is not False:
                self.view.SetCursor(self.view.HandCursor)
            else:
                self.view.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        elif self.view.state.eq('xmarker') and evt.LeftIsDown():
            self._mousestop = self.view.GetXY(evt)
            self.view._setXMarker(rng=(self._mousestart[0], self._mousestop[0]))
            self.view.Redraw()
            pub.sendMessage((self.view.instid, 'plot', 'xmarker'), wl=(self._mousestart[0], self._mousestop[0]))
        elif self.view.state.eq('zoom') and evt.LeftIsDown():
            if self._hasDragged:
                self.view._setRubberBand(self._zoomCorner1, self._zoomCorner2)  # remove old
            else:
                self._hasDragged = True
            self._zoomCorner2[0], self._zoomCorner2[1] = self.view._getXY(evt)
            self.view._setRubberBand(self._zoomCorner1, self._zoomCorner2)  # add new
            self.view.Redraw()
        elif (self.view.state.eq('drag') and evt.LeftIsDown()) or evt.MiddleIsDown():
            coordinates = evt.GetPosition()
            newpos, oldpos = [np.array(self.view.PositionScreenToUser(q)) for q in
                              [coordinates, self._screenCoordinates]]
            dist = [newpos - oldpos, np.log10(newpos / oldpos)]

            self._screenCoordinates = coordinates

            if self.view.last_draw is not None:
                graphics, xAxis, yAxis = self.view.last_draw
                dx = dist[int(self.view._logscale[0])][0]
                dy = dist[int(self.view._logscale[1])][1]
                yAxis -= dy
                xAxis -= dx
                self.view._Draw(graphics, xAxis, yAxis)

    def OnMouseLeftDown(self, evt):
        self._zoomCorner1[0], self._zoomCorner1[1] = self.view._getXY(evt)
        self._screenCoordinates = np.array(evt.GetPosition())
        self._mousestart = self._mousestop = self.view.GetXY(evt)

        if evt.ShiftDown():
            pt = self.view.GetXY(evt)
            write_clipboard('{}'.format(pt[0]))
            pub.sendMessage((self.view.instid, 'message'), msg='X-coordinate copied to clipboard.')
        if self.view.state.eq('getpars') and len(self.view._cmds) > 0:
            cmd, cb = self.view._cmds[0]
            x, y = self.view.GetXY(evt)
            arg = {'x': x, 'y': y, 'xy': (x, y)}[str(cmd)]
            cb(arg)
            self.view._cmds.pop(0)
            self.updatePlot(None, misc_ui.GOTPARS_DOWN)
            if len(self.view._cmds) == 0:
                self.updatePlot(None, misc_ui.GOTPARS_END)
                self.view.state.restore_last()
        elif self.view.state.eq('handle'):
            pt = self.view.GetXY(evt)
            is_close = self.view._close_to_handle(pt)
            self._save = None
            if is_close is not False:
                indx = list(range(self.view._handles['fix'].shape[0]))
                indx.pop(is_close)
                self.view._handles['moving'] = self.view._handles['fix'][is_close]
                # self._drawHandle(pt)
                self._save = None
                self._moving_handle = True
                self.view._handles['fix'] = np.take(self.view._handles['fix'], indx, axis=0)
            else:
                self.view._handles['fix'] = np.vstack((self.view._handles['fix'], np.atleast_2d(pt)))
                self._moving_handle = False
                self.view.Redraw()
                self.handles_changed()
        elif self.view.state.eq('xmarker'):
            pt = self.view.GetXY(evt)
            self.view._setXMarker(x=pt[0])
            self.view.Redraw()
            pub.sendMessage((self.view.instid, 'plot', 'xmarker'), wl=[pt[0]])
        elif self.view.state.eq('drag'):
            self.view.SetCursor(self.view.GrabHandCursor)
            self.view.canvas.CaptureMouse()
        else:
            pt = self.view.GetXY(evt)
            write_clipboard('{}'.format(pt[0]))

    def OnMouseLeftUp(self, evt):
        self.view._corner1 = self.view._corner2 = None
        if self.view.state.eq('erase'):
            self._mousestop = self.view.GetXY(evt)
            x1, y1 = self._mousestart
            x2, y2 = self._mousestop
            pub.sendMessage((self.view.instid, 'canvas', 'erase'),
                            msg=((min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2))))
            self._hasDragged = False
        elif self.view.state.eq('zoom'):
            if self._hasDragged == True:
                self._zoomCorner2[0], self._zoomCorner2[1] = self.view._getXY(evt)
                self._hasDragged = False  # reset flag
                minX, minY = np.minimum(self._zoomCorner1, self._zoomCorner2)
                maxX, maxY = np.maximum(self._zoomCorner1, self._zoomCorner2)
                if self.view.last_draw != None:
                    self.view.Draw(self.view.last_draw[0], xAxis=(minX, maxX), yAxis=(minY, maxY))
                    self.range_changed()
        elif self.view.state.eq('drag'):
            self.view.SetCursor(self.view.HandCursor)
            if self.view.canvas.HasCapture():
                self.view.canvas.ReleaseMouse()
            self.range_changed()
        elif self.view.state.eq('handle') and self._moving_handle:
            pt = self.view.GetXY(evt)
            is_close = self.view._close_to_handle(pt)
            if is_close is False and not self.view._outside(pt):
                self.view._handles['fix'] = np.vstack((self.view._handles['fix'], np.atleast_2d(pt)))
            self.view._handles['moving'] = None
            self._moving_handle = False
            self.handles_changed()
        elif self.view.state.eq('xmarker'):
            if np.any(self._mousestart != self._mousestop):
                pub.sendMessage((self.view.instid, 'plot', 'xmarker'), wl=(self._mousestart[0], self._mousestop[0]))

    def OnMouseDoubleClick(self, evt):
        if self.view.state.eq('zoom'):
            # Give a little time for the click to be totally finished
            # before (possibly) removing the scrollbars and trigering
            # size evts, etc.
            wx.FutureCall(200, self.view.Reset)

    def OnMouseRightDown(self, evt):
        if evt.ShiftDown():
            pt = self.view.GetXY(evt)
            write_clipboard('{}'.format(pt[1]))
            pub.sendMessage((self.view.instid, 'message'), msg='Y-coordinate copied to clipboard.')
        elif self.view.state.eq('zoom'):
            X, Y = self.view._getXY(evt)
            self.view.Zoom((X, Y), (self._zoomOutFactor, self._zoomOutFactor))
        elif self.view.state.eq('handle'):
            pt = self.view.GetXY(evt)
            is_close = self.view._close_to_handle(pt)
            if is_close is not False and self.view._handles['fix'].shape[0] > 2:
                indx = list(range(self.view._handles['fix'].shape[0]))
                indx.pop(is_close)
                self.view.Redraw()
                self._moving_handle = False
                self.view._handles['fix'] = np.atleast_2d(np.take(self.view._handles['fix'], indx, axis=0))
                self.handles_changed()

    def OnMouseMiddleUp(self, evt):
        if self.view.state.eq('drag'):
            self.view.state.restore_last()
            self.range_changed()

    def OnMouseMiddleDown(self, evt):
        self._screenCoordinates = np.array(evt.GetPosition())
        self._mousestart = self._mousestop = self.view.GetXY(evt)

        if evt.ShiftDown():
            x, y = self.view.GetXY(evt)
            text = '{:.16f};{:.16f}'.format(x, y)
            write_clipboard(text)
            pub.sendMessage((self.view.instid, 'message'), msg='Point-coordinate copied to clipboard.')
        else:
            self.view.state.set('drag')

    def OnScroll(self, evt):
        if not self._adjustingSB:
            self._sb_ignore = True
            sbpos = evt.GetPosition()

            if evt.GetOrientation() == wx.VERTICAL:
                fullrange, pagesize = self.view.sb_vert.GetRange(), self.view.sb_vert.GetPageSize()
                sbpos = fullrange - pagesize - sbpos
                dist = sbpos * self.view._sb_yunit - (self.view._getYCurrentRange()[0] - self.view._sb_yfullrange[0])
                self.view.ScrollUp(dist)

            if evt.GetOrientation() == wx.HORIZONTAL:
                dist = sbpos * self.view._sb_xunit - (self.view._getXCurrentRange()[0] - self.view._sb_xfullrange[0])
                self.view.ScrollRight(dist)

            self.range_changed()


class State:
    def __init__(self, view):
        self.view = view
        self._last = None
        self._mode = None
        self._opt = None

    def set(self, mode, arg=None):
        modes = ['drag', 'zoom', 'erase', 'getpars', 'handle', 'xmarker', None]
        if mode not in modes:
            raise TypeError("mode has to be on of 'drag','zoom','erase','getpars','handle','xmarker',None")

        cursors = [self.view.HandCursor,
                   self.view.MagCursor,
                   wx.Cursor(wx.CURSOR_CROSS),
                   wx.Cursor(wx.CURSOR_CROSS),
                   wx.Cursor(wx.CURSOR_CROSS),
                   wx.Cursor(wx.CURSOR_CROSS),
                   ]

        if mode is not None:
            self.view.SetCursor(cursors[modes.index(mode)])
        else:
            self.view.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        try:
            pub.sendMessage((self.view.instid, 'canvas', 'newmode'), mode=mode)
        except AttributeError:
            pass

        self._last = self._mode
        self._mode = mode
        self._opt = arg or None

    @property
    def opt(self):
        return self._opt

    def eq(self, other):
        return self._mode == other

    def restore_last(self):
        self.set(self._last, self._opt)


class PlotCanvas(misc_ui.WithMessage, wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)
        misc_ui.WithMessage.__init__(self)

        self.setup_canvas()
        self.setup_cursors()

        # scrollbar variables
        self._sb_ignore = False
        self._sb_xfullrange = 0
        self._sb_yfullrange = 0
        self._sb_xunit = 0
        self._sb_yunit = 0

        self._screenCoordinates = np.array([0.0, 0.0])

        self._logscale = [False, False]

        self._buffer = None

        # Drawing Variables
        self.last_draw = None
        self._pointScale = 1
        self._pointShift = 0
        self._xSpec = 'auto'
        self._ySpec = 'auto'
        self._gridEnabled = True

        # Fonts
        self._fontCache = {}
        self._fontSizeAxis = 10
        self._fontSizeTitle = 15

        self._gridColour = wx.Colour(0, 0, 0, 20)
        self._canvasBgColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        self._bgColour = wx.Colour(240, 240, 250)

        self._handles = {'fix': np.zeros((0, 2)), 'moving': None}
        self._xmarker = None
        self._corner1 = None
        self._corner2 = None

        self.state = State(self)

        self.canvas.Bind(wx.EVT_PAINT, self.OnPaint)
        self.canvas.Bind(wx.EVT_SIZE, self.OnSize)

        Interactor().install(self)

    def OnPaint(self, evt):
        # log.print('paint')
        dc = wx.BufferedPaintDC(self.canvas)
        dc.DrawBitmap(self._buffer, 0, 0)
        if 'wxMac' not in wx.PlatformInfo:
            dc = wx.GCDC(dc)
        self._draw_overlay(dc)

    def OnSize(self, evt):
        w, h = self.canvas.GetClientSize()
        w = max(1, w)
        h = max(1, h)
        # log.print('on size ({}/{})'.format(w,h))
        self._buffer = wx.Bitmap(w, h)
        self._setSize()
        self.Redraw(True)
        self.Refresh()

        return
        # The Buffer init is done here, to make sure the buffer is always
        # the same size as the Window
        Size = self.view.canvas.GetClientSize()
        if Size.width <= 0 or Size.height <= 0:
            return

        # Make new offscreen bitmap: this bitmap will always have the
        # current drawing in it, so it can be used to save the image to
        # a file, or whatever.
        self.view._Buffer = wx.Bitmap(Size[0], Size[1])

        if self.view.last_draw is None:
            self.view.Clear()
        else:
            graphics, xSpec, ySpec = self.view.last_draw
            self.view._Draw(graphics, xSpec, ySpec)

            # if self.view.state.eq('handle') is not False and len(self.view._handles['fix']) > 0:
            #    self.view._drawHandles()
            # if self.view.state.eq('xmarker') is not False:
            #    self.view._drawXMarker()

    def Redraw(self, full=False):
        success = False
        if full and self.last_draw is not None:
            graphics, xAxis, yAxis = self.last_draw
            success = self.Draw(graphics, xAxis, yAxis)
            dc = wx.BufferedDC(wx.ClientDC(self.canvas))
        else:
            dc = wx.BufferedDC(wx.ClientDC(self.canvas))
            dc.DrawBitmap(self._buffer, 0, 0)

        # log.print('redraw full: {}, succes: {}'.format(full, success))
        if not full or success:
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)
            self._draw_overlay(dc)

    def Clear(self):
        dc = wx.BufferedDC(wx.ClientDC(self.canvas), self._buffer)
        dc.Clear()
        self.last_draw = None

    def Draw(self, graphics, xAxis=None, yAxis=None):
        """Wrapper around _Draw, which handles log axes"""

        graphics.setLogScale(self.getLogScale())

        # check Axis is either tuple or none
        if type(xAxis) not in [type(None), list, tuple, np.ndarray]:
            raise TypeError("xAxis should be None or (minX,maxX) " + str(xAxis))
        if type(yAxis) not in [type(None), list, tuple, np.ndarray]:
            raise TypeError("yAxis should be None or (minY,maxY) " + str(xAxis))

        # check case for axis = (a,b) where a==b caused by improper zooms
        if xAxis is not None:
            if xAxis[0] == xAxis[1]:
                return
            if self.getLogScale()[0]:
                xAxis = np.log10(xAxis)
                if np.any(np.isnan(xAxis)):
                    xAxis = None
        if yAxis is not None:
            if yAxis[0] == yAxis[1]:
                return
            if self.getLogScale()[1]:
                yAxis = np.log10(yAxis)
                if np.any(np.isnan(yAxis)):
                    yAxis = None
        return self._Draw(graphics, xAxis, yAxis)

    def _Draw(self, graphics, xAxis=None, yAxis=None):
        # print(time.time(), '_draw')
        # log.print('draw')
        if self._buffer is not None:
            dc = wx.BufferedDC(wx.ClientDC(self.canvas), self._buffer)
            if 'wxMac' not in wx.PlatformInfo:
                dc = wx.GCDC(dc)

            br = wx.Brush(self._canvasBgColour, wx.SOLID)
            dc.SetBackground(br)
            dc.SetBackgroundMode(wx.SOLID)
            dc.Clear()

            dc.SetBackgroundMode(wx.TRANSPARENT)

            # set font size for every thing but title and legend
            dc.SetFont(self._getFont(self._fontSizeAxis))

            # sizes axis to axis type, create lower left and upper right corners of plot
            if xAxis is None or yAxis is None:
                # One or both axis not specified in Draw
                p1, p2 = graphics.boundingBox()  # min, max points of graphics
                if xAxis is None:
                    xAxis = self._axisInterval(self._xSpec, p1[0], p2[0])  # in user units
                if yAxis is None:
                    yAxis = self._axisInterval(self._ySpec, p1[1], p2[1])
                # Adjust bounding box for axis spec
                p1[0], p1[1] = xAxis[0], yAxis[0]  # lower left corner user scale (xmin,ymin)
                p2[0], p2[1] = xAxis[1], yAxis[1]  # upper right corner user scale (xmax,ymax)
            else:
                # Both axis specified in Draw
                p1 = np.array([xAxis[0], yAxis[0]])  # lower left corner user scale (xmin,ymin)
                p2 = np.array([xAxis[1], yAxis[1]])  # upper right corner user scale (xmax,ymax)

            self.last_draw = (graphics, np.array(xAxis), np.array(yAxis))  # saves most recient values

            # Get ticks and textExtents for axis if required
            if self._xSpec != 'none':
                xticks = self._xticks(xAxis[0], xAxis[1])
                xTextExtent = dc.GetTextExtent(xticks[-1][1])  # w h of x axis text last number on axis
            else:
                xticks = None
                xTextExtent = (0, 0)  # No text for ticks
            if self._ySpec != 'none':
                yticks = self._yticks(yAxis[0], yAxis[1])
                if self.getLogScale()[1]:
                    yTextExtent = dc.GetTextExtent('-2e-2')  # largest text extension
                else:
                    # TODO
                    # unter bestimmten Umstaenden funktioneirt die Skala nicht
                    # print yticks
                    yTextExtentBottom = dc.GetTextExtent(yticks[0][1])
                    yTextExtentTop = dc.GetTextExtent(yticks[-1][1])
                    yTextExtent = (max(yTextExtentBottom[0], yTextExtentTop[0]),
                                   max(yTextExtentBottom[1], yTextExtentTop[1]))
            else:
                yticks = None
                yTextExtent = (0, 0)  # No text for ticks

            # TextExtents for Title and Axis Labels
            titleWH, xLabelWH, yLabelWH = self._titleLablesWH(dc, graphics)

            # room around graph area
            rhsW = xTextExtent[0]
            lhsW = yTextExtent[0] + yLabelWH[1]
            bottomH = max(xTextExtent[1], yTextExtent[1] / 2.) + xLabelWH[1]
            topH = yTextExtent[1] / 2. + titleWH[1]
            # textSize_scale= _Numeric.array([rhsW+lhsW,bottomH+topH]) # make plot area smaller by text size
            # textSize_shift= _Numeric.array([lhsW, bottomH])          # shift plot area by this amount
            textSize_scale = np.array([0, 0])  # make plot area smaller by text size
            textSize_shift = np.array([0, 0])  # shift plot area by this amount

            # drawing title and labels text
            dc.SetFont(self._getFont(self._fontSizeTitle))
            titlePos = (
            int(self.plotbox_origin[0] + lhsW + (self.plotbox_size[0] - lhsW - rhsW) / 2. - titleWH[0] / 2.),
            int(self.plotbox_origin[1] - self.plotbox_size[1]))
            dc.DrawText(graphics.getTitle(), titlePos[0], titlePos[1])
            dc.SetFont(self._getFont(self._fontSizeAxis))
            xLabelPos = (
            int(self.plotbox_origin[0] + lhsW + (self.plotbox_size[0] - lhsW - rhsW) / 2. - xLabelWH[0] / 2.),
            int(self.plotbox_origin[1] - xLabelWH[1]))
            dc.DrawText(graphics.getXLabel(), xLabelPos[0], xLabelPos[1])
            yLabelPos = (int(self.plotbox_origin[0]),
                         int(self.plotbox_origin[1] - bottomH - (self.plotbox_size[1] - bottomH - topH) / 2. + yLabelWH[
                             0] / 2.))
            if graphics.getYLabel():  # bug fix for Linux
                dc.DrawRotatedText(graphics.getYLabel(), yLabelPos[0], yLabelPos[1], 90)

            # allow for scaling and shifting plotted points
            scale = (self.plotbox_size - textSize_scale) / (p2 - p1) * np.array((1, -1))
            shift = -p1 * scale + self.plotbox_origin + textSize_shift * np.array((1, -1))
            self._pointScale = scale  # make available for mouse evts
            self._pointShift = shift
            self._drawAxes(dc, p1, p2, scale, shift, xticks, yticks)

            xoff, yoff = self.plotbox_origin
            width, height = self.plotbox_size
            graphics.scaleAndShift(scale, shift, (p1, p2), [xoff, yoff - bottomH], [width, height - bottomH])

            # set clipping area so drawing does not occur outside axis box
            ptx, pty, rectWidth, rectHeight = self._point2ClientCoord(p1, p2)
            self._clippingRegion = ptx, pty, rectWidth, rectHeight
            dc.SetClippingRegion(ptx, pty, rectWidth, rectHeight)
            # Draw the lines and markers
            # start = _time.clock()
            graphics.draw(dc)
            # print "entire graphics drawing took: %f second"%(_time.clock() - start)
            # remove the clipping region
            dc.DestroyClippingRegion()

            if self.state.eq('handle'):
                dc = wx.BufferedDC(wx.ClientDC(self.canvas))
                if 'wxMac' not in wx.PlatformInfo:
                    dc = wx.GCDC(dc)
                dc.DrawBitmap(self._buffer, 0, 0)
                self._drawHandles(dc)
            if self.state.eq('xmarker'):
                dc = wx.BufferedDC(wx.ClientDC(self.canvas))
                if 'wxMac' not in wx.PlatformInfo:
                    dc = wx.GCDC(dc)
                dc.DrawBitmap(self._buffer, 0, 0)
                self._drawXMarker(dc)

            self._adjustScrollbars()
            return True
        return False

    def _draw_overlay(self, dc):
        self._drawHandles(dc)
        self._drawXMarker(dc)
        self._drawRubberBand(dc)

    def report(self, cmds):
        self.state.set('getpars')
        self._cmds = cmds

    def setup_canvas(self):
        sizer = wx.FlexGridSizer(2, 2, 0, 0)
        self.canvas = wx.Window(self, -1)
        self.canvas.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.sb_vert = wx.ScrollBar(self, -1, style=wx.SB_VERTICAL)
        self.sb_vert.SetScrollbar(0, 1000, 1000, 1000)
        self.sb_hor = wx.ScrollBar(self, -1, style=wx.SB_HORIZONTAL)
        self.sb_hor.SetScrollbar(0, 1000, 1000, 1000)

        sizer.Add(self.canvas, 1, wx.EXPAND)
        sizer.Add(self.sb_vert, 0, wx.EXPAND)
        sizer.Add(self.sb_hor, 0, wx.EXPAND)
        sizer.Add((0, 0))

        sizer.AddGrowableRow(0, 1)
        sizer.AddGrowableCol(0, 1)

        self.sb_vert.Show(True)
        self.sb_hor.Show(True)

        self.SetSizer(sizer)
        self.Fit()

    def setup_cursors(self):
        self.canvas.SetCursor(wx.CROSS_CURSOR)
        # img = getHandImage()
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 8)
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 8)
        self.HandCursor = wx.Cursor(wx.CURSOR_HAND)

        # img = getGrabHandImage()
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 8)
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 8)
        self.GrabHandCursor = wx.Cursor(wx.CURSOR_HAND)

        # img = getMagPlusImage()
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_X, 9)
        # img.SetOptionInt(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, 9)

        self.MagCursor = wx.Cursor(wx.CURSOR_MAGNIFIER)

    def SetCursor(self, cursor):
        self.canvas.SetCursor(cursor)

    def set_handles(self, handles):
        handles = np.asarray(handles)
        if handles.ndim == 1:
            handles = np.vstack((handles, np.zeros(handles.shape))).T
        self._handles['fix'] = handles
        self.Redraw()

    def setLogScale(self, logscale):
        if type(logscale) != list:
            raise TypeError('logscale must be a list of bools, e.g. [False, False]')
        x, y = logscale
        if x is not None:
            self._logscale[0] = x
        if y is not None:
            self._logscale[1] = y

        if self.last_draw is not None:
            graphics, xAxis, yAxis = self.last_draw
            graphics.setLogScale(self._logscale)
            self.last_draw = (graphics, None, None)
        self.SetXSpec('min')
        self.SetYSpec('min')

    def getLogScale(self):
        return list(self._logscale)

    def Reset(self):
        """Unzoom the plot."""
        if self.last_draw is not None:
            self._Draw(self.last_draw[0])

    def ScrollRight(self, units):
        """Move view right number of axis units."""
        if self.last_draw is not None:
            graphics, xAxis, yAxis = self.last_draw
            xAxis = (xAxis[0] + units, xAxis[1] + units)
            self._Draw(graphics, xAxis, yAxis)

    def ScrollUp(self, units):
        """Move view up number of axis units."""
        if self.last_draw is not None:
            graphics, xAxis, yAxis = self.last_draw
            yAxis = (yAxis[0] + units, yAxis[1] + units)
            self._Draw(graphics, xAxis, yAxis)

    def _getXY(self, evt):
        """Takes a mouse evt and returns the XY user axis values."""
        x, y = self.PositionScreenToUser(evt.GetPosition())
        return x, y

    def GetXY(self, event):
        """Wrapper around _getXY, which handles log scales"""
        x, y = self._getXY(event)
        if self.getLogScale()[0]:
            x = np.power(10, x)
        if self.getLogScale()[1]:
            y = np.power(10, y)
        return x, y

    def PositionUserToScreen(self, pntXY):
        """Converts User position to Screen Coordinates"""
        userPos = np.array(pntXY)
        x, y = userPos * self._pointScale + self._pointShift
        return x, y

    def PositionScreenToUser(self, pntXY):
        """Converts Screen position to User Coordinates"""
        screenPos = np.array(pntXY)
        x, y = (screenPos - self._pointShift) / self._pointScale
        return x, y

    def SetXSpec(self, type='auto'):
        """xSpec- defines x axis type. Can be 'none', 'min' or 'auto'
        where:
            'none' - shows no axis or tick mark values
            'min' - shows min bounding box values
            'auto' - rounds axis range to sensible values
        """
        self._xSpec = type

    def SetYSpec(self, type='auto'):
        """ySpec- defines x axis type. Can be 'none', 'min' or 'auto'
        where:
            'none' - shows no axis or tick mark values
            'min' - shows min bounding box values
            'auto' - rounds axis range to sensible values
        """
        self._ySpec = type

    def GetXSpec(self):
        """Returns current XSpec for axis"""
        return self._xSpec

    def GetYSpec(self):
        """Returns current YSpec for axis"""
        return self._ySpec

    def GetXMaxRange(self):
        xAxis = self._getXMaxRange()
        if self.getLogScale()[0]:
            xAxis = np.power(10, xAxis)
        return xAxis

    def _getXMaxRange(self):
        """Returns (minX, maxX) x-axis range for displayed graph"""
        graphics = self.last_draw[0]
        p1, p2 = graphics.boundingBox()  # min, max points of graphics
        xAxis = self._axisInterval(self._xSpec, p1[0], p2[0])  # in user units
        return xAxis

    def GetYMaxRange(self):
        yAxis = self._getYMaxRange()
        if self.getLogScale()[1]:
            yAxis = np.power(10, yAxis)
        return yAxis

    def _getYMaxRange(self):
        """Returns (minY, maxY) y-axis range for displayed graph"""
        graphics = self.last_draw[0]
        p1, p2 = graphics.boundingBox()  # min, max points of graphics
        yAxis = self._axisInterval(self._ySpec, p1[1], p2[1])
        return yAxis

    def GetXCurrentRange(self):
        xAxis = self._getXCurrentRange()
        if self.getLogScale()[0]:
            xAxis = np.power(10, xAxis)
        return xAxis

    def _getXCurrentRange(self):
        """Returns (minX, maxX) x-axis for currently displayed portion of graph"""
        return self.last_draw[1]

    def GetYCurrentRange(self):
        yAxis = self._getYCurrentRange()
        if self.getLogScale()[1]:
            yAxis = np.power(10, yAxis)
        return yAxis

    def _getYCurrentRange(self):
        """Returns (minY, maxY) y-axis for currently displayed portion of graph"""
        return self.last_draw[2]

    def Zoom(self, Mouse, Ratio):
        """ Zoom on the plot
            Zoom center at the mouse coordinates
            Zooms by the Ratio = (Xratio, Yratio) given
        """
        x, y = Mouse

        if self.last_draw != None:
            (graphics, xAxis, yAxis) = self.last_draw

            xr = (x - xAxis[0]) / (xAxis[1] - xAxis[0])
            yr = (y - yAxis[0]) / (yAxis[1] - yAxis[0])

            w = (xAxis[1] - xAxis[0]) * Ratio[0]
            xAxis = (x - w * xr, x + w * (1 - xr))
            h = (yAxis[1] - yAxis[0]) * Ratio[1]
            yAxis = (y - h * yr, y + h * (1 - yr))

            self._Draw(graphics, xAxis, yAxis)

    # Private Methods **************************************************
    def _setSize(self, width=None, height=None):
        """DC width and height."""
        if width == None:
            (self.width, self.height) = self.canvas.GetClientSize()
        else:
            self.width, self.height = width, height
        self.plotbox_size = 1 * np.array([self.width - 1, self.height - 1])
        xo = 0.5 * (self.width - self.plotbox_size[0])
        yo = self.height - 0.5 * (self.height - self.plotbox_size[1])
        self.plotbox_origin = np.array([xo, yo])

    def _titleLablesWH(self, dc, graphics):
        """Draws Title and labels and returns width and height for each"""
        # TextExtents for Title and Axis Labels
        dc.SetFont(self._getFont(self._fontSizeTitle))
        title = graphics.getTitle()
        titleWH = dc.GetTextExtent(title)
        dc.SetFont(self._getFont(self._fontSizeAxis))
        xLabel, yLabel = graphics.getXLabel(), graphics.getYLabel()
        xLabelWH = dc.GetTextExtent(xLabel)
        yLabelWH = dc.GetTextExtent(yLabel)
        return titleWH, xLabelWH, yLabelWH

    def _setXMarker(self, x=None, rng=None):
        if x is not None:
            self._xmarker = x
        elif rng is not None:
            yr = self.GetYCurrentRange()
            self._xmarker = (rng[0], yr[0]), (rng[1], yr[1])

    def _drawXMarker(self, dc):
        if self._xmarker is not None:
            if np.isscalar(self._xmarker):
                self._drawVerticalLine(dc)
            else:
                self._drawHorizontalRange(dc)

    def _setRubberBand(self, ll, ur):
        self._corner1 = ll
        self._corner2 = ur

    def _drawHorizontalRange(self, dc):
        x0, y0 = self.PositionUserToScreen(self._xmarker[0])
        x1, y1 = self.PositionUserToScreen(self._xmarker[1])

        if y1 < y0:
            y0, y1 = y1, y0
        if x1 < x0:
            x0, x1 = x1, x0

        w = x1 - x0
        h = y1 - y0

        color = wx.Colour(0xc0, 0xc0, 0xff)
        dc.SetPen(wx.Pen(color, 1))

        r, g, b = color.Get(False)
        color.Set(r, g, b, 0x60)
        dc.SetBrush(wx.Brush(color))

        dc.DrawRectangle(x0, y0, w, h)

    def _drawVerticalLine(self, dc):
        x, _ = self.PositionUserToScreen((self._xmarker, 1))
        rx, ry, rw, rh = self._clippingRegion
        dc.DrawLine(x, ry, x, ry + rh)

    def _drawRubberBand(self, dc):
        if self._corner1 is not None:
            x0, y0 = self.PositionUserToScreen(self._corner1)
            x1, y1 = self.PositionUserToScreen(self._corner2)

            if y1 < y0:
                y0, y1 = y1, y0
            if x1 < x0:
                x0, x1 = x1, x0

            w = x1 - x0
            h = y1 - y0

            color = wx.Colour(0xc0, 0xc0, 0xff)
            dc.SetPen(wx.Pen(color, 1))

            r, g, b = color.Get(False)
            color.Set(r, g, b, 0x60)
            dc.SetBrush(wx.Brush(color))

            dc.DrawRectangle(x0, y0, w, h)

    def _drawHandles(self, dc):
        if self._handles['fix'].size > 0 or self._handles['moving'] is not None:
            rx, ry, rw, rh = self._clippingRegion

            def _draw(x, y, mode):
                if mode == 'x':
                    dc.DrawLine(x, ry, x, ry + rh)
                elif mode == 'y':
                    dc.DrawLine(rx, y, rx + rw, y)
                elif mode == 'xy':
                    dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 100)))
                    dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 200), 1))
                    dc.DrawCircle(x, y, 6)

            dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 100)))
            dc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 200), 1))
            for x, y in self._handles['fix']:
                screenx, screeny = self.PositionUserToScreen((x, y))
                _draw(screenx, screeny, self.state.opt)

            if self._handles['moving'] is not None:
                x, y = self._handles['moving']
                screenx, screeny = self.PositionUserToScreen((x, y))
                _draw(screenx, screeny, self.state.opt)

    def _outside(self, pt):
        x, y, w, h = self._clippingRegion
        userx, usery = pt
        screenx, screeny = self.PositionUserToScreen((userx, usery))
        return screenx > x + w or screenx < x

    def _close_to_handle(self, pt):
        pt = np.array(pt)
        if len(self._handles['fix']) == 0:
            return False
        handles = self._handles['fix'] * self._pointScale + self._pointShift
        pt = pt * self._pointScale + self._pointShift
        if self.state.opt == 'x':
            dist = abs(pt - handles)[:, 0]
            idx = np.argmin(dist)
            if dist[idx] < 10:
                return idx
            else:
                return False
        elif self.state.opt == 'y':
            dist = abs(pt - handles)[:, 1]
            idx = np.argmin(dist)
            if dist[idx] < 10:
                return idx
            else:
                return False
        else:
            dist = np.sqrt((pt - handles) ** 2).sum(axis=1)
            idx = np.argmin(dist)
            if dist[idx] < 10:
                return idx
            else:
                return False

    def _getFont(self, size):
        """Take font size, adjusts if printing and returns wx.Font"""
        # s = size*self.printerScale
        of = self.GetFont()
        # Linux speed up to get font from cache rather than X font server
        key = (int(size), of.GetFamily(), of.GetStyle(), of.GetWeight())
        font = self._fontCache.get(key, None)
        if font:
            return font  # yeah! cache hit
        else:
            font = wx.Font(int(size), of.GetFamily(), of.GetStyle(), of.GetWeight())
            self._fontCache[key] = font
            return font

    def _point2ClientCoord(self, corner1, corner2):
        """Converts user point coords to client screen int coords x,y,width,height"""
        c1 = np.array(corner1)
        c2 = np.array(corner2)
        # convert to screen coords
        pt1 = (c1 * self._pointScale + self._pointShift).astype(int)
        pt2 = (c2 * self._pointScale + self._pointShift).astype(int)
        # make height and width positive
        pul = np.minimum(pt1, pt2)  # Upper left corner
        plr = np.maximum(pt1, pt2)  # Lower right corner
        rectWidth, rectHeight = plr - pul
        ptx, pty = pul
        return ptx, pty, rectWidth, rectHeight

    def _axisInterval(self, spec, lower, upper):
        """Returns sensible axis range for given spec"""
        if spec == 'none' or spec == 'min':
            if lower == upper:
                return lower - 0.5, upper + 0.5
            else:
                return lower, upper
        elif spec == 'auto':
            range = upper - lower
            if range == 0.:
                return lower - 0.5, upper + 0.5
            log = np.log10(range)
            power = np.floor(log)
            fraction = log - power
            if fraction <= 0.05:
                power = power - 1
            grid = 10. ** power
            lower = lower - lower % grid
            mod = upper % grid
            if mod != 0:
                upper = upper - mod + grid
            return lower, upper
        elif isinstance(spec, tuple):
            lower, upper = spec
            if lower <= upper:
                return lower, upper
            else:
                return upper, lower
        else:
            raise ValueError(str(spec) + ': illegal axis specification')

    def _drawAxes(self, dc, p1, p2, scale, shift, xticks, yticks):

        x, y, width, height = [int(q + 0.5) for q in self._point2ClientCoord(p1, p2)]
        dc.SetBrush(wx.Brush(self._bgColour))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangle(x, y, width, height)

        # set length of tick marks--long ones make grid
        if self._gridEnabled:
            x, y, width, height = self._point2ClientCoord(p1, p2)
            if self._gridEnabled == 'Horizontal':
                yTickLength = width / 2.0 + 1
                xTickLength = 3
            elif self._gridEnabled == 'Vertical':
                yTickLength = 3
                xTickLength = height / 2.0 + 1
            else:
                yTickLength = width / 2.0 + 1
                xTickLength = height / 2.0 + 1
        else:
            yTickLength = 6
            xTickLength = 6

        dc.SetPen(wx.Pen(self._gridColour, 1))

        if self._xSpec != 'none':
            lower, upper = p1[0], p2[0]
            text = 1
            for y, d in [(p1[1], -xTickLength), (p2[1], xTickLength)]:  # miny, maxy and tick lengths
                a1 = (scale * np.array([lower, y]) + shift).astype(int)
                a2 = (scale * np.array([upper, y]) + shift).astype(int)
                dc.DrawLine(a1[0], a1[1], a2[0], a2[1])  # draws upper and lower axis line
                for x, label in xticks:
                    pt = (scale * np.array([x, y]) + shift).astype(int)
                    dc.DrawLine(pt[0], pt[1], pt[0], pt[1] + int(d))  # draws tick mark d units
                    if text:
                        dc.DrawText(label, pt[0] - int(dc.GetTextExtent(label)[0] * 0.5),
                                    pt[1] - dc.GetTextExtent(label)[1] - 10)  # find something better than 25
                text = 0  # axis values not drawn on top side

        if self._ySpec != 'none':
            lower, upper = p1[1], p2[1]
            text = 1
            h = dc.GetCharHeight()
            for x, d in [(p1[0], -yTickLength), (p2[0], yTickLength)]:
                a1 = (scale * np.array([x, lower]) + shift).astype(int)
                a2 = (scale * np.array([x, upper]) + shift).astype(int)
                dc.DrawLine(a1[0], a1[1], a2[0], a2[1])
                for y, label in yticks:
                    pt = (scale * np.array([x, y]) + shift).astype(int)
                    dc.DrawLine(pt[0], pt[1], pt[0] - int(d), pt[1])
                    if text:
                        dc.DrawText(label, pt[0] + 10,
                                    pt[1] - int(0.5 * h))
                text = 0  # axis values not drawn on right side

    def _xticks(self, *args):
        if self._logscale[0]:
            return self._logticks(*args)
        else:
            return self._ticks(*args)

    def _yticks(self, *args):
        if self._logscale[1]:
            return self._logticks(*args)
        else:
            return self._ticks(*args)

    def _logticks(self, lower, upper):
        ticks = []
        lower = max(-300, lower)
        upper = min(300, upper)
        mag = np.power(10, np.floor(lower))
        if upper - lower > 6:
            t = np.power(10, np.ceil(lower))
            base = np.power(10, np.floor((upper - lower) / 6))

            def inc(t):
                return t * base - t
        else:
            t = np.ceil(np.power(10, lower) / mag) * mag

            def inc(t):
                return 10 ** int(np.floor(np.log10(t) + 1e-16))
        majortick = int(np.log10(mag + 1e-16))
        while t <= pow(10, upper):
            if majortick != int(np.floor(np.log10(t) + 1e-16)):
                majortick = int(np.floor(np.log10(t) + 1e-16))
                ticklabel = '1e%d' % majortick
            else:
                if upper - lower < 2:
                    minortick = int(t / pow(10, majortick) + .5)
                    ticklabel = '%de%d' % (minortick, majortick)
                else:
                    ticklabel = ''
            ticks.append((np.log10(t), ticklabel))
            t += inc(t)
        if len(ticks) == 0:
            ticks = [(0, '')]
        return ticks

    def _ticks(self, lower, upper):
        ideal = (upper - lower) / 7.
        log = np.log10(ideal)
        power = np.floor(log)
        fraction = log - power
        factor = 1.
        error = fraction
        for f, lf in self._multiples:
            e = np.fabs(fraction - lf)
            if e < error:
                error = e
                factor = f
        grid = factor * 10. ** power
        if power > 4 or power < -4:
            format = '%+7.1e'
        elif power >= 0:
            digits = max(1, int(power))
            format = '%' + repr(digits) + '.0f'
        else:
            digits = -int(power)
            format = '%' + repr(digits + 2) + '.' + repr(digits) + 'f'
        ticks = []
        t = -grid * np.floor(-lower / grid)
        while t <= upper:
            ticks.append((t, format % (t,)))
            t = t + grid
        if len(ticks) == 0:
            return [(lower, format % (lower,))]
        else:
            return ticks

    _multiples = [(2., np.log10(2.)), (5., np.log10(5.))]

    def _adjustScrollbars(self):
        if self._sb_ignore:
            self._sb_ignore = False
            return

        self._adjustingSB = True
        needScrollbars = False

        # horizontal scrollbar
        r_current = self._getXCurrentRange()
        r_max = list(self._getXMaxRange())
        sbfullrange = int(self.sb_hor.GetRange())

        r_max[0] = min(r_max[0], r_current[0])
        r_max[1] = max(r_max[1], r_current[1])

        self._sb_xfullrange = r_max

        unit = (r_max[1] - r_max[0]) / float(self.sb_hor.GetRange())
        pos = int((r_current[0] - r_max[0]) / unit)

        if pos >= 0:
            pagesize = int((r_current[1] - r_current[0]) / unit)

            self.sb_hor.SetScrollbar(pos, pagesize, sbfullrange, pagesize)
            self._sb_xunit = unit
            needScrollbars = needScrollbars or (pagesize != sbfullrange)
        else:
            self.sb_hor.SetScrollbar(0, 1000, 1000, 1000)

        # vertical scrollbar
        r_current = self._getYCurrentRange()
        r_max = list(self._getYMaxRange())
        sbfullrange = int(self.sb_vert.GetRange())

        r_max[0] = min(r_max[0], r_current[0])
        r_max[1] = max(r_max[1], r_current[1])

        self._sb_yfullrange = r_max

        unit = (r_max[1] - r_max[0]) / sbfullrange
        pos = int((r_current[0] - r_max[0]) / unit)

        if pos >= 0:
            pagesize = int((r_current[1] - r_current[0]) / unit)
            pos = int((sbfullrange - 1 - pos - pagesize))
            self.sb_vert.SetScrollbar(pos, pagesize, sbfullrange, pagesize)
            self._sb_yunit = unit
            needScrollbars = needScrollbars or (pagesize != sbfullrange)
        else:
            self.sb_vert.SetScrollbar(0, 1000, 1000, 1000)

        # self.SetShowScrollbars(needScrollbars)
        self._adjustingSB = False


def write_clipboard(text):
    if wx.TheClipboard.Open():
        do = wx.TextDataObject()
        do.SetText(text)
        wx.TheClipboard.SetData(do)
        wx.TheClipboard.Close()


# ----------------------------------------------------------------------
from wx import ImageFromStream, BitmapFromImage
import io, zlib


def getMagPlusData():
    return zlib.decompress(
        'x\xda\x01*\x01\xd5\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\
\x00\x00\x00\x18\x08\x06\x00\x00\x00\xe0w=\xf8\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x00\xe1IDATx\x9c\xb5U\xd1\x0e\xc4 \x08\xa3n\xff\
\xff\xc5\xdb\xb8\xa7\xee<\x04\x86gFb\xb2\x88\xb6\x14\x90\x01m\x937m\x8f\x1c\
\xd7yh\xe4k\xdb\x8e*\x01<\x05\x04\x07F\x1cU\x9d"\x19\x14\\\xe7\xa1\x1e\xf07"\
\x90H+$?\x04\x16\x9c\xd1z\x04\x00J$m\x06\xdc\xee\x03Hku\x13\xd8C\x16\x84+"O\
\x1b\xa2\x07\xca"\xb7\xc6sY\xbdD\x926\xf5.\xce\x06!\xd2)x\xcb^\'\x08S\xe4\
\xe5x&5\xb4[A\xb5h\xb4j=\x9a\xc8\xf8\xecm\xd4\\\x9e\xdf\xbb?\x10\xf0P\x06\
\x12\xed?=\xb6a\xd8=\xcd\xa2\xc8T\xd5U2t\x11\x95d\xa3"\x9aQ\x9e\x12\xb7M\x19\
I\x9f\xff\x1e\xd8\xa63#q\xff\x07U\x8b\xd2\xd9\xa7k\xe9\xa1U\x94,\xbf\xe4\x88\
\xe4\xf6\xaf\x12x$}\x8a\xc2Q\xf1\'\x89\xf2\x9b\xfbKE\xae\xd8\x07+\xd2\xa7c\
\xdf\x0e\xc3D\x00\x00\x00\x00IEND\xaeB`\x82\xe2ovy')


def getMagPlusBitmap():
    return BitmapFromImage(getMagPlusImage())


def getMagPlusImage():
    stream = io.StringIO(getMagPlusData())
    return ImageFromStream(stream)


# ----------------------------------------------------------------------
def getGrabHandData():
    return zlib.decompress(
        'x\xda\x01Z\x01\xa5\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\
\x00\x00\x00\x18\x08\x06\x00\x00\x00\xe0w=\xf8\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x01\x11IDATx\x9c\xb5U\xd1\x12\x830\x08Kh\xff\xff\
\x8b7\xb3\x97\xd1C\xa4Zw\x93;\x1fJ1\t\x98VJ\x92\xb5N<\x14\x04 I\x00\x80H\xb4\
\xbd_\x8a9_{\\\x89\xf2z\x02\x18/J\x82\xb5\xce\xed\xfd\x12\xc9\x91\x03\x00_\
\xc7\xda\x8al\x00{\xfdW\xfex\xf2zeO\x92h\xed\x80\x05@\xa45D\xc5\xb3\x98u\x12\
\xf7\xab.\xa9\xd0k\x1eK\x95\xbb\x1a]&0\x92\xf0\'\xc6]gI\xda\tsr\xab\x8aI\x1e\
\\\xe3\xa4\x0e\xb4*`7"\x07\x8f\xaa"x\x05\xe0\xdfo6B\xf3\x17\xe3\x98r\xf1\xaf\
\x07\xd1Z\'%\x95\x0erW\xac\x8c\xe3\xe0\xfd\xd8AN\xae\xb8\xa3R\x9as>\x11\x8bl\
yD\xab\x1f\xf3\xec\x1cY\x06\x89$\xbf\x80\xfb\x14\\dw\x90x\x12\xa3+\xeeD\x16%\
I\xe3\x1c\xb8\xc7c\'\xd5Y8S\x9f\xc3Zg\xcf\x89\xe8\xaao\'\xbbk{U\xfd\xc0\xacX\
\xab\xbb\xe8\xae\xfa)AEr\x15g\x86(\t\xfe\x19\xa4\xb5\xe9f\xfem\xde\xdd\xbf$\
\xf8G<>\xa2\xc7\t>\tE\xfc\x8a\xf6\x8dqc\x00\x00\x00\x00IEND\xaeB`\x82\xdb\
\xd0\x8f\n')


def getGrabHandBitmap():
    return BitmapFromImage(getGrabHandImage())


def getGrabHandImage():
    stream = io.StringIO(getGrabHandData())
    return ImageFromStream(stream)


# ----------------------------------------------------------------------
def getHandData():
    return zlib.decompress(
        'x\xda\x01Y\x01\xa6\xfe\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x18\
\x00\x00\x00\x18\x08\x06\x00\x00\x00\xe0w=\xf8\x00\x00\x00\x04sBIT\x08\x08\
\x08\x08|\x08d\x88\x00\x00\x01\x10IDATx\x9c\xad\x96\xe1\x02\xc2 \x08\x849\
\xf5\xfd\x9fx\xdb\xf5\'\x8c!\xa8\xab\xee\x975\xe5\x83\x0b\\@\xa9\xb2\xab\xeb\
<\xa8\xebR\x1bv\xce\xb4\'\xc1\x81OL\x92\xdc\x81\x0c\x00\x1b\x88\xa4\x94\xda\
\xe0\x83\x8b\x88\x00\x10\x92\xcb\x8a\xca,K\x1fT\xa1\x1e\x04\xe0f_\n\x88\x02\
\xf1:\xc3\x83>\x81\x0c\x92\x02v\xe5+\xba\xce\x83\xb7f\xb8\xd1\x9c\x8fz8\xb2*\
\x93\xb7l\xa8\xe0\x9b\xa06\xb8]_\xe7\xc1\x01\x10U\xe1m\x98\xc9\xefm"ck\xea\
\x1a\x80\xa0Th\xb9\xfd\x877{V*Qk\xda,\xb4\x8b\xf4;[\xa1\xcf6\xaa4\x9cd\x85X\
\xb0\r\\j\x83\x9dd\x92\xc3 \xf6\xbd\xab\x0c2\x05\xc0p\x9a\xa7]\xf4\x14\x18]3\
7\x80}h?\xff\xa2\xa2\xe5e\x90\xact\xaf\xe8B\x14y[4\x83|\x13\xdc\x9e\xeb\x16e\
\x90\xa7\xf2I\rw\x91\x87d\xd7p\x96\xbd\xd70\x07\xda\xe3v\x9a\xf5\xc5\xb2\xb2\
+\xb24\xbc\xaew\xedZe\x9f\x02"\xc8J\xdb\x83\xf6oa\xf5\xb7\xa5\xbf8\x12\xffW\
\xcf_\xbd;\xe4\x8c\x03\x10\xdb^\x00\x00\x00\x00IEND\xaeB`\x82\xd1>\x97B')


def getHandBitmap():
    return BitmapFromImage(getHandImage())


def getHandImage():
    stream = io.StringIO(getHandData())
    return ImageFromStream(stream)


def test_plot():
    app = wx.App()
    f = wx.Frame(None)
    c = PlotCanvas(f)
    c.OnSize(None)
    data = np.array([[1, 2], [1.5, 10.0], [2, 2.5], [3, 1.7]])
    s = Spikes(data)
    g = PlotGraphics([s], 'Spikes', 'wave', 'int')

    x = np.linspace(0, 60, 50000)
    y = np.sin(x)
    p = PolyLine([x, y])
    g = PlotGraphics([p])

    c.Draw(g)
    c.state.set('drag')
    # c.setLogScale([True, True])
    f.Show()
    app.MainLoop()


if __name__ == '__main__':
    test_plot()
