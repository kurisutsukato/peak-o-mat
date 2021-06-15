__author__ = 'kristukat'

from .controller import Controller
from .view import View
from .interactor import Interactor

def new(controller, parent):
    return Controller(controller, View(parent), Interactor())
