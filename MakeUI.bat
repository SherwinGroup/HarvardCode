@ECHO OFF
set input="%~1"
set postpend="_ui.py"
set output=%input:~1,-4%
python "C:\Program Files (x86)\WinPython\python-2.7.6.amd64\Lib\site-packages\PyQt4\uic\pyuic.py" %input% -o "%input:~0,-4%_ui.py"
