
import os

from glob import glob
import sys
import cStringIO

from peak_o_mat import __version__

def configuration():

    configdict = { 'name' : 'peak-o-mat',
                   'cmdclass' : {"py2exe": build_installer},
                   'version':'%s'%(__version__),
                   'license':'GPL',
                   'author':'Christian Kristukat',
                   'author_email':'ckkart@hoc.net',
                   'url':'http://lorentz.sourceforge.net',
                   'description':'peak-o-mat is a curve fitting program written in python',
                   'scripts':['peak-o-mat.py'],
                   'packages':['peak_o_mat','peak_o_mat.modules','peak_o_mat.datagrid'],
                   'package_data':{'peak_o_mat.modules':[os.path.basename(x) for x in glob('peak_o_mat/modules/*.xrc')],},
                   'data_files':[('xrc',glob('peak_o_mat/modules/*.xrc')+['peak-o-mat.xrc']),
                                 ('',['peak-o-mat.ico','peak-o-mat.png','DOCUMENTATION','COPYING']),
                                 ('examples',glob('data/*.dat')+['example.lpj']),
                                 ('Microsoft.VC90.CRT',glob(r'c:\ms_runtime\*.*')),
                                 ('images',glob('images/*.png')),],
                   }
      
    excludes = ['Tkconstants', 'Tkinter', '_gtkagg', '_tkagg', 'bsddb',
                'curses', 'email', 'pywin.debugger', 'pywin.debugger.dbgcon',
                'pywin.dialogs', 'tcl']
    dll_excludes = ['msvcp90.dll','libgdk-win32-2.0-0.dll', 'libgobject-2.0-0.dll', 'tcl84.dll','tk84.dll']

    configdict['options'] = {"py2exe": {"compressed": 0,
                                        "optimize": 0,
                                        "excludes": excludes,
                                        "dll_excludes": dll_excludes,
                                        "bundle_files": 2,
                                        "dist_dir": "dist",
                                        'packages':['wx.lib.pubsub'],
                                        }}
    pom = {'name' : 'peak-o-mat',
           'script' : 'peak-o-mat.py',
           'icon_resources' : [(1,'peak-o-mat.ico')]
           }
    configdict['windows'] = [pom]
    configdict['zipfile' ] = r"peak-o-mat.lib"

    return configdict

from py2exe.build_exe import py2exe

class build_installer(py2exe):
    # This class first builds the exe file(s), then creates a Windows installer.
    # You need InnoSetup for it.
    def run(self):
        # First, let py2exe do it's work.
        py2exe.run(self)

        lib_dir = self.lib_dir
        dist_dir = self.dist_dir

        # create the Installer, using the files py2exe has created.
        script = InnoScript("peak-o-mat", lib_dir, dist_dir, self.windows_exe_files,
                            self.lib_files, version = __version__)
        print "*** creating the inno setup script***"
        script.create()
        print "*** compiling the inno setup script***"
        #script.compile()
        # Note: By default the final setup.exe will be in an Output subdirectory.

class InnoScript:
    def __init__(self, name, lib_dir, dist_dir, windows_exe_files = [], lib_files = [], version = "1.0"):
        self.lib_dir = lib_dir
        self.dist_dir = dist_dir
        if not self.dist_dir[-1] in "\\/":
            self.dist_dir += "\\"
        self.name = name
        self.version = version
        self.windows_exe_files = [self.chop(p) for p in windows_exe_files]
        self.lib_files = [self.chop(p) for p in lib_files]

    def chop(self, pathname):
        assert pathname.startswith(self.dist_dir)
        return pathname[len(self.dist_dir):]

    def create(self, pathname=r"dist\peak-o-mat.iss"):
        self.pathname = pathname
        ofi = self.file = open(pathname, "w")
        print >> ofi, "; WARNING: This script has been created by py2exe. Changes to this script"
        print >> ofi, "; will be overwritten the next time py2exe is run!"
        print >> ofi, r"[Setup]"
        print >> ofi, r"AppName=%s" % self.name
        print >> ofi, r"AppVerName=%s %s" % (self.name, self.version)
        print >> ofi, r"DefaultDirName={pf}\%s" % self.name
        print >> ofi, r"DefaultGroupName=%s" % self.name
        #print >> ofi, r"Compression=lzma"
        #print >> ofi, r"SolidCompression=yes"
        print >> ofi, r"OutputBaseFilename=%s-standalone-%s"%(self.name, self.version)
        print >> ofi

        print >> ofi, r"[Files]"
        for path in self.windows_exe_files + self.lib_files:
            print >> ofi, r'Source: "%s"; DestDir: "{app}\%s"; Flags: ignoreversion' % (path, os.path.dirname(path))
        print >> ofi

        print >> ofi, r"[Icons]"
        for path in self.windows_exe_files:
            print >> ofi, r'Name: "{group}\%s"; Filename: "{app}\%s"; IconFilename: "{app}\peak-o-mat.ico"' % \
                  (self.name, path)
        print >> ofi, 'Name: "{group}\Uninstall %s"; Filename: "{uninstallexe}"' % self.name
        print >> ofi

        print >> ofi, r'[Registry]'
        print >> ofi, r'Root: HKCR; Subkey: ".lpj"; ValueType: string; ValueData: "%s"' % self.name
        print >> ofi, r'Root: HKCR; Subkey: "%s\DefaultIcon"; ValueType: string; ValueData: "{app}\%s.ico"' % (self.name,self.name)
        print >> ofi, r'Root: HKCR; Subkey: "%s\shell\open\command"; ValueType: string; ValueData: "{app}\%s.exe ""%%1"" "' % (self.name,self.name)

    def compile(self):
        import ctypes

        res = ctypes.windll.shell32.ShellExecuteA(0, "compile",
                                                  self.pathname,
                                                  None,
                                                  None,
                                                  0)
        if res < 32:
            raise RuntimeError, "ShellExecute failed, error %d" % res

if __name__ == "__main__":
    from distutils.core import setup
    
    data = configuration()
    setup(**data)
    

        
