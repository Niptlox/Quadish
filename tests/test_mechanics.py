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


def test_space_chunks_empty():
    gm = fresh_world(5).game_map
    chunk = gm.generate_chunk(0, -100)  # глубокий космос
    types = chunk[0][0::gm.tile_data_size]
    assert all(t == 0 for t in types), "в космосе не должно быть блоков"


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

def test_config_values():
    from units import config as cfg
    from units.common import FPS
    assert isinstance(cfg.GameSettings.max_fps, int)
    assert FPS == cfg.GameSettings.max_fps
    assert cfg.GameSettings.language in cfg.GameSettings.all_languages
