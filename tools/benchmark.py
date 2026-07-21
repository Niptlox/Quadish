"""Бенчмарк: FPS игрового цикла и скорость генерации чанков.

Запуск: python game.py benchmark [--frames N] [--seed N] [--pure-noise]
"""
import random
import time


def _arg(argv, name, default):
    if name in argv:
        try:
            return int(argv[argv.index(name) + 1])
        except (IndexError, ValueError):
            pass
    return default


def main(argv=None):
    argv = argv or []
    frames = _arg(argv, "--frames", 400)
    seed = _arg(argv, "--seed", 12345)

    t0 = time.time()
    from units.App.Game import GameApp
    from units.Map import WorldStorage
    from units.noise_compat import HAS_C_NOISE

    # миры бенчмарка — во временную папку, не в data/maps
    import tempfile
    WorldStorage.GAMEMAPS_PATH = tempfile.mkdtemp(prefix="quadish-bench-")

    app = GameApp()
    print(f"Инициализация: {time.time() - t0:.2f}с "
          f"(шум: {'C-расширение noise' if HAS_C_NOISE else 'встроенный python'})")

    random.seed(42)
    game = app.game_scene
    game.game_map.new_world(base_generation=seed)
    game.elapsed_time = 16  # фиксируем кадр как при 60 FPS

    # прогрев: генерация стартовых чанков вокруг игрока
    for _ in range(30):
        game.pg_events()
        game.update()

    # 1) статичная сцена
    t0 = time.time()
    for _ in range(frames):
        game.pg_events()
        game.update()
    dt = time.time() - t0
    print(f"Статичная сцена:  {frames / dt:6.1f} FPS  ({dt / frames * 1000:.2f} мс/кадр)")

    # 2) движение с генерацией новых чанков
    move_frames = max(100, frames // 2)
    t0 = time.time()
    for _ in range(move_frames):
        game.player.rect.x += 24  # ~ бег
        game.pg_events()
        game.update()
    dt = time.time() - t0
    print(f"Бег по миру:      {move_frames / dt:6.1f} FPS  ({dt / move_frames * 1000:.2f} мс/кадр)")

    # 3) чистая генерация чанков уровня земли
    n = 30
    t0 = time.time()
    for cx in range(1000, 1000 + n):
        game.game_map.generate_chunk(cx, 0)
    dt = (time.time() - t0) / n * 1000
    print(f"Генерация чанка:  {dt:6.1f} мс/чанк")
    return 0
