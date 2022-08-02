__author__ = 'kristukat'

import sys
import re
import numpy as np
from io import open

from ..misc import PomError
from .. import config

from .fileformat import guess_format

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

def get(ext):
    return all[ext]['loader']

def asfloat(arg):
    if arg.strip() in ['','-'] or '#' in arg:
        return np.nan
    else:
        return float(arg)

def DATLoader(obj):
    data = open(obj).read().split(',')
    maxtime = int(data[0])
    tin = [float(data[36+q*23]) for q in range(maxtime)]
    tout = [float(data[37+q*23]) for q in range(maxtime)]
    ta = [float(data[38+q*23]) for q in range(maxtime)]
    return ['time (h)','tin (C)', 'tout (C)','ta (C)'],[list(range(maxtime)),tin,tout,ta]

def XMLLoader(obj): # loader for Dektak Profilometer data
    try:
        tree = ET.ElementTree(file=obj)
    except IOError:
        raise

    root = tree.getroot()
    for block in root.findall('DataBlock'):
        data = []
        for d in block.findall('Data'):
            xy = [float(d.find(q).text) for q in ['X','Z']]
            data.append(xy)
    return ['X','Z'],np.transpose(data) # no labels

def SPCLoader(path):
    f = spc.File(path)
    data = [f.x]+[q.y for q in f.sub]
    print(len(f.x),f.x)
    for s in f.sub:
        print(len(s.y),s.y)
    print([q.y for q in f.sub])
    collabels = [None]*(len(data))
    print(np.asarray(data).shape)
    return collabels,data

def NGSLoader(path):
    from struct import unpack_from
    from array import array
    buf = open(path, 'rb').read()
    sty = buf.find('\xFF\xFF\xFF\xFF')
    # get size
    size = unpack_from('i',buf,sty+4)[0]
    print(size)
    data = array('f')
    #data starts 16 bytes later
    data.fromstring(buf[sty+16:size*4+sty+16])
    y = data.tolist()

    #there seems to be a constant offset of 71 between the end of the first data block and the next one
    stx = sty+16+4*size+71
    print(stx)
    data = array('f')
    try:
        data.fromstring(buf[stx:size*4+stx])
    except ValueError:
        x = list(range(size))
    else:
        x = data.tolist()

    return [None,None],np.asarray([x,y])

def PPMLoader(path):
    data = np.loadtxt(path)
    return ['ang','counts'],data.take([2,0],axis=1).T

import struct
import array
import numpy as np

def spa_loader(path):
    print('spa loader')
    with open(path, 'rb') as f:
        f.seek(30)
        cmt = f.read(255).strip(b'\x00').decode('utf-8')

        f.seek(564)
        num_points = struct.unpack('<I', f.read(4))[0]

        f.seek(576)
        wmin, wmax = struct.unpack('<ff', f.read(8))

        f.seek(288)

        flag = 0
        while flag != 3:
            flag, offset = struct.unpack('<HH', f.read(4))

        f.seek(offset)
        intensities = array.array('f')
        intensities.fromfile(f, num_points)

        intensities = np.array(intensities)
        wl = np.linspace(wmin, wmax, num_points)
        return None, np.asarray([wl,intensities]).T

def TXTLoader(path):
    """\
Reads numeric data with an arbitrary number of columns while trying to
guess the columns delimiter and ignoring comments.
"""

    try:
        enc, cl, rl, delimiter, fpc, datastart, columns = guess_format(path)
        #print('cl: {}, rl: {}'.format(cl,rl))
    except PomError as pe:
        raise
    else:
        rowlabels = []
        collabels = []

        with open(path, encoding=enc) as datafile:
            mat = re.compile(delimiter)
            data = []
            for k in range(datastart - int(cl)):
                datafile.readline()
            if cl:
                collabels = mat.split(datafile.readline().rstrip().rstrip(delimiter))[int(rl):]
                if collabels[0] == '':
                    collabels.pop(0)
            for line in datafile:
                line = line.rstrip() #.rstrip(delimiter)
                if fpc:
                    line = line.replace(',', '.')
                line = mat.split(line.rstrip())
                if rl:
                    rowlabels.append(line[0])
                try:
                    tmp = [float(q) if q.strip() != '' else np.nan for q in line[int(rl):]]
                    if len(tmp) == 0 or (len(data) > 0 and len(tmp) != len(data[-1])):
                        raise PomError('Unable to read file. Unaligned data found.')
                        break
                    else:
                        data.append(tmp)
                except ValueError:
                    break

        try:
            data = np.asarray(data, dtype=float)
        except ValueError:
            raise PomError('Unable to read file. Unaligned data found.')
        print(data)
        r,c = data.shape
        if r < 5 and c>r*2:
            data = data.T

        return collabels if len(collabels) == len(data[0]) else None, np.asarray(data)
               #rowlabels if rowlabels != [] else None, \

from collections import OrderedDict
class Loaders(OrderedDict):
    def __missing__(self, key):
        return self['_fallback_']

    def __getitem__(self, item):
        item = ''.join(i for i in item if not i.isdigit())
        return super(Loaders, self).__getitem__(item)

all = Loaders([
    ('.txt',{'wildcard':'Text files (*.txt)|*.txt', 'loader':TXTLoader}),
    ('.spa',{'wildcard':'Thermo Fisher (*.spa)|*.spa', 'loader':spa_loader}),
    #('.xml',{'wildcard':'Profilometer XML (*.xml)|*.xml', 'loader':XMLLoader}),
    #('.spc',{'wildcard':'Thermo Scientific (*.spc)|*.spc', 'loader':SPCLoader}),
    #('.pp',{'wildcard':'PPM XRR code (*.pp?)|*.pp?', 'loader':PPMLoader}),
    #('.ngs',{'wildcard':'SpecWin (*.ngs)|*.ngs', 'loader':NGSLoader}),
    ('_fallback_',{'wildcard':'All files (*.*)|*.*', 'loader':TXTLoader})
])

wildcards = '|'.join([all[q]['wildcard'] for q in list(all.keys())])

xml = '<ProfilometerData><Header><TestDate>10-05-2015</TestDate><TestTime>14:49:22</TestTime><XUnits>MICRON</XUnits><ZUnits>NANOMETER</ZUnits><NumData>3745</NumData><DataGain>1</DataGain><DataOffset>0</DataOffset></Header><DataBlock><Data><X>0</X><Z>2.226047</Z></Data><Data><X>0.08009425</X><Z>0.719367</Z></Data><Data><X>0.1601913</X><Z>1.52586</Z></Data></DataBlock></ProfilometerData>'

import unittest

class Tests(unittest.TestCase):
    def test1(self):
        import io
        f = io.StringIO(xml)
        XMLLoader(f)
        print(wildcards)
        print(get('.mp3'))

    def test2(self):
        TXTLoader('/Users/ck/devel/sandbox/testspek/ASCII (dat)/dat_test2a.dat')

    def test3(self):
        SPCLoader('/Users/ck/devel/sandbox/testspek/THERMO Galactic (spc)/Raman/Diamond.spc')

    def test3(self):
        head,data = PPMLoader(r'C:\Program Files\PPM 3.0\examples\ex_scalar_2_fit\tial_fit_res.pp1')
        print(head)

if __name__ == '__main__':
    unittest.main()

