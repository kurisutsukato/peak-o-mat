__author__ = 'kristukat'

import wx.dataview as dv
from pubsub import pub
import logging
from operator import itemgetter
from glob import glob
import os.path
import os

from ..appdata import configdir

logger = logging.getLogger('pom')

prjscripts = [
    [False, 'rename',
     '''\
for p in project:
    for s in p:
        print(p.name, s.name)
''']
]

class SortList(list):
    def _append(self, item):
        super(SortList, self).append(item)
        self[:] = sorted(self, key=itemgetter(1))

    def index(self, item):
        for n, i in enumerate(self):
            if i[1] == item:
                return n

class LocalScripts(SortList):
    def __init__(self, basepath):
        self.basepath = basepath
        fls = glob(os.path.join(basepath, '*.py'))

        super(LocalScripts, self).__init__([[False, os.path.basename(q)] for q in fls])

    def append(self, item):
        super(SortList, self).append([False, item])
        self[:] = sorted(self, key=itemgetter(1))

    def load(self, row):
        return open(os.path.join(self.basepath, self[row][1])).read()

    def names(self):
        for a, name in self:
            yield name

class PrjScripts(SortList):
    def load(self, row):
        return self[row][2]

    def append(self, item):
        super(SortList, self).append([False, item, ''])
        self[:] = sorted(self, key=itemgetter(1))

    def names(self):
        for a, name, script in self:
            yield name

    def update(self, row, val):
        self[row][2] = val

class ListModel(dv.DataViewIndexListModel):
    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self, len(data))
        self._data = data

    def __contains__(self, item):
        for a, name in self.data:
            if name == item:
                return True
        return False

    def pop(self, row):
        self._data.pop(row)
        self.Reset(len(self._data))

    def index(self, item):
        for n, (a, name) in enumerate(self.data):
            logger.warning('searching {}, found {}'.format(item, name))
            if name == item:
                return n
        raise ValueError('\'{}\' not in list'.format(item))

    def append(self, item):
        self._data.append(item)
        self.Reset(len(self._data))
        return self._data.index(item)

    def sort(self):
        self._data[:] = sorted(self._data, key=itemgetter(1))
        self.Reset(len(self._data))

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self.Reset(len(data))

    def GetValueByRow(self, row, col):
        try:
            return str(self._data[row][col]) if col > 0 else self._data[row][col]
        except IndexError:
            print('getvaluebyrow index error row {}, col {}'.format(row, col))
            return 0

    def SetValueByRow(self, value, row, col):
        if col == 0:
            self._data[row][col] = bool(value)
        else:
            self._data[row][col] = str(value)
        return True

    def update(self):
        self.Reset(len(self.data))

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        return ['bool', 'string'][col]


class Controller(object):
    def __init__(self, view=None, interactor=None):
        self.view = view
        if interactor is not None:
            interactor.Install(self, view)

        self.model = {
            'prj': ListModel(PrjScripts(prjscripts)),
            'local': ListModel(LocalScripts(os.path.join(configdir(), 'userfunc')))
        }
        self.edit_mode = None   # maybe 'prj' or 'local'

        self.view.set_model('local', self.model['local'])
        self.view.set_model('prj', self.model['prj'])

        self.view.run()

    def rename(self, model, oldval, row):
        logger.warning('renaming {}: {}->{}'.format(self.edit_mode, oldval, model.data[row][1]))
        if hasattr(model.data, 'basepath'):
            try:
                os.rename(os.path.join(model.data.basepath, oldval),
                          os.path.join(model.data.basepath, model.data[row][1]))
            except OSError:
                return False
            return True
        else:
            pass
        
    def model_update(self):
        val = self.view.editor.GetText()
        self.model[self.edit_mode].data.update(getattr(self.view,'lst_{}'.format(self.edit_mode))._selected, val)

    def editor_push_file(self, scope, row):
        data = self.model[scope].data
        cont = data.load(row)
        logger.warning('stopping event handler, loading content')
        self.view.SetEvtHandlerEnabled(False)  # TODO:does not work
        self.view.editor.SetText(cont)
        self.view.SetEvtHandlerEnabled(True)

    def delete_entry(self, scope, row):
        model = self.model[scope]
        logger.warning('delete row {}'.format(row))
        model.pop(row)

    def add_entry(self, scope):
        model = self.model[scope]
        count = 0
        for name in model.data.names():
            try:
                name, num = name.split('-')
            except ValueError:
                num = 0
            if name == 'untitled':
                count = max(count, int(num) + 1)
        if count > 0:
            row = model.append('untitled-{}'.format(count))
        else:
            row = model.append('untitled')
        return row


if __name__ == '__main__':
    import wx
    from .view import View
    from .interactor import Interactor

    app = wx.App()
    Controller(View(None), Interactor())
