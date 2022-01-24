from _ast import Tuple
from typing import List, Dict, Any

from units.Creatures import Slime
from ..common import *
from ..Tiles import *
import random
from noise import pnoise2
import pickle
import glob


class GameMap:
    save_slots = 16

    def __init__(self, game, generate_type) -> None:
        self.game = game
        self.gen_type = generate_type
        self.tile_data_size = 4
        self.map_size = [-1, -1]
        self.chunk_arr_width = CHUNK_SIZE * self.tile_data_size
        self.chunk_arr_size = self.tile_data_size * CHUNK_SIZE ** 2
        self.game_map = {}

    def set_vars(self, vrs):
        for k, i in vrs.items():
            self.__dict__[k] = i

    def chunk(self, xy, default=None) :
        res = self.game_map.get(xy, default)
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

    def get_static_tile(self, x, y, default=None):
        chunk = self.chunk(self.to_chunk_xy(x, y))
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i:i + self.tile_data_size]

    def get_static_tile_type(self, x, y, default=None):
        chunk = self.chunk((x // CHUNK_SIZE, y // CHUNK_SIZE), default=default)
        if chunk == default:
            return chunk
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
            chunk[0][i + 1] = state
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

    def del_dinamic_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            chunk[1].remove(obj)
            return True
        return False

    def add_dinamic_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:
            chunk[1].append(obj)
            return True
        return False

    def convert_pos_to_i(self, x, y):
        # cx, cy = x % CHUNK_SIZE, y % CHUNK_SIZE
        # i = (cy * CHUNK_SIZE + cx) * self.tile_data_size
        return ((y % CHUNK_SIZE) * CHUNK_SIZE + (x % CHUNK_SIZE)) * self.tile_data_size

    def get_tile_ttile(self, ttile):
        return [ttile, TILES_SOLIDITY.get(ttile, -1), 0, 0]

    def create_pass_chunk(self, xy):
        # self.game_map[xy] = [bytearray([0]*self.chunk_arr_size), [], []]
        self.game_map[xy] = [[0] * self.chunk_arr_size, [], {}]
        return self.game_map[xy]

    def generate_chunk(self, x, y):
        if self.gen_type == TGENERATE_INFINITE_LANDS:
            return self.generate_chunk_noise_island(x, y)
        return

    def generate_chunk_noise_island(self, x, y):
        static_tiles, dinamic_tiles, group_handlers = self.create_pass_chunk((x, y))
        tile_index = 0
        octaves = 6
        freq_x = 35
        freq_y = 15
        base_x = x * CHUNK_SIZE
        base_y = y * CHUNK_SIZE
        tile_y = base_y  # global tile y (not px)
        for y_pos in range(CHUNK_SIZE):  # local tile y in chunk (not px)
            tile_x = base_x  # global tile x (not px)
            for x_pos in range(CHUNK_SIZE):  # local tile x in chunk (not px)
                tile_type = None
                v = pnoise2(tile_x / freq_x, tile_y / freq_y, octaves, persistence=0.35)
                if v > 0.1:
                    v3 = pnoise2(tile_x / freq_x, (tile_y - 5 - random.randint(0, 1)) / freq_y, octaves,
                                 persistence=0.35)
                    if v3 > 0.10:
                        tile_type = 3  # stone
                        v4 = pnoise2(tile_x / 5, tile_y / 5, 2, persistence=0.85)
                        if v4 > 0.2:
                            tile_type = 4  # blore
                        else:
                            v5 = pnoise2(tile_x / 10, tile_y / 10, 2, persistence=0.6)
                            if v5 > 0.2:
                                tile_type = 5  # granite
                    else:
                        v2 = pnoise2((tile_x + 1) / freq_x, (tile_y - 2 - random.randint(0, 1)) / freq_y, octaves,
                                     persistence=0.35)
                        if v2 > 0.10:
                            tile_type = 2  # dirt
                        else:
                            tile_type = 1  # grass

                            if y_pos > 1 and static_tiles[tile_index - self.chunk_arr_width] == 0:
                                plant_tile_type = random_plant_selection()  # plant
                                if plant_tile_type is not None:
                                    pl_i = tile_index - self.chunk_arr_width
                                    static_tiles[pl_i] = plant_tile_type
                                    static_tiles[pl_i + 1] = TILES_SOLIDITY.get(plant_tile_type, -1)
                                    if random.randint(0, 7) == 1:
                                        dinamic_tiles.append(Slime(self.game, tile_x*TSIZE, tile_y*TSIZE))

                else:
                    # пусто  
                    # ставим растение     
                    if y_pos == CHUNK_SIZE - 1 and \
                            self.get_static_tile(tile_x, tile_y + 1, default=0) == 1:
                        tile_type = random_plant_selection()
                if tile_index >= self.chunk_arr_size:
                    break
                if tile_type is not None:
                    static_tiles[tile_index] = tile_type
                    static_tiles[tile_index + 1] = TILES_SOLIDITY.get(tile_type, -1)
                tile_x += 1
                tile_index += self.tile_data_size
            tile_y += 1
        return static_tiles, dinamic_tiles, group_handlers

    def save_game_map(self, game, num=0):
        file_p = f'data/maps/game_map-{num}.pclv'
        print(f"GamaMap: '{file_p}' - SAVING...")
        if 1 or input("Вы уверены? если да ('t' или 'д') если нет любое другое: ").lower() in ("t", "д"):
            with open(file_p, 'wb') as f:
                d = {"game_map_vars": vars(self), "player_vars": game.player.get_vars()}
                pickle.dump(
                    {"game_map_vars": vars(self), "player_vars": game.player.get_vars(), "game_version": GAME_VERSION},
                    f)
            print("GamaMap - SAVE!")
            return True

    def open_game_map(self, game, num=0):
        file_p = f'data/maps/game_map-{num}.pclv'
        print(f"GamaMap: '{file_p}' - LOADING...")
        if 1 or input("Вы уверены? если да ('t' или 'д') если нет любое другое: ").lower() in ("t", "д"):
            try:
                with open(file_p, 'rb') as f:
                    data = pickle.load(f)
                    version = data.get("game_version", "0.4")
                    if version != GAME_VERSION:
                        return
                    game_map = data["game_map_vars"]
                    self.set_vars(game_map)
                    player = data["player_vars"]
                    game.player.set_vars(player)

                    game.ui.redraw_top()
            except FileNotFoundError:
                print("Такой карты нет!")
                return False
        print("GamaMap - LOAD!")
        return file_p

    def get_list_maps(self):
        path = 'data/maps/'
        files = glob.glob(path + '*.pclv', recursive=False)
        return files

    def get_list_num_maps(self):
        files = self.get_list_maps()
        ar = [int(f.split("-")[1].split(".")[0]) for f in files]
        return ar


def random_plant_selection():
    plant_tile_type = random.choices(['red', 'black', 'green'], [18, 18, 2], k=1)
    plant_tile_type = None
    if random.randint(0, 10) == 0:
        plant_tile_type = 101
    elif random.randint(0, 10) == 0:
        plant_tile_type = 102
    elif random.randint(0, 40) == 0:
        plant_tile_type = 121
    elif random.randint(0, 40) == 0:
        plant_tile_type = 122
    elif random.randint(0, 40) == 0:
        plant_tile_type = 120
    elif random.randint(0, 40) == 0:
        plant_tile_type = 9
    return plant_tile_type
