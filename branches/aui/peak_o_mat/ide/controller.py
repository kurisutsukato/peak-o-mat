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
    [False, 'rename.py',
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
        super(SortList, self).append(item)
        self[:] = sorted(self, key=itemgetter(1))

    def load(self, row):
        return open(os.path.join(self.basepath, self[row][1])).read()

    def names(self):
        for a, name in self:
            yield name

    def path(self, row):
        return os.path.join(self.basepath, self[row][1])

class PrjScripts(SortList):
    def load(self, row):
        return self[row][2]

    def append(self, item):
        super(SortList, self).append(item)
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

    def Reset(self, length=None):
        if length is None:
            super(ListModel, self).Reset(len(self.data))
        else:
            super(ListModel, self).Reset(length)

    def __contains__(self, item):
        for row in self.data:
            if row[1] == item:
                return True
        return False

    def pop(self, row):
        self._data.pop(row)
        self.Reset(len(self._data))

    def index(self, item):
        for n, row in enumerate(self.data):
            if row[1] == item:
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
            for _r in self._data:
                if _r[1] == str(value):
                    return False
            self._data[row][col] = str(value)
        return True

    def update(self):
        self.Reset(len(self.data))

    def GetColumnCount(self):
        return 2

    def GetColumnType(self, col):
        return ['bool', 'string'][col]


class Controller(object):
    def __init__(self, parent_controller, view=None, interactor=None):
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
        logger.debug('renaming {}: {}->{}'.format(self.edit_mode, oldval, model.data[row][1]))
        if hasattr(model.data, 'basepath'):
            try:
                os.rename(os.path.join(model.data.basepath, oldval),
                          os.path.join(model.data.basepath, model.data[row][1]))
            except IOError:
                return False
            return True
        else:
            return True

    def load_from_project(self, project_data):
        self.model['prj'].data[:] = []
        reg = {}
        for name, cont in project_data:
            if name not in reg.keys():
                reg[name] = 0
            else:
                reg[name] += 1
            if reg[name] > 0:
                name += '-{}'.format(reg[name])
            if name[-3:] != '.py':
                name = name.replace('.','')
                name += '.py'

            self.model['prj'].data.append([False, name, cont])
        self.model['prj'].Reset()

    def save_to_project(self):
        logger.debug('save to project')
        return [[q,p] for _,q,p in self.model['prj'].data]

    def model_update(self):
        val = self.view.editor.GetText()
        ctrl = getattr(self.view,'lst_{}'.format(self.edit_mode))
        if self.edit_mode == 'prj':
            self.model[self.edit_mode].data.update(ctrl._selected, val)
        elif self.edit_mode == 'local':
            with open(self.model[self.edit_mode].data.path(ctrl._selected), 'w', encoding='utf-8') as fp:
                fp.write(val)

    def editor_push_file(self, scope, row):
        data = self.model[scope].data
        cont = data.load(row)
        self.view.editor.ChangeValue(cont)

    def delete_entry(self, scope, row):
        model = self.model[scope]
        logger.debug('delete row {}'.format(row))
        if scope == 'local':
            try:
                os.unlink(model.data.path(row))
            except OSError:
                raise
            else:
                model.pop(row)
        else:
            model.pop(row)

    def add_entry(self, scope):
        model = self.model[scope]
        count = 0
        for name in model.data.names():
            name = name.rstrip('.py')
            try:
                name, num = name.split('-')
            except ValueError:
                num = 0
            if name == 'untitled':
                count = max(count, int(num) + 1)
        if count > 0:
            newname = 'untitled-{}.py'.format(count)
        else:
            newname = 'untitled.py'
        if scope == 'local':
            try:
                open(os.path.join(model.data.basepath, newname), 'w')
            except OSError:
                raise
            else:
                row = model.append([False, newname])
        else:
            row = model.append([False, newname, ''])
        return row


if __name__ == '__main__':
    import wx
    from .view import View
    from .interactor import Interactor

    app = wx.App()
    Controller(View(None), Interactor())
