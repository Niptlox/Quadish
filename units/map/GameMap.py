import glob
import pickle
import random

from noise import snoise2 as pnoise2

from units import Items
from units.Items import ItemsTile
from units.Tools import ItemTool
from units.biomes import biome_of_pos
from units.Creatures import Slime, Cow, Wolf
from units.Entity import PhysicalObject
from ..Tiles import *


class GameMap:
    save_slots = 16

    def __init__(self, game, generate_type, base_generation=None) -> None:
        self.game = game
        self.gen_type = generate_type
        self.tile_data_size = 4
        self.map_size = [-1, -1]
        self.chunk_arr_width = CHUNK_SIZE * self.tile_data_size
        self.chunk_arr_size = self.tile_data_size * CHUNK_SIZE ** 2
        self.game_map = {}
        self.base_generation = base_generation
        self.num_save_map = None
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
        # set vars
        for k, i in vrs.items():
            self.__dict__[k] = i

    def get_vars(self):
        d = self.__dict__.copy()
        print("==", d["game_map"][0, 0])
        # === convert dynamic_objs ===
        game_map = {}
        for pos, chunk in d["game_map"].items():
            game_map[pos] = chunk.copy()
            game_map[pos][1] = [(type(obj), obj.get_vars()) for obj in chunk[1]]
        d["game_map"] = game_map
        d.pop("game")
        return d

    def chunk(self, xy, default=None, for_player=False, create_chunk=False):
        res = self.game_map.get(xy, default)
        if res is default and create_chunk:
            res = self.generate_chunk(*xy)
        if res and for_player:
            crt_cash = res[3]
            if self.game.tact > crt_cash[2] + 10 * FPS:
                if crt_cash[1] < 3:
                    crt_cash[2] = self.game.tact
                    dynamic_tiles = res[1]
                    scroll = self.game.screen_map.scroll
                    for tile_xy in crt_cash[0]:
                        x, y = tile_xy[0] * TSIZE, tile_xy[1] * TSIZE
                        if not self.game.screen_map.display_rect.collidepoint(x - scroll[0], y - scroll[1]):
                            Crt = random_creature_selection()
                            if Crt is not None:
                                dynamic_tiles.append(Crt(self.game, (x, y)))
                                crt_cash[1] += 1
                            if crt_cash[1] > 15:
                                break
        return res

    def chunk_gen(self, xy):
        index = 0
        chunk = self.chunk(xy)
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                yield index, y, x, chunk[0][index:index + self.tile_data_size]
                index += self.tile_data_size

    def index_gen(self):
        index = 0
        while index < self.chunk_array_size:
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

    def get_static_tile(self, x, y, default=None, create_chunk=False):
        chunk = self.chunk(self.to_chunk_xy(x, y), create_chunk=create_chunk)
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i:i + self.tile_data_size]

    def get_static_tile_type(self, x, y, default=None):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE))
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i]

    def set_static_tile(self, x, y, tile):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE))
        if chunk is not None:
            if tile is None:
                tile = [0, 0, 0, 0]
            i = self.convert_pos_to_i(x, y)
            chunk[0][i:i + self.tile_data_size] = tile
            return True
        return False

    def set_static_tile_group(self, x, y, group_id):
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

    def move_dinamic_obj(self, chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj, creature=False):
        # print(chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj)
        chunk = self.chunk((new_chunk_x, new_chunk_y))
        if not chunk:
            chunk = self.generate_chunk(new_chunk_x, new_chunk_y)
        ochunk = self.chunk((chunk_x, chunk_y))
        if ochunk is not None and obj in ochunk[1]:
            if creature:
                ochunk[3][1] -= 1
                chunk[3][1] += 1
            ochunk[1].remove(obj)
            chunk[1].append(obj)
            return True
        # else:
        #     raise Exception(f"Ошибка передвижения динамики. Объект {obj} не находится в чанке {(chunk_x, chunk_y)}")

        return

    def move_group_obj(self, chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj):
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
            return False
        return

    def del_group_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        i = obj.id
        if chunk and i in chunk[2]:
            del chunk[2][i]
            return True
        return False

    def add_group_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            chunk[2][obj.id] = obj
            return True
        return False

    def del_dinamic_obj(self, chunk_x, chunk_y, obj, creature=False):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            if creature:
                chunk[3][1] -= 1
            if obj in chunk[1]:
                chunk[1].remove(obj)
            else:
                print("Error !!! del_dinamic_obj", (chunk_x, chunk_y), obj)
            return True
        return False

    def add_dinamic_obj(self, chunk_x, chunk_y, obj, creature=False):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            if creature:
                chunk[3][1] += 1
            chunk[1].append(obj)
            return True
        return False

    def add_item_of_index(self, index, count_items, x, y):
        items = ItemsTile(self.game, index, count_items, (x * TSIZE + random.randint(0, TSIZE - HAND_SIZE), y * TSIZE))
        self.add_dinamic_obj(*self.to_chunk_xy(x, y), items)

    def convert_pos_to_i(self, x, y):
        # cx, cy = x % CHUNK_SIZE, y % CHUNK_SIZE
        # i = (cy * CHUNK_SIZE + cx) * self.tile_data_size
        return ((y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)) * self.tile_data_size

    def get_tile_ttile(self, ttile):
        """тип, прочность, состояние, переменная"""
        return [ttile, TILES_SOLIDITY.get(ttile, -1), 0, 0]

    def create_pass_chunk(self, xy):
        """static tiles; dynamic tiles; group obj; creatures cash \
        (on graund tiles, cnt creatures, last tact generate); climate"""
        #                    0                          1   2   3              4
        self.game_map[xy] = [[0] * self.chunk_arr_size, [], {}, [set(), 0, 0], [0] * (CHUNK_SIZE ** 2)]
        return self.game_map[xy]

    def generate_chunk(self, x, y):
        if self.gen_type == TGENERATE_INFINITE_LANDS:
            return self.generate_chunk_noise_island(x, y)
        return

    def generate_chunk_noise_island(self, x, y):
        res = self.create_pass_chunk((x, y))
        static_tiles, dynamic_tiles, group_handlers, creature_cash, biome_info = res
        on_ground_tiles, cnt_creatures = creature_cash[0], creature_cash[1]
        tile_index = 0
        octaves = 6
        freq_x = 45 * 3.5
        freq_y = 15 * 3.5
        base = self.base_generation
        threshold = -0.3
        lacunarity = 2.4
        base_x = x * CHUNK_SIZE
        base_y = y * CHUNK_SIZE
        tile_y = base_y  # global tile y (not px)
        i = 0
        for y_pos in range(CHUNK_SIZE):  # local tile y in chunk (not px)
            tile_x = base_x  # global tile x (not px)
            for x_pos in range(CHUNK_SIZE):  # local tile x in chunk (not px)
                biome_info[i] = biome_of_pos(tile_x, tile_y)
                tile_type = None
                v = pnoise2(tile_x / freq_x, tile_y / freq_y, octaves, persistence=0.35, base=base,
                            lacunarity=lacunarity)
                if v < threshold:
                    v3 = pnoise2(tile_x / freq_x, (tile_y - 2 - random.randint(0, 1)) / freq_y, octaves,
                                 persistence=0.35, base=base, lacunarity=lacunarity)
                    if v3 < threshold:
                        tile_type = 3  # stone
                        v4 = pnoise2(tile_x / 10, tile_y / 10, 2, persistence=0.55, base=base, lacunarity=1)
                        if v4 < -0.7:
                            tile_type = 4  # blore
                        else:
                            v5 = pnoise2(tile_x / 8, tile_y / 8, 2, persistence=0.35, base=base + 1, lacunarity=1)
                            if v5 < -0.7:
                                tile_type = 5  # granite
                    else:
                        # v2 = pnoise2((tile_x + 1) / freq_x, (tile_y - 2 - random.randint(0, 1)) / freq_y, octaves,
                        #              persistence=0.35, base=base, lacunarity=lacunarity)
                        # if v2 < threshold:
                        tile_type = 2  # dirt
                        if (y_pos > 0 and static_tiles[tile_index - self.chunk_arr_width] == 0) or \
                                (y_pos == 0 and self.get_static_tile(tile_x, tile_y - 1, create_chunk=True)[0] == 0):
                            tile_type = 1  # grass
                            if y_pos > 0:
                                on_ground_tiles.add((tile_x, tile_y))
                                plant_tile_type_state = random_plant_selection(biome_info[i][0])  # plant
                                if plant_tile_type_state is not None:
                                    plant_tile_type, state = plant_tile_type_state
                                    pl_i = tile_index - self.chunk_arr_width
                                    static_tiles[pl_i] = plant_tile_type
                                    static_tiles[pl_i + 1] = TILES_SOLIDITY.get(plant_tile_type, -1)
                                    static_tiles[pl_i + 2] = state
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
                            static_tiles[tile_index+2] = tile_type_state[1]
                if tile_index >= self.chunk_arr_size:
                    break
                if tile_type is not None:
                    static_tiles[tile_index] = tile_type
                    static_tiles[tile_index + 1] = TILES_SOLIDITY.get(tile_type, -1)
                tile_x += 1  # v28557
                tile_index += self.tile_data_size
                i += 1
            tile_y += 1
        creature_cash[1] = cnt_creatures
        return res

    def save_game_map(self, game, num=0):
        file_p = f'data/maps/game_map-{num}.pclv'
        print(f"GamaMap: '{file_p}' - SAVING...")
        self.num_save_map = num
        try:
            data = {"game_map_vars": self.get_vars(), "player_vars": game.player.get_vars(),
                     "game_version": GAME_VERSION, "game_tact": game.tact}
            t = pickle.dumps(data)
            with open(file_p, 'wb') as f:
                f.write(t)
            print("GamaMap - SAVE!")
            self.game.ui.new_sys_message(f"Карта сохранена #{num}")
        except Exception as exc:
            print("Ошибка сохранения:", exc)
            self.game.ui.new_sys_message(f"Ошибка {exc}")
            return False
        finally:


            return True

    def open_game_map(self, game, num=0):
        file_p = f'data/maps/game_map-{num}.pclv'
        self.num_save_map = num
        print(f"GamaMap: '{file_p}' - LOADING...")
        try:
            with open(file_p, 'rb') as f:
                data = pickle.load(f)
            version = data.get("game_version", "0.4")
            if version != GAME_VERSION:
                return
            game_map = data["game_map_vars"]
            game.game_map.set_vars(game_map)
            player = data["player_vars"]
            game.player.set_vars(player)
            game.tact = data.get("game_tact", 0)
            print(game.player.rect.center)
            if abs(game.player.rect.x) > 10000 or abs(game.player.rect.y) > 10000:
                game.screen_map.teleport_to_player()
            game.ui.redraw_top()
        except Exception as exc:
            print("Ошибка загрузки:", exc)
            return False
        print("GamaMap - LOAD!")
        return file_p

    def get_list_maps(self):
        path = 'data/maps/'
        files = glob.glob(path + '*.pclv', recursive=False)
        return files

    def get_list_num_maps(self):
        files = self.get_list_maps()
        ar = [int(f.split("-")[1].split(".")[0]) for f in files if "None" not in f]
        return ar


def random_plant_selection(biome = None):
    if random.randint(0, 5) == 0:
        plants = {101: 0.1, 102: 0.1, 120: 0.05}
        if biome == 0:
            plants = {101: 0.1, 103: 0.1}
        plant_tile_type = random.choices(list(plants.keys()), list(plants.values()), k=1)[0]
            
        if plant_tile_type == 101:
            return plant_tile_type, random.randint(0, 3)
        return plant_tile_type, 0
    return None


def random_creature_selection():
    crt = random.choices([None, Slime, Cow, Wolf], [90, 10, 5, 5], k=1)
    return crt[0]


