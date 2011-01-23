#!/bin/bash

rst2html --link-stylesheet --stylesheet-path=DOCUMENTATION.css DOCUMENTATION >DOCUMENTATION.html
scp DOCUMENTATION.html ckkart@shell.sf.net:/home/groups/l/lo/lorentz/htdocs/index.html
scp CHANGELOG ckkart@shell.sf.net:/home/groups/l/lo/lorentz/htdocs/
#rsync -avz -e ssh DOCUMENTATION.html CHANGELOG ckkart@shell.sf.net:/home/groups/l/lo/lorentz/htdocs/
#rsync --delete-excluded --exclude '.svn*' -avz -e ssh images ckkart@shell.sf.net:/home/groups/l/lo/lorentz/htdocs/

