#!/usr/bin/python

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

import os
import sys
from optparse import OptionParser

import locale

parser = OptionParser()
parser.add_option("-a", "--antialias", dest="antialias", action="store_true", default=False,
                  help='antialiased drawing')
parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
                  help='print debugging information')

options, sysargs = parser.parse_args()

fast_display = False
fast_max_pts = 500

truncate = False
truncate_max_pts = 2000
truncate_interpolate = False

floating_point_is_comma = ',' in locale.str(1.2)

home = os.path.expanduser("~")

if os.path.exists(home+'/.peak-o-mat/config.py'):
    try:
        execfile(home+'/.peak-o-mat/config.py')
    except:
        print 'could not read config.py'
else:
    print 'no config.py in \'%s\''%os.path.join(home,'.peak-o-mat')


