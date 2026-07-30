"""Тесты игровых механик Quadish.

Запуск: python game.py test            — все тесты
        python game.py test инвентарь  — по подстроке имени (латиницей: inventory)

Игра инициализируется один раз (headless), каждый тест берёт свежий мир.
Сохранения миров уходят во временную папку — data/maps не трогается.
"""
import os
import random
import tempfile

_app = None


def get_app():
    """Ленивая инициализация игры (окно/звук в dummy-режиме)."""
    global _app
    if _app is None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        from units.Map import WorldStorage
        # сохранения тестов — во временную папку
        WorldStorage.GAMEMAPS_PATH = tempfile.mkdtemp(prefix="quadish-tests-")
        from units.App.Game import GameApp
        _app = GameApp()
    return _app


def fresh_world(seed=12345):
    """Новый мир с фиксированным сидом; возвращает игровую сцену."""
    app = get_app()
    random.seed(42)
    app.game_scene.game_map.new_world(base_generation=seed)
    # Игра одна на весь прогон, поэтому флаги игрока обязаны сбрасываться:
    # тест, включивший player.active, менял поведение всех следующих тестов
    # (игрок начинал двигаться в их кадрах) — и падал не он, а они.
    player = app.game_scene.player
    player.active = False
    player.moving_left = player.moving_right = False
    player.track_speed = 0
    return app.game_scene


# ===================== шум =====================

def test_noise_deterministic():
    from units.noise_compat import snoise2
    a = snoise2(1.5, 2.5, 6, persistence=0.35, base=3, lacunarity=2.4)
    b = snoise2(1.5, 2.5, 6, persistence=0.35, base=3, lacunarity=2.4)
    assert a == b
    assert -1.0 <= a <= 1.0
    assert snoise2(1.5, 2.5) != snoise2(1.6, 2.5), "разные точки — разные значения"


def test_noise_pure_python_fallback():
    import importlib
    import units.noise_compat as nc
    os.environ["QUADISH_PURE_NOISE"] = "1"
    try:
        importlib.reload(nc)
        assert not nc.HAS_C_NOISE
        v1 = nc.snoise2(0.7, 0.3, 4, persistence=0.5, base=5, lacunarity=2.0)
        v2 = nc.snoise2(0.7, 0.3, 4, persistence=0.5, base=5, lacunarity=2.0)
        assert v1 == v2
        assert -1.0 <= v1 <= 1.0
        # разные сиды — разные значения
        assert nc.snoise2(0.7, 0.3, base=1) != nc.snoise2(0.7, 0.3, base=2)
    finally:
        os.environ.pop("QUADISH_PURE_NOISE", None)
        importlib.reload(nc)


# ===================== генерация мира =====================

def test_generation_deterministic():
    from units.common import CHUNK_SIZE
    ga = fresh_world(111).game_map
    random.seed(7)
    a = list(ga.generate_chunk(50, 0)[0])
    gb = fresh_world(111).game_map
    random.seed(7)
    b = list(gb.generate_chunk(50, 0)[0])
    assert a == b, "одинаковый сид должен давать одинаковый чанк"

    gc = fresh_world(222).game_map
    random.seed(7)
    c = list(gc.generate_chunk(50, 0)[0])
    assert a != c, "разные сиды должны давать разные чанки"
    assert len(a) == CHUNK_SIZE ** 2 * ga.tile_data_size


def test_chunk_structure():
    from units.common import CHUNK_SIZE
    gm = fresh_world(5).game_map
    chunk = gm.chunk((0, 0), create_chunk=True)
    assert len(chunk) == 6  # static, dynamic, tile_objs, creature_cash, biome, backtiles
    assert len(chunk[0]) == CHUNK_SIZE ** 2 * gm.tile_data_size
    assert len(chunk[4]) == CHUNK_SIZE ** 2
    assert len(chunk[5]) == CHUNK_SIZE ** 2


def test_dynamic_dump_unload():
    from units.common import CHUNK_SIZE
    game = fresh_world(321)
    gm = game.game_map
    gm.dynamic_dump = True
    game.player.rect.x = 0
    game.player.rect.y = 0
    game.player.update_chunk_pos()

    # 1) чистый дальний чанк выгружается из памяти
    far = (400, 400)
    gm.create_pass_chunk(far)
    assert far in gm.game_map and far not in gm.modified_chunks
    gm.unload_far_chunks()
    assert far not in gm.game_map, "чистый дальний чанк должен выгрузиться"

    # 2) модифицированный чанк остаётся в памяти
    gm.set_static_tile(400 * CHUNK_SIZE, 400 * CHUNK_SIZE, 3)
    assert far in gm.modified_chunks
    gm.unload_far_chunks()
    assert far in gm.game_map, "модифицированный чанк выгружать нельзя"

    # 3) чанк с динамикой не выгружается (предметы/существа не теряются)
    other = (410, 410)
    gm.create_pass_chunk(other)
    gm.add_item_of_index(2, 1, 410 * CHUNK_SIZE, 410 * CHUNK_SIZE)
    gm.unload_far_chunks()
    assert other in gm.game_map, "чанк с предметами не выгружается"

    # 4) отключение — ничего не выгружается
    gm.dynamic_dump = False
    empty = (600, 600)
    gm.create_pass_chunk(empty)
    assert gm.unload_far_chunks() == 0
    assert empty in gm.game_map


def test_generation_reproducible_after_unload():
    game = fresh_world(654)
    gm = game.game_map
    a = list(gm.chunk((80, 0), create_chunk=True)[0])
    del gm.game_map[(80, 0)]
    b = list(gm.chunk((80, 0), create_chunk=True)[0])
    assert a == b, "регенерация чанка должна быть идентичной (детерминизм по сиду)"


def test_space_has_asteroids_in_vacuum():
    """До v0.2.16 космос был абсолютно пуст: ни встать, ни копать, ни
    спавниться существам. Теперь там астероиды — но именно вкраплениями,
    а не сплошной породой, иначе это уже не космос."""
    from collections import Counter
    for seed in (5, 42):
        gm = fresh_world(seed).game_map
        types = Counter()
        for cx in range(-6, 7):
            types += Counter(gm.generate_chunk(cx, -100)[0][0::gm.tile_data_size])
        rock = types[26] + types[27] + types[28]
        total = sum(types.values())
        assert rock > 0, f"сид {seed}: астероиды должны генерироваться"
        assert rock < total * 0.5, f"сид {seed}: космос не должен зарастать породой"


def test_space_asteroid_veins_are_findable():
    """Жила даёт пыль (топливо космических механизмов), кристалл — рубины.

    Пороги жил задавались на глаз и на встроенном фолбэке шума: на реальном
    пакете noise (на нём собираются релизы) жила приходилась на 0.26% породы
    — чтобы добыть первую пыль, пришлось бы срыть весь астероид. Тест
    проверяет именно долю, а не сам факт наличия.
    """
    from collections import Counter
    from units.Tiles import tile_drops
    assert any(i == 408 for i, _c, _ch in tile_drops[27]), "жила должна давать пыль"
    assert any(i == 66 for i, _c, _ch in tile_drops[28]), "кристалл должен давать рубины"

    gm = fresh_world(5).game_map
    types = Counter()
    for cx in range(-6, 7):
        types += Counter(gm.generate_chunk(cx, -100)[0][0::gm.tile_data_size])
    rock = types[26] + types[27] + types[28]
    assert rock > 200, "мало породы для оценки доли"
    veins = types[27] / rock
    crystals = types[28] / rock
    assert 0.03 <= veins <= 0.3, f"жил {veins:.1%} породы — ферму пыли не окупить"
    assert 0.005 <= crystals <= 0.1, f"кристаллов {crystals:.1%} породы"


def test_space_creature_pool_has_new_creatures():
    """В космосе был один вид существ на всю зону. Рой — то, что можно
    фармить ради пыли, страж — верхний край сложности."""
    get_app()
    from units.Map.GameMap import random_creature_selection
    from units.Objects.Creatures import DustSwarm, VoidSentinel
    from units.common import START_SPACE_Y
    seen = set()
    for _ in range(4000):
        cls = random_creature_selection(START_SPACE_Y - 500, None)
        if cls is not None:
            seen.add(cls)
    assert DustSwarm in seen and VoidSentinel in seen, seen
    assert any(i == 408 for _c, (i, _n) in DustSwarm.drop_items), "рой должен ронять пыль"


def test_ground_has_tiles():
    gm = fresh_world(5).game_map
    found = False
    for cy in range(1, 4):
        chunk = gm.chunk((0, cy), create_chunk=True)
        if any(t != 0 for t in chunk[0][0::gm.tile_data_size]):
            found = True
            break
    assert found, "под поверхностью должны быть блоки"


def test_biome_of_pos():
    from units.biomes import biome_of_pos, biome_names
    biome, t, p = biome_of_pos(10, 10)
    assert 0 <= biome < len(biome_names)
    # кэш климата 4x4 не меняет тип результата и детерминирован
    cache = {}
    r1 = biome_of_pos(10, 10, cache)
    r2 = biome_of_pos(10, 10, cache)
    assert r1 == r2


# ===================== тайлы =====================

def test_set_get_tile():
    from units.Tiles import TILES_SOLIDITY
    gm = fresh_world(5).game_map
    gm.set_static_tile(10, 10, 3)
    assert gm.get_static_tile_type(10, 10) == 3
    tile = gm.get_static_tile(10, 10)
    assert tile[0] == 3
    assert tile[1] == TILES_SOLIDITY.get(3, -1)

    gm.set_static_tile_solidity(10, 10, 5)
    assert gm.get_static_tile(10, 10)[1] == 5
    gm.set_static_tile_state(10, 10, 2)
    assert gm.get_static_tile(10, 10)[2] == 2

    gm.set_static_tile(10, 10, None)  # сломать блок
    assert gm.get_static_tile_type(10, 10) == 0


def test_tiles_negative_coords():
    gm = fresh_world(5).game_map
    gm.set_static_tile(-5, -7, 2)
    assert gm.get_static_tile_type(-5, -7) == 2


def test_backtiles():
    gm = fresh_world(5).game_map
    gm.set_backtile(4, 4, 1003)
    assert gm.get_backtile(4, 4) == 1003


def test_tile_flags_registry():
    """TILE_FLAGS - единый реестр флагов тайлов (units/Map/TileFlags.py),
    посчитанный из старых set()-ов в units/Tiles.py. Должен согласовываться
    с этими списками и давать корректную битовую комбинацию флагов."""
    from units.Map.TileFlags import TILE_FLAGS, TileFlag, has_flag
    from units.Tiles import PHYSBODY_TILES, SEMIPHYSBODY_TILES, CLASS_TILE, ACTIVATE_TILES, Eats

    for ttile in PHYSBODY_TILES:
        assert has_flag(ttile, TileFlag.PHYSBODY), ttile
    for ttile in SEMIPHYSBODY_TILES:
        assert has_flag(ttile, TileFlag.SEMIPHYSBODY), ttile
    for ttile in CLASS_TILE:
        assert has_flag(ttile, TileFlag.CLASS_TILE), ttile
    for ttile in ACTIVATE_TILES:
        assert has_flag(ttile, TileFlag.ACTIVATABLE), ttile
    for ttile in Eats:
        assert has_flag(ttile, TileFlag.FOOD), ttile

    # активационный блок (210): и класс-тайл, и активируемый - в одной битовой маске
    combo = TILE_FLAGS[210]
    assert combo & TileFlag.CLASS_TILE and combo & TileFlag.ACTIVATABLE

    assert not has_flag(999999, TileFlag.PHYSBODY)  # неизвестный id - без флагов, без KeyError


def test_get_tile_and_obj_ignores_non_int_state():
    """get_tile_and_obj не должен путать dict/list-состояние тайла с id
    объекта (регресс: 'unhashable type: dict' в get_tile_obj)."""
    gm = fresh_world(21).game_map
    gm.set_static_tile(3, 3, gm.get_tile_ttile(102))  # дерево: tile[3] — dict (таймер)
    tile, obj = gm.get_tile_and_obj(3, 3)
    assert obj is None
    assert gm.get_tile_obj(0, 0, {"t": 1}) is None  # прямой вызов с dict тоже безопасен


def test_activator_large_cluster_no_crash():
    """Регресс: скопление активаторов (index 210) рядом с растением-таймером
    (dict-состояние в tile[3]) роняло игру 'unhashable type: dict', т.к.
    get_tile_and_obj принимал любое truthy tile[3] за id объекта. Плюс обход
    кластера был рекурсивным (уязвим к глубокой рекурсии) — теперь итеративный
    (очередь + visited по id)."""
    game = fresh_world(22)
    gm = game.game_map

    n = 120  # длинная цепочка — проверяем, что обход не рекурсивный
    for i in range(n):
        gm.set_static_tile(i, 0, 210)

    # растение с dict-состоянием и динамит сбоку от цепочки (не разрывая её) —
    # раньше именно комбо активатор+растение роняло activate_nearby_tiles
    # на 'unhashable type: dict'
    gm.set_static_tile(5, 1, gm.get_tile_ttile(102))  # дерево
    gm.set_static_tile(60, 1, 9)  # динамит

    first = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    assert first is not None
    first.right_click(None)  # не должно бросить исключение

    activated = sum(
        1 for i in range(n)
        if (obj := gm.get_tile_obj(*gm.to_chunk_xy(i, 0), gm.get_static_tile(i, 0)[3])) is not None
        and obj.activating
    )
    assert activated == n, f"вся цепочка ({n}) должна активироваться, активировано {activated}"

    assert gm.get_static_tile_type(60, 1) == 0  # динамит сдетонировал, тайл очищен
    chunk = gm.chunk(gm.to_chunk_xy(60, 1))
    assert any(type(obj).__name__ == "Dynamite" for obj in chunk[1])


def test_timer_block_auto_triggers_network():
    """TimerBlock должен сам (без клика игрока) периодически запускать
    подключённую сеть активаторов через bfs_activate."""
    game = fresh_world(23)
    gm = game.game_map
    gm.set_static_tile(0, 0, 211)  # таймер
    gm.set_static_tile(1, 0, 210)  # активатор рядом

    timer = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    activator = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    assert timer is not None and activator is not None

    for _ in range(timer.interval):
        assert not activator.activating
        timer.update(16)
    assert activator.activating, "по истечении интервала таймер должен активировать сеть"


def test_pressure_plate_triggers_on_player_step():
    """PressurePlate должна активировать сеть, когда игрок встаёт на неё, и
    продолжать держать сеть активной, пока он с неё не сойдёт (не только в
    момент наступания — иначе всё дальше по сети, например лампа, гасло бы
    через 1 такт, хотя игрок всё ещё стоит на плите)."""
    game = fresh_world(24)
    gm = game.game_map
    gm.set_static_tile(0, 0, 212)  # нажимная плита
    gm.set_static_tile(1, 0, 210)  # активатор рядом

    plate = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    activator = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])

    from units.common import TSIZE
    game.player.rect.topleft = (TSIZE * 100, TSIZE * 100)  # далеко от плиты
    plate.update(16)
    assert not plate.pressed
    assert not activator.activating

    game.player.rect.topleft = plate.rect.topleft  # встал на плиту
    for _ in range(3):
        game.tact += 1
        plate.update(16)
        activator.update(16)
        assert plate.pressed
        assert activator.activating, "сеть должна оставаться активной, пока игрок стоит на плите"

    game.player.rect.topleft = (TSIZE * 100, TSIZE * 100)  # сошёл с плиты
    game.tact += 1
    plate.update(16)
    assert not plate.pressed
    game.tact += 2  # запас на допуск в 1 такт у activator.is_active()
    activator.update(16)
    assert not activator.activating, "после ухода игрока сеть должна погаснуть"


def test_signal_tact_freshness_independent_of_update_order():
    """Регресс: activator.update() раньше безусловно сбрасывал activating
    каждый кадр (self.activating = False), а тайлы обновляются в порядке
    растрового обхода видимых тайлов, а не 'сначала источники, потом
    приёмники'. Если бы Lamp читала голый activating без допуска в такт,
    результат кадра зависел бы от того, кто из них обновился раньше.
    Проверяем оба порядка вызова update() в одном такте — итог должен
    быть одинаковым."""
    game = fresh_world(26)
    gm = game.game_map
    gm.set_static_tile(0, 0, 214)  # рычаг
    gm.set_static_tile(1, 0, 215)  # лампа рядом

    lever = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lamp = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    lever.on = True

    from units.Tiles import lamp_on_img, lamp_off_img

    # Порядок 1: лампа обновляется РАНЬШЕ рычага в этом такте
    game.tact += 1
    img = lamp.update(16)
    lever.update(16)
    assert img is lamp_off_img  # рычаг ещё не успел коснуться лампы в этом такте
    game.tact += 1
    img = lamp.update(16)  # но со следующего такта (допуск в 1) уже видно
    lever.update(16)
    assert img is lamp_on_img

    # Порядок 2: рычаг обновляется РАНЬШЕ лампы — тоже должно корректно засветиться
    lever2_pos = (5, 0)
    gm.set_static_tile(*lever2_pos, 214)
    gm.set_static_tile(6, 0, 215)
    lever2 = gm.get_tile_obj(*gm.to_chunk_xy(*lever2_pos), gm.get_static_tile(*lever2_pos)[3])
    lamp2 = gm.get_tile_obj(*gm.to_chunk_xy(6, 0), gm.get_static_tile(6, 0)[3])
    lever2.on = True
    game.tact += 1
    lever2.update(16)
    img = lamp2.update(16)
    assert img is lamp_on_img


def test_logic_gates_not_and_or():
    """НЕ/И/ИЛИ должны корректно вычисляться по числу активных соседей."""
    game = fresh_world(27)
    gm = game.game_map

    def tick(*tiles):
        # имитирует кадр игры: каждый причастный тайл обновляется на
        # каждом такте (иначе "источник" сам перестанет числиться активным)
        game.tact += 1
        for t in tiles:
            t.update(16)

    # НЕ: горит, пока нет сигнала; гаснет, когда сосед-рычаг включён
    gm.set_static_tile(0, 0, 216)  # NOT
    not_gate = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    tick(not_gate)
    assert not_gate.activating, "без входов вентиль НЕ должен быть включён"

    gm.set_static_tile(1, 0, 214)  # рычаг рядом с NOT
    lever = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    lever.on = True
    tick(lever, not_gate)
    tick(lever, not_gate)
    tick(lever, not_gate)
    assert not not_gate.activating, "с активным соседом вентиль НЕ должен погаснуть"

    # И: горит только при двух активных соседях
    gm.set_static_tile(10, 0, 217)  # AND
    and_gate = gm.get_tile_obj(*gm.to_chunk_xy(10, 0), gm.get_static_tile(10, 0)[3])
    gm.set_static_tile(9, 0, 214)
    gm.set_static_tile(11, 0, 214)
    lever_a = gm.get_tile_obj(*gm.to_chunk_xy(9, 0), gm.get_static_tile(9, 0)[3])
    lever_b = gm.get_tile_obj(*gm.to_chunk_xy(11, 0), gm.get_static_tile(11, 0)[3])

    lever_a.on = True
    tick(lever_a, lever_b, and_gate)
    tick(lever_a, lever_b, and_gate)
    assert not and_gate.activating, "с одним активным входом И ещё не должен включиться"

    lever_b.on = True
    tick(lever_a, lever_b, and_gate)
    tick(lever_a, lever_b, and_gate)
    assert and_gate.activating, "с двумя активными входами И должен включиться"

    # ИЛИ: горит уже при одном активном соседе
    gm.set_static_tile(20, 0, 218)  # OR
    or_gate = gm.get_tile_obj(*gm.to_chunk_xy(20, 0), gm.get_static_tile(20, 0)[3])
    gm.set_static_tile(19, 0, 214)
    lever_c = gm.get_tile_obj(*gm.to_chunk_xy(19, 0), gm.get_static_tile(19, 0)[3])
    lever_c.on = True
    tick(lever_c, or_gate)
    tick(lever_c, or_gate)
    assert or_gate.activating, "ИЛИ должен включиться уже от одного активного соседа"


def test_wire_lamp_chain():
    """Рычаг -> провод(а) -> лампа: лампа должна оставаться включённой всё
    время, пока рычаг ON, и погаснуть в течение допуска после выключения."""
    game = fresh_world(28)
    gm = game.game_map
    gm.set_static_tile(0, 0, 214)  # рычаг
    gm.set_static_tile(1, 0, 213)  # провод
    gm.set_static_tile(2, 0, 213)  # провод
    gm.set_static_tile(3, 0, 215)  # лампа

    lever = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lamp = gm.get_tile_obj(*gm.to_chunk_xy(3, 0), gm.get_static_tile(3, 0)[3])

    from units.Tiles import lamp_on_img, lamp_off_img

    lever.on = True
    for _ in range(4):
        game.tact += 1
        lever.update(16)
        img = lamp.update(16)
    assert img is lamp_on_img, "лампа должна загореться через провод от рычага"

    lever.on = False
    img = None
    for _ in range(3):
        game.tact += 1
        lever.update(16)
        img = lamp.update(16)
    assert img is lamp_off_img, "лампа должна погаснуть после выключения рычага"


def test_chunk_loader_protects_area_when_active():
    """ChunkLoader должен защищать чанки в радиусе от выгрузки, только пока
    получает сигнал от сети — переключается рычагом, как и остальные
    сигнальные блоки (см. GameMap.unload_far_chunks)."""
    from units.common import CHUNK_SIZE
    game = fresh_world(322)
    gm = game.game_map
    gm.dynamic_dump = True
    game.player.rect.x = 0
    game.player.rect.y = 0
    game.player.update_chunk_pos()

    loader_chunk = (300, 300)
    near_chunk = (301, 300)  # в базовом радиусе прогрузчика
    far_chunk = (310, 300)  # далеко за радиусом

    loader_tx, loader_ty = loader_chunk[0] * CHUNK_SIZE, loader_chunk[1] * CHUNK_SIZE
    gm.set_static_tile(loader_tx, loader_ty, 219)
    loader = gm.get_tile_obj(*loader_chunk, gm.get_static_tile(loader_tx, loader_ty)[3])
    assert loader is not None and loader.radius == loader.BASE_RADIUS

    # без сигнала: прогрузчик ничего не защищает сверх обычных правил
    gm.create_pass_chunk(near_chunk)
    gm.create_pass_chunk(far_chunk)
    loader.update(16)
    gm.unload_far_chunks()
    assert near_chunk not in gm.game_map, "без сигнала прогрузчик не должен защищать соседние чанки"
    assert far_chunk not in gm.game_map

    # включаем сигнал рычагом вплотную к прогрузчику
    gm.create_pass_chunk(near_chunk)
    gm.create_pass_chunk(far_chunk)
    lever_x, lever_y = loader_tx - 1, loader_ty
    gm.set_static_tile(lever_x, lever_y, 214)
    lever = gm.get_tile_obj(*gm.to_chunk_xy(lever_x, lever_y), gm.get_static_tile(lever_x, lever_y)[3])
    lever.on = True
    game.tact += 1
    lever.update(16)
    loader.update(16)

    gm.unload_far_chunks()
    assert near_chunk in gm.game_map, "активный прогрузчик должен защитить соседний чанк в радиусе"
    assert far_chunk not in gm.game_map, "чанк за радиусом прогрузчика должен выгружаться как обычно"

    # выключаем рычаг — защита должна сняться (с учётом допуска в 1 такт)
    lever.on = False
    game.tact += 1
    lever.update(16)
    loader.update(16)
    game.tact += 2
    loader.update(16)

    gm.unload_far_chunks()
    assert near_chunk not in gm.game_map, "после выключения сигнала прогрузчик не должен защищать чанк"


def test_delay_block_fires_after_delay_not_before():
    """DelayBlock не может быть собран из готовых блоков — bfs_activate
    распространяется мгновенно на весь связный участок (нет задержки по
    расстоянию), поэтому нужен отдельный узел с памятью о такте выстрела."""
    game = fresh_world(29)
    gm = game.game_map
    gm.set_static_tile(0, 0, 220)  # задержка
    gm.set_static_tile(1, 0, 214)  # рычаг рядом

    delay = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lever = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    assert delay.delay > 1

    lever.on = True
    for _ in range(delay.delay):
        game.tact += 1
        lever.update(16)
        delay.update(16)
    assert not delay.activating, "раньше срока задержка не должна срабатывать"

    game.tact += 1
    lever.update(16)
    delay.update(16)
    assert delay.activating, "ровно через delay тактов после фронта сигнала должна сработать"


def test_music_block_plays_note_on_signal_rising_edge():
    """MusicBlock должен проигрывать ноту (зависящую от предмета в ячейке)
    ровно один раз на фронт сигнала, а не на каждый такт, пока сигнал
    держится (иначе вместо ноты был бы жужжащий треск при удержании рычага)."""
    from units.Objects.Items import ItemsTile
    from units.Tiles import music_block_img, music_block_flash_img

    game = fresh_world(30)
    gm = game.game_map
    gm.set_static_tile(0, 0, 221)  # муз-блок
    gm.set_static_tile(1, 0, 214)  # рычаг рядом

    music = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lever = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    music.inventory.put_to_inventory(ItemsTile(game, 3, count=1))  # камень задаёт ноту

    img = music.update(16)
    assert img is music_block_img, "без сигнала муз-блок не вспыхивает"

    lever.on = True
    game.tact += 1
    lever.update(16)
    img = music.update(16)
    assert img is music_block_flash_img, "на фронте сигнала должна быть вспышка (и играть нота)"

    game.tact += 1
    lever.update(16)
    img = music.update(16)
    assert img is music_block_img, "пока сигнал держится дальше, повторной вспышки/ноты быть не должно"


def test_note_sound_for_item_differs_by_item():
    """Разные предметы в ячейке — разные ноты."""
    from units.sound import note_sound_for_item
    assert note_sound_for_item(3) is note_sound_for_item(3)  # кэш - тот же объект
    assert note_sound_for_item(3) is not note_sound_for_item(12)


def test_transmitter_receiver_matching_frequency():
    """Передатчик должен удалённо включать только Приёмники с такой же
    4-предметной комбинацией и в пределах TRANSMITTER_RANGE — без
    физического провода между ними (см. docs/SIGNAL_NETWORK_CONCEPT.md)."""
    from units.Objects.Items import ItemsTile
    from units.common import TRANSMITTER_RANGE

    game = fresh_world(31)
    gm = game.game_map
    gm.set_static_tile(0, 0, 223)  # передатчик
    gm.set_static_tile(1, 0, 214)  # рычаг рядом (локальный источник)
    gm.set_static_tile(50, 0, 222)  # приёмник в радиусе, та же частота
    gm.set_static_tile(500, 0, 222)  # приёмник далеко за радиусом

    tx = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lever = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    rx_near = gm.get_tile_obj(*gm.to_chunk_xy(50, 0), gm.get_static_tile(50, 0)[3])
    rx_far = gm.get_tile_obj(*gm.to_chunk_xy(500, 0), gm.get_static_tile(500, 0)[3])
    assert 50 <= TRANSMITTER_RANGE < 500

    tx.inventory.put_to_inventory(ItemsTile(game, 3, count=1))
    rx_near.inventory.put_to_inventory(ItemsTile(game, 3, count=1))
    rx_far.inventory.put_to_inventory(ItemsTile(game, 3, count=1))
    assert gm.signal_receivers[(3,)] == {rx_near, rx_far}

    lever.on = True
    game.tact += 1
    lever.update(16)
    tx.update(16)
    rx_near.update(16)
    rx_far.update(16)

    assert rx_near.activating, "приёмник в радиусе с той же частотой должен включиться"
    assert not rx_far.activating, "приёмник за пределами радиуса не должен включиться"


def test_receiver_ignores_mismatched_frequency():
    """Приёмник с другой комбинацией предметов не должен реагировать."""
    from units.Objects.Items import ItemsTile

    game = fresh_world(32)
    gm = game.game_map
    gm.set_static_tile(0, 0, 223)
    gm.set_static_tile(1, 0, 214)
    gm.set_static_tile(10, 0, 222)

    tx = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    lever = gm.get_tile_obj(*gm.to_chunk_xy(1, 0), gm.get_static_tile(1, 0)[3])
    rx = gm.get_tile_obj(*gm.to_chunk_xy(10, 0), gm.get_static_tile(10, 0)[3])

    tx.inventory.put_to_inventory(ItemsTile(game, 3, count=1))
    rx.inventory.put_to_inventory(ItemsTile(game, 12, count=1))  # другой предмет - другая частота

    lever.on = True
    game.tact += 1
    lever.update(16)
    tx.update(16)
    rx.update(16)
    assert not rx.activating, "разная частота - приёмник не должен реагировать"


def test_receiver_unregisters_on_break():
    """Сломанный приёмник должен исчезать из GameMap.signal_receivers, а не
    висеть там мёртвой ссылкой."""
    from units.Objects.Items import ItemsTile

    game = fresh_world(33)
    gm = game.game_map
    gm.set_static_tile(0, 0, 222)
    rx = gm.get_tile_obj(*gm.to_chunk_xy(0, 0), gm.get_static_tile(0, 0)[3])
    rx.inventory.put_to_inventory(ItemsTile(game, 3, count=1))
    assert rx in gm.signal_receivers.get((3,), set())

    rx.items_of_break()
    assert (3,) not in gm.signal_receivers or rx not in gm.signal_receivers[(3,)]


# ===================== хранилище миров =====================

def test_world_storage_crud():
    get_app()
    from units.Map import WorldStorage as WS
    before = {w["id"] for w in WS.list_worlds()}
    meta = WS.new_world_meta()
    assert meta["id"] not in before
    assert meta["name"].startswith("Мир ")
    # мир без world.dat не показывается в списке
    assert meta["id"] not in {w["id"] for w in WS.list_worlds()}
    with open(WS.data_path(meta["id"]), "wb") as f:
        f.write(b"data")
    assert meta["id"] in {w["id"] for w in WS.list_worlds()}

    WS.touch_meta(meta["id"], playtime=125)
    assert WS.load_meta(meta["id"])["playtime"] == 125

    WS.delete_world(meta["id"])
    assert meta["id"] not in {w["id"] for w in WS.list_worlds()}
    assert WS.load_meta(meta["id"]) is None


def test_world_storage_migration():
    get_app()
    from units.Map import WorldStorage as WS
    legacy = os.path.join(WS.GAMEMAPS_PATH, "game_map-3.pclv")
    with open(legacy, "wb") as f:
        f.write(b"legacy")
    worlds = WS.list_worlds()
    assert not os.path.exists(legacy), "старый файл должен переехать"
    migrated = [w for w in worlds if "#3" in w.get("name", "")]
    assert migrated, worlds
    WS.delete_world(migrated[0]["id"])


def test_world_storage_format_helpers():
    from units.Map import WorldStorage as WS
    assert WS.format_playtime(0) == "0 мин"
    assert WS.format_playtime(90) == "1 мин"
    assert WS.format_playtime(3700).startswith("1 ч")
    assert WS.format_last_played(None) == ""


# ===================== сохранение/загрузка =====================

def test_save_load_roundtrip():
    from units.common import TSIZE
    from units.Objects.Items import ItemsTile
    game = fresh_world(9)
    gm = game.game_map

    gm.set_static_tile(3, 3, 3)  # метка в мире
    game.player.tp_to((TSIZE * 7, -TSIZE * 2))
    px, py = game.player.rect.x, game.player.rect.y
    ok, _ = game.player.inventory.put_to_inventory(ItemsTile(game, 12, count=5))
    assert ok

    gm.save_current_game_map()
    wid = gm.world_id
    assert wid is not None

    fresh_world(1)  # затираем всё другим миром
    res = gm.open_game_map(game, wid)
    assert res, "мир должен загрузиться"
    assert gm.world_id == wid
    assert gm.get_static_tile_type(3, 3) == 3
    assert (game.player.rect.x, game.player.rect.y) == (px, py)
    assert any(it and it.index == 12 and it.count == 5 for it in game.player.inventory)


def test_load_missing_world():
    game = fresh_world(2)
    assert game.game_map.open_game_map(game, "no-such-world") is None


# ===================== инвентарь =====================

def _empty_inventory(game):
    inv = game.player.inventory
    inv.inventory[:] = [None] * inv.inventory_size
    return inv


def test_inventory_stacking():
    from units.Objects.Items import ItemsTile
    game = fresh_world(3)
    inv = _empty_inventory(game)
    ok, _ = inv.put_to_inventory(ItemsTile(game, 2, count=10))
    assert ok
    ok, _ = inv.put_to_inventory(ItemsTile(game, 2, count=20))
    assert ok
    assert inv[0].count == 30, "одинаковые предметы должны складываться в стопку"
    assert inv.find_in_inventory(2, 30)
    assert not inv.find_in_inventory(2, 31)


def test_inventory_overflow_to_next_cell():
    from units.Objects.Items import ItemsTile
    game = fresh_world(3)
    inv = _empty_inventory(game)
    cell_size = ItemsTile.cell_size
    ok, _ = inv.put_to_inventory(ItemsTile(game, 3, count=cell_size + 5))
    assert ok
    assert inv[0].count == cell_size
    assert inv[1].count == 5


def test_inventory_full():
    from units.Objects.Items import ItemsTile
    game = fresh_world(3)
    inv = _empty_inventory(game)
    for i in range(inv.inventory_size):
        inv[i] = ItemsTile(game, 4, count=ItemsTile.cell_size)
    ok, rest = inv.put_to_inventory(ItemsTile(game, 5, count=7))
    assert not ok and rest == 7, "полный инвентарь должен вернуть предмет"


def test_inventory_take_across_cells():
    from units.Objects.Items import ItemsTile
    game = fresh_world(3)
    inv = _empty_inventory(game)
    inv[0] = ItemsTile(game, 2, count=10)
    inv[3] = ItemsTile(game, 2, count=10)
    assert inv.get_from_inventory(2, 15)
    assert not inv.find_in_inventory(2, 6)
    assert inv.find_in_inventory(2, 5)


def test_inventory_discard_drops_item():
    from units.Objects.Items import ItemsTile
    game = fresh_world(3)
    inv = _empty_inventory(game)
    inv[0] = ItemsTile(game, 2, count=1)
    item = inv[0]
    inv.discard_item(0)
    assert inv[0] is None
    chunk = game.game_map.chunk(item.chunk_pos)
    assert item in chunk[1], "выброшенный предмет должен попасть в мир"


def test_craft():
    from units.Objects.Items import ItemsTile
    game = fresh_world(4)
    inv = _empty_inventory(game)
    # рецепт #0: доски (11) x2 из бревна (12) x1
    assert not inv.check_creating_item_of_i(0), "без ресурсов крафт запрещён"
    inv.put_to_inventory(ItemsTile(game, 12, count=1))
    assert inv.check_creating_item_of_i(0)
    inv.creating_item_of_i(0)
    assert inv.find_in_inventory(11, 2), "результат крафта должен появиться"
    assert not inv.find_in_inventory(12, 1), "ресурсы должны потратиться"


def test_craft_creative_ignores_resources():
    game = fresh_world(4)
    inv = _empty_inventory(game)
    game.player.set_game_mode(True)
    try:
        assert inv.check_creating_item_of_i(0)
    finally:
        game.player.set_game_mode(False)


# ===================== игрок =====================

def test_player_damage_and_death():
    game = fresh_world(6)
    p = game.player
    p.lives = p.max_lives
    assert p.damage(5)
    assert p.lives == p.max_lives - 5
    assert p.alive
    p.damage(p.lives)
    assert not p.alive


def test_player_relive():
    game = fresh_world(6)
    p = game.player
    p.damage(p.max_lives * 2)
    assert not p.alive
    p.relive()
    assert p.alive
    assert p.lives == p.max_lives


def test_player_creative_immortal():
    game = fresh_world(6)
    p = game.player
    p.lives = p.max_lives
    p.set_game_mode(True)
    try:
        assert p.damage(9999)
        assert p.lives == p.max_lives
    finally:
        p.set_game_mode(False)


def test_player_teleport():
    from units.common import TSIZE
    game = fresh_world(6)
    p = game.player
    p.spawn_point = (100, 200)
    p.tp_to_home()
    assert p.rect.center == (100 + TSIZE // 2, 200 + TSIZE // 2)


# ===================== физика =====================

def test_physics_gravity_landing():
    from units.common import TSIZE
    from units.Objects.Entity import PhysicalObject
    game = fresh_world(8)
    obj = PhysicalObject(game, x=8, y=0, width=16, height=16, use_physics=True)
    # пол из камня на тайловой строке y=2
    game.screen_map.static_tiles = {(0, 2): 3, (1, 2): 3}
    for _ in range(150):
        obj.update_physics(16)
    assert obj.rect.bottom == 2 * TSIZE, "объект должен приземлиться на пол"
    # и остаться стоять, а не проваливаться
    for _ in range(150):
        obj.update_physics(16)
    assert obj.rect.bottom == 2 * TSIZE


def test_physics_wall_stops_movement():
    from units.common import TSIZE
    from units.Objects.Entity import PhysicalObject
    game = fresh_world(8)
    obj = PhysicalObject(game, x=0, y=0, width=16, height=16)
    coll = obj.move((60, 0), {(2, 0): 3})
    assert obj.rect.right == 2 * TSIZE, "стена справа должна остановить"
    assert coll["right"]

    obj2 = PhysicalObject(game, x=40, y=0, width=16, height=16)
    coll2 = obj2.move((-30, 0), {(0, 0): 3})
    assert obj2.rect.left == TSIZE, "стена слева должна остановить"
    assert coll2["left"]


def test_physics_dangerous_tile_damages():
    from units.Objects.Entity import PhysicalObject
    game = fresh_world(8)

    class Dummy(PhysicalObject):
        max_lives = 10

    d = Dummy(game, x=0, y=0, width=16, height=16)
    d.lives = d.max_lives
    d.move((40, 0), {(1, 0): 103})  # тайл 103 наносит урон при касании
    assert d.lives < d.max_lives


# ===================== существа и предметы =====================

def test_creature_selection():
    from units.Map.GameMap import random_creature_selection
    random.seed(1)
    picks = [random_creature_selection() for _ in range(300)]
    assert any(p is None for p in picks)
    assert any(p is not None for p in picks), "существа должны иногда выпадать"


def test_creature_selection_biome_diversity():
    """Разные биомы должны давать разный набор мобов вместо одного пула на
    весь мир: пустыня — скорпионы, тундра/тайга — волки, тропики — змеи."""
    from units.Map.GameMap import random_creature_selection
    from units.Objects.Creatures import Scorpion, Wolf, Snake, Imp

    random.seed(2)
    desert_picks = {random_creature_selection(0, 0) for _ in range(500)}
    assert Scorpion in desert_picks

    tundra_picks = {random_creature_selection(0, 3) for _ in range(500)}
    assert Wolf in tundra_picks

    tropical_picks = {random_creature_selection(0, 2) for _ in range(500)}
    assert Snake in tropical_picks

    # глубина ада (tile_y) сильнее биома — там водятся бесы независимо от биома
    from units.common import START_HELL_Y
    hell_picks = {random_creature_selection(START_HELL_Y + 10, 0) for _ in range(500)}
    assert Imp in hell_picks
    assert Scorpion not in hell_picks


def test_new_creatures_registered_and_spawnable():
    """10 новых существ (заяц, олень, лиса, кабан, верблюд, пингвин, краб,
    летучая мышь, голем, пришелец) должны быть в общем реестре и появляться
    в подходящих для них зонах/биомах."""
    from units.Map.GameMap import random_creature_selection
    from units.Objects.Creatures import (CREATURES_D, Rabbit, Deer, Fox, Boar, Camel, Penguin,
                                         Crab, Bat, StoneGolem, SpaceDrifter)
    from units.common import START_HELL_Y, START_SPACE_Y, BOTTOM_MIDDLE_WORLD

    new_creatures = [Rabbit, Deer, Fox, Boar, Camel, Penguin, Crab, Bat, StoneGolem, SpaceDrifter]
    for cls in new_creatures:
        assert CREATURES_D[cls.__name__] is cls

    random.seed(3)
    assert Camel in {random_creature_selection(0, 0) for _ in range(500)}  # пустыня
    assert Rabbit in {random_creature_selection(0, 1) for _ in range(500)}  # саванна
    assert {Deer, Penguin} & {random_creature_selection(0, 3) for _ in range(1000)}  # тундра
    assert Crab in {random_creature_selection(0, 2) for _ in range(1000)}  # тропики
    assert {Fox, Boar} & {random_creature_selection(0, 4) for _ in range(1000)}  # лес
    assert {Bat, StoneGolem} & {random_creature_selection(BOTTOM_MIDDLE_WORLD + 50, 0) for _ in range(1000)}
    assert SpaceDrifter in {random_creature_selection(START_SPACE_Y - 10, None) for _ in range(200)}
    assert random_creature_selection(START_HELL_Y + 10, 0) is not None or True  # ад не должен падать


def test_creature_spawn_creates_valid_object():
    """Каждое новое существо должно создаваться без ошибок и иметь спрайт."""
    from units.Objects.Creatures import Rabbit, Deer, Fox, Boar, Camel, Penguin, Crab, Bat, StoneGolem, SpaceDrifter
    game = fresh_world(25)
    for cls in (Rabbit, Deer, Fox, Boar, Camel, Penguin, Crab, Bat, StoneGolem, SpaceDrifter):
        creature = cls(game, (0, -64))
        assert creature.sprite is not None
        assert creature.sprite.get_width() > 0 and creature.sprite.get_height() > 0


def test_plants_defined_for_all_biomes():
    """Все 10 биомов (units.biomes.biome_names) должны иметь собственный
    набор растений, а не молча падать на дефолт (None)."""
    from units.biomes import biome_names
    from units.Tiles import biomes_plants_chance
    for biome_id in range(len(biome_names)):
        assert biome_id in biomes_plants_chance, biome_names[biome_id]


def test_creature_spawn_and_chunk_counter():
    from units.common import OBJ_CREATURE
    from units.Objects.Creatures import Slime
    game = fresh_world(7)
    gm = game.game_map
    s = Slime(game, (0, -64))
    assert s.class_obj & OBJ_CREATURE
    chunk = gm.chunk(s.chunk_pos, create_chunk=True)
    before = chunk[3][1]
    assert gm.add_dinamic_obj(*s.chunk_pos, s)
    assert chunk[3][1] == before + 1
    assert gm.del_dinamic_obj(*s.chunk_pos, s)
    assert chunk[3][1] == before


def test_map_add_item():
    game = fresh_world(7)
    gm = game.game_map
    chunk = gm.chunk((0, 0), create_chunk=True)
    before = len(chunk[1])
    gm.add_item_of_index(2, 3, 5, 5)  # 3 куска земли в тайл (5,5)
    assert len(chunk[1]) == before + 1


def test_mouse_aim_matches_world_scale():
    """Клик мышью (в реальных экранных координатах) должен целиться в мир с
    учётом WORLD_SCALE — иначе на широких экранах (мир меньше экрана) копка
    и постройка блоков будут промахиваться."""
    import pygame
    import units.common as common
    game = fresh_world(3)
    p = game.player
    p.active = True
    scroll = game.screen_map.scroll
    vp = pygame.Vector2(p.rect.center)
    vector_player_display = vp - pygame.Vector2(scroll)

    captured = {}
    p.tool.right_button_click = lambda vtm: captured.setdefault("vtm", pygame.Vector2(vtm)) or True

    real_pos = (777, 333)
    expected = pygame.Vector2(common.screen_to_world_pos(real_pos)) - vector_player_display
    p.pg_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=real_pos, button=3))
    assert (expected - captured["vtm"]).length() < 0.01

    if common.WORLD_SCALE != (1, 1):
        assert real_pos != tuple(expected), \
            "при уменьшенном мире экранные и мировые координаты должны отличаться"


# ===================== рендер =====================

def test_inventory_cell_matches_the_on_screen_block():
    """Ячейка инвентаря и хотбара должна быть примерно с блок, каким игрок
    видит его на экране.

    Раньше она считалась от МИРОВОГО TSIZE и от разрешения не зависела вовсе,
    хотя мир масштабируется из WSIZE в SCREEN_SIZE: на узком экране ячейка
    выходила крупнее блока, на широком — мельче.
    """
    import units.common as common
    from units.UI.InventoryUI import compute_cell_size
    get_app()
    for w, h in ((1366, 768), (1920, 1080), (2560, 1440), (3440, 1440)):
        wsize = common._compute_wsize((w, h))
        block = common.TSIZE * w / wsize[0]
        cell = max(16, int(block * common.UI_CELL_SCALE))
        assert abs(cell - block * common.UI_CELL_SCALE) < 1, f"{w}x{h}: ячейка {cell} против блока {block}"
    # 2560x1440 — эталон из запроса: на "нормальном" ячейка равна блоку
    wsize = common._compute_wsize((2560, 1440))
    block = common.TSIZE * 2560 / wsize[0]
    assert round(block) == 51, f"блок на 2560x1440 должен быть 51 px, а не {block}"
    assert compute_cell_size() == max(16, int(common.screen_tile_size() * common.UI_CELL_SCALE))


def test_menu_size_auto_does_not_count_resolution_twice():
    """У ячейки "авто" — это 1.0, а не эвристика от ширины экрана: ячейка уже
    привязана к экранному размеру блока и подстраивается сама."""
    import units.common as common
    from units import config
    assert common._MENU_SIZE_SCALE["medium"] == 1.0
    if config.Window.menu_size not in common._MENU_SIZE_SCALE:
        assert common.UI_CELL_SCALE == 1.0, "в режиме 'авто' ячейка не должна масштабироваться повторно"


def test_inventory_cell_follows_window_resize():
    """После растягивания окна ячейка обязана пересчитаться: она привязана к
    экранному размеру блока, а тот от размера окна и зависит."""
    import units.common as common
    from units.UI import InventoryUI as inv_mod
    game = fresh_world(12)
    ui = game.player.inventory.ui
    old_screen = tuple(common.SCREEN_SIZE)
    old_cell = ui.cell_size
    try:
        common.apply_resize((old_screen[0] * 2, old_screen[1] * 2))
        ui.relayout()
        assert ui.cell_size == inv_mod.compute_cell_size()
        assert ui.cell_size > old_cell, f"ячейка не выросла вместе с окном: {old_cell} -> {ui.cell_size}"
        # таблица и хотбар пересобраны под новую ячейку, а не остались старыми
        assert ui.work_inventory.rect.h == ui.cell_size
        ui.redraw_top()
    finally:
        common.apply_resize(old_screen)
        ui.relayout()


def test_world_screen_split():
    """Мир (game.display) может быть меньше экрана (game.screen) — HUD/меню
    рисуются на экране напрямую (для чёткости текста), а blit_world должен
    растягивать мир на экран без падений, при любом соотношении размеров."""
    game = fresh_world(11)
    assert game.display.get_size() == game.ui.display.get_size()
    game.ui.blit_world()  # не должен падать при любом соотношении размеров
    # HUD-виджеты (хотбар/сообщения) должны быть в разрешении экрана, не мира
    assert game.player.inventory.ui.get_size() == game.screen.get_size()


def test_view_tiles_width_setting():
    """WSIZE подбирается так, чтобы по ширине экрана было видно ровно
    config.Window.view_tiles_width тайлов (не больше SCREEN_SIZE - иначе
    был бы апскейл/блюр вместо честного даунскейла)."""
    import units.common as common
    import units.config as config
    win = config.Window
    expected_w = min(max(10, win.view_tiles_width) * common.TSIZE, common.SCREEN_SIZE[0])
    assert common.WSIZE[0] == expected_w
    assert common.WSIZE[0] <= common.SCREEN_SIZE[0]
    assert common.WSIZE[1] <= common.SCREEN_SIZE[1]


def test_apply_resize_updates_screen_size_and_scale():
    """apply_resize — единая точка входа для живого ресайза/F11: должна
    пересоздать screen_, обновить SCREEN_SIZE/WORLD_SCALE по месту (не
    трогая WSIZE — мир пересчитывать не нужно, см. common.py) и сохранить
    новый размер в конфиг, если это не полноэкранный режим."""
    import units.common as common
    get_app()
    orig_size = tuple(common.SCREEN_SIZE)
    # fullscreen кwarg не передаём ни на ресайз, ни на восстановление — он
    # уже False/не менялся, а apply_resize(fullscreen=...) при каждом
    # непустом значении перезаписывает settings.ini (str(bool) вместо
    # исходного "Off"/"On" из ini) без реальной необходимости
    try:
        wsize_before = tuple(common.WSIZE)
        common.apply_resize((640, 480))
        assert tuple(common.SCREEN_SIZE) == (640, 480)
        assert tuple(common.WSIZE) == wsize_before, "WSIZE не должен меняться при ресайзе окна"
        assert common.WORLD_SCALE == (common.WSIZE[0] / 640, common.WSIZE[1] / 480)
        assert common.config.Window.size == "640,480"
    finally:
        common.apply_resize(orig_size)
    assert tuple(common.SCREEN_SIZE) == orig_size


def test_relayout_matches_screen_size_after_resize():
    """После apply_resize+relayout меню (титульный экран/пауза/настройки)
    должны занимать актуальный self.screen.get_size(), а не устаревший
    размер, посчитанный один раз при создании сцены (баг «меню в углу»)."""
    import units.common as common
    app = get_app()
    orig_size = tuple(common.SCREEN_SIZE)
    try:
        common.apply_resize((900, 640))
        new_size = tuple(common.SCREEN_SIZE)

        app.title_scene.title_ui.relayout()
        assert app.title_scene.title_ui.rect.size == new_size

        app.title_scene.settings_ui.relayout()
        assert app.title_scene.settings_ui.rect.size == new_size

        app.pause_scene.ui.relayout()
        assert app.pause_scene.ui.rect.center == (new_size[0] // 2, new_size[1] // 2)
    finally:
        common.apply_resize(orig_size)


def test_game_frame_renders():
    game = fresh_world(10)
    game.elapsed_time = 16
    game.pg_events()
    game.update()
    sm = game.screen_map
    assert sm.static_tiles, "после кадра должны быть зарегистрированы коллизии"


def test_offscreen_tiles_registered_for_collisions():
    from units.common import TSIZE, WSIZE
    game = fresh_world(10)
    game.elapsed_time = 16
    game.pg_events()
    game.update()
    sm = game.screen_map
    # тайлы за пределами экрана (но в окне чанков) должны попадать в коллизии
    sx0, sx1 = sm.scroll[0], sm.scroll[0] + WSIZE[0]
    assert any(tx * TSIZE > sx1 or (tx + 1) * TSIZE < sx0
               for tx, ty in sm.static_tiles), \
        "существа за экраном должны стоять на блоках"


# ===================== UI =====================

def test_keyboard_nav():
    import pygame
    from units.UI.Button import Button, KeyboardNav, createImagesButton
    get_app()
    clicked = []
    imgs = createImagesButton((50, 20), "t")
    btns = [Button(lambda b, i=i: clicked.append(i), (0, i * 30, 50, 20), *imgs)
            for i in range(3)]
    nav = KeyboardNav(btns)
    down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, unicode="")
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")
    assert nav.pg_event(down)
    assert nav.pg_event(down)
    assert btns[1].mauseInButton, "вторая кнопка должна подсветиться"
    assert nav.pg_event(enter)
    assert clicked == [1]


def test_world_list_ui():
    app = get_app()
    from units.Map import WorldStorage as WS
    meta = WS.new_world_meta()
    with open(WS.data_path(meta["id"]), "wb") as f:
        f.write(b"d")
    try:
        ui = app.worlds_scene.ui
        ui.reload_worlds()
        assert any(w["id"] == meta["id"] for w in ui.worlds)
        ui.draw()  # не должен падать
        ui.scroll(-40)
        ui.scroll(999)
    finally:
        WS.delete_world(meta["id"])


def test_tutorial_world_and_steps():
    from units.common import TSIZE
    from units.Objects.Items import ItemsTile
    app = get_app()
    from units.Map import WorldStorage
    game = app.game_scene
    random.seed(42)

    game.game_map.new_world(tutorial=True)
    gm = game.game_map
    assert gm.tutorial_step == 0
    assert gm.world_meta.get("tutorial")
    assert gm.world_meta["name"], "у мира обучения должно быть имя"
    gm.save_current_game_map()
    assert WorldStorage.find_tutorial_world()["id"] == gm.world_id

    # сундук с припасами создан и запомнен в состоянии мира
    chest_pos = gm.tutorial_state.get("chest_pos")
    assert chest_pos, "мир обучения должен создать сундук с припасами"
    chest_tile = gm.get_static_tile(*chest_pos)
    assert chest_tile[0] == 129
    chest = gm.get_tile_obj(*gm.to_chunk_xy(*chest_pos), chest_tile[3])
    from units.Tutorial import count_in_inventory
    assert count_in_inventory(chest.inventory, 66) >= 2, "в сундуке должны быть рубины для зелий"

    tut = game.tutorial
    tut.__init__(game)  # свежий трекинг
    inv = _empty_inventory(game)
    game.player.blocks_placed_count = 0
    tut.update()  # показывает первую подсказку, шаг не двигается
    assert gm.tutorial_step == 0
    tut.draw_hud(game.screen)  # панель задачи рисуется без падений
    assert tut._task_surf is not None

    # шаг 0: движение + прыжок (события запоминаются в состоянии мира)
    game.player.rect.x += TSIZE * 6
    gm.tutorial_state["seen_jump"] = True
    tut.update()
    assert gm.tutorial_step == 1

    # шаг 1: выбор ячейки хотбара
    gm.tutorial_state["seen_cell"] = True
    tut.update()
    assert gm.tutorial_step == 2

    # шаг 2: добыть 3 дерева; маркер находит ближайший ствол
    px, py = game.player.rect.centerx // TSIZE, game.player.rect.centery // TSIZE
    gm.set_static_tile(px + 3, py, 110)
    game.elapsed_time = 16
    game.pg_events()
    game.update()  # заполняет static_tiles для поиска цели
    tut.update()
    assert tut.target_tile is not None, "маркер должен найти ствол дерева"
    inv.put_to_inventory(ItemsTile(game, 12, count=2))
    tut.update()
    assert gm.tutorial_step == 2, "двух брёвен мало — нужно 3"
    inv.put_to_inventory(ItemsTile(game, 12, count=1))
    tut.update()
    assert gm.tutorial_step == 3
    assert game.player.achievements.is_completed("tutorial_wood")
    tut.draw_world(game.display)  # маркер — не должен падать
    tut.draw_hud(game.screen)
    assert tut._task_text is not None

    # шаг 3: инвентарь
    gm.tutorial_state["seen_inventory"] = True
    tut.update()
    assert gm.tutorial_step == 4
    # шаг 4: доски (2 шт — один крафт)
    inv.put_to_inventory(ItemsTile(game, 11, count=2))
    tut.update()
    assert gm.tutorial_step == 5
    # шаг 5: блоки
    game.player.blocks_placed_count = 5
    tut.update()
    assert gm.tutorial_step == 6
    # шаг 6: стол — касание верстака
    game.player.collisions_ttile = {121}
    tut.update()
    assert gm.tutorial_step == 7
    # шаг 7: припасы из сундука — маркер ведёт к нему
    assert tuple(tut.target_tile) == tuple(chest_pos), "маркер должен вести к сундуку"
    inv.put_to_inventory(ItemsTile(game, 66, count=2))
    tut.update()
    assert gm.tutorial_step == 8
    # шаги 8-9: печка и котёл
    game.player.collisions_ttile = {131}
    tut.update()
    assert gm.tutorial_step == 9
    game.player.collisions_ttile = {125}
    tut.update()
    assert gm.tutorial_step == 10
    # шаги 10-12: ведро, вода, зелье. Котёл стал машиной с тремя ячейками, и
    # без этих шагов игрок кладёт ягоды в топливо.
    from units.Tools import TOOLS
    inv.put_to_inventory(TOOLS[410](game))
    tut.update()
    assert gm.tutorial_step == 11, "шаг с ведром не закрылся"
    inv.get_from_inventory(410, 1)
    inv.put_to_inventory(TOOLS[411](game))
    tut.update()
    assert gm.tutorial_step == 12, "шаг с набором воды не закрылся"
    # финальный шаг закрывается сам
    inv.put_to_inventory(ItemsTile(game, 351, count=1))
    tut.update()
    tut.update()
    assert gm.tutorial_step == -1, "обучение должно завершиться"
    for ach in ("tutorial_craft", "tutorial_builder", "tutorial_workbench",
                "tutorial_supplies", "tutorial_furnace", "tutorial_cauldron",
                "tutorial_bucket", "tutorial_water",
                "tutorial_potion", "tutorial_done"):
        assert game.player.achievements.is_completed(ach), f"нет достижения {ach}"

    # прогресс и состояния сохраняются вместе с миром
    wid = gm.world_id
    gm.save_current_game_map()
    game.game_map.new_world()  # обычный мир — обучение неактивно
    assert gm.tutorial_step == -1
    assert not gm.tutorial_state
    gm.open_game_map(game, wid)
    assert gm.tutorial_step == -1  # завершённое обучение не перезапускается
    assert tuple(gm.tutorial_state.get("chest_pos")) == tuple(chest_pos), \
        "состояния обучения должны сохраняться с миром"

    WorldStorage.delete_world(wid)
    assert WorldStorage.find_tutorial_world() is None, "мир обучения удаляем как обычный"


def test_audio_optional():
    """Игра без аудиоустройства (WSL/сервер) не должна падать на звуке."""
    get_app()
    from units import sound
    # заглушки безопасны и поддерживают всю цепочку вызовов
    ch = sound._DummySound().play(loops=-1)
    ch.set_endevent(1)
    ch.set_volume(0.5)
    ch.stop()
    assert ch.get_busy() is False
    # при отключённом аудио load_sound/load_sounds возвращают заглушки
    orig = sound.AUDIO_ENABLED
    sound.AUDIO_ENABLED = False
    try:
        assert isinstance(sound.load_sound("data/audio/UI/click.wav"), sound._DummySound)
        lst = sound.load_sounds("data/audio/UI/click.wav", 2, 0)
        assert all(isinstance(s, sound._DummySound) for s in lst)
    finally:
        sound.AUDIO_ENABLED = orig


def test_help_ui():
    import pygame
    app = get_app()
    ui = app.help_scene.ui
    assert ui.content.get_height() > 200, "контент справки должен отрисоваться"
    ui.draw()  # не должен падать
    before = ui.scroll_y
    ui.pg_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-3))
    assert ui.scroll_y > before, "прокрутка колесом должна работать"
    ui.pg_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP, unicode=""))
    assert ui.scroll_y == 0


# ===================== конфиг =====================

def test_settings_ui_view_tiles_dropdown():
    """Настройка 'Обзор (блоков в ширину)' должна строиться без падений и
    сохранять выбор через config.Window.set_view_tiles_width.

    Живёт в разделе «Экран и производительность»: в основном меню оставлены
    только размер меню и режим экрана (см. MainSettingsUI).
    """
    from units import config as cfg
    app = get_app()
    ui = app.title_scene.screen_settings_ui
    ui.draw()  # не должен падать
    dd = next(d for d in ui.dropdowns if "Обзор" in d.label)
    assert str(cfg.Window.view_tiles_width) == dd.options[dd.index]
    old = cfg.Window.view_tiles_width
    try:
        new_value = 40 if old != 40 else 50
        dd.on_select(str(new_value), dd.options.index(str(new_value)))
        assert cfg.Window.view_tiles_width == new_value
    finally:
        cfg.Window.set_view_tiles_width(old)


def test_config_values():
    from units import config as cfg
    from units.common import FPS
    assert isinstance(cfg.GameSettings.max_fps, int)
    assert FPS == cfg.GameSettings.max_fps
    assert cfg.GameSettings.language in cfg.GameSettings.all_languages


# ===================== моды =====================

def _write_mod(tmpdir, name, manifest):
    """Создать папку мода с mod.json и вернуть корень для load_mods()."""
    import json
    import os
    mod_dir = os.path.join(tmpdir, name)
    os.makedirs(mod_dir, exist_ok=True)
    with open(os.path.join(mod_dir, "mod.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    return tmpdir


def test_mods_example_mod_registered():
    """Мод из data/modifications должен зарегистрироваться в тех же
    структурах, что и ванильные блоки: спрайт, имя, прочность, копаемость,
    крафт и выпадение предметов."""
    get_app()
    from units import mods, Tiles
    from units.creating_items import RECIPES
    assert mods.MODS, "пример мода должен загружаться"
    assert not mods.MOD_ERRORS, f"пример мода не должен давать ошибок: {mods.MOD_ERRORS}"

    for spec in mods.mod_blocks():
        idx = spec["id"]
        assert idx in Tiles.tile_imgs
        assert idx in Tiles.tile_words and Tiles.tile_words[idx]
        # ScreenMap индексирует TILES_SOLIDITY напрямую — обязателен
        assert idx in Tiles.TILES_SOLIDITY
        assert idx in Tiles.iron_capability, "мод-блок должен быть копаемым"
        assert idx in Tiles.tile_hand_imgs, "нужна иконка для инвентаря"
        assert idx in Tiles.all_tiles

    recipe_ids = {r[0][0] for r in RECIPES}
    assert any(s["id"] in recipe_ids for s in mods.mod_blocks() if s["recipe"]), \
        "рецепты мода должны попадать в общий список крафта"


def test_mods_creature_registered_and_picklable():
    """Существо мода строится на базе ванильного класса и должно
    пиклиться: сохранение мира пиклит сам класс существа."""
    import pickle
    get_app()
    from units.Objects.Creatures import MOD_CREATURES, CREATURES, CREATURES_D
    assert MOD_CREATURES, "пример мода добавляет существо"
    for cls, spec in MOD_CREATURES:
        assert cls in CREATURES and CREATURES_D[cls.__name__] is cls
        assert cls.max_lives == spec["lives"]
        # динамический класс должен быть доступен как атрибут модуля,
        # иначе pickle не восстановит его при загрузке мира
        assert pickle.loads(pickle.dumps(cls)) is cls


def test_mods_creature_spawns_alongside_vanilla():
    """Существа мода ДОБАВЛЯЮТСЯ к ванильному пулу спавна, а не заменяют
    его — иначе мод выключил бы обычных мобов в своём биоме."""
    get_app()
    from units.Map.GameMap import random_creature_selection
    from units.Objects.Creatures import MOD_CREATURES, Slime
    cls, spec = MOD_CREATURES[0]
    biome = spec["biomes"][0] if spec["biomes"] else 1
    picks = {random_creature_selection(0, biome) for _ in range(2000)}
    assert cls in picks, "существо мода должно попадать в жеребьёвку своего биома"
    assert Slime in picks, "ванильные мобы должны остаться в том же биоме"


def test_mods_animated_tile_frames_advance():
    """Анимированный блок мода подменяет кадр прямо в tile_imgs (ScreenMap
    читает его заново каждый кадр и не кэширует поверхности чанков)."""
    get_app()
    from units import mods, Tiles
    # реестр общий для ванильных тайлов (лава) и модов — см. units/Tiles.py
    assert Tiles.ANIMATED_TILES, "должны быть анимированные тайлы (лава и блок мода)"
    mod_animated = {i for i in Tiles.ANIMATED_TILES if i >= mods.MOD_ID_MIN}
    assert mod_animated, "пример мода содержит анимированный блок"
    tile_id = next(iter(mod_animated))
    anim = Tiles.ANIMATED_TILES[tile_id]
    seen = set()
    for tact in range(anim["fps"] * 2):
        mods.update_tile_animations(Tiles.tile_imgs, tact, Tiles.ANIMATED_TILES)
        seen.add(id(Tiles.tile_imgs[tile_id]))
    assert len(seen) == len(anim["frames"]), \
        f"должны прокрутиться все {len(anim['frames'])} кадров, а прокрутилось {len(seen)}"


def test_mods_broken_mod_does_not_crash_game():
    """Сломанный мод обязан быть пропущен с понятной ошибкой, а не
    уронить игру: иначе один плохой мод делает игру незапускаемой."""
    import tempfile
    get_app()
    from units import mods
    saved_mods, saved_errors = list(mods.MODS), list(mods.MOD_ERRORS)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _write_mod(tmp, "no_json", {})            # перезапишем ниже
            import os
            os.remove(os.path.join(tmp, "no_json", "mod.json"))
            _write_mod(tmp, "bad_id", {"name": "плохой id",
                                       "blocks": [{"id": 3, "name": "Камень?", "color": "#fff"}]})
            _write_mod(tmp, "bad_color", {"name": "плохой цвет",
                                          "blocks": [{"id": 9001, "name": "X", "color": "не цвет"}]})
            _write_mod(tmp, "empty", {"name": "пустой"})
            _write_mod(tmp, "ok", {"name": "рабочий",
                                   "blocks": [{"id": 9100, "name": "Хороший", "color": "#123456"}]})
            loaded, errors = mods.load_mods(tmp)
            names = {m["name"] for m in loaded}
            assert names == {"рабочий"}, f"должен загрузиться только рабочий мод, а не {names}"
            broken = {folder for folder, _msg in errors}
            assert broken == {"no_json", "bad_id", "bad_color", "empty"}, broken
            # у базовой игры id 3 — камень; мод не должен его переопределить
            assert all("id 3" in msg or "id" in msg for folder, msg in errors if folder == "bad_id")
    finally:
        mods.MODS[:], mods.MOD_ERRORS[:] = saved_mods, saved_errors


def test_mods_sprite_path_cannot_escape_mod_dir():
    """Путь к спрайту не должен выводить за папку мода (../../ и т.п.)."""
    import tempfile
    get_app()
    from units import mods
    saved_mods, saved_errors = list(mods.MODS), list(mods.MOD_ERRORS)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _write_mod(tmp, "escape", {"name": "побег", "blocks": [
                {"id": 9200, "name": "Побег", "sprite": "../../../settings.ini"}]})
            loaded, errors = mods.load_mods(tmp)
            assert not loaded
            assert any("выходит за пределы" in msg for _f, msg in errors), errors
    finally:
        mods.MODS[:], mods.MOD_ERRORS[:] = saved_mods, saved_errors


def test_mods_disabled_by_setting():
    """Выключение модов в настройках должно полностью пропускать загрузку."""
    get_app()
    from units import mods, config as cfg
    saved_mods, saved_errors = list(mods.MODS), list(mods.MOD_ERRORS)
    was_enabled = cfg.ModSettings.enabled
    try:
        cfg.ModSettings.enabled = False
        loaded, errors = mods.load_mods()
        assert loaded == [] and errors == []
    finally:
        cfg.ModSettings.enabled = was_enabled
        mods.MODS[:], mods.MOD_ERRORS[:] = saved_mods, saved_errors


# ===================== сюжет и структуры =====================

def test_structure_builder_ascii():
    """Схема собирается в тот же формат, что у старых структур, прочность
    берётся из TILES_SOLIDITY, а не задаётся руками."""
    get_app()
    from units.Map.structure_builder import build_ascii, StructureError
    from units.Tiles import TILES_SOLIDITY
    size, array = build_ascii([
        "..#..",
        "..C..",
    ])
    assert size == (5, 2)
    assert len(array) == 10
    assert array[0] == [150, TILES_SOLIDITY.get(150, -1), 0, 0]   # '.' — пустота
    assert array[2] == [31, TILES_SOLIDITY[31], 0, 0]             # '#' — кирпич
    assert array[7] == [129, TILES_SOLIDITY.get(129, -1), 0, 0]   # 'C' — сундук

    # цифра ставит плиту нужного варианта (кадр тайла)
    _size, arr = build_ascii(["3"])
    assert arr[0][0] == 300 and arr[0][2] == 3

    for bad, why in ((["##", "#"], "разная длина строк"),
                     ([], "пустая схема"),
                     (["#?#"], "неизвестный символ")):
        try:
            build_ascii(bad)
        except StructureError:
            pass
        else:
            raise AssertionError(f"должно падать: {why}")


def test_biome_structures_registered():
    """10 новых структур попали в жеребьёвку своей зоны (веса считались до
    слияния — легко забыть пересчитать) и имеют корректные биомы."""
    get_app()
    from units.Map.Structures import Structures_chance, Structures_all
    from units.Map.StructuresBiome import Structures_biome_middleworld
    assert len(Structures_biome_middleworld) == 10
    ids, weights = Structures_chance["middleworld"]
    for build_id, build in Structures_biome_middleworld.items():
        assert build_id in ids, f"{build[0]} не попал в жеребьёвку"
        assert build_id in Structures_all
        biomes = build[3]
        assert biomes is None or (biomes and all(0 <= b <= 9 for b in biomes)), build[0]
        (w, h), array = build[2][0], build[2][1]
        assert len(array) == w * h, f"{build[0]}: размер не совпадает с числом ячеек"
    assert len(ids) == len(weights)


def test_structure_points_use_height_not_width():
    """У левого-нижнего угла структуры должна прибавляться высота, а не
    ширина: иначе у невысоких широких построек регистрируется не тот
    чанк-триггер и постройка не появляется при подходе с той стороны."""
    get_app()
    game = fresh_world(31)
    gm = game.game_map
    gm.structures.clear()
    gm.structures_lst.clear()
    structure = gm.get_structure_dict(0, 0)
    assert gm.structures_lst, "в блоке структур должна появиться хотя бы одна постройка"
    from units.Map.Structures import Structures_all
    for _idx, build_id, points in gm.structures_lst:
        size = Structures_all[build_id][2][0]
        lt, rt, lb, rb = points
        assert rt[0] - lt[0] == size[0], "правый-верхний смещён на ширину"
        assert lb[1] - lt[1] == size[1], "левый-нижний должен быть смещён на ВЫСОТУ"
        assert rb == (lt[0] + size[0], lt[1] + size[1])
    assert structure is gm.structures[(0, 0)]


def test_biome_structure_only_in_its_biome():
    """Структура с указанными биомами не должна выпадать в чужом биоме."""
    get_app()
    game = fresh_world(32)
    gm = game.game_map
    from units.Map.Structures import Structures

    zone = Structures["middleworld"]
    # найдём структуру, привязанную к единственному биому
    target_id, target = next((i, b) for i, b in zone.items()
                             if len(b) > 3 and b[3] is not None and len(b[3]) == 1)
    allowed = target[3][0]
    import units.Map.GameMap as gmod
    wrong = next(b for b in range(9) if b != allowed)
    saved = gmod.biome_of_pos
    try:
        gmod.biome_of_pos = lambda x, y, _c=None: (wrong, 0, 0)
        picks = {gm._pick_structure("middleworld", (0, 0)) for _ in range(400)}
        assert target_id not in picks, f"{target[0]} выпала в биоме {wrong}, а разрешён {allowed}"
        gmod.biome_of_pos = lambda x, y, _c=None: (allowed, 0, 0)
        picks = {gm._pick_structure("middleworld", (0, 0)) for _ in range(400)}
        assert target_id in picks, f"{target[0]} не выпала в своём биоме {allowed}"
    finally:
        gmod.biome_of_pos = saved


def test_lore_tablet_reads_inscription_and_fills_journal():
    """Плита отдаёт надпись по своему варианту и пополняет журнал мира;
    журнал сохраняется вместе с миром."""
    game = fresh_world(33)
    gm = game.game_map
    from units.Lore import TABLET_VARIANTS, get_inscription
    gm.set_static_tile(6, 6, [300, 90, 2, 0])
    tile = gm.get_static_tile(6, 6)
    obj = gm.get_tile_obj(*gm.to_chunk_xy(6, 6), tile[3])
    assert obj is not None and obj.index == 300
    assert obj.variant == 2
    assert obj.inscription_id() == TABLET_VARIANTS[2]
    title, lines = obj.inscription()
    assert title and lines
    assert (title, lines) == get_inscription(TABLET_VARIANTS[2])

    assert gm.read_inscriptions == []
    obj.right_click((0, 0))
    assert gm.read_inscriptions == [TABLET_VARIANTS[2]]
    # повторное чтение не должно дублировать запись в журнале
    assert gm.mark_inscription_read(TABLET_VARIANTS[2]) is False
    assert gm.read_inscriptions == [TABLET_VARIANTS[2]]
    # интерфейс чтения открылся и рисуется без падений
    ui = game.blocks_ui_manager.blocks_ui[300]
    assert ui.opened
    ui.draw(game.screen)


def test_lore_unknown_variant_is_not_crash():
    """Мир мог быть создан версией с другим списком надписей — неизвестный
    вариант должен дать стёртую плиту, а не уронить игру."""
    get_app()
    from units.Lore import inscription_by_variant, get_inscription
    assert inscription_by_variant(9999) == ""
    assert inscription_by_variant(-1) == ""
    title, lines = get_inscription("нет такой надписи")
    assert title and lines


def test_story_state_saved_with_world():
    """Состояние арки живёт в мире и переживает сохранение/загрузку —
    тем же приёмом, что состояние обучения."""
    game = fresh_world(34)
    gm = game.game_map
    # в новом мире арка не начата; altar_pos ставится самой генерацией
    assert gm.story_stage == 0
    assert "altar_read" not in gm.story_state
    assert gm.read_inscriptions == []
    gm.story_stage = 2
    gm.story_state["altar_read"] = True
    gm.mark_inscription_read("altar")
    gm.save_current_game_map()
    wid = gm.world_id

    gm.new_world(base_generation=1234)
    assert gm.story_stage == 0
    assert "altar_read" not in gm.story_state
    assert gm.read_inscriptions == []
    game.game_map.open_game_map(game, wid)
    gm = game.game_map
    assert gm.story_stage == 2
    assert gm.story_state.get("altar_read") is True
    assert "altar" in gm.read_inscriptions


def test_altar_tablet_placed_in_every_new_world():
    """Плита алтаря — точка входа в сюжет, поэтому она должна стоять в
    каждом новом мире у спавна и на твёрдом блоке, а не зависеть от того,
    повезёт ли игроку найти структуру."""
    game = fresh_world(35)
    gm = game.game_map
    pos = gm.story_state.get("altar_pos")
    assert pos, "позиция алтаря должна запоминаться в состоянии сюжета"
    tile = gm.get_static_tile(*pos)
    assert tile[0] == 300, "у спавна должна стоять плита с надписью"
    assert tile[2] == 0, "на алтаре — надпись варианта 0 (altar)"
    assert gm.get_static_tile_type(pos[0], pos[1] + 1) != 0, "плита должна стоять на блоке"
    obj = gm.get_tile_obj(*gm.to_chunk_xy(*pos), tile[3])
    assert obj.inscription_id() == "altar"


# ===================== пиксель-арт существ =====================

def test_pixel_art_builder():
    """Сетка собирается 1:1, палитра привязана к базовому цвету, а
    неровная сетка отвергается (опечатку в строке легко не заметить)."""
    get_app()
    from units.Graphics.PixelArt import build_sprite, palette, shade, PixelArtError
    s = build_sprite(["BK", ".e"], base="#204080")
    assert s.get_size() == (2, 2)
    assert s.get_at((0, 0))[:3] == (0x20, 0x40, 0x80), "B — базовый цвет"
    assert s.get_at((1, 0))[:3] == (28, 25, 23), "K — обводка"
    assert s.get_at((0, 1))[3] == 0, "'.' — прозрачный пиксель"

    # оттенки должны идти по яркости: тень < средний < базовый < блик
    pal = palette("#808080")

    def brightness(c):
        return sum(tuple(c)[:3])

    assert brightness(pal['D']) < brightness(pal['M']) < brightness(pal['B']) < brightness(pal['L'])
    assert shade("#808080", 0.5)[0] == 64, "затемнение"
    assert shade("#808080", 2)[0] == 255, "осветление должно ограничиваться 255"

    # масштабирование даёт запрошенный размер и не мылит (nearest)
    big = build_sprite(["BK"], base="#204080", size=(4, 2))
    assert big.get_size() == (4, 2)
    assert big.get_at((0, 0))[:3] == big.get_at((1, 0))[:3]

    for bad in (["BB", "B"], [], ["B?B"]):
        try:
            build_sprite(bad)
        except PixelArtError:
            pass
        else:
            raise AssertionError(f"должно падать: {bad}")


def test_biome_tint_paints_grass_not_earth():
    """Цвет биома относится к траве. Накладка заливала тайл целиком, и в
    лесных биомах «земля с травой» зеленела вся — вместе с землёй под дёрном."""
    from units.Tiles import ground_imgs, _is_grass_pixel
    get_app()
    base_set = ground_imgs[None]
    for biome_id in (4, 5, 6, 7, 8):
        for base, tinted in zip(base_set, ground_imgs[biome_id]):
            grass_changed = earth_changed = 0
            for y in range(base.get_height()):
                for x in range(base.get_width()):
                    b, c = base.get_at((x, y)), tinted.get_at((x, y))
                    if (b.r, b.g, b.b) == (c.r, c.g, c.b):
                        continue
                    if _is_grass_pixel(b.r, b.g, b.b, b.a):
                        grass_changed += 1
                    else:
                        earth_changed += 1
            assert earth_changed == 0, \
                f"биом {biome_id}: перекрашено {earth_changed} пикселей земли"
            assert grass_changed > 0, f"биом {biome_id}: трава не перекрашена вовсе"


def test_grass_mask_separates_turf_from_soil():
    """Маска должна разделять дёрн и землю по пикселю, а не по номеру строки:
    в спрайте граница неровная — на правом краю земля начинается выше."""
    from units.Tiles import _is_grass_pixel
    assert _is_grass_pixel(96, 178, 49, 255), "зелень дёрна — трава"
    assert _is_grass_pixel(46, 135, 43, 255)
    assert not _is_grass_pixel(104, 73, 55, 255), "коричневая земля — не трава"
    assert not _is_grass_pixel(81, 57, 43, 255)
    assert not _is_grass_pixel(96, 178, 49, 0), "прозрачный пиксель красить нечего"


def test_creature_sprites_are_pixel_art_grids():
    """Каждое животное должно иметь корректную сетку (все строки одной
    длины, только известные символы) и рисоваться в свой размер."""
    get_app()
    from units.Objects import CreatureSprites as CS
    from units.Objects import Creatures as C

    pairs = [
        ("Cow", CS.create_cow_sprite), ("Wolf", CS.create_wolf_sprite),
        ("Fox", CS.create_fox_sprite), ("Rabbit", CS.create_rabbit_sprite),
        ("Deer", CS.create_deer_sprite), ("Camel", CS.create_camel_sprite),
        ("Boar", CS.create_boar_sprite), ("Snake", CS.create_snake_sprite),
        ("Imp", CS.create_imp_sprite), ("Scorpion", CS.create_scorpion_sprite),
        ("Crab", CS.create_crab_sprite), ("Penguin", CS.create_penguin_sprite),
        ("Bat", CS.create_bat_sprite), ("StoneGolem", CS.create_golem_sprite),
        ("SpaceDrifter", CS.create_space_drifter_sprite),
    ]
    assert len(pairs) == 15
    for name, fn in pairs:
        cls = getattr(C, name)
        size = (int(cls.width), int(cls.height))
        colors = getattr(cls, "colors", None)
        base = colors[0] if isinstance(colors, list) else getattr(cls, "color", None)
        spr = fn(base, size)
        assert spr.get_size() == size, f"{name}: спрайт не в размер существа"
        # спрайт не должен быть полностью пустым
        assert any(spr.get_at((x, y))[3] for x in range(size[0]) for y in range(size[1])), \
            f"{name}: спрайт пустой"


def test_creature_sprite_grids_have_ground_contact():
    """Животное должно опираться на нижнюю часть спрайта, а не висеть в
    воздухе: у процедурных спрайтов лапы часто не доходили до низа."""
    get_app()
    from units.Objects import CreatureSprites as CS
    # у этих сеток последняя строка — лапы/основание
    for name in ("COW", "WOLF", "FOX", "RABBIT", "DEER", "CAMEL", "BOAR",
                 "IMP", "SCORPION", "CRAB", "PENGUIN", "GOLEM"):
        rows = getattr(CS, name)
        assert rows, name
        # ищем самую нижнюю непрозрачную строку и требуем, чтобы она была
        # в двух последних строках сетки
        last_filled = max(i for i, r in enumerate(rows) if set(r) != {'.'})
        assert last_filled >= len(rows) - 2, \
            f"{name}: низ сетки пустой — существо будет висеть над землёй"


# ===================== привязка структур к поверхности =====================

def test_terrain_probe_matches_generated_ground():
    """Зонд поверхности должен совпадать с реально сгенерированным рельефом.

    Формула плотности породы одна и та же у генератора и у зонда (иначе они
    однажды разойдутся и структуры начнут висеть). Растения стоят НА земле,
    поэтому сравниваем с первым блоком именно породы."""
    game = fresh_world(41)
    gm = game.game_map
    from units.Map.GameMap import terrain_is_solid
    GROUND = {1, 2, 3, 4, 5}  # дёрн, земля, камень, блор, гранит
    checked = 0
    start_y = -30
    for tx in range(-60, 60, 11):
        probe = gm.surface_y_at(tx, start_y)
        if probe is None:
            continue
        assert terrain_is_solid(tx, probe, gm.base_generation)
        # проверять "выше пусто" можно только внутри просмотренного отрезка:
        # то, что лежит выше start_y, зонд и не смотрел
        if probe > start_y:
            assert not terrain_is_solid(tx, probe - 1, gm.base_generation), \
                "над найденной поверхностью не должно быть породы"
        real = gm.get_static_tile_type(tx, probe, default=0, create_chunk=True)
        assert real in GROUND, f"x={tx}: зонд показал породу, а в мире {real}"
        checked += 1
    assert checked >= 3, "проверить нужно хотя бы несколько столбцов"


def test_surface_snap_puts_structure_on_ground():
    """Структура с якорем surface встаёт низом на землю и не оказывается
    вмурованной в породу; негодные места (пустота, навесы) отклоняются."""
    game = fresh_world(42)
    gm = game.game_map
    from units.Map.GameMap import terrain_is_solid
    from units.Map.StructuresBiome import TUNDRA_CAMP, FOREST_OBSERVATORY
    base = gm.base_generation
    placed = skipped = 0
    for x in range(-150, 150, 17):
        for schema in (TUNDRA_CAMP, FOREST_OBSERVATORY):
            w, h = schema[0]
            snap = gm._snap_to_surface((x, -40), (w, h))
            if snap is None:
                skipped += 1
                continue
            bottom_row = snap[1] + h - 1
            buried = sum(1 for dx in range(w) if terrain_is_solid(snap[0] + dx, bottom_row, base))
            assert buried * 2 <= w, f"x={x}: структура вмурована в породу"
            assert any(terrain_is_solid(snap[0] + dx, snap[1] + h, base) for dx in range(w)), \
                f"x={x}: под структурой нет земли"
            placed += 1
    assert placed, "хоть где-то структура должна вставать на землю"
    assert skipped, "негодные места должны отклоняться, а не застраиваться"


def test_foundation_fills_gap_down_to_ground():
    """На склоне помеченные столбы ('=') сами достраиваются вниз до земли,
    иначе постройка висела бы над уклоном одним углом."""
    game = fresh_world(43)
    gm = game.game_map
    from units.Map.StructuresBiome import TUNDRA_CAMP
    size, _array, _backs, foundation = TUNDRA_CAMP
    w, h = size
    assert foundation, "у стоянки в схеме есть столбы фундамента"

    # ищем место с заметным уклоном, где фундамент реально нужен
    for x in range(-300, 300, 3):
        snap = gm._snap_to_surface((x, -40), size)
        if not snap:
            continue
        tops = [gm.surface_y_at(x + dx, -40) for dx in range(w)]
        if None in tops or max(tops) - min(tops) < 3:
            continue
        gm.set_structure(snap, TUNDRA_CAMP)
        # у столба над более низкой землёй должен появиться фундамент
        filled_any = False
        for dx, dy, tile_type in foundation:
            col, start = snap[0] + dx, snap[1] + dy + 1
            ground = gm.surface_y_at(col, -40)
            if ground is None or ground <= start:
                continue  # под этим столбом земля сразу — достраивать нечего
            filled_any = True
            for y in range(start, min(ground, start + gm.FOUNDATION_MAX_DEPTH)):
                assert gm.get_static_tile_type(col, y, create_chunk=True) == tile_type, \
                    f"просвет под структурой не заполнен на y={y}"
        assert filled_any, "на выбранном склоне фундамент должен был понадобиться"
        return
    raise AssertionError("не нашлось склона для проверки фундамента")


def test_foundation_depth_is_capped():
    """Над пропастью фундамент не должен выкладывать столб на всю глубину."""
    game = fresh_world(44)
    gm = game.game_map
    assert gm.FOUNDATION_MAX_DEPTH <= 20
    # ставим фундамент в заведомую пустоту высоко над миром
    high_y = -400
    gm._build_foundation((0, high_y), [(0, 0, 31)])
    depth = 0
    for d in range(1, gm.FOUNDATION_MAX_DEPTH + 30):
        if gm.get_static_tile_type(0, high_y + d, default=0, create_chunk=True) == 31:
            depth += 1
        else:
            break
    assert depth <= gm.FOUNDATION_MAX_DEPTH, f"фундамент ушёл на {depth} блоков"


def test_cave_structures_stay_unanchored():
    """Пещерные постройки не должны получать привязку к поверхности —
    им место в камне."""
    get_app()
    from units.Map.StructuresBiome import Structures_biome_middleworld as S
    anchors = {v[0]: (v[4] if len(v) > 4 else None) for v in S.values()}
    assert anchors["deep mine"] is None
    assert anchors["cave shrine"] is None
    surface = [n for n, a in anchors.items() if a == "surface"]
    assert len(surface) == 8, f"наземных структур должно быть 8, а не {len(surface)}"


# ===================== пиксель-арт предметов =====================

def test_item_sprites_are_not_flat_placeholders():
    """У ресурсов должна быть форма, а не плоский квадрат одного цвета:
    раньше сера от жареного мяса отличалась только оттенком."""
    get_app()
    from units.Tiles import tile_imgs, original_tile_words

    def count_colors(surf):
        w, h = surf.get_size()
        return len({surf.get_at((x, y))[:3] for x in range(w) for y in range(h)})

    # сера, хитин, шкура, сырое/жареное мясо, космическая пыль, палка
    for idx in (402, 403, 404, 405, 406, 408, 801):
        img = tile_imgs[idx]
        n = count_colors(img)
        assert n >= 4, f"{idx} ({original_tile_words.get(idx)}): всего {n} цветов — похоже на заглушку"
        # и в спрайте должна быть прозрачность (форма, а не полный квадрат)
        w, h = img.get_size()
        assert any(img.get_at((x, y))[3] == 0 for x in range(w) for y in range(h)), \
            f"{idx}: спрайт залит целиком, формы не видно"


def test_item_sprite_grids_valid():
    """Все сетки предметов — 16x16 и собираются без ошибок."""
    get_app()
    from units.ItemSprites import SHAPES, ITEM_SIZE
    from units.Graphics.PixelArt import build_sprite
    assert SHAPES
    for name, rows in SHAPES.items():
        assert len(rows) == ITEM_SIZE, f"{name}: {len(rows)} строк вместо {ITEM_SIZE}"
        assert {len(r) for r in rows} == {ITEM_SIZE}, f"{name}: строки разной длины"
        spr = build_sprite(rows, base="#808080", size=(32, 32))
        assert spr.get_size() == (32, 32)


def test_mod_can_use_pixel_art():
    """Мод должен уметь задавать спрайт сеткой ('pixels') и брать готовую
    форму по имени ('shape') — иначе ему доступен только плоский квадрат."""
    import tempfile
    get_app()
    from units import mods
    saved_mods, saved_errors = list(mods.MODS), list(mods.MOD_ERRORS)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _write_mod(tmp, "art", {"name": "арт", "items": [
                {"id": 9300, "name": "Своя сетка", "color": "#20A0F0",
                 "pixels": ["..BB..", ".BLLB.", "BLBBLB", "BLBBLB", ".BLLB.", "..BB.."]},
                {"id": 9301, "name": "Готовая форма", "color": "#F08020", "shape": "meat"},
            ]})
            loaded, errors = mods.load_mods(tmp)
            assert not errors, errors
            specs = {s["id"]: s for s in mods.mod_blocks()}
            for idx in (9300, 9301):
                frames = specs[idx]["frames"]
                assert len(frames) == 1
                surf = frames[0]
                w, h = surf.get_size()
                ncol = len({surf.get_at((x, y))[:3] for x in range(w) for y in range(h)})
                assert ncol >= 3, f"{idx}: спрайт вышел плоским"
    finally:
        mods.MODS[:], mods.MOD_ERRORS[:] = saved_mods, saved_errors
        mods.load_mods()


def test_mod_pixel_art_errors_are_reported():
    """Кривая сетка и неизвестная форма должны давать понятную ошибку, а не
    ронять игру: опечатку в строке легко не заметить."""
    import tempfile
    get_app()
    from units import mods
    saved_mods, saved_errors = list(mods.MODS), list(mods.MOD_ERRORS)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _write_mod(tmp, "ragged", {"name": "кривая", "items": [
                {"id": 9310, "name": "Кривая", "color": "#ffffff", "pixels": ["BB", "B"]}]})
            _write_mod(tmp, "noshape", {"name": "нет формы", "items": [
                {"id": 9311, "name": "Нет", "color": "#ffffff", "shape": "такой-формы-нет"}]})
            loaded, errors = mods.load_mods(tmp)
            assert not loaded
            folders = {f for f, _m in errors}
            assert folders == {"ragged", "noshape"}, folders
            assert any("одной длины" in m for _f, m in errors), errors
            assert any("shape" in m for _f, m in errors), errors
    finally:
        mods.MODS[:], mods.MOD_ERRORS[:] = saved_mods, saved_errors
        mods.load_mods()


# ===================== лава и тик вне экрана =====================

def test_lava_damages_and_is_animated():
    """Лава должна наносить урон по общей таблице (раньше урон был зашит
    константой 103 прямо в физике) и анимироваться."""
    get_app()
    from units.Objects.Entity import PhysicalObject
    from units.Tiles import DAMAGE_TILES, ANIMATED_TILES, original_tile_words
    assert DAMAGE_TILES[140] > DAMAGE_TILES[103], "лава должна быть опаснее кактуса"
    assert original_tile_words[140] == "Лава"
    assert len(ANIMATED_TILES[140]["frames"]) >= 2, "лава анимирована"

    game = fresh_world(51)

    class Dummy(PhysicalObject):
        max_lives = 100

    d = Dummy(game, x=0, y=0, width=16, height=16)
    d.lives = d.max_lives
    d.move((40, 0), {(1, 0): 140})
    assert d.max_lives - d.lives == DAMAGE_TILES[140], "урон лавы должен браться из таблицы"


def test_lava_generated_in_hell():
    """Лава появляется в аду сама, а не только в структурах — иначе ад
    ничем не отличается от обычных пещер."""
    game = fresh_world(52)
    gm = game.game_map
    from units.common import START_HELL_Y, LAVA_DEPTH_MARGIN
    y = START_HELL_Y + LAVA_DEPTH_MARGIN + 60
    found = 0
    for x in range(0, 200, 4):
        for dy in range(0, 40, 2):
            if gm.get_static_tile_type(x, y + dy, default=0, create_chunk=True) == 140:
                found += 1
                break
    assert found, "в аду должна встречаться лава"


def test_forced_chunks_tick_only_when_loader_on():
    """Прогрузчик тикает тайлы только когда включён; видимые чанки
    пропускаются, иначе они получали бы два тика за кадр."""
    game = fresh_world(53)
    gm = game.game_map
    far = ground = None
    for cand in range(300, 900, 7):
        y = gm.surface_y_at(cand, -60)
        if y is not None:
            far, ground = cand, y
            break
    assert far is not None
    gm.set_static_tile(far, ground - 1, 101)          # куст с таймером
    gm.set_static_tile(far + 2, ground - 1, 219)      # прогрузчик
    tile = gm.get_static_tile(far + 2, ground - 1)
    loader = gm.get_tile_obj(*gm.to_chunk_xy(far + 2, ground - 1), tile[3])

    loader.activating = False
    assert gm.tick_forced_chunks(gm.FORCED_TICK_PERIOD, ()) == 0, "выключенный не должен тикать"

    loader.activated_tact, loader.activating = game.tact, True
    ticked = gm.tick_forced_chunks(gm.FORCED_TICK_PERIOD * 2, ())
    assert ticked > 0, "включённый должен тикать тайлы"

    loader.activated_tact, loader.activating = game.tact, True
    visible = gm.forced_chunk_coords()
    assert gm.tick_forced_chunks(gm.FORCED_TICK_PERIOD * 3, visible) == 0, \
        "видимые чанки должен обновлять ScreenMap, а не этот тик"


def test_plant_grows_offscreen_under_loader():
    """Главное, ради чего всё затевалось: саженец должен вырастать в
    дерево, пока игрок далеко. До этого рост шёл только на экране."""
    game = fresh_world(54)
    gm = game.game_map
    far = ground = None
    for cand in range(300, 900, 7):
        y = gm.surface_y_at(cand, -60)
        if y is not None:
            far, ground = cand, y
            break
    sap = (far, ground - 1)
    gm.set_static_tile(sap[0], sap[1], 102)           # саженец
    gm.set_static_tile(far + 2, ground - 1, 219)
    tile = gm.get_static_tile(far + 2, ground - 1)
    loader = gm.get_tile_obj(*gm.to_chunk_xy(far + 2, ground - 1), tile[3])

    from units.common import FPS
    tact = 0
    for _ in range(FPS * 700):
        tact += 1
        loader.activated_tact, loader.activating = tact, True
        if tact % gm.FORCED_TICK_PERIOD == 0:
            gm.tick_forced_chunks(tact, ())
    grown = any(gm.get_static_tile_type(sap[0], sap[1] - d, default=0) == 110
                for d in range(0, 4))
    assert grown, "саженец под прогрузчиком должен вырасти в дерево вне экрана"


def test_plant_growth_logic_shared_with_screenmap():
    """Рост на экране и вне его должен идти одним кодом: две копии
    однажды разойдутся, и фермы будут вести себя по-разному."""
    get_app()
    import inspect
    from units.Map.ScreenMap import ScreenMap
    src = inspect.getsource(ScreenMap.update_tile)
    assert "grow_plant_tile" in src, "ScreenMap должен звать общий GameMap.grow_plant_tile"
    assert "TILE_TIMER" not in src, "своей копии логики роста в ScreenMap быть не должно"


# ===================== логистика: воронка, конвейер, дропер, лесоруб =====================

def _place_block(gm, x, y, index):
    gm.set_static_tile(x, y, index)
    tile = gm.get_static_tile(x, y)
    return gm.get_tile_obj(*gm.to_chunk_xy(x, y), tile[3])


def test_hopper_picks_up_and_pushes_into_chest():
    """Воронка подбирает лежащие предметы и отдаёт их в сундук снизу —
    без этого ни одна ферма не автоматическая."""
    game = fresh_world(61)
    gm = game.game_map
    x, y = 12, 4
    hopper = _place_block(gm, x, y, 224)
    chest = _place_block(gm, x, y + 1, 129)
    assert hopper is not None and chest is not None

    gm.add_item_of_index(11, 5, x, y)         # доски прямо в воронку

    # такт двигаем ПО ОДНОМУ, как в игре: блок срабатывает на кратных
    # PERIOD тактах, и прибавление сразу PERIOD от произвольного старта
    # могло не попасть в них ни разу
    def run(ticks):
        for _ in range(ticks):
            game.tact += 1
            hopper.update(16)

    run(hopper.PERIOD * 3)
    picked = sum(c.count for c in hopper.inventory if c) + \
             sum(c.count for c in chest.inventory if c)
    assert picked > 0, "воронка должна была подобрать предмет"
    # и передать вниз
    run(hopper.PERIOD * 8)
    assert any(c and c.index == 11 for c in chest.inventory), "предмет должен уйти в сундук"


def test_conveyor_moves_items_and_flips_direction():
    """Конвейер толкает предметы вбок; направление переключается правым
    кликом (кадром тайла), а не вторым блоком."""
    game = fresh_world(62)
    gm = game.game_map
    x, y = 20, 6
    conv = _place_block(gm, x, y, 225)
    gm.add_item_of_index(11, 1, x, y - 1)
    items = conv.items_in_tile(x, y - 1)
    assert items, "предмет должен лежать на конвейере"
    item = items[0]

    def run(ticks):
        for _ in range(ticks):
            game.tact += 1
            conv.update(16)

    start = item.rect.x
    run(conv.PERIOD * 4)
    assert item.rect.x > start, "вправо по умолчанию"

    conv.right_click((0, 0))
    assert conv.direction() == -1, "правый клик разворачивает"
    mid = item.rect.x
    run(conv.PERIOD * 4)
    assert item.rect.x < mid, "после разворота — влево"


def test_dropper_drops_one_item_per_signal_edge():
    """Дропер выбрасывает предмет по ФРОНТУ сигнала: иначе он вывалил бы
    весь запас за секунду, пока включён рычаг."""
    game = fresh_world(63)
    gm = game.game_map
    x, y = 26, 5
    dropper = _place_block(gm, x, y, 226)
    from units.Objects.Items import ItemsTile
    dropper.inventory.put_to_inventory(ItemsTile(game, 11, count=3))
    before = sum(c.count for c in dropper.inventory if c)

    # держим сигнал включённым несколько тактов — должен выпасть ОДИН
    for _ in range(5):
        dropper.activated_tact = game.tact
        dropper.update(16)
        game.tact += 1
    assert sum(c.count for c in dropper.inventory if c) == before - 1, \
        "за один фронт сигнала — ровно один предмет"

    # отпустили и снова включили — ещё один
    dropper.activated_tact = float("-inf")
    dropper.update(16)
    game.tact += 1
    dropper.activated_tact = game.tact
    dropper.update(16)
    assert sum(c.count for c in dropper.inventory if c) == before - 2


def test_chopper_cuts_tree_above_on_signal():
    """Лесоруб срубает ствол над собой по сигналу и роняет брёвна —
    основа фермы дерева."""
    game = fresh_world(64)
    gm = game.game_map
    x, y = 33, 8
    chopper = _place_block(gm, x, y, 227)
    for dy in range(1, 4):
        gm.set_static_tile(x, y - dy, 110)      # ствол дерева
    assert gm.get_static_tile_type(x, y - 1) == 110

    chopper.activated_tact = game.tact
    chopper.update(16)
    assert gm.get_static_tile_type(x, y - 1, default=0) == 0, "ствол должен быть срублен"
    dropped = chopper.items_in_tile(x, y - 1) if hasattr(chopper, "items_in_tile") else []
    chunk = gm.chunk(gm.to_chunk_xy(x, y - 1))
    from units.common import OBJ_ITEM
    assert any(o.class_obj & OBJ_ITEM for o in chunk[1]), "должны выпасть брёвна"


# ===================== двигатели, лифт, порталы, гнездо голема =====================

def test_fuel_engine_burns_wood_and_pulses_network():
    """Топливный двигатель должен разгонять сеть быстрее таймера, но за
    дерево: бесплатной скорости в игре быть не должно, иначе таймер и
    экономика дерева обесцениваются."""
    game = fresh_world(70)
    gm = game.game_map
    x, y = 12, 4
    engine = _place_block(gm, x, y, 228)
    lamp = _place_block(gm, x + 1, y, 215)
    from units.Objects.Items import ItemsTile
    engine.inventory.put_to_inventory(ItemsTile(game, 11, count=1))   # доски

    def run(ticks):
        for _ in range(ticks):
            game.tact += 1
            engine.update(16)

    run(engine.period + 1)
    assert lamp.activated_tact >= game.tact - 1, "двигатель должен зажечь сеть"
    assert engine.charge == engine.pulses_per_fuel - 1, "одна доска = запас импульсов"

    # выработали топливо — двигатель встал
    run(engine.period * (engine.pulses_per_fuel + 2))
    assert not any(c for c in engine.inventory), "топливо должно сгореть"
    assert engine.update(16) is engine.img_off, "без топлива двигатель стоит"


def test_creative_engine_needs_no_fuel_and_is_fastest():
    """Креативный двигатель — отладочный: топлива не просит и быстрее
    остальных. Рецепта у него нет, иначе он обнулил бы смысл прочих."""
    game = fresh_world(71)
    gm = game.game_map
    engine = _place_block(gm, 15, 4, 229)
    from units.Objects.TileClasses import FuelEngine, SpaceEngine, HellEngine
    assert engine.period < min(FuelEngine.period, SpaceEngine.period, HellEngine.period)

    lamp = _place_block(gm, 16, 4, 215)
    for _ in range(engine.period + 1):
        game.tact += 1
        engine.update(16)
    assert lamp.activated_tact >= game.tact - 1

    from units.creating_items import RECIPES
    assert all(rec[0][0] != 229 for rec in RECIPES), "у креативного двигателя не должно быть рецепта"


def test_space_and_hell_engines_accept_only_their_fuel():
    """Космический и адский двигатели работают на ресурсах своих миров —
    именно это и делает их наградой за поход туда, а не просто «ещё один
    таймер»."""
    game = fresh_world(72)
    gm = game.game_map
    space = _place_block(gm, 18, 4, 230)
    hell = _place_block(gm, 22, 4, 231)
    from units.Objects.TileClasses import FuelEngine
    assert space.fuel_items == (408,) and hell.fuel_items == (402,)
    assert space.inventory.filter_items == {408}
    assert hell.inventory.filter_items == {402}

    from units.Objects.Items import ItemsTile
    space.inventory.put_to_inventory(ItemsTile(game, 408, count=1))
    for _ in range(space.period + 1):
        game.tact += 1
        space.update(16)
    assert space.charge == space.pulses_per_fuel - 1, "пыль должна дать длинный запас"
    assert space.pulses_per_fuel > FuelEngine.pulses_per_fuel, "пыль экономнее дерева"


def test_portals_pair_by_code_and_teleport_player():
    """Два портала с одинаковым набором предметов — это пара. Пустая
    «частота» парой не считается: два только что поставленных портала не
    должны утаскивать игрока неизвестно куда."""
    game = fresh_world(73)
    gm = game.game_map
    a = _place_block(gm, 10, 5, 232)
    b = _place_block(gm, 400, 5, 232)
    assert a.pair() is None and b.pair() is None, "пустые порталы не пара"

    from units.Objects.Items import ItemsTile
    for portal in (a, b):
        portal.inventory.put_to_inventory(ItemsTile(game, 51, count=1))
        portal.inventory.put_to_inventory(ItemsTile(game, 62, count=1))
    assert a.pair() is b and b.pair() is a, "одинаковая частота = пара"

    from units.common import TSIZE
    game.player.tp_to((a.tx * TSIZE, a.ty * TSIZE))
    game.tact += a.COOLDOWN * 2
    a.update(16)
    assert abs(game.player.rect.centerx - b.tx * TSIZE) <= TSIZE, "игрок должен оказаться у второго портала"
    # обратного мгновенного прыжка быть не должно
    at_b = tuple(game.player.rect.center)
    b.update(16)
    assert tuple(game.player.rect.center) == at_b, "кулдаун должен держать игрока на месте"


def test_portal_code_changes_reindex_pairing():
    """Смена предметов в портале должна менять и его частоту: иначе
    перенастроенный портал остался бы связан со старой парой."""
    game = fresh_world(74)
    gm = game.game_map
    a = _place_block(gm, 10, 5, 232)
    b = _place_block(gm, 300, 5, 232)
    from units.Objects.Items import ItemsTile
    for portal in (a, b):
        portal.inventory.put_to_inventory(ItemsTile(game, 51, count=1))
    assert a.pair() is b

    a.inventory.set_cell(0, None)
    assert a.pair() is None, "частота изменилась — старая пара не действует"
    assert b.pair() is None, "и обратная связь тоже"


def _stand_in_shaft(game, tile_id, x=50, y=20):
    """Поставить игрока внутрь вертикальной шахты из заданного блока."""
    from units.common import TSIZE
    gm = game.game_map
    for dy in range(-6, 7):
        gm.set_static_tile(x, y + dy, tile_id)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    game.update()                           # кадр заполняет static_tiles
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.player.moving(16)
    return game.player


def test_blore_columns_move_player_by_direction_of_the_shaft():
    """Два отдельных блока вместо одного «универсального лифта»: направление
    задаёт сама шахта, а не зажатая клавиша. Так видно, куда шахта везёт, и
    собирается нормальный двухполосный подъёмник — вверх слева, вниз справа.

    Спуск медленнее подъёма и держится ниже порога урона от падения, иначе
    приезд на дно шахты бил бы игрока.
    """
    from units.common import ELEVATOR_UP_SPEED, ELEVATOR_DOWN_SPEED
    assert ELEVATOR_DOWN_SPEED < 0.75, "спуск не должен наносить урон при приземлении"
    assert ELEVATOR_DOWN_SPEED < ELEVATOR_UP_SPEED

    up = _stand_in_shaft(fresh_world(75), 234)
    assert 234 in up.collisions_ttile, "игрок должен стоять в шахте"
    assert up.vertical_momentum == -ELEVATOR_UP_SPEED, "восходящий столб тянет вверх"
    assert up.jump_count == 0, "столб не должен съедать прыжки"

    # клавиша «вниз» на подъём не влияет: направление у блока, не у игрока
    up.on_down = True
    up.moving(16)
    assert up.vertical_momentum == -ELEVATOR_UP_SPEED

    down = _stand_in_shaft(fresh_world(76), 236)
    assert 236 in down.collisions_ttile
    assert down.vertical_momentum == ELEVATOR_DOWN_SPEED, "нисходящий столб опускает"


def test_blore_columns_cost_blore():
    """Столбы завязаны на блор: по сюжету именно блор держит перемещение.
    Подъём дороже спуска — падать планета помогает и так."""
    get_app()
    from units.creating_items import RECIPES
    recipes = {rec[0][0]: dict(rec[1]) for rec in RECIPES if rec[0][0] in (234, 236)}
    assert 234 in recipes and 236 in recipes, "у обоих столбов должен быть рецепт"
    assert recipes[234].get(61), "восходящий столб должен стоить блоровой руды"
    assert recipes[236].get(61), "нисходящий тоже"
    assert recipes[234][61] > recipes[236][61], "подъём должен быть дороже спуска"


def test_golem_nest_spawns_golem_for_stone_under_signal():
    """Гнездо голема — ферма железа: отдаёшь камень, планета возвращает
    камень и немного железа. Без сигнала и без камня — ничего."""
    game = fresh_world(76)
    gm = game.game_map
    x, y = 40, 30
    nest = _place_block(gm, x, y, 233)
    from units.Objects.Items import ItemsTile
    from units.Objects.Creatures import StoneGolem

    def heat(ticks, powered=True):
        for _ in range(ticks):
            game.tact += 1
            if powered:
                nest.activated_tact = game.tact
            nest.update(16)

    # без камня гнездо не греется
    heat(nest.HEAT_TACTS + 5)
    assert nest.heat == 0, "пустое гнездо не должно греться"

    nest.inventory.put_to_inventory(ItemsTile(game, 3, count=nest.STONE_PER_GOLEM))
    # без сигнала — тоже. activated_tact сбрасываем явно: у сигнальных
    # тайлов есть допуск в 1 такт, иначе первый же «выключенный» тик
    # всё ещё читался бы как включённый
    nest.activated_tact = float("-inf")
    nest.heat = 0
    heat(10, powered=False)
    assert nest.heat == 0, "без сигнала гнездо холодное"

    heat(nest.HEAT_TACTS + 1)
    chunk = gm.chunk(gm.to_chunk_xy(x, y - 2))
    assert any(isinstance(o, StoneGolem) for o in chunk[1]), "должен появиться голем"
    assert nest.stone_count() == 0, "камень должен уйти на голема"
    assert (64, (0, 2)) in [args for _cls, args in StoneGolem.drop_items], \
        "голем — источник железа, иначе ферма бессмысленна"


def test_new_machines_registered_consistently():
    """Каждый новый блок должен быть зарегистрирован везде: без картинки
    он падает при отрисовке, без прочности — при копании, без имени —
    в инвентаре."""
    get_app()
    from units import Tiles
    from units.Objects.TileClasses import tiles_class
    from units.UI.BlocksUI import BLOCKS_UI
    for index in (228, 229, 230, 231, 232, 233, 234):
        assert index in Tiles.tile_imgs, index
        assert index in Tiles.original_tile_words, index
        assert index in Tiles.TILES_SOLIDITY, index
        assert index in Tiles.iron_capability, index
        assert index in Tiles.SEMIPHYSBODY_TILES, index
    for index in (228, 229, 230, 231, 232, 233):
        assert index in Tiles.CLASS_TILE, index
        assert index in Tiles.CLASS_UPDATING_TILES, index
        assert index in tiles_class, index
        assert index in BLOCKS_UI, index
    assert 234 not in Tiles.CLASS_TILE, "лифт обходится без класса — его ведёт физика игрока"


def test_block_with_inventory_drops_itself_once():
    """Блок с инвентарём не должен выпадать дважды: item_of_break_tile уже
    кладёт сам блок, а items_of_break — только содержимое."""
    game = fresh_world(77)
    gm = game.game_map
    x, y = 14, 4
    hopper = _place_block(gm, x, y, 224)
    from units.Objects.Items import ItemsTile
    hopper.inventory.put_to_inventory(ItemsTile(game, 11, count=2))
    from units.Tiles import item_of_break_tile
    drops = item_of_break_tile(gm.get_static_tile(x, y), gm, (x, y))
    assert sum(cnt for i, cnt in drops if i == 224) == 1, f"воронка должна выпасть один раз: {drops}"
    assert any(i == 11 for i, _ in drops), "содержимое тоже должно выпасть"


# ===================== космос: пылеуловитель и топливо прогрузчика =====================

def _clear_vacuum(gm, x, y):
    """Расчистить вакуум вокруг тайла: в космосе рядом может оказаться
    астероид, и тест зависел бы от сида."""
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            gm.set_static_tile(x + dx, y + dy, 0)


def test_dust_collector_needs_vacuum_and_space():
    """Пылеуловитель — ферма пыли, но только в открытом вакууме: закладка
    парусов блоками должна её глушить, иначе ферма была бы «поставил в
    ящик и забыл»."""
    from units.common import START_SPACE_Y
    game = fresh_world(80)
    gm = game.game_map
    x, y = 10, START_SPACE_Y - 200
    _clear_vacuum(gm, x, y)                 # рядом может оказаться астероид
    collector = _place_block(gm, x, y, 235)

    def run(ticks):
        for _ in range(ticks):
            game.tact += 1
            collector.activated_tact = game.tact
            collector.update(16)

    run(collector.PERIOD + 2)
    assert any(c and c.index == 408 for c in collector.inventory), \
        "в вакууме уловитель должен собирать пыль"

    # закладываем соседей — парусу нечего ловить
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx or dy:
                gm.set_static_tile(x + dx, y + dy, 26)
    assert not collector.works(), "заложенный блоками уловитель не работает"

    # и на поверхности он тоже бесполезен
    ground = _place_block(gm, 60, 5, 235)
    assert not ground.works(), "на поверхности пыль не ловится"


def test_dust_collector_needs_signal():
    """Ферма пыли должна что-то стоить: без сигнала уловитель стоит."""
    from units.common import START_SPACE_Y
    game = fresh_world(81)
    gm = game.game_map
    _clear_vacuum(gm, 30, START_SPACE_Y - 300)
    collector = _place_block(gm, 30, START_SPACE_Y - 300, 235)
    assert collector.works(), "место подходящее"
    for _ in range(collector.PERIOD * 2):
        game.tact += 1
        collector.update(16)          # сигнала не даём
    assert not any(c for c in collector.inventory), "без сигнала пыль не копится"


def test_chunk_loader_burns_dust_for_big_radius():
    """Прогрузчик — самая сильная способность в игре (мир тикает без
    игрока), поэтому большой радиус теперь стоит космической пыли. Малый
    радиус остаётся бесплатным, иначе ранние фермы стали бы невозможны."""
    game = fresh_world(82)
    gm = game.game_map
    loader = _place_block(gm, 20, 6, 219)
    from units.Objects.Items import ItemsTile
    assert loader.radius == loader.BASE_RADIUS

    loader.inventory.put_to_inventory(ItemsTile(game, 408, count=1))
    game.tact += 1
    loader.activated_tact = game.tact
    loader.update(16)
    assert loader.radius == loader.FUELED_RADIUS, "пыль должна расширить радиус"
    assert not any(c for c in loader.inventory), "пыль должна сгореть"

    # топливо кончилось — радиус возвращается к базовому
    for _ in range(loader.FUEL_PERIOD + 2):
        game.tact += 1
        loader.activated_tact = game.tact
        loader.update(16)
    assert loader.radius == loader.BASE_RADIUS, "без пыли радиус базовый"


def test_chunk_loader_loads_old_saves_without_fuel_slot():
    """Миры, созданные до появления топлива, не содержат ключа inventory:
    загрузка не должна падать на каждом старом прогрузчике."""
    game = fresh_world(83)
    gm = game.game_map
    loader = _place_block(gm, 24, 6, 219)
    old_vars = {"tile_pos": (24, 6), "activated_tact": 0}
    loader.set_vars(dict(old_vars))    # не должно бросить KeyError
    assert loader.radius == loader.BASE_RADIUS


# ===================== проверка обновлений =====================

def test_update_version_compare():
    """Сравнение версий должно переживать «v» и суффикс -alpha: теги
    релизов выглядят именно так, а GAME_VERSION — без «v»."""
    from units.Updater import parse_version, is_newer
    assert parse_version("v0.2.16-alpha") == (0, 2, 16)
    assert parse_version("0.3") == (0, 3, 0)
    assert parse_version("мусор") is None

    assert is_newer("v0.2.17-alpha", "0.2.16-alpha")
    assert is_newer("v0.3.0-alpha", "0.2.16-alpha")
    assert not is_newer("v0.2.16-alpha", "0.2.16-alpha"), "та же версия — не обновление"
    assert not is_newer("v0.2.15-alpha", "0.2.16-alpha"), "старая версия — не обновление"
    assert not is_newer(None, "0.2.16-alpha"), "нет ответа — нет обновления"


def test_game_version_matches_changelog():
    """GAME_VERSION отставал от тегов релизов (0.1.7 против v0.2.x), из-за
    чего проверка обновлений считала бы новым любой релиз."""
    from units.common import GAME_VERSION
    from units.Updater import parse_version
    with open("CHANGELOG.md", encoding="utf-8") as f:
        for line in f:
            if line.startswith("## [v"):
                latest = line.split("[", 1)[1].split("]", 1)[0]
                break
        else:
            raise AssertionError("в CHANGELOG нет ни одной версии")
    assert parse_version(GAME_VERSION) == parse_version(latest), \
        f"GAME_VERSION {GAME_VERSION} != {latest} из CHANGELOG"


def test_update_asset_picked_for_platform():
    """Скачивать надо архив своей ОС, а не первый попавшийся."""
    from units import Updater
    assets = {
        "Quadish-v0.2.16-alpha-linux-x64.tar.gz": "http://example/linux",
        "Quadish-v0.2.16-alpha-windows-x64.zip": "http://example/windows",
    }
    suffix = Updater.platform_asset_suffix()
    picked = Updater.asset_for_platform(assets)
    if suffix is None:                      # macOS — сборок нет
        assert picked is None
    else:
        assert picked is not None and picked[0].endswith(suffix)
    assert Updater.asset_for_platform({}) is None, "без файлов качать нечего"


def test_update_checker_states_without_network():
    """Проверка обновлений не должна ни падать, ни блокировать игру, когда
    сети нет: это обычное состояние, а не ошибка."""
    from units import Updater
    checker = Updater.UpdateChecker("0.2.16-alpha")
    assert checker.state == checker.IDLE and not checker.busy()

    real_fetch = Updater.fetch_latest
    try:
        Updater.fetch_latest = lambda: None          # «сети нет»
        checker._check()
        assert checker.state == checker.ERROR
        assert checker.message

        Updater.fetch_latest = lambda: {"tag": "v0.2.16-alpha", "url": "u", "assets": {}}
        checker._check()
        assert checker.state == checker.UPTODATE

        Updater.fetch_latest = lambda: {
            "tag": "v9.9.9-alpha", "url": "u",
            "assets": {"Quadish-v9.9.9-alpha-linux-x64.tar.gz": "l",
                       "Quadish-v9.9.9-alpha-windows-x64.zip": "w"}}
        checker._check()
        assert checker.state == checker.AVAILABLE
        assert checker.latest_tag == "v9.9.9-alpha"
    finally:
        Updater.fetch_latest = real_fetch

    # загрузка не должна стартовать из неподходящего состояния
    checker.state = checker.IDLE
    checker.download_async()
    assert checker.state == checker.IDLE, "качать нечего, пока не проверили"


# ===================== кривая сложности и старт =====================

def test_difficulty_curve_grows_with_distance_and_depth():
    """Сила существ была одинаковой везде — ни начала, ни развития. Теперь
    у спавна легче всего, а к аду и глубокому космосу выходит на максимум."""
    from units.common import (difficulty_scale, DIFFICULTY_MIN, DIFFICULTY_MAX,
                              START_HELL_Y, START_SPACE_Y)
    spawn = difficulty_scale(0, 0)
    assert spawn == DIFFICULTY_MIN, "у спавна должно быть проще всего"
    assert difficulty_scale(0, 400) > spawn, "глубже — сложнее"
    assert difficulty_scale(3000, 0) > spawn, "дальше от спавна — сложнее"
    assert difficulty_scale(0, START_HELL_Y) == DIFFICULTY_MAX, "ад — потолок"
    assert difficulty_scale(0, START_SPACE_Y - 600) == DIFFICULTY_MAX, "глубокий космос — потолок"
    # шкала берёт максимум из составляющих, а не сумму: иначе край карты в
    # аду давал бы неберущихся мобов просто за счёт координаты
    assert difficulty_scale(9000, START_HELL_Y + 500) == DIFFICULTY_MAX
    assert difficulty_scale(None, None) == 1.0, "без координат — без поправки"


def _count_ores(game, y0, chunks_wide=14, chunks_tall=2):
    """Сколько какой руды в куске породы на этой глубине."""
    from collections import Counter
    gm = game.game_map
    c = Counter()
    total = 0
    for cx in range(chunks_wide):
        for cy in range(y0 // 32, y0 // 32 + chunks_tall):
            arr = gm.chunk((cx, cy), create_chunk=True)[0]
            for i in range(0, len(arr), 4):
                if arr[i]:
                    total += 1
                    if arr[i] in (21, 22, 23, 24, 25):
                        c[arr[i]] += 1
    return c, total


def test_ore_reward_grows_with_depth():
    """Риск и награда обязаны идти по одной кривой.

    До этого пороги руд были постоянными: замер по 15 000 тайлов породы давал
    железо 1 на 98 у поверхности и 1 на 60 на глубине 1000, то есть спуск не
    окупался НИЧЕМ, хотя difficulty_scale делал мобов там вдвое сильнее.
    """
    game = fresh_world(4242)
    shallow, n_shallow = _count_ores(game, 120)
    deep, n_deep = _count_ores(game, 1000)

    def per_tile(counter, total, ore):
        return counter[ore] / max(1, total)

    for ore, name in ((21, "блор"), (25, "серебро")):
        near = per_tile(shallow, n_shallow, ore)
        far = per_tile(deep, n_deep, ore)
        assert far > near * 1.5, \
            f"{name}: на глубине {far:.5f}/тайл против {near:.5f} у поверхности — спуск не окупается"


def test_gold_is_findable_at_depth():
    """Золото участвует в 7 рецептах, а в породе не встречалось ВООБЩЕ:
    0 находок на 15 000 тайлов на всех глубинах. Золотая кирка (7 золота)
    была недостижима иначе как с босса."""
    game = fresh_world(4242)
    deep, total = _count_ores(game, 1000, chunks_wide=20)
    assert deep[23] > 0, f"золота нет на глубине даже в {total} тайлах породы"
    # и остаётся самым редким — это по-прежнему сокровище, а не расходник
    for ore, name in ((21, "блора"), (24, "железа"), (25, "серебра")):
        assert deep[23] < deep[ore], f"золота не должно быть больше {name}"


def test_ore_ladder_order_holds_at_depth():
    """Лестница редкости: железо — рабочая лошадка, золото — сокровище.
    Порядок должен держаться, иначе «ценность» материала ничем не обеспечена."""
    game = fresh_world(4243)
    deep, _ = _count_ores(game, 1000, chunks_wide=20)
    assert deep[24] > deep[22], "железа должно быть больше меди"
    assert deep[22] >= deep[23], "меди должно быть не меньше золота"
    assert deep[25] > deep[23], "серебра должно быть больше золота"


def test_loot_scales_with_danger_of_the_place():
    """Лут идёт по той же кривой, что и сила. До этого каменный голем был
    худшей сделкой в игре: 120 HP и 20 урона ради 5-10 камня, а на глубине
    ещё и вдвое крепче — за тот же камень."""
    from units.Map.GameMap import spawn_creature
    from units.Objects.Creatures import StoneGolem
    from units.common import START_HELL_Y
    game = fresh_world(91)
    easy = spawn_creature(StoneGolem, game, 0, 0)
    hard = spawn_creature(StoneGolem, game, 0, START_HELL_Y)
    assert hard.loot_scale > easy.loot_scale
    top_easy = StoneGolem._scaled_count((5, 10), easy.loot_scale)[1]
    top_hard = StoneGolem._scaled_count((5, 10), hard.loot_scale)[1]
    assert top_hard > top_easy, f"на глубине лут должен быть богаче: {top_easy} против {top_hard}"
    # нижняя граница не растёт — разброс и неудачный бой должны остаться
    assert StoneGolem._scaled_count((5, 10), hard.loot_scale)[0] == 5


def test_nest_golem_keeps_base_loot():
    """Гнездо голема порождает настоящих големов, поэтому поправка на место
    НЕ должна на них распространяться: иначе ферма железа меняла бы выработку
    от того, где игрок её поставил, и глубокая ферма ломала бы экономику."""
    from units.Objects.Creatures import StoneGolem
    game = fresh_world(92)
    golem = StoneGolem(game, (0, 0))          # так его создаёт гнездо
    assert getattr(golem, "loot_scale", 1.0) == 1.0
    assert StoneGolem._scaled_count((5, 10), 1.0) == (5, 10)


def test_spawned_creature_scales_with_place():
    """Множитель должен садиться на экземпляр, а не на класс: одна и та же
    змея у спавна и в аду обязана отличаться, а класс общий на весь мир."""
    from units.Map.GameMap import spawn_creature
    from units.Objects.Creatures import Wolf
    from units.common import START_HELL_Y
    game = fresh_world(90)
    easy = spawn_creature(Wolf, game, 0, 0)
    hard = spawn_creature(Wolf, game, 0, START_HELL_Y)
    assert hard.max_lives > easy.max_lives
    assert hard.punch_damage > easy.punch_damage
    assert hard.lives == hard.max_lives, "существо должно появляться полным"
    base = Wolf.__dict__["max_lives"]
    spawn_creature(Wolf, game, 0, START_HELL_Y)
    assert Wolf.__dict__["max_lives"] == base, "класс не должен меняться при спавне"


def test_no_boss_spawns_near_spawn_point():
    """Слайм-босс (250 HP, 35 урона) мог появиться у спавна на первой
    минуте — это не сложность, а стена."""
    from units.Map.GameMap import random_creature_selection
    from units.Objects.Creatures import SlimeBigBoss
    from units.common import DIFFICULTY_SAFE_RADIUS
    get_app()
    near = {random_creature_selection(5, None, 0) for _ in range(4000)}
    assert SlimeBigBoss not in near, "у спавна боссов быть не должно"
    far = {random_creature_selection(5, None, DIFFICULTY_SAFE_RADIUS * 4) for _ in range(4000)}
    assert SlimeBigBoss in far, "вдали босс должен остаться — иначе он просто исчез из игры"


def test_starter_grove_gives_wood_near_spawn():
    """Рядом со спавном могло не оказаться ни одного дерева, а дерево — это
    доски, стол, кирка и топливо, то есть вся первая цепочка. Игра
    начиналась с долгой ходьбы наугад."""
    from units.common import TSIZE
    for seed in (11, 12, 13, 14):
        game = fresh_world(seed)
        gm = game.game_map
        px = game.player.rect.centerx // TSIZE
        py = game.player.rect.centery // TSIZE
        wood = berries = 0
        for sx in range(px - gm.GROVE_RADIUS, px + gm.GROVE_RADIUS + 1):
            top = gm.surface_top_at(sx, py)
            if top is None:
                continue
            for dy in range(-9, 2):
                t = gm.get_static_tile_type(sx, top + dy, default=0, create_chunk=True)
                wood += t == 110
                berries += t == 101
        assert wood >= 8, f"сид {seed}: у спавна должно быть дерево, найдено стволов {wood}"
        assert berries >= 1, f"сид {seed}: у спавна должны быть ягоды"


def test_surface_top_finds_top_of_mountain():
    """surface_y_at ищет только вниз: если старт пришёлся внутрь горы, он
    возвращал ту же точку, и «поверхностью» оказывалась середина скалы."""
    game = fresh_world(15)
    gm = game.game_map
    from units.Map.GameMap import terrain_is_solid
    base = gm.base_generation
    buried = None
    for tx in range(-200, 200):
        if terrain_is_solid(tx, 0, base):
            buried = tx
            break
    if buried is None:
        return                      # на этом сиде спавн и так на открытом месте
    top = gm.surface_top_at(buried, 0)
    assert top is not None and top <= 0
    assert terrain_is_solid(buried, top, base), "найденная точка — порода"
    assert not terrain_is_solid(buried, top - 1, base), "а над ней воздух"


# ===================== логистика в настоящем игровом цикле =====================
#
# Прежние тесты логистики дёргали block.update() напрямую и раскладывали
# предметы руками. Из-за этого они не заметили, что конвейер был
# полу-физическим: предмет проваливался сквозь ленту, переставал попадать в
# тайл над ней и никуда не ехал. Здесь мир крутится настоящими кадрами
# (game.update()), с физикой предметов — как у игрока.

def _run_frames(game, n):
    game.elapsed_time = 16
    for _ in range(n):
        game.update()


def _any_item(gm, tx, ty, radius_chunks=2):
    """Первый живой предмет в округе (предметы живут в чанках, не в тайлах)."""
    from units.common import OBJ_ITEM
    cx0, cy0 = gm.to_chunk_xy(tx, ty)
    for cx in range(cx0 - radius_chunks, cx0 + radius_chunks + 1):
        for cy in range(cy0 - radius_chunks, cy0 + radius_chunks + 1):
            chunk = gm.chunk((cx, cy))
            if not chunk:
                continue
            for o in chunk[1]:
                if o.class_obj & OBJ_ITEM and o.alive:
                    return o
    return None


def _build_bench(game, length=12, floor=3):
    """Ровная площадка у поверхности: пол + место под механизмы."""
    from units.common import TSIZE
    gm = game.game_map
    px = game.player.rect.centerx // TSIZE
    py = game.player.rect.centery // TSIZE
    top = gm.surface_top_at(px, py) or py
    x, y = px + 3, top - 1
    for dx in range(-3, length + 3):
        gm.set_static_tile(x + dx, y + 1, floor)
        gm.set_static_tile(x + dx, y, 0)
        gm.set_static_tile(x + dx, y - 1, 0)
        gm.set_static_tile(x + dx, y - 2, 0)
    # Игрок подбирает лежащие предметы вокруг себя (Player.get_item_rect),
    # поэтому стоять на стенде нельзя — он соберёт всё раньше воронки.
    # Но и уходить с экрана нельзя: тайлы обновляются только видимые.
    game.player.tp_to(((x - 12) * TSIZE, (y - 3) * TSIZE))
    game.screen_map.teleport_to_player()
    return x, y


def test_conveyor_carries_item_in_real_frames():
    """Предмет должен ЕХАТЬ по ленте настоящими кадрами.

    Баг, который это ловит: конвейер был полу-физическим, предмет
    проваливался сквозь него и переставал находиться в тайле над лентой —
    в игре конвейер выглядел полностью сломанным, хотя старый тест (с
    ручной раскладкой предметов) проходил.
    """
    from units.common import TSIZE
    game = fresh_world(200)
    gm = game.game_map
    x, y = _build_bench(game)
    for dx in range(0, 10):
        gm.set_static_tile(x + dx, y, 225)          # лента
    gm.add_item_of_index(11, 1, x, y - 1)

    item = _any_item(gm, x, y)
    assert item is not None, "предмет должен существовать"
    start_tile = item.rect.centerx // TSIZE

    _run_frames(game, 120)
    item = _any_item(gm, x, y)
    assert item is not None, "предмет не должен пропадать"
    assert item.rect.centerx // TSIZE > start_tile, "предмет должен уехать вправо"
    assert item.rect.centery // TSIZE == y - 1, \
        "предмет должен ЛЕЖАТЬ на ленте, а не провалиться сквозь неё"


def test_conveyor_direction_flips_on_right_click():
    """Правым кликом лента разворачивается — и предмет едет обратно."""
    from units.common import TSIZE
    game = fresh_world(201)
    gm = game.game_map
    x, y = _build_bench(game)
    for dx in range(-2, 10):
        gm.set_static_tile(x + dx, y, 225)
    conv = gm.get_tile_obj(*gm.to_chunk_xy(x, y), gm.get_static_tile(x, y)[3])
    gm.add_item_of_index(11, 1, x, y - 1)

    _run_frames(game, 60)
    right_x = _any_item(gm, x, y).rect.centerx

    for dx in range(-2, 10):                        # развернуть всю ленту
        tile = gm.get_static_tile(x + dx, y)
        gm.set_static_tile_state_img(x + dx, y, 0 if tile[2] else 1)
    assert conv.direction() == -1
    _run_frames(game, 60)
    assert _any_item(gm, x, y).rect.centerx < right_x, "после разворота — влево"


def test_conveyor_feeds_hopper_and_chest():
    """Полная цепочка фермы: лента везёт предмет в воронку, воронка кладёт
    его в сундук. Это то, ради чего логистика и существует."""
    game = fresh_world(202)
    gm = game.game_map
    x, y = _build_bench(game, length=14)
    for dx in range(0, 6):
        gm.set_static_tile(x + dx, y, 225)
    gm.set_static_tile(x + 6, y, 224)               # воронка в конце ленты
    gm.set_static_tile(x + 6, y + 1, 129)           # сундук под воронкой
    chest = gm.get_tile_obj(*gm.to_chunk_xy(x + 6, y + 1),
                            gm.get_static_tile(x + 6, y + 1)[3])
    gm.add_item_of_index(11, 3, x, y - 1)

    _run_frames(game, 400)
    in_chest = sum(c.count for c in chest.inventory if c)
    assert in_chest > 0, "предмет должен доехать до сундука"


def test_items_do_not_fall_through_conveyor_line():
    """Лента — сплошной блок: по ней можно и ходить, и возить. Если она
    снова станет проходимой, предметы посыплются сквозь ферму."""
    get_app()
    from units.Tiles import PHYSBODY_TILES, SEMIPHYSBODY_TILES
    assert 225 in PHYSBODY_TILES, "конвейер должен быть сплошным"
    assert 225 not in SEMIPHYSBODY_TILES


def test_imp_does_not_burn_in_lava():
    """Бес живёт в аду: если лава его жжёт, адские мобы вымирают сами, в
    собственном биоме, ещё до встречи с игроком."""
    from units.common import TSIZE, START_HELL_Y
    from units.Objects.Creatures import Imp, Wolf
    game = fresh_world(203)
    gm = game.game_map
    x, y = 40, START_HELL_Y + 100
    for dx in range(-4, 5):
        gm.set_static_tile(x + dx, y + 1, 3)        # дно
        gm.set_static_tile(x + dx, y, 140)          # лужа лавы
        for dy in range(1, 7):                      # выкопать полость над ней:
            gm.set_static_tile(x + dx, y - dy, 0)   # иначе существо стоит в породе
    game.player.tp_to((x * TSIZE, (y - 5) * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    game.update()

    imp = Imp(game, (x * TSIZE, (y - 1) * TSIZE))
    wolf = Wolf(game, ((x + 1) * TSIZE, (y - 1) * TSIZE))
    for creature in (imp, wolf):
        gm.add_dinamic_obj(*gm.to_chunk_xy(creature.rect.centerx // TSIZE,
                                           creature.rect.centery // TSIZE), creature)
    _run_frames(game, 90)
    assert imp.lives == imp.max_lives, f"бес не должен гореть в лаве ({imp.lives}/{imp.max_lives})"
    assert wolf.lives < wolf.max_lives, "а обычный зверь — должен, иначе тест ничего не проверяет"


def test_creatures_do_not_spawn_on_screen():
    """Существо, возникшее в кадре из ничего, читается как баг, а не как
    «пришло»."""
    from units.common import TSIZE
    game = fresh_world(204)
    gm = game.game_map
    px = game.player.rect.centerx // TSIZE
    py = game.player.rect.centery // TSIZE
    assert gm.spawn_is_visible(px, py), "под игроком — заведомо видно"
    assert gm.spawn_is_visible(px + 2, py), "рядом — тоже"
    from units.common import WSIZE
    far = px + gm.SPAWN_VIEW_MARGIN + WSIZE[0] // TSIZE
    assert not gm.spawn_is_visible(far, py), "далеко за экраном — можно"
    # и запас за кромкой экрана тоже закрыт
    edge = px + WSIZE[0] // 2 // TSIZE + gm.SPAWN_VIEW_MARGIN - 1
    assert gm.spawn_is_visible(edge, py), "у самой кромки рождать нельзя"


# ===================== электричество: сеть, вентили, циклы =====================
#
# Сигнальная сеть — самая «программируемая» часть игры, и до сих пор она была
# покрыта одним тестом на провод и лампу. Здесь схемы собираются целиком и
# гоняются тактами, как в игре: важна не отдельная функция, а поведение
# схемы во времени (фронты, задержки, обратные связи).

def _net(game, blocks):
    """Поставить схему: {(dx, dy): tile_id} вокруг базовой точки.

    Возвращает {(dx, dy): tile_obj} — только для блоков со своим классом.
    """
    from units.common import TSIZE
    gm = game.game_map
    bx, by = 60, 8
    for dy in range(-4, 5):                       # расчистить место под схему
        for dx in range(-4, 12):
            gm.set_static_tile(bx + dx, by + dy, 0)
    objs = {}
    for (dx, dy), tid in blocks.items():
        gm.set_static_tile(bx + dx, by + dy, tid)
        tile = gm.get_static_tile(bx + dx, by + dy)
        obj = gm.get_tile_obj(*gm.to_chunk_xy(bx + dx, by + dy), tile[3])
        if obj is not None:
            objs[(dx, dy)] = obj
    game.player.tp_to((bx * TSIZE, (by - 8) * TSIZE))
    game.screen_map.teleport_to_player()
    return objs


def _tick(game, objs, n=1):
    """Такт схемы: как в игре — сначала растёт tact, потом обновляются блоки.

    Порядок обновления внутри такта не фиксирован (в игре он растровый),
    поэтому схемы и не должны от него зависеть — на этом стоит вся
    конструкция с activated_tact.
    """
    for _ in range(n):
        game.tact += 1
        for obj in objs.values():
            obj.update(16)


def test_lever_powers_wire_chain_and_lamp():
    """Базовая цепь: рычаг → провода → лампа. Пока рычаг включён, лампа
    горит; выключили — гаснет (с допуском в один такт)."""
    game = fresh_world(300)
    objs = _net(game, {(0, 0): 214, (1, 0): 213, (2, 0): 213, (3, 0): 213, (4, 0): 215})
    lever, lamp = objs[(0, 0)], objs[(4, 0)]

    _tick(game, objs, 3)
    assert not lamp.is_active(), "без рычага лампа не горит"

    lever.on = True
    _tick(game, objs, 3)
    assert lamp.is_active(), "включённый рычаг должен зажечь лампу через провода"

    lever.on = False
    _tick(game, objs, 4)
    assert not lamp.is_active(), "выключенный рычаг должен погасить лампу"


def test_wire_gap_breaks_the_chain():
    """Разрыв в проводе должен рвать цепь: иначе сигнал «телепортируется»
    и схемы теряют смысл."""
    game = fresh_world(301)
    objs = _net(game, {(0, 0): 214, (1, 0): 213, (3, 0): 213, (4, 0): 215})
    objs[(0, 0)].on = True
    _tick(game, objs, 4)
    assert not objs[(4, 0)].is_active(), "через разрыв сигнал идти не должен"


def test_not_gate_inverts():
    """НЕ: горит, пока на входе пусто, и гаснет под сигналом."""
    game = fresh_world(302)
    objs = _net(game, {(0, 0): 214, (1, 0): 213, (2, 0): 216, (3, 0): 213, (4, 0): 215})
    lever, gate, lamp = objs[(0, 0)], objs[(2, 0)], objs[(4, 0)]

    _tick(game, objs, 4)
    assert gate.is_active(), "без входа вентиль НЕ должен быть включён"
    assert lamp.is_active(), "и должен питать лампу за собой"

    lever.on = True
    _tick(game, objs, 4)
    assert not gate.is_active(), "под сигналом вентиль НЕ должен погаснуть"


def test_and_gate_needs_both_inputs():
    """И: включается только когда есть оба входа.

    Входы разведены по РАЗНЫЕ стороны вентиля не для красоты: сеть связна
    по восьми соседям, включая диагональ, поэтому два провода, лежащие
    рядом, — это один провод, и один рычаг зажёг бы оба «входа».
    """
    game = fresh_world(303)
    objs = _net(game, {(0, 0): 214, (1, 0): 213,
                       (2, 0): 217,
                       (3, 0): 213, (4, 0): 214})
    a, b, gate = objs[(0, 0)], objs[(4, 0)], objs[(2, 0)]

    a.on = True
    _tick(game, objs, 4)
    assert not gate.is_active(), "одного входа для И мало"

    b.on = True
    _tick(game, objs, 4)
    assert gate.is_active(), "два входа должны включить И"

    a.on = False
    _tick(game, objs, 4)
    assert not gate.is_active(), "убрали вход — И выключается"


def test_or_gate_needs_any_input():
    """ИЛИ: хватает одного входа."""
    game = fresh_world(304)
    objs = _net(game, {(0, 0): 214, (1, 0): 213,
                       (2, 0): 218,
                       (3, 0): 213, (4, 0): 214})
    a, b, gate = objs[(0, 0)], objs[(4, 0)], objs[(2, 0)]

    _tick(game, objs, 4)
    assert not gate.is_active(), "без входов ИЛИ выключен"

    a.on = True
    _tick(game, objs, 4)
    assert gate.is_active(), "одного входа для ИЛИ достаточно"

    b.on = True
    _tick(game, objs, 4)
    assert gate.is_active(), "два входа тоже включают ИЛИ"


def test_delay_block_one_front_one_pulse():
    """Задержка стреляет ОДИН раз на фронт сигнала, а не каждый такт, пока
    рычаг включён: иначе за секунду удержания она выдала бы 60 импульсов и
    перестала быть задержкой."""
    game = fresh_world(305)
    objs = _net(game, {(0, 0): 214, (1, 0): 213, (2, 0): 220, (3, 0): 215})
    lever, delay, lamp = objs[(0, 0)], objs[(2, 0)], objs[(3, 0)]

    lever.on = True
    pulses = 0
    was = False
    for _ in range(delay.delay * 3):
        _tick(game, objs)
        now = lamp.is_active()
        pulses += now and not was          # считаем фронты на выходе
        was = now
    assert pulses >= 1, "задержка должна сработать хотя бы раз"
    assert pulses <= 4, f"на одно удержание рычага — не поток импульсов, получено {pulses}"


def test_timer_pulses_the_network_periodically():
    """Таймер — авто-клокер: сам, без игрока, зажигает подключённую сеть."""
    game = fresh_world(306)
    objs = _net(game, {(0, 0): 211, (1, 0): 213, (2, 0): 215})
    timer, lamp = objs[(0, 0)], objs[(2, 0)]

    lit = 0
    for _ in range(timer.interval * 2 + 4):
        _tick(game, objs)
        lit += lamp.is_active()
    assert lit > 0, "таймер должен хотя бы раз зажечь лампу"
    assert lit < timer.interval * 2, "и не должен держать её постоянно — это клокер"


def test_not_gate_ring_does_not_hang():
    """Кольцо из НЕ — классическая обратная связь: схема не имеет права
    зациклить игру, для этого bfs_activate и обходит сеть очередью с
    visited, а не рекурсией."""
    game = fresh_world(307)
    objs = _net(game, {(0, 0): 216, (1, 0): 213, (2, 0): 216, (3, 0): 213,
                       (4, 0): 216, (5, 0): 213})
    states = set()
    for _ in range(60):                    # если схема повесит игру — тест не закончится
        _tick(game, objs)
        states.add(tuple(o.is_active() for o in objs.values()))
    assert states, "схема должна отработать без зависания"


def test_dense_wire_grid_does_not_recurse():
    """Плотная сетка проводов: обход сети — очередь, а не рекурсия. На
    рекурсии такая сетка ловила RecursionError."""
    game = fresh_world(308)
    blocks = {(0, 0): 214}
    for dx in range(1, 10):
        for dy in range(-3, 4):
            blocks[(dx, dy)] = 213
    objs = _net(game, blocks)
    objs[(0, 0)].on = True
    _tick(game, objs, 3)
    powered = sum(1 for (dx, dy), o in objs.items() if dx > 0 and o.is_active())
    assert powered > 50, f"сигнал должен залить всю сетку, залил {powered}"


def test_pressure_plate_follows_player_presence():
    """Плита — датчик присутствия: держит сеть, пока игрок стоит, и
    отпускает, когда он сошёл."""
    from units.common import TSIZE
    game = fresh_world(309)
    objs = _net(game, {(0, 0): 212, (1, 0): 213, (2, 0): 215})
    plate, lamp = objs[(0, 0)], objs[(2, 0)]

    game.player.rect.center = plate.rect.center
    _tick(game, objs, 3)
    assert plate.pressed and lamp.is_active(), "под игроком плита должна питать сеть"

    game.player.rect.center = (plate.rect.centerx + TSIZE * 20, plate.rect.centery)
    _tick(game, objs, 4)
    assert not plate.pressed, "игрок ушёл — плита отпущена"
    assert not lamp.is_active(), "и лампа гаснет"


def test_engine_drives_chopper_through_wire():
    """Схема целиком: двигатель на дереве гонит лесоруба через провод.
    Именно так собирается ферма дерева, и именно это должно работать."""
    game = fresh_world(310)
    gm = game.game_map
    objs = _net(game, {(0, 0): 228, (1, 0): 213, (2, 0): 227})
    engine, chopper = objs[(0, 0)], objs[(2, 0)]
    from units.Objects.Items import ItemsTile
    engine.inventory.put_to_inventory(ItemsTile(game, 11, count=1))

    bx, by = chopper.tx, chopper.ty
    for dy in range(1, 4):
        gm.set_static_tile(bx, by - dy, 110)        # ствол над лесорубом
    assert gm.get_static_tile_type(bx, by - 1) == 110

    _tick(game, objs, engine.period + 4)
    assert gm.get_static_tile_type(bx, by - 1, default=0) == 0, \
        "двигатель должен был запустить лесоруба через провод"


def test_gate_does_not_latch_itself_on():
    """Вентиль не должен считать входом то, что сам же и запитал.

    Сеть связна по восьми соседям и не имеет направления, поэтому вентиль
    питал собственные входные провода: включившись один раз, И и ИЛИ
    больше никогда не гасли, и любая схема с ними была одноразовой.
    """
    game = fresh_world(311)
    objs = _net(game, {(0, 0): 214, (1, 0): 213,
                       (2, 0): 218,
                       (3, 0): 213, (4, 0): 215})
    lever, gate, lamp = objs[(0, 0)], objs[(2, 0)], objs[(4, 0)]

    lever.on = True
    _tick(game, objs, 4)
    assert gate.is_active() and lamp.is_active(), "схема должна включиться"

    lever.on = False
    _tick(game, objs, 6)
    assert not gate.is_active(), "вентиль обязан погаснуть вслед за рычагом"
    assert not lamp.is_active(), "и отпустить сеть за собой"


# ===================== озёра =====================

def _find_lake(gm, cells=range(-10, 11)):
    from units.Map.GameMap import lake_site
    for cell in cells:
        site = lake_site(cell, gm.base_generation)
        if site is not None:
            return site
    return None


def test_lakes_are_generated_as_flat_basins():
    """Вода в игре была, но ставилась как «растение» с шансом 0.05 — то есть
    одиночными тайлами на склонах. Озеро — это ровное зеркало и чашеобразное
    дно, а не мазок воды по холму."""
    from units.common import LAKE_MAX_DEPTH
    for seed in (1, 7, 21):
        game = fresh_world(seed)
        gm = game.game_map
        site = _find_lake(gm)
        assert site is not None, f"сид {seed}: озёр не нашлось вообще"
        center, r, level = site

        widths = {}
        for tx in range(center - r, center + r + 1):
            col = [ty for ty in range(level - 10, level + LAKE_MAX_DEPTH + 3)
                   if gm.get_static_tile_type(tx, ty, default=0, create_chunk=True) == 120]
            if col:
                widths[tx] = (min(col), max(col))
        assert len(widths) >= 8, f"сид {seed}: озеро шириной {len(widths)} — это лужа"
        # Зеркало ровное: верхняя вода во всех колонках на одном уровне.
        tops = {v[0] for v in widths.values()}
        assert len(tops) == 1, f"сид {seed}: зеркало неровное, уровни {sorted(tops)}"
        # Дно — чаша: в середине глубже, чем у берега.
        mid_depth = max(v[1] for v in widths.values()) - level
        edge = min(widths), max(widths)
        edge_depth = max(widths[edge[0]][1], widths[edge[1]][1]) - level
        assert mid_depth > edge_depth, f"сид {seed}: дно плоское, это не чаша"
        assert mid_depth <= LAKE_MAX_DEPTH, "озеро не должно быть колодцем"


def test_lake_has_open_sky_above_the_water():
    """Над озером вырезается берег: без этого озеро, вписанное в склон,
    вырождалось в узкую шахту — замер давал полосу в 5 тайлов при радиусе 20."""
    game = fresh_world(21)
    gm = game.game_map
    site = _find_lake(gm)
    assert site is not None
    center, r, level = site
    for dy in range(1, 4):
        t = gm.get_static_tile_type(center, level - dy, default=0, create_chunk=True)
        assert t in (0, 104, 101, 102), f"над зеркалом должно быть открыто, а не {t}"


def test_lakes_are_only_in_the_middle_world():
    """В аду лава, в космосе вакуум — воде там не место."""
    get_app()
    from units.Map.GameMap import lake_tile_at
    from units.common import START_HELL_Y, START_SPACE_Y, BOTTOM_MIDDLE_WORLD, TOP_MIDDLE_WORLD
    base = 12345
    for ty in (START_HELL_Y + 50, BOTTOM_MIDDLE_WORLD + 10,
               START_SPACE_Y - 50, TOP_MIDDLE_WORLD - 10):
        for tx in range(0, 600, 37):
            assert lake_tile_at(tx, ty, base) is None, f"вода на y={ty}"


def test_lake_lookup_is_a_pure_function_of_seed():
    """Как и terrain_is_solid: озеро можно узнать заранее, без генерации
    чанка, — иначе генератор и проба однажды разъедутся."""
    game = fresh_world(7)
    gm = game.game_map
    from units.Map.GameMap import lake_tile_at
    site = _find_lake(gm)
    assert site is not None
    center, r, level = site
    checked = 0
    for dy in range(1, 5):
        predicted = lake_tile_at(center, level + dy, gm.base_generation)
        tile = gm.get_static_tile(center, level + dy, create_chunk=True)
        if predicted is not None and predicted[0] == 120:
            checked += 1
            assert tile[0] == 120, f"проба обещала воду на y={level + dy}, в мире {tile[0]}"
            # Кадр — часть ответа пробы: уровень заполнения воды считает та же
            # функция, что и форму чаши, и мир обязан положить именно его.
            assert tile[2] == predicted[1], \
                f"уровень воды на y={level + dy}: проба {predicted[1]}, мир {tile[2]}"
    assert checked, "проба не нашла воды в центре озера — тест ничего не проверил"


def test_lake_generation_is_free_for_chunks_without_lakes():
    """Поиск площадки под озеро — скан столба на 1650 тайлов. Он обязан
    платиться только там, где озеро действительно есть: замеры давали +61%
    к стоимости генерации чанка без общего кэша и +29% без дешёвой проверки
    по горизонтали."""
    game = fresh_world(1)
    gm = game.game_map
    from units.Map.GameMap import lake_shape
    import inspect
    src = inspect.getsource(type(gm)._chunk_touches_lake)
    assert "lake_shape" in src, "сначала должна идти дешёвая проверка по горизонтали"
    assert src.index("lake_shape") < src.index("lake_site"), \
        "дорогой поиск уровня не должен идти раньше дешёвой отсечки"
    assert lake_shape(0, gm.base_generation) is None or \
        len(lake_shape(0, gm.base_generation)) == 2, "форма — только центр и радиус"


# ===================== многоуровневая вода и полости =====================

def test_water_frame_zero_is_the_full_tile():
    """Кадр 0 обязан быть ПОЛНЫМ тайлом воды.

    state_img по умолчанию 0: так лежит вся вода в старых мирах и так её ставит
    игрок из инвентаря. При порядке кадров «1..4» вся уже существующая вода
    превратилась бы в плёнку на дне тайла."""
    get_app()
    from units.Tiles import water_imgs, water_frame, WATER_LEVELS
    assert water_frame() == 0, "полная вода — это кадр 0"
    assert len(water_imgs) == WATER_LEVELS * 2, "четыре уровня обычной и четыре глубинной"
    full = water_imgs[0]
    # у полного тайла верхняя строка непрозрачна, у плёнки — нет
    assert full.get_at((16, 1))[3] > 0, "кадр 0 не заполняет тайл целиком"
    assert water_imgs[water_frame(1)].get_at((16, 1))[3] == 0, "плёнка не должна быть полной"
    assert water_frame(4, deep=True) != water_frame(4), "глубинная вода — отдельный кадр"


def test_lake_shore_is_a_shoal_not_a_wall():
    """У берега ряд зеркала заполнен не до конца — иначе озеро обрывается
    вертикальной стеной в полный блок, и берега как явления нет."""
    from units.Tiles import water_frame, WATER_LEVELS
    game = fresh_world(21)
    gm = game.game_map
    from units.Map.GameMap import lake_tile_at
    site = _find_lake(gm)
    assert site is not None
    center, r, level = site
    surface = [lake_tile_at(tx, level + 1, gm.base_generation)
               for tx in range(center - r, center + r + 1)]
    water = [t for t in surface if t is not None and t[0] == 120]
    assert water, "в ряду зеркала нет воды вообще"
    assert water[0][1] != water_frame(WATER_LEVELS), "у берега вода должна быть мельче"
    assert any(t[1] == water_frame(WATER_LEVELS) for t in water), \
        "в середине озеро обязано быть полным"


def test_lake_has_depth_shading():
    """Ниже третьего ряда вода рисуется глубинным кадром: без этого водоём —
    однородная синяя заливка без ощущения толщи."""
    from units.Tiles import WATER_LEVELS
    game = fresh_world(21)
    gm = game.game_map
    from units.Map.GameMap import lake_tile_at
    site = max((s for s in (__import__("units.Map.GameMap", fromlist=["lake_site"])
                            .lake_site(c, gm.base_generation) for c in range(-10, 11))
                if s is not None), key=lambda s: s[1])
    center, r, level = site
    deep = [lake_tile_at(center, level + dy, gm.base_generation) for dy in (1, 4)]
    assert deep[0] is not None and deep[1] is not None, "озеро слишком мелкое для проверки"
    assert deep[0][1] < WATER_LEVELS, "верхний ряд — обычная вода"
    assert deep[1][1] >= WATER_LEVELS, "нижние ряды — глубинный кадр"


def test_lake_level_is_always_inside_the_water_band():
    """Площадка под озеро искалась по ВСЕМУ столбу, включая атмосферу выше
    границы среднего мира. Такое озеро lake_tile_at раскладывать отказывался, и
    клетка решётки молча оставалась без воды: на сиде 21 зеркало приходилось на
    -768 при границе -650."""
    from units.common import LAKE_TOP_MIN, LAKE_TOP_MAX
    from units.Map.GameMap import lake_site, lake_tile_at
    for seed in (1, 7, 21):
        game = fresh_world(seed)
        base = game.game_map.base_generation
        for cell in range(-10, 11):
            site = lake_site(cell, base)
            if site is None:
                continue
            center, r, level = site
            assert LAKE_TOP_MIN < level < LAKE_TOP_MAX, \
                f"сид {seed}: зеркало на {level} вне полосы воды"
            got = lake_tile_at(center, level + 1, base)
            assert got is not None and got[0] == 120, \
                f"сид {seed}: озеро есть в решётке, а воды в нём нет"


def test_water_pocket_is_sealed_and_has_a_waterline():
    """Полость с водой внутри острова: вода не течёт, поэтому полость обязана
    быть запечатана в породе, а над зеркалом должен быть воздух — иначе линии
    воды не видно и находка выглядит просто синим прямоугольником."""
    from units.Map.Water import pocket_site, POCKET_WALL
    from units.Tiles import water_frame, WATER_LEVELS
    game = fresh_world(5)
    gm = game.game_map
    base = gm.base_generation
    found = 0
    for cx in range(-10, 11):
        for cy in range(2, 18):
            site = pocket_site(cx, cy, base)
            if site is None:
                continue
            found += 1
            # воздух над зеркалом
            above = gm.get_static_tile_type(site.cx, site.mirror - 1, default=0,
                                            create_chunk=True)
            assert above == 0, f"над зеркалом {above}, а должен быть воздух"
            # вода под зеркалом и на самом зеркале
            for ty in (site.mirror, site.mirror + 1):
                if ty > site.cy + site.ry:
                    continue
                tile = gm.get_static_tile(site.cx, ty, create_chunk=True)
                assert tile[0] == 120, f"в полости на y={ty} стоит {tile[0]}"
                assert tile[2] >= WATER_LEVELS, "вода в полости — глубинный кадр"
            mirror_tile = gm.get_static_tile(site.cx, site.mirror, create_chunk=True)
            assert mirror_tile[2] == water_frame(site.fill, deep=True), \
                "ряд зеркала обязан быть того уровня, который посчитала полость"
            # породу проверяем по краям: полость не должна вскрываться
            for dx in (-(site.rx + POCKET_WALL), site.rx + POCKET_WALL):
                side = gm.get_static_tile_type(site.cx + dx, site.cy, default=0,
                                               create_chunk=True)
                assert side not in (0, 120), f"полость вскрыта сбоку: {side}"
            if found >= 3:
                return
    assert found, "полостей с водой не нашлось вообще"


def test_water_pocket_lookup_is_a_pure_function_of_seed():
    """Как озеро и подземелье: полость можно узнать заранее, без генерации
    чанка. Иначе проба и генератор однажды разъедутся."""
    from units.Map.Water import pocket_site, water_pocket_tile_at
    game = fresh_world(5)
    gm = game.game_map
    base = gm.base_generation
    site = None
    for cx in range(-10, 11):
        for cy in range(2, 18):
            site = pocket_site(cx, cy, base)
            if site is not None:
                break
        if site is not None:
            break
    assert site is not None
    checked = 0
    for ty in range(site.cy - site.ry, site.cy + site.ry + 1):
        predicted = water_pocket_tile_at(site.cx, ty, base)
        if predicted is None:
            continue
        checked += 1
        tile = gm.get_static_tile(site.cx, ty, create_chunk=True)
        assert tile[0] == predicted[0], f"y={ty}: проба {predicted[0]}, мир {tile[0]}"
        if predicted[0] == 120:
            assert tile[2] == predicted[1], f"y={ty}: уровень воды разъехался"
    assert checked, "проба не нашла полость там, где она есть"


# ===================== физика воды =====================

def _water_arena(game, x=70, y=8, w=30):
    """Ровная площадка с полом и чистым воздухом над ним."""
    gm = game.game_map
    for tx in range(x - 4, x + w):
        gm.set_static_tile(tx, y + 1, 3)
        for dy in range(0, 8):
            gm.set_static_tile(tx, y - dy, 0)
    gm.water_flow.queue.clear()
    gm.water_flow.pending.clear()
    return x, y


def _pour(gm, tx, ty, rows=4, level=4):
    from units.Tiles import water_frame
    for dy in range(rows):
        gm.set_static_tile(tx, ty - dy, [120, 0, water_frame(level), 0])


def _water_volume(gm, x0, x1, y0, y1):
    from units.Tiles import water_frame_level
    total = 0
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            tile = gm.get_static_tile(tx, ty, create_chunk=True)
            if tile and tile[0] == 120:
                total += water_frame_level(tile[2])
    return total


def test_water_falls_spreads_and_settles():
    """Вода была рельефом: поставленный в воздухе блок воды там и стоял.
    Теперь столб падает, растекается по полу — и поток ЗАТУХАЕТ: очередь
    пустеет, иначе водоём тикал бы вечно."""
    game = fresh_world(700)
    gm = game.game_map
    x, y = _water_arena(game)
    _pour(gm, x + 10, y)
    for tact in range(0, 600):
        gm.water_flow.tick(tact)
    assert not gm.water_flow.queue, "поток не успокоился — вода тикала бы вечно"
    row = [gm.get_static_tile(tx, y, create_chunk=True)[0] for tx in range(x + 5, x + 16)]
    assert row.count(120) >= 5, f"вода не растеклась по полу: {row}"
    assert gm.get_static_tile(x + 10, y - 3, create_chunk=True)[0] == 0, \
        "вода осталась висеть в воздухе"


def test_water_volume_is_conserved():
    """Ни одна единица воды не должна ни исчезнуть, ни появиться: иначе
    водоём либо высыхает сам, либо становится бесконечным источником."""
    game = fresh_world(701)
    gm = game.game_map
    x, y = _water_arena(game, w=40)
    _pour(gm, x + 12, y, rows=4, level=4)
    before = _water_volume(gm, x - 4, x + 36, y - 8, y)
    for tact in range(0, 800):
        gm.water_flow.tick(tact)
    after = _water_volume(gm, x - 4, x + 36, y - 8, y)
    assert before == 16, f"налили не 16 единиц, а {before}"
    assert after == before, f"объём воды изменился: {before} -> {after}"


def test_water_does_not_eat_blocks():
    """Вода течёт только в воздух и в воду. Вытеснение блока потоком — это
    разрушение мира водой, и такого решения никто не принимал."""
    game = fresh_world(702)
    gm = game.game_map
    x, y = _water_arena(game)
    gm.set_static_tile(x + 12, y, 3)            # камень на пути растекания
    gm.set_static_tile(x + 13, y, 104)          # и трава
    _pour(gm, x + 10, y)
    for tact in range(0, 600):
        gm.water_flow.tick(tact)
    assert gm.get_static_tile(x + 12, y, create_chunk=True)[0] == 3, "вода съела камень"
    assert gm.get_static_tile(x + 13, y, create_chunk=True)[0] == 104, "вода съела траву"


def test_generated_lake_does_not_tick_until_disturbed():
    """Главное решение всей физики: водоём в равновесии не стоит НИЧЕГО.
    Озеро на сотни тайлов не должно попадать в очередь просто потому, что
    сгенерировалось."""
    game = fresh_world(21)
    gm = game.game_map
    site = _find_lake(gm)
    assert site is not None
    center, r, level = site
    for tx in range(center - r, center + r + 1):
        gm.get_static_tile_type(tx, level + 1, default=0, create_chunk=True)
    gm.water_flow.queue.clear()
    gm.water_flow.pending.clear()
    moved = sum(gm.water_flow.tick(t) for t in range(0, 200))
    assert moved == 0, "спокойное озеро не должно течь само по себе"
    # А вот прокоп в дне обязан его разбудить
    gm.set_static_tile(center, level + 4, 0)
    assert gm.water_flow.queue, "правка тайла рядом с водой не разбудила поток"


def test_dug_lake_bottom_drains_the_water():
    """Прокопал дно — вода пошла в дырку. Это то, зачем физика воды нужна
    игроку: водоём стал частью мира, а не рисунком на нём."""
    game = fresh_world(703)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    # ванна: пол и стенки, в ней вода
    for tx in range(x + 8, x + 13):
        gm.set_static_tile(tx, y + 1, 3)
    gm.set_static_tile(x + 7, y, 3)
    gm.set_static_tile(x + 13, y, 3)
    for tx in range(x + 8, x + 13):
        gm.set_static_tile(tx, y, [120, 0, 0, 0])
    for tact in range(0, 200):
        gm.water_flow.tick(tact)
    assert gm.get_static_tile(x + 10, y, create_chunk=True)[0] == 120, "вода не удержалась в ванне"
    for ty in range(y + 1, y + 5):
        gm.set_static_tile(x + 10, ty, 0)       # пробили дно
    for tact in range(0, 400):
        gm.water_flow.tick(tact)
    below = _water_volume(gm, x + 8, x + 12, y + 1, y + 5)
    assert below > 0, "вода не потекла в пробитое дно"


# ===================== плавание =====================

def _flood(gm, x, y, w=6, depth=5):
    """Залить водой прямоугольник и удержать её стенками."""
    for tx in range(x - 1, x + w + 1):
        gm.set_static_tile(tx, y + 1, 3)
    for ty in range(y, y - depth, -1):
        gm.set_static_tile(x - 1, ty, 3)
        gm.set_static_tile(x + w, ty, 3)
        for tx in range(x, x + w):
            gm.set_static_tile(tx, ty, [120, 0, 0, 0])
    gm.water_flow.queue.clear()
    gm.water_flow.pending.clear()


def test_player_sinks_slowly_in_water():
    """Вода была проходимой пустотой: падали в неё с той же скоростью, что и
    в воздухе. Теперь она держит — иначе в вертикальном мире у воды нет
    вообще никакой функции."""
    from units.common import TSIZE, WATER_SINK_SPEED
    game = fresh_world(710)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 5, y, w=6, depth=6)
    player = game.player
    player.active = True
    player.first_fall = False
    player.tp_to(((x + 7) * TSIZE, (y - 4) * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 30)
    assert player.swimming, "игрок в воде обязан плыть"
    assert player.vertical_momentum <= WATER_SINK_SPEED + 1e-9, \
        f"в воде тонут медленно, а скорость {player.vertical_momentum}"


def test_player_swims_up_while_holding_the_key():
    """Из воды выплывают, а не выпрыгивают одним разрешённым прыжком:
    гребок повторяется, пока держат клавишу."""
    from units.common import TSIZE
    game = fresh_world(711)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 5, y, w=6, depth=6)
    player = game.player
    player.active = True
    player.first_fall = False
    player.tp_to(((x + 7) * TSIZE, (y - 1) * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 10)
    start = player.rect.y
    player.on_up = True
    player.jump_count = player.max_jump_count      # прыжки кончились — плыть это не мешает
    _run_frames(game, 60)
    player.on_up = False
    assert player.rect.y < start - TSIZE, \
        f"игрок не выплыл: {start} -> {player.rect.y}"


def test_water_saves_from_fall_damage():
    """Упасть в воду должно быть безопасно — это первая польза воды в
    вертикальном мире."""
    from units.common import TSIZE
    game = fresh_world(712)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    for dy in range(0, 40):
        for tx in range(x + 4, x + 12):
            gm.set_static_tile(tx, y - dy, 0)
    _flood(gm, x + 5, y, w=6, depth=6)
    player = game.player
    player.active = True
    player.first_fall = False
    player.tp_to(((x + 7) * TSIZE, (y - 35) * TSIZE))
    game.screen_map.teleport_to_player()
    lives = player.lives
    _run_frames(game, 150)
    assert player.lives == lives, f"вода не спасла от падения: {lives} -> {player.lives}"


def test_shallow_water_is_not_deep_enough_to_swim():
    """Плёнка воды на дне тайла — это лужа: по ней ходят. Иначе уровни
    заполнения ничего не значат для физики."""
    from units.common import TSIZE
    from units.Tiles import water_frame
    game = fresh_world(713)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    for tx in range(x + 5, x + 11):
        gm.set_static_tile(tx, y, [120, 0, water_frame(1), 0])
    player = game.player
    player.active = True
    player.tp_to(((x + 7) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 10)
    assert not player.swimming, "в луже нельзя плавать"


def test_land_creature_floats_instead_of_walking_the_bottom():
    """Корова, свалившаяся в озеро, раньше стояла на его дне до конца жизни
    мира: вода её не держала вообще."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow
    game = fresh_world(714)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 5, y, w=8, depth=7)
    cow = _place(game, Cow, x + 8, y - 1)
    game.screen_map.teleport_to_player()
    bottom_start = cow.rect.bottom
    for tact in range(120):
        cow.update(tact, 1000 / 60)
    assert cow.rect.bottom <= bottom_start + TSIZE, \
        f"корова утонула на дно: {bottom_start} -> {cow.rect.bottom}"


# ===================== водные твари =====================

def test_fish_stays_in_the_water():
    """Плавающему существу граница воды не мешает, а ДЕРЖИТ: рыба
    разворачивается у берега так же, как наземное существо у обрыва."""
    from units.Objects.Creatures import Fish
    game = fresh_world(720)
    gm = game.game_map
    x, y = _water_arena(game, w=24)
    _flood(gm, x + 5, y, w=10, depth=6)
    fish = _place(game, Fish, x + 9, y - 3)
    game.screen_map.teleport_to_player()
    assert fish.use_gravity is False, "рыба не должна падать"
    for tact in range(240):
        fish.update(tact, 1000 / 60)
        assert fish.in_water(), f"рыба вышла из воды на такте {tact}: {fish.rect.topleft}"
    assert fish.lives == fish.max_lives, "рыба в воде не должна получать урон"


def test_fish_suffocates_out_of_water():
    """Рыба, выброшенная обмелевшим озером на берег, должна биться на берегу —
    а не исчезать в тот же кадр и не жить в воздухе вечно."""
    from units.Objects.Creatures import Fish
    game = fresh_world(721)
    game_map = game.game_map
    x, y = _water_arena(game, w=20)
    fish = _place(game, Fish, x + 8, y - 4)      # в воздухе
    game.screen_map.teleport_to_player()
    assert not fish.in_water()
    lives = fish.lives
    for tact in range(int(fish.AIR_DAMAGE_PERIOD * 3)):
        fish.update(tact, 1000 / 60)
    assert fish.lives < lives, "на суше рыба обязана задыхаться"
    assert fish.use_gravity, "вне воды рыба падает"


def test_water_creatures_spawn_in_lakes():
    """Наземный спавн привязан к дёрну и воду не видит вообще — до этого в
    водоёмах не было никого."""
    from units.Objects.Creatures import SwimmingCreature
    from units.Map.GameMap import lake_site
    game = fresh_world(21)
    gm = game.game_map
    found = 0
    for cell in range(-10, 11):
        site = lake_site(cell, gm.base_generation)
        if site is None:
            continue
        cx0, cy0 = site[0] // 32, site[2] // 32
        for cx in range(cx0 - 1, cx0 + 2):
            for cy in range(cy0 - 1, cy0 + 2):
                for obj in gm.generate_chunk(cx, cy)[1]:
                    if isinstance(obj, SwimmingCreature):
                        found += 1
                        assert obj.in_water(), \
                            f"{type(obj).__name__} появился не в воде: {obj.rect.topleft}"
    assert found, "в озёрах не появилось ни одной водной твари"


def test_gulls_spawn_over_the_water():
    """Чайка — единственный признак водоёма, видимый издалека. Лимит существ
    на чанк мал, а рыбья стая забирает его целиком, поэтому чайки ставятся
    первыми: при обратном порядке их не появлялось вообще (замер — ноль на
    пяти сидах)."""
    from units.Objects.Creatures import Gull
    from units.Map.GameMap import lake_site
    game = fresh_world(5)
    gm = game.game_map
    gulls = 0
    for cell in range(-10, 11):
        site = lake_site(cell, gm.base_generation)
        if site is None:
            continue
        cx0, cy0 = site[0] // 32, site[2] // 32
        for cx in range(cx0 - 1, cx0 + 2):
            for cy in range(cy0 - 1, cy0 + 2):
                gulls += sum(1 for o in gm.generate_chunk(cx, cy)[1] if isinstance(o, Gull))
    assert gulls, "над водой не появилось ни одной чайки"


def test_deep_lurker_lives_only_in_sealed_pockets():
    """Глубинник существует ради того, чтобы находка «пустота в камне, а в ней
    зеркало» не была бесплатной. В открытом озере его быть не должно.

    Чанки берём по РЕШЁТКЕ ПОЛОСТЕЙ, а не подряд: полость — одна на ~18 000
    тайлов, глубинник выпадает не в каждой, и слепой обход прямоугольника
    зависел от того, куда попали чанки (правка соседнего генератора однажды
    оставила тест вообще без глубинников)."""
    from units.Objects.Creatures import DeepLurker
    from units.Map.Water import water_pocket_tile_at, pocket_site
    game = fresh_world(5)
    gm = game.game_map
    base = gm.base_generation
    checked = 0
    for cx in range(-14, 15):
        for cy in range(2, 24):
            site = pocket_site(cx, cy, base)
            if site is None:
                continue
            chunk = gm.generate_chunk(site.cx // 32, site.cy // 32)
            for obj in chunk[1]:
                if isinstance(obj, DeepLurker):
                    checked += 1
                    tx, ty = obj.rect.centerx // 32, obj.rect.centery // 32
                    assert water_pocket_tile_at(tx, ty, base) is not None, \
                        "глубинник оказался вне полости"
    assert checked, "глубинников не нашлось — тест ничего не проверил"


def test_hawk_dives_to_the_player_instead_of_hovering():
    """Ястреб — первая угроза, приходящая СВЕРХУ. Без этого он висел бы на
    своей высоте и «охотился», не долетая: горизонтально догоняет, вертикально
    нет."""
    from units.common import TSIZE
    from units.Objects.Creatures import Hawk, ST_CHASE
    game = fresh_world(722)
    x, y = _flat_arena(game, w=30)
    hawk = _place(game, Hawk, x + 10, y - 12)
    game.player.active = True
    game.player.tp_to(((x + 10) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    hawk.state = ST_CHASE
    hawk.update_altitude(0)
    assert hawk.target_y == game.player.rect.y, \
        f"в погоне ястреб обязан идти на высоту игрока: {hawk.target_y}"


# ===================== управление, население, звери =====================

def test_chest_closes_by_esc_and_e():
    """Из сундука можно было выйти ТОЛЬКО через паузу: базовый обработчик
    закрывал экран, но его результат терялся, поэтому сцена получала то же
    нажатие и открывала паузу. E при этом закрывала инвентарь ПОД сундуком."""
    import pygame as pg
    game = fresh_world(920)
    gm = game.game_map
    gm.set_static_tile(5, 0, 129)
    chest = _tile_obj(gm, 5, 0)
    ui = game.blocks_ui_manager.blocks_ui[129]
    for key in (pg.K_ESCAPE, pg.K_e):
        game.blocks_ui_manager.set_block(chest)
        assert ui.opened, "сундук не открылся"
        handled = game.blocks_ui_manager.pg_event(pg.event.Event(pg.KEYDOWN, key=key))
        assert handled, f"нажатие {pg.key.name(key)} не считается обработанным — " \
                        "сцена откроет паузу поверх сундука"
        assert not ui.opened, f"сундук не закрылся по {pg.key.name(key)}"
        assert not ui.player_inventory_ui.opened, \
            "инвентарь игрока остался открытым и продолжает перехватывать управление"


def test_population_near_player_is_capped():
    """За пять минут на острове собиралось два десятка существ: подселение шло
    раз в пять минут на КАЖДЫЙ чанк, счётчик чанка считал «сколько я породил за
    всю жизнь», а ночной множитель умножал не предел, а остаток."""
    from units.common import FPS, OBJ_CREATURE, CHUNK_CREATURE_LIMIT
    game = fresh_world(921)
    gm = game.game_map
    game.player.tp_to((0, 0))
    game.screen_map.teleport_to_player()
    # полчаса мира: подселение успевает сработать много раз
    for step in range(60):
        game.tact += FPS * 60
        gm._crowd_cache = None
        for chunk in list(gm.game_map.values()):
            gm.update_chunk(chunk)
    near = gm.creatures_near_player()
    assert near <= gm.CREATURE_SOFT_CAP + CHUNK_CREATURE_LIMIT * 2, \
        f"вокруг игрока развелось {near} существ"


def test_night_multiplier_does_not_break_the_chunk_limit():
    """Ночью гуще — но не «девять существ при пределе четыре»: множитель идёт
    на предел, а не на уже посчитанный остаток."""
    from units.common import (FPS, NIGHT_SPAWN_MULT, OBJ_CREATURE, DAY_LENGTH,
                              CHUNK_CREATURE_LIMIT)
    game = fresh_world(922)
    gm = game.game_map
    gm.world_time = int(DAY_LENGTH * 0.8)      # ночь
    game.player.tp_to((0, 0))
    game.screen_map.teleport_to_player()
    limit = int(CHUNK_CREATURE_LIMIT * NIGHT_SPAWN_MULT)
    for step in range(20):
        game.tact += FPS * 60
        gm._crowd_cache = None
        for chunk in list(gm.game_map.values()):
            gm.update_chunk(chunk)
    worst = max((sum(1 for o in ch[1] if o.class_obj & OBJ_CREATURE and o.alive)
                 for ch in gm.game_map.values()), default=0)
    assert worst <= limit + CHUNK_CREATURE_LIMIT, \
        f"в одном чанке {worst} существ при ночном пределе {limit}"


def test_predator_hunts_prey():
    """Существа не замечали друг друга: волк и заяц могли стоять в одном тайле,
    и мир читался как набор мишеней для игрока."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf, Cow, ST_CHASE
    game = fresh_world(923)
    x, y = _flat_arena(game, w=40)
    wolf = _place(game, Wolf, x + 5, y)
    cow = _place(game, Cow, x + 7, y)
    game.player.active = True
    game.player.tp_to(((x + 39) * TSIZE, y * TSIZE))    # игрок далеко
    game.screen_map.teleport_to_player()
    lives = cow.lives
    chased = False
    for tact in range(600):
        wolf.update(tact, 1000 / 60)
        cow.update(tact, 1000 / 60)
        chased = chased or wolf.state == ST_CHASE
    assert chased, "волк не начал охоту"
    assert cow.lives < lives, f"волк не укусил корову: {lives} -> {cow.lives}"


def test_prey_runs_from_the_predator():
    """Добыча убегает от хищника тем же состоянием, что и от игрока."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf, Rabbit, ST_FLEE
    game = fresh_world(924)
    x, y = _flat_arena(game, w=40)
    wolf = _place(game, Wolf, x + 5, y)
    rabbit = _place(game, Rabbit, x + 9, y)
    game.player.active = True
    game.player.tp_to(((x + 39) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    started_at = rabbit.rect.centerx
    fled = False
    for tact in range(240):
        wolf.update(tact, 1000 / 60)
        rabbit.update(tact, 1000 / 60)
        fled = fled or rabbit.state == ST_FLEE
    assert fled, "заяц не испугался волка"
    # Проверяем НАПРАВЛЕНИЕ бегства, а не итоговую дистанцию: волк быстрее
    # зайца и вполне может его догнать — это правильный исход охоты, но тогда
    # дистанция в конце маленькая, и тест ловил бы не то.
    assert rabbit.rect.centerx > started_at, "заяц побежал не прочь от волка"


def test_hunt_never_overrides_the_player():
    """Игрок важнее охоты: существо, которое бьют, обязано реагировать на
    того, кто бьёт, а не догонять зайца."""
    from units.common import TSIZE, FPS
    from units.Objects.Creatures import Wolf, Rabbit, ST_CHASE
    game = fresh_world(925)
    x, y = _flat_arena(game, w=40)
    wolf = _place(game, Wolf, x + 5, y)
    _place(game, Rabbit, x + 8, y)
    game.player.active = True
    game.player.tp_to(((x + 2) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    wolf.alert_tacts = FPS * 3
    wolf.last_seen_x = game.player.rect.centerx
    wolf.hunt_update(0)
    assert not wolf.hunt_step(), "охота перебила реакцию на игрока"


def test_trough_tames_livestock_and_gives_products():
    """Хозяйство — это МЕСТО, а не список ручных зверей: кормушка кормит тех,
    кто рядом, и они у неё живут."""
    from units.common import FPS, OBJ_ITEM
    from units.Objects.Items import ItemsTile
    from units.Objects.Creatures import Cow
    game = fresh_world(926)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    gm.set_static_tile(x + 5, y, 113)
    trough = _tile_obj(gm, x + 5, y)
    assert trough is not None and trough.index == 113
    trough.inventory.put_to_inventory(ItemsTile(game, 53, count=10))
    cow = _place(game, Cow, x + 7, y)
    game.screen_map.teleport_to_player()
    game.tact = 100
    for _ in range(40):
        game.tact += FPS * 10
        trough.tick(FPS * 10)
    assert cow.tamed, "корова не приручилась у кормушки"
    assert cow.home == (x + 5, y), "домом должна стать кормушка"
    assert trough.inventory[0] is None or trough.inventory[0].count < 10, \
        "кормушка должна тратить еду"
    products = [o for ch in gm.game_map.values() for o in ch[1]
                if o.class_obj & OBJ_ITEM and o.alive and o.index == 426]
    assert products, "сытая корова должна давать молоко"


def test_trough_needs_food():
    """Без еды кормушка не приручает: хозяйство не должно быть бесплатным."""
    from units.common import FPS
    from units.Objects.Creatures import Cow
    game = fresh_world(927)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    gm.set_static_tile(x + 5, y, 113)
    trough = _tile_obj(gm, x + 5, y)
    cow = _place(game, Cow, x + 7, y)
    game.tact = 100
    for _ in range(20):
        game.tact += FPS * 10
        trough.tick(FPS * 10)
    assert not cow.tamed, "корова приручилась у пустой кормушки"


def test_tamed_animal_does_not_flee_and_stays_home():
    """Домашнее животное не шарахается от хозяина и держится кормушки."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow, ST_WANDER
    game = fresh_world(928)
    x, y = _flat_arena(game, w=40)
    cow = _place(game, Cow, x + 25, y)
    cow.tamed = True
    cow.home = (x + 5, y)          # ушла далеко от кормушки
    game.player.active = True
    game.player.tp_to(((x + 26) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    cow.alert_tacts = cow.memory_tacts
    cow.last_seen_x = game.player.rect.centerx
    assert not cow.wants_to_flee(), "домашняя корова убегает от хозяина"
    cow.alert_tacts = 0
    cow.state = ST_WANDER
    cow.move_direction = 1
    cow.flock_cohesion()
    assert cow.move_direction == -1, "домашнее животное должно возвращаться к кормушке"


def test_cauldron_uses_three_ingredient_cells():
    """Составной рецепт — то, ради чего появились лишние ячейки: те же травы,
    но две порции."""
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    game = fresh_world(929)
    gm = game.game_map
    gm.set_static_tile(5, 0, 125)
    cauldron = _tile_obj(gm, 5, 0)
    assert sum(1 for _ in cauldron.input_cell) >= 3, \
        "у котла должно быть три ячейки ингредиентов"
    cauldron.fuel_cell.put_to_inventory(ItemsTile(game, 11, count=4))
    cauldron.water_cell.put_to_inventory(TOOLS[411](game))
    cauldron.input_cell.put_to_inventory(ItemsTile(game, 109, count=2))
    cauldron.input_cell.put_to_inventory(ItemsTile(game, 421, count=2))
    assert cauldron.check_cells(), "составной рецепт не собрался"
    for _ in range(cauldron.brew_time + 2):
        cauldron.update(16)
    out = cauldron.result_cell[0]
    assert out is not None and out.index == 413 and out.count == 2, \
        f"составной рецепт дал {out and (out.index, out.count)}"


def test_cauldron_rejects_extra_ingredients():
    """Лишний ингредиент рецепт не подходит: иначе котёл — мусорка, куда
    сваливают всё подряд."""
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    game = fresh_world(932)
    gm = game.game_map
    gm.set_static_tile(5, 0, 125)
    cauldron = _tile_obj(gm, 5, 0)
    cauldron.fuel_cell.put_to_inventory(ItemsTile(game, 11, count=4))
    cauldron.water_cell.put_to_inventory(TOOLS[411](game))
    cauldron.input_cell.put_to_inventory(ItemsTile(game, 53, count=6))
    assert cauldron.check_cells(), "простой рецепт должен работать"
    cauldron.input_cell.put_to_inventory(ItemsTile(game, 3, count=1))   # камень
    assert not cauldron.check_cells(), "котёл сварил зелье с лишним ингредиентом"


def test_cauldron_ui_hints_what_goes_where():
    """Без иконок котёл — четыре одинаковых квадрата, и что куда класть,
    приходится угадывать перебором."""
    get_app()
    from units.UI.BlocksUI import CauldronUI
    ui = CauldronUI()
    assert set(ui._hints) == {"fuel", "water", "input"}, \
        f"подсказки не для всех ячеек: {sorted(ui._hints)}"


# ===================== вода и лава, дыхание, грядки, рыбалка =====================

def test_water_quenches_lava():
    """У ведра не было главного применения: лаву нельзя было убрать ничем,
    кроме динамита, и ад проходился только облётом."""
    from units.Tiles import water_frame
    game = fresh_world(900)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    for tx in range(x + 4, x + 8):
        gm.set_static_tile(tx, y, 140)          # лужа лавы
    gm.water_flow.queue.clear()
    gm.water_flow.pending.clear()
    gm.set_static_tile(x + 3, y, [120, 0, water_frame(4), 0])   # вылили ведро
    for tact in range(0, 400):
        gm.water_flow.tick(tact)
    assert gm.get_static_tile_type(x + 4, y, default=0, create_chunk=True) == 3, \
        "лава рядом с водой не превратилась в породу"


def test_quenching_costs_water():
    """Гасим одну клетку за единицу воды: иначе одно ведро вычищало бы озеро
    лавы целиком, и объём воды перестал бы что-то значить."""
    from units.Tiles import water_frame
    game = fresh_world(904)
    gm = game.game_map
    x, y = _water_arena(game, w=24)
    for tx in range(x + 4, x + 16):
        gm.set_static_tile(tx, y, 140)
    gm.water_flow.queue.clear()
    gm.water_flow.pending.clear()
    gm.set_static_tile(x + 3, y, [120, 0, water_frame(4), 0])
    for tact in range(0, 600):
        gm.water_flow.tick(tact)
    lava_left = sum(1 for tx in range(x + 4, x + 16)
                    if gm.get_static_tile_type(tx, y, default=0, create_chunk=True) == 140)
    assert lava_left >= 8, f"одно ведро погасило слишком много лавы: осталось {lava_left} из 12"


def test_air_runs_out_under_water_and_hurts():
    """Раньше в воде можно было жить вечно. Утопление сделано только вместе с
    индикатором: смерть от невидимого таймера — плохая цена за купание."""
    from units.common import TSIZE, AIR_MAX, FPS
    game = fresh_world(905)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 5, y, w=6, depth=8)
    player = game.player
    player.active = True
    player.creative_mode = False
    player.first_fall = False
    player.tp_to(((x + 7) * TSIZE, (y - 5) * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 5)
    assert player.air > AIR_MAX * 0.9, "воздух начал тратиться не с полного запаса"
    lives = player.lives
    _run_frames(game, int(AIR_MAX) + FPS * 2)
    assert player.air == 0, "воздух под водой обязан кончаться"
    assert player.lives < lives, "без воздуха игрок должен получать урон"


def test_air_refills_above_water():
    """Наверху дыхание восстанавливается быстро: наказывать за то, что игрок
    уже выплыл, нечестно."""
    from units.common import TSIZE, AIR_MAX, FPS
    game = fresh_world(906)
    game.player.active = True
    game.player.creative_mode = False
    x, y = _flat_arena(game, w=20)
    game.player.tp_to(((x + 5) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.player.air = 10
    _run_frames(game, FPS * 3)
    assert game.player.air == AIR_MAX, f"воздух не восстановился: {game.player.air}"


def test_walking_in_shallow_water_does_not_drown():
    """Захлебнуться можно только там, где воды почти полный тайл. По пояс —
    это брод, и там дышат: иначе уровни воды не значили бы ничего для физики,
    а лужа убивала бы так же, как омут."""
    from units.common import TSIZE, AIR_MAX, FPS
    from units.Tiles import water_frame
    game = fresh_world(907)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    for tx in range(x + 4, x + 10):
        gm.set_static_tile(tx, y, [120, 0, water_frame(2), 0])   # по пояс
    player = game.player
    player.active = True
    player.creative_mode = False
    player.tp_to(((x + 6) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, FPS * 3)
    assert player.air == AIR_MAX, f"на мелководье игрок задыхается: {player.air}"


def test_breath_potion_stretches_the_air():
    """Зелье дыхания растягивает запас, а не отменяет его."""
    from units.common import TSIZE, AIR_MAX, FPS
    from units.Effects import BREATH
    game = fresh_world(908)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 5, y, w=6, depth=8)
    player = game.player
    player.active = True
    player.creative_mode = False
    player.first_fall = False
    player.tp_to(((x + 7) * TSIZE, (y - 5) * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 5)
    player.air = AIR_MAX
    _run_frames(game, FPS * 5)
    plain = AIR_MAX - player.air
    player.air = AIR_MAX
    player.effects.add(BREATH, FPS * 60)
    _run_frames(game, FPS * 5)
    with_potion = AIR_MAX - player.air
    assert 0 < with_potion < plain, f"зелье не помогло: {plain} -> {with_potion}"


def test_planted_crop_grows_and_regrows_after_harvest():
    """Посаженное растение стояло вечно, и грядка на базе ничем не отличалась
    от декорации. Теперь оно растёт, а урожай снимается со зрелого — само
    растение при этом остаётся."""
    from units.common import FPS, TILE_TIMER
    from units.Tiles import GROWING_PLANT_STAGES, item_of_right_click_tile
    from units.Tools.Tools import tile_click
    game = fresh_world(909)
    gm = game.game_map
    x, y = 70, 8
    gm.set_static_tile(x, y + 1, 1)
    gm.set_static_tile(x, y, 109)              # посадили лунный цвет
    assert gm.get_static_tile(x, y)[2] == 0, "посаженное растение должно быть ростком"
    chunk = gm.game_map[gm.to_chunk_xy(x, y)]
    i = gm.convert_pos_to_i(x, y)
    tact = 0
    for _ in range(GROWING_PLANT_STAGES + 2):
        tact += FPS * 200
        gm.grow_plant_tile(chunk, i, chunk[0][i:i + 4], x, y, tact)
    assert chunk[0][i + 2] == GROWING_PLANT_STAGES - 1, "растение не выросло"
    assert item_of_right_click_tile(gm.get_static_tile(x, y)), "урожай не снимается"
    tile_click(gm, None, x, y, (0, 0), game.player)
    assert gm.get_static_tile_type(x, y, create_chunk=True) == 109, "растение пропало после сбора"
    assert gm.get_static_tile(x, y)[2] == 0, "после сбора растение должно отрасти заново"
    assert not item_of_right_click_tile(gm.get_static_tile(x, y)), \
        "с ростка урожай снимать нельзя"


def test_generated_plants_are_grown():
    """Мир должен выглядеть выросшим: ростки бывают только там, где сажал
    игрок."""
    from units.Tiles import GROWING_PLANTS, GROWING_PLANT_STAGES
    game = fresh_world(11)
    gm = game.game_map
    seen = 0
    for cx in range(-5, 6):
        for cy in range(-2, 4):
            static = gm.generate_chunk(cx, cy)[0]
            for i in range(0, len(static), 4):
                if static[i] in GROWING_PLANTS:
                    seen += 1
                    assert static[i + 2] == GROWING_PLANT_STAGES - 1, \
                        f"генератор поставил недоросшее растение {static[i]}"
    assert seen, "новых растений не нашлось"


def test_fishing_rod_casts_only_into_water():
    """Поплавок ставится на воду, а не на землю: иначе рыбалка работала бы
    посреди поля."""
    from units.common import TSIZE
    from pygame import Vector2
    game = fresh_world(910)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 6, y, w=6, depth=4)
    player = game.player
    player.active = True
    player.tp_to(((x + 3) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 2)
    _give(player, 520)
    rod = _hold(player, 520)
    rod.tool.owner = player
    to_ground = Vector2((x + 2) * TSIZE + 16 - player.rect.centerx,
                        (y + 1) * TSIZE + 16 - player.rect.centery)
    assert not rod.tool.right_button_click(to_ground), "удочка забросилась в землю"
    to_water = Vector2((x + 7) * TSIZE + 16 - player.rect.centerx,
                       (y - 1) * TSIZE + 16 - player.rect.centery)
    assert rod.tool.right_button_click(to_water), "заброс в воду не сработал"
    assert rod.tool.float_tile is not None


def test_fishing_catches_something():
    """Клюёт по таймеру, добыча падает у поплавка."""
    from units.common import TSIZE, FPS, OBJ_ITEM
    from pygame import Vector2
    game = fresh_world(911)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    _flood(gm, x + 6, y, w=6, depth=4)
    player = game.player
    player.active = True
    player.tp_to(((x + 3) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 2)
    _give(player, 520)
    rod = _hold(player, 520)
    rod.tool.owner = player
    to_water = Vector2((x + 7) * TSIZE + 16 - player.rect.centerx,
                       (y - 1) * TSIZE + 16 - player.rect.centery)
    rod.tool.right_button_click(to_water)
    for _ in range(FPS * 12):
        _run_frames(game, 1)
        rod.tool.update(to_water)
        if rod.tool.float_tile is None:
            break
    assert rod.tool.float_tile is None, "за двенадцать секунд обязано клюнуть"
    items = [o for ch in gm.game_map.values() for o in ch[1]
             if o.class_obj & OBJ_ITEM and o.alive]
    assert items, "улов не появился в мире"


def test_fishing_line_breaks_when_you_walk_away():
    """Рыбалка не должна работать в фоне, пока игрок ушёл на другой конец
    карты."""
    from units.common import TSIZE
    from pygame import Vector2
    game = fresh_world(912)
    gm = game.game_map
    x, y = _water_arena(game, w=30)
    _flood(gm, x + 6, y, w=6, depth=4)
    player = game.player
    player.active = True
    player.tp_to(((x + 3) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 2)
    _give(player, 520)
    rod = _hold(player, 520)
    rod.tool.owner = player
    to_water = Vector2((x + 7) * TSIZE + 16 - player.rect.centerx,
                       (y - 1) * TSIZE + 16 - player.rect.centery)
    assert rod.tool.right_button_click(to_water)
    player.tp_to(((x + 28) * TSIZE, y * TSIZE))
    rod.tool.update(to_water)
    assert rod.tool.float_tile is None, "леска не оборвалась при уходе"


def test_fishing_table_is_mostly_fish():
    """Основа улова — еда: рыбалка должна кормить, а редкости только делают
    улов не всегда одинаковым."""
    from units.Tools.ToolFishing import CATCH_TABLE
    total = sum(w for _, _, w in CATCH_TABLE)
    fish = sum(w for idx, _, w in CATCH_TABLE if idx == 405)
    assert fish / total > 0.5, f"рыбы в таблице всего {fish / total:.0%}"


# ===================== ведро, котёл и эффекты =====================

def _tile_obj(gm, tx, ty):
    return gm.get_tile_obj(*gm.to_chunk_xy(tx, ty), gm.get_static_tile(tx, ty)[3])


def _give(player, index, count=1):
    """Положить предмет игроку и вернуть его."""
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    if index in TOOLS:
        item = TOOLS[index](player.game, pos=player.rect.topleft)
    else:
        item = ItemsTile(player.game, index, player.rect.topleft, count)
    player.inventory.put_to_inventory(item)
    return item


def _hold(player, index):
    """Взять предмет с этим индексом в активную ячейку."""
    for i, cell in enumerate(player.inventory):
        if cell is not None and cell.index == index:
            player.inventory.active_cell = i
            player.choose_active_cell(i)
            return cell
    return None


def test_bucket_takes_water_and_pours_it_back():
    """Ведро — единственный способ ПРИНЕСТИ воду туда, где её нет. Два
    предмета (пустое и полное), а не поле «полное»: иконку видно в тулбаре, и
    вода не теряется при подборе пустого ведра."""
    from units.common import TSIZE
    from units.Tiles import water_frame
    from pygame import Vector2
    game = fresh_world(800)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    gm.set_static_tile(x + 6, y, [120, 0, water_frame(4), 0])
    player = game.player
    player.active = True
    player.tp_to(((x + 5) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    # Инструмент считает цель от player.vector, а он выставляется в update:
    # без кадра он остался бы нулевым, и «до воды» вышло бы полкарты.
    _run_frames(game, 2)
    _give(player, 410)
    bucket = _hold(player, 410)
    assert bucket is not None, "ведро не попало в инвентарь"
    to_water = Vector2((x + 6) * TSIZE + 16 - player.rect.centerx,
                       y * TSIZE + 16 - player.rect.centery)
    bucket.tool.owner = player
    assert bucket.tool.right_button_click(to_water), "ведро не набрало воду"
    assert gm.get_static_tile(x + 6, y, create_chunk=True)[0] == 0, "вода осталась на месте"
    full = _hold(player, 411)
    assert full is not None, "полного ведра в инвентаре нет"
    # выливаем на другой тайл
    full.tool.owner = player
    to_air = Vector2((x + 8) * TSIZE + 16 - player.rect.centerx,
                     y * TSIZE + 16 - player.rect.centery)
    assert full.tool.right_button_click(to_air), "полное ведро не вылилось"
    assert gm.get_static_tile(x + 8, y, create_chunk=True)[0] == 120, "воды нет там, где вылили"
    assert _hold(player, 410) is not None, "ведро не стало пустым"


def test_bucket_does_not_pour_into_stone():
    """Вода не вытесняет блоки — то же правило, что у потока."""
    from units.common import TSIZE
    from pygame import Vector2
    game = fresh_world(801)
    gm = game.game_map
    x, y = _water_arena(game, w=20)
    player = game.player
    player.active = True
    player.tp_to(((x + 5) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 2)
    _give(player, 411)
    full = _hold(player, 411)
    full.tool.owner = player
    to_floor = Vector2((x + 6) * TSIZE + 16 - player.rect.centerx,
                       (y + 1) * TSIZE + 16 - player.rect.centery)
    assert not full.tool.right_button_click(to_floor), "ведро вылилось в камень"
    assert gm.get_static_tile(x + 6, y + 1, create_chunk=True)[0] == 3, "камень подменился водой"


def test_cauldron_brews_only_with_fuel_water_and_ingredient():
    """Котёл был «столом с огоньком»: зелья собирались мгновенным крафтом от
    касания. Теперь это машина, и без любой из трёх составляющих она не
    работает."""
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    game = fresh_world(802)
    gm = game.game_map
    gm.set_static_tile(5, 0, 125)
    cauldron = _tile_obj(gm, 5, 0)
    assert cauldron is not None and cauldron.index == 125

    cauldron.input_cell.put_to_inventory(ItemsTile(game, 53, count=6))   # ягоды
    assert not cauldron.check_cells(), "без топлива и воды варить нельзя"
    cauldron.fuel_cell.put_to_inventory(ItemsTile(game, 11, count=4))    # доски
    assert not cauldron.check_cells(), "без воды варить нельзя"
    cauldron.water_cell.put_to_inventory(TOOLS[411](game))               # ведро с водой
    assert cauldron.check_cells(), "всё на месте, а котёл не варит"

    for _ in range(cauldron.brew_time + 2):
        cauldron.update(16)
    out = cauldron.result_cell[0]
    assert out is not None and out.index == 55, f"в результате {out and out.index}"
    # вода израсходована: ведро в ячейке стало пустым
    assert cauldron.water_cell[0] is not None and cauldron.water_cell[0].index == 410, \
        "ведро должно опустеть — это и есть «вода израсходована»"


def test_cauldron_needs_enough_of_the_ingredient():
    """У рецепта есть количество: одна ягода не превращается в зелье."""
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    game = fresh_world(803)
    gm = game.game_map
    gm.set_static_tile(5, 0, 125)
    cauldron = _tile_obj(gm, 5, 0)
    cauldron.fuel_cell.put_to_inventory(ItemsTile(game, 11, count=4))
    cauldron.water_cell.put_to_inventory(TOOLS[411](game))
    cauldron.input_cell.put_to_inventory(ItemsTile(game, 53, count=2))
    assert not cauldron.check_cells(), "двух ягод на зелье не хватает"


def test_cauldron_recipes_use_hunt_and_plants():
    """Ингредиенты зелий — трофеи существ и новые растения, а не руда: зелье
    оплачивается охотой или походом в биом (docs/BALANCE_SCHEME.md)."""
    from units.Objects.TileClasses import CAULDRON_RECIPES
    from units.Objects.Creatures import CREATURES
    from units.Tiles import tile_words
    drops = {p[0] for cls in CREATURES for _, p in cls.drop_items}
    plants = {107, 108, 109, 111, 112}
    ingredients = set()
    for need, (result, count) in CAULDRON_RECIPES:
        assert need, "рецепт без ингредиентов"
        for index, amount in need.items():
            assert index in tile_words, f"ингредиент {index} без названия"
            assert amount >= 1
            ingredients.add(index)
        assert result in tile_words, f"результат {result} без названия"
        assert count >= 1
    assert drops & ingredients, "ни один трофей существ не идёт в зелья"
    assert plants & ingredients, "ни одно новое растение не идёт в зелья"
    # Составные рецепты нужны, иначе три ячейки ингредиентов не для чего
    assert any(len(need) > 1 for need, _ in CAULDRON_RECIPES), \
        "нет ни одного рецепта, которому нужна вторая ячейка"


def test_pill_is_the_earliest_healing_recipe():
    """Таблетка: четыре ягоды и слизь — то, что есть у любого, кто дошёл до
    первого куста и первого слизня. И лечит она эффектом, а не мгновенно."""
    from units.creating_items import RECIPES
    from units.Effects import ITEM_EFFECTS, REGEN
    pill = [r for r in RECIPES if r[0][0] == 412]
    assert pill, "рецепта таблетки нет"
    out, need = pill[0]
    assert dict(need) == {53: 4, 51: 1}, f"состав таблетки: {need}"
    assert out[1] >= 1
    assert any(spec[0] == REGEN for spec in ITEM_EFFECTS[412]), \
        "таблетка обязана давать заживление, а не мгновенное лечение"


def test_potions_are_no_longer_instant_hand_crafts():
    """Зелья убраны из ручного крафта: мгновенная сборка зелья обесценивала и
    котёл, и сами зелья — варка была неотличима от сборки стула."""
    from units.creating_items import RECIPES
    from units.Objects.TileClasses import CAULDRON_RECIPES
    hand_results = {r[0][0] for r in RECIPES}
    brewed = {out[0] for _, out in CAULDRON_RECIPES}
    assert not (hand_results & brewed), \
        f"эти зелья всё ещё собираются руками: {hand_results & brewed}"


def test_effects_expire_and_do_not_touch_player_fields():
    """Главное правило системы: эффект НИЧЕГО не меняет в игроке. Иначе правка
    поля пережила бы сам эффект и осталась бы в сейве навсегда."""
    from units.common import FPS
    from units.Effects import SPEED
    game = fresh_world(804)
    player = game.player
    speed_before = player.max_speed
    player.effects.add(SPEED, FPS)
    assert player.effects.has(SPEED)
    assert player.max_speed == speed_before, "эффект правит поле игрока"
    assert player.effects.mult(SPEED) > 1
    for tact in range(FPS + 2):
        player.effects.update(tact)
    assert not player.effects.has(SPEED), "эффект не кончился по времени"
    assert player.effects.mult(SPEED) == 1.0
    assert player.max_speed == speed_before


def test_effect_is_extended_not_stacked():
    """Второе зелье продлевает, а не умножает: 1.45 * 1.45 — это уже полёт."""
    from units.common import FPS
    from units.Effects import SPEED
    game = fresh_world(805)
    player = game.player
    player.effects.add(SPEED, FPS * 10)
    power = player.effects.mult(SPEED)
    player.effects.add(SPEED, FPS * 10)
    assert player.effects.mult(SPEED) == power, "сила эффекта сложилась"
    assert player.effects.left(SPEED) > FPS * 10, "время не продлилось"


def test_regen_heals_over_time():
    """Заживление лечит понемногу и по секундам, а не по кадрам: единица за
    кадр — это шестьдесят здоровья в секунду, то есть бессмертие."""
    from units.common import FPS
    from units.Effects import REGEN
    game = fresh_world(806)
    player = game.player
    player.lives = player.max_lives - 10
    hurt = player.lives
    player.effects.add(REGEN, FPS * 5)
    for tact in range(FPS * 3):
        player.effects.update(tact)
    healed = player.lives - hurt
    assert 1 <= healed <= 4, f"заживление вылечило {healed} за три секунды"


def test_stoneskin_reduces_damage_but_never_to_zero():
    """Полная неуязвимость от зелья превратила бы бой в ожидание."""
    from units.common import FPS
    from units.Effects import STONESKIN
    game = fresh_world(807)
    player = game.player
    player.creative_mode = False
    player.lives = player.max_lives
    player.damage(10)
    plain = player.max_lives - player.lives
    player.lives = player.max_lives
    player.effects.add(STONESKIN, FPS * 5)
    player.damage(10)
    with_skin = player.max_lives - player.lives
    assert 0 < with_skin < plain, f"каменная кожа: {plain} -> {with_skin}"


def test_fireproof_effect_saves_from_lava_only_while_it_lasts():
    """Огнеупорность даётся эффектом, а не приписывается в immune_tiles: класс
    общий на всех существ вида, и лава осталась бы безвредной навсегда."""
    from units.common import FPS
    from units.Effects import FIREPROOF
    from units.Objects.Entity import FIREPROOF_TILES
    game = fresh_world(808)
    player = game.player
    assert 140 in FIREPROOF_TILES, "лава обязана входить в защиту от жара"
    assert player.effect_immunity() == frozenset()
    player.effects.add(FIREPROOF, FPS)
    assert 140 in player.effect_immunity()
    for tact in range(FPS + 2):
        player.effects.update(tact)
    assert player.effect_immunity() == frozenset(), "защита осталась после эффекта"
    assert 140 not in type(player).immune_tiles, "иммунитет просочился в класс"


def test_eating_a_pill_grants_the_effect():
    """Съеденный предмет накладывает эффекты из таблицы ITEM_EFFECTS."""
    from units.Effects import REGEN
    game = fresh_world(809)
    player = game.player
    player.active = True
    player.lives = player.max_lives - 5
    _give(player, 412, 2)
    _hold(player, 412)
    player.eat = True
    _run_frames(game, 2)
    assert player.effects.has(REGEN), "таблетка не дала заживления"


def test_effects_survive_save_and_load():
    """Эффекты — это числа в поле игрока, поэтому они переживают сохранение.
    Сам объект Effects в сейв не идёт: он держит ссылку на игру, а в игре есть
    непиклящийся pygame.time.Clock — именно на этом падало сохранение."""
    from units.common import FPS
    from units.Effects import SPEED
    game = fresh_world(810)
    player = game.player
    player.effects.add(SPEED, FPS * 20)
    import copy
    # Копия, а не сам словарь: get_vars отдаёт ссылку на поля игрока, и
    # очистка эффектов ниже стёрла бы заодно «сохранённое» состояние.
    vrs = copy.deepcopy(player.get_vars())
    assert "effects" not in vrs, "объект эффектов не должен попадать в сейв"
    assert vrs["effects_state"].get(SPEED), "состояние эффектов не сохранилось"
    player.effects.clear()
    player.set_vars(vrs)
    assert player.effects.has(SPEED), "после загрузки эффект потерялся"


def test_old_world_cauldron_gets_its_object_on_click():
    """Котёл до этого релиза был мебелью: в сохранённых мирах у него нет
    объекта, и первый правый клик падал бы на None. Объект должен создаваться
    на месте — это цена превращения блока в машину."""
    from units.Tools.Tools import tile_click
    game = fresh_world(811)
    gm = game.game_map
    gm.set_static_tile(7, 0, 125)
    tile = gm.get_static_tile(7, 0)
    tile[3] = 0                       # как в старом сейве: объекта нет
    gm.set_static_tile(7, 0, list(tile))
    tile = gm.get_static_tile(7, 0)
    tile[3] = 0
    assert gm.get_static_tile(7, 0)[0] == 125
    tile_click(gm, None, 7, 0, (0, 0), game.player)
    obj = _tile_obj(gm, 7, 0)
    assert obj is not None and obj.index == 125, "объект котла не создался"


# ===================== новые растения =====================

def test_new_plants_grow_in_their_places():
    """Пять новых растений: три на дёрне по биомам, два на камне под землёй.
    Пещерным нужна своя ветка генератора — дёрна на глубине нет."""
    game = fresh_world(11)
    gm = game.game_map
    found = set()
    for cx in range(-6, 7):
        for cy in range(-2, 22):
            static = gm.generate_chunk(cx, cy)[0]
            for i in range(0, len(static), 4):
                if static[i] in (107, 108, 109, 111, 112):
                    found.add(static[i])
    assert found == {107, 108, 109, 111, 112}, f"не выросли: {{107,108,109,111,112}} - {found}"


def test_cave_plants_stand_on_stone():
    """Гриб и мох растут на камне: если их поставить в воздух, они висят."""
    from units.Map.GameMap import cave_plant_selection
    from units.Tiles import CAVE_PLANTS
    game = fresh_world(12)
    gm = game.game_map
    checked = 0
    for cx in range(-4, 5):
        for cy in range(4, 20):
            static = gm.generate_chunk(cx, cy)[0]
            for i in range(0, len(static), 4):
                if static[i] in CAVE_PLANTS:
                    cell = i // 4
                    tx = cx * 32 + cell % 32
                    ty = cy * 32 + cell // 32
                    below = gm.get_static_tile_type(tx, ty + 1, default=0, create_chunk=True)
                    assert below not in (0, 120), f"растение висит в воздухе на {tx},{ty}"
                    checked += 1
    assert checked, "пещерных растений не нашлось"
    assert cave_plant_selection(0) is None, "у поверхности пещерной флоры быть не должно"


def test_creature_drops_feed_the_cauldron():
    """Дроп из существ стал ингредиентом: у охоты появилась цель помимо мяса."""
    from units.Objects.Creatures import Wolf, Bat, Jellyfish, StoneGolem, DeepLurker, Hawk
    from units.Objects.TileClasses import CAULDRON_RECIPES
    expected = {Wolf: 420, Bat: 422, Jellyfish: 423, StoneGolem: 424, Hawk: 421}
    for cls, index in expected.items():
        drops = {p[0] for _, p in cls.drop_items}
        assert index in drops, f"{cls.__name__} не даёт {index}: {drops}"
    brewable = {idx for need, _ in CAULDRON_RECIPES for idx in need}
    assert {420, 422, 423, 424} <= brewable, "трофеи не участвуют в зельеварении"
    assert 425 in {p[0] for _, p in DeepLurker.drop_items}, "глубинник без чешуи"


# ===================== пересчёт меню при смене размера окна =====================

def test_resize_relayouts_every_menu_of_the_scene():
    """Сцена держит несколько экранов (титул, настройки, звук), а событие
    ресайза приходит только в активную сцену. Раньше пересчитывался лишь
    self.ui: растянув окно на титуле, игрок получал корректный титул и
    разъехавшиеся настройки."""
    app = get_app()
    from units import common
    scene = app.title_scene
    uis = scene.all_uis()
    assert len(uis) >= 3, f"у титульной сцены должно быть несколько экранов, нашлось {len(uis)}"

    old = tuple(common.SCREEN_SIZE)
    try:
        common.apply_resize((900, 700))
        scene._on_screen_changed()
        for ui in uis:
            assert ui.rect.size == (900, 700), f"{type(ui).__name__} не пересчитался: {ui.rect.size}"
    finally:
        common.apply_resize(old)
        scene._on_screen_changed()


def test_inactive_scene_relayouts_lazily():
    """Пересчёт должен быть ленивым: сцена, которая была неактивна во время
    ресайза, обязана привести раскладку в порядок, когда её покажут."""
    app = get_app()
    from units import common
    scene = app.title_scene
    ui = scene.settings_ui
    old = tuple(common.SCREEN_SIZE)
    try:
        # ресайз «в другой сцене»: событие сюда не приходило
        common.apply_resize((1000, 600))
        assert ui.rect.size != (1000, 600), "раскладка ещё старая — это нормально"
        ui.ensure_layout()
        assert ui.rect.size == (1000, 600), "показ экрана должен пересчитать раскладку"
        # повторный вызов не должен пересчитывать заново
        gen = ui._layout_generation
        ui.ensure_layout()
        assert ui._layout_generation == gen
    finally:
        common.apply_resize(old)
        scene._on_screen_changed()


def test_screen_generation_grows_on_resize():
    """Поколение экрана — то, по чему UI понимает, что пора пересчитаться."""
    get_app()
    from units import common
    old = tuple(common.SCREEN_SIZE)
    before = common.SCREEN_GENERATION[0]
    try:
        common.apply_resize((820, 640))
        assert common.SCREEN_GENERATION[0] > before
    finally:
        common.apply_resize(old)


# ===================== настройки по разделам и меню модов =====================

def test_main_settings_keeps_only_the_frequent_options():
    """15 пунктов одним списком не влезали в низкое окно, а нужное
    приходилось искать глазами. В основном меню остаются размер меню и режим
    экрана, остальное — по разделам."""
    app = get_app()
    ui = app.title_scene.settings_ui
    ui.draw()
    labels = [d.label for d in ui.dropdowns]
    assert any("Размер меню" in l for l in labels), labels
    assert any("Режим экрана" in l for l in labels), labels
    assert len(ui.dropdowns) == 2, f"в основном меню только две настройки, а не {labels}"
    texts = [b.text for b in ui.buttons]
    for section in ("Экран", "Графика", "Звук", "Мир", "Модификации"):
        assert any(section in t for t in texts), f"нет перехода в раздел {section}: {texts}"


def test_every_settings_section_draws_and_has_way_back():
    """Из каждого раздела должен быть выход — иначе игрок в нём застревает."""
    app = get_app()
    scene = app.title_scene
    sections = [scene.screen_settings_ui, scene.graphics_settings_ui,
                scene.sound_settings_ui, scene.world_settings_ui, scene.mods_settings_ui]
    for ui in sections:
        ui.draw()                                   # не должен падать
        texts = [b.text for b in ui.buttons]
        assert any("Назад" in t for t in texts), f"{type(ui).__name__}: нет кнопки назад ({texts})"


def test_settings_sections_cover_all_old_options():
    """При разбивке легко потерять настройку. Все, что были в одном списке,
    должны найтись в разделах."""
    app = get_app()
    scene = app.title_scene
    labels = []
    for ui in (scene.settings_ui, scene.screen_settings_ui, scene.graphics_settings_ui,
               scene.world_settings_ui, scene.mods_settings_ui):
        ui.draw()
        labels += [d.label for d in ui.dropdowns]
    for expected in ("Монитор", "Обзор", "Режим экрана", "Размер меню", "Лимит FPS",
                     "Вертикальная синхронизация", "Выгрузка карты", "облаков",
                     "звёзд", "ID предмета", "Курсор", "моды"):
        assert any(expected in l for l in labels), f"настройка «{expected}» потерялась"


def test_mods_menu_lists_mods_with_state():
    """Общий выключатель — это «всё или ничего», а ломает игру обычно один
    мод. Меню должно показывать каждый мод: что добавляет и включён ли."""
    app = get_app()
    ui = app.title_scene.mods_settings_ui
    ui.draw()
    from units import mods
    folders = mods.mod_folders()
    if not folders:
        return                                      # модов нет — рисуем подсказку
    assert ui.mod_rows, "моды на диске есть, а список пуст"
    for info, rect, btn in ui.mod_rows:
        assert info["folder"] in folders
        assert isinstance(info["blocks"], int) and isinstance(info["creatures"], int)
        assert btn.text in ("Выключить", "Включить")


def test_single_mod_can_be_disabled_without_the_others():
    """Выключение одного мода не должно отключать остальные и не должно
    трогать общий выключатель."""
    get_app()
    from units import config as cfg, mods
    folders = mods.mod_folders()
    if not folders:
        return
    folder = folders[0]
    was_disabled = cfg.ModSettings.is_disabled(folder)
    was_enabled = cfg.ModSettings.enabled
    try:
        cfg.ModSettings.set_mod_disabled(folder, True)
        assert cfg.ModSettings.is_disabled(folder)
        assert cfg.ModSettings.enabled == was_enabled, "общий выключатель трогать нельзя"
        loaded, errors = mods.load_mods()
        assert folder in mods.MOD_SKIPPED, "выключенный мод не должен загружаться"
        assert all(os.path.basename(m["dir"]) != folder for m in loaded)
    finally:
        cfg.ModSettings.set_mod_disabled(folder, was_disabled)
        mods.load_mods()


def test_mod_switch_survives_being_toggled_twice():
    """Переключатель мода ломался после первого же нажатия: в класс попадала
    СТРОКА, собранная из списка, и на следующем вызове её перебирали по буквам.
    Список выключенных превращался в набор символов, is_disabled переставал
    работать, а settings.ini обрастал строкой из запятых."""
    get_app()
    from units import config as cfg
    folder = "watermelon_mod"
    was = cfg.ModSettings.is_disabled(folder)
    try:
        for _ in range(3):
            cfg.ModSettings.set_mod_disabled(folder, True)
            assert isinstance(cfg.ModSettings.disabled, list), \
                f"список выключенных стал {type(cfg.ModSettings.disabled).__name__}"
            assert cfg.ModSettings.is_disabled(folder), "мод не выключился"
            cfg.ModSettings.set_mod_disabled(folder, False)
            assert not cfg.ModSettings.is_disabled(folder), "мод не включился обратно"
            assert all(len(n) > 1 for n in cfg.ModSettings.disabled), \
                f"в списке появились отдельные буквы: {cfg.ModSettings.disabled}"
    finally:
        cfg.ModSettings.set_mod_disabled(folder, was)


def test_worlds_menu_uses_the_same_button_geometry_as_settings():
    """Экран миров был отдельным окном-панелью со своими шрифтами и мелкими
    кнопками — рядом с остальными меню он читался как чужой. Геометрия
    строки и высота кнопки должны совпадать с настройками."""
    app = get_app()
    worlds = app.worlds_scene.ui if hasattr(app, "worlds_scene") else None
    if worlds is None:
        from units.UI.UI import WorldListUI
        worlds = WorldListUI(app.title_scene)
    settings = app.title_scene.settings_ui
    settings.draw()
    worlds.draw()
    ref = settings.widgets[0].rect
    assert worlds.btn_back.rect.width == ref.width, \
        f"ширина кнопки {worlds.btn_back.rect.width} != {ref.width} в настройках"
    assert worlds.btn_back.rect.height == ref.height, \
        f"высота кнопки {worlds.btn_back.rect.height} != {ref.height} в настройках"
    assert worlds.btn_tutorial.rect.height == ref.height
    assert worlds.btn_new.rect.height == ref.height
    # и заголовок ставится так же, как в настройках
    assert worlds.header_pos[1] == settings.header_pos[1]


def test_worlds_menu_relayouts_with_the_window():
    """Экран миров тоже должен переживать ресайз без перезапуска."""
    app = get_app()
    from units import common
    from units.UI.UI import WorldListUI
    ui = WorldListUI(app.title_scene)
    old = tuple(common.SCREEN_SIZE)
    try:
        common.apply_resize((950, 660))
        ui.ensure_layout()
        assert ui.rect.size == (950, 660)
        assert ui.btn_back.rect.centerx == ui.rect.centerx, "кнопки должны переехать в центр"
        ui.draw()
    finally:
        common.apply_resize(old)


# ===================== ИИ существ =====================
#
# Раньше поведение было одно на всех: шаг в случайную сторону каждые 30-205
# тактов, а если игрок попал в коробку 19x19 тайлов — идти на него напрямую и
# бесконечно. Корова гналась за игроком так же, как волк, никто не терял его
# из виду, и все видели сквозь камень.

def _flat_arena(game, x=70, y=8, w=40):
    """Ровная площадка с чистым воздухом — чтобы поведение не путалось с
    рельефом."""
    gm = game.game_map
    for tx in range(x - 4, x + w):
        gm.set_static_tile(tx, y + 1, 3)
        for dy in range(0, 7):
            gm.set_static_tile(tx, y - dy, 0)
    return x, y


def _place(game, cls, tx, ty):
    from units.common import TSIZE
    obj = cls(game, (tx * TSIZE, ty * TSIZE))
    game.game_map.add_dinamic_obj(*game.game_map.to_chunk_xy(tx, ty), obj)
    return obj


def test_peaceful_creature_runs_away_instead_of_charging():
    """Корова не должна идти на игрока: раньше она использовала ту же логику
    погони, что волк."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow, ST_FLEE
    game = fresh_world(400)
    x, y = _flat_arena(game)
    cow = _place(game, Cow, x + 3, y)        # внутри радиуса испуга
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()

    # Состояние проверяем ПО ХОДУ, а не в конце: убегая, корова выходит за
    # радиус испуга (5 тайлов) и законно возвращается в wander. Проверка
    # «в конце ровно ST_FLEE» держалась на том, что за 30 кадров корова не
    # успевала отойти — то есть на фазе кадра, а не на поведении: сдвиг
    # game.tact соседними тестами её ронял.
    started = abs(cow.rect.centerx - game.player.rect.centerx)
    fled = False
    for _ in range(30):
        _run_frames(game, 1)
        if cow.state == ST_FLEE:
            fled = True
            assert cow.move_direction == 1, "убегать — значит в сторону ОТ игрока"

    assert cow.temperament != "aggressive"
    assert fled, f"корова обязана испугаться, а не {cow.state}"
    assert abs(cow.rect.centerx - game.player.rect.centerx) > started, \
        "корова должна оказаться дальше от игрока, а не ближе"


def test_aggressive_creature_chases_and_then_gives_up():
    """У охоты должен быть конец: волк не терял игрока никогда."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf, ST_CHASE
    game = fresh_world(401)
    x, y = _flat_arena(game, w=60)
    wolf = _place(game, Wolf, x + 8, y)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 30)
    assert wolf.state == ST_CHASE, f"волк должен охотиться, а не {wolf.state}"
    assert wolf.move_direction == -1, "в сторону игрока"

    # игрок ушёл далеко — память должна истечь
    game.player.tp_to(((x + 400) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    for _ in range(wolf.memory_tacts + 30):
        game.tact += 1
        wolf.update(game.tact, 16)
    # Проверяем память об ИГРОКЕ, а не состояние: волк теперь охотится и на
    # зверей (hunts), и оставшийся ST_CHASE может относиться к зайцу рядом —
    # это правильное поведение, а не незакончившаяся погоня за игроком.
    assert wolf.alert_tacts == 0, "волк не забыл игрока"
    assert wolf.last_seen_x is None, "волк помнит, где был игрок"
    if wolf.state == ST_CHASE:
        assert getattr(wolf, "prey", None) is not None, \
            "погоня за игроком обязана заканчиваться"


def _place_flock(game, cls, tx, ty, count, flock_id=777):
    """Поставить группу с общим flock_id — так их создаёт _spawn_flocks."""
    mates = []
    for i in range(count):
        obj = _place(game, cls, tx + i * 2, ty)
        obj.flock_id = flock_id
        mates.append(obj)
    return mates


def test_flock_shares_the_alarm():
    """Тронул одного — сорвалась вся группа. Это и есть «спот»: группа
    реагирует как целое, иначе рядом стоящие звери — просто N одиночек."""
    from units.Objects.Creatures import Cow
    game = fresh_world(410)
    x, y = _flat_arena(game)
    herd = _place_flock(game, Cow, x + 2, y, 3)
    game.screen_map.teleport_to_player()
    # Тревога ровно у одного: игрока рядом нет, сами увидеть его они не могут.
    herd[0].alert_tacts = herd[0].memory_tacts
    herd[0].last_seen_x = herd[0].rect.centerx - 200
    for tact in range(herd[0].FLOCK_PERIOD * 3):
        for cow in herd:
            cow.flock_update(tact)
    assert all(cow.alert_tacts > 0 for cow in herd[1:]), \
        f"тревога не разошлась по стае: {[c.alert_tacts for c in herd]}"
    assert all(cow.last_seen_x == herd[0].last_seen_x for cow in herd[1:]), \
        "стая должна знать, откуда опасность, а не просто нервничать"


def test_solitary_creature_is_not_in_a_flock():
    """flock_id 0 — «не в стае». Без этой проверки все существа, появившиеся
    не групповым спавном, считали бы друг друга одной стаей просто потому, что
    значение по умолчанию у всех совпадает."""
    from units.Objects.Creatures import Cow
    game = fresh_world(411)
    x, y = _flat_arena(game)
    a = _place(game, Cow, x + 2, y)
    b = _place(game, Cow, x + 4, y)
    assert a.flock_id == 0 and b.flock_id == 0
    assert a.flockmates() == [], "существа без стаи не должны считаться стаей"
    a.flock_id = b.flock_id = 5
    assert b in a.flockmates(), "а с общим flock_id — должны"


def test_flock_straggler_walks_back_to_the_group():
    """Без сплочения стая расходится случайным блужданием за минуту, и от неё
    остаётся только факт спавна."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow, ST_WANDER
    game = fresh_world(412)
    x, y = _flat_arena(game, w=60)
    herd = _place_flock(game, Cow, x + 2, y, 3)
    lost = herd[0]
    # Дальше 2*flock_radius стая друг друга не видит (flockmates) — это
    # намеренный предел: зверь, унесённый на полкарты, стае уже не член.
    # Отбившийся здесь в этом пределе, но за порогом сплочения.
    lost.rect.x = (x + 14) * TSIZE
    lost.update_chunk_pos()
    center = sum(c.rect.centerx for c in herd[1:]) // 2
    for tact in range(lost.FLOCK_PERIOD * 2):
        lost.flock_update(tact)
    lost.state = ST_WANDER
    lost.move_direction = 1                 # шёл прочь от стаи
    lost.flock_cohesion()
    assert lost.move_direction == -1, "отбившийся должен повернуть к стае"
    assert lost.flock_center is not None and lost.flock_center < lost.rect.centerx, \
        f"центр стаи посчитан неверно: {lost.flock_center} при {center}"


def test_bird_holds_altitude_instead_of_falling():
    """Птица не ходит по земле: гравитации у неё нет, высоту она держит сама.
    Обычное существо на том же месте просто упало бы на пол арены."""
    from units.common import TSIZE
    from units.Objects.Creatures import Bird
    game = fresh_world(413)
    x, y = _flat_arena(game, w=30)
    bird = _place(game, Bird, x + 5, y - 5)
    game.screen_map.teleport_to_player()
    assert bird.use_gravity is False, "у птицы не должно быть гравитации"
    for tact in range(120):
        bird.update(tact, 1000 / 60)
        bird.update_altitude(tact)
    floor = y + 1
    height = floor - bird.rect.bottom / TSIZE
    assert height > bird.fly_height - 3, \
        f"птица просела до {height:.1f} тайлов над землёй вместо {bird.fly_height}"
    assert bird.rect.bottom < floor * TSIZE, "птица не должна лежать на полу"


def test_bird_flaps_its_wings():
    """Два кадра взмаха: без анимации птица читается как висящий камешек."""
    from units.Objects.Creatures import Bird
    game = fresh_world(414)
    x, y = _flat_arena(game, w=20)
    bird = _place(game, Bird, x + 5, y - 5)
    seen = set()
    for tact in range(bird.WING_PERIOD * 4):
        bird.update(tact, 1000 / 60)
        seen.add(id(bird.sprite))
    assert len(seen) == 2, f"кадров взмаха должно быть два, а не {len(seen)}"


def test_flocking_species_spawn_as_groups():
    """Генератор выбирает существо на каждый тайл отдельно, поэтому стая при
    таком спавне невозможна: каждый зверь — независимый бросок. Группы
    досыпаются вторым проходом по уже выпавшим существам."""
    from units.common import TSIZE
    game = fresh_world(415)
    gm = game.game_map
    for cx in range(-4, 5):
        for cy in range(-1, 3):
            gm.generate_chunk(cx, cy)
    groups = {}
    for chunk in gm.game_map.values():
        for obj in chunk[1]:
            fid = getattr(obj, "flock_id", 0)
            if fid:
                groups.setdefault((type(obj).__name__, fid), []).append(obj)
    assert groups, "стайных существ не появилось вообще"
    big = [m for m in groups.values() if len(m) >= 2]
    assert big, f"все «стаи» оказались одиночками: {[len(m) for m in groups.values()]}"
    for mates in big:
        xs = [o.rect.centerx // TSIZE for o in mates]
        radius = mates[0].flock_radius
        assert max(xs) - min(xs) <= radius * 3, \
            f"стая {type(mates[0]).__name__} рассыпана на {max(xs) - min(xs)} тайлов"


def _count_direction_flips(game, obj, frames):
    """Сколько раз за N кадров существо сменило сторону хода.

    Именно это игрок видит как дрожание: направление пересчитывалось каждый
    кадр, и знак прыгал туда-обратно.
    """
    flips = 0
    prev = obj.move_direction
    for _ in range(frames):
        _run_frames(game, 1)
        if obj.move_direction and prev and obj.move_direction != prev:
            flips += 1
        if obj.move_direction:
            prev = obj.move_direction
    return flips


def test_chaser_does_not_jitter_at_the_player():
    """Дойдя до игрока, волк дрожал на месте: знак (игрок − я) менялся каждый
    кадр, потому что мёртвой зоны у цели не было."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf
    game = fresh_world(403)
    x, y = _flat_arena(game, w=40)
    wolf = _place(game, Wolf, x + 1, y)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 15)                    # дать дойти вплотную
    flips = _count_direction_flips(game, wolf, 45)
    assert flips <= 2, f"волк у игрока сменил сторону {flips} раз за 45 кадров — это дрожь"


def test_creature_does_not_jitter_on_the_edge_of_a_cliff():
    """Существо у обрыва дёргалось влево-вправо: check_abyss разворачивал его
    каждый кадр, на следующем кадре обрыв уже не определялся, и оно шло
    обратно."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow
    game = fresh_world(404)
    x, y = _flat_arena(game, w=20)
    # обрыв справа, вплотную к корове: пола нет вовсе
    gm = game.game_map
    for tx in range(x + 9, x + 24):
        for dy in range(1, 8):
            gm.set_static_tile(tx, y + dy, 0)
    cow = _place(game, Cow, x + 8, y)
    game.player.tp_to(((x - 60) * TSIZE, y * TSIZE))   # игрок далеко, чистый ST_WANDER
    game.screen_map.teleport_to_player()
    cow.move_direction = 1                             # идёт прямо в обрыв
    flips = _count_direction_flips(game, cow, 60)
    assert flips <= 3, f"корова у обрыва сменила сторону {flips} раз за 60 кадров"
    assert cow.rect.bottom <= (y + 2) * TSIZE, "корова не должна свалиться в обрыв"


def test_chaser_stops_at_the_cliff_instead_of_turning_back():
    """Цель за обрывом: разворот читался бы как бегство, а пересчёт каждый
    кадр давал дрожь. Правильное поведение — стоять на краю."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf, ST_CHASE
    game = fresh_world(405)
    x, y = _flat_arena(game, w=20)
    gm = game.game_map
    for tx in range(x + 8, x + 30):            # широкий провал, не перепрыгнуть
        for dy in range(1, 8):
            gm.set_static_tile(tx, y + dy, 0)
    wolf = _place(game, Wolf, x + 6, y)
    game.player.tp_to(((x + 14) * TSIZE, y * TSIZE))   # за провалом
    game.screen_map.teleport_to_player()
    _run_frames(game, 30)
    assert wolf.state == ST_CHASE, f"волк должен видеть игрока, а не {wolf.state}"
    assert wolf.move_direction == 0, \
        f"у края волк должен стоять, а не идти в сторону {wolf.move_direction}"
    assert wolf.rect.bottom <= (y + 2) * TSIZE, "волк не должен упасть в провал"


def test_turn_at_cliff_is_committed_for_a_while():
    """Разворот у обрыва фиксируется на несколько тактов — иначе решение
    пересчитывается на следующем же кадре."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow, ST_WANDER
    game = fresh_world(406)
    x, y = _flat_arena(game, w=20)
    gm = game.game_map
    for tx in range(x + 9, x + 20):
        for dy in range(1, 8):
            gm.set_static_tile(tx, y + dy, 0)
    cow = _place(game, Cow, x + 8, y)
    game.player.tp_to(((x - 60) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    cow.state = ST_WANDER
    cow.move_tact = 1000            # чтобы think() не перевыбрал сторону сам
    cow.move_direction = 1          # идёт прямо в обрыв
    cow.update(game.tact, 16)
    assert cow.move_direction == -1, "у обрыва существо обязано развернуться"
    assert cow.turn_lock > 0, "разворот должен быть зафиксирован"
    # и следующий кадр это решение не отменяет
    cow.update(game.tact + 1, 16)
    assert cow.move_direction == -1, "разворот отменён на следующем же кадре"


# ===================== транспорт =====================
#
# Одна идея на всю лестницу: блок, который несёт того, кто в нём стоит.
# Батут (237) — вертикаль для новичка, блоровая дорожка (238) — горизонталь,
# блоровые столбы (234/236) — шахты, портал (232) — мгновенно и дорого.
# См. docs/TRANSPORT.md.

def _drop_player_onto(game, tile_type, height=6):
    """Уронить игрока с высоты на указанный блок и вернуть его."""
    from units.common import TSIZE
    gm = game.game_map
    x, y = _flat_arena(game, w=20)
    gm.set_static_tile(x + 5, y + 1, tile_type)
    game.player.active = True        # в свежем тестовом мире игрок не обновляется
    game.player.tp_to(((x + 5) * TSIZE + 2, (y - height) * TSIZE))
    game.player.first_fall = False
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    return game.player, (x + 5, y)


def test_trampoline_throws_the_player_up():
    """Батут — самый ранний транспорт: он должен реально подбрасывать."""
    game = fresh_world(500)
    player, _ = _drop_player_onto(game, 237)
    bounced = False
    for _ in range(90):
        _run_frames(game, 1)
        if player.vertical_momentum < -0.3:      # летит вверх
            bounced = True
            break
    assert bounced, "батут не подбросил игрока"


def test_trampoline_cancels_fall_damage():
    """И гасит удар: в этом половина смысла раннего транспорта — вертикальный
    мир перестаёт наказывать за спуск ещё до блора на столбы."""
    game = fresh_world(501)
    player, _ = _drop_player_onto(game, 237, height=40)
    lives = player.lives
    _run_frames(game, 120)
    assert player.lives == lives, f"батут не спас от урона: {lives} -> {player.lives}"


def test_falling_on_stone_still_hurts():
    """Контроль: без батута падение с той же высоты обязано бить, иначе
    предыдущий тест ничего не проверяет."""
    game = fresh_world(502)
    player, _ = _drop_player_onto(game, 3, height=40)
    lives = player.lives
    _run_frames(game, 120)
    assert player.lives < lives, "падение с 40 блоков должно наносить урон"


def test_blore_track_carries_the_player():
    """Дорожка несёт игрока без нажатых клавиш — направление задаёт сама
    дорожка, как у конвейера и у блоровых столбов."""
    from units.common import TSIZE
    game = fresh_world(503)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    for tx in range(x, x + 20):
        gm.set_static_tile(tx, y + 1, 238)
    game.player.active = True
    game.player.tp_to((x * TSIZE + 2, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.player.moving_left = game.player.moving_right = False
    start = game.player.rect.x
    _run_frames(game, 40)
    assert game.player.rect.x > start + TSIZE, \
        f"дорожка не понесла игрока: {start} -> {game.player.rect.x}"


def _distance_over(game, tile_type, frames=60, running=False):
    from units.common import TSIZE
    gm = game.game_map
    x, y = _flat_arena(game, w=80)
    for tx in range(x, x + 70):
        gm.set_static_tile(tx, y + 1, tile_type)
    p = game.player
    p.active = True
    p.tp_to((x * TSIZE + 2, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    p.moving_right, p.moving_left = running, False
    start = p.rect.x
    _run_frames(game, frames)
    return (p.rect.x - start) / TSIZE


def test_blore_track_is_faster_than_walking():
    """Транспорт обязан быть быстрее ходьбы — иначе он не транспорт.

    Первая версия читала дорожку из collisions['bottom'] и была МЕДЛЕННЕЕ
    бега: стоя на месте, игрок падает на доли пикселя, rect.y округляется до
    нуля, и столкновение с полом в этом кадре не регистрируется — разгон
    получался рваным (замер: 4.8 блока против 9.1 у бега).
    """
    track = _distance_over(fresh_world(506), 238)
    walk = _distance_over(fresh_world(506), 3, running=True)
    assert track > walk * 1.3, \
        f"дорожка ({track:.1f} блока) должна быть заметно быстрее бега ({walk:.1f})"


def test_blore_track_direction_flips():
    """Правый клик разворачивает дорожку — тот же жест, что у конвейера."""
    from units.common import TSIZE
    game = fresh_world(504)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    for tx in range(x, x + 20):
        gm.set_static_tile(tx, y + 1, 238)
    track = gm.get_tile_obj(*gm.to_chunk_xy(x + 10, y + 1), gm.get_static_tile(x + 10, y + 1)[3])
    assert track.direction() == 1
    track.right_click((0, 0))
    assert track.direction() == -1, "разворот дорожки не сработал"
    # и игрока теперь несёт в другую сторону
    for tx in range(x, x + 20):
        gm.set_static_tile_state_img(tx, y + 1, 1)
    game.player.active = True
    game.player.tp_to(((x + 15) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.player.moving_left = game.player.moving_right = False
    start = game.player.rect.x
    _run_frames(game, 40)
    assert game.player.rect.x < start - TSIZE, \
        f"развёрнутая дорожка должна нести влево: {start} -> {game.player.rect.x}"


def test_blore_track_also_moves_items():
    """Блор несёт ВСЁ, что в нём стоит: дорожка это и транспорт, и логистика.
    Отдельный «рельс» и отдельный «конвейер» были бы двумя блоками про одно."""
    from units.common import TSIZE
    game = fresh_world(505)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    for tx in range(x, x + 20):
        gm.set_static_tile(tx, y + 1, 238)
    track = gm.get_tile_obj(*gm.to_chunk_xy(x + 5, y + 1), gm.get_static_tile(x + 5, y + 1)[3])
    gm.add_item_of_index(3, 1, x + 5, y)
    item = gm.chunk(gm.to_chunk_xy(x + 5, y))[1][-1]
    start = item.rect.x
    for _ in range(20):
        track.tick(1, 16)
    assert item.rect.x > start, f"дорожка не двигает предметы: {start} -> {item.rect.x}"


def test_early_transport_is_reachable_without_iron():
    """Транспорт обязан быть доступен в первые минуты. Батут специально не
    требует ни печки, ни стола: доски — с первого дерева, слизь — с первого
    слизня."""
    from units.creating_items import RECIPES
    recipe = next((r for r in RECIPES if r[0][0] == 237), None)
    assert recipe is not None, "у батута нет рецепта"
    out, ingredients = recipe
    ids = {i[0] for i in ingredients}
    assert ids <= {11, 51}, f"ранний транспорт не должен требовать {ids - {11, 51}}"
    assert 121 not in ids, "батут не должен требовать стол"
    assert out[1] >= 2, "за один крафт должно получаться несколько батутов"


def test_transport_ladder_is_ordered_by_materials():
    """Порядок ступеней транспорта держится на материалах, а не на словах:
    правило из docs/BALANCE.md — рецепт содержит ресурс той зоны, для которой
    блок нужен. Считать «сумму штук» бессмысленно: 4 доски и 2 блоровой руды
    это разные по цене четвёрки и двойки."""
    from units.creating_items import RECIPES
    by_out = {r[0][0]: r for r in RECIPES}
    def ids(idx):
        return {i[0] for i in by_out[idx][1] if i[1] > 0}

    surface = {11, 51, 801, 12, 3}          # то, что есть в первые минуты
    assert ids(237) <= surface, f"батут требует не стартовые ресурсы: {ids(237) - surface}"
    # Блор — то, что удерживает порядок: без спуска в пещеры дорожку не собрать
    assert 61 in ids(238), "дорожка должна стоить блора"
    assert 61 in ids(234), "восходящий столб уже стоит блора — дорожка ему ровня"
    assert 61 not in ids(237), "батут не должен требовать блора"
    # Портал — верх лестницы: дороже по числу разных материалов
    assert len(ids(232)) >= len(ids(238)), "портал должен требовать не меньше видов ресурсов"


# ===================== транспортные средства =====================
#
# Второй вид транспорта: не линия, которую строят, а сущность, на которой
# едут. Ключевое правило — каждое средство умеет РОВНО одну среду и вне её
# мёртвый груз, а не медленный вариант. См. docs/TRANSPORT.md.

def _spawn_vehicle(game, cls, tx, ty):
    from units.common import TSIZE
    v = cls(game, (tx * TSIZE, ty * TSIZE))
    game.game_map.add_dinamic_obj(*game.game_map.to_chunk_xy(tx, ty), v)
    return v


def test_all_five_vehicles_are_registered():
    """Пять средств: по одному на среду — вода, воздух, твердь, лава, вакуум."""
    from units.Objects.Vehicles import VEHICLES, VEHICLES_D
    from units.Tiles import tile_words, IDX_TOOLS
    from units.Tools import TOOLS_CLASSES
    from units.creating_items import RECIPES
    assert len(VEHICLES) == 5, f"средств должно быть 5, а не {len(VEHICLES)}"
    outs = {r[0][0] for r in RECIPES}
    for cls in VEHICLES:
        i = cls.index
        assert i in tile_words, f"{cls.__name__}: нет названия"
        assert i in IDX_TOOLS, f"{cls.__name__}: предмет не зарегистрирован как инструмент"
        assert i in TOOLS_CLASSES, f"{cls.__name__}: нет инструмента установки"
        assert i in outs, f"{cls.__name__}: нет рецепта"
        assert VEHICLES_D[i] is cls
    # среды должны быть разными — иначе средства дублируют друг друга
    mediums = [(c.medium, c.vertical_control) for c in VEHICLES]
    assert len(set(mediums)) >= 4, f"средства должны отличаться средой: {mediums}"


def test_vehicle_carries_the_player():
    """Сел — едешь. Игрок за рулём не должен идти своей физикой."""
    from units.common import TSIZE
    from units.Objects.Vehicles import MineCrawler
    game = fresh_world(700)
    x, y = _flat_arena(game, w=60)
    crawler = _spawn_vehicle(game, MineCrawler, x + 5, y)
    p = game.player
    p.active = True
    p.tp_to(((x + 5) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    assert crawler.mount(p), "не удалось сесть"
    assert p.vehicle is crawler
    p.moving_right, p.moving_left = True, False
    start = crawler.rect.x
    _run_frames(game, 40)
    assert crawler.rect.x > start + TSIZE, f"ползун не поехал: {start} -> {crawler.rect.x}"
    assert abs(p.rect.centerx - crawler.rect.centerx) <= 2, "игрок должен ехать вместе со средством"


def test_vehicle_dismount_puts_player_back():
    from units.common import TSIZE
    from units.Objects.Vehicles import MineCrawler
    game = fresh_world(701)
    x, y = _flat_arena(game, w=40)
    crawler = _spawn_vehicle(game, MineCrawler, x + 5, y)
    p = game.player
    p.active = True
    p.tp_to(((x + 5) * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    crawler.mount(p)
    crawler.dismount()
    assert p.vehicle is None
    assert crawler.driver is None
    assert p.rect.bottom <= crawler.rect.top + 1, "игрок должен встать НА средство, а не в него"
    # и снова может ходить сам
    p.moving_right = True
    start = p.rect.x
    _run_frames(game, 30)
    assert p.rect.x != start, "после высадки игрок должен снова ходить"


def test_vehicle_is_occupied_by_one_driver():
    from units.Objects.Vehicles import Raft
    game = fresh_world(702)
    x, y = _flat_arena(game, w=20)
    raft = _spawn_vehicle(game, Raft, x + 3, y)
    p = game.player
    assert raft.mount(p) is True
    assert raft.mount(p) is False, "занятое средство не должно пускать второго"


def test_each_vehicle_works_only_in_its_medium():
    """Главное правило: вне своей среды средство не едет.

    Иначе пять средств были бы пятью скинами одного, и смысла в лестнице
    (вода → воздух → твердь → лава → вакуум) не осталось бы."""
    from units.common import TSIZE, START_SPACE_Y
    from units.Objects.Vehicles import Raft, LavaBarge, VoidSkiff
    game = fresh_world(703)
    x, y = _flat_arena(game, w=30)
    gm = game.game_map

    # плот на суше — не в своей среде
    raft = _spawn_vehicle(game, Raft, x + 3, y)
    raft.collisions = {"bottom": [((0, 0), 3)]}
    assert not raft.in_medium(), "плот на суше работать не должен"
    # налили воду — заработал
    for tx in range(x, x + 10):
        gm.set_static_tile(tx, y + 1, 120)
    raft.rect.midbottom = ((x + 5) * TSIZE, (y + 1) * TSIZE)
    assert raft.in_medium(), "плот на воде должен работать"

    # баржа держится на лаве, но не на воде
    barge = _spawn_vehicle(game, LavaBarge, x + 3, y)
    barge.rect.midbottom = ((x + 5) * TSIZE, (y + 1) * TSIZE)
    assert not barge.in_medium(), "баржа не должна работать на воде"
    gm.set_static_tile(x + 5, y + 1, 140)
    assert barge.in_medium(), "баржа должна работать на лаве"

    # скиф — только в вакууме
    skiff = _spawn_vehicle(game, VoidSkiff, x + 3, y)
    assert not skiff.in_medium(), "скиф в атмосфере работать не должен"
    skiff.rect.centery = (START_SPACE_Y - 10) * TSIZE
    assert skiff.in_medium(), "скиф в космосе должен работать"


def test_lava_barge_survives_lava():
    """Баржа делает главное препятствие ада его же дорогой — значит не горит."""
    from units.Objects.Vehicles import LavaBarge, Raft
    assert 140 in LavaBarge.immune_tiles, "баржа обязана быть неуязвима к лаве"
    assert 140 not in Raft.immune_tiles, "плот в лаве гореть должен"


def test_broken_vehicle_returns_its_item():
    """Разбил — получил предмет обратно, а не потерял средство насовсем."""
    from units.common import TSIZE, OBJ_ITEM
    from units.Objects.Vehicles import MineCrawler
    game = fresh_world(704)
    x, y = _flat_arena(game, w=20)
    crawler = _spawn_vehicle(game, MineCrawler, x + 5, y)
    crawler.kill()
    gm = game.game_map
    chunk = gm.chunk(gm.to_chunk_xy(x + 5, y))
    dropped = [o for o in chunk[1] if o.class_obj & OBJ_ITEM and o.index == MineCrawler.index]
    assert dropped, "разбитое средство должно выпасть предметом"


def test_vehicle_speed_ladder():
    """Средство обязано быть быстрее ходьбы, иначе оно не транспорт, а мебель.

    Первая версия этого не проходила: опора проверялась по
    collisions['bottom'], а стоя на месте средство падает на доли пикселя,
    rect.y округляется до нуля и столкновения в кадре нет — опора «мигала»
    через кадр и рвала разгон (ползун 10.9 блока против 9.1 у пешей ходьбы).
    """
    from units.common import TSIZE
    from units.Objects.Vehicles import MineCrawler

    def walk():
        game = fresh_world(705)
        x, y = _flat_arena(game, w=90)
        p = game.player
        p.active = True
        p.tp_to((x * TSIZE, y * TSIZE))
        game.screen_map.teleport_to_player()
        p.moving_right, p.moving_left = True, False
        start = p.rect.x
        _run_frames(game, 60)
        return (p.rect.x - start) / TSIZE

    def ride():
        game = fresh_world(705)
        x, y = _flat_arena(game, w=90)
        v = _spawn_vehicle(game, MineCrawler, x + 3, y)
        p = game.player
        p.active = True
        p.tp_to(((x + 3) * TSIZE, y * TSIZE))
        game.screen_map.teleport_to_player()
        v.mount(p)
        p.moving_right, p.moving_left = True, False
        start = v.rect.x
        _run_frames(game, 60)
        return (v.rect.x - start) / TSIZE

    on_foot, on_crawler = walk(), ride()
    assert on_crawler > on_foot * 1.4, \
        f"ползун ({on_crawler:.1f} блока) должен быть заметно быстрее ходьбы ({on_foot:.1f})"


def test_vehicle_survives_save_and_load():
    """Средство живёт в чанке как существо — значит обязано сохраняться."""
    from units.common import TSIZE, OBJ_VEHICLE
    from units.Objects.Vehicles import AirBoat
    game = fresh_world(706)
    x, y = _flat_arena(game, w=30)
    _spawn_vehicle(game, AirBoat, x + 5, y)
    gm = game.game_map
    gm.save_current_game_map()
    wid = gm.world_id
    fresh_world(707)                      # затираем всё другим миром
    assert gm.open_game_map(game, wid), "мир должен загрузиться"
    chunk = gm.chunk(gm.to_chunk_xy(x + 5, y))
    found = [o for o in (chunk[1] if chunk else []) if o.class_obj & OBJ_VEHICLE]
    assert found, "средство пропало после сохранения и загрузки"
    assert isinstance(found[0], AirBoat)
    assert found[0].driver is None, "водитель не должен воскресать из сейва"


def test_vehicle_recipes_are_gated_by_zone():
    """Зональный вентиль: баржу не собрать, не побывав в аду, скиф — в космосе.
    Это единственное, что удерживает порядок открытия (docs/BALANCE_SCHEME.md)."""
    from units.creating_items import RECIPES
    by_out = {r[0][0]: r for r in RECIPES}
    def ids(idx):
        return {i[0] for i in by_out[idx][1] if i[1] > 0}
    assert 402 in ids(614), "адская баржа должна требовать серу"
    assert 408 in ids(615), "пустотный скиф должен требовать космическую пыль"
    assert 61 in ids(612), "воздушная лодка держится на блоре — как и всё перемещение"
    # плот — самое раннее: ни металла, ни зональных ресурсов
    early = {12, 106, 801, 11, 51, 3}
    assert ids(611) <= early, f"плот не должен требовать {ids(611) - early}"


# ===================== сутки, события, сюжет =====================
#
# До этого в игре не происходило ничего: мир был неподвижен во времени, никто
# не угрожал, никто ничего не просил, а сюжет лежал в docs/STORY.md и в поле
# read_inscriptions, у которого не было ни одного читателя.

def test_new_world_starts_in_daylight():
    """Сутки начинаются ДНЁМ. При порядке «сначала рассвет» world_time == 0
    попадал на темноту, и первое, что видел игрок в новом мире, — ночь."""
    from units.common import daylight, is_night
    game = fresh_world(910)
    assert game.game_map.world_time == 0
    assert daylight(0) == 1.0, "новый мир должен начинаться при полном свете"
    assert not is_night(0)


def test_day_night_cycle_is_a_full_circle():
    """Свет обязан пройти полный круг: день → закат → ночь → рассвет → день."""
    from units.common import DAY_LENGTH, daylight, is_night
    seen_day = seen_night = seen_twilight = False
    for i in range(200):
        t = int(DAY_LENGTH * i / 200)
        light = daylight(t)
        if light == 1.0:
            seen_day = True
        elif light <= 0.3:
            seen_night = True
        else:
            seen_twilight = True
    assert seen_day and seen_night and seen_twilight, "в сутках должны быть все фазы"
    assert daylight(0) == daylight(DAY_LENGTH), "цикл должен замыкаться"
    assert is_night(int(DAY_LENGTH * 0.8)), "середина ночи обязана быть ночью"


def test_underground_does_not_blink_with_the_night():
    """Под землёй смена суток ничего не значит: там свой свет, и мигающая с
    ночью пещера читалась бы как баг."""
    from units.common import DAY_LENGTH, surface_daylight, BOTTOM_MIDDLE_WORLD
    night = int(DAY_LENGTH * 0.8)
    assert surface_daylight(night, 0) < 0.5, "на поверхности ночью темно"
    assert surface_daylight(night, BOTTOM_MIDDLE_WORLD) == 1.0, "внизу ночи нет"
    assert surface_daylight(night, 200) > surface_daylight(night, 0), "глубже — меньше влияния"


def test_world_time_survives_save_and_load():
    """Время суток живёт в мире, а не в запуске: иначе каждая загрузка
    выбрасывала бы игрока в один и тот же час."""
    game = fresh_world(911)
    gm = game.game_map
    gm.world_time = 12345
    gm.save_current_game_map()
    wid = gm.world_id
    fresh_world(912)
    assert gm.open_game_map(game, wid)
    assert gm.world_time == 12345, f"часы мира сбросились: {gm.world_time}"


def test_lit_lamp_keeps_creatures_away():
    """Свет отгоняет тварей — и это первая причина тянуть провода не из
    любопытства, а чтобы ночью не съели.

    Проверяется именно ПИТАНИЕ, а не наличие блока: лампа без сигнала это
    просто стекляшка.
    """
    game = fresh_world(913)
    gm = game.game_map
    x, y = _flat_arena(game, w=30)
    lamp = _place_block(gm, x + 10, y, 215)
    assert lamp is not None
    assert not gm.lit_by_lamp(x + 10, y), "негорящая лампа не должна защищать"
    lamp.activated_tact = game.tact          # подали сигнал
    assert gm.lit_by_lamp(x + 10, y), "горящая лампа должна отгонять"
    assert gm.lit_by_lamp(x + 10 + gm.LAMP_SAFE_RADIUS, y), "на границе радиуса — ещё защищает"
    assert not gm.lit_by_lamp(x + 10 + gm.LAMP_SAFE_RADIUS + 3, y), "дальше радиуса — уже нет"


def test_night_raid_only_at_night_and_on_the_surface():
    """Налёт — событие, а не расписание: он не идёт днём и не идёт под землёй,
    где случайный спавн от него не отличить."""
    from units.common import TSIZE, DAY_LENGTH
    from units.Events import NightRaid
    game = fresh_world(914)
    raid = NightRaid()
    game.player.tp_to((0, 8 * TSIZE))
    assert not raid.can_start(game, 0), "днём налёта быть не должно"
    night = int(DAY_LENGTH * 0.8)
    assert raid.can_start(game, night), "ночью на поверхности налёт возможен"
    game.player.tp_to((0, 600 * TSIZE))                # глубоко под землёй
    assert not raid.can_start(game, night), "под землёй налёта быть не должно"


def test_event_warns_before_it_starts():
    """Событие предупреждает о себе: внезапная смерть из ниоткуда — это не
    сложность, а несправедливость."""
    from units.common import TSIZE, DAY_LENGTH
    from units.Events import NightRaid
    game = fresh_world(915)
    raid = NightRaid()
    game.player.tp_to((0, 8 * TSIZE))
    t = int(DAY_LENGTH * 0.8)
    raid.tick(game, t)
    assert raid.warned_at == t, "первым делом событие обязано предупредить"
    assert not raid.active(), "и не начинаться в тот же такт"
    raid.tick(game, t + raid.warning)
    assert raid.active(), "после предупреждения событие должно начаться"


def test_only_one_event_at_a_time():
    """Два наложившихся события игрок читает как «игра сломалась»."""
    from units.common import TSIZE, DAY_LENGTH
    from units.Events import EventDirector
    game = fresh_world(916)
    director = EventDirector()
    game.player.tp_to((0, 8 * TSIZE))
    game.game_map.world_time = int(DAY_LENGTH * 0.8)
    for _ in range(400):
        game.game_map.world_time += 10
        director.update(game)
    assert sum(1 for e in director.events if e.active()) <= 1


def test_story_goal_advances_with_the_world():
    """Цель проверяется по состоянию мира, а не по скрипту: прочитал плиту —
    акт закрылся сам."""
    from units.Story import current_goal, update_story
    game = fresh_world(917)
    first = current_goal(game)
    assert first, "у нового мира должна быть цель"
    game.game_map.read_inscriptions = ["altar"]
    closed = update_story(game)
    assert closed is not None and closed.id == "arrival"
    assert current_goal(game) != first, "цель должна смениться"


def test_story_progress_is_irreversible():
    """Выполненный акт остаётся выполненным: иначе цель прыгала бы назад."""
    from units.Story import update_story, current_act
    game = fresh_world(918)
    game.game_map.read_inscriptions = ["altar"]
    update_story(game)
    game.game_map.read_inscriptions = []      # условие пропало
    update_story(game)
    assert "arrival" in game.game_map.story_done, "прогресс не должен откатываться"
    assert current_act(game).id != "arrival"


def test_story_survives_save_and_load():
    from units.Story import update_story
    game = fresh_world(919)
    game.game_map.read_inscriptions = ["altar"]
    update_story(game)
    gm = game.game_map
    gm.save_current_game_map()
    wid = gm.world_id
    fresh_world(920)
    assert gm.open_game_map(game, wid)
    assert "arrival" in gm.story_done, "сюжет должен сохраняться вместе с миром"


def test_journal_shows_acts_and_read_notes():
    """Журнал — тот самый читатель, которого у read_inscriptions не было."""
    from units.Story import journal_entries, ACTS
    game = fresh_world(921)
    game.game_map.read_inscriptions = ["altar"]
    acts, notes = journal_entries(game)
    assert len(acts) == len(ACTS)
    assert notes and "алтар" in notes[0][0].lower(), f"надпись не попала в журнал: {notes}"


def test_story_never_crashes_on_an_old_world():
    """Мир мог быть создан версией без сюжетных полей — сюжет обязан это
    пережить, а не уронить игру."""
    from units.Story import update_story, current_goal, journal_entries
    game = fresh_world(922)
    gm = game.game_map
    for field in ("story_done", "story_flags", "read_inscriptions", "world_time"):
        if hasattr(gm, field):
            delattr(gm, field)
    update_story(game)
    assert current_goal(game)
    journal_entries(game)


# ===================== подземелья =====================

def _dungeons(seed=1234, limit=30):
    from units.Map.Dungeons import dungeon_site, in_dungeon_band
    game = fresh_world(seed)
    base = game.game_map.base_generation
    out = []
    for cx in range(14):
        for cy in range(1, 14):
            d = dungeon_site(cx, cy, base)
            if d is not None and in_dungeon_band(d.y):
                out.append(d)
                if len(out) >= limit:
                    return game, base, out
    return game, base, out


def _reachable(dungeon):
    """Куда можно дойти от входа: воздух, лифты и плиты проходимы."""
    from collections import deque
    passable = {0, 234, 236, 300}
    rx, ry, rw, rh = dungeon.room_rect(*dungeon.entrance)
    start = (rx + 2, ry + rh - 2)
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in seen or not dungeon.contains(nx, ny):
                continue
            if dungeon.tile_at(nx, ny) in passable:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def test_dungeon_vault_is_always_reachable():
    """Самая важная проверка: до сокровищницы можно дойти.

    Она поймала три разных дефекта подряд, и ни один не был виден снаружи —
    подземелье каждый раз выглядело целым:
    1. пол комнаты перекрывал вертикальную шахту (25 из 25 непроходимы);
    2. нижний ряд комнат связывался жребием, а в нём сокровищница (8 из 25);
    3. рудная кладка забивала собственный дверной проём (4 из 32).
    """
    _, _, dungeons = _dungeons()
    assert len(dungeons) >= 10, "мало подземелий для проверки"
    broken = []
    for d in dungeons:
        seen = _reachable(d)
        vx, vy, vw, vh = d.room_rect(*d.vault)
        if not any((vx + i, vy + vh - 2) in seen for i in range(vw)):
            broken.append((d.x, d.y))
    assert not broken, f"сокровищница недостижима в {len(broken)} из {len(dungeons)}: {broken[:3]}"


def test_dungeon_has_an_entrance_from_outside():
    """Запечатанное подземелье — это потраченная генерация: его не найти."""
    _, _, dungeons = _dungeons()
    for d in dungeons[:10]:
        seen = _reachable(d)
        outside = [(x, y) for (x, y) in seen
                   if x < d.x or x >= d.x + d.w]
        assert outside, f"у подземелья на ({d.x},{d.y}) нет выхода наружу"


def test_dungeon_layout_is_deterministic():
    """Раскладка — чистая функция от (клетка, сид), как у озёр: иначе
    подземелье, пересекающее границу чанков, порвалось бы пополам."""
    from units.Map.Dungeons import dungeon_site, dungeon_tile_at
    game = fresh_world(1235)
    base = game.game_map.base_generation
    a = dungeon_site(3, 2, base)
    b = dungeon_site(3, 2, base)
    assert (a is None) == (b is None)
    if a is None:
        return
    assert (a.x, a.y, a.w, a.h, a.cols, a.rows) == (b.x, b.y, b.w, b.h, b.cols, b.rows)
    for tx in range(a.x, a.x + min(a.w, 40)):
        for ty in range(a.y, a.y + min(a.h, 20)):
            assert dungeon_tile_at(tx, ty, base) == dungeon_tile_at(tx, ty, base)


def test_dungeons_are_underground():
    """Подземелье должно быть НАЙДЕНО, а не торчать из холма у спавна."""
    from units.Map.Dungeons import in_dungeon_band, MIN_DEPTH
    assert not in_dungeon_band(0)
    assert not in_dungeon_band(MIN_DEPTH - 1)
    assert in_dungeon_band(MIN_DEPTH + 50)


def test_dungeon_vault_pays_for_the_trip():
    """Награда подземелья — плотность, а не редкость: те же руды, что в мире,
    но собранные в одном месте (docs/BALANCE_SCHEME.md)."""
    from collections import Counter
    _, _, dungeons = _dungeons()
    ores = Counter()
    for d in dungeons:
        vx, vy, vw, vh = d.room_rect(*d.vault)
        for ty in range(vy, vy + vh):
            for tx in range(vx, vx + vw):
                t = d.tile_at(tx, ty)
                if t in (21, 23, 24, 25):
                    ores[t] += 1
    per = {k: v / len(dungeons) for k, v in ores.items()}
    assert sum(per.values()) >= 8, f"в сокровищнице слишком мало руды: {per}"
    assert per.get(23, 0) >= 1, "золото должно встречаться — ради него и идут"
    assert per.get(23, 0) < sum(per.values()) / 2, \
        f"золота не должно быть больше всей остальной руды: {per}"


def test_dungeon_appears_in_a_generated_chunk():
    """Подземелье должно попадать в настоящую генерацию, а не только в
    собственную функцию."""
    from units.common import CHUNK_SIZE
    game, base, dungeons = _dungeons(limit=6)
    gm = game.game_map
    d = dungeons[0]
    cx, cy = d.x // CHUNK_SIZE, (d.y + 3) // CHUNK_SIZE
    gm.game_map.pop((cx, cy), None)
    gm.generate_chunk(cx, cy)
    walls = sum(1 for i in range(0, gm.chunk_arr_size, gm.tile_data_size)
                if gm.chunk((cx, cy))[0][i] in (31, 32, 33))
    assert walls > 20, f"кладки подземелья в чанке нет: {walls} тайлов"


def test_dungeon_guards_do_not_double_on_regeneration():
    """Стражи — функция сида: чанк, созданный дважды, даёт тех же, а не толпу.
    Мир выгружает и пересоздаёт чанки на ходу (dynamic_dump)."""
    _, _, dungeons = _dungeons(limit=8)
    from units.common import CHUNK_SIZE
    d = dungeons[0]
    cx, cy = d.x // CHUNK_SIZE, d.y // CHUNK_SIZE
    first = d.guard_spots(cx, cy, CHUNK_SIZE)
    second = d.guard_spots(cx, cy, CHUNK_SIZE)
    assert first == second, "раскладка стражей должна быть детерминированной"


def test_dungeon_kinds_differ_by_zone():
    """Каждой зоне свой вид: склеп в пещерах, кузня в аду, станция в космосе."""
    from units.Map.Dungeons import kind_for_depth, KINDS
    from units.common import START_HELL_Y, START_SPACE_Y
    assert kind_for_depth(500) == "crypt"
    assert kind_for_depth(START_HELL_Y + 50) == "forge"
    assert kind_for_depth(START_SPACE_Y) == "station"
    assert len({k.wall for k in KINDS.values()}) >= 2, "виды должны отличаться кладкой"


# ===================== события: расширенный набор =====================

def test_seven_events_cover_the_zones():
    """События должны покрывать разные места и время, а не быть семью
    вариантами одного налёта."""
    from units.Events import EventDirector
    director = EventDirector()
    assert len(director.events) >= 7, f"событий всего {len(director.events)}"
    names = {e.name for e in director.events}
    assert len(names) == len(director.events), "имена событий должны различаться"


def test_not_every_event_is_an_attack():
    """Если КАЖДОЕ событие бьёт, они сливаются в ровный стресс, и игрок
    пережидает их все одинаково — в яме. Миграция не угроза вообще."""
    from units.common import TSIZE, DAY_LENGTH
    from units.Events import Migration
    from units.Objects.Creatures import TEMPER_AGGRESSIVE
    game = fresh_world(930)
    x, y = _flat_arena(game, w=40)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    event = Migration()
    assert event.can_start(game, 0), "миграция идёт днём"
    assert not event.can_start(game, int(DAY_LENGTH * 0.8)), "и не ночью"
    event.started_at = 0          # обычно ставит tick(), тут дёргаем напрямую
    event.on_start(game)
    gm = game.game_map
    # Ловим ровно тех, кого добавило СОБЫТИЕ. Считать по округе нельзя:
    # событие попутно создаёт чанки, а свежий чанк приходит со своими
    # существами, среди которых бывают и агрессивные.
    arrived = []
    real_add = gm.add_dinamic_obj

    def catching(cx, cy, obj, create_chunk=True):
        from units.common import OBJ_CREATURE
        if obj.class_obj & OBJ_CREATURE:
            arrived.append(obj)
        return real_add(cx, cy, obj, create_chunk)

    gm.add_dinamic_obj = catching
    try:
        for i in range(1, event.STEP * (event.HERD + 1)):
            event.on_tick(game, i)
    finally:
        del gm.add_dinamic_obj
    assert arrived, "стадо должно появиться"
    for creature in arrived:
        assert creature.temperament != TEMPER_AGGRESSIVE, \
            f"{type(creature).__name__} в миграции агрессивен — это уже налёт"


def _creatures(gm, tx, ty, radius=3):
    from units.common import OBJ_CREATURE
    cx0, cy0 = gm.to_chunk_xy(tx, ty)
    out = []
    for cx in range(cx0 - radius, cx0 + radius + 1):
        for cy in range(cy0 - radius, cy0 + radius + 1):
            chunk = gm.chunk((cx, cy))
            if chunk:
                out += [o for o in chunk[1] if o.class_obj & OBJ_CREATURE and o.alive]
    return out


def _count_creatures(gm, tx, ty, radius=3):
    return len(_creatures(gm, tx, ty, radius))


def test_meteor_shower_leaves_a_prize():
    """Событие-награда: дождь оставляет космическую пыль на поверхности —
    единственный способ увидеть материал верхней зоны, не добравшись до неё."""
    from units.common import TSIZE, DAY_LENGTH, OBJ_ITEM
    from units.Events import MeteorShower
    game = fresh_world(931)
    x, y = _flat_arena(game, w=60)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    event = MeteorShower()
    assert event.can_start(game, int(DAY_LENGTH * 0.8)), "дождь идёт ночью"
    assert not event.can_start(game, 0), "и не днём"
    gm = game.game_map
    for _ in range(12):
        event.drop_one(game)
    prizes = [o for o in _items_around(gm, x, y) if o.index in (408, 66)]
    assert prizes, "после дождя должна остаться добыча"


def _items_around(gm, tx, ty, radius=3):
    from units.common import OBJ_ITEM
    cx0, cy0 = gm.to_chunk_xy(tx, ty)
    out = []
    for cx in range(cx0 - radius, cx0 + radius + 1):
        for cy in range(cy0 - radius, cy0 + radius + 1):
            chunk = gm.chunk((cx, cy))
            if chunk:
                out += [o for o in chunk[1] if o.class_obj & OBJ_ITEM and o.alive]
    return out


def test_events_are_tied_to_places():
    """Каждое событие обязано иметь своё место: событие «везде» неотличимо от
    обычного спавна и не даёт месту характера."""
    from units.common import TSIZE, DAY_LENGTH, START_SPACE_Y
    from units.Events import EventDirector
    game = fresh_world(932)
    director = EventDirector()
    night = int(DAY_LENGTH * 0.8)
    places = {"поверхность": 8, "пещеры": 700, "космос": START_SPACE_Y - 300}
    fired = {}
    for name, ty in places.items():
        game.player.tp_to((0, ty * TSIZE))
        fired[name] = {e.name for e in director.events
                       if e.can_start(game, night) or e.can_start(game, 0)}
    assert fired["поверхность"] != fired["пещеры"], "поверхность и пещеры должны отличаться"
    assert fired["космос"] != fired["поверхность"], "космос должен отличаться"
    for name, evs in fired.items():
        assert evs, f"в месте «{name}» не может произойти вообще ничего"


# ===================== наполнение контейнеров, НПС, полный сюжет ============

def test_container_is_never_empty():
    """Пустой контейнер — худший исход находки: игрок дошёл, открыл и получил
    ничего. Все шансы в таблице могут не сработать разом, поэтому минимум
    одна позиция выдаётся принудительно."""
    import random as _r
    from units.Loot import TABLES
    for name, table in TABLES.items():
        for i in range(60):
            rolled = table.roll(_r.Random(f"t{i}"), 0.0)
            assert rolled, f"таблица «{name}» выдала пустоту на броске {i}"


def test_loot_is_deterministic_per_position():
    """Сундук, найденный дважды, даёт то же самое: чанки выгружаются и
    создаются заново на ходу, и «новая порция при каждом заходе» была бы
    бесконечным источником золота."""
    from units.Loot import fill_container
    from units.Inventory import Inventory
    game = fresh_world(960)
    gm = game.game_map
    first = fill_container(game, Inventory(gm, None, [5, 3]), 100, 600, 7, "забой")
    second = fill_container(game, Inventory(gm, None, [5, 3]), 100, 600, 7, "забой")
    assert first == second, f"выдача разошлась: {first} против {second}"
    other = fill_container(game, Inventory(gm, None, [5, 3]), 101, 600, 7, "забой")
    assert other != first, "разные сундуки не должны давать одно и то же"


def test_loot_grows_with_depth():
    """Награда идёт по той же кривой, что и опасность."""
    import random as _r
    from units.Loot import MINE
    shallow = sum(c for _, c in MINE.roll(_r.Random("d"), 0.0))
    deep = sum(c for _, c in MINE.roll(_r.Random("d"), 1.0))
    assert deep > shallow, f"на глубине должно быть больше: {shallow} -> {deep}"


def test_cupboard_is_a_container_now():
    """Шкаф был чистой мебелью — блоком без инвентаря, который структуры
    ставили как обстановку. Открыть его было нельзя."""
    from units.Tiles import CLASS_TILE
    from units.Objects.TileClasses import tiles_class, Cupboard
    from units.UI.BlocksUI import BLOCKS_UI
    assert 126 in CLASS_TILE
    assert tiles_class[126] is Cupboard
    assert 126 in BLOCKS_UI, "у шкафа должен быть интерфейс"
    game = fresh_world(961)
    obj = _place_block(game.game_map, 40, 8, 126)
    assert obj is not None and getattr(obj, "inventory", None) is not None


def test_generated_class_tiles_get_their_objects():
    """Генератор пишет тайлы прямо в массив, минуя set_static_tile, поэтому у
    сундука, лампы и плиты подземелья не появлялось объекта: лампа не светила,
    плита не читалась, сундук не открывался вовсе."""
    from units.common import CHUNK_SIZE
    from units.Map.Dungeons import dungeon_site, in_dungeon_band
    game = fresh_world(962)
    gm = game.game_map
    base = gm.base_generation
    site = next(s for s in (dungeon_site(cx, cy, base)
                            for cx in range(14) for cy in range(1, 14))
                if s is not None and in_dungeon_band(s.y))
    r, c = site.vault
    rx, ry, rw, rh = site.room_rect(r, c)
    tx, ty = rx + rw // 2, ry + rh - 2
    gm.generate_chunk(tx // CHUNK_SIZE, ty // CHUNK_SIZE)
    tile = gm.get_static_tile(tx, ty)
    assert tile and tile[0] == 129, f"сундука в сокровищнице нет: {tile}"
    obj = gm.get_tile_obj(*gm.to_chunk_xy(tx, ty), tile[3])
    assert obj is not None, "у сундука подземелья нет объекта"
    assert any(cell for cell in obj.inventory), "сундук подземелья пуст"


def test_echo_answers_the_current_chapter():
    """Отголосок — единственный НПС, и он не человек: соплеменников не
    осталось, живой болтливый спутник отменил бы тон брошенного мира.
    Он отвечает на главу, в которой игрок СЕЙЧАС."""
    from units.Lore import echo_for_act, ECHOES
    from units.Story import ACTS, update_story, current_act
    game = fresh_world(963)
    first = current_act(game)
    line_before = echo_for_act(first.id)
    game.game_map.read_inscriptions = ["altar"]
    update_story(game)
    line_after = echo_for_act(current_act(game).id)
    assert line_before != line_after, "реплика должна меняться вместе с главой"
    for act in ACTS:
        assert act.id in ECHOES, f"у главы {act.id} нет реплики отголоска"
    silent = echo_for_act(None)
    assert silent and silent[1], "пройденный сюжет тоже должен что-то отвечать"


def test_echo_is_registered_and_walkable():
    """Отголосок — не препятствие: он висит в воздухе, сквозь него проходят."""
    from units.Tiles import CLASS_TILE, SEMIPHYSBODY_TILES, PHYSBODY_TILES, tile_words
    from units.Objects.TileClasses import tiles_class, Echo
    assert 239 in tile_words and 239 in CLASS_TILE
    assert tiles_class[239] is Echo
    assert 239 in SEMIPHYSBODY_TILES and 239 not in PHYSBODY_TILES


def test_altar_has_an_echo_nearby():
    """Первое, что игрок встречает после плиты, — отголосок: он говорит, куда
    идти, ничего не приказывая."""
    from units.common import TSIZE
    from units import config
    game = fresh_world(964)
    gm = game.game_map
    pos = config.GameSettings.start_pos
    px, py = pos[0] // TSIZE, pos[1] // TSIZE
    found = any(gm.get_static_tile_type(px + dx, py + dy, 0, create_chunk=False) == 239
                for dx in range(-2, 9) for dy in range(-4, 9))
    assert found, "у алтаря должен стоять отголосок"


def test_story_covers_every_chapter_of_the_storybook():
    """Сюжет из стори-бука доведён до игры целиком, а не первыми тремя главами.

    Число глав сверяется со СТОРИ-БУКОМ, а не с константой в тесте: раньше
    здесь стояло «должно быть 12», и пятый акт уронил тест, хотя и код, и
    документ были согласованы между собой."""
    import re
    from units.Story import ACTS
    book = open("docs/STORYBOOK.md", encoding="utf-8").read()
    chapters = set(re.findall(r"\*\*Глава (\d+)\.", book))
    assert len(ACTS) == len(chapters), \
        f"глав в коде {len(ACTS)}, в стори-буке {len(chapters)}"
    acts_titles = {a.title for a in ACTS}
    book_acts = set(re.findall(r"### (Акт [IVX]+)\.", book))
    assert len(acts_titles) == len(book_acts), \
        f"актов в коде {len(acts_titles)}, в стори-буке {len(book_acts)}"
    ids = [a.id for a in ACTS]
    assert len(set(ids)) == len(ids), "id глав должны быть уникальны"
    for a in ACTS:
        assert a.goal and len(a.goal) > 10, f"у главы {a.id} нет внятной цели"


def test_story_never_nags():
    """Главное требование к ведению: подсказка не должна бесить. Значит игра
    НЕ напоминает о невыполненной цели — сообщение приходит только когда
    глава ЗАКРЫЛАСЬ, то есть как награда, а не как понукание."""
    from units.Story import update_story
    game = fresh_world(965)
    # десять секунд «ничего не делаем» — ни одного сообщения быть не должно
    said = []
    real = game.ui.new_sys_message
    game.ui.new_sys_message = lambda text, *a, **k: said.append(text)
    try:
        for _ in range(10):
            assert update_story(game) is None or True
        assert not said, f"игра напомнила о цели сама: {said}"
        # а вот закрытие главы сообщить обязана
        game.game_map.read_inscriptions = ["altar"]
        closed = update_story(game)
        assert closed is not None
    finally:
        del game.ui.new_sys_message


def test_creatures_do_not_see_through_stone():
    """Стая сбегалась к игроку, который копал в закрытой шахте через двадцать
    блоков породы."""
    from units.common import TSIZE
    from units.Objects.Creatures import Wolf
    game = fresh_world(402)
    x, y = _flat_arena(game, w=30)
    wolf = _place(game, Wolf, x + 6, y)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    game.update()
    assert wolf.sees_player(), "на открытом месте игрок виден"

    for dy in range(-3, 2):                     # стена между ними
        for dx in range(0, 3):
            game.game_map.set_static_tile(x + 3 + dx, y + dy, 3)
    assert not wolf.sees_player(), "сквозь породу видеть нельзя"


def test_hurt_peaceful_creature_flees_and_calms_down_later():
    """Задели — убегает; но не до конца жизни мира."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow, ST_FLEE
    game = fresh_world(403)
    x, y = _flat_arena(game)
    cow = _place(game, Cow, x + 20, y)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    game.update()
    assert not cow.provoked

    cow.damage(1)
    assert cow.provoked and cow.alert_tacts > 0
    cow.think(game.tact)
    assert cow.state == ST_FLEE

    game.player.tp_to(((x + 500) * TSIZE, y * TSIZE))
    for _ in range(cow.memory_tacts + 10):
        game.tact += 1
        cow.think(game.tact)
    assert not cow.provoked, "испуг должен проходить"


def test_territorial_creature_attacks_only_when_touched():
    """Кабан не охотится, но задень его — ответит. Раньше он гонялся за
    игроком с полэкрана, как волк."""
    from units.common import TSIZE
    from units.Objects.Creatures import Boar, ST_CHASE
    game = fresh_world(404)
    x, y = _flat_arena(game)
    boar = _place(game, Boar, x + 7, y)
    game.player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    _run_frames(game, 20)
    assert boar.state != ST_CHASE, "издалека кабан не нападает"

    boar.damage(1)
    boar.think(game.tact)
    assert boar.state == ST_CHASE, "после удара — нападает"


def test_creatures_stand_still_sometimes():
    """Без паузы звери бесконечно семенят из стороны в сторону — это первое,
    что читается как «болванчик»."""
    from units.Objects.Creatures import Cow, ST_IDLE
    game = fresh_world(405)
    x, y = _flat_arena(game)
    cow = _place(game, Cow, x + 8, y)
    game.player.tp_to((-9000 * 32, 0))       # игрока рядом нет
    states = set()
    for _ in range(3000):
        game.tact += 1
        cow.think(game.tact)
        states.add(cow.state)
    assert ST_IDLE in states, f"существо должно иногда стоять, состояния: {states}"


def test_creature_jumps_over_a_gap_instead_of_turning_back():
    """У провала существо просто разворачивалось и не могло сойти с островка,
    на котором появилось."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow
    game = fresh_world(406)
    gm = game.game_map
    x, y = 70, 8
    for tx in range(x - 4, x + 20):
        for dy in range(0, 7):
            gm.set_static_tile(tx, y - dy, 0)
        gm.set_static_tile(tx, y + 1, 3)
    gm.set_static_tile(x + 4, y + 1, 0)          # провал в один тайл
    cow = _place(game, Cow, x + 3, y)
    # Ставим корову СТОЯЩЕЙ вплотную к провалу: пока она падает, её низ не
    # привязан к границе тайла, и вопрос «прыгать ли» не имеет смысла.
    # На 2 пикселя ВНУТРЬ пола: коллизия «снизу» возникает только когда
    # существо реально въехало в блок, а стоя ровно на границе оно за кадр
    # опускается меньше чем на пиксель и физика не считает это опорой.
    cow.rect.bottom = (y + 1) * TSIZE + 2
    # Игрок рядом (иначе существо за экраном не обновляется, см.
    # COLLIDE_MARGIN), а реакции подавляем в hold_course: иначе корова то
    # убегает, то разворачивается по таймеру, и тест проверяет случайность.
    game.player.tp_to((x * TSIZE, (y - 6) * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16

    def hold_course():
        from units.Objects.Creatures import ST_WANDER
        cow.state = ST_WANDER
        cow.move_tact = 10 ** 6      # не перевыбирать направление
        cow.move_direction = 1
        cow.alert_tacts = 0

    hold_course()
    game.update()
    assert cow.collisions.get("bottom"), "корова должна стоять на полу"
    hold_course()
    assert cow.rect.centerx // TSIZE == x + 3, "корова стоит перед провалом"
    assert cow.can_jump_the_gap(), "за провалом есть твердь — надо прыгать"
    cow.check_abyss()
    assert cow.move_direction == 1, "разворачиваться не должен"

    # и провал действительно преодолевается
    start = cow.rect.centerx // TSIZE
    for _ in range(400):
        hold_course()
        game.update()
    assert cow.rect.centerx // TSIZE > x + 4, \
        f"корова должна перебраться за провал (x={x + 4}), была на {start}, стала на {cow.rect.centerx // TSIZE}"


def test_creature_does_not_jump_on_flat_ground():
    """Прыжок через провал не должен срабатывать на ровном месте: с проверкой
    «есть ли пол где-то впереди» существо прыгало непрерывно."""
    from units.common import TSIZE
    from units.Objects.Creatures import Cow
    game = fresh_world(407)
    x, y = _flat_arena(game, w=30)
    cow = _place(game, Cow, x + 10, y)
    game.player.tp_to((-9000 * TSIZE, 0))       # игрока рядом нет
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    for _ in range(60):
        game.update()
        if cow.collisions.get("bottom"):
            break
    cow.move_direction = 1
    assert not cow.can_jump_the_gap(), "на ровном полу прыгать незачем"


def test_no_creature_keeps_its_own_copy_of_chase_logic():
    """Почти одинаковый update() был скопирован у Cow, PassiveWanderer, Wolf
    и SlimeBigBoss — четыре копии расходятся при первой же правке."""
    get_app()
    import inspect
    from units.Objects.Creatures import Cow, PassiveWanderer, Wolf, SlimeBigBoss
    for cls in (Cow, PassiveWanderer, Wolf, SlimeBigBoss):
        assert "update" not in cls.__dict__, f"{cls.__name__} снова завёл свой update"
    src = inspect.getsource(Wolf)
    assert "angry_rect" not in src, "старая коробка агра должна была уйти"


# ===================== оптимизация отрисовки =====================

def test_collisions_and_entities_only_near_the_screen():
    """Раньше в static_tiles попадали ВСЕ непустые тайлы всех загруженных
    чанков: замер давал 3700 записей на поверхности и 6500 в пещерах при 960
    тайлах на экране — несколько тысяч лишних кортежей и вставок в словарь
    каждый кадр."""
    from units.common import TSIZE, COLLIDE_MARGIN
    game = fresh_world(500)
    game.player.tp_to((0, 500 * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    for _ in range(20):
        game.update()
    sm = game.screen_map
    sw, sh = sm.display.get_size()
    visible = (sw // TSIZE + 2) * (sh // TSIZE + 2)
    area = (sw // TSIZE + 2 + COLLIDE_MARGIN * 2) * (sh // TSIZE + 2 + COLLIDE_MARGIN * 2)
    assert sm.static_tiles, "коллизии рядом с игроком нужны"
    assert len(sm.static_tiles) <= area, \
        f"{len(sm.static_tiles)} записей при площади с запасом {area}"
    # и всё, что близко к игроку, в коллизиях есть
    px, py = game.player.rect.centerx // TSIZE, game.player.rect.centery // TSIZE
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            t = game.game_map.get_static_tile_type(px + dx, py + dy, default=0, create_chunk=False)
            if t != 0:
                assert (px + dx, py + dy) in sm.static_tiles, "тайл под игроком обязан быть в коллизиях"
    assert visible <= area


def test_hidden_backtiles_are_not_drawn():
    """44% блитов кадра уходило на задние панельки, полностью скрытые
    передним тайлом: замер показал, что скрыто было 100% отрисованных."""
    get_app()
    from units.Tiles import OPAQUE_TILES, TILE_WITH_LOCAL_POS
    import inspect
    from units.Map.ScreenMap import ScreenMap
    src = inspect.getsource(ScreenMap.update)
    assert "tile_type not in opaque" in src, "проверка сплошного тайла должна быть в цикле"
    # набор считается по пикселям, а не угадывается списком id
    for solid in (1, 2, 3, 4, 5, 31):
        assert solid in OPAQUE_TILES, f"тайл {solid} сплошной, панелька под ним не видна"
    for transparent in (104, 251, 102):
        assert transparent not in OPAQUE_TILES, f"тайл {transparent} прозрачный"
    # тайлы со смещением спрайта клетку не закрывают по определению
    assert not (OPAQUE_TILES & TILE_WITH_LOCAL_POS)


def test_tile_state_is_read_before_update_tile():
    """update_tile может переписать сам тайл (саженец за этот же вызов
    вырастает в дерево), поэтому поля тайла надо прочитать до него — иначе
    решения об отрисовке относятся уже к другому тайлу."""
    get_app()
    import inspect
    from units.Map.ScreenMap import ScreenMap
    src = inspect.getsource(ScreenMap.update)
    assert src.index("state = chunk_static[index + 3]") < src.index("img = update_tile("), \
        "состояние тайла должно читаться раньше update_tile"


def _frame_hash(game, strips):
    """Хеш нарисованного слоя тайлов при заданном наборе склеиваемых тайлов."""
    import hashlib
    import pygame
    import units.Map.ScreenMap as SM
    SM.STRIP_TILES = strips
    game.display.fill((0, 0, 0))
    game.screen_map.update(game.tact, 16)
    return hashlib.md5(pygame.image.tostring(game.display, "RGB")).hexdigest()


def test_tile_strips_draw_exactly_the_same_pixels():
    """Склейка одинаковых тайлов в полосу — оптимизация, а не изменение
    картинки: пиксели обязаны совпасть до последнего.

    Стенд приходится замораживать целиком. Сам проход по тайлам меняет мир
    (саженцы растут), двигает облака и существ — без заморозки два
    одинаковых кадра уже различаются, и сравнение ничего не значит. Именно
    на этом сравнение сначала «нашло» расхождения, которых не было.
    """
    from units.common import TSIZE, START_HELL_Y, START_SPACE_Y
    from units import config
    from units.Map.ScreenMap import ScreenMap
    from units.Tiles import STRIP_TILES
    import units.Map.ScreenMap as SM

    real = (ScreenMap.update_dynamic, ScreenMap.update_particles, ScreenMap.update_tile)
    clouds, stars = config.GameSettings.clouds, config.GameSettings.stars
    ScreenMap.update_dynamic = lambda self: None
    ScreenMap.update_particles = lambda self: None
    ScreenMap.update_tile = lambda self, *a, **k: None
    config.GameSettings.clouds = False
    config.GameSettings.stars = False
    try:
        for y in (0, 30, 500, 900, START_HELL_Y + 120, START_SPACE_Y - 200):
            game = fresh_world(910)
            game.player.tp_to((0, y * TSIZE))
            game.screen_map.teleport_to_player()
            game.elapsed_time = 16
            for _ in range(30):
                game.update()
            game.tact = 1000
            assert _frame_hash(game, frozenset()) == _frame_hash(game, frozenset()), \
                f"y={y}: стенд нестабилен, сравнивать нечем"
            assert _frame_hash(game, frozenset()) == _frame_hash(game, STRIP_TILES), \
                f"y={y}: полосы изменили картинку"
    finally:
        ScreenMap.update_dynamic, ScreenMap.update_particles, ScreenMap.update_tile = real
        config.GameSettings.clouds, config.GameSettings.stars = clouds, stars
        SM.STRIP_TILES = STRIP_TILES


def test_strip_tiles_exclude_everything_that_would_break():
    """Список склеиваемых тайлов выводится из свойств, а не пишется руками:
    два условия из него нашлись только сравнением кадров по пикселям."""
    get_app()
    from units.Tiles import (STRIP_TILES, OPAQUE_TILES, ANIMATED_TILES, NEEDS_TICK,
                             TILE_WITH_LOCAL_POS, tile_many_imgs, tile_imgs, TILE_SIZE)
    assert STRIP_TILES <= OPAQUE_TILES
    assert not (STRIP_TILES & set(ANIMATED_TILES)), \
        "у анимированного тайла кадр в полосе застыл бы навсегда"
    assert not (STRIP_TILES & NEEDS_TICK), "тайл со своей логикой нельзя склеивать"
    assert not (STRIP_TILES & TILE_WITH_LOCAL_POS)
    assert not (STRIP_TILES & set(tile_many_imgs)), "у тайла с кадрами полоса неоднозначна"
    assert 1 not in STRIP_TILES, "дёрн рисуется биомными вариантами"
    for idx in STRIP_TILES:
        assert tile_imgs[idx].get_size() == (TILE_SIZE, TILE_SIZE), \
            f"тайл {idx}: спрайт крупнее клетки заходил бы на соседей"
    assert 3 in STRIP_TILES, "камень — главный случай, ради которого всё и делалось"


def test_tile_strip_is_cached_and_correct_width():
    """Полоса создаётся один раз на (тип, длину) и имеет ровно эту ширину."""
    get_app()
    from units.Tiles import tile_strip, TILE_SIZE, STRIP_LENGTHS
    for length in STRIP_LENGTHS:
        strip = tile_strip(3, length)
        assert strip.get_size() == (TILE_SIZE * length, TILE_SIZE)
        assert tile_strip(3, length) is strip, "полоса должна кэшироваться"


# ===================== обслуживание тайлов за экраном =====================
#
# Три измеренные проблемы прежней схемы (полный проход по площади раз в 30
# кадров):
#   1) 16384 просмотренных слота на 30 активных тайлов — 99.8% работы впустую;
#   2) залп в один кадр: на 10 прогрузчиках 21.6 мс, то есть целый кадр стоя;
#   3) блоки сверялись с ГЛОБАЛЬНЫМ тактом, поэтому выработка фермы за экраном
#      зависела от НОК периода блока и периода тика — при периоде 31 вместо 30
#      воронка складывала в сундук втрое меньше.

def _offscreen_farm(seed, budget=None):
    """Воронка + сундук + прогрузчик далеко от игрока. Возвращает всё нужное."""
    from units.common import TSIZE
    from units.Objects.Items import ItemsTile
    game = fresh_world(seed)
    gm = game.game_map
    if budget is not None:
        gm.OFFSCREEN_CHUNK_BUDGET = budget
    px, y = 300, 8
    for d in range(-6, 10):                     # площадка, не зависящая от сида
        gm.set_static_tile(px + d, y + 1, 3)
        for dy in range(0, 8):
            gm.set_static_tile(px + d, y - dy, 0)
    gm.set_static_tile(px, y, 224)              # воронка
    hopper = gm.get_tile_obj(*gm.to_chunk_xy(px, y), gm.get_static_tile(px, y)[3])
    gm.set_static_tile(px, y + 1, 129)          # сундук под ней
    chest = gm.get_tile_obj(*gm.to_chunk_xy(px, y + 1), gm.get_static_tile(px, y + 1)[3])
    gm.set_static_tile(px + 2, y, 219)          # прогрузчик
    loader = gm.get_tile_obj(*gm.to_chunk_xy(px + 2, y), gm.get_static_tile(px + 2, y)[3])
    loader.inventory.put_to_inventory(ItemsTile(game, 408, count=99))
    gm.add_item_of_index(11, 8, px, y)
    game.player.tp_to((0, 8 * TSIZE))           # игрок далеко: чанк не виден
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    return game, gm, hopper, chest, loader, (px, y)


def _spin_offscreen(game, gm, loader, frames):
    for _ in range(frames):
        loader.activated_tact = game.tact
        loader.update(16)
        gm.tick_offscreen(game.tact, game.screen_map.visible_chunks)
        game.tact += 1


def test_offscreen_farm_delivers_to_chest():
    """Ферма за экраном должна работать — ради этого прогрузчик и существует."""
    from units.common import FPS
    game, gm, hopper, chest, loader, _ = _offscreen_farm(650)
    _spin_offscreen(game, gm, loader, FPS * 6)
    assert sum(c.count for c in chest.inventory if c) > 0, "воронка за экраном не доносит до сундука"


def test_offscreen_throughput_does_not_depend_on_schedule():
    """Выработка не должна зависеть от того, как часто мы успеваем обслужить
    чанк. Раньше зависела: блок сверялся с глобальным тактом, и при периоде
    тика 31 вместо 30 воронка складывала втрое меньше."""
    from units.common import FPS
    results = {}
    for budget in (1, 48):
        game, gm, hopper, chest, loader, _ = _offscreen_farm(650, budget=budget)
        _spin_offscreen(game, gm, loader, FPS * 6)
        results[budget] = sum(c.count for c in chest.inventory if c)
    slow, fast = results[1], results[48]
    assert slow > 0 and fast > 0, f"ферма должна работать при любом бюджете: {results}"
    assert abs(slow - fast) <= max(2, fast // 2), \
        f"выработка не должна зависеть от расписания: {results}"


def test_tile_steps_contract_matches_many_small_ticks():
    """Один вызов со steps=N обязан дать то же, что N вызовов со steps=1 —
    на этом стоит весь тик за экраном."""
    from units.common import FPS
    from units.Objects.TileClasses import TimerBlock
    game = fresh_world(651)
    gm = game.game_map
    a = _place_block(gm, 20, 6, 211)
    b = _place_block(gm, 60, 6, 211)
    assert isinstance(a, TimerBlock) and isinstance(b, TimerBlock)
    for _ in range(40):
        a.tick(1)
    b.tick(40)
    assert a.timer == b.timer, f"steps не эквивалентны: {a.timer} против {b.timer}"


def test_active_tile_registry_is_tiny_and_stays_in_sync():
    """Индекс живых тайлов — вместо просмотра всей площади чанка. Раньше это
    было 16384 просмотренных слота на 30 активных."""
    game = fresh_world(652)
    gm = game.game_map
    cxy = gm.to_chunk_xy(400, 8)
    gm.chunk(cxy, create_chunk=True)
    active = gm.chunk_active_tiles(cxy)
    assert active is not None
    base = len(active)
    slots = gm.chunk_arr_size // gm.tile_data_size
    assert base < slots // 10, f"живых тайлов {base} из {slots} — индекс не имеет смысла"

    # поставили механизм — он появился в индексе
    tx, ty = cxy[0] * 32 + 5, cxy[1] * 32 + 5
    gm.set_static_tile(tx, ty, 224)
    i = gm.convert_pos_to_i(tx, ty)
    assert i in gm.chunk_active_tiles(cxy), "новый механизм должен попасть в индекс"
    # сломали — исчез
    gm.set_static_tile(tx, ty, 0)
    assert i not in gm.chunk_active_tiles(cxy), "сломанный блок должен уйти из индекса"
    # обычный камень в индекс не попадает
    gm.set_static_tile(tx, ty, 3)
    assert i not in gm.chunk_active_tiles(cxy)


def test_offscreen_tick_respects_frame_budget():
    """Работа за экраном режется бюджетом: раньше всё делалось залпом раз в
    30 кадров, и на 10 прогрузчиках залп занимал 21.6 мс."""
    from units.common import FPS
    from units.Objects.Items import ItemsTile
    game = fresh_world(653)
    gm = game.game_map
    gm.OFFSCREEN_CHUNK_BUDGET = 5
    game.player.tp_to((0, 8 * 32))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    loaders = []
    for i in range(3):
        tx = 400 + i * 300
        gm.set_static_tile(tx, 8, 219)
        o = gm.get_tile_obj(*gm.to_chunk_xy(tx, 8), gm.get_static_tile(tx, 8)[3])
        o.inventory.put_to_inventory(ItemsTile(game, 408, count=99))
        o.activated_tact = game.tact
        o.update(16)
        loaders.append(o)
    for cxy in gm.forced_chunk_coords():
        gm.chunk(cxy, create_chunk=True)

    served = []
    real = gm._tick_chunk_offscreen
    def counting(cxy, tact, steps, elapsed):
        served[-1] += 1
        return real(cxy, tact, steps, elapsed)
    gm._tick_chunk_offscreen = counting
    try:
        for _ in range(50):
            served.append(0)
            for o in loaders:
                o.activated_tact = game.tact
            gm.tick_offscreen(game.tact, ())
            game.tact += 1
    finally:
        # Именно del, а не присваивание обратно: присваивание оставило бы в
        # gm.__dict__ атрибут с замыканием на game, а game держит
        # pygame.time.Clock — get_vars() потом падает при pickle сохранения.
        del gm._tick_chunk_offscreen
    assert max(served) <= gm.OFFSCREEN_CHUNK_BUDGET, \
        f"за кадр обслужено {max(served)} чанков при бюджете {gm.OFFSCREEN_CHUNK_BUDGET}"
    assert sum(served) > 0, "круг должен идти"


def test_offscreen_tick_never_generates_chunks():
    """За экраном игра не должна создавать новый мир: генерация чанка это
    ~7 мс прямо в кадре. Замер до правила: худший кадр тика 17.75 мс, из них
    14 мс на две генерации, которые вызвал рост деревьев."""
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(654)
    # саженцы у самой границы чанка — самый вероятный источник генерации
    for d in (30, 31, 32, 33):
        gm.set_static_tile(px + d, y + 1, 1)
        gm.set_static_tile(px + d, y, 102)
    # и падающие предметы: их переезд в соседний чанк шёл мимо запрета, потому
    # что move_dinamic_obj звал generate_chunk напрямую
    for d in (30, 31, 32, 33):
        gm.add_item_of_index(3, 1, px + d, y - 4)
    gens = []
    real = gm.generate_chunk
    def counting(x, cy, *a, **k):
        if gm._offscreen_now:
            gens.append((x, cy))
        return real(x, cy, *a, **k)
    gm.generate_chunk = counting
    try:
        _spin_offscreen(game, gm, loader, FPS * 8)
    finally:
        del gm.generate_chunk  # см. комментарий выше: иначе не пикнется
    assert not gens, f"тик за экраном сгенерировал чанки: {gens[:5]}"


def _item_at(gm, tx, ty, index=3, count=1):
    """Положить предмет в мир и вернуть его объект."""
    gm.add_item_of_index(index, count, tx, ty)
    return gm.chunk(gm.to_chunk_xy(tx, ty))[1][-1]


def test_offscreen_item_falls():
    """Предмет за экраном должен падать.

    Физика сущностей шла только по видимым чанкам, поэтому за экраном
    предмет висел в воздухе: конвейер его толкал, а в воронку он не попадал
    никогда — ферма молча стояла, хотя блоки исправно тикали.
    """
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(660)
    item = _item_at(gm, px + 5, y - 5)
    start = item.rect.y
    _spin_offscreen(game, gm, loader, FPS * 6)
    assert item.rect.y > start, "предмет за экраном не падает"


def test_offscreen_item_lands_on_the_floor():
    """И не проваливается сквозь пол: за экраном коллизии считаются по той же
    физике, просто окружение собирается локально (GameMap.tiles_around)."""
    from units.common import FPS, TSIZE
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(661)
    item = _item_at(gm, px + 5, y - 5)
    _spin_offscreen(game, gm, loader, FPS * 10)
    assert item.alive, "предмет потерялся"
    assert item.rect.bottom <= (y + 1) * TSIZE, \
        f"предмет провалился сквозь пол: bottom={item.rect.bottom}, пол={(y + 1) * TSIZE}"
    assert item.rect.bottom >= y * TSIZE, "предмет не долетел до пола"


def test_offscreen_item_reaches_the_hopper():
    """Смысл всей затеи: предмет, упавший за экраном, доходит до логистики."""
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(662)
    _item_at(gm, px, y - 5, index=3, count=4)
    _spin_offscreen(game, gm, loader, FPS * 8)
    got = sum(c.count for c in chest.inventory if c and c.index == 3)
    assert got > 0, "упавший за экраном предмет не дошёл до сундука"


def test_offscreen_item_reregisters_when_it_crosses_chunk_border():
    """Конвейер меняет rect напрямую, а перерегистрацию в новый чанк делает
    физика. Пока физика за экраном не шла, уехавший предмет оставался записан
    в старом чанке: воронка нового его не видела, и он выпадал из логистики
    насовсем."""
    from units.common import FPS, TSIZE, CHUNK_SIZE
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(663)
    border = (px // CHUNK_SIZE + 1) * CHUNK_SIZE      # первый тайл нового чанка
    old_cxy = gm.to_chunk_xy(border - 1, y)
    new_cxy = gm.to_chunk_xy(border, y)
    assert old_cxy != new_cxy
    # пол под предметом на обеих сторонах границы, чтобы он не улетел вниз
    for tx in (border - 1, border):
        gm.set_static_tile(tx, y + 1, 3)
        gm.set_static_tile(tx, y, 0)
    item = _item_at(gm, border - 1, y)
    assert item in gm.chunk(old_cxy)[1]
    item.rect.x = border * TSIZE + 2                  # так его толкает конвейер
    _spin_offscreen(game, gm, loader, FPS)
    assert item in gm.chunk(new_cxy)[1], "предмет не перерегистрировался в новый чанк"
    assert item not in gm.chunk(old_cxy)[1], "предмет остался записан в старом чанке"


def test_offscreen_creatures_stay_still():
    """Осознанная граница охвата: за экраном двигаются предметы, но не
    существа. Шаг существа — это зрение, память и поиск пути, то есть совсем
    другая цена, и оживлять мобов вне кадра значило бы, что моб приходит к
    игроку из ниоткуда."""
    from units.common import FPS
    from units.Objects.Creatures import Cow
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(664)
    cow = Cow(game, ((px + 5) * 32, (y - 3) * 32))
    gm.add_dinamic_obj(*gm.to_chunk_xy(px + 5, y - 3), cow)
    pos = cow.rect.topleft
    _spin_offscreen(game, gm, loader, FPS * 4)
    assert cow.rect.topleft == pos, f"существо за экраном сдвинулось: {pos} -> {cow.rect.topleft}"


def test_offscreen_entity_substeps_are_capped():
    """Догон после долгой паузы — не телепорт. Растянуть elapsed_time нельзя:
    move() смещает rect целиком и проверяет только его вершины, так что
    большой шаг проходит сквозь пол. Поэтому подшаги честные, кадровые, но их
    число за круг ограничено."""
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(665)
    item = _item_at(gm, px + 5, y - 5)
    chunk = gm.chunk(gm.to_chunk_xy(px + 5, y - 5))
    calls = []
    real = item.update

    def counting(tact, elapsed_time):
        calls.append(elapsed_time)
        return real(tact, elapsed_time)

    item.update = counting
    # бюджет кадра обычно ставит tick_offscreen; здесь дёргаем чанк напрямую
    gm._offscreen_entity_left = gm.OFFSCREEN_ENTITY_BUDGET
    try:
        gm._tick_entities_offscreen(chunk, game.tact, 1000)
    finally:
        del item.update
    assert len(calls) == gm.OFFSCREEN_ENTITY_SUBSTEPS, \
        f"подшагов {len(calls)} при пределе {gm.OFFSCREEN_ENTITY_SUBSTEPS}"
    assert all(abs(e - 1000 / FPS) < 0.01 for e in calls), \
        f"подшаг должен быть кадровым, а не растянутым: {calls}"


def test_offscreen_move_between_chunks_does_not_generate():
    """Переезд предмета в другой чанк шёл мимо запрета на генерацию: он звал
    generate_chunk напрямую. Замер: ОДИН падающий за экраном предмет,
    пересёкший границу чанка, давал кадр 5.7 мс на двух генерациях."""
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(669)
    old_cxy = gm.to_chunk_xy(px + 5, y - 5)
    far = (old_cxy[0] + 200, 0)                 # заведомо не загруженный чанк
    assert gm.game_map.get(far) is None
    item = _item_at(gm, px + 5, y - 5)
    before = len(gm.game_map)
    gm._offscreen_now = True
    try:
        moved = gm.move_dinamic_obj(*item.chunk_pos, far[0], far[1], item)
    finally:
        gm._offscreen_now = False
    assert moved is False, "переезд без чанка не должен считаться удавшимся"
    assert len(gm.game_map) == before, "переезд предмета сгенерировал чанк"
    assert item in gm.chunk(old_cxy)[1], \
        "не переехавший предмет обязан остаться в старом чанке, иначе он потерян"


def test_failed_chunk_move_keeps_chunk_pos():
    """Если переезд не состоялся, объект НЕ должен считать себя в новом чанке:
    иначе он числится там, где его нет, и переезд не повторится никогда —
    предмет выпадает из логистики молча."""
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(670)
    item = _item_at(gm, px + 5, y - 5)
    was = item.chunk_pos
    real = gm.move_dinamic_obj
    gm.move_dinamic_obj = lambda *a: False      # как будто чанка нет
    try:
        item.rect.y += 32 * 40                  # уехал далеко вниз
        item.update_physics(16)
    finally:
        del gm.move_dinamic_obj
    assert item.chunk_pos == was, \
        f"chunk_pos сдвинулся при неудавшемся переезде: {was} -> {item.chunk_pos}"
    assert real is not None
    # а когда переезд удаётся — chunk_pos обязан обновиться
    item.update_physics(16)
    assert item.chunk_pos != was, "после удачного переезда chunk_pos должен обновиться"


def test_offscreen_entity_budget_bounds_the_frame():
    """Куча лежащих предметов не должна стоить кадра. Без бюджета замер давал
    худший кадр 9.57 мс на 150 предметах — цена снова росла с размером фермы,
    ровно тот дефект, который бюджет чанков уже убрал у тайлов."""
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(667)
    for i in range(120):
        gm.add_item_of_index(3, 1, px - 6 + (i % 14), y - 3 - (i // 14) % 4)
    served = []
    real = gm._tick_entities_offscreen

    def counting(chunk, tact, steps):
        n = real(chunk, tact, steps)
        served[-1] += n
        return n

    gm._tick_entities_offscreen = counting
    try:
        for _ in range(60):
            served.append(0)
            loader.activated_tact = game.tact
            loader.update(16)
            gm.tick_offscreen(game.tact, game.screen_map.visible_chunks)
            game.tact += 1
    finally:
        del gm._tick_entities_offscreen   # иначе замыкание на game не пикнется
    assert max(served) <= gm.OFFSCREEN_ENTITY_BUDGET, \
        f"за кадр продвинуто {max(served)} предметов при бюджете {gm.OFFSCREEN_ENTITY_BUDGET}"
    assert sum(served) > 0, "предметы должны обслуживаться"


def test_offscreen_budget_does_not_double_tick_tiles():
    """Чанк, доигрываемый на следующем кадре из-за бюджета на предметы, не
    должен отработать свои тайлы дважды: это была бы двойная выработка."""
    from units.common import FPS
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(668)
    for i in range(60):                         # заведомо больше бюджета
        gm.add_item_of_index(3, 1, px - 6 + (i % 14), y - 3 - (i // 14) % 4)
    ticks = {}
    real = gm._tick_chunk_offscreen
    seen_rounds = []

    def counting(cxy, tact, steps, elapsed):
        before = cxy in gm._offscreen_tiles_done
        res = real(cxy, tact, steps, elapsed)
        if not before:
            ticks[cxy] = ticks.get(cxy, 0) + 1
        seen_rounds.append(cxy)
        return res

    gm._tick_chunk_offscreen = counting
    try:
        # ровно один круг: пока _offscreen_pos не обнулился заново
        for _ in range(FPS):
            loader.activated_tact = game.tact
            loader.update(16)
            gm.tick_offscreen(game.tact, game.screen_map.visible_chunks)
            game.tact += 1
            if gm._offscreen_pos >= len(gm._offscreen_ring):
                break
    finally:
        del gm._tick_chunk_offscreen
    assert seen_rounds, "круг вообще не пошёл"
    assert max(ticks.values()) == 1, \
        f"тайлы чанка отработали такт дважды за круг: {ticks}"


def test_tiles_around_is_local_and_does_not_generate():
    """Локальная карта коллизий должна быть маленькой (десяток тайлов вместо
    экранных двух тысяч) и не создавать мир под собой."""
    import pygame
    game, gm, hopper, chest, loader, (px, y) = _offscreen_farm(666)
    item = _item_at(gm, px + 5, y - 5)
    tiles = gm.tiles_around(item.rect)
    assert len(tiles) <= 30, f"окрестность на {len(tiles)} тайлов — это уже не локально"
    # далеко в неизведанном: чанка нет и появиться он не должен
    far = pygame.Rect(9000 * 32, 8 * 32, 8, 8)
    before = len(gm.game_map)
    assert gm.tiles_around(far) == {}, "в несозданном чанке взялись тайлы"
    assert len(gm.game_map) == before, "tiles_around создала чанк"
