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
    # шаг 10: зелье; финальный шаг закрывается сам
    inv.put_to_inventory(ItemsTile(game, 351, count=1))
    tut.update()
    tut.update()
    assert gm.tutorial_step == -1, "обучение должно завершиться"
    for ach in ("tutorial_craft", "tutorial_builder", "tutorial_workbench",
                "tutorial_supplies", "tutorial_furnace", "tutorial_cauldron",
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
    сохранять выбор через config.Window.set_view_tiles_width."""
    from units import config as cfg
    app = get_app()
    ui = app.title_scene.settings_ui
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


def test_elevator_carries_player_up_and_down():
    """Лифт: расстояния до ада и космоса — тысячи блоков по вертикали,
    пешком их не пройти. Спуск медленнее подъёма и ниже порога урона от
    падения, иначе приезд на дно бил бы игрока."""
    from units.common import ELEVATOR_UP_SPEED, ELEVATOR_DOWN_SPEED
    assert ELEVATOR_DOWN_SPEED < 0.75, "спуск не должен наносить урон при приземлении"
    assert ELEVATOR_DOWN_SPEED < ELEVATOR_UP_SPEED

    from units.common import TSIZE
    game = fresh_world(75)
    gm = game.game_map
    x, y = 50, 20
    for dy in range(-6, 7):                 # шахта лифта
        gm.set_static_tile(x, y + dy, 234)
    player = game.player
    player.tp_to((x * TSIZE, y * TSIZE))
    game.screen_map.teleport_to_player()
    game.elapsed_time = 16
    game.update()                           # кадр заполняет static_tiles
    player.tp_to((x * TSIZE, y * TSIZE))

    player.on_down = False
    player.moving(16)
    assert 234 in player.collisions_ttile, "игрок должен стоять в шахте"
    assert player.vertical_momentum == -ELEVATOR_UP_SPEED, "в шахте игрока тянет вверх"
    assert player.jump_count == 0, "лифт не должен съедать прыжки"

    player.on_down = True
    player.moving(16)
    assert player.vertical_momentum == ELEVATOR_DOWN_SPEED, "присед опускает"


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
