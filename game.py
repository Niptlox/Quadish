"""Точка входа Quadish.

Команды (работают и из исходников, и в собранном exe):
    python game.py              — запустить игру
    python game.py test         — прогнать тесты игровых механик
    python game.py test физика  — только тесты с подстрокой в имени
    python game.py benchmark    — замерить FPS и скорость генерации
    python game.py help         — справка по командам

Флаги:
    test/benchmark --window     — не скрывать окно (по умолчанию headless)
    benchmark --frames N        — число кадров замера (по умолчанию 400)
    benchmark --pure-noise      — замер со встроенным python-шумом
"""
import os
import sys

# Windows-консоль по умолчанию cp1252 и падает на печати кириллицы
# (UnicodeEncodeError). Переводим вывод в UTF-8; в оконной сборке потоки
# могут быть None — тогда просто пропускаем.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

USAGE = __doc__


def _headless(args):
    # тесты и бенчмарки по умолчанию без окна и звука
    if "--window" not in args:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def main():
    args = sys.argv[1:]
    cmd = args[0].lower() if args and not args[0].startswith("-") else None

    if cmd == "test":
        _headless(args)
        from tools.run_tests import main as run_tests
        sys.exit(run_tests([a for a in args[1:] if not a.startswith("--")]))
    elif cmd in ("benchmark", "bench"):
        _headless(args)
        if "--pure-noise" in args:
            os.environ["QUADISH_PURE_NOISE"] = "1"
        from tools.benchmark import main as run_bench
        sys.exit(run_bench(args[1:]))
    elif cmd in ("help", "--help", "-h"):
        print(USAGE)
        sys.exit(0)
    elif cmd is not None:
        print(f"Неизвестная команда: {cmd}\n{USAGE}")
        sys.exit(2)

    from units.App.Game import GameApp
    game = GameApp()
    game.main()


if __name__ == "__main__":
    main()
