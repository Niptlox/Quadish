# Сборка и запуск Quadish

## Запуск из исходников

Нужен Python 3.10–3.13 (проверено на 3.13).

```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
python game.py
```

## Сборка в исполняемый файл

Готовые скрипты создают отдельную сборочную среду и собирают игру
через PyInstaller в папку `dist/Quadish/` — её можно целиком отдать
игроку, Python у него не нужен.

- **Windows:** запустить `build.bat` (двойным кликом или из консоли).
  Результат: `dist\Quadish\Quadish.exe`
- **Linux:** `./build.sh`
  Результат: `dist/Quadish/Quadish`

Сборка под Windows делается на Windows, под Linux — на Linux
(PyInstaller не умеет кросс-компиляцию).

## Про пакет `noise` на Windows

Пакет `noise` (simplex-шум для генерации мира) — это C-расширение без
готовых сборок под Windows, поэтому `pip install noise` требует
установленный компилятор и часто падает с ошибкой про
"Microsoft Visual C++ Build Tools".

Что важно знать:

1. **Игра работает и без него.** Если пакет не установлен, автоматически
   включается встроенный генератор шума на чистом Python
   (`units/noise_compat.py`). Он медленнее (генерация новых чанков
   подтормаживает) и даёт другие миры при том же сиде, но всё играбельно.
   Скрипты сборки учитывают это: если `noise` не собрался, сборка
   продолжается с фолбэком.

2. **Чтобы поставить настоящий `noise` на Windows**, установите
   [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   (галочка "Desktop development with C++"), затем:

   ```bash
   pip install noise
   ```

3. На Linux обычно достаточно установленного `gcc` и заголовков Python
   (`sudo apt install build-essential python3-dev`) — там `noise`
   собирается без проблем.

## Частые проблемы

- **Чёрное окно / нет картинок после сборки** — проверьте, что рядом с
  исполняемым файлом лежат папка `data/` и `settings.ini` (spec-файл
  кладёт их автоматически, не перемещайте exe отдельно от папки).
- **Игра не запускается с ошибкой про settings.ini** — файл настроек
  должен лежать рядом с `game.py` (или с exe в сборке).
- **Антивирус ругается на exe** — обычное дело для PyInstaller-сборок,
  добавьте в исключения или собирайте сами из исходников.
