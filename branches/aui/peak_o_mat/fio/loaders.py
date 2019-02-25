__author__ = 'kristukat'

import sys
import re
import numpy as np
from io import open

from ..misc import PomError
from .. import config

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


def TXTLoader(path):
    """\
Reads numeric data with an arbitrary number of columns while trying to
guess the columns delimiter and ignoring comments.
"""

    data = []

    class Found(Exception):
        pass

    try:
        for enc in config.options('encodings'):
            print(enc)
            try:
                f = open(path.encode(sys.getfilesystemencoding()),encoding=enc)
            except IOError:
                raise PomError('Cannot read \'%s\'. Check file permissions.'%path)
            else:
                try:
                    f.read()
                except UnicodeDecodeError:
                    continue
                else:
                    f.seek(0)
                    raise Found
    except Found:
        pass
    else:
        raise PomError('Cannot read \'%s\'. Unknown encoding.'%path)

    delimiters = ['\t',r'\s+',';']
    try:
        fp = config.getboolean('general','floating_point_is_comma')
    except:
        pass
    else:
        if not fp:
            delimiters.append(',')

    replace_comma = False

    try:
        for row in range(10):
            # maybe there is a header, so try the first 20 lines
            try:
                line = f.readline().strip()
            except UnicodeDecodeError:
                break
            # try to guess the delimiter
            for delimiter in delimiters:
                try:
                    assert len([float(x.strip()) for x in re.split(delimiter,line)]) >= 2
                except AssertionError:
                    pass
                except ValueError:
                    pass # non numeric data
                except IndexError:
                    pass # less than 2 columns
                else:
                    raise Found
            if ',' not in delimiters:
                line = line.replace(',','.')
                replace_comma = True
    except Found:
        print('delimiter identified at row {}: {}'.format(row,delimiter))
        pass
    else:
        f.close()
        raise PomError('Cannot parse \'%s\'. Unknown format.'%path)

    mat = re.compile(delimiter)
    while line != "":
        if replace_comma:
            line = line.replace(',','.')
        out = [x.strip() for x in mat.split(line.strip())]
        if len(out) >= 2:
            data.append(out)
        line = f.readline()
    f.close()

    # try to load labels:
    f = open(path.encode(sys.getfilesystemencoding()),encoding=enc)
    line = f.readlines()[max(0,row-1)]
    f.close()

    if replace_comma:
        line = line.replace(',','.')

    try:
        [float(x.strip()) for x in mat.split(line.strip())]
        collabels = [None]*len(data[0])
    except ValueError:
        collabels = [x.strip() for x in mat.split(line.strip())]
    if len(collabels) == len(data[0])+1:
        if collabels[0] in ['#',';','//']:
            collabels.pop(0)
    if len(collabels) != len(data[0]):
        collabels = [None]*len(data[0])

    data = [[asfloat(x) for x in line] for line in data]

    if len(data) == 0:
        raise PomError('unable to parse %s'%path)

    #if len(data[0]) > 2:
    #    data = np.asarray(data)
    #    u0,u1 = [ len(np.unique(q)) for q in data[:,:2].T ]
    #    if u1*u0 == data.shape[0]:
    #        print 'bidim'

    return collabels,list(zip(*data))


from collections import OrderedDict
class Loaders(OrderedDict):
    def __missing__(self, key):
        return self['_fallback_']

    def __getitem__(self, item):
        item = ''.join(i for i in item if not i.isdigit())
        return super(Loaders, self).__getitem__(item)

all = Loaders([
    ('.txt',{'wildcard':'Text files (*.txt)|*.txt', 'loader':TXTLoader}),
    #('.dat',{'wildcard':'Geotherm Ergebnis files (*.dat)|*.dat', 'loader':DATLoader}),
    ('.xml',{'wildcard':'Profilometer XML (*.xml)|*.xml', 'loader':XMLLoader}),
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

