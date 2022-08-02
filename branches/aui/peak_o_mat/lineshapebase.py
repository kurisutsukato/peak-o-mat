__author__ = 'ck'

from .pickers import DummyPicker
import re
import sys
#from RestrictedPython import compile_restricted
import logging

logger = logging.getLogger()

class StripDict(dict):
    """\
    Special dict which strips a trailing number from the item
    name. This was added to support numbering of tokens, e.g. LO1 GA1 LO2
    """
    def __contains__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return dict.__contains__(self, name)
    def __getitem__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return dict.__getitem__(self, name)

class StripList(list):
    """\
    Special list which strips a trailing number from the item
    name. This was added to support numbering of tokens, e.g. LO1 GA1 LO2
    """
    def __contains__(self, name):
        name = re.sub(r'[0-9]*','',name,re.UNICODE)
        return list.__contains__(self, name)
    def __getitem__(self, name):
        name = re.sub(r'[0-9]*','',name)
        return list.__getitem__(self, name)

class LineShape:
    picker = DummyPicker
    info = 'no description available'
    func = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        try:
            setattr(self, 'code', compile(self.func, '<string>', 'eval'))
        except:
            tp,msg,tb = sys.exc_info()
            logger.warning(tp,msg,'in user func',self.func)

class LineShapes(StripDict):
    def __init__(self, data):
        StripDict.__init__(self, data)
        self.setup()

    def setup(self):
        self.auto = []
        self.background = []
        self.peak = []
        ptypes = {}
        for k,v in self.items():
            if v.picker is not DummyPicker and k not in self.auto:
                self.auto.append(k)
            if v.ptype == 'BACKGROUND' and k not in self.background:
                self.background.append(k)
            if v.ptype == 'PEAK' and k not in self.peak:
                self.peak.append(k)
            ptypes[v.ptype] = True
        self.auto = StripList(self.auto)
        self.background = StripList(self.background)
        self.peak = StripList(self.peak)
        self.ptypes = list(ptypes.keys())
        self.ptypes.sort()

    def update(self, data):
        StripDict.update(self, data)
        self.setup()

    def group(self, id):
        """\
        returns the list of peak symbols belonging to
        group 'id' (either 'BACKGROUND','PEAK','EXP','MISC')
        """
        out = []
        for k,v in self.items():
            if v.ptype == id:
                out.append(k)
        out.sort()
        return StripList(out)

    def known(self, tokens):
        for i in tokens:
            if i not in self:
                return False
        return True

lineshapes = LineShapes({})

def add(name, **kwargs):
    lineshapes.update({name:LineShape(**kwargs)})

