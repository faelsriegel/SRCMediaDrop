@echo off
setlocal

cd /d %~dp0

set PYTHON_BIN=python
if exist .venv\Scripts\python.exe set PYTHON_BIN=.venv\Scripts\python.exe

%PYTHON_BIN% -m pip install --upgrade pip
%PYTHON_BIN% -m pip install pyinstaller -r requirements.txt
%PYTHON_BIN% tools\generate_app_icons.py

%PYTHON_BIN% -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name SRCMediaDrop ^
  --icon "build\icons\app_icon.ico" ^
  --version-file "tools\windows_version.txt" ^
  --hidden-import pystray ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageDraw ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "ffmpeg;ffmpeg" ^
  --add-data "app_meta.py;." ^
  launcher_gui.py

echo.
echo Build release concluido. Execute: dist\SRCMediaDrop.exe
pause
