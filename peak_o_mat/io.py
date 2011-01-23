# -*- coding: utf-8 -*-

import csv, codecs, cStringIO
import re
import sys, os
import numpy as N

import settings as config
from misc import PomError

def asfloat(arg):
    if arg.strip() == '':
        return N.NaN
    else:
        return float(arg)

class PomDialect(csv.Dialect):
    delimiter = ','
    skipinitialspace = True
    quoting = 0
    quotechar = '"'
    lineterminator = os.linesep
    doublequote = True
    escapechar = None
    has_rl = False
    has_cl = False
    
    def __str__(self):
        return 'dialect.delimiter = \'%s\''%self.delimiter
    
class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        a = self.reader.next().rstrip()
        while a == '':
            a = self.reader.next().rstrip()
        return a.encode("utf-8")
    
class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encode = codecs.getencoder(encoding)

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data,length = self.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def read_txt(path):
    """\
Reads numeric data with an arbitrary number of columns while trying to
guess the columns delimiter and ignoring comments.
"""
    data = []

    try:
        f = open(path.encode(sys.getfilesystemencoding()))
    except IOError:
        raise PomError,'unable to open \'%s\''%path

    if config.floating_point_is_comma:
        delimiters = ['\t',r'\s+',';']
    else:
        delimiters = ['\t',r'\s+',',',';']

    found = False
    for i in range(20):
        # maybe there is a header, so try the first 20 lines
        line = f.readline().strip()

        # try to guess the delimiter
        for delimiter in delimiters:
            try:
                [float(x.strip()) for x in re.split(delimiter,line)][1]
            except ValueError:
                pass # non float data
            except IndexError:
                pass # less than 2 columns
            else:
                found = True
                break
        if found:
            break
    if not found:
        raise PomError('unable to parse \'%s\''%path)
    
    #print 'delimiter',delimiter
    #print 'data starts at',i

    mat = re.compile(delimiter)
    while line != "":
        out = [x.strip() for x in mat.split(line.strip())]
        if len(out) >= 2:
            data.append(out)
        line = f.readline()
    f.close()

    # try to load labels:
    f = open(path.encode(sys.getfilesystemencoding()))
    line = f.readline()
    f.close()

    try:
        [float(x.strip()) for x in mat.split(line.strip())]
        collabels = [None]*len(data[0])
    except ValueError:
        collabels = [x.strip() for x in mat.split(line.strip())]
    if len(collabels) != len(data[0]):
        collabels = [None]*len(data[0])
        
    try:
        data = [[asfloat(x) for x in line] for line in data]
    except ValueError:
        data = [[asfloat(x.replace(',','.')) for x in line] for line in data]
        config.floating_point_is_comma = True

    if len(data) == 0:
        raise PomError, 'unable to parse %s'%path

    return collabels,N.transpose(data)

def read_dat(path):
    data = [[float(x) for x in re.split('[, \t]+',line.strip())] for line in open(path)]
    return data, None, None

def read_csv(path):
    hascollabels = False
    hasrowlabels = False
    data = []

    dialect = PomDialect()
    
    delimiters = [',',' ',';']
    if config.floating_point_is_comma:
        delimiters = [';']

    for dialect.delimiter in delimiters:
        #csv.register_dialect('pom', dialect)
        csvr = UnicodeReader(open(path), dialect=dialect)

        while True:
            try:
                row = csvr.next()
            except:
                break
            if config.floating_point_is_comma:
                row = [q.replace(',','.') for q in row]
            data.append(row)

        firstcol = [list(x) for x in zip(*data)][0]
        firstrow = data[0]

        rlab = None
        clab = None

        try:
            [float(x) for x in firstcol]
        except:
            rlab = firstcol
            data = [list(y) for y in zip(*([list(x) for x in zip(*data)][1:]))]

        try:
            [float(x) for x in firstrow]
        except:
            clab = firstrow
            data = data[1:]

        if rlab is not None and clab is not None:
            rlab = rlab[1:]
            clab = clab[1:]

        if rlab is not None:
            strip = False
            for n,r in enumerate(rlab):
                if r.find(unicode(n)) != 0:
                    break
                strip = True
            if strip:
                rlab = [r[len(unicode(n)):] for n,r in enumerate(rlab)]

        if clab is not None:
            strip = False
            for n,c in enumerate(clab):
                if c.find(unicode(n)) != 0:
                    break
                strip = True
            if strip:
                clab = [c[len(unicode(n)):] for n,c in enumerate(clab)]


        try:
            data = [[asfloat(x) for x in row] for row in data]
            data[0][0]
        except: pass
        else: break
    
    return data, rlab, clab
    
def read_array(path, ext=None):
    if ext is None:
        try:
            ext = path.split('.')[-1]
        except IndexError:
            ext = 'dat'

    data = {'csv':read_csv,'dat':read_dat}[ext](path)
    return data

def write_csv(path, data, rlab=None, clab=None):
    data = data.astype(list)
    if config.floating_point_is_comma:
        data = [[unicode(q).replace('.',',') for q in row] for row in data]
    else:
        data = [[unicode(col) for col in row] for row in data]
    if clab is not None:
        data = [clab]+data

    tmp = []
    data = map(list, zip(*data))
    if rlab is not None:
        if clab is not None:
            rlab = ['']+rlab
        tmp = [rlab]
    data = tmp+data
    data = map(list, zip(*data))

    #dialect = csv.get_dialect('excel')
    dialect = PomDialect()
    if config.floating_point_is_comma:
        dialect.delimiter = ';'
    #csv.register_dialect('pom', dialect)

    f = open(path, 'w')
    csvwriter = UnicodeWriter(f,dialect=dialect)
    csvwriter.writerows(data)

    f.close()

def write_tex(path, data, rlab=None, clab=None):
    data = data.astype(list)
    data = [[unicode(col) for col in row] for row in data]
    if clab is not None:
        data = [clab]+data

    tmp = []
    data = map(list, zip(*data))
    if rlab is not None:
        if clab is not None:
            rlab = ['']+rlab
        tmp = [rlab]
    data = tmp+data
    data = map(list, zip(*data))

    out = []
    ncols = len(data[0])
    nrows = len(data)
    header = '|l|'+'|'.join(['r']*ncols)+'|'
    out.append('\\begin{tabular}{%s}'%header)
    out.append('\\hline')

    for row in data:
        out.append('&'.join([unicode(x) for x in row])+r'\\\hline')
    out.append('\\end{tabular}')
    
    f = open(path, 'w')
    writer = codecs.getwriter('utf-8')(f)
    writer.write('\n'.join(out))
    f.close()

def test1():
    import numpy as N
    cl = ['eins','zwei']
    rl = [u'\u308d','B']
    data = N.zeros((2,2))
    
    write_tex('neu.tex', data, rl, cl)
    write_csv('neu.csv', data, rl, cl)

def test2():  
    a = read_array('deutsch.csv')
    #print a
    
if __name__ == '__main__':
    test1()
    
    
