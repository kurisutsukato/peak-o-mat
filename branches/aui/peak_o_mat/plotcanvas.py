#!/usr/bin/python


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

import wx
import numpy as N

from wx.lib.pubsub import pub as Publisher

# dos not work with wx.lib.plot currently 
from plot import PlotGraphics,PlotCanvas,PolyMarker,PolyLine,PolyPoints
import misc
import peaks

class Points(PolyPoints):
    skipbb = False
    def __init__(self, skipbb):
        self.skipbb = skipbb
        
    def boundingBox(self):
        if len(self.points) == 0:
            # no curves to draw
            # defaults to (-1,-1) and (1,1) but axis can be set in Draw
            minXY= N.array([-1.0,-1.0])
            maxXY= N.array([ 1.0, 1.0])
        else:
            minXY= N.minimum.reduce(self.points)
            maxXY= N.maximum.reduce(self.points)
            dx,dy = (maxXY-minXY)*0.02
            minXY -= [dx,dy]
            maxXY += [dx,dy]
        return minXY, maxXY

class Line(Points,PolyLine):
    def __init__(self, *args, **kwargs):
        if 'skipbb' in kwargs:
            skipbb = kwargs['skipbb']
            kwargs.pop('skipbb')
            Points.__init__(self, skipbb)
            args = list(args)
            args[0] = N.transpose(args[0])
        PolyLine.__init__(self, *args, **kwargs)

class Marker(Points,PolyMarker):
    def __init__(self, *args, **kwargs):
        if 'skipbb' in kwargs:
            skipbb = kwargs['skipbb']
            kwargs.pop('skipbb')
            Points.__init__(self, skipbb)
            args = list(args)
            args[0] = N.transpose(args[0])
        PolyMarker.__init__(self, *args, **kwargs)

class Graphics(PlotGraphics):
    def __init__(self, *args, **kwargs):
        PlotGraphics.__init__(self,*args,**kwargs)

    def boundingBox(self):
        if len(self.objects) == 0:
            return N.array([-1.0,-1.0]),N.array([1.0,1.0])
        p1, p2 = self.objects[0].boundingBox()
        for o in self.objects[1:]:
            if not o.skipbb:
                p1o, p2o = o.boundingBox()
                p1 = N.minimum(p1, p1o)
                p2 = N.maximum(p2, p2o)
        return p1, p2

class Canvas(PlotCanvas):
    def __init__(self, parent, **kwargs):
        PlotCanvas.__init__(self, parent, **kwargs)

        self.SetShowScrollbars(True)
        
        self._getparsEnabled = False
        self._eraseEnabled = False
        self._xrangeEnabled = False
        self._handleEnabled = False
        self._mousestart = None
        self._mousestop = None
        self._mouseClicked = False

        self._save = None
        self._handles = N.zeros((0,1))
        self._handle_dim = self._handles.shape[1]
        self._moving_handle = False
        
        self._clippingRegion = 0,0,0,0
        self._logscale = [False, False]

        self._cmds = []
        self._info = None
        
        self.lastmode = None

        self.canvas.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)

    def report(self, cmds):
        self.SetMode('getpars')
        self._cmds = cmds

    def OnLeave(self, evt):
        if self._xrangeEnabled and self._mousestart is not None:
            self._drawVerticalLine(self._mousestart)
            self._mousestart = None
        if self._handleEnabled and self._moving_handle:
            self._save = None
            self._moving_handle = False
            self.handles_changed()
            self.Redraw()
            
    def OnMotion(self, evt):
        if self._getparsEnabled and len(self._cmds) > 0:
            cmd, cb = self._cmds[0]
            if 'm' in cmd:
                x,y = self.GetXY(evt)
                arg = {'x':x,'y':y,'xy':(x,y)}[unicode(cmd)]
                cb(arg)
                self.updatePlot(self._info, misc.GOTPARS_MOVE)
        elif self._eraseEnabled and evt.LeftIsDown():
            if self._hasDragged:
                self._drawRubberBand(self._zoomCorner1, self._zoomCorner2) # remove old
            else:
                self._hasDragged = True
            self._zoomCorner2[0], self._zoomCorner2[1] = self._getXY(evt)
            self._drawRubberBand(self._zoomCorner1, self._zoomCorner2) # add new
        elif self._handleEnabled and self._moving_handle:
            pt = self.GetXY(evt)
            if self._handle_dim == 1:
                pt = pt[0]
            if self._save is not None:
                self._drawHandle(self._save)
            is_close = self._close_to_handle(pt)
            if is_close is not False:
                self._save = None
                self.SetCursor(self.HandCursor)
            else:
                self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
                self._drawHandle(pt)
                self._save = pt
        elif self._handleEnabled:
            pt = self.GetXY(evt)
            if self._handle_dim == 1:
                pt = pt[0]
            is_close = self._close_to_handle(pt)
            if is_close is not False:
                self.SetCursor(self.HandCursor)
            else:
                self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

        self.Shout('X: %.5e   Y: %.5e' % self.GetXY(evt))

        PlotCanvas.OnMotion(self, evt)

    def OnMouseLeftUp(self, evt):
        PlotCanvas.OnMouseLeftUp(self, evt)
        if self._eraseEnabled:
            self._mousestop = self.GetXY(evt)
            x1, y1 = self._mousestart
            x2, y2 = self._mousestop
            Publisher.sendMessage(('canvas','erase'),((min(x1,x2),min(y1,y2)),(max(x1,x2),max(y1,y2))))
            self._hasDragged = False
            return
        elif self._zoomEnabled or self._dragEnabled:
            self.range_changed()
        elif self._handleEnabled and self._moving_handle:
            pt = self.GetXY(evt)
            if self._handle_dim == 1:
                pt = pt[0]
            is_close = self._close_to_handle(pt)
            if is_close is False and not self._outside(pt):
                self._handles = N.vstack((self._handles,pt))
            self._save = None
            self._moving_handle = False
            self.handles_changed()

    def OnMouseRightDown(self, evt):
        PlotCanvas.OnMouseRightDown(self, evt)
        if self._zoomEnabled:
            self.range_changed()
        elif self._handleEnabled:
            pt = self.GetXY(evt)
            if self._handle_dim == 1:
                pt = pt[0]
            is_close = self._close_to_handle(pt)
            if is_close is not False:
                indx = range(self._handles.shape[0])
                indx.pop(is_close)
                pt = self._handles[is_close]
                self._drawHandle(pt)
                self._moving_handle = False
                self._handles = N.take(self._handles,indx,0)
                self.handles_changed()
                
    def OnMouseLeftDown(self, evt):
        if self._getparsEnabled and len(self._cmds) > 0:
            cmd, cb = self._cmds[0]
            x,y = self.GetXY(evt)
            arg = {'x':x,'y':y,'xy':(x,y)}[unicode(cmd)]
            cb(arg)
            self._cmds.pop(0)
            self.updatePlot(None, misc.GOTPARS_DOWN)
            if len(self._cmds) == 0:
                self.updatePlot(None, misc.GOTPARS_END)
                self.RestoreLastMode()
        if self._eraseEnabled:
            self._mousestart = self.GetXY(evt)
        elif self._handleEnabled:
            pt = self.GetXY(evt)
            if self._handle_dim == 1:
                pt = pt[0]
            is_close = self._close_to_handle(pt)
            self._save = None
            if is_close is not False:
                indx = range(self._handles.shape[0])
                indx.pop(is_close)
                pt = self._handles[is_close]
                self._drawHandle(pt)
                self._save = None
                self._moving_handle = True
                self._handles = N.take(self._handles,indx,0)
            else:
                self._handles = N.vstack((self._handles,pt))
                self._moving_handle = False
                self._drawHandle(pt)
                self.handles_changed()
        PlotCanvas.OnMouseLeftDown(self, evt)

    def _outside(self, pt):
        x,y,w,h = self._clippingRegion
        if self._handle_dim == 2:
            userx,usery = pt
            screenx, screeny = self.PositionUserToScreen((userx,usery))
            return screenx > x+w or screenx < x or screeny > y+h or screeny < y
        else:
            userx,usery = N.asscalar(pt),0
            screenx, screeny = self.PositionUserToScreen((userx,usery))
            return screenx > x+w or screenx < x

    def _close_to_handle(self, pt):
        pt = N.array(pt)
        if len(self._handles) == 0:
            return False
        if self._handle_dim == 1:
            handles = N.array(self._handles) * self._pointScale[0] + self._pointShift[0]
            pt = pt * self._pointScale[0] + self._pointShift[0]
            dist = abs(pt-handles)
        else:
            handles = self._handles * self._pointScale + self._pointShift
            pt = pt * self._pointScale + self._pointShift
            dist = N.sqrt(N.add.reduce((pt-handles)**2,1))
        idx = N.argmin(dist)
        if dist[idx] < 10:
            return idx
        else:
            return False
        
    def _Draw(self, *args, **kwargs):
        PlotCanvas._Draw(self, *args, **kwargs)
        if self._handleEnabled and self._handles is not None:
            for pt in self._handles:
                self._drawHandle(pt)

    def set_handles(self, handles=None):
        handles = N.asarray(handles)
        if len(handles.shape) == 1:
            if handles.shape[0] == 0:
                handles = N.zeros((0,1),dtype=float)
            else:
                handles = handles.reshape(-1,1)
        self._handles = handles
        self._handle_dim = self._handles.shape[1]
        self.Redraw()

    def Shout(self, msg, target=0):
        evt = misc.ShoutEvent(self.GetId(), msg=msg, target=target)
        wx.PostEvent(self, evt)

    def OnScroll(self, evt):
        PlotCanvas.OnScroll(self, evt)
        self.range_changed()

    def MouseReset(self):
        self._mousestart = None
        self._mousestop = None
        self._mouseClicked = False

    def GetMode(self):
        modes = [self._getparsEnabled, self._eraseEnabled, self.GetEnableZoom(), self.GetEnableDrag(), self._handleEnabled]
        for n,m in enumerate(modes):
            if m:
                return ['getpars','erase','zoom','drag','handle'][n]
        return None
    
    def RestoreLastMode(self):
        self.SetMode(self.lastmode)

    def SetMode(self, mode):
        modes = ['drag','zoom','erase','getpars', 'handle', None]
        if mode not in modes:
            raise TypeError, "mode has to be on of 'drag','zoom','erase','getpars','handle',None"

        cursors = [self.HandCursor,
                   self.MagCursor,
                   wx.StockCursor(wx.CURSOR_CROSS),
                   wx.StockCursor(wx.CURSOR_CROSS),
                   wx.StockCursor(wx.CURSOR_CROSS)
                   ]
        
        self.lastmode = self.GetMode()

        if mode is not None:
            self.SetCursor(cursors[modes.index(mode)])
            enable = modes.pop(modes.index(mode))
            setattr(self,'_%sEnabled'%enable, True)
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        for m in modes[:-1]:
            setattr(self,'_%sEnabled'%m, False)

        self.Redraw()
        Publisher.sendMessage(('canvas','newmode'),mode)
        
    def SetEnableHandle(self, state):
        self._handleEnabled = state
        if state:
            self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            
    def GetEnableHandle(self):
        return self._handleEnabled
            
    def SetEnableErase(self, state):
        self._eraseEnabled = state
        if state:
            self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def GetEnableErase(self):
        return self._eraseEnabled
            
    def SetEnableGetpars(self, state):
        self._getparsEnabled = state
        if state:
            self.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))
        else:
            self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def GetEnableGetpars(self, state):
        return self._getparsEnabled
            
    def startGetPars(self, mod):
        self.SetMode('getpars')

        for el in self.mod:
            if peaks.functions.getProp(el.name)['auto'] is not False:
                self.Shout('place %s'%el.name, 1)
                break
            else:
                self.count += 1

    def updatePlot(self, msg, cmd=None):
        if cmd is not None:
            if not self._getparsEnabled:
                cmd = misc.GOTPARS_END
                self.RestoreLastMode()
            event = misc.ParEvent(self.GetId(), cmd=cmd)
            wx.PostEvent(self, event)
        if msg is not None:
            self.Shout(unicode(msg), 1)

    def handles_changed(self, data='x'):
        if self._handle_dim == 1:
            self._handles.sort(0)
            handles = self._handles.ravel()
        else:
            handles = self._handles
        evt = misc.HandlesChangedEvent(self.GetId(), handles=handles.tolist())
        wx.PostEvent(self, evt)

    def range_changed(self):
        xr = self.GetXCurrentRange()
        yr = self.GetYCurrentRange()
        evt = misc.RangeEvent(self.GetId(), range=(xr,yr))
        wx.PostEvent(self, evt)

    def _drawHandle(self, pt):
        x,y,w,h = self._clippingRegion
        """Draws/erases vertical line at user x-coordinate x"""
        dc = wx.ClientDC( self.canvas )
        dc.BeginDrawing()
        dc.SetClippingRegion(x,y,w,h)
        pen = wx.Pen(wx.BLACK)
        dc.SetPen(pen)
        dc.SetBrush(wx.Brush( wx.WHITE, wx.TRANSPARENT ) )
        dc.SetLogicalFunction(wx.INVERT)
        if self._handle_dim == 2:
            userx,usery = pt
            if self.getLogScale()[0]:
                userx = N.log10(userx)
            if self.getLogScale()[1]:
                usery = N.log10(usery)
            screenx, screeny = self.PositionUserToScreen((userx,usery))
            dc.DrawCircle(screenx,screeny,9)
            dc.DrawLine(screenx-2,screeny,screenx+3,screeny)
            dc.DrawLine(screenx,screeny-2,screenx,screeny+3)
        else:
            userx,usery = N.asscalar(pt),0
            screenx, screeny = self.PositionUserToScreen((userx,usery))
            pen.SetStyle(wx.SHORT_DASH)
            dc.DrawLine(screenx,y,screenx,y+h)
        dc.EndDrawing()

