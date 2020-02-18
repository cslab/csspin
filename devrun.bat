@echo off
echo Preparing an editable install of 'spin' ...
pip uninstall -q -y virtualenv
pip install -q "virtualenv<20.0"
pip install -q -e .
c:\Scoop\apps\python\current\Scripts\spin %*

