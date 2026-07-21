"""Мини-раннер тестов без внешних зависимостей — работает и в exe-сборке.

Запуск: python game.py test [подстрока имени...]
"""
import time
import traceback


def main(filters=None):
    filters = filters or []
    from tests import test_mechanics as tm

    names = [n for n in dir(tm) if n.startswith("test_")]
    if filters:
        names = [n for n in names if any(f.lower() in n.lower() for f in filters)]
    if not names:
        print("Тесты не найдены по фильтру:", filters)
        return 2

    print(f"Запуск {len(names)} тестов...\n")
    passed, failed = 0, []
    t_all = time.time()
    for name in names:
        t0 = time.time()
        try:
            getattr(tm, name)()
            print(f"  OK   {name} ({time.time() - t0:.2f}с)")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            print()
            failed.append(name)

    print(f"\nИтог: {passed} прошло, {len(failed)} упало, "
          f"{time.time() - t_all:.1f}с")
    if failed:
        print("Упавшие:", ", ".join(failed))
        return 1
    return 0
