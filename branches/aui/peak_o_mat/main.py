import sys
import os
import argparse

from pubsub import pub
import wx

import numpy as np

np.seterr(all='print', under='ignore')
np.set_printoptions(precision=8)

class LoggerWriter:
    def __init__(self, logfct):
        self.logfct = logfct
        self.buf = []

    def write(self, msg):
        if msg.endswith('\n'):
            self.buf.append(msg.rstrip('\n'))
            self.logfct(''.join(self.buf))
            self.buf = []
        else:
            self.buf.append(msg)

    def flush(self):
        pass

import logging
logging.getLogger().handlers = []

#
# # create logger
logger = logging.getLogger('pom')
logger.handlers = []
logger.setLevel(logging.DEBUG)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logfile = logging.FileHandler(filename='peak-o-mat.log')
logfile.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(name)s.%(levelname)s:%(filename)s:%(lineno)d - %(message)s')

console.setFormatter(formatter)
logfile.setFormatter(formatter)
logger.addHandler(console)
logger.addHandler(logfile)

sys.stdout = LoggerWriter(logger.info)
sys.stderr = LoggerWriter(logger.error)

from .appdata import configdir

if not getattr(__builtins__, "WindowsError", None):
    class WindowsError(OSError): pass


def run():
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--silent', dest='silent', action='store_true',
                        help='suppress splash screen on startup')
    parser.add_argument('lpjfile', metavar='peak-o-mat project file', nargs='?', default=None)
    args = parser.parse_args()

    lpj_path = args.lpjfile
    silent = args.silent

    if not os.path.exists(configdir()):
        try:
            os.mkdir(configdir())
        except (IOError, WindowsError):
            logger.warning('unable to create config folder \'%s\'' % configdir())

    if sys.platform == 'win32' and not hasattr(sys, 'frozen'):
        from .winregistry import check, register
        if not check():
            try:
                register()
            except:
                logger.warning('Unable to register .lpj extension. Rerun peak-o-mat as admin.')

    logger.debug('program start')
    new_controller(lpj_path, silent, startapp=True)


import wx.lib.mixins.inspection as wit

class MyApp(wx.App, wit.InspectionMixin):
    def OnInit(self):
        self.Init()  # initialize the inspection tool
        return True

def new_controller(path=None, silent=True, startapp=False):
    logger.debug('new controller %s %s %s', path, silent, startapp)
    if startapp:
        app = MyApp()
        app.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
    from .controller import Controller
    from .interactor import Interactor
    from .project import Project
    from .mainframe import MainFrame

    v = MainFrame(silent)
    c = Controller(Project(), v, Interactor(), path)

    logger.debug('starting view')
    c.view.start(startapp=startapp)

pub.subscribe(new_controller, ('new'))

if __name__ == '__main__':
    run()
