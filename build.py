tmpl = '''\
# -*- mode: python -*-

block_cipher = None

a = Analysis(['peak-o-mat.py'],
             pathex=[r'{path}'],
             binaries=[],
             datas=[('peak_o_mat/modules/*.xrc','peak_o_mat/modules'),
             ('peak-o-mat.xrc','.'),
             ('peak-o-mat.ico','.'),
             ('images/*.png','images'),
             ('data/*','data'),
             ('example.lpj', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter',
             'psutil','jedi','share','IPython','tcl','tornado','pandas','django'
             'notebook','nbconvert','jupyter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='peak-o-mat2-{version}',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon = 'peak-o-mat.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='peak-o-mat2')
'''

from os.path import join, abspath, normpath
import os
import sys
import shutil
import ctypes
from peak_o_mat import version

if len(sys.argv) > 1:
    if sys.argv[1] != '--tag':
        print('only allowed argument: --tag')
        sys.exit()
    else:
        __version__ = version.VERSION
    SVN = False
else:
    SVN = True
    __version__ = version.__version__

out = join('dist','peak-o-mat2-{}'.format(__version__))
diss = abspath(join(out,'peak-o-mat2-{}.iss'.format(__version__)))

def build():
    with open('peak-o-mat.spec', 'w') as f:
        f.write(tmpl.format(path=abspath(os.curdir), version=__version__))

    rem = ['build']
    for d in rem:
        if os.path.exists(d):
            shutil.rmtree(d)

    from subprocess import run
    run([r'pyinstaller.exe', '--clean', 'peak-o-mat.spec'], shell=True)

def package_win():
    tmp = []
    os.chdir(out)
    for root, subdirs, files in os.walk(os.curdir):
        for filename in files:
            file_path = normpath(join(root, filename))
            tmp.append(file_path)

    name = 'peak-o-mat2'
    exe = 'peak-o-mat2-{}.exe'.format(__version__)

    with open(diss, "w") as ofi:
        print(r"[Setup]", file=ofi)
        print(r"AppName=%s" % name, file=ofi)
        print(r"AppVerName=%s %s" % (name, __version__), file=ofi)
        print(r"DefaultDirName={pf}\%s %s" % (name, __version__), file=ofi)
        print(r"DefaultGroupName=%s %s" % (name, __version__), file=ofi)
        print(r"Compression=lzma", file=ofi)
        print(r"SolidCompression=yes", file=ofi)
        print(r"OutputBaseFilename=%s-%s_installer"%(name, __version__), file=ofi)
        print(file=ofi)

        print(r"[Files]", file=ofi)
        for path in tmp:
            if path[:3].lower() == 'api':
                continue
            print(r'Source: "%s"; DestDir: "{app}\%s"; Flags: ignoreversion' % (path, os.path.dirname(path)), file=ofi)
        print(file=ofi)

        print(r"[Icons]", file=ofi)
        print(r'Name: "{group}\%s %s"; Filename: "{app}\%s"; IconFilename: "{app}\peak-o-mat.ico"' % \
              (name, __version__, exe), file=ofi)
        print(file=ofi)

        print(r'[Registry]', file=ofi)
        print(r'Root: HKCR; Subkey: ".lpj"; ValueType: string; ValueData: "%s"' % name, file=ofi)
        print('Root: HKCR; Subkey: "%s\DefaultIcon"; ValueType: string; ValueData: "\'{app}\%s.ico\'"' % (name,name), file=ofi)
        print('Root: HKCR; Subkey: "%s\shell\open\command"; ValueType: string; ValueData: "\"\"{app}\%s\"\" \"\"%%1\"\""' % (name,exe), file=ofi)

        res = ctypes.windll.shell32.ShellExecuteA(0, "compile",
                                                  diss,
                                                  None,
                                                  None,
                                                  0)
        if res < 32:
            print('install InnoSetup')

if __name__ == '__main__':
    build()
    package_win()
