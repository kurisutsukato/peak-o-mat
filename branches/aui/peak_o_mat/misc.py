import wx
from wx import xrc
import sys
import traceback

import os
import re

import numpy as N


xres_loaded = False
frozen_base = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))  
source_base = os.path.split(os.path.dirname(__file__))[0]

def xrc_resource():
    global xres_loaded
    if not xres_loaded:
        if hasattr(sys,"frozen") and sys.frozen == "windows_exe":
            xrcpath = os.path.join(frozen_base, 'xrc', 'peak-o-mat.xrc')
        else:
            xrcpath = os.path.join(source_base, 'peak-o-mat.xrc')
        res = xrc.XmlResource(xrcpath)
        assert res is not None
        xrc.XmlResource.Set(res)
        xres_loaded = True
    return res

class xrcctrl(object):
    def __getitem__(self, item):
        return self.FindWindowByName(item)

def get_bmp(image):
    if hasattr(sys, 'frozen'):
        imgpath = os.path.join(frozen_base, 'images', image)
    else:
        imgpath = os.path.join(source_base,'images',image)
    bmp = wx.Bitmap(imgpath)
    assert bmp is not None
    return bmp

_cwd = None
def cwd():
    global _cwd
    if _cwd is not None:
        while True:
            if os.path.exists(_cwd):
                return _cwd
            _cwd = os.path.split(_cwd)[0]
    try:
        path = os.getcwd()
    except:
        path = os.path.expanduser('~')
    return path

def set_cwd(cwd):
    global _cwd
    _cwd = os.path.split(os.path.abspath(cwd))[0]
    
def parse_operation(op):
    yreg = re.compile(r'(^|.*[^a-z]+)y([^a-z]+.*|$)',re.I)
    xreg = re.compile(r'(^|.*[^a-z]+)x([^a-z]+.*|$)',re.I)

    if re.search(r'.*col(\d+).*', op) is not None:
        op = re.sub(r'col(\d+)',r"(data[:,\1])[:,newaxis]",op)
    if re.search(r'row(\d+)', op) is not None:
        op = re.sub(r'row(\d+)',r"(data[\1])[newaxis,:]",op)

    if yreg.search(op) is not None:
        tmp = ''
        while tmp != op:
            tmp = op
            op = yreg.sub(r'\1arange(rows)[:,newaxis]\2',op)
    if xreg.search(op) is not None:
        tmp = ''
        while tmp != op:
            tmp = op
            op = xreg.sub(r'\1arange(cols)[newaxis,:]\2',op)
    return op

def str2array(arg):
    for sep in ['\t',' ',None]:
        try:
            data = [[locale.atof((lambda x: ['0',x][x.strip()!=''])(x)) for x in line.split(sep)] for line in arg.strip().split('\n')]
        except:
            #tp, msg, tb = sys.exc_info()
            #print tp,msg
            #traceback.print_tb(tb)
            continue
        try:
            data = N.atleast_2d(N.array(data))
            return data
        except ValueError:
            maxlen = max([len(q) for q in data])
            for r in data:
                r.extend([0]*(maxlen-len(r)))
            print data
            data = N.atleast_2d(N.array(data))
            return data
    return None

def format(arg):
    return re.sub(r'(?<!\n)\n(?!\n)',' ',arg)

from wx.lib import newevent

ResultEvent, EVT_RESULT = newevent.NewCommandEvent()
HandlesChangedEvent, EVT_HANDLES_CHANGED = newevent.NewCommandEvent()
ShoutEvent, EVT_SHOUT = newevent.NewCommandEvent()
ParEvent, EVT_GOTPARS = newevent.NewCommandEvent()
RangeEvent, EVT_RANGE = newevent.NewCommandEvent()

ShoutEvent.forever = False

GOTPARS_MOVE = 1
GOTPARS_DOWN = 2
GOTPARS_EDIT = 3
GOTPARS_END = 4

from threading import Thread

class WorkerThread(Thread):
    threadnum = 0
    def __init__(self, notify, fitter):
        Thread.__init__(self)
        self._notify = notify
        self._fitter = fitter
        WorkerThread.threadnum += 1
        
    def run(self):
        msg = self._fitter.run()
        event = ResultEvent(self._notify.GetId(), result=msg)
        wx.PostEvent(self._notify, event)

class PomError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
    
