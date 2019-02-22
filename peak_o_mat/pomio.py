# -*- coding: cp1252 -*-

import csv, codecs, io
import re
import sys, io
import numpy as np

import locale

from .misc import PomError

def asfloat(arg):
    if arg.strip() == '' or '#' in arg:
        return np.NaN
    else:
        return float(arg)

class PomDialect(csv.Dialect):
    delimiter = ';'
    skipinitialspace = True
    quoting = 0
    quotechar = '"'
    lineterminator = '\n'
    doublequote = True
    escapechar = None
    has_rl = False
    has_cl = False
    skiplines = 0

    def __str__(self):
        return 'dialect.delimiter = \'%s\''%self.delimiter

import re
reg = re.compile(r'(\S+)\s*(\s{1})')

class LocaleAware(object):
    def __init__(self):
        locale.setlocale(locale.LC_ALL, '')
        self.defaultencoding = locale.getpreferredencoding()

class CSVReader(LocaleAware):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding=None):
        super(CSVReader, self).__init__()
        if encoding is None:
            encoding = self.defaultencoding
        self.reader = csv.reader(f, dialect=dialect)

    def __next__(self):
        row = next(self.reader)
        return row

    def __iter__(self):
        return self

class CSVWriter(LocaleAware):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding=None):
        super(CSVWriter, self).__init__()
        if encoding is None:
            encoding = self.defaultencoding
            print(encoding)

        # Redirect output to a queue
        self.queue = io.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect)
        self.stream = f
        self.encode = codecs.getencoder(encoding)

    def writerow(self, row):
        #self.writer.writerow([s.encode("utf-8") for s in row])
        self.writer.writerow(row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()#.decode("utf-8")
        # ... and reencode it into the target encoding
        data,length = self.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)
        self.queue.seek(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

#TODO: not used
def __read_txt(path):
    """\
Reads numeric data with an arbitrary number of columns while trying to
guess the columns delimiter and ignoring comments.
"""
    data = []

    try:
        f = io.open(path.encode(sys.getfilesystemencoding()), encoding=sys.getdefaultencoding())
    except IOError as e:
        raise PomError('unable to open \'%s\'\n{}'.format(path, e))

    if config.floating_point_is_comma:
        delimiters = ['\t',r'\s+',';']
    else:
        delimiters = ['\t',r'\s+',',',';']

    replace_comma = False
    class Found(Exception):
        pass

    try:
        for row in range(20):
            # maybe there is a header, so try the first 20 lines
            line = f.readline().strip()

            # try to guess the delimiter
            for i in range(2):
                for delimiter in delimiters:
                    try:
                        assert len([float(x.strip()) for x in re.split(delimiter,line)]) >= 2
                    except AssertionError:
                        pass
                    except ValueError:
                        pass # non float data
                    except IndexError:
                        pass # less than 2 columns
                    else:
                        raise Found
                line = line.replace(',','.')
                replace_comma = True
    except:
        print(('delimiter indentified at row {}'.format(row)))
        pass
    else:
        f.close()
        raise PomError('unable to parse \'{}\''.format(path))
    
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
    f = open(path.encode(sys.getfilesystemencoding()))
    line = f.readlines()[max(0,row-1)]
    f.close()

    if replace_comma:
        line = line.replace(',','.')

    try:
        [float(x.strip()) for x in mat.split(line.strip())]
        collabels = [None]*len(data[0])
    except ValueError:
        collabels = [x.strip() for x in mat.split(line.strip())]
    if len(collabels) != len(data[0]):
        collabels = [None]*len(data[0])
        
    data = [[asfloat(x) for x in line] for line in data]
 
    if len(data) == 0:
        raise PomError('unable to parse {}'.format(path))

    return collabels,np.transpose(data)

def read_csv(path):
    data = []

    dialect = PomDialect()
    
    delimiters = [',',' ',';']
    if config.floating_point_is_comma:
        delimiters = [';',' ']

    for dialect.delimiter in delimiters:
        #csv.register_dialect('pom', dialect)
        csvr = CSVReader(open(path,'rb'), dialect=dialect)

        while True:
            try:
                row = next(csvr)
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
                if r.find(str(n)) != 0:
                    break
                strip = True
            if strip:
                rlab = [r[len(str(n)):] for n,r in enumerate(rlab)]

        if clab is not None:
            strip = False
            for n,c in enumerate(clab):
                if c.find(str(n)) != 0:
                    break
                strip = True
            if strip:
                clab = [c[len(str(n)):] for n,c in enumerate(clab)]

        try:
            data = [[asfloat(x) for x in row] for row in data]
            data[0][0]
        except: pass
        else: break
    
    return data, rlab, clab

def write_txt(path, data):
    np.savetxt(path, data)

def write_csv(path, data, rlab=None, clab=None, encoding=None):
    data = data.astype(list)

    data = [[str(col) for col in row] for row in data]

    if clab is not None:
        data = [clab]+data

    tmp = []
    data = list(map(list, list(zip(*data))))
    if rlab is not None:
        if clab is not None:
            rlab = ['']+rlab
        tmp = [rlab]
    data = tmp+data
    data = list(map(list, list(zip(*data))))

    dialect = csv.get_dialect('excel')

    with open(path, 'wb') as f:
        csvwriter = CSVWriter(f, dialect=dialect, encoding=encoding)
        csvwriter.writerows(data)

def write_tex(path, data, rlab=None, clab=None):
    data = data.astype(list)
    data = [[str(col) for col in row] for row in data]
    if clab is not None:
        data = [clab]+data

    tmp = []
    data = list(map(list, list(zip(*data))))
    if rlab is not None:
        if clab is not None:
            rlab = ['']+rlab
        tmp = [rlab]
    data = tmp+data
    data = list(map(list, list(zip(*data))))

    out = []
    ncols = len(data[0])
    nrows = len(data)
    header = '|l|'+'|'.join(['r']*ncols)+'|'
    out.append('\\begin{tabular}{%s}'%header)
    out.append('\\hline')

    for row in data:
        out.append('&'.join([str(x) for x in row])+r'\\\hline')
    out.append('\\end{tabular}')
    
    f = open(path, 'w')
    writer = codecs.getwriter('ascii')(f, 'ignore')
    writer.write('\n'.join(out))
    f.close()

def test1():
    import numpy as np
    cl = ['tensi\xf3n','eñe']
    rl = ['A','B']
    data = np.zeros((2,2))
    
    write_tex('data.tex', data, rl, cl)
    write_csv('dataN.csv', data, rl, cl)

if __name__ == '__main__':
    test1()
    
    
