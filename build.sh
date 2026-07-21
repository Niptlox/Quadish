#!/usr/bin/env bash
# Сборка игры под Linux: ./build.sh  ->  dist/Quadish/
set -e
cd "$(dirname "$0")"

PY=${PYTHON:-python3}

$PY -m venv .venv-build
source .venv-build/bin/activate

pip install --upgrade pip
pip install pillow numpy pygame pyinstaller
# noise — C-расширение; если не соберётся, игра использует встроенный
# (медленный) генератор шума и всё равно работает
pip install noise || echo "ПРЕДУПРЕЖДЕНИЕ: 'noise' не собрался — будет медленный встроенный шум"

pyinstaller Quadish.spec --noconfirm

echo
echo "Готово: dist/Quadish/  (запуск: dist/Quadish/Quadish)"
