@echo off
rem Сборка игры под Windows: build.bat  ->  dist\Quadish\
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

%PY% -m venv .venv-build
call .venv-build\Scripts\activate.bat

pip install --upgrade pip
pip install pillow numpy pygame pyinstaller
rem noise - C-расширение, на Windows требует MSVC Build Tools.
rem Если не соберётся — игра использует встроенный (медленный) шум и всё равно работает.
pip install noise
if errorlevel 1 echo ПРЕДУПРЕЖДЕНИЕ: 'noise' не собрался — будет медленный встроенный шум (см. BUILDING.md)

pyinstaller Quadish.spec --noconfirm

echo.
echo Готово: dist\Quadish\  (запуск: dist\Quadish\Quadish.exe)
pause
