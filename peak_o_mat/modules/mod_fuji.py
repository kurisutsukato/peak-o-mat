#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib2
import httplib
import sys
import os
import re
import tempfile
import threading

import wx

from peak_o_mat import module, misc

class Getter(threading.Thread):
    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window
        self.timeToQuit = threading.Event()
        self.timeToQuit.clear()

    def stop(self):
        self.timeToQuit.set()

    def run(self):
        url = 'http://www.fujigoko.tv/livecam13/cam.jpg'

        head,client = 'User-Agent','Mozilla/5.001 (windows; U; NT4.0; en-us) Gecko/25250101'

        req = urllib2.Request(url)
        req.add_header(head,client)
        opener = urllib2.build_opener()
        try:
            data = opener.open(req).read()
        except:
            return
        
        tmp,name = tempfile.mkstemp()
        os.write(tmp,data)
        os.close(tmp)
        
        #self.bmp = wx.Bitmap(name)
        #os.unlink(name)
        wx.CallAfter(self.window.read_bmp, name)
        
class Module(module.Module):
    title = u'\u5bcc\u58eb\u5c71'
    
    def __init__(self, *args):
        module.Module.__init__(self, __file__, *args)
        self._buffer = None
        self.bmp = None
        self.maximg = 0
        
    def init(self):
        thread = Getter(self)
        thread.start()

        self.panel.Bind(wx.EVT_PAINT, self.OnPaint)
        self.panel.Bind(wx.EVT_SIZE, self.OnSize)

        self.timer = wx.Timer()
        self.timer.Start(10*60*1000) # wake up every 10 minutes

        self.timer.Bind(wx.EVT_TIMER, self.OnTimer)
        
        self.OnSize(None)
        
    def OnSize(self, event):
        self.width, self.height = self.panel.GetClientSizeTuple()
        self._buffer = wx.EmptyBitmap(self.width, self.height)
        self.update()
        
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self.panel, self._buffer)

    def OnTimer(self, evt):
        self.message('fetching image...',target=1)
        thread = Getter(self)
        thread.start()

    def update(self, evt=None):
        dc = wx.BufferedDC(wx.ClientDC(self.panel), self._buffer)
        dc.BeginDrawing()
        dc.SetBackground( wx.Brush("White") )
        dc.Clear() # make sure you clear the bitmap!
        if self.bmp is not None:
            dc.DrawBitmap(self.bmp, 0, 2, False)
        dc.EndDrawing()
        
    def read_bmp(self, name):
        bmp = wx.Bitmap(name)
        img = bmp.ConvertToImage()
        img = img.GetSubImage(wx.Rect(0,82,799,180))
        w,h = [float(x) for x in [img.GetWidth(),img.GetHeight()]]
        asp = w/h
        self.imgh = self.height-4
        self.imgw = self.imgh*asp
        img = img.Scale(self.imgw,self.imgh)

        self.bmp =img.ConvertToBitmap()
        
        os.unlink(name)
        self.update()
        
        
