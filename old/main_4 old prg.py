from pygame.locals import *
import os
import pickle
import random
from time import time

from noise import pnoise2
from pygame.locals import *
from pygame.math import Vector2

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from units.Tiles import *

# INIT GAME ================================================



# screen = pygame.display.set_mode(WINDOW_SIZE, flags=pygame.SHOWN, vsync=2)


# WINDOW_CHUNK_SIZE = (2, 1)
print("WINDOW_CHUNK_SIZE", WINDOW_CHUNK_SIZE)

random.seed(12321)

# INIT TIME ================================================================

clock = pygame.time.Clock()
EVENT_100_MSEC = USEREVENT+1
pygame.time.set_timer(EVENT_100_MSEC, 100, False)

# INIT TEXT ==================================================

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.SysFont("Fenix", 19, )
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

# STRUCTS OF DINAMIC ==========================================


# CLASS GAMEMAP===================================================
def randint(i1, i2):
    pass
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
    return plant_tile_type

class GameMap:
    def __init__(self, generate_type) -> None:
        self.gen_type = generate_type
        self.tile_size = TILE_SIZE
        self.tile_data_size = 4
        self.chunk_size = CHUNK_SIZE
        self.map_size = [-1, -1]
        self.chunk_arr_width = self.chunk_size * self.tile_data_size
        self.chunk_arr_size = self.tile_data_size * self.chunk_size ** 2
        self.game_map = {}

    def chunk(self, xy, default=None):
        res = self.game_map.get(xy, default)
        return res

    def chunk_gen(self, xy):
        index = 0
        chunk = self.chunk(xy)
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                yield index, y, x, chunk[0][index:index+self.tile_data_size]
                index += self.tile_data_size

    def index_gen(self):
        index = 0
        while index < self.chunk_array_size:
            yield index
            index += self.tile_data_size

    def get_static_tile(self, x, y, default=None):        
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size))
        if chunk is None:
            return default
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i:i+self.tile_data_size]

    def get_static_tile_type(self, x, y, default=None):  
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size), default=default)
        if chunk == default:
            return chunk
        i = self.convert_pos_to_i(x, y)
        return chunk[0][i]

    def set_static_tile(self, x, y, tile):
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size))
        if chunk is not None:
            if tile is None:
                tile = [0, 0 ,0 ,0]
            i = self.convert_pos_to_i(x, y)
            chunk[0][i:i+self.tile_data_size] = tile
            return True
        return False

    def set_static_tile_group(self, x, y, group_id):
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i+3] = group_id
            return True
        return False

    def set_static_tile_solidity(self, x, y, sol):
        """Установить прочность тайла"""
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i+1] = sol
            return True
        return False

    def set_static_tile_state(self, x, y, state):
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size))
        if chunk is not None:
            i = self.convert_pos_to_i(x, y)
            chunk[0][i+1] = state
            return True
        return False

    def move_dinamic_obj(self, chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj):
        chunk = self.chunk((new_chunk_x, new_chunk_y))
        if chunk:
            ochunk = self.chunk((chunk_x, chunk_y))
            if ochunk is not None and obj in ochunk[1]:                
                    ochunk[1].remove(obj)
                    chunk[1].append(obj)
                    return True
            # else:
            #     raise Exception(f"Ошибка передвижения динамики. Объект {obj} не находится в чанке {(chunk_x, chunk_y)}")        
            return False
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
                raise Exception(f"Ошибка передвижения динамики. Объект {i, obj} не находится в чанке {(chunk_x, chunk_y)}")        
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
        #cx, cy = x % self.chunk_size, y % self.chunk_size
        #i = (cy * self.chunk_size + cx) * self.tile_data_size        
        return ((y % self.chunk_size) * self.chunk_size + (x % self.chunk_size)) * self.tile_data_size

    def get_tile_ttile(self, ttile):
        return [ttile, TILES_SOLIDITY.get(ttile, -1), 0, 0]

    def set_chunk_arr2(self, arr):
        pass

    def create_pass_chunk(self, xy):
        # self.game_map[xy] = [bytearray([0]*self.chunk_arr_size), [], []]
        self.game_map[xy] = [[0]*self.chunk_arr_size, [], {}]
        return self.game_map[xy]

    def generate_chunk(self, x,y):      
        if self.gen_type == TGENERATE_INFINITE_LANDS:
            return self.generate_chunk_noise_island(x, y)
        return

    def generate_chunk_noise_island(self, x,y):            
        static_tiles, dinamic_tiles, group_handlers = self.create_pass_chunk((x,y))
        tile_index = 0
        octaves = 6
        freq_x = 35
        freq_y = 15
        base_x = x * CHUNK_SIZE
        base_y = y * CHUNK_SIZE
        tile_y = base_y  # global tile y (not px)
        for y_pos in range(CHUNK_SIZE): # local tile y in chunk (not px)            
            tile_x = base_x # global tile x (not px)
            for x_pos in range(CHUNK_SIZE): # local tile x in chunk (not px)
                tile_type = None
                v = pnoise2(tile_x / freq_x, tile_y / freq_y, octaves, persistence=0.35)
                if v > 0.1:
                    v3 = pnoise2(tile_x / freq_x, (tile_y-5-random.randint(0, 1)) / freq_y, octaves, persistence=0.35)
                    if v3 > 0.10:
                        tile_type = 3 # stone
                        v4 = pnoise2(tile_x / 5, tile_y / 5, 2, persistence=0.85)
                        if v4 > 0.2:                    
                            tile_type = 4 # blore
                    else:
                        v2 = pnoise2((tile_x+1) / freq_x, (tile_y-2-random.randint(0, 1)) / freq_y, octaves, persistence=0.35)
                        if v2 > 0.10:
                            tile_type = 2 # dirt                                         
                        else:
                            tile_type = 1 # grass
                            
                            if y_pos > 1 and static_tiles[tile_index-self.chunk_arr_width] == 0:
                                plant_tile_type = random_plant_selection() #plant
                                if plant_tile_type is not None:
                                    pl_i = tile_index-self.chunk_arr_width
                                    static_tiles[pl_i] = plant_tile_type
                                    static_tiles[pl_i+1] = TILES_SOLIDITY.get(plant_tile_type, -1)
                                    
                else:
                    # пусто  
                    # ставим растение     
                    if y_pos == CHUNK_SIZE-1 and\
                        self.get_static_tile(tile_x, tile_y+1, default=0)==1:
                        tile_type = random_plant_selection()            
                    
                if tile_type is not None:
                    static_tiles[tile_index] = tile_type
                    static_tiles[tile_index+1] = TILES_SOLIDITY.get( tile_type, -1)
                tile_x += 1
                tile_index += self.tile_data_size
            tile_y += 1
        return static_tiles, dinamic_tiles, group_handlers

def save_game_map(num=0):
    file_p=f'data/maps/game_map-{num}.pcl'
    print(f"GamaMap: '{file_p}' - SAVING...")
    if input("Вы уверены? если да ('t' или 'д') если нет любое другое: ").lower() in ("t", "д"):
        with open(file_p, 'wb') as f:
            pickle.dump({"game_map": game_map, "inventory": inventory, "player": player}, f)
            print("GamaMap - SAVE!")

def load_game_map(num=0):
    global game_map, inventory, player
    file_p=f'data/maps/game_map-{num}.pcl'
    print(f"GamaMap: '{file_p}' - LOADING...")    
    if input("Вы уверены? если да ('t' или 'д') если нет любое другое: ").lower() in ("t", "д"):
        try:
            with open(file_p, 'rb') as f:
                data = pickle.load(f)
                game_map = data["game_map"]
                inventory = data["inventory"]
                pl = data["player"]
                if type(pl) is PhiscalObject:
                    pl = pl.rect.topleft
                player.rect.topleft = pl
                print("GamaMap - LOAD!")
                redraw_top()
        except FileNotFoundError:
            print("Такой карты нет!")
    return

# gm = GameMap(2)
# gm.generate_chunk_noise_island(0, 0)
# gm.generate_chunk_noise_island(1, 0)
# gm.generate_chunk_noise_island(0, 1)
# gm.generate_chunk_noise_island(1, 1)
# pass
# GENERATING MAP OR CHANK ========================================

TGENERATE_LOAD = 0
TGENERATE_INFINITE = 1
TGENERATE_INFINITE_LANDS = 2
generate_type = 2 # 0:load map,1: autogenerate
game_map: GameMap = GameMap(generate_type)


# HANDLERS GAME OBJECTS ==================================================

def collision_test(rect: pygame.Rect, static_tiles: dict, dynamic_tiles: list=[], first_tile_pos=(0, 0)):
    # rect_x_map, rect_y_map = rect.x // TILE_SIZE, rect. // 
    hit_dynamic_lst = []

    for tile in dynamic_tiles:
        if rect.colliderect(tile):
            hit_dynamic_lst.append(tile)

    hit_static_lst = []
    rect = rect.move(-first_tile_pos[0], -first_tile_pos[1])
    vertexes = rect.topleft, (rect.left, rect.bottom-1), (rect.right-1, rect.top), (rect.right-1, rect.bottom-1)
    
    for vertex in vertexes:
        # координаты угла в перещёте на блоки
        v_xy_map = v_x_map, v_y_map = (vertex[0] // TILE_SIZE, vertex[1] // TILE_SIZE)
        if game_map.gen_type == TGENERATE_LOAD and not(0 <= v_x_map < game_map.map_size[0] and 0 <= v_y_map < game_map.map_size[1]):
            hit_static_lst.append((v_xy_map, -1)) 
        elif static_tiles.get(v_xy_map) in PHYSBODY_TILES:
            hit_static_lst.append((v_xy_map, static_tiles.get(v_xy_map)))
    return hit_static_lst, hit_dynamic_lst

class PhiscalObject:
    def __init__(self, x, y, width, height) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)

    def move(self, movement, static_tiles: dict, dynamic_tiles: list=[], first_tile_pos=(0, 0)):
        collision_types = {'top':False,'bottom':False,'right':False,'left':False}
        mx, my = movement
        self.rect.x += mx
        # блоки с которыми стлкунулись после премещения по оси x (hit_static_lst, hit_dynamic_lst )
        collision_lsts = collision_test(self.rect, static_tiles, dynamic_tiles, first_tile_pos)
        for type_coll in range(2):
            for block in collision_lsts[type_coll]:
                if mx > 0:
                    if type_coll == 0:
                        self.rect.right = block[0][0] * TILE_SIZE + first_tile_pos[0]
                    elif type_coll == 1:
                        self.rect.right = block.left
                    collision_types['right'] = True
                elif mx < 0:
                    if type_coll == 0:
                        self.rect.left = block[0][0] * TILE_SIZE + first_tile_pos[0] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.left = block.right
                    collision_types['left'] = True            
        self.rect.y += my
        # блоки с которыми стлкунулись после премещения по оси y (hit_static_lst, hit_dynamic_lst )
        collision_lsts = collision_test(self.rect, static_tiles, dynamic_tiles, first_tile_pos)
        for type_coll in range(2):
            for block in collision_lsts[type_coll]:
                if my > 0:
                    if type_coll == 0:
                        self.rect.bottom = block[0][1] * TILE_SIZE + first_tile_pos[1]
                    elif type_coll == 1:
                        self.rect.bottom = block.top
                    collision_types['bottom'] = True
                elif my < 0:
                    if type_coll == 0:
                        self.rect.top = block[0][1] * TILE_SIZE + first_tile_pos[1] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.top = block.bottom
                    collision_types['top'] = True     
        return collision_types  

    def draw(self):
        pygame.draw.rect(screen,(255,255,0),self.rect)

# CREATING PLAYER ==========================================================
def set_tile(x, y):
    global pickaxe_time, set_time
    cell = inventory[active_cell]
    if time() - pickaxe_time < 1 or time() - set_time < 0.6 or cell is None:        
        return False
    ttile = inventory[active_cell][0]
    if ttile in STANDING_TILES and game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
        return False
    inventory[active_cell][1] -= 1
    game_map.set_static_tile(x, y, game_map.get_tile_ttile(ttile))
    if inventory[active_cell][1] == 0:
        inventory[active_cell] = None
    choose_active_cell()
    redraw_top()    
    set_time = time()
    return True

def dig_tile(x, y):
    global pickaxe_time, set_time
    tile = game_map.get_static_tile(x, y)    
    if tile is None or tile[1] == -1:
        return 
    d_ttile = game_map.get_static_tile_type(x, y-1)    
    if d_ttile in {101, 102}:
        return False
    ttile = tile[0]
    if ttile == 0:
        return set_tile(x, y)
    sol = tile[1] # прочность
    if time() - set_time < 1 or time() - pickaxe_time < 1 / PICKAXES_SPEED[pickaxe]:
        # время нового удара ещё не подошло
        return False
    pickaxe_time = time()
    if PICKAXES_CAPABILITY[pickaxe] is not None and ttile not in PICKAXES_CAPABILITY[pickaxe]:
        # мы не можем выкопать этой киркой
        return False
    stg = PICKAXES_STRENGTH[pickaxe]
    sol -= stg
    if sol <= 0:
        i = 0
        while i < inventory_size:
            if inventory[i] is None:
                inventory[i] = [ttile, 1]
                redraw_top()
                break
            if inventory[i][1] < cell_size and inventory[i][0] == ttile:
                inventory[i][1] += 1
                redraw_top()
                break
            i += 1
        else:
            print("Перепонен инвентарь", ttile)
        
        game_map.set_static_tile(x, y, None)
    else:
        game_map.set_static_tile_solidity(x, y, sol)
    choose_active_cell()
    return True


def choose_active_cell(cell=-1):
    global active_cell, player_hand_img
    if cell != -1:
        active_cell = cell
    player_hand_img = hand_pass_img
    if inventory[active_cell]:
        player_hand_img = tile_hand_imgs[inventory[active_cell][0]]
    redraw_top()


global player
player = PhiscalObject(0, 0, TILE_SIZE-1, TILE_SIZE-1)    
inventory_size = 16
inventory = [None] * inventory_size
active_cell = 0
cell_size = 100

pickaxe = 1
pickaxe_time = 0
# время последнего удара
set_time = 0
# время последнего установки блока
NUM_KEYS = [K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0]

# GLOBAL VARS================================================================

DIRECTION_VECTORS = [(1, 0), (0, -1), (-1, 0), (0, 1)]

global wind_direction
wind_direction = 2 # 0:right, 1:up, 2:left, 3:down, 

global wind
wind = 0.05 # speed of wind
wind_to_one = 1 / wind

# DRAW UI ==================================================================
global top_surface
top_surface = pygame.Surface(((TILE_SIZE + 7) * inventory_size, TILE_SIZE + 8), pygame.SRCALPHA, 32)
top_bg_color = (82, 82, 91, 150)
def redraw_top():
    top_surface.fill(top_bg_color)
    x = 0
    i = 0
    for i in range(inventory_size):
        color = "#000000"
        if i == active_cell:
            color = "#FFFFFF"
        pygame.draw.rect(top_surface, color, 
            (x, 0, TILE_SIZE + 7, TILE_SIZE + 7), 1)
        cell = inventory[i]
        if cell is not None:
            img = tile_imgs[cell[0]]
            top_surface.blit(img, (x+3, 3))
            res = str(cell[1])
            tx, ty = (x+TILE_SIZE+3-7*len(res), TILE_SIZE-8)
            text = textfont.render(res, False, text_color_dark)
            top_surface.blit(text, (tx + 1, ty + 1))
            text = textfont.render(res, False, text_color_light)
            top_surface.blit(text, (tx, ty))
        x += TILE_SIZE + 7
redraw_top()

global text_fps, true_fps

global info_surface
info_surface = pygame.Surface( (200, 80), pygame.SRCALPHA, 32)

def redraw_info():
    update_fps()
    info_surface.fill(top_bg_color)
    text_fps = textfont_info.render(f" fps: {int(true_fps)}", False, "white")
    text_pos_real = textfont_info.render(f"rpos: {player.rect.x, player.rect.y}", False, "white")
    text_pos = textfont_info.render(f" pos: {player.rect.x//TILE_SIZE, player.rect.y//TILE_SIZE}", False, "white")
    info_surface.blit(text_fps, (8, 5))
    info_surface.blit(text_pos_real, (8, 25))
    info_surface.blit(text_pos, (8, 45))
    
# MAIN LOOP =================================================================

def update_fps():
    global true_fps
    true_fps = clock.get_fps()    

def main():  
    global active_cell, pickaxe
    tact = 0
    true_scroll = [player.rect.x, player.rect.y]

    on_wall = False
    moving_right = False
    moving_left = False
    dig = False 
    dig_pos = None
    punch = False
    punch_tick = 0
    punch_speed = 0.8
    min_hand_space = TILE_SIZE // 1.5
    hand_space = min_hand_space
    num_down = -1

    vertical_momentum= 0
    jump_speed = 10
    jump_count = 0
    max_jump_count = 5
    fall_speed = 0.3 #* (60 / FPS)
    max_fall_speed = 7 #* (60 / FPS)
    player_speed = 4.1 * (WINDOW_SIZE[0] / 700) * (60 / FPS)
    running = True
    air_timer = 0
    choose_active_cell()
    pause = False
    while running:     
        if pause:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == KEYDOWN and event.key == K_u:
                    pause = False
            continue
        display.fill(sky)

        # CALCULATION SCROLL MAP AND PLAYER ==================================

        true_scroll[0] += (player.rect.x - true_scroll[0] - WINDOW_SIZE[0] // 2) / 20
        true_scroll[1] += (player.rect.y - true_scroll[1] - WINDOW_SIZE[1] // 2) / 20
        if game_map.gen_type == TGENERATE_LOAD:
            true_scroll = [max(0, true_scroll[0]), max(0, true_scroll[1])]
            if true_scroll[0] > game_map.map_size[0] * TILE_SIZE - WINDOW_SIZE[0]:
                true_scroll[0] = game_map.map_size[0] * TILE_SIZE - WINDOW_SIZE[0]
        scroll = [int(true_scroll[0]), int(true_scroll[1])]
        # scroll = player.rect.x, player.rect.y

        # LOAD TILES (CHUNKS) AND DRAW OF VIEW WINDOW =========================

        static_tiles = {}
        dinamic_tiles = []
        group_handlers = {}
        scroll_chunk_x = ((scroll[0])//(TILE_SIZE)+ CHUNK_SIZE-1)//CHUNK_SIZE-1
        chunk_y = ((scroll[1])//(TILE_SIZE)+ CHUNK_SIZE-1)//CHUNK_SIZE-1   

        # SHOW DEBUG GRID CHUNKS ++++
        if show_chunk_grid:
            ch_x = scroll_chunk_x*CHUNK_SIZE*TILE_SIZE-scroll[0]
            for cx in range(WINDOW_CHUNK_SIZE[0]):                                                                
                pygame.draw.line(display, CHUNK_BD_COLOR, (ch_x, 0), (ch_x, WINDOW_SIZE[1]))
                ch_x += CHUNK_SIZE_PX
            ch_y = chunk_y*CHUNK_SIZE*TILE_SIZE-scroll[1]
            for cy in range(WINDOW_CHUNK_SIZE[1]):
                pygame.draw.line(display, CHUNK_BD_COLOR, (0, ch_y), (WINDOW_SIZE[0]-1, ch_y))
                ch_y += CHUNK_SIZE_PX
        #-----------------------------

        # SHOW AND LOAD TILES ++++++++
        for cy in range(WINDOW_CHUNK_SIZE[1]):                
            chunk_x = scroll_chunk_x
            for cx in range(WINDOW_CHUNK_SIZE[0]):
                chunk_pos = (chunk_x, chunk_y)    
                chunk = game_map.chunk(chunk_pos)            
                if chunk is None:
                    if game_map.gen_type != TGENERATE_LOAD:
                        # генериует статические и динамичские
                        chunk = game_map.generate_chunk(chunk_x, chunk_y) # [static_lst, dinamic_lst]
                if chunk:
                    # if cx  + cy == 0:
                    #     print("chunk_pos", chunk_pos)
                    dinamic_tiles += chunk[1]
                    group_handlers.update(chunk[2])
                    index = 0        
                    tile_y = chunk_y*CHUNK_SIZE
                    for y in range(game_map.chunk_size):
                        tile_x = chunk_x*CHUNK_SIZE
                        for x in range(game_map.chunk_size):
                            tile = chunk[0][index:index+game_map.tile_data_size]
                            tile_type = tile[0]
                            if tile_type > 0:
                                # print(tile_xy)
                                if tile_type == 201:
                                    img = tile_imgs[tile_type+1][tile[2]-1]
                                else:
                                    img = tile_imgs[tile_type]                                
                                b_pos = (tile_x*TILE_SIZE-scroll[0], tile_y*TILE_SIZE-scroll[1])
                                display.blit(img, b_pos)
                                sol = tile[1]
                                if sol != -1 and sol != TILES_SOLIDITY[tile_type]:
                                    br_i = 2 - int(sol / (TILES_SOLIDITY[tile_type] / 3))
                                    display.blit(break_imgs[br_i], b_pos)

                            if tile_type in PHYSBODY_TILES:                                
                                static_tiles[(tile_x, tile_y)] = tile_type
                            index += game_map.tile_data_size
                            tile_x += 1
                        tile_y += 1

                chunk_x += 1
            chunk_y += 1
     
        # PROCESSING DINAMIC TILES =======================================
        
        for i in range(len(dinamic_tiles)):
            tile = dinamic_tiles[i]            
            tile.update(tact)
            tile.draw(display, scroll)

        # PROCESSING GROUP TILES =======================================

        for tile in group_handlers.values():
            tile.update(tact)
            if show_group_obj:
                display.blit(tile_imgs[151], (tile.x*TILE_SIZE-scroll[0], tile.y*TILE_SIZE-scroll[1]))
           
        # PROCESSING PLAYER ACTIONS =======================================

        player_movement = [0,0]
        if moving_right:
            player_movement[0] += player_speed
        if moving_left:
            player_movement[0] -= player_speed
 
        player_movement[1] += vertical_momentum
        vertical_momentum += fall_speed
        if vertical_momentum > max_fall_speed:
            vertical_momentum = max_fall_speed

        
        collisions = player.move(player_movement, static_tiles)

        if collisions['bottom']:
            air_timer = 0
            jump_count = 0
            vertical_momentum = 0
        else:
            air_timer += 1
        if collisions['top']:
            vertical_momentum = 0
        on_wall = False
        if (collisions['left'] and moving_left) or (collisions['right'] and moving_right):
            if vertical_momentum > 0:
                vertical_momentum = 0
                jump_count = min(max_jump_count, jump_count)
                on_wall = True                
        
        display.blit(player_img, (player.rect.x-scroll[0], player.rect.y-scroll[1]))

        # SHOW PLAYER HAND ===============================================

        pVec = Vector2(player.rect.centerx-scroll[0], player.rect.centery-scroll[1])
        mVec = Vector2(pygame.mouse.get_pos())
        
        hVec = mVec - pVec
        if dig:
            if hVec.length_squared() <= (TILE_SIZE * 2.5) ** 2:
                dig_pos = Vector2(scroll) + mVec
            else: 
                dig_pos = hVec.normalize() * TILE_SIZE * 1.2 + Vector2(player.rect.center)
        if hVec.length_squared() == 0:
            hVec = Vector2(1, 0)
            
        hVec.scale_to_length(hand_space)
        real_hVec = hVec + pVec - Vector2(HAND_SIZE//2, HAND_SIZE//2)

        if num_down != -1:
            choose_active_cell(num_down)
            num_down = -1
            
        display.blit(player_hand_img, real_hVec)
        
        # DIG TILE =======================================================

        if dig:
            # dig = False
            px, py = int(dig_pos.x // TILE_SIZE), int(dig_pos.y // TILE_SIZE)
            
            new_punch = dig_tile(px, py)
            if new_punch is not None:
                display.blit(dig_rect_img, (px * TILE_SIZE-scroll[0], py * TILE_SIZE-scroll[1]))
            if new_punch:
                punch = True
                punch_tick = 0
                hand_space = min_hand_space
        if punch:                
            punch_tick += 1
            if punch_tick < 10:
                hand_space += punch_speed
            elif punch_tick > 20:
                punch = False
                punch_tick = 0
                hand_space = min_hand_space
            else:
                hand_space -= punch_speed
        

        # PROCESSING PYGAME EVENTS =======================================

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key in (K_RIGHT, K_d):
                    moving_right = True
                elif event.key in (K_LEFT, K_a):
                    moving_left = True
                elif event.key in (K_UP, K_w, K_SPACE):
                    on_up = True
                    if on_wall:
                        vertical_momentum = -jump_speed
                        jump_on_wall = True
                    elif air_timer < 6:
                        jump_count += 1
                        vertical_momentum = -jump_speed
                    elif jump_count < max_jump_count:
                        jump_count += 1
                        vertical_momentum = -jump_speed
                elif event.key == K_DOWN:
                    on_down = True                
                elif event.key == K_u:
                    pause = not pause
                elif event.key == K_j:                    
                    pickaxe = 77 if pickaxe == 1 else 1
                elif event.key == K_t:
                    player.rect.center = (0, 0)
                elif event.key == K_o:
                    load_game_map(active_cell)
                elif event.key == K_p:
                    save_game_map(active_cell)
                elif event.key in NUM_KEYS:
                    num_down = NUM_KEYS.index(event.key) 
            elif event.type == KEYUP:
                if event.key in (K_RIGHT, K_d):
                    moving_right = False
                elif event.key in (K_LEFT, K_a):
                    moving_left = False
                elif event.key in (K_UP, K_w, K_SPACE):
                    on_up = False                
                elif event.key == K_DOWN:
                    on_down = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    dig = True
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    dig = False
            elif event.type == MOUSEWHEEL:
                active_cell += event.y
                if active_cell == -1:
                    active_cell = inventory_size - 1
                elif active_cell == inventory_size:
                    active_cell = 0
                choose_active_cell()
            elif event.type == EVENT_100_MSEC:
                if show_info_menu:
                    redraw_info()
         
        # DRAW DISPLAY GAME TO WINDOW ========================================
        display.blit(top_surface, (0, 0))  
        if show_info_menu:      
            display.blit(info_surface, (WINDOW_SIZE[0]-200, 0))

        # pygame.transform.scale(display,(WINDOW_SIZE[0]//1.8, WINDOW_SIZE[1]//1.8)), (100, 100)
        screen.blit(display, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

        tact += 1
    pygame.quit()


if __name__ == '__main__':
    pygame.init()
    main()
