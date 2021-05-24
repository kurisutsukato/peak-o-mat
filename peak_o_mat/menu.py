##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

import wx


class MenuFactory(object):
    def __init__(self):
        self.module_menu_ids = {}
        self.menu_ids = {'About': wx.ID_ABOUT}

    def add_module(self, mb, name):
        menu = mb.GetMenu(2)
        count = menu.GetMenuItemCount()-4
        self.module_menu_ids[menu.Append(wx.ID_ANY, '{}\tCTRL-{}'.format(name,count), kind=wx.ITEM_CHECK).GetId()] = name

    def create(self):
        mb = wx.MenuBar()

        def append(menu, mi_desc, **kwargs):
            lab = mi_desc.split('\t')[0]
            self.menu_ids[lab] = menu.Append(wx.ID_ANY, mi_desc, **kwargs).GetId()

        file_menu = wx.Menu()
        append(file_menu,'New')
        append(file_menu,'Open project...')
        append(file_menu,'Save as...')
        append(file_menu,'Save\tCTRL-s')
        #append(file_menu,'Preferences')
        file_menu.AppendSeparator()
        append(file_menu,'Quit\tCTRL-q')

        data_menu = wx.Menu()
        append(data_menu,'Import...')
        append(data_menu,'Export...')

        view_menu = wx.Menu()
        append(view_menu,'Code Editor\tCTRL-e', kind=wx.ITEM_CHECK)
        append(view_menu,'Data Grid\tCTRL-d', kind=wx.ITEM_CHECK)
        append(view_menu,'Notepad\tCTRL-i', kind=wx.ITEM_CHECK)
        view_menu.AppendSeparator()

        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "&About peak-o-mat")

        mb.Append(file_menu, 'File')
        mb.Append(data_menu, 'Data')
        mb.Append(view_menu, 'Tools')

        mb.Append(help_menu, "&Help")

        return mb