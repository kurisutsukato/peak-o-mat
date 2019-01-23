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

menu_ids = ['New','Open project...','Save as...','Save','Quit',
            'Import...','Export...',
            'Notepad','Code Editor','Data Grid',
            'Start plot server',
            'About']
menu_ids = dict([(q,wx.NewId()) for q in menu_ids])

menu_ids['About'] = wx.ID_ABOUT
menu_ids['Preferences'] = wx.ID_PREFERENCES

module_counter = 1
# TODO: das ist nicht schoen: besser als 1000 IDs zu reservieren waere es den omodule_counter
# wieder auf 1 zu setzen, wenn ein neues Projekt geoeffnet wird.

module_menu_ids = dict([(q,wx.NewId()) for q in range(module_counter,1000)])

def add_module(mb, name):
    global module_counter
    mid = module_menu_ids.pop(module_counter)
    module_menu_ids[mid] = name
    menu = mb.GetMenu(2)
    menu.Append(mid, '{}\tCTRL-{}'.format(name,module_counter))
    module_counter += 1

def create(plotserver=False):
    mb = wx.MenuBar()

    def _q(arg):
        mid = arg.split('\t')[0]
        return menu_ids[mid], arg

    file_menu = wx.Menu()
    file_menu.Append(*_q('New'))
    file_menu.Append(*_q('Open project...'))
    file_menu.Append(*_q('Save as...'))
    file_menu.Append(*_q('Save\tCTRL-s'))
    file_menu.Append(*_q('Preferences'))
    file_menu.AppendSeparator()
    file_menu.Append(*_q('Quit\tCTRL-q'))

    data_menu = wx.Menu()
    data_menu.Append(*_q('Import...'))
    data_menu.Append(*_q('Export...'))

    view_menu = wx.Menu()
    view_menu.AppendCheckItem(*_q('Code Editor\tCTRL-e'))
    view_menu.AppendCheckItem(*_q('Data Grid\tCTRL-d'))
    view_menu.AppendCheckItem(*_q('Notepad\tCTRL-i'))
    view_menu.AppendSeparator()

    #for n,m in enumerate(modules):
    #    view_menu.AppendCheckItem(*_q('{}\tCTRL-{}'.format(m,n)))

    help_menu = wx.Menu()
    help_menu.Append(wx.ID_ABOUT, "&About peak-o-mat")

    mb.Append(file_menu, 'File')
    mb.Append(data_menu, 'Data')
    mb.Append(view_menu, 'View')
    if plotserver:
        tools_menu = wx.Menu()
        tools_menu.Append(*_q('Start plot server'))
        mb.Append(tools_menu, 'Tools')
    mb.Append(help_menu, "&Help")

    return mb