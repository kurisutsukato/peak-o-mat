
from ..misc import PomError
from .. import config

import sys
import re
import numpy as np

def asfloat(arg):
    if arg.strip() == '' or '#' in arg:
        return np.NaN
    else:
        return float(arg)

def guess_format(path):
    data = []

    class Found(Exception):
        pass

    try:
        for enc in [None]+config.options('encodings'):
            try:
                f = open(path,encoding=enc)
            except IOError:
                raise PomError('Cannot read \'%s\'. Check file permissions.'%path)
            else:
                try:
                    rawdata = f.read()
                except UnicodeDecodeError:
                    continue
                else:
                    f.seek(0)
                    raise Found
    except Found:
        pass
    else:
        raise PomError('Cannot read \'%s\'. Unknown encoding.'%path)
    finally:
        f.close()

    text = rawdata.strip().split('\n')

    delimiters = ['\t',r'\s+',';']
    fp = config.getboolean('general','floating_point_is_comma')
    if not fp:
        delimiters.append(',')

    replace_comma = False
    try:
        for _ in range(2):
            for row in range(20):
                # maybe there is a header, so try the first 20 lines
                try:
                    line = text[row]
                except IndexError:
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
            delimiters.remove(',')
            text = rawdata.replace(',','.').strip().split('\n')
            replace_comma = True
    except Found:
        print('delimiter identified at row {}: {}'.format(row,delimiter))
        print('floting comma:',replace_comma)
        datastart = row
    else:
        raise PomError('Cannot parse \'%s\'. Unknown format.'%path)

    mat = re.compile(delimiter)
    for line in text[datastart:]:
        out = [x.strip() for x in mat.split(line.strip())]
        if len(out) >= 2:
            data.append(out)

    # try to load labels:
    line = text[datastart-1]

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

    data = [[asfloat(x) for x in mat.split(line.strip())] for line in text[datastart:]]

    if len(data) == 0:
        raise PomError('unable to parse %s'%path)

    data = np.asarray(data)
    print('found {} columns'.format(data.shape[1]))
    print('encoding:', enc)
    return

if __name__ == '__main__':
    guess_format('Untitled.csv')
    guess_format('latin.txt')
    guess_format('jap.txt')