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


# ===================== рендер =====================

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


# ===================== конфиг =====================

def test_config_values():
    from units import config as cfg
    from units.common import FPS
    assert isinstance(cfg.GameSettings.max_fps, int)
    assert FPS == cfg.GameSettings.max_fps
    assert cfg.GameSettings.language in cfg.GameSettings.all_languages
