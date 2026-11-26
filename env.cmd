@echo off
for %%I in ("%~dp0..") do set "ENVROOT=%%~fI"
set "PATH=%ENVROOT%;%ENVROOT%\Scripts;%ENVROOT%\Library\bin;%PATH%"
set "PYTHONNOUSERSITE=1"
cd /d "%~dp0"
python -c "import os, sys; r = os.environ['ENVROOT'].lower(); e = sys.executable.lower(); print(('OK: ' if e.startswith(r) else 'ERROR: python is not from ' + os.environ['ENVROOT'] + ': ') + sys.executable)"