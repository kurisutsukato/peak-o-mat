import sys
import os
import argparse
#import inspect

#os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

from pubsub import pub
import wx

import numpy as np
np.seterr(all='print',under='ignore')
np.set_printoptions(precision=8)

sys.stderr = sys.stdout

from .appdata import configdir

if not getattr(__builtins__, "WindowsError", None):
    class WindowsError(OSError): pass

def run():
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--silent', dest='silent', action='store_true',
                       help='suppress splash screen on startup')
    parser.add_argument('lpjfile', metavar='peak-o-mat project file', nargs='?',default=None)
    args = parser.parse_args()

    lpj_path = args.lpjfile
    silent = args.silent

    if not os.path.exists(configdir()):
        try:
            os.mkdir(configdir())
        except (IOError, WindowsError):
            print('unable to create config folder \'%s\''%configdir())
            
    if sys.platform == 'win32' and not hasattr(sys, 'frozen'):
        from .winregistry import check, register
        if not check():
            try:
                register()
            except:
                print('Unable to register .lpj extension. Rerun peak-o-mat as admin.')

    new_controller(lpj_path, silent, startapp=True)


import wx.lib.mixins.inspection as wit

class MyApp(wx.App, wit.InspectionMixin):
    def OnInit(self):
        self.Init()  # initialize the inspection tool
        return True

def new_controller(path=None, silent=True, startapp=False):
    print('new controller', path, silent, startapp)
    if startapp:

        app = MyApp()
        #app = wx.App()
        app.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
    from .controller import Controller
    from .interactor import Interactor
    from .project import Project
    from .mainframe import MainFrame

    v = MainFrame(silent)
    c = Controller(Project(),v,Interactor(),path)

    c.view.start(startapp=startapp)

pub.subscribe(new_controller, ('new'))

if __name__ == '__main__':
    run()

