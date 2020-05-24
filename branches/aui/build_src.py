from peak_o_mat import __version__
from os.path import join, normpath, dirname
import os
from glob import glob

filelist = '''
peak_o_mat/appdata.py
peak_o_mat/calib.py
peak_o_mat/codeeditor.py
peak_o_mat/controller.py
peak_o_mat/controls.py
peak_o_mat/csvwizard.py
peak_o_mat/dialog.py
peak_o_mat/findpeaks.py
peak_o_mat/fit.py
peak_o_mat/fitcontroller.py
peak_o_mat/fitinteractor.py
peak_o_mat/fitpanel.py
peak_o_mat/gridlib.py
peak_o_mat/images.py
peak_o_mat/interactor.py
peak_o_mat/lineshapebase.py
peak_o_mat/lineshapes.py
peak_o_mat/main.py
peak_o_mat/mainframe.py
peak_o_mat/menu.py
peak_o_mat/misc.py
peak_o_mat/misc_ui.py
peak_o_mat/model.py
peak_o_mat/module.py
peak_o_mat/pargrid.py
peak_o_mat/pickers.py
peak_o_mat/plot.py
peak_o_mat/plotcanvas.py
peak_o_mat/pomio.py
peak_o_mat/project.py
peak_o_mat/spec.py
peak_o_mat/stc.py
peak_o_mat/symbols.py
peak_o_mat/tree.py
peak_o_mat/weights.py
peak_o_mat/weightsgrid.py
peak_o_mat/winregistry.py
peak_o_mat/__init__.py
peak_o_mat/mplplot/__init__.py
peak_o_mat/mplplot/controller.py
peak_o_mat/mplplot/interactor.py
peak_o_mat/mplplot/model.py
peak_o_mat/mplplot/plotlayout.py
peak_o_mat/mplplot/view.py
peak_o_mat/datagrid/controller.py
peak_o_mat/datagrid/databridge.py
peak_o_mat/datagrid/interactor.py
peak_o_mat/datagrid/tablebase.py
peak_o_mat/datagrid/view.py
peak_o_mat/datagrid/__init__.py
peak_o_mat/fio/codecs.py
peak_o_mat/fio/loaders.py
peak_o_mat/fio/fileformat.py
peak_o_mat/fio/__init__.py
peak_o_mat/modules/mod_background.py
peak_o_mat/modules/mod_background.xrc
peak_o_mat/modules/mod_calib.py
peak_o_mat/modules/mod_eval.py
peak_o_mat/modules/mod_eval.xrc
peak_o_mat/modules/mod_op.py
peak_o_mat/modules/mod_op.xrc
peak_o_mat/modules/mod_ruby.py
peak_o_mat/modules/mod_ruby.xrc
peak_o_mat/modules/mod_setinfo.py
peak_o_mat/modules/mod_setinfo.xrc
peak_o_mat/modules/template.py
peak_o_mat/modules/template.xrc
peak_o_mat/modules/__init__.py
peak-o-mat.py
peak-o-mat.xrc
peak-o-mat.ico
example.lpj
userfunc_sample.py
images/auto.png
images/auto2fit.png
images/dataset.png
images/dataset_hide.png
images/dataset_model.png
images/dataset_model_hide.png
images/eraser.png
images/hand.png
images/linestyle.png
images/logo.icns
images/logo.png
images/logosmall.png
images/logo_taskbar.png
images/logx.png
images/logy.png
images/peaks.png
images/scalex.png
images/scaley.png
images/zoomxy.png
data/1.89RBM.txt
data/1.90RBM.txt
data/1.91RBM.txt
data/1.92RBM.txt
data/1.93RBM.txt
data/calib.txt
data/gauss.txt
data/peak.txt
data/ruby.txt
data/ruby2.txt
data/ruby3.txt
'''

import sys
from peak_o_mat import version

if len(sys.argv) > 1:
    if sys.argv[1] != '--tag':
        print('only allowed argument: --tag')
        sys.exit()
    else:
        __version__ = '2rev'+version.VERSION
    SVN = False
else:
    SVN = True
    __version__ = '2rev'+version.__version__

files = []

def searchall():
    for dp,dn,fn in os.walk('peak_o_mat'):
        tmp = [os.path.join(dp,q) for q in fn if q.split('.')[-1] in ['py','xrc']]
        files.extend(tmp)
    files.extend(['peak-o-mat.py','peak-o-mat.xrc','example.lpj','userfunc_sample.py'])
    files.extend(glob('images/*'))
    files.extend(glob('data/*'))
    return files

import shutil
out = 'dist/peak-o-mat-{}'.format(__version__)

import zipfile
def zip():
    def zipdir(path, ziph):
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for f in files:
                ziph.write(os.path.join(root, f),
                           os.path.relpath(os.path.join(root, f), os.path.join(path, '..')))

    zipf = zipfile.ZipFile(out+'.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir(out, zipf)
    zipf.close()

def copy():
    if os.path.exists(out):
        shutil.rmtree(out)
    os.mkdir(out)
    for l in filelist.strip().split('\n'):
        if not os.path.exists(normpath(join(out, dirname(l)))):
            os.mkdir(normpath(join(out, dirname(l))))
        shutil.copy(normpath(l), normpath(join(out, l)))
    with open(normpath(join(out, 'peak_o_mat','version.py')), 'w') as f:
        f.write('__version__="{}"\n'.format(__version__))

copy()
zip()
shutil.rmtree(out)
