__author__ = 'ck'

import subprocess
import sys
import os
import zipfile

from threading  import Thread
from queue import Queue, Empty

from peak_o_mat import __version__

dest_dir = 'dist/peak-o-mat-{}'.format(__version__)

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--local", help="create distribution from working copy",
                    action="store_true")
args = parser.parse_args()

def export():
    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    try:
        os.mkdir('dist')
    except OSError:
        pass

    if args.local:
        prc = subprocess.Popen('svn export --trust-server-cert --force . {}'.format(dest_dir),
                               shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
    else:
        prc = subprocess.Popen('svn export --trust-server-cert --force https://svn.hoc.net/peak-o-mat/branches/aui {}'.format(dest_dir),
                               shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

    qout = Queue()
    t = Thread(target=enqueue_output, args=(prc.stdout, qout))
    t.daemon = True # thread dies with the program
    t.start()

    qin = Queue()
    t = Thread(target=enqueue_output, args=(sys.stdin, qin))
    t.daemon = True # thread dies with the program
    t.start()

    inp = ''
    while True:
        try:  #line = q.get_nowait() # or
            line = qout.get(timeout=.5)
        except Empty:
            try:
                ch = qin.get_nowait()
                inp += ch
                if ch == '\n':
                    prc.stdin.write(inp)
                    inp = ''
            except Empty:
                pass
        else: # got line
            print(line.strip())
        if prc.poll() is not None:
            break

def zip():
    def zipdir(path, ziph):
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for f in files:
                ziph.write(os.path.join(root, f),
                           os.path.relpath(os.path.join(root, f), os.path.join(path, '..')))

    zipf = zipfile.ZipFile(dest_dir+'.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir(dest_dir, zipf)
    zipf.close()


exclude = '''\
dist/peak-o-mat-{0}/A90_map_pol_0.txt
dist/peak-o-mat-{0}/distfromsvn.py
dist/peak-o-mat-{0}/distfromsvn.sh
dist/peak-o-mat-{0}/MANIFEST.in
dist/peak-o-mat-{0}/neon.lpj
dist/peak-o-mat-{0}/publish.sh
dist/peak-o-mat-{0}/setup.py
'''.format(__version__)

def customize():
    for ex in exclude.split('\n'):
        try:
            os.unlink(ex)
        except OSError:
            pass

    if not '.' in __version__:
        f = open(os.path.join(dest_dir,'SVNREVISION'),'w')
        f.write('%s\n'%__version__)
        f.close()

export()
customize()
zip()


