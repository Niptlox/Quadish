import os
import pickle
from typing import Union

from units.noise_compat import snoise2 as noise2

from units.Objects.Creatures import (Slime, Cow, Wolf, SlimeBigBoss, Snake, Imp, Scorpion,
                                     Rabbit, Deer, Fox, Camel, Penguin, Boar, Crab, Bat, StoneGolem, SpaceDrifter,
                                     DustSwarm, VoidSentinel, Bird, Gull, Raven, Hawk,
                                     MOD_CREATURES)
from units.Objects.Entities import PortalMainGate
from units.Objects.Entity import PhysicalObject
from units.Objects.Items import ItemsTile
from units.Objects.TileClasses import tiles_class, ChunkLoader
from units.Tools import TOOLS
from units.Map import WorldStorage
from units.Trees import grow_tree
from units.biomes import biome_of_pos
from units.Map.Structures import Structures_chance, Structures, Structures_all, structure_start
from units.Map.Dungeons import (dungeon_tile_at, chunk_touches_dungeon, dungeon_at,
                                DUNGEON_CELL_W, DUNGEON_CELL_H)
from units.Map.Water import water_pocket_tile_at, chunk_touches_pocket
from units.Map.WaterFlow import WaterFlow
from units.Tiles import *
from units.sound import sound_gate
from units.Updater import parse_version


class GameMap(SavedObject):
    not_save_vars = SavedObject.not_save_vars | {"gate", "particles", "world_id", "world_meta",
                                                 "dynamic_dump", "dump_keep_radius", "signal_receivers",
                                                 "portals", "lake_sites", "dungeon_sites", "pocket_sites",
                                                 "active_tiles", "water_flow", "_water_writing",
                                                 "_crowd_cache", "_crowd_tact",
                                                 "_offscreen_ring", "_offscreen_ring_set",
                                                 "_offscreen_pos", "_offscreen_round_tact",
                                                 "_offscreen_steps", "_forced_cache",
                                                 "_forced_checked_tact", "_offscreen_now",
                                                 "_offscreen_seen", "_offscreen_tiles_done",
                                                 "_offscreen_entity_left"}
    # держим в памяти чанки в этом радиусе (в чанках) вокруг игрока
    DUMP_KEEP_RADIUS = 8

    def __init__(self, game, generate_type, base_generation=None) -> None:
        self.game = game
        self.gen_type = generate_type
        # tile - (tile_id, breaked state, state of image, state(obj_id, etd))
        self.tile_data_size = 4
        self.map_size = [-1, -1]
        self.chunk_arr_width = CHUNK_SIZE * self.tile_data_size
        self.chunk_arr_size = self.tile_data_size * CHUNK_SIZE ** 2
        self.game_map = {}
        self.particles = []
        self.structures = {}
        # build - (build_index, build_id, points)
        self.structures_lst = []
        self.base_generation = base_generation
        self.world_id = None  # id папки мира (data/maps/<world_id>/)
        self.world_meta = None
        self.saved = False
        self.start_space_y = START_SPACE_Y
        self.start_hell_y = START_HELL_Y
        self.creative_mode = CREATIVE_MODE
        self.tutorial_step = -1  # -1 = обучение неактивно; >=0 = номер шага
        self.tutorial_state = {}  # запоминаемые состояния обучения (сохраняются с миром)
        # Сюжетная арка (docs/STORY.md) — тем же приёмом, что и обучение:
        # состояние живёт в мире и сохраняется вместе с ним, поэтому не
        # нужен отдельный код миграции сейвов.
        self.story_stage = 0      # номер акта, 0 = ещё ничего не начато
        self.story_state = {}     # что найдено/сделано по сюжету
        self.read_inscriptions = []  # id прочитанных надписей = журнал
        # Сюжет (units/Story.py): закрытые акты и необратимые отметки.
        # Живут в мире, а не в игроке: это состояние ЭТОГО мира.
        self.story_done = []
        self.story_flags = []
        # Динамическая выгрузка карты: дальние немодифицированные чанки
        # удаляются из памяти и детерминированно регенерируются при возврате.
        # modified_chunks — чанки с правками игрока/структурами, их не трогаем.
        self.modified_chunks = set()
        self.dynamic_dump = config.GameSettings.dynamic_dump
        self.dump_keep_radius = self.DUMP_KEEP_RADIUS
        self.gate = None
        # Индекс Приёмников (222) по их 4-предметной "частоте" — чтобы
        # Передатчик (223) не перебирал весь загруженный мир при каждом
        # срабатывании, см. docs/SIGNAL_NETWORK_CONCEPT.md. Чисто runtime-
        # кэш (в not_save_vars), заполняется самими Receiver при создании/
        # загрузке (см. Receiver._reregister в TileClasses.py).
        self.signal_receivers = {}
        # Тот же индекс, но для Порталов (232): пара ищется по "частоте" —
        # набору предметов внутри. Тоже runtime-кэш: порталы перерегистрируют
        # себя при создании и загрузке (Portal._register в TileClasses.py).
        self.portals = {}
        # Кэш мест под озёра по клеткам решётки. Поиск площадки под озеро —
        # это скан столба на ~1650 тайлов, и без общего кэша он повторялся для
        # КАЖДОГО чанка: замер давал +61% к стоимости генерации чанка. Кэш
        # выводится из сида, поэтому в сейв не идёт.
        self.lake_sites = {}
        self.dungeon_sites = {}
        self.pocket_sites = {}
        # Поток воды: активное множество неуспокоенных клеток. Выводится из
        # состояния мира, поэтому в сейв не идёт — загруженный водоём стоит в
        # равновесии, и будить его незачем.
        self.water_flow = WaterFlow(self)
        self._water_writing = False
        # Кэш населения вокруг игрока (см. creatures_near_player)
        self._crowd_cache = None
        self._crowd_tact = 0
        # Индекс «живых» тайлов по чанкам: {cxy: {индекс_в_массиве}}. Тик за
        # экраном раньше просматривал ВСЮ площадь чанка — замер дал 16384
        # просмотренных слота на 30 активных тайлов (0.18%). Лежит на карте, а
        # не в самом чанке, чтобы не менять формат сохранений; строится лениво
        # и поддерживается в set_static_tile.
        self.active_tiles = {}
        # Круговое обслуживание тайлов за экраном с бюджетом на кадр: раньше
        # вся работа шла залпом раз в 30 кадров, и на 10 прогрузчиках один
        # такой залп занимал 21.6 мс — целый кадр.
        self._offscreen_ring = []
        self._offscreen_ring_set = frozenset()
        self._offscreen_pos = 0
        self._offscreen_round_tact = 0
        self._offscreen_steps = 1
        self._forced_cache = None
        self._forced_checked_tact = 0
        self._offscreen_now = False
        # id предметов, уже обслуженных в текущем круге: предмет может уехать
        # в чанк, который в этом же круге ещё не обслужен
        self._offscreen_seen = set()
        # чанки, тайлы которых уже отработали такт в текущем круге
        self._offscreen_tiles_done = set()
        self._offscreen_entity_left = 0
        # Часы мира: отдельно от game.tact, потому что tact живёт только в
        # текущем запуске, а время суток должно сохраняться вместе с миром —
        # иначе каждая загрузка выбрасывала бы игрока в рассвет.
        self.world_time = 0
        if self.base_generation is None:
            self.new_base_generation()

    def new_base_generation(self):
        self.base_generation = random.randint(-100000, 100000)
        print("base_generation", self.base_generation)

    def set_vars(self, vrs):
        # convert dynamic objs
        for pos, chunk in vrs["game_map"].items():
            for i in range(len(chunk[1])):
                type_obj, vrs_obj = chunk[1][i]
                obj: PhysicalObject = type_obj(self.game)
                obj.set_vars(vrs_obj)
                chunk[1][i] = obj
            for key, val in chunk[2].items():
                type_obj, vrs_obj = chunk[2][key]
                tile_obj = type_obj(self.game, vrs_obj.get("tile_pos", (0, 0)))
                tile_obj.set_vars(vrs_obj)
                chunk[2][key] = tile_obj
        # set vars
        super(GameMap, self).set_vars(vrs)
        # Все загруженные чанки считаем модифицированными: они были сохранены,
        # поэтому их нельзя выгружать и регенерировать (совместимо со старыми
        # сейвами, где modified_chunks ещё не было).
        if not isinstance(getattr(self, "modified_chunks", None), set):
            self.modified_chunks = set()
        self.modified_chunks.update(self.game_map.keys())

    def get_vars(self):
        d = super(GameMap, self).get_vars()
        # === convert dynamic_objs ===
        game_map = {}
        for pos, chunk in d["game_map"].items():
            game_map[pos] = chunk.copy()
            game_map[pos][1] = [(type(obj), obj.get_vars()) for obj in chunk[1]]
            game_map[pos][2] = {key: (type(obj), obj.get_vars()) for key, obj in chunk[2].items()}
        d["game_map"] = game_map
        d.pop("game")
        return d

    def chunk(self, xy, default=None, for_player=False, create_chunk=False):
        res = self.game_map.get(xy, default)
        if res is default and create_chunk and self._offscreen_now:
            # Единое правило: обслуживание за экраном не создаёт мир.
            # Путей, ведущих к записи тайла, много (рост дерева, лесоруб,
            # гнездо голема, выброс предмета), и каждый из них по умолчанию
            # готов сгенерировать чанк — а это ~7 мс прямо в кадре. Замер до
            # правила: худший кадр тика 17.75 мс, из них 14 на две генерации.
            create_chunk = False
        if res is default and create_chunk:
            res = self.generate_chunk(*xy)
        if res and for_player:
            self.update_chunk(res)
        return res

    def spawn_is_visible(self, tile_x, tile_y):
        """Виден ли тайл игроку прямо сейчас (с запасом).

        Существо, возникшее в кадре из ничего, читается как баг, а не как
        «пришло». Запас нужен, потому что появиться у самой кромки экрана
        почти так же заметно: игрок видит рождение боковым зрением.
        """
        player = getattr(self.game, "player", None)
        if player is None:
            return False
        half_w = WSIZE[0] // 2 // TSIZE + self.SPAWN_VIEW_MARGIN
        half_h = WSIZE[1] // 2 // TSIZE + self.SPAWN_VIEW_MARGIN
        px, py = player.rect.centerx // TSIZE, player.rect.centery // TSIZE
        return abs(tile_x - px) <= half_w and abs(tile_y - py) <= half_h

    # Радиус, в котором горящая лампа не даёт существу родиться. Это единственный
    # способ сделать базу по-настоящему безопасной — и заодно первая причина
    # тянуть провода не «чтобы красиво», а чтобы ночью не съели.
    LAMP_SAFE_RADIUS = 8
    LAMP_TILE = 215

    def lit_by_lamp(self, tile_x, tile_y):
        """Есть ли рядом ГОРЯЩАЯ лампа.

        Проверяем не наличие блока, а поданный на него сигнал: лампа без
        питания — просто стекляшка, и защищать она не должна. Так ночь даёт
        сигнальной сети первое применение, ради которого её строят не из
        любопытства.
        """
        r = self.LAMP_SAFE_RADIUS
        for cxy in {self.to_chunk_xy(tile_x + dx, tile_y + dy)
                    for dx in (-r, 0, r) for dy in (-r, 0, r)}:
            chunk = self.game_map.get(cxy)
            if chunk is None:
                continue
            for obj in chunk[2].values():
                if getattr(obj, "index", None) != self.LAMP_TILE:
                    continue
                if abs(obj.tx - tile_x) <= r and abs(obj.ty - tile_y) <= r and obj.is_active():
                    return True
        return False

    # Сколько существ терпим вокруг игрока и в каком радиусе считаем.
    # Без этого предела остров зарастал: подселение шло раз в пять минут на
    # КАЖДЫЙ чанк, счётчик чанка считал «сколько я породил за всю жизнь», а
    # существа расходятся и идут к игроку — за пять минут на экране собиралось
    # два десятка.
    CREATURE_SOFT_CAP = 20
    CREATURE_CAP_RADIUS = 3
    CROWD_RECHECK = FPS * 2

    def creatures_near_player(self, tact=None):
        """Сколько существ живёт вокруг игрока. С кэшем на пару секунд.

        Обход соседних чанков стоит заметно, а вызывается это при обслуживании
        каждого чанка — без кэша проверка населения была бы дороже самого
        подселения.
        """
        if tact is not None and self._crowd_cache is not None \
                and tact - self._crowd_tact < self.CROWD_RECHECK:
            return self._crowd_cache
        player = getattr(self.game, "player", None)
        if player is None:
            return 0
        pcx, pcy = self.to_chunk_xy(player.rect.centerx // TSIZE, player.rect.centery // TSIZE)
        r = self.CREATURE_CAP_RADIUS
        total = 0
        for cx in range(pcx - r, pcx + r + 1):
            for cy in range(pcy - r, pcy + r + 1):
                chunk = self.game_map.get((cx, cy))
                if chunk is None:
                    continue
                total += sum(1 for o in chunk[1]
                             if o.class_obj & OBJ_CREATURE and o.alive)
        if tact is not None:
            self._crowd_cache, self._crowd_tact = total, tact
        return total

    def update_chunk(self, chunk):
        if not config.GameSettings.creatures:
            return
        crt_cash = chunk[3]
        tact = self.game.tact
        if tact <= crt_cash[2] + FPS * 300:
            return
        crt_cash[2] = tact
        # Предел на окрестность игрока. Главная защита от «двадцати существ на
        # экране»: подселение просто не происходит, пока вокруг и так тесно.
        if self.creatures_near_player(tact) >= self.CREATURE_SOFT_CAP:
            return
        # Считаем ЖИВЫХ в чанке, а не то, сколько он породил за свою жизнь.
        # Счётчик никогда не уменьшался (существа умирают и уходят в соседние
        # чанки), поэтому он ограничивал не плотность, а историю.
        dynamic_tiles = chunk[1]
        alive = sum(1 for o in dynamic_tiles if o.class_obj & OBJ_CREATURE and o.alive)
        crt_cash[1] = alive
        limit = CHUNK_CREATURE_LIMIT
        if is_night(getattr(self, "world_time", 0)):
            # Ночью мир населяется гуще — иначе ночь это просто тёмный экран, а
            # не время, когда лучше не выходить. Множитель идёт на ПРЕДЕЛ, а не
            # на уже посчитанный остаток: раньше он умножал остаток, и ночной
            # чанк мог получить девять существ при пределе четыре.
            limit = int(limit * NIGHT_SPAWN_MULT)
        room = limit - alive
        if room <= 0 or not crt_cash[0]:
            return
        crt_cnt = min(len(crt_cash[0]), random.randint(0, room))
        for tile_xy in random.choices(tuple(crt_cash[0]), k=crt_cnt):
            if self.spawn_is_visible(*tile_xy):
                continue        # не рождаем существо на глазах
            if self.lit_by_lamp(*tile_xy):
                continue        # свет отгоняет — см. lit_by_lamp
            biome = biome_of_pos(tile_xy[0], tile_xy[1])[0]
            Crt = random_creature_selection(tile_xy[1], biome, tile_xy[0])
            if Crt is not None:
                dynamic_tiles.append(spawn_creature(Crt, self.game, *tile_xy))
                crt_cash[1] += 1

    def chunk_gen(self, xy):
        index = 0
        chunk = self.chunk(xy)
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                yield index, y, x, chunk[0][index:index + self.tile_data_size]
                index += self.tile_data_size

    def index_gen(self):
        index = 0
        while index < self.chunk_arr_size:
            yield index
            index += self.tile_data_size

    @staticmethod
    def to_chunk_xy(x, y):
        return x // CHUNK_SIZE, y // CHUNK_SIZE

    @staticmethod
    def to_tile_xy(x, y):
        return x // TSIZE, y // TSIZE

    def get_tile_climate(self, x, y):
        chunk = self.chunk(self.to_chunk_xy(x, y))
        if chunk is None:
            return
        return chunk[4][(y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)]

    def get_tile_and_obj(self, x, y, create_chunk=True):
        tile = self.get_static_tile(x, y, create_chunk=create_chunk)
        if tile:
            # tile[3] — это id объекта тайла (Chest/Furnace/Activator/...)
            # ТОЛЬКО для CLASS_TILE; для остальных тайлов там служебное
            # состояние (dict с таймером у растений, list у шкафа) — не id
            if tile[3] and isinstance(tile[3], int):
                return tile, self.get_tile_obj(*self.to_chunk_xy(x, y), tile[3])
            else:
                return tile, None
        return None

    def get_static_tile(self, x, y, default=None, create_chunk=False):
        chunk = self.chunk(self.to_chunk_xy(x, y), create_chunk=create_chunk)
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i:i + self.tile_data_size]

    def get_static_tile_type(self, x, y, default=None, create_chunk=True):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), create_chunk=create_chunk)
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i]

    def set_static_tile(self, x, y, tile: Union[int, list], create_chunk=True):
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy, create_chunk=create_chunk)
        if chunk is not None:
            if tile is None:
                tile = [0, 0, 0, 0]
            if type(tile) is int:
                tile = self.get_tile_ttile(tile)
            if tile[0] in CLASS_TILE:  # chest
                obj = tiles_class[tile[0]](self.game, (x, y))
                self.add_tile_obj_to_chunk(chunk, obj)
                tile[3] = obj.id
            i = self.convert_pos_to_i(x, y)
            chunk[0][i:i + self.tile_data_size] = tile
            self.modified_chunks.add(cxy)
            self._note_active_tile(cxy, i, tile[0])
            if not self._water_writing:
                # Правка тайла может выпустить воду: прокоп в дне озера, снятый
                # блок рядом с водой, поставленный игроком блок воды. Будим
                # окрестность — сама вода не «знает», что мир изменился.
                # Записи самого потока сюда не попадают: он будит соседей сам, и
                # рекурсия через set_static_tile была бы двойной работой.
                self.water_flow.touch_around(x, y)
            return True
        return False

    def _note_active_tile(self, cxy, index, tile_type):
        """Поддержать индекс живых тайлов при записи тайла."""
        active = self.active_tiles.get(cxy)
        if active is None:
            return            # индекс для этого чанка ещё не строился
        if tile_type in NEEDS_TICK:
            active.add(index)
        else:
            active.discard(index)

    def chunk_active_tiles(self, cxy):
        """Индексы тайлов чанка, которым есть что делать в свой такт.

        Один полный проход по чанку на весь его срок жизни вместо прохода на
        каждый тик: активных тайлов — единицы на тысячу.
        """
        active = self.active_tiles.get(cxy)
        if active is not None:
            return active
        chunk = self.game_map.get(cxy)
        if chunk is None:
            return None
        static = chunk[0]
        active = {i for i in range(0, self.chunk_arr_size, self.tile_data_size)
                  if static[i] in NEEDS_TICK}
        self.active_tiles[cxy] = active
        return active

    def set_static_tile_state_img(self, x, y, state_img):
        """Сменить кадр тайла (например направление конвейера), не трогая
        сам тайл и его объект."""
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy)
        if not chunk:
            return False
        i = self.convert_pos_to_i(x, y)
        chunk[0][i + 2] = state_img
        self.modified_chunks.add(cxy)
        return True

    def set_obj_static_tile(self, x, y, group_id):
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy)
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 3] = group_id
            self.modified_chunks.add(cxy)
            return True
        return False

    def set_static_tile_solidity(self, x, y, sol):
        """Установить прочность тайла"""
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy)
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 1] = sol
            self.modified_chunks.add(cxy)
            return True
        return False

    def set_static_tile_state(self, x, y, state):
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy)
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 2] = state
            self.modified_chunks.add(cxy)
            return True
        return False

    def get_backtile(self, x, y, create_chunk=True):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), create_chunk=create_chunk)
        if not chunk:
            return
        i = (y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)
        return chunk[5][i]

    def set_backtile(self, x, y, backtile_type, create_chunk=True):
        cxy = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        chunk = self.chunk(cxy, create_chunk=create_chunk)
        i = (y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)
        chunk[5][i] = backtile_type
        self.modified_chunks.add(cxy)

    def move_tile_obj(self, chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj):
        chunk = self.chunk((new_chunk_x, new_chunk_y))
        i = obj.id
        if chunk:
            ochunk = self.chunk((chunk_x, chunk_y))
            if ochunk is not None and i in ochunk[2]:
                del ochunk[2][i]
                chunk[2][i] = obj
                return True
            else:
                raise Exception(
                    f"Ошибка передвижения динамики. Объект {i, obj} не находится в чанке {(chunk_x, chunk_y)}")
            # return False
        return

    def del_tile_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        i = obj.id
        if chunk and i in chunk[2]:
            del chunk[2][i]
            return True
        return False

    def add_tile_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            self.add_tile_obj_to_chunk(chunk, obj)
            return True
        return False

    def get_tile_obj(self, chunk_x, chunk_y, obj_id: int):
        # obj_id иногда приходит из tile[3], которое для не-CLASS_TILE тайлов
        # хранит служебное состояние (dict/list), а не id — на всякий случай
        # подстраховываемся здесь тоже (единая точка входа для всех вызовов)
        if not isinstance(obj_id, int):
            return None
        chunk = self.chunk((chunk_x, chunk_y), create_chunk=True)
        if chunk:
            return chunk[2].get(obj_id)
        return None

    def add_tile_obj_to_chunk(self, chunk, obj):
        chunk[2][obj.id] = obj

    def del_dinamic_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            if obj in chunk[1]:
                chunk[1].remove(obj)
                if obj.class_obj & OBJ_CREATURE:
                    chunk[3][1] -= 1
            else:
                print("Error !!! del_dinamic_obj", (chunk_x, chunk_y), obj)
            return True
        return False

    def add_dinamic_obj(self, chunk_x, chunk_y, obj, create_chunk=True):
        chunk = self.chunk((chunk_x, chunk_y), create_chunk=create_chunk)
        if chunk:
            if obj.class_obj & OBJ_CREATURE:
                chunk[3][1] += 1
            chunk[1].append(obj)
            return True
        return False

    def move_dinamic_obj(self, chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj):
        # print(chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj)
        chunk = self.chunk((new_chunk_x, new_chunk_y))
        if not chunk:
            if self._offscreen_now:
                # Тот же запрет, что и в chunk(), но этот путь шёл мимо него —
                # прямой вызов generate_chunk. Замер поймал его не сразу:
                # ОДИН падающий за экраном предмет, пересёкший границу чанка,
                # давал кадр 5.7 мс (две генерации по ~10 мс на два подшага).
                # Предмет остаётся в старом чанке и переедет, когда чанк
                # появится: вернув False, мы просим вызывающего не менять
                # chunk_pos, иначе объект «числился» бы там, где его нет.
                return False
            chunk = self.generate_chunk(new_chunk_x, new_chunk_y)
        ochunk = self.chunk((chunk_x, chunk_y))
        if ochunk is not None and obj in ochunk[1]:
            ochunk[1].remove(obj)
            chunk[1].append(obj)
            if obj.class_obj & OBJ_CREATURE:
                ochunk[3][1] -= 1
                chunk[3][1] += 1
            return True
        else:
            obj.sprite.blit(pg.Surface((10, 10)), (0, 0))
            print(f"Ошибка передвижения динамики. Объект {obj} не находится в чанке {(chunk_x, chunk_y)}")
            # raise Exception(f"Ошибка передвижения динамики. Объект {obj} не находится в чанке {(chunk_x, chunk_y)}")

        return False

    def add_particle(self, particle):
        self.particles.append(particle)

    def del_particle_of_idx(self, idx):
        return self.particles.pop(idx)

    # Как часто обновлять тайлы в чанках под прогрузчиком. Не каждый кадр:
    # там сканируется весь чанк (1024 тайла), а таймеры растений идут
    # десятками секунд — раз в полсекунды более чем достаточно.
    FORCED_TICK_PERIOD = FPS // 2
    # Сколько обновлений тайлов за экраном разрешено за один кадр. Раньше вся
    # работа шла залпом раз в FORCED_TICK_PERIOD кадров, и на 10 прогрузчиках
    # залп занимал 21.6 мс — игрок видел это как рывок.
    OFFSCREEN_CHUNK_BUDGET = 12
    # Предел «сколько тактов зачесть за один круг»: на первом круге и после
    # долгой паузы разница тактов может быть огромной, а мгновенный скачок
    # фермы на минуту вперёд — это не работа, а телепорт.
    OFFSCREEN_MAX_STEPS = FPS * 2
    # Как часто пересчитывать набор чанков под прогрузчиками: пересчёт
    # обходит все загруженные чанки и их тайл-объекты, и каждый кадр это
    # дорого.
    FORCED_RECHECK = FPS // 4
    # Сколько кадров физики разрешено сущности за один круг обслуживания.
    # Физику нельзя ускорить, растянув elapsed_time: move() смещает rect
    # целиком и проверяет только его вершины, так что большой шаг проходит
    # сквозь пол. Поэтому за экраном идут честные кадровые подшаги, но их
    # число ограничено — иначе большая ферма после долгой паузы потратила бы
    # на догон весь кадр.
    OFFSCREEN_ENTITY_SUBSTEPS = 4
    # Сколько предметов разрешено продвинуть за один кадр — тот же приём, что
    # и OFFSCREEN_CHUNK_BUDGET, и по той же причине: замер без бюджета давал
    # худший кадр 9.57 мс на 150 лежащих предметах, то есть цена снова росла с
    # размером фермы. Чанк, в котором предметы не поместились в бюджет,
    # дорабатывается на следующем кадре — круг стоит на месте.
    OFFSCREEN_ENTITY_BUDGET = 24
    # Запас вокруг экрана (в тайлах), внутри которого существо не спавнится:
    # рождение у самой кромки видно почти так же хорошо, как в центре.
    SPAWN_VIEW_MARGIN = 6

    def grow_plant_tile(self, chunk, index, tile, tile_x, tile_y, tact, create_chunk=True):
        """Отработать такт роста растения (куст 101 / саженец 102).

        Раньше эта логика жила только в ScreenMap.update_tile, то есть
        вызывалась ТОЛЬКО для видимых тайлов: стоило отойти — и грядка
        замирала. Вынесено сюда, чтобы тот же код работал и для чанков под
        прогрузчиком (см. tick_forced_chunks); две копии однажды разошлись
        бы, и фермы вели бы себя по-разному на экране и вне его."""
        tile_type = tile[0]
        if tile_type == 101:
            if tile[2] < 3 and tile[3][TILE_TIMER] < tact:
                if tile[3][TILE_TIMER] != 0:
                    chunk[0][index + 2] += 1
                else:
                    chunk[0][index + 3][TILE_TIMER] = tact
                chunk[0][index + 3][TILE_TIMER] += random.randint(FPS * 60, FPS * 120)
        elif tile_type in GROWING_PLANTS:
            # Камыш, огнецвет, лунный цвет: три стадии (росток, полурост,
            # зрелое). Тот же приём, что у куста, — кадр тайла это стадия, а не
            # вариант картинки, поэтому рост виден без отдельной анимации.
            if tile[2] < GROWING_PLANT_STAGES - 1 and tile[3][TILE_TIMER] < tact:
                if tile[3][TILE_TIMER] != 0:
                    chunk[0][index + 2] += 1
                else:
                    chunk[0][index + 3][TILE_TIMER] = tact
                chunk[0][index + 3][TILE_TIMER] += random.randint(FPS * 45, FPS * 90)
        elif tile_type == 102:
            if tile[2] == 0:
                chunk[0][index + 3][TILE_TIMER] = tact + random.randint(FPS * 240, FPS * 660)
                chunk[0][index + 2] = 1
            elif tile[2] == 2:
                grow_tree((tile_x, tile_y), game_map=self, create_chunk=create_chunk)
            elif tile[2] == 1 and tile[3][TILE_TIMER] <= tact:
                if tile[3][TILE_TIMER] != 0:
                    grow_tree((tile_x, tile_y), game_map=self, create_chunk=create_chunk)

    def _chunk_touches_lake(self, base_x, base_y):
        """Может ли в этом чанке быть вода озера."""
        if not (TOP_MIDDLE_WORLD < base_y + CHUNK_SIZE and
                base_y < BOTTOM_MIDDLE_WORLD):
            return False
        base = self.base_generation
        for cell in range(base_x // LAKE_CELL, (base_x + CHUNK_SIZE) // LAKE_CELL + 1):
            # Сначала дешёвая проверка по горизонтали — без поиска уровня.
            shape = lake_shape(cell, base)
            if shape is None:
                continue
            if base_x + CHUNK_SIZE <= shape[0] - shape[1] or shape[0] + shape[1] < base_x:
                continue
            if cell not in self.lake_sites:
                self.lake_sites[cell] = lake_site(cell, base)
            site = self.lake_sites[cell]
            if site is None:
                continue
            center, r, level = site
            top = level - LAKE_RIM_CLEAR
            bottom = level + LAKE_MAX_DEPTH
            if base_y + CHUNK_SIZE > top and base_y <= bottom:
                return True
        return False

    @staticmethod
    def _asteroid_tile(tile_x, tile_y, base):
        """Тип блока астероида в этом тайле космоса или None (вакуум).

        Форму задаёт свой шум с растянутой вертикалью — иначе астероиды
        выходили бы вытянутыми колоннами, как обычный рельеф. Жилы считаются
        отдельными сидами, поэтому они связные, а не рассыпаны по пикселю.
        """
        if noise2(tile_x * 0.035, tile_y * 0.05, 3, persistence=0.45,
                  base=base + 21, lacunarity=1.8) >= ASTEROID_THRESHOLD:
            return None
        if noise2(tile_x * 0.09, tile_y * 0.09, 2, persistence=0.5,
                  base=base + 22, lacunarity=1.6) < ASTEROID_CRYSTAL_THRESHOLD:
            return 28   # звёздный кристалл (рубины)
        if noise2(tile_x * 0.07, tile_y * 0.07, 2, persistence=0.5,
                  base=base + 23, lacunarity=1.6) < ASTEROID_DUST_THRESHOLD:
            return 27   # пылевая жила
        return 26       # астероидный камень

    def forced_chunk_coords(self):
        """Чанки, которые держат включённые прогрузчики."""
        forced = set()
        for (cx, cy), chunk in self.game_map.items():
            for obj in chunk[2].values():
                if isinstance(obj, ChunkLoader) and obj.activating:
                    r = obj.radius
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            forced.add((cx + dx, cy + dy))
        return forced

    def forced_chunk_coords_cached(self, tact):
        """Набор чанков под прогрузчиками, с кэшем на несколько кадров.

        Пересчёт обходит все загруженные чанки и все их тайл-объекты. Раньше
        это делалось раз в 30 кадров и было незаметно; при обслуживании
        каждый кадр — уже нет, поэтому держим кэш.
        """
        if tact - self._forced_checked_tact >= self.FORCED_RECHECK or self._forced_cache is None:
            self._forced_checked_tact = tact
            self._forced_cache = self.forced_chunk_coords()
        return self._forced_cache

    def tick_offscreen(self, tact, visible_chunks=()):
        """Обслужить тайлы за экраном: круг по чанкам с бюджетом на кадр.

        Три вещи, которые здесь исправлены (все три измерены):

        1. **Площадь вместо списка.** Раньше просматривался каждый тайл
           каждого чанка под прогрузчиком: 16384 слота на 30 активных тайлов,
           99.8% работы впустую. Теперь у чанка есть индекс живых тайлов
           (chunk_active_tiles), и он строится один раз за жизнь чанка.
        2. **Залп в один кадр.** Раньше вся работа шла раз в 30 кадров: на 10
           прогрузчиках это 21.6 мс в одном кадре — целый кадр стоя. Теперь за
           кадр обслуживается не больше OFFSCREEN_CHUNK_BUDGET чанков, круг
           идёт дальше на следующем кадре. Бюджет ограничивает и построение
           индексов: их строится столько же, сколько обслуживается чанков.
        3. **Скрытая связь периодов.** Блоки сверялись с ГЛОБАЛЬНЫМ тактом
           (`game.tact % PERIOD`), поэтому выработка фермы за экраном зависела
           от НОК периода блока и периода тика: при периоде 31 вместо 30
           воронка складывала втрое меньше. Теперь блок получает steps —
           сколько тактов прошло с его прошлого обслуживания.

        Следствие схемы: маленькая ферма (чанков меньше бюджета) обслуживается
        каждый кадр со steps=1, то есть работает буквально как на экране;
        большая — реже, но с большим steps, и суммарная выработка та же. Цена
        кадра при этом ограничена сверху.
        """
        forced = self.forced_chunk_coords_cached(tact)
        visible = set(visible_chunks)
        target = forced - visible
        if not target:
            self._offscreen_ring = []
            self._offscreen_pos = 0
            return 0

        ring = self._offscreen_ring
        if self._offscreen_pos >= len(ring) or target != self._offscreen_ring_set:
            # Новый круг: сколько тактов он занял — столько и зачтём каждому
            # тайлу. Предел нужен на первом круге и после долгой паузы: скачок
            # фермы на минуту вперёд — это не работа, а телепорт.
            passed = tact - self._offscreen_round_tact
            self._offscreen_steps = max(1, min(passed, self.OFFSCREEN_MAX_STEPS))
            self._offscreen_round_tact = tact
            self._offscreen_ring_set = frozenset(target)
            ring = self._offscreen_ring = sorted(target)
            self._offscreen_pos = 0
            self._offscreen_seen = set()
            self._offscreen_tiles_done = set()

        steps = self._offscreen_steps
        elapsed = steps * (1000 / FPS)
        end = min(len(ring), self._offscreen_pos + self.OFFSCREEN_CHUNK_BUDGET)
        ticked = 0
        self._offscreen_entity_left = self.OFFSCREEN_ENTITY_BUDGET
        self._offscreen_now = True
        try:
            for pos in range(self._offscreen_pos, end):
                ticked += self._tick_chunk_offscreen(ring[pos], tact, steps, elapsed)
                if self._offscreen_entity_left <= 0:
                    # Предметов в чанке больше, чем помещается в кадр:
                    # останавливаем круг на нём же. Повторно двигать уже
                    # обслуженные предметы и тайлы не даст память круга
                    # (_offscreen_seen / _offscreen_tiles_done).
                    end = pos
                    break
        finally:
            self._offscreen_now = False
        self._offscreen_pos = end
        return ticked

    def tiles_around(self, rect, margin=1):
        """Локальная карта коллизий вокруг rect — {(tx, ty): тип}.

        Тот же формат, что строит ScreenMap, но на десяток тайлов вместо
        экрана. Нужна потому, что физика сущности смотрит в
        screen_map.static_tiles, а там лежит только окрестность экрана: за
        экраном предмет падал бы сквозь пол. Строить ради одного предмета
        полную карту экрана — это ~2000 тайлов; здесь их 12.

        Воздух (0) не кладём — так же, как ScreenMap: collision_test всё
        равно трактует отсутствие ключа как «пусто».
        """
        x0, x1 = rect.left // TSIZE - margin, rect.right // TSIZE + margin
        y0, y1 = rect.top // TSIZE - margin, rect.bottom // TSIZE + margin
        tiles = {}
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                # create_chunk=False: обслуживание за экраном не создаёт мир
                ttile = self.get_static_tile_type(tx, ty, 0, create_chunk=False)
                if ttile:
                    tiles[(tx, ty)] = ttile
        return tiles

    def _tick_entities_offscreen(self, chunk, tact, steps):
        """Продвинуть физику лежащих предметов в чанке за экраном.

        Зачем вообще: конвейер за экраном толкает предмет вбок, но упасть в
        сундук предмет не мог — физика сущностей идёт только по видимым
        чанкам, и за экраном предмет висел в воздухе. Хуже: конвейер меняет
        rect напрямую, а перерегистрацию в новый чанк делает как раз физика,
        так что предмет, уехавший за границу чанка, оставался записан не туда.

        Только предметы. Существа за экраном по-прежнему стоят: их шаг — это
        зрение, память и поиск пути, то есть совсем другая цена, и оживлять
        их вне кадра означало бы, что моб придёт к игроку из ниоткуда.
        """
        objs = chunk[1]
        if not objs:
            return 0
        substeps = min(steps, self.OFFSCREEN_ENTITY_SUBSTEPS)
        frame = 1000 / FPS
        seen = self._offscreen_seen
        moved = 0
        # Слияние одинаковых предметов сверяет предмет со ВСЕМ списком чанка.
        # На 150 лежащих предметах это 150 проверок на каждого — квадрат, и
        # замер это подтвердил: худший кадр 9.41 мс, из них 9.39 на слияние.
        # Раскладываем предметы по тайловым корзинам один раз за вызов и даём
        # каждому только соседей. Корзины за круг слегка устаревают — предмет
        # успевает сдвинуться; это стоит пропущенного слияния, которое
        # случится следующим кругом, а не потери предмета.
        grid = {}
        for o in objs:
            if o.class_obj & OBJ_ITEM and o.alive:
                grid.setdefault((o.rect.centerx // TSIZE, o.rect.centery // TSIZE), []).append(o)
        for obj in list(objs):
            if self._offscreen_entity_left <= 0:
                break
            if not (obj.class_obj & OBJ_ITEM) or not obj.alive:
                continue
            # Предмет мог переехать в ещё не обслуженный чанк того же круга:
            # без этой отметки он получил бы двойную скорость, и выработка
            # снова зависела бы от расписания, а не от игры.
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            self._offscreen_entity_left -= 1
            region = None
            near = None
            box = None
            try:
                for _ in range(substeps):
                    r = obj.rect
                    now = (r.left // TSIZE, r.top // TSIZE, r.right // TSIZE, r.bottom // TSIZE)
                    if now != box:
                        # Пересобираем окрестность только когда предмет
                        # действительно перешёл на другие тайлы.
                        box = now
                        region = self.tiles_around(r)
                        gx, gy = r.centerx // TSIZE, r.centery // TSIZE
                        near = [o for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                for o in grid.get((gx + dx, gy + dy), ())]
                    obj._collision_tiles = region
                    obj._collision_dynamic = near
                    obj.update(tact, frame)
                    # По значению update судить нельзя: Items.update возвращает
                    # None при успехе. Признак жизни — alive, как и в
                    # ScreenMap.update_dynamic.
                    if not obj.alive:
                        break
            finally:
                obj.__dict__.pop("_collision_tiles", None)
                obj.__dict__.pop("_collision_dynamic", None)
            if not obj.alive:
                self.del_dinamic_obj(*self.to_chunk_xy(*self.to_tile_xy(*obj.rect.topleft)), obj)
            moved += 1
        return moved

    def _tick_chunk_offscreen(self, cxy, tact, steps, elapsed):
        """Обслужить живые тайлы и лежащие предметы одного чанка."""
        chunk = self.game_map.get(cxy)
        if chunk is None:
            return 0
        ticked = self._tick_entities_offscreen(chunk, tact, steps)
        if cxy in self._offscreen_tiles_done:
            # Чанк доигрывается на следующем кадре из-за бюджета на предметы —
            # тайлы в нём свой такт уже получили, второй был бы двойной
            # выработкой.
            return ticked
        self._offscreen_tiles_done.add(cxy)
        active = self.chunk_active_tiles(cxy)
        if not active:
            return ticked
        static = chunk[0]
        base_x, base_y = cxy[0] * CHUNK_SIZE, cxy[1] * CHUNK_SIZE
        # список, а не сам set: grow_plant_tile может заменить тайл и через
        # set_static_tile изменить индекс во время обхода
        for index in list(active):
            ttile = static[index]
            if ttile not in NEEDS_TICK:
                continue                  # тайл сломали/заменили с прошлого круга
            if ttile in CLASS_UPDATING_TILES:
                obj = self.get_tile_obj(cxy[0], cxy[1], static[index + 3])
                if obj is not None:
                    obj.tick(steps, elapsed)
                    ticked += 1
            else:
                cell = index // self.tile_data_size
                tx = base_x + cell % CHUNK_SIZE
                ty = base_y + cell // CHUNK_SIZE
                # create_chunk=False: за экраном игра не должна создавать
                # новый мир — генерация чанка это ~7 мс прямо в кадре.
                self.grow_plant_tile(chunk, index, static[index:index + self.tile_data_size],
                                     tx, ty, tact, create_chunk=False)
                ticked += 1
        return ticked

    # Совместимость: имя из v0.2.14 осталось у вызывающего кода и тестов.
    def tick_forced_chunks(self, tact, visible_chunks=()):
        return self.tick_offscreen(tact, visible_chunks)

    def mark_inscription_read(self, inscription_id):
        """Запомнить прочитанную надпись (журнал сюжета).

        Список, а не множество: порядок чтения — это порядок, в котором
        игрок узнавал историю, и он пригодится журналу. Возвращает True,
        если надпись прочитана впервые."""
        if not inscription_id:
            return False
        # старые миры сохранены без этого поля — не падаем на них
        if not isinstance(getattr(self, "read_inscriptions", None), list):
            self.read_inscriptions = []
        if inscription_id in self.read_inscriptions:
            return False
        self.read_inscriptions.append(inscription_id)
        return True

    def register_receiver(self, code, receiver):
        self.signal_receivers.setdefault(code, set()).add(receiver)

    def unregister_receiver(self, code, receiver):
        bucket = self.signal_receivers.get(code)
        if bucket:
            bucket.discard(receiver)
            if not bucket:
                del self.signal_receivers[code]

    def register_portal(self, code, portal):
        self.portals.setdefault(code, set()).add(portal)

    def unregister_portal(self, code, portal):
        bucket = self.portals.get(code)
        if bucket:
            bucket.discard(portal)
            if not bucket:
                del self.portals[code]

    def unload_far_chunks(self):
        """Выгрузить из памяти дальние немодифицированные чанки.

        Удаляются только чанки без правок игрока/структур (modified_chunks),
        без динамики (существ/предметов) и тайл-объектов — при возврате они
        регенерируются идентично из сида. Отключается настройкой.

        Активный ChunkLoader (219, включается сигнальной сетью — провод/
        рычаг/таймер/датчик) дополнительно защищает от выгрузки чанки в
        своём радиусе, даже далеко от игрока — держит автоматику (фермы
        триггеров, авто-клокеры) работающей без игрока рядом. Без сигнала
        ChunkLoader ничего не защищает сверх обычных правил (сам его чанк
        всё равно защищён — в нём есть тайл-объект, см. ниже)."""
        if not self.dynamic_dump:
            return 0
        pcx, pcy = self.game.player.chunk_pos
        r = self.dump_keep_radius
        gate_pos = self.gate.chunk_pos if self.gate is not None else None

        force_loaded = set()
        for (cx, cy), chunk in self.game_map.items():
            for tile_obj in chunk[2].values():
                if isinstance(tile_obj, ChunkLoader) and tile_obj.is_active():
                    rad = tile_obj.radius
                    for dx in range(-rad, rad + 1):
                        for dy in range(-rad, rad + 1):
                            force_loaded.add((cx + dx, cy + dy))

        to_del = []
        for (cx, cy), chunk in self.game_map.items():
            if abs(cx - pcx) <= r and abs(cy - pcy) <= r:
                continue
            if (cx, cy) in self.modified_chunks or (cx, cy) == gate_pos:
                continue
            if (cx, cy) in force_loaded:
                continue
            if chunk[1] or chunk[2]:  # есть существа/предметы или тайл-объекты
                continue
            to_del.append((cx, cy))
        for key in to_del:
            del self.game_map[key]
        return len(to_del)

    def add_item_of_index(self, index, count_items, x, y):
        npos = (x * TSIZE + random.randint(0, TSIZE - HAND_SIZE), y * TSIZE)
        if index in TOOLS:
            # Инструмент
            item = TOOLS[index](self.game, pos=npos)
            item.set_owner(self)
        else:
            item = ItemsTile(self.game, index, npos, count_items)
        self.add_dinamic_obj(*self.to_chunk_xy(x, y), item)

    # насколько далеко вниз ищем поверхность от предложенной высоты
    SURFACE_SCAN = 120
    # предел, до которого фундамент достраивается вниз: иначе структура над
    # пропастью выложила бы столб на всю её глубину
    FOUNDATION_MAX_DEPTH = 14

    def surface_y_at(self, tile_x, from_y, scan=None):
        """Найти верхний тайл породы в столбце tile_x, начиная с from_y вниз.

        Возвращает y первого сплошного тайла или None, если на всём отрезке
        порода не встретилась (например, столб пришёлся на пустоту между
        летающими островами).

        Работает БЕЗ генерации чанков: плотность породы — чистая функция от
        (тайл, сид), см. terrain_is_solid. Это важно, потому что позиция
        структуры выбирается до того, как местность вокруг существует."""
        base = self.base_generation
        scan = self.SURFACE_SCAN if scan is None else scan
        for y in range(int(from_y), int(from_y) + scan):
            if terrain_is_solid(tile_x, y, base):
                return y
        return None

    def surface_top_at(self, tile_x, from_y):
        """Верх породы в столбце, даже если from_y уже внутри горы.

        surface_y_at() ищет только ВНИЗ: если начать внутри породы, он
        вернёт ту же точку, и «поверхностью» окажется середина скалы. Здесь
        сначала поднимаемся до воздуха, а потом падаем на первую твердь.
        """
        base = self.base_generation
        y = int(from_y)
        for _ in range(self.SURFACE_SCAN):
            if not terrain_is_solid(tile_x, y, base):
                break
            y -= 1
        else:
            return None
        return self.surface_y_at(tile_x, y)

    def _snap_to_surface(self, pos, size):
        """Опустить структуру на поверхность: её низ должен лечь на землю.

        Землю щупаем по всей ширине постройки и встаём на САМЫЙ ВЫСОКИЙ
        найденный уровень: если встать на самый низкий, столбцы с высокой
        землёй окажутся закопанными, а это уже ничем не исправить. Просвет
        под остальными столбцами добирает фундамент ('=' / '_' в схеме).

        Возвращает None, если место не годится: под постройкой нет земли
        (пустота между летающими островами) или рельеф слишком рваный и
        нижний ряд всё равно попал бы в породу (навесы, скалы)."""
        w, h = size
        base = self.base_generation
        tops = []
        for dx in range(0, w, max(1, w // 6)):
            top = self.surface_y_at(pos[0] + dx, pos[1])
            if top is not None:
                tops.append(top)
        if not tops:
            return None
        ground = min(tops)          # самый высокий уровень земли
        new_y = ground - h          # низ структуры ложится на этот уровень

        # Нижний ряд не должен уходить в породу: на навесах и скалах
        # постройка иначе окажется вмурованной в камень.
        bottom_row = new_y + h - 1
        buried = sum(1 for dx in range(w)
                     if terrain_is_solid(pos[0] + dx, bottom_row, base))
        if buried * 2 > w:
            return None
        return pos[0], new_y

    def _pick_structure(self, structures_area, pos):
        """Выбрать структуру для зоны с учётом биома в этой точке.

        У структуры может быть список биомов (4-й элемент описания). Такие
        участвуют в жеребьёвке только в своём биоме — до этого расстановка
        зависела лишь от зоны по Y, и «структура для тундры» была
        невыразима. Структуры без списка биомов работают как раньше — в
        любом биоме своей зоны."""
        ids, weights = Structures_chance[structures_area]
        zone_structures = Structures[structures_area]
        # биом считаем один раз на попытку, а не на каждую структуру
        biome = None
        allowed_ids, allowed_weights = [], []
        for build_id, weight in zip(ids, weights):
            build = zone_structures[build_id]
            biomes = build[3] if len(build) > 3 else None
            if biomes is not None:
                if biome is None:
                    biome = biome_of_pos(pos[0], pos[1])[0]
                if biome not in biomes:
                    continue
            allowed_ids.append(build_id)
            allowed_weights.append(weight)
        if not allowed_ids:
            return None
        return random.choices(allowed_ids, allowed_weights, k=1)[0]

    def get_structure_dict(self, structure_x, structure_y):
        # print("get structure", structure_x, structure_y)
        structure = self.structures.get((structure_x, structure_y))
        if structure is None:
            structure = {}
            pos_1 = structure_x * STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE, \
                    structure_y * STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE
            pos_2 = (structure_x + 1) * STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE, \
                    (structure_y + 1) * STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE - CHUNK_SIZE
            structure_rect = pg.Rect(pos_1, (STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE, STRUCTURE_CHUNKS_SIZE * CHUNK_SIZE))
            for i in range(CNT_BUILDS_OF_STRUCTURE_BLOCK):
                pos = random.randint(pos_1[0], pos_2[0]), random.randint(pos_1[1], pos_2[1])
                if pos[1] < START_SPACE_Y:
                    structures_area = "space"
                elif pos[1] < START_HELL_Y:
                    structures_area = "middleworld"
                elif pos[1] > START_HELL_Y:
                    structures_area = "hell"

                build_id = self._pick_structure(structures_area, pos)
                if build_id is None:
                    continue
                build = Structures[structures_area][build_id]
                # схема — (size, array[, backtiles[, foundation]]), берём только размер
                size = build[2][0]

                # Структуры с якорем "surface" опускаются на землю: иначе
                # постройка встаёт на случайной высоте внутри блока 100x100
                # чанков и может оказаться в толще камня или висеть в воздухе.
                if len(build) > 4 and build[4] == "surface":
                    snapped = self._snap_to_surface(pos, size)
                    if snapped is None:
                        continue  # под этим столбом земли нет (пустота между островами)
                    pos = snapped

                # left_top, right_top, left_bottom, right_bottom
                # (у левого-нижнего угла раньше по ошибке прибавлялась ширина
                # вместо высоты — у невысоких широких структур из-за этого
                # регистрировался не тот чанк-триггер постройки)
                points = [(pos[0], pos[1]), (pos[0] + size[0], pos[1]),
                          (pos[0], pos[1] + size[1]), (pos[0] + size[0], pos[1] + size[1])]
                # TODO: сделать смещение здания вместо пропуска итерации
                if not all([structure_rect.collidepoint(point) for point in points]):
                    continue
                build_index = len(self.structures_lst)
                # build - (build_index, build_id, points)
                self.structures_lst.append((build_index, build_id, points))
                for j in range(4):
                    tile_x, tile_y = points[j]
                    tile_chunk_pos = tile_x // CSIZE, tile_y // CSIZE
                    structure.setdefault(tile_chunk_pos, {})
                    # pos_point: (build_index(in_lst), build_id, num_of_point, state)
                    structure[tile_chunk_pos][(tile_x, tile_y)] = [build_index, build_id, j, 0]
            self.structures[(structure_x, structure_y)] = structure
        return structure

    def build_structure_of_chunk(self, chunk_x, chunk_y):
        # print("build_structure_of_chunk", chunk_x, chunk_y)
        # (build_id, num_of_point)
        structure_x, structure_y = chunk_x // STRUCTURE_CHUNKS_SIZE, chunk_y // STRUCTURE_CHUNKS_SIZE
        structure = self.get_structure_dict(structure_x, structure_y)
        # chunk os structures (100x100 real chu nks)
        schunk = structure.get((chunk_x, chunk_y))
        if schunk is None:
            return
        # pos_point: (build_index(in_lst), build_id, num_of_point, state)
        for pos_point, info in schunk.items():
            # point
            build_index, build_id, num_of_point, state = info
            if state != 0:
                continue
            # build - (build_index, build_id, points)
            points = self.structures_lst[build_index][2]
            self.set_state_of_points_build(points, 1)  # building
            pos = points[0]
            self.set_structure(pos, Structures_all[build_id][2],
                               self.STRUCTURE_LOOT.get(Structures_all[build_id][0]))
            self.set_state_of_points_build(points, 2)  # builded

    # Какая таблица добычи у какой структуры (units/Loot.py). Ключ — имя из
    # StructuresBiome; чего нет в таблице, наполняется по глубине.
    STRUCTURE_LOOT = {
        "Home": "жильё", "Abandoned tower": "дозор", "Bunker": "бункер",
        "desert marker": "храм", "desert crypt": "храм",
        "savanna watchpost": "дозор", "tundra camp": "жильё",
        "rainforest greenhouse": "оранжерея", "tropical flooded temple": "храм",
        "forest observatory": "дозор", "boreal sawmill": "жильё",
        "deep mine": "забой", "cave shrine": "забой",
    }

    def fill_structure_containers(self, pos, size, array, kind_name=None):
        """Наполнить сундуки и шкафы только что поставленной структуры.

        Раньше структуры ставили контейнеры пустыми: тайл создаётся вместе с
        объектом-инвентарём, а положить в него что-то было некому. Игрок
        находил склеп, открывал сундук и получал ничего — самое
        разочаровывающее, что может сделать находка.
        """
        from units.Loot import fill_container
        for i_y in range(size[1]):
            for i_x in range(size[0]):
                ttile = array[i_y * size[0] + i_x][0]
                if ttile not in (129, 126):          # сундук, шкаф
                    continue
                tx, ty = pos[0] + i_x, pos[1] + i_y
                tile = self.get_static_tile(tx, ty, create_chunk=False)
                if not tile or tile[0] != ttile:
                    continue
                obj = self.get_tile_obj(*self.to_chunk_xy(tx, ty), tile[3])
                inv = getattr(obj, "inventory", None)
                if inv is not None:
                    fill_container(self.game, inv, tx, ty, self.base_generation, kind_name)

    def set_structure(self, pos, build, kind_name=None):
        foundation = ()
        if len(build) == 2:
            backtiles = []
            size, array = build
        elif len(build) == 3:
            size, array, backtiles = build
        else:
            size, array, backtiles, foundation = build
        backtile = 0
        for i_y in range(size[1]):
            for i_x in range(size[0]):
                tile = array[i_y * size[0] + i_x]
                if backtiles:
                    backtile = backtiles[i_y * size[0] + i_x]
                # Если не структурная пустота
                if tile[0] != 150:
                    self.set_backtile(pos[0] + i_x, pos[1] + i_y, backtile, create_chunk=True)
                    self.set_static_tile(pos[0] + i_x, pos[1] + i_y, tile, create_chunk=True)
        if foundation:
            self._build_foundation(pos, foundation)
        self.fill_structure_containers(pos, size, array, kind_name)

    def _build_foundation(self, pos, foundation):
        """Достроить фундамент вниз до земли.

        Рельеф неровный, поэтому структура, посаженная на поверхность, одним
        углом висела бы над склоном. Помеченные в схеме столбы ('=' и '_')
        сами доводятся до породы. Глубина ограничена: над пропастью иначе
        выкладывался бы столб на всю её глубину."""
        base = self.base_generation
        for dx, dy, tile_type in foundation:
            tx = pos[0] + dx
            solidity = TILES_SOLIDITY.get(tile_type, -1)
            for depth in range(1, self.FOUNDATION_MAX_DEPTH + 1):
                ty = pos[1] + dy + depth
                # дошли до породы — дальше достраивать нечего
                if terrain_is_solid(tx, ty, base):
                    break
                self.set_static_tile(tx, ty, [tile_type, solidity, 0, 0], create_chunk=True)

    def set_state_of_points_build(self, points, state):
        for point in points:
            chunk_x, chunk_y = point[0] // CHUNK_SIZE, point[1] // CHUNK_SIZE
            structure_x, structure_y = chunk_x // STRUCTURE_CHUNKS_SIZE, chunk_y // STRUCTURE_CHUNKS_SIZE
            chunk = self.get_structure_dict(structure_x, structure_y).get((chunk_x, chunk_y))
            # pos_point: (build_index(in_lst), build_id, num_of_point, state)
            chunk[point][3] = state

    def convert_pos_to_i(self, x, y):
        # cx, cy = x % CHUNK_SIZE, y % CHUNK_SIZE
        # i = (cy * CHUNK_SIZE + cx) * self.tile_data_size
        return ((y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)) * self.tile_data_size

    @staticmethod
    def get_tile_ttile(ttile):
        """тип, прочность, состояние, переменная(таймер | ссылка на объект и тд)"""
        state = {}
        state_img = 0
        if ttile in PLANT_WITH_RANDOM_SPRITE:
            # -1 тк это количество
            state_img = random.randint(0, PLANT_WITH_RANDOM_SPRITE[ttile]-1)
        if ttile in PLANT_WITH_RANDOM_LOCAL_POS:
            img = tile_imgs[ttile]
            state[TILE_LOCAL_POS] = (random.randint(0, TSIZE - img.get_width()),
                                     TSIZE - img.get_height())
        if ttile in PLANT_WITH_TIMER:
            state[TILE_TIMER] = 0
        elif ttile in ITEM_WITH_STATE_IS_LIST:
            state = []
        if state is {}:
            state = 0
        return [ttile, TILES_SOLIDITY.get(ttile, -1), state_img, state]

    def get_tile_ttile_tpos(self, ttile, tpos):
        """тип, прочность, состояние, переменная"""
        tile = self.get_tile_ttile(ttile)

        return tile

    def create_pass_chunk(self, xy):
        """0:static tiles; 1:dynamic object; 2:tile object; 3:creatures cash \
        (on graund tiles, cnt creatures, last tact generate); 4:climate;
        5:back static tile"""
        #                    0                          1   2   3              4
        self.game_map[xy] = [[0] * self.chunk_arr_size, [], {}, [set(), 0, 0], [0] * (CHUNK_SIZE ** 2),
                             [0] * (CHUNK_SIZE ** 2)]
        return self.game_map[xy]

    def generate_chunk(self, x, y):
        chunk = None
        if self.gen_type == TGENERATE_INFINITE_LANDS:
            chunk = self.generate_chunk_noise_island(x, y)
            self.build_structure_of_chunk(x, y)
        return chunk

    def generate_chunk_noise_island(self, x, y):
        # Детерминированная генерация по (сид, x, y): при выгрузке и повторной
        # генерации чанк выходит идентичным (терраин, растения, существа), что
        # делает динамическую выгрузку карты незаметной.
        _rng_state = random.getstate()
        random.seed((self.base_generation * 1000003) ^ (x * 73856093) ^ (y * 19349663))
        try:
            return self._generate_chunk_noise_island(x, y)
        finally:
            random.setstate(_rng_state)

    def _generate_chunk_noise_island(self, x, y):
        res = self.create_pass_chunk((x, y))
        static_tiles, dynamic_tiles, tile_objs, creature_cash, biome_info, back_tiles = res
        on_ground_tiles, cnt_creatures = creature_cash[0], creature_cash[1]
        tile_index = 0
        backtile_index = 0
        base = self.base_generation
        base_x = x * CHUNK_SIZE
        base_y = y * CHUNK_SIZE
        tile_y = base_y  # global tile y (not px)
        i = 0
        # Кэш результатов по тайлу: одна и та же проверка вызывается для
        # нескольких соседей, а раньше внутри неё noise2 считался 4 раза.
        _noise_cache = {}
        _climate_cache = {}
        _lake_cache = self.lake_sites
        # Пересекает ли этот чанк хоть одно озеро. Проверяем один раз на
        # чанк, а не на каждый из 1024 тайлов: озёра редки, и подавляющее
        # большинство чанков не должно платить за них вообще.
        chunk_has_lake = self._chunk_touches_lake(base_x, base_y)
        # То же самое для подземелий (units/Map/Dungeons.py): дешёвая проверка
        # на чанк вместо раскладки на каждый из 1024 тайлов.
        _dungeon_cache = self.dungeon_sites
        chunk_has_dungeon = chunk_touches_dungeon(base_x, base_y, CHUNK_SIZE,
                                                  base, _dungeon_cache)
        # И для полостей с водой (units/Map/Water.py): их проверка считает
        # пробы породы, и в чанках без полостей платить за них незачем.
        _pocket_cache = self.pocket_sites
        chunk_has_pocket = chunk_touches_pocket(base_x, base_y, CHUNK_SIZE,
                                                base, _pocket_cache)

        def standart_noise2_bool(tx, ty):
            # кэш по тайлу: одна и та же проверка нужна нескольким соседям
            res = _noise_cache.get((tx, ty))
            if res is None:
                res = terrain_is_solid(tx, ty, base)
                _noise_cache[(tx, ty)] = res
            return res


        # print("noise", (noise2(base_x / freq_x, base_y / freq_y) * 20 + base_y) > START_SPACE_Y)
        for y_pos in range(CHUNK_SIZE):  # local tile y in chunk (not px)
            tile_x = base_x  # global tile x (not px)
            for x_pos in range(CHUNK_SIZE):  # local tile x in chunk (not px)
                biome_info[i] = biome_of_pos(tile_x, tile_y, _climate_cache)
                tile_type = None
                # Кадр тайла (state_img). Нужен воде: уровень заполнения — это
                # часть формы водоёма, и решает его тот, кто эту форму считает.
                tile_frame = 0
                backtile_type = None
                if config.GameSettings.vertical_tunel and tile_x in (-2, -1, 0, 1):
                    tile_type = 0
                # if (noise2(tile_x / freq_x, tile_y / freq_y) * 20 + tile_y) > START_SPACE_Y:
                #     tile_type = 2
                # Озеро вырезается поверх рельефа, поэтому считается ДО
                # ветки «порода / пустота»: чаша выедает и породу тоже.
                if chunk_has_lake and tile_type is None and biome_info[i][0] != 9:
                    ltile = lake_tile_at(tile_x, tile_y, base, _lake_cache)
                    if ltile is not None:
                        tile_type, tile_frame = ltile
                # Полость с водой (units/Map/Water.py) вырезается в породе, то
                # есть тоже ДО ветки «порода / пустота». После озера: полость
                # внутри острова, озеро на его поверхности, и если они всё же
                # пересеклись — сверху должно остаться озеро.
                if chunk_has_pocket and tile_type is None:
                    ptile = water_pocket_tile_at(tile_x, tile_y, base, _pocket_cache)
                    if ptile is not None:
                        tile_type, tile_frame = ptile
                # Подземелье кладётся ПОВЕРХ рельефа, озера и полостей: это
                # постройка, она вытесняет и породу, и воду, иначе комнату
                # затопило бы.
                if chunk_has_dungeon:
                    dtile = dungeon_tile_at(tile_x, tile_y, base, _dungeon_cache)
                    if dtile is not None:
                        tile_type, tile_frame = dtile, 0
                if standart_noise2_bool(tile_x, tile_y) and tile_type is None:
                    if standart_noise2_bool(tile_x, tile_y - 2 - random.randint(0, 1)):
                        tile_type = 3  # stone
                        # Пещерные растения (гриб, блоровый мох). Пишем НАД
                        # собой, в уже посчитанный тайл: обход идёт сверху вниз,
                        # поэтому «что под этим воздухом» известно только здесь,
                        # в ветке породы. Тем же приёмом ставится трава на дёрн.
                        if y_pos > 0 and static_tiles[tile_index - self.chunk_arr_width] == 0:
                            cave_plant = cave_plant_selection(tile_y)
                            if cave_plant is not None:
                                pl_i = tile_index - self.chunk_arr_width
                                static_tiles[pl_i] = cave_plant
                                static_tiles[pl_i + 1] = TILES_SOLIDITY.get(cave_plant, -1)
                        if standart_noise2_bool(tile_x, tile_y + 1 + random.randint(0, 1)) and standart_noise2_bool(
                                tile_x + 1, tile_y) and standart_noise2_bool(tile_x - 1, tile_y):
                            backtile_type = 1003  # backstone
                        v4 = noise2(tile_x / 10, tile_y / 10, 2, persistence=0.55, base=base + 1, lacunarity=1)
                        if v4 < -0.8:
                            tile_type = 4  # blore
                        else:
                            v5 = noise2(tile_x / 16 + 100, tile_y / 16 + 100, 2, persistence=0.35, base=base + 2,
                                        lacunarity=1)
                            if v5 < -0.88:
                                tile_type = 5  # granite
                            else:
                                v6 = noise2(tile_x / 10, tile_y / 10, 2, persistence=0.55, base=base + 3, lacunarity=1)
                                if v6 < -0.7:
                                    tile_type = 2  # dirt
                                else:
                                    cof = 0.05
                                    # Порог руды поднимается с глубиной: риск и
                                    # награда идут по ОДНОЙ кривой (см.
                                    # depth_reward и docs/BALANCE_SCHEME.md).
                                    # Раньше пороги были постоянными, и замер
                                    # показывал железо 1 на 98 у поверхности
                                    # против 1 на 60 на глубине 1000 — спуск не
                                    # окупался, хотя мобы там уже вдвое сильнее.
                                    deep = depth_reward(tile_y)
                                    v7 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55, base=base + 4,
                                                lacunarity=1)
                                    if v7 < ORE_BLORE_T + ORE_BLORE_DEEP * deep:
                                        tile_type = 21  # ore blore
                                    else:
                                        v8 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55, base=base + 5,
                                                    lacunarity=1)
                                        if v8 < ORE_COPPER_T + ORE_COPPER_DEEP * deep:
                                            tile_type = 22  # ore copper
                                        else:
                                            v9 = noise2(tile_x * 0.03, tile_y * 0.03, 2, persistence=0.55,
                                                        base=base + 6,
                                                        lacunarity=1)
                                            if v9 < ORE_GOLD_T + ORE_GOLD_DEEP * deep:
                                                tile_type = 23  # ore gold
                                            else:
                                                v10 = noise2(tile_x * 0.08, tile_y * 0.08, 2, persistence=0.55,
                                                             base=base + 7,
                                                             lacunarity=1)
                                                if v10 < ORE_IRON_T + ORE_IRON_DEEP * deep:
                                                    tile_type = 24  # ore iron
                                                else:
                                                    v10 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55,
                                                                 base=base + 8,
                                                                 lacunarity=1)
                                                    if v10 < ORE_SILVER_T + ORE_SILVER_DEEP * deep:
                                                        tile_type = 25  # ore silver

                    else:
                        tile_type = 2  # dirt
                        if (y_pos > 0 and static_tiles[tile_index - self.chunk_arr_width] == 0) or \
                                (y_pos == 0 and self.get_static_tile_type(tile_x, tile_y - 1, create_chunk=True) == 0):
                            tile_type = 1  # ground
                            if biome_info[i][0] == 9:  # HELL
                                tile_type = 2
                            if y_pos > 0:
                                on_ground_tiles.add((tile_x, tile_y))
                                plant_tile_type_state = random_plant_selection(biome_info[i][0])  # plant
                                if plant_tile_type_state is not None:
                                    plant_tile_type, state_img, state = plant_tile_type_state
                                    pl_i = tile_index - self.chunk_arr_width
                                    static_tiles[pl_i] = plant_tile_type
                                    static_tiles[pl_i + 1] = TILES_SOLIDITY.get(plant_tile_type, -1)
                                    static_tiles[pl_i + 2] = state_img
                                    static_tiles[pl_i + 3] = state
                                    if config.GameSettings.creatures and cnt_creatures < CHUNK_CREATURE_LIMIT:
                                        Crt = random_creature_selection(tile_y, biome_info[i][0], tile_x)
                                        if Crt is not None:
                                            dynamic_tiles.append(
                                                spawn_creature(Crt, self.game, tile_x, tile_y))
                                            cnt_creatures += 1
                else:
                    # пусто
                    # Лавовые озёра в аду: заполняют пустоты ниже уровня ада
                    # своим шумом, поэтому получаются связными лужами, а не
                    # рассыпанными пикселями.
                    if tile_y > START_HELL_Y + LAVA_DEPTH_MARGIN:
                        if noise2(tile_x * 0.04, tile_y * 0.09, 2, persistence=0.5,
                                  base=base + 11, lacunarity=1.6) < LAVA_THRESHOLD:
                            tile_type = 140  # лава
                    # Астероиды: единственная твердь в космосе. Без них выше
                    # атмосферы вообще нечего было делать — ни встать, ни
                    # копать, ни спавниться существам.
                    elif tile_y < START_SPACE_Y - ASTEROID_MARGIN:
                        tile_type = self._asteroid_tile(tile_x, tile_y, base)
                        if tile_type is not None and y_pos > 0 and \
                                static_tiles[tile_index - self.chunk_arr_width] == 0:
                            # тайл над астероидом — площадка для спавна;
                            # on_ground_tiles заполняется только в ветке
                            # породы, а космос идёт по ветке пустоты
                            on_ground_tiles.add((tile_x, tile_y - 1))
                    # ставим растение
                    if tile_type is None and y_pos == CHUNK_SIZE - 1 and \
                            self.get_static_tile(tile_x, tile_y + 1, default=0) == 1:
                        on_ground_tiles.add((tile_x, tile_y))
                        tile_type_state = random_plant_selection(biome_info[i][0])
                        if tile_type_state:
                            tile_type = tile_type_state[0]
                            static_tiles[tile_index + 2] = tile_type_state[1]
                if tile_index >= self.chunk_arr_size:
                    break
                if tile_type is not None:
                    static_tiles[tile_index] = tile_type
                    static_tiles[tile_index + 1] = TILES_SOLIDITY.get(tile_type, -1)
                    if tile_frame:
                        static_tiles[tile_index + 2] = tile_frame
                if backtile_type:
                    back_tiles[backtile_index] = backtile_type
                tile_x += 1  # v28557
                tile_index += self.tile_data_size
                backtile_index += 1
                i += 1
            tile_y += 1
        if chunk_has_lake or chunk_has_pocket:
            cnt_creatures = self._spawn_water_creatures(res, x, y, base, cnt_creatures,
                                                        chunk_has_pocket)
        creature_cash[1] = self._spawn_flocks(res, on_ground_tiles, cnt_creatures)
        if chunk_has_dungeon:
            self._place_dungeon_guards(res, x, y, base, _dungeon_cache)
        return res

    def _spawn_water_creatures(self, chunk, chunk_x, chunk_y, base, cnt_creatures,
                               has_pocket):
        """Заселить воду этого чанка (units/Objects/Creatures.py).

        Отдельным проходом, а не общей жеребьёвкой по тайлам: наземный спавн
        привязан к дёрну (`random_creature_selection` зовут из ветки земли), и
        воду он не видит вообще — до этого в водоёмах не было никого.

        Ищем ВНУТРЕННЮЮ воду: тайл, у которого вода и слева, и справа, и сверху.
        Рыба, посаженная в кромку озера толщиной в тайл, всю жизнь билась бы о
        два берега. Проход по массиву чанка платится только там, где вода
        вообще есть (проверка на чанк уже сделана вызывающим).
        """
        if not config.GameSettings.creatures:
            return cnt_creatures
        import units.Objects.Creatures as C
        static = chunk[0]
        tds = self.tile_data_size
        width = CHUNK_SIZE
        spots = []
        for cell in range(CHUNK_SIZE * CHUNK_SIZE):
            i = cell * tds
            if static[i] != WATER_TILE:
                continue
            cx, cy = cell % width, cell // width
            if not (0 < cx < width - 1 and 0 < cy < width - 1):
                continue        # у границы чанка соседей не видно
            if (static[i - tds] != WATER_TILE or static[i + tds] != WATER_TILE
                    or static[i - self.chunk_arr_width] != WATER_TILE):
                continue
            spots.append((chunk_x * CHUNK_SIZE + cx, chunk_y * CHUNK_SIZE + cy))
        if not spots:
            return cnt_creatures
        rnd = random.Random(f"water-life:{base}:{chunk_x}:{chunk_y}")
        # Чайки идут ПЕРВЫМИ и берут не больше двух мест. Лимит существ на чанк
        # маленький (CHUNK_CREATURE_LIMIT = 4), а рыбья стая заполняет его
        # целиком: при обратном порядке чаек не появлялось вообще — замер дал
        # ноль на пяти сидах. Чайка при этом единственный признак водоёма,
        # видимый издалека, и терять её дороже, чем третью рыбу.
        if rnd.random() < 0.5:
            tx, ty = rnd.choice(spots)
            # В запечатанной полости чайке не место — там нет неба.
            if not (has_pocket and water_pocket_tile_at(
                    tx, ty, base, self.pocket_sites) is not None):
                gull = spawn_creature(C.Gull, self.game, tx, ty - C.Gull.fly_height)
                chunk[1].append(gull)
                cnt_creatures += 1
                cnt_creatures = self._fill_flock(
                    chunk, gull, [(x, y - C.Gull.fly_height) for x, y in spots],
                    cnt_creatures, limit=cnt_creatures + 1)
        # Один бросок на водоём в чанке, а не на тайл: иначе озеро на сорок
        # тайлов воды выдавало бы сорок жеребьёвок и превращалось в аквариум.
        for _ in range(rnd.randint(1, 2)):
            if cnt_creatures >= CHUNK_CREATURE_LIMIT:
                break
            tx, ty = rnd.choice(spots)
            # Кто живёт в этой воде, решает сама вода, а не чанк: глубинник —
            # хозяин ЗАПЕЧАТАННОЙ полости, и в открытом озере его быть не
            # должно, иначе находка перестаёт быть находкой. Чанк при этом
            # запросто содержит и полость, и озеро сразу, так что проверять
            # надо выбранный тайл.
            in_pocket = has_pocket and water_pocket_tile_at(
                tx, ty, base, self.pocket_sites) is not None
            pool = [(C.Fish, 10), (C.Piranha, 4), (C.Jellyfish, 3)]
            if in_pocket:
                pool.append((C.DeepLurker, 4))
            cls = rnd.choices([c for c, _ in pool], [w for _, w in pool])[0]
            obj = spawn_creature(cls, self.game, tx, ty)
            chunk[1].append(obj)
            cnt_creatures += 1
            if obj.flock_size > 1:
                cnt_creatures = self._fill_flock(chunk, obj, spots, cnt_creatures)
        return cnt_creatures

    def _spawn_flocks(self, chunk, on_ground_tiles, cnt_creatures):
        """Досыпать компаньонов стайным существам этого чанка.

        Почему вторым проходом, а не в самой жеребьёвке. Генератор выбирает
        существо на КАЖДЫЙ подходящий тайл отдельно, поэтому стая при таком
        спавне невозможна в принципе: каждый зверь — независимый бросок, и
        встречаются они по одному. Стаю добавляем по уже выпавшим существам —
        тогда биомные пулы, лимит чанка и кривая сложности остаются
        единственным источником правды о том, кто где живёт, а стайность
        оказывается свойством вида, а не второй таблицей спавна.

        flock_id считается из позиции вожака, а не берётся из счётчика: чанк
        выгружается и создаётся заново на ходу (`dynamic_dump`), и стая обязана
        собраться той же самой, иначе после возвращения игрока на месте одной
        группы оказались бы две.
        """
        # Существа, у которых стая уже собрана, пропускаются: водную живность
        # заселяет свой проход, и места он берёт в воде, а не на дёрне.
        leaders = [o for o in chunk[1]
                   if getattr(o, "flock_size", 1) > 1 and not getattr(o, "flock_id", 0)]
        if not leaders:
            return cnt_creatures
        spots = None
        for leader in leaders:
            if cnt_creatures >= CHUNK_CREATURE_LIMIT:
                break
            if spots is None:
                spots = list(on_ground_tiles)
            cnt_creatures = self._fill_flock(chunk, leader, spots, cnt_creatures)
        return cnt_creatures

    def _fill_flock(self, chunk, leader, spots, cnt_creatures, limit=None):
        """Досыпать вожаку компаньонов из списка подходящих мест.

        Список мест передаётся, а не берётся отсюда: для стада это дёрн, для
        рыбьей стаи — внутренняя вода. Рыба, посаженная на дёрн, задохнулась бы
        на берегу собственного озера.

        limit — свой предел числа существ, ниже общего: у водоёма нужно оставить
        места и рыбе, и чайкам, а лимит на чанк всего четыре.
        """
        if limit is None:
            limit = CHUNK_CREATURE_LIMIT
        ltx, lty = leader.rect.centerx // TSIZE, leader.rect.centery // TSIZE
        leader.flock_id = ltx * 4096 + lty
        near = [t for t in spots
                if abs(t[0] - ltx) <= leader.flock_radius and abs(t[1] - lty) <= 4
                and (t[0], t[1]) != (ltx, lty)]
        random.shuffle(near)
        for tx, ty in near[:leader.flock_size - 1]:
            if cnt_creatures >= limit:
                break
            mate = spawn_creature(type(leader), self.game, tx, ty)
            mate.flock_id = leader.flock_id
            chunk[1].append(mate)
            cnt_creatures += 1
        return cnt_creatures

    def _place_dungeon_guards(self, chunk, chunk_x, chunk_y, base, cache):
        """Поставить стражей подземелья в только что созданный чанк.

        Именно при генерации, а не по входу игрока: раскладка стражей —
        функция сида (Dungeon.guard_spots), поэтому чанк, созданный дважды,
        даёт тех же стражей, а не удваивает толпу.
        """
        import units.Objects.Creatures as C
        # Сначала выдать объекты блокам, которые генератор написал прямо в
        # массив. Генерация не проходит через set_static_tile, поэтому у
        # сундука, лампы и плиты подземелья не появлялось объекта: лампа не
        # светила, плита не читалась, сундук не открывался вовсе.
        self._bind_class_tile_objects(chunk, chunk_x, chunk_y)
        seen = set()
        for dx in (0, CHUNK_SIZE - 1):
            for dy in (0, CHUNK_SIZE - 1):
                site = dungeon_at(chunk_x * CHUNK_SIZE + dx, chunk_y * CHUNK_SIZE + dy, base, cache)
                if site is None or id(site) in seen:
                    continue
                seen.add(id(site))
                self._fill_dungeon_chests(chunk, site, chunk_x, chunk_y)
                for name, tx, ty in site.guard_spots(chunk_x, chunk_y, CHUNK_SIZE):
                    cls = getattr(C, name, None)
                    if cls is None:
                        continue
                    chunk[1].append(spawn_creature(cls, self.game, tx, ty))
                    chunk[3][1] += 1

    def _bind_class_tile_objects(self, chunk, chunk_x, chunk_y):
        """Создать объекты для CLASS_TILE-блоков, записанных генератором.

        set_static_tile создаёт объект (сундук/лампа/плита) при постановке, а
        генератор пишет тип прямо в массив чанка и объект не создаёт. Для
        обычного рельефа это неважно — там нет таких блоков, — но подземелья
        их ставят, и без этого прохода они были бы декорацией.
        """
        static = chunk[0]
        base_x, base_y = chunk_x * CHUNK_SIZE, chunk_y * CHUNK_SIZE
        for i in range(0, self.chunk_arr_size, self.tile_data_size):
            ttile = static[i]
            if ttile not in CLASS_TILE:
                continue
            if static[i + 3]:
                continue                    # объект уже есть
            cell = i // self.tile_data_size
            tx = base_x + cell % CHUNK_SIZE
            ty = base_y + cell // CHUNK_SIZE
            obj = tiles_class[ttile](self.game, (tx, ty))
            self.add_tile_obj_to_chunk(chunk, obj)
            static[i + 3] = obj.id

    def bind_tile_object(self, x, y):
        """Выдать объект классовому блоку, у которого его нет.

        Нужно для миров, сохранённых ДО того, как блок стал классовым: котёл
        (125) до этого релиза был обычной мебелью, объекта у него не было, и
        первый же правый клик по нему падал бы на None. Тот же случай — блок,
        записанный генератором мимо set_static_tile.
        """
        cxy = self.to_chunk_xy(x, y)
        chunk = self.game_map.get(cxy)
        if chunk is None:
            return None
        i = self.convert_pos_to_i(x, y)
        ttile = chunk[0][i]
        cls = tiles_class.get(ttile)
        if cls is None:
            return None
        obj = cls(self.game, (x, y))
        self.add_tile_obj_to_chunk(chunk, obj)
        chunk[0][i + 3] = obj.id
        self.modified_chunks.add(cxy)
        return obj

    def _fill_dungeon_chests(self, chunk, site, chunk_x, chunk_y):
        """Наполнить сундуки подземелья, попавшие в этот чанк.

        Раньше сундук в сокровищнице стоял пустым (docs/DUNGEONS.md отмечал
        это как незакрытый пробел): раскладка подземелья — чистая функция от
        тайла, а наполнение требует объекта-инвентаря, который существует
        только после генерации.

        Читаем из переданного chunk, а не через get_static_tile: чанк ещё НЕ
        вставлен в self.game_map — он только строится, и по координатам его
        пока не найти.
        """
        from units.Loot import fill_container
        for tx, ty in site.chest_spots(chunk_x, chunk_y, CHUNK_SIZE):
            i = self.convert_pos_to_i(tx, ty)
            if chunk[0][i] != 129:
                continue
            obj = chunk[2].get(chunk[0][i + 3])
            inv = getattr(obj, "inventory", None)
            if inv is not None:
                fill_container(self.game, inv, tx, ty, self.base_generation,
                               site.kind.name)

    def save_current_game_map(self):
        if self.world_id is None:
            # мир ещё не привязан к папке — создаём
            self.world_meta = WorldStorage.new_world_meta()
            self.world_id = self.world_meta["id"]
        self.save_game_map(self.game, self.world_id)

    def save_game_map(self, game, world_id=None):
        if world_id is None:
            self.save_current_game_map()
            return
        self.saved = True
        self.world_id = world_id
        self.game.ui.new_sys_message(f"Сохранение", draw_now=True)

        file_p = WorldStorage.data_path(world_id)
        print(f"GamaMap: '{file_p}' - SAVING...")
        data = {"game_map_vars": self.get_vars(), "player_vars": game.player.get_vars(),
                "game_version": GAME_VERSION, "game_tact": game.tact, "game_total_time": game.total_time}
        t = pickle.dumps(data)
        os.makedirs(WorldStorage.world_dir(world_id), exist_ok=True)
        with open(file_p, 'wb') as f:
            f.write(t)
        self.world_meta = WorldStorage.touch_meta(world_id, playtime=game.total_time / 1000)
        print("GamaMap - SAVE!")
        self.game.ui.new_sys_message(
            get_translated_text("Мир сохранён: ") + self.world_meta["name"], draw_now=True)

    @staticmethod
    def _load_error_message(exc):
        """Понятная причина вместо технической ошибки pickle.

        Мир с контентом мода не откроется, если мод выключили или удалили:
        сохранение ссылается на класс существа по имени модуля. Без этой
        подсказки игрок видел бы только «Не удалось загрузить мир» и не
        понял бы, что виноват мод."""
        if isinstance(exc, AttributeError) or "attribute" in str(exc).lower():
            return get_translated_text("Не удалось загрузить мир: включите мод, "
                                       "с которым он создан")
        return get_translated_text("Не удалось загрузить мир")

    def open_game_map(self, game, world_id):
        meta = WorldStorage.load_meta(world_id)
        name = meta["name"] if meta else str(world_id)
        self.game.ui.new_sys_message(get_translated_text("Загрузка мира: ") + name, draw_now=True)

        file_p = WorldStorage.data_path(world_id)
        print(f"GamaMap: '{file_p}' - LOADING...")
        try:
            with open(file_p, 'rb') as f:
                data = pickle.load(f)
        except Exception as exc:
            print("Ошибка загрузки:", exc)
            self.game.ui.new_sys_message(self._load_error_message(exc), draw_now=True)
            return None
        version = data.get("game_version", "0.4")
        # Предупреждаем только при разной major.minor: точное сравнение
        # означало бы, что после каждого патч-релиза игрок видит это
        # сообщение на каждом своём мире, хотя формат сейва не менялся.
        if parse_version(version)[:2] != parse_version(GAME_VERSION)[:2]:
            # пробуем загрузить, но предупреждаем
            self.game.ui.new_sys_message(
                get_translated_text("Мир из другой версии: ") + str(version), draw_now=True)
        try:
            game.game_map.set_vars(data["game_map_vars"])
            game.player.set_vars(data["player_vars"])
        except Exception as exc:
            print("Ошибка загрузки:", exc)
            self.game.ui.new_sys_message(self._load_error_message(exc), draw_now=True)
            return None
        self.world_id = world_id
        self.world_meta = meta
        game.tact = data.get("game_tact", 0)
        game.total_time = data.get("game_total_time", 0)
        if abs(game.player.rect.x) > 10000 or abs(game.player.rect.y) > 10000:
            game.screen_map.teleport_to_player()
        game.player.inventory.ui.redraw_top()
        print("GamaMap - LOAD!")
        return file_p

    def get_choice_world(self, pos_1, pos_2):
        size = pos_2[0] + 1 - pos_1[0], pos_2[1] + 1 - pos_1[1]
        array = []
        for y in range(size[1]):
            for x in range(size[0]):
                array.append(self.get_static_tile(x + pos_1[0], y + pos_1[1]))
        return size, array

    def spawn_gate(self):
        self.gate = PortalMainGate(self.game, TSIZE // 2, TSIZE // 2)
        self.add_dinamic_obj(*self.gate.chunk_pos, self.gate)
        self.game.player.active = False
        sound_gate.play()

    def new_world(self, base_generation=None, tutorial=False):
        if tutorial and base_generation is None:
            base_generation = 4242  # у мира обучения фиксированный сид
        self.__init__(self.game, self.gen_type, base_generation)
        if tutorial:
            self.world_meta = WorldStorage.new_world_meta(
                name=get_translated_text("Обучение"), tutorial=True)
            self.tutorial_step = 0
        else:
            self.world_meta = WorldStorage.new_world_meta()
        self.world_id = self.world_meta["id"]
        self.set_structure((-10, -13), structure_start)
        self.game.reinit_player()
        # У нового мира нет незакрытых событий: директор помнит
        # кулдауны и незавершённый налёт, а они относились к прошлому миру.
        if hasattr(self.game, 'events'):
            self.game.events.__init__()
        self.game.player.tp_to(config.GameSettings.start_pos)
        self.spawn_gate()
        self._place_altar_tablet()
        self._place_altar_echo()
        self._build_starter_grove()
        if tutorial:
            self._build_tutorial_island()
            self._place_tutorial_chest()
            self._give_tutorial_items()

    # Стартовая роща: сколько тайлов вокруг спавна засеваем и сколько
    # деревьев ставим сразу. Раньше рядом со спавном могло не оказаться ни
    # одного дерева — а дерево это доски, стол, кирка, топливо, то есть
    # ВСЯ первая цепочка. Игра начиналась с долгой ходьбы наугад.
    GROVE_RADIUS = 26
    GROVE_TREES = 5
    GROVE_BUSHES = 4

    def _place_altar_echo(self):
        """Поставить отголосок у алтаря.

        Первое, что игрок видит после плиты: он отвечает на текущую главу и
        тем самым говорит, куда идти дальше, — но говорит про то, что делали
        ОНИ, а не приказывает (docs/STORYBOOK.md).
        """
        pos = config.GameSettings.start_pos
        tx, ty = pos[0] // TSIZE + 3, pos[1] // TSIZE
        for dy in range(0, 6):
            if self.get_static_tile_type(tx, ty + dy, 0, create_chunk=True):
                self.set_static_tile(tx, ty + dy - 1, 239, create_chunk=True)
                return

    def _build_starter_grove(self):
        """Гарантировать у спавна деревья и ягодные кусты.

        Ставим только растительность и только на существующий дёрн: платформ
        и сундуков в обычном мире быть не должно — это обучение, а не
        песочница. Задача скромнее: чтобы первые пять минут игрок собирал
        ресурсы, а не искал, есть ли они вообще.
        """
        sx = config.GameSettings.start_pos[0] // TSIZE
        sy = config.GameSettings.start_pos[1] // TSIZE
        spots = []
        for tx in range(sx - self.GROVE_RADIUS, sx + self.GROVE_RADIUS + 1):
            top = self.surface_top_at(tx, sy)
            if top is None:
                continue
            if self.get_static_tile_type(tx, top, default=0, create_chunk=True) not in (1, 2):
                continue
            if self.get_static_tile_type(tx, top - 1, default=0, create_chunk=True) != 0:
                continue
            spots.append((tx, top - 1))
        if not spots:
            return
        rnd = random.Random(self.base_generation)      # роща одинакова для сида
        rnd.shuffle(spots)
        # деревья ставим не вплотную — иначе grow_tree сцепит их в сплошную
        # стену из стволов, и рубить будет нечего, кроме одной колонны
        placed = []
        for tx, ty in spots:
            if len(placed) >= self.GROVE_TREES:
                break
            if any(abs(tx - px) < 4 for px in placed):
                continue
            grow_tree((tx, ty), game_map=self)
            placed.append(tx)
        bushes_left = self.GROVE_BUSHES
        for tx, ty in spots[::-1]:
            if bushes_left <= 0:
                break
            if self.get_static_tile_type(tx, ty, default=0, create_chunk=True) != 0:
                continue                                # тут уже вырос ствол
            self.set_static_tile(tx, ty, 101)
            self.set_static_tile_state_img(tx, ty, 3)   # куст сразу с ягодами
            bushes_left -= 1

    def _give_tutorial_items(self):
        """Выдать игроку меч и кирку в инвентарь на старте обучения."""
        inv = self.game.player.inventory
        for idx in (530, 501):  # деревянная кирка, меч
            if idx in TOOLS:
                item = TOOLS[idx](self.game)
                item.set_owner(inv)
                inv.put_to_inventory(item)
        inv.ui.redraw_top()

    def _build_tutorial_island(self):
        """Гарантированный островок с деревом у спавна — не зависит от генерации,
        чтобы игроку всегда было куда встать и что срубить."""
        sx = config.GameSettings.start_pos[0] // TSIZE
        sy = config.GameSettings.start_pos[1] // TSIZE
        top_y = sy + 3
        for tx in range(sx - 7, sx + 9):
            self.set_static_tile(tx, top_y, 1)          # трава сверху
            for dy in range(1, 4):
                self.set_static_tile(tx, top_y + dy, 2)  # земля под ней
        # чистое небо над платформой, чтобы дерево росло свободно
        for tx in range(sx - 7, sx + 9):
            for dy in range(1, 9):
                if self.get_static_tile_type(tx, top_y - dy, default=0, create_chunk=True) != 0:
                    self.set_static_tile(tx, top_y - dy, None)
        grow_tree((sx - 4, top_y - 1), game_map=self)   # дерево слева от спавна

    def _place_tutorial_chest(self):
        """Сундук с припасами для обучения (руда, кирпич, слизь, ягоды, рубины) —
        ставится на землю недалеко от спавна, позиция запоминается для маркера."""
        x = 4
        chest_y = None
        for y in range(-6, 40):
            if self.get_static_tile_type(x, y, default=0, create_chunk=True) != 0:
                chest_y = y - 1
                break
        if chest_y is None:
            chest_y = -1
        self.set_static_tile(x, chest_y, 129)
        tile = self.get_static_tile(x, chest_y)
        chest = self.get_tile_obj(*self.to_chunk_xy(x, chest_y), tile[3])
        if chest is not None:
            # Хватает на печку (31x4, 11x1, 64x2), котёл (11x1, 64x8), ведро
            # (64x3) и первую варку: котлу теперь нужны топливо, ведро воды и
            # ингредиент, поэтому в припасах есть и доски, и ягоды.
            for idx, cnt in ((31, 8), (64, 20), (51, 30), (53, 30), (66, 6), (11, 12)):
                chest.inventory.put_to_inventory(ItemsTile(self.game, idx, count=cnt))
        self.tutorial_state["chest_pos"] = [x, chest_y]

    def _place_altar_tablet(self):
        """Плита алтаря у спавна — та самая, на которой герой очнулся
        (docs/STORY.md, завязка). Ставится в каждом новом мире: это первая
        точка входа в сюжет, и она не должна зависеть от того, повезёт ли
        игроку найти структуру.

        Позицию ищем так же, как у сундука обучения: сверху вниз до первого
        непустого тайла, плиту кладём на него."""
        x = -2
        y_ground = None
        for y in range(-6, 40):
            if self.get_static_tile_type(x, y, default=0, create_chunk=True) != 0:
                y_ground = y - 1
                break
        if y_ground is None:
            y_ground = -1
        # вариант 0 = надпись "altar" (units/Lore.TABLET_VARIANTS)
        self.set_static_tile(x, y_ground, [300, TILES_SOLIDITY.get(300, -1), 0, 0])
        self.story_state["altar_pos"] = [x, y_ground]


# Плотность породы — чистая функция от (тайл, сид): никакого состояния
# чанка. Именно поэтому поверхность можно прощупать до генерации (см.
# GameMap.surface_y_at) — это и позволяет ставить структуры на землю.
# Вынесено сюда, чтобы у генератора и у зонда была ОДНА формула: если
# держать две копии, они однажды разойдутся и структуры начнут висеть.
_TERRAIN_OCTAVES = 6
_TERRAIN_THRESHOLD = -0.2
_TERRAIN_LACUNARITY = 2.4


def terrain_is_solid(tx, ty, base):
    """Есть ли порода в тайле (tx, ty) при сиде base."""
    h = noise2(tx / freq_x, ty / freq_y) * 20 + ty
    if h <= START_ATMO_Y or START_HELL_Y <= h <= START_HELL_Y + 50:
        return False
    return noise2(tx / freq_x, ty / freq_y, _TERRAIN_OCTAVES, persistence=0.35,
                  base=base, lacunarity=_TERRAIN_LACUNARITY) < _TERRAIN_THRESHOLD


def lake_shape(cell, base):
    """Центр и полуширина озера в клетке решётки — БЕЗ поиска уровня.

    Решётка вместо шума — чтобы у озера были заданные размер и центр: из шума
    получались бы «поля воды» неопределённой формы, а нужна именно чаша.

    Дешёвая часть отделена от дорогой намеренно: уровень зеркала — это скан
    столба на 1650 тайлов, и платить за него для чанков, которые с озером
    даже не пересекаются по горизонтали, незачем (замер: +29% к стоимости
    генерации чанков, где озёр нет вообще).
    """
    rnd = random.Random(f"lake:{base}:{cell}")
    if rnd.random() >= LAKE_CHANCE:
        return None
    r = rnd.randint(LAKE_MIN_R, LAKE_MAX_R)
    margin = r + 4
    center = cell * LAKE_CELL + rnd.randint(margin, max(margin, LAKE_CELL - margin))
    return center, r


def _lake_flanks_hold(center, r, level, base):
    """Опирается ли чаша такой полуширины на остров, а не свисает с обрыва.

    Проверяется порода под зеркалом в БОКОВЫХ колонках. Без этого озеро,
    попавшее центром на площадку у края острова, наполовину висело в
    воздухе: центр опирался на породу, а половина зеркала торчала над
    обрывом — вода в игре не течёт, и так это и оставалось.
    """
    for dx in (-r, -(r * 2) // 3, (r * 2) // 3, r):
        if not terrain_is_solid(center + dx, level + 2, base):
            return False
    return True


def lake_site(cell, base):
    """Озеро в клетке: (центр_x, полуширина, уровень зеркала) или None.

    Слой выбирается случайно из годных площадок столба, а не берётся самый
    верхний: мир — это стопка летающих островов с воздушными провалами между
    ними, и «самый верхний» — это осколок у потолка атмосферы, за тысячу
    тайлов от игрока.

    Две отсечки, без которых половина озёр была фикцией:

    * **Площадка обязана быть в полосе, где вода вообще разрешена.** Раньше
      площадку искали по всему столбу, включая атмосферу выше
      TOP_MIDDLE_WORLD; `lake_tile_at` такое озеро отказывался раскладывать, и
      клетка решётки молча оставалась без воды. Замер на сиде 21: озеро с
      зеркалом на -768 при границе -650, то есть ни одного тайла воды.
    * **Чаша обязана опираться на остров ВСЕЙ шириной.** Если не опирается —
      сужаем её, а не выбрасываем: узкое озеро на площадке лучше, чем
      отсутствие озера или зеркало, свисающее с обрыва.
    """
    shape = lake_shape(cell, base)
    if shape is None:
        return None
    center, r = shape
    tops = [t for t in _island_tops(center, base)
            if LAKE_TOP_MIN < t < LAKE_TOP_MAX]
    if not tops:
        return None
    rnd = random.Random(f"lake-level:{base}:{cell}")
    level = rnd.choice(tops)
    while r >= LAKE_MIN_R:
        if _lake_flanks_hold(center, r, level, base):
            return center, r, level
        r -= 2
    return None


def lake_tile_at(tx, ty, base, cache=None):
    """Что стоит в этом тайле из-за озера: (тайл, кадр) или None.

    Кадр возвращается вместе с тайлом, а не подбирается потом: уровень
    заполнения воды — это часть формы озера, и разделить их значило бы иметь
    два места, где считается одна и та же геометрия. Для породы и воздуха
    кадр 0, то есть возврат остаётся однородным.

    Чистая функция от (тайл, сид) — как terrain_is_solid, не требует
    сгенерированного чанка. Значит зеркало озера можно узнать заранее (для
    структур и проверок), а генератор и проба не разъедутся.

    Берег вырезается вместе с чашей: искать готовую открытую котловину не
    получается (замер — 8 подходящих тайлов на 800 колонок), а озеро,
    вписанное в склон без выемки берега, вырождается в узкую шахту.
    """
    if not (TOP_MIDDLE_WORLD < ty < BOTTOM_MIDDLE_WORLD):
        return None
    cell = tx // LAKE_CELL
    if cache is None:
        cache = {}
    if cell not in cache:
        cache[cell] = lake_site(cell, base)
    site = cache[cell]
    if site is None:
        return None
    center, r, level = site
    dx = tx - center
    if abs(dx) > r:
        return None
    # Полукруглый профиль: у берега мелко, в середине глубоко.
    bowl = (1 - (dx / r) ** 2) ** 0.5
    raw = r * LAKE_DEPTH_FACTOR * bowl      # глубина чаши в тайлах, с дробью
    depth = min(LAKE_MAX_DEPTH, int(raw))
    # Уровень заполнения ряда зеркала: у берега мельче, к середине полный.
    # Именно это делает многоуровневость воды видимой — линия воды у отмели не
    # совпадает с сеткой блоков, и берег перестаёт быть бортом бассейна.
    shoal = max(1, min(WATER_LEVELS,
                       int(raw * WATER_LEVELS / LAKE_SHOAL_SPAN + 0.5)))
    if level < ty <= level + depth:
        # Толща ниже третьего ряда — тёмная: так у озера видно глубину.
        return WATER_TILE, water_frame(shoal if ty == level + 1 else WATER_LEVELS,
                                       ty - level >= LAKE_DEEP_ROW)
    if depth < 1:
        # Кромка: чаша тоньше тайла, но вода тут всё равно должна быть —
        # плёнкой, иначе озеро обрывается вертикальной стеной в полный блок.
        if raw >= LAKE_SHOAL_MIN and ty == level + 1:
            return WATER_TILE, water_frame(shoal)
    if level - int(LAKE_RIM_CLEAR * bowl) <= ty <= level:
        return 0, 0                         # берег: снимаем породу над зеркалом
    return None


# Мир — не «земля и небо над ней», а облако летающих островов от потолка
# атмосферы до ада. Поэтому «верх породы в столбце» бесполезен: он находит
# самый высокий тонкий осколок в тысяче тайлов над игроком. Ищем ПЛОЩАДКУ:
# верх острова, над которым есть настоящее открытое небо и под которым есть
# толща породы. Считается один раз на клетку решётки озёр и кэшируется.
SURFACE_PROBE_SCAN = range(START_ATMO_Y + 5, BOTTOM_MIDDLE_WORLD)
ISLAND_TOP_CLEARANCE = 14   # воздуха над площадкой (иначе это не поверхность)
# Породы под площадкой должно быть заведомо больше, чем самая глубокая чаша,
# иначе у широкого озера дно оказывалось ниже толщи острова, проверка дна не
# проходила — и озеро молча не появлялось вообще.
ISLAND_TOP_THICKNESS = int(LAKE_MAX_R * LAKE_DEPTH_FACTOR) + 3


def _island_tops(tx, base, clearance=ISLAND_TOP_CLEARANCE,
                 thickness=ISLAND_TOP_THICKNESS):
    """Все верхушки островов в столбце, годные под озеро.

    Годная — та, над которой есть настоящее открытое небо (clearance) и под
    которой есть толща породы (thickness): на тонком осколке озеро вытекло
    бы через его низ.
    """
    tops = []
    air_run = 0
    for y in SURFACE_PROBE_SCAN:
        if terrain_is_solid(tx, y, base):
            if air_run >= clearance and \
                    all(terrain_is_solid(tx, y + d, base) for d in range(1, thickness + 1)):
                tops.append(y)
            air_run = 0
        else:
            air_run += 1
    return tops


# Пещерная флора. Гриб — везде под землёй, блоровый мох — только на глубине,
# рядом с блором: он и светится тем же синим. Шансы маленькие, потому что
# проверка идёт на КАЖДЫЙ тайл породы с воздухом над ним, а таких в пещерах
# много — но «камень с воздухом над ним» это только пол пещеры, и замер
# показал, что при 0.02 на 312 чанков находилось СЕМЬ растений на весь мир.
CAVE_MUSHROOM_CHANCE = 0.09
BLORE_MOSS_CHANCE = 0.12
BLORE_MOSS_DEPTH = 420


def cave_plant_selection(tile_y):
    """Растение на камне под землёй или None.

    Отдельно от `random_plant_selection`: та выбирает по БИОМУ и ставится на
    дёрн, а под землёй биома нет — там есть только глубина.
    """
    if tile_y < BOTTOM_MIDDLE_WORLD // 8:
        return None                     # у поверхности пещерной флоры нет
    if tile_y > BLORE_MOSS_DEPTH and random.random() < BLORE_MOSS_CHANCE:
        return 112                      # блоровый мох
    if random.random() < CAVE_MUSHROOM_CHANCE:
        return 111                      # пещерный гриб
    return None


def random_plant_selection(biome=None):
    if random.randint(0, 2) == 0:

        plants = biomes_plants_chance.get(biome, biomes_plants_chance[None])
        if not plants:
            return None
        plant_tile_type = random.choices(list(plants.keys()), list(plants.values()), k=1)[0]
        if plant_tile_type is None:
            return None
        if plant_tile_type is None:
            return None

        state_img = 0
        state = {}
        if plant_tile_type in GROWING_PLANTS:
            # Генерация ставит зрелые: мир должен выглядеть выросшим, а не
            # только что засеянным. Ростки бывают только там, где сажал игрок.
            state_img = GROWING_PLANT_STAGES - 1
        if plant_tile_type == 101:
            # рандомная картинка только если ставиться при генерации карты
            state_img = random.randint(0, 3)
        elif plant_tile_type == 102:
            if random.randint(0, 10) < 9:
                state_img = 2  # вырастить мгновено дерево

        if plant_tile_type in PLANT_WITH_RANDOM_SPRITE:
            state_img = random.randint(0, PLANT_WITH_RANDOM_SPRITE[plant_tile_type]-1)
        if plant_tile_type in PLANT_WITH_RANDOM_LOCAL_POS:
            img = tile_imgs[plant_tile_type]
            lx, ly = random.randint(0, max(0, TSIZE - img.get_width())), TSIZE - img.get_height()
            state[TILE_LOCAL_POS] = [max(0, lx), max(0, ly)]
        if plant_tile_type in PLANT_WITH_TIMER:
            state[TILE_TIMER] = 0
        if not state:
            state = 0

        return plant_tile_type, state_img, state
    return None


def spawn_creature(cls, game, tile_x, tile_y):
    """Создать существо с поправкой на кривую сложности места.

    Множитель ставится на экземпляр, а не на класс: одна и та же змея у
    спавна и в аду должна отличаться, а трогать класс значило бы менять
    её сразу везде.
    """
    creature = cls(game, (tile_x * TSIZE, tile_y * TSIZE))
    scale = difficulty_scale(tile_x, tile_y)
    if scale != 1.0 and creature.max_lives > 0:
        creature.max_lives = max(1, int(round(creature.max_lives * scale)))
        creature.lives = creature.max_lives
        creature.punch_damage = max(1, int(round(creature.punch_damage * scale)))
    # Тот же множитель идёт и в лут: риск и награда обязаны идти по одной
    # кривой (см. docs/BALANCE_SCHEME.md). Без этого каменный голем был худшей
    # сделкой в игре — 120 HP и 20 урона ради 5-10 камня, а на глубине ещё и
    # вдвое крепче за тот же камень.
    creature.loot_scale = scale
    return creature


# Существа, которых не выпускаем в «песочнице» у спавна: слайм-босс это
# 250 HP и 35 урона — встреча с ним на первой минуте не сложность, а стена.
HARD_CREATURES = (SlimeBigBoss,)


def near_spawn(tile_x):
    if tile_x is None:
        return False
    start_x = config.GameSettings.start_pos[0] // TSIZE
    return abs(tile_x - start_x) <= DIFFICULTY_SAFE_RADIUS


def random_creature_selection(tile_y=None, biome=None, tile_x=None):
    """tile_y и biome задают биом/глубину-зависимость спавна вместо единого
    для всего мира пула мобов:
    - космос (tile_y < START_SPACE_Y) — пылевые рои, дрейферы, стражи
    - ад (tile_y > START_HELL_Y) — бесы, волки, слаймы
    - глубокие пещеры (BOTTOM_MIDDLE_WORLD < tile_y <= START_HELL_Y) —
      летучие мыши, каменные големы
    - пустыня (0) — скорпионы, верблюды; саванна (1) — коровы, зайцы
    - тундра/тайга (3, 8) — волки, олени, пингвины
    - тропики/джунгли (2, 5) — змеи, крабы
    - леса (4, 6, 7) — олени, лисы, кабаны
    - остальное — исходный набор + зайцы

    Существа из модов добавляются в жеребьёвку своей зоны/биома с
    собственным весом (см. units/mods.py, поле "spawn")."""
    if not config.GameSettings.creatures:
        return None
    r = random.random()
    if r >= CHUNK_CREATURE_CHANCE:
        return None

    if tile_y is not None and tile_y < START_SPACE_Y:
        zone, pool, weights = "space", [DustSwarm, SpaceDrifter, VoidSentinel], [10, 4, 1]
    elif tile_y is not None and tile_y > START_HELL_Y:
        zone, pool, weights = "hell", [Slime, Wolf, Imp], [10, 3, 4]
    elif tile_y is not None and tile_y > BOTTOM_MIDDLE_WORLD:
        zone, pool, weights = "caves", [Slime, Bat, StoneGolem], [10, 6, 2]
    elif biome == 0:  # desert
        zone, pool, weights = "surface", [Slime, Scorpion, Snake, Camel, Bird, Hawk], [10, 6, 2, 3, 2, 1]
    elif biome == 1:  # savanna
        zone, pool, weights = "surface", [Slime, Cow, Wolf, Rabbit, Bird, Raven, Hawk], [15, 10, 1, 6, 2, 1.5, 1]
    elif biome in (3, 8):  # tundra, boreal_forest
        zone, pool, weights = "surface", [Slime, Wolf, Cow, Deer, Penguin, Bird, Raven], [12, 5, 1, 4, 3, 2, 2]
    elif biome in (2, 5):  # tropical_woodland, rainforest
        zone, pool, weights = "surface", [Slime, Snake, Cow, Wolf, Crab, Bird, Hawk], [15, 4, 3, 1, 3, 2, 1]
    elif biome in (4, 6, 7):  # seasonal/temperate/temperate_rainforest
        zone, pool, weights = "surface", [Slime, Deer, Fox, Boar, Rabbit, Bird, Raven, Hawk], [15, 5, 4, 2, 5, 2, 1.5, 1]
    else:
        zone = "surface"
        pool = [Slime, Cow, Snake, Wolf, SlimeBigBoss, Rabbit, Bird, Raven]
        weights = [20, 5, 1, 0.7, 0.25, 6, 2, 1]

    if zone == "surface" and near_spawn(tile_x):
        filtered = [(c, w) for c, w in zip(pool, weights) if c not in HARD_CREATURES]
        if filtered:
            pool, weights = [c for c, _ in filtered], [w for _, w in filtered]

    # мод-существа ДОБАВЛЯЮТСЯ к ванильному пулу, а не заменяют его —
    # иначе один мод выключил бы всех обычных мобов в своём биоме
    for cls, spec in MOD_CREATURES:
        if spec["zone"] != zone:
            continue
        if spec["biomes"] is not None and biome not in spec["biomes"]:
            continue
        pool.append(cls)
        weights.append(spec["weight"])

    return random.choices(pool, weights, k=1)[0]




# from collections import Counter
# Counter(random.choices(['Slime', 'Cow', 'Wolf', 'SlimeBigBoss'], [20, 5, 0.7, 0.25])[0]
#         for _ in range(100000))
# Counter({'Slime': 77209, 'Cow': 19239, 'Wolf': 2595, 'SlimeBigBoss': 957})
