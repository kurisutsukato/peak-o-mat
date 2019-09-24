##     Copyright (C) 2003 Christian Kristukat (ckkart@hoc.net)     

##     This program is free software; you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation; either version 2 of the License, or
##     (at your option) any later version.

##     This program is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.

##     You should have received a copy of the GNU General Public License
##     along with this program; if not, write to the Free Software
##     Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import wx


class MenuFactory(object):
    def __init__(self):
        self.module_menu_ids = {}
        self.menu_ids = {'About': wx.ID_ABOUT}

    def add_module(self, mb, name):
        menu = mb.GetMenu(2)
        count = menu.GetMenuItemCount()
        self.module_menu_ids[menu.Append(wx.ID_ANY, '{}\tCTRL-{}'.format(name,count)).GetId()] = name

    def create(self, plotserver=False):
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
        mb.Append(view_menu, 'View')

        if plotserver:
            tools_menu = wx.Menu()
            append(tools_menu,'Start plot server')
            mb.Append(tools_menu, 'Tools')
        mb.Append(help_menu, "&Help")

        return mb