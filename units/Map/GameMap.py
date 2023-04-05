import glob
from typing import Union

from noise import snoise2 as noise2

from units.Objects.Creatures import Slime, Cow, Wolf, SlimeBigBoss, Snake
from units.Objects.Entities import PortalMainGate
from units.Objects.Entity import PhysicalObject
from units.Objects.Items import ItemsTile
from units.Objects.TileClasses import tiles_class
from units.Tools import TOOLS
from units.biomes import biome_of_pos
from units.Map.Structures import Structures_chance, Structures, Structures_all, structure_start
from units.Tiles import *
from units.sound import sound_gate


class GameMap(SavedObject):
    not_save_vars = SavedObject.not_save_vars | {"gate", "particles"}
    save_slots = 16

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
        self.num_save_map = 0
        self.saved = False
        self.start_space_y = START_SPACE_Y
        self.start_hell_y = START_HELL_Y
        self.creative_mode = CREATIVE_MODE
        self.gate = None
        if self.base_generation is None:
            self.new_base_generation()

    def new_base_generation(self):
        self.base_generation = random.randint(-1e5, 1e5)
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
        # for k, i in vrs.items():
        #     self.__dict__[k] = i

    def get_vars(self):
        d = super(GameMap, self).get_vars()
        ch = d["game_map"][-1, -1]
        print("==", d["game_map"][-1, -1])
        # === convert dynamic_objs ===
        game_map = {}
        for pos, chunk in d["game_map"].items():
            game_map[pos] = chunk.copy()
            game_map[pos][1] = [(type(obj), obj.get_vars()) for obj in chunk[1]]
            game_map[pos][2] = {key: (type(obj), obj.get_vars()) for key, obj in chunk[2].items()}
        d["game_map"] = game_map
        d.pop("game")
        d.pop("particles")
        return d

    def chunk(self, xy, default=None, for_player=False, create_chunk=False):
        res = self.game_map.get(xy, default)
        if res is default and create_chunk:
            res = self.generate_chunk(*xy)
        if res and for_player:
            self.update_chunk(res)
        return res

    def update_chunk(self, chunk):
        if config.GameSettings.creatures:
            crt_cash = chunk[3]
            if self.game.tact > crt_cash[2] + FPS * 300:
                if crt_cash[1] < CHUNK_CREATURE_LIMIT:
                    crt_cash[2] = self.game.tact
                    dynamic_tiles = chunk[1]
                    scroll = self.game.screen_map.scroll
                    # if not self.game.screen_map.display_rect.collidepoint(x - scroll[0], y - scroll[1]):
                    crt_cnt = min(len(crt_cash[0]), random.randint(0, CHUNK_CREATURE_LIMIT - crt_cash[1]))
                    tiles_xy = random.choices(tuple(crt_cash[0]), k=crt_cnt)
                    for tile_xy in tiles_xy:
                        # if random.random() < 0.005:
                        x, y = tile_xy[0] * TSIZE, tile_xy[1] * TSIZE
                        Crt = random_creature_selection()
                        if Crt is not None:
                            dynamic_tiles.append(Crt(self.game, (x, y)))
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
            if tile[3]:
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
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), create_chunk=create_chunk)
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
            return True
        return False

    def set_obj_static_tile(self, x, y, group_id):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 3] = group_id
            return True
        return False

    def set_static_tile_solidity(self, x, y, sol):
        """Установить прочность тайла"""
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 1] = sol
            return True
        return False

    def set_static_tile_state(self, x, y, state):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i + 2] = state
            return True
        return False

    def get_backtile(self, x, y, create_chunk=True):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), create_chunk=create_chunk)
        if not chunk:
            return
        i = (y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)
        return chunk[5][i]

    def set_backtile(self, x, y, backtile_type, create_chunk=True):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), create_chunk=create_chunk)
        i = (y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)
        chunk[5][i] = backtile_type

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

        return

    def add_particle(self, particle):
        self.particles.append(particle)

    def del_particle_of_idx(self, idx):
        return self.particles.pop(idx)

    def add_item_of_index(self, index, count_items, x, y):
        npos = (x * TSIZE + random.randint(0, TSIZE - HAND_SIZE), y * TSIZE)
        if index in TOOLS:
            # Инструмент
            item = TOOLS[index](self.game, pos=npos)
            item.set_owner(self)
        else:
            item = ItemsTile(self.game, index, npos, count_items)
        self.add_dinamic_obj(*self.to_chunk_xy(x, y), item)

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

                build_id = random.choices(Structures_chance[structures_area][0],
                                          Structures_chance[structures_area][1], k=1)[0]
                build = Structures[structures_area][build_id]
                size, construction = build[2]

                # left_top, right_top, left_bottom, right_bottom
                points = [(pos[0], pos[1]), (pos[0] + size[0], pos[1]),
                          (pos[0], pos[1] + size[0]), (pos[0] + size[0], pos[1] + size[1])]
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
            self.set_structure(pos, Structures_all[build_id][2])
            self.set_state_of_points_build(points, 2)  # builded

    def set_structure(self, pos, build):
        if len(build) == 2:
            backtiles = []
            size, array = build
        else:
            size, array, backtiles = build
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
        res = self.create_pass_chunk((x, y))
        static_tiles, dynamic_tiles, tile_objs, creature_cash, biome_info, back_tiles = res
        on_ground_tiles, cnt_creatures = creature_cash[0], creature_cash[1]
        tile_index = 0
        backtile_index = 0
        octaves = 6
        base = self.base_generation
        threshold = -0.3
        threshold = -0.2
        lacunarity = 2.4
        base_x = x * CHUNK_SIZE
        base_y = y * CHUNK_SIZE
        tile_y = base_y  # global tile y (not px)
        i = 0
        standart_noise2_bool = lambda tx, ty: noise2(tx / freq_x, ty / freq_y, octaves, persistence=0.35, base=base,
                                                     lacunarity=lacunarity) < threshold and (
                                                      noise2(tx / freq_x, ty / freq_y) * 20 + ty) > START_ATMO_Y and (
                                                      (noise2(tx / freq_x, ty / freq_y) * 20 + ty) < START_HELL_Y or (
                                                      noise2(tx / freq_x, ty / freq_y) * 20 + ty) > (
                                                              START_HELL_Y + 50))

        # print("noise", (noise2(base_x / freq_x, base_y / freq_y) * 20 + base_y) > START_SPACE_Y)
        for y_pos in range(CHUNK_SIZE):  # local tile y in chunk (not px)
            tile_x = base_x  # global tile x (not px)
            for x_pos in range(CHUNK_SIZE):  # local tile x in chunk (not px)
                biome_info[i] = biome_of_pos(tile_x, tile_y)
                tile_type = None
                backtile_type = None
                if config.GameSettings.vertical_tunel and tile_x in (-2, -1, 0, 1):
                    tile_type = 0
                # if (noise2(tile_x / freq_x, tile_y / freq_y) * 20 + tile_y) > START_SPACE_Y:
                #     tile_type = 2
                if standart_noise2_bool(tile_x, tile_y) and tile_type is None:
                    if standart_noise2_bool(tile_x, tile_y - 2 - random.randint(0, 1)):
                        tile_type = 3  # stone
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
                                    v7 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55, base=base + 4,
                                                lacunarity=1)
                                    if v7 < -0.915:
                                        tile_type = 21  # ore blore
                                    else:
                                        v8 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55, base=base + 5,
                                                    lacunarity=1)
                                        if v8 < -0.9:
                                            tile_type = 22  # ore copper
                                        else:
                                            v9 = noise2(tile_x * 0.03, tile_y * 0.03, 2, persistence=0.55,
                                                        base=base + 6,
                                                        lacunarity=1)
                                            if v9 < -0.97:
                                                tile_type = 23  # ore gold
                                            else:
                                                v10 = noise2(tile_x * 0.08, tile_y * 0.08, 2, persistence=0.55,
                                                             base=base + 7,
                                                             lacunarity=1)
                                                if v10 < -0.84:
                                                    tile_type = 24  # ore iron
                                                else:
                                                    v10 = noise2(tile_x * cof, tile_y * cof, 2, persistence=0.55,
                                                                 base=base + 8,
                                                                 lacunarity=1)
                                                    if v10 < -0.93:
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
                                        Crt = random_creature_selection()
                                        if Crt is not None:
                                            dynamic_tiles.append(Crt(self.game, (tile_x * TSIZE, tile_y * TSIZE)))
                                            cnt_creatures += 1
                else:
                    # пусто
                    # ставим растение
                    if y_pos == CHUNK_SIZE - 1 and \
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
                if backtile_type:
                    back_tiles[backtile_index] = backtile_type
                tile_x += 1  # v28557
                tile_index += self.tile_data_size
                backtile_index += 1
                i += 1
            tile_y += 1
        creature_cash[1] = cnt_creatures
        return res

    def save_current_game_map(self):
        self.save_game_map(self.game, self.num_save_map)

    def save_game_map(self, game, num=0):
        self.saved = True
        self.game.ui.new_sys_message(f"Сохранение", draw_now=True)

        file_p = GAMEMAPS_PATH + f'game_map-{num}.pclv'
        print(f"GamaMap: '{file_p}' - SAVING...")
        self.num_save_map = num
        # try:
        data = {"game_map_vars": self.get_vars(), "player_vars": game.player.get_vars(),
                "game_version": GAME_VERSION, "game_tact": game.tact, "game_total_time": game.total_time}
        # with open("save_data.json", 'w') as f:
        #     f.write(str(data))
        t = pickle.dumps(data)
        with open(file_p, 'wb') as f:
            f.write(t)
        print("GamaMap - SAVE!")
        self.game.ui.new_sys_message(get_translated_text("Карта сохранена #") + f"{num}", draw_now=True)
        # except Exception as exc:
        #     print("Ошибка сохранения:", exc)
        #     self.game.ui.new_sys_message(f"Ошибка {exc}")
        #     return False
        # finally:
        #
        #     return True

    def open_game_map(self, game, num=0):
        self.game.ui.new_sys_message(get_translated_text("Загрузка карты #") + f"{num}", draw_now=True)

        file_p = GAMEMAPS_PATH + f'game_map-{num}.pclv'
        self.num_save_map = num
        print(f"GamaMap: '{file_p}' - LOADING...")
        # try:
        with open(file_p, 'rb') as f:
            data = pickle.load(f)
        version = data.get("game_version", "0.4")
        if version != GAME_VERSION:
            self.game.ui.new_sys_message(f"Конфликт версий с картой", draw_now=True)

            return
        game_map = data["game_map_vars"]
        game.game_map.set_vars(game_map)
        player = data["player_vars"]
        game.player.set_vars(player)
        game.tact = data.get("game_tact", 0)
        game.total_time = data.get("game_total_time", 0)
        print(game.player.rect.center)
        if abs(game.player.rect.x) > 10000 or abs(game.player.rect.y) > 10000:
            game.screen_map.teleport_to_player()
        game.player.inventory.ui.redraw_top()
        # except Exception as exc:
        #     print("Ошибка загрузки:", exc)
        #     return False
        print("GamaMap - LOAD!")
        return file_p

    def get_list_maps(self):
        files = glob.glob(GAMEMAPS_PATH + '*.pclv', recursive=False)
        return files

    def get_list_num_maps(self):
        files = self.get_list_maps()
        ar = [int(f.split("-")[-1].split(".")[0]) for f in files if "None" not in f]
        return ar

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

    def new_world(self, base_generation=None):
        self.__init__(self.game, self.gen_type, base_generation)
        self.set_structure((-10, -13), structure_start)
        self.game.reinit_player()
        self.game.player.tp_to(config.GameSettings.start_pos)
        self.spawn_gate()


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


def random_creature_selection():
    if not config.GameSettings.creatures:
        return None
    r = random.random()
    if r >= CHUNK_CREATURE_CHANCE:
        return None

    crt = random.choices([Slime, Cow, Snake, Wolf, SlimeBigBoss], [20, 5, 1, 0.7, 0.25], k=1)
    # print("random_creature_selection", crt)
    return crt[0]




# from collections import Counter
# Counter(random.choices(['Slime', 'Cow', 'Wolf', 'SlimeBigBoss'], [20, 5, 0.7, 0.25])[0]
#         for _ in range(100000))
# Counter({'Slime': 77209, 'Cow': 19239, 'Wolf': 2595, 'SlimeBigBoss': 957})
