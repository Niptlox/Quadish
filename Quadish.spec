# PyInstaller spec: сборка игры в папку dist/Quadish
# Запуск: pyinstaller Quadish.spec --noconfirm  (или через build.sh / build.bat)

a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data', 'data'),
        ('settings.ini', '.'),
        ('help.txt', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[],
    excludes=['tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Quadish',
    console=False,
    icon='data/sprites/Icon.ico',
    # всё содержимое рядом с exe (data/, settings.ini), а не в _internal —
    # units/config.py ищет файлы рядом с исполняемым файлом
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='Quadish',
)
