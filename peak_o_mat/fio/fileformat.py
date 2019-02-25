
from ..misc import PomError
from .. import config

import sys
import re
import numpy as np

def asfloat(arg):
    if arg.rstrip() == '' or '#' in arg:
        return np.NaN
    else:
        return float(arg)

def guess_format(path):
    data = []

    class Found(Exception):
        pass

    try:
        for enc in [None]+config.options('encodings'):
            # None corresponds to the default platform encoding
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
        #print('encoding', enc)
        pass
    else:
        raise PomError('Cannot read \'%s\'. Unknown encoding.'%path)
    finally:
        f.close()

    text = rawdata.rstrip().split('\n')

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
                for skipcol in range(2):
                    for delimiter in delimiters:
                        try:
                            assert len([float(x.strip()) for x in re.split(delimiter,line)[skipcol:]]) >= 2
                        except AssertionError:
                            #print('asert')
                            pass
                        except ValueError:
                            #print('value')
                            pass # non numeric data
                        except IndexError:
                            #print('index')
                            pass # less than 2 columns
                        else:
                            raise Found
            delimiters.remove(',')
            text = rawdata.replace(',','.').rstrip().split('\n')
            replace_comma = True
    except Found:
        #print('delimiter identified at row {}: "{}"'.format(row,delimiter))
        #print('floting comma:',replace_comma)
        #print('has row label: {}'.format(bool(skipcol)))
        datastart = row
    else:
        raise PomError('Cannot parse \'%s\'. Unknown format.'%path)

    mat = re.compile(delimiter)

    data = [[asfloat(x) for x in mat.split(line)[skipcol:]] for line in text[datastart:]]
    data = np.asarray(data)

    if len(data) == 0:
        raise PomError('unable to parse %s'%path)

    # try to load labels:
    collabels = [x.strip() for x in mat.split(text[min(0,datastart-1)])]
    has_collabels = len(collabels) == data.shape[1]+skipcol
    print(len(collabels),data.shape[1],skipcol)
    print(collabels)
    #print('found {} columns'.format(data.shape[1]))
    #print('encoding:', enc)

    return path, enc, has_collabels, bool(skipcol), replace_comma, datastart, data.shape[1]

if __name__ == '__main__':

    print(guess_format('windows_utf.csv'))
    print(guess_format('windows_utf-norowlabel.csv'))
    print(guess_format('windows_utf-tab.csv'))
    print(guess_format('windows_utf-tab-comma.csv'))
    print(guess_format('windows_utf-tab-comma-nocollabel.csv'))
