
from setuptools import setup

import zmq.backend.cython.error

import os
from glob import glob
import sys
import shutil

import matplotlib
import zmq

sys.setrecursionlimit(5000)

from peak_o_mat import __version__
    
manifest = '''
<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<assembly xmlns='urn:schemas-microsoft-com:asm.v1' manifestVersion='1.0'>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level='asInvoker' uiAccess='false' />
      </requestedPrivileges>
    </security>
  </trustInfo>
  <description>peak-o-mat</description>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
     type='win32'
     name='Microsoft.VC90.CRT'
     version='9.0.21022.8'
     processorArchitecture='*'
     publicKeyToken='1fc8b3b9a1e18e3b' />
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
         type="win32"
         name="Microsoft.Windows.Common-Controls"
         version="6.0.0.0"
         processorArchitecture="*"
         publicKeyToken="6595b64144ccf1df"
         language="*" />
    </dependentAssembly>
  </dependency>
</assembly>
'''    
    
def configuration():

    configdict = { 'name' : 'peak-o-mat',
                   'version':'%s'%(__version__),
                   'license':'GPL',
                   'author':'Christian Kristukat',
                   'author_email':'ckkart@hoc.net',
                   'url':'http://lorentz.sourceforge.net',
                   'description':'peak-o-mat - curve fitting software',
                   'packages':['peak_o_mat','peak_o_mat.fio','peak_o_mat.modules','peak_o_mat.datagrid','peak_o_mat.mplplot'],
                   'package_data':{'peak_o_mat.modules':[os.path.basename(x) for x in glob('peak_o_mat/modules/*.xrc')],},
                   'data_files':[('xrc',glob('peak_o_mat/modules/*.xrc')+['peak-o-mat.xrc']),
                                 ('',['peak-o-mat.ico','peak-o-mat.png','COPYING','SVNREVISION','CHANGELOG']),
                                 ('examples',glob('data/*.dat')+['example.lpj']),
                                 ('images',glob('images/*.png'))],

                   }


    excludes = ['Tkconstants', 'Tkinter', '_gtkagg', '_tkagg', 'bsddb',
                'curses', 'email', 'pywin.debugger', 'pywin.debugger.dbgcon',
                'pywin.dialogs', 'tcl', 'jinja2',
                ]
    includes = ['scipy.special._ufuncs_cxx','scipy.sparse.csgraph._validation',
                'scipy.linalg.cython_blas','scipy.linalg.cython_lapack',
                'wx.py.path','cython',
                'zmq.backend.cython','scipy._lib.messagestream'
                ]

    dll_excludes = ['msvcp90.dll','libgdk-win32-2.0-0.dll','user32.dll',
                    'libgobject-2.0-0.dll', 'tcl84.dll','tk84.dll','shell32.dll','advapi32.dll','mpr.dll'
                    ]

    apidlls = '''\
API-MS-Win-Core-LocalRegistry-L1-1-0.dll
API-MS-Win-Core-ProcessThreads-L1-1-0.dll
API-MS-Win-Security-Base-L1-1-0.dll
    '''.strip().split('\n')
    dll_excludes.extend(apidlls)

    if sys.argv[1] != 'sdist':
        if sys.platform == 'win32':
            #if not os.path.exists('Microsoft.VC90.CRT'):
            #    print('Microsoft.VC90.CRT folder not found. aborting.')
            #    sys.exit(0)

            configdict['setup_requires'] = ['py2exe'],
            configdict['cmdclass'] = {"py2exe": build_installer}
            #configdict['data_files'].append(('Microsoft.VC90.CRT',glob(r'Microsoft.VC90.CRT\*.*')))
            configdict['data_files'].append(('',glob(r'C:\Python27\Lib\site-packages\scipy\extra-dll\*.*')))

            mpldata = [p for p in matplotlib.get_py2exe_datafiles() if len(p[1]) > 0]
            configdict['data_files'].extend(mpldata)
            configdict['data_files'].append(('',(zmq.libzmq.__file__,)))
            configdict['data_files'].append(('',(r'C:\Python27\Lib\site-packages\numpy\core\numpy-atlas.dll',)))

            configdict['options'] = {"py2exe": {"compressed": 0,
                                                "optimize": 1,
                                                "excludes": excludes,
                                                'includes': includes,
                                                "dll_excludes": dll_excludes,
                                                "bundle_files": 1,
                                                "dist_dir": "dist",
                                                }}
            pom = {'name' : 'peak-o-mat',
                   'script' : 'peak-o-mat.py',
                   'icon_resources' : [(1,'peak-o-mat.ico')],
                   "other_resources": [(24,1,manifest)]
                   }

            configdict['console'] = [pom]
            configdict['zipfile' ] = "packages.lib"
        elif sys.platform == 'darwin':
            configdict['setup_requires'] = ['py2app'],
            configdict['options'] = dict( py2app = dict(argv_emulation = True,
                                                        packages = ['wx'],
                                                        plist = dict(CFBundleName               = "peak-o-mat",
                                                                     CFBundleIdentifier         = "com.hoc.peak-o-mat"
                                                                     ),
                                                        iconfile = 'images/logo.icns'))

            configdict['app'] = ['peak-o-mat.py']

    return configdict

import py2exe
from distutils.command import py2exe as p2e
if True:
    class build_installer(p2e):
        # This class first builds the exe file(s), then creates a Windows installer.
        # You need InnoSetup for it.
        def run(self):
            # First, let py2exe do it's work.
            py2exe.run(self)

            lib_dir = self.lib_dir
            dist_dir = self.dist_dir

            shutil.copy('SVNREVISION',dist_dir)
            self.lib_files.append(os.path.join(dist_dir,'SVNREVISION'))

            # create the Installer, using the files py2exe has created.
            script = InnoScript("peak-o-mat", lib_dir, dist_dir, self.windows_exe_files, \
                                self.console_exe_files, self.lib_files, version = __version__)
            script.create()
            script.compile()
            # Note: By default the final setup.exe will be in an Output subdirectory.

class InnoScript:
    def __init__(self, name, lib_dir, dist_dir, windows_exe_files = [], console_exe_files = [], lib_files = [], version='999'):
        self.lib_dir = lib_dir
        self.dist_dir = dist_dir
        if not self.dist_dir[-1] in "\\/":
            self.dist_dir += "\\"
        self.name = name
        self.version = version
        self.exe_files = [self.chop(p) for p in windows_exe_files+console_exe_files]
        self.lib_files = [self.chop(p) for p in lib_files]

    def chop(self, pathname):
        #return pathname[len(self.dist_dir):]
        try:
            assert pathname.startswith(self.dist_dir)
        except AssertionError as e:
            print(pathname, self.dist_dir)
            
        return pathname[len(self.dist_dir):]

    def create(self, pathname=r"dist\peak-o-mat.iss"):
        self.pathname = pathname
        ofi = self.file = open(pathname, "w")
        print("; WARNING: This script has been created by py2exe. Changes to this script", file=ofi)
        print("; will be overwritten the next time py2exe is run!", file=ofi)
        print(r"[Setup]", file=ofi)
        print(r"AppName=%s" % self.name, file=ofi)
        print(r"AppVerName=%s %s" % (self.name, self.version), file=ofi)
        print(r"DefaultDirName={pf}\%s" % self.name, file=ofi)
        print(r"DefaultGroupName=%s" % self.name, file=ofi)
        #print >> ofi, r"Compression=lzma"
        #print >> ofi, r"SolidCompression=yes"
        print(r"OutputBaseFilename=%s-%s"%(self.name, self.version), file=ofi)
        print(file=ofi)

        print(r"[Files]", file=ofi)
        for path in self.exe_files + self.lib_files:
            print(r'Source: "%s"; DestDir: "{app}\%s"; Flags: ignoreversion' % (path, os.path.dirname(path)), file=ofi)
        print(file=ofi)

        print(r"[Icons]", file=ofi)
        for path in self.exe_files:
            print(r'Name: "{group}\%s"; Filename: "{app}\%s"; IconFilename: "{app}\peak-o-mat.ico"' % \
                  (self.name, path), file=ofi)
        print('Name: "{group}\\Uninstall %s"; Filename: "{uninstallexe}"' % self.name, file=ofi)
        print(file=ofi)

        print(r'[Registry]', file=ofi)
        print(r'Root: HKCR; Subkey: ".lpj"; ValueType: string; ValueData: "%s"' % self.name, file=ofi)
        print('Root: HKCR; Subkey: "%s\DefaultIcon"; ValueType: string; ValueData: "\'{app}\%s.ico\'"' % (self.name,self.name), file=ofi)
        print('Root: HKCR; Subkey: "%s\shell\open\command"; ValueType: string; ValueData: "\"\"{app}\%s.exe\"\" \"\"%%1\"\""' % (self.name,self.name), file=ofi)

    def compile(self):
        return
        import ctypes
        
        res = ctypes.windll.shell32.ShellExecuteA(0, "compile",
                                                  self.pathname,
                                                  None,
                                                  None,
                                                  0)
        if res < 32:
            print('Wrote .iss file. Start InnoSetup by hand')

class SDist:
    def __init__(self, *args):
        print(args)

if __name__ == "__main__":
    from distutils.core import setup

    if __version__[:2] == '00':
        f = open('SVNREVISION','w')
        f.write('%s\n'%__version__)
        f.close()

    data = configuration()
    if sys.argv[1] == 'sdist':
        data['distclass'] = SDist

    import os, zmq
    os.environ["PATH"] = \
    os.environ["PATH"] + \
    os.path.pathsep + os.path.split(zmq.__file__)[0]
    setup(**data)
    

        
