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

def new_controller(path=None, silent=True, startapp=False):
    print('new controller')
    if startapp:
        app = wx.App()
        app.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
    from .controller import Controller, PLOTSERVER
    from .interactor import Interactor
    from .project import Project
    from .mainframe import MainFrame

    v = MainFrame(silent, plotserver=PLOTSERVER)
    c = Controller(Project(),v,Interactor('ID'+str(id(v))),path)

    c.view.start(startapp=startapp)

def open_project(path):
    #if self.project_modified:
    #    if not self.view.confirm_open_project_dialog():
    #        return

    if path is not None:
        msg = self.project.load(path, datastore=self.datagrid)

        if msg is not None:
            if msg.type == 'warn':
                wx.CallAfter(self.view.msg_dialog, '\n'.join([str(q) for q in msg]))
            else:
                wx.CallAfter(self.view.error_dialog, '\n'.join([str(q) for q in msg]))
                return

        self.view.title = self.project.name
        self.view.annotations = self.project.annotations

        self.codeeditor.data = self.project.code

        self.view.tree.build(self.project)
        if self.project.path is not None:
            #print 'added to history',self.project.path
            self.view.filehistory.AddFileToHistory(os.path.abspath(path))
            self.save_filehistory()
        self.project_modified = False
        wx.CallAfter(pub.sendMessage, (self.view.id, 'figurelist','needsupdate'))
        misc.set_cwd(path)


pub.subscribe(new_controller, ('new'))

if __name__ == '__main__':
    run()

