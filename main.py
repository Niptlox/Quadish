import os
from pygame.display import update

from pygame.event import event_name
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import math
import random
from copy import deepcopy

from noise import snoise2, pnoise2

import pygame
from pygame.locals import *

# INIT GAME ================================================

DEBUG = True
# DEBUG = False
WINDOW_SIZE = (2200, 1100)
WINDOW_SIZE = (700*2, 400*2)
FPS = 120

pygame.init() # initiate pygame
pygame.display.set_caption('Pygame Window')
screen = pygame.display.set_mode(WINDOW_SIZE, flags=pygame.SHOWN, vsync=2)

display = pygame.Surface(WINDOW_SIZE)

TILE_SIZE = 40
# TILE_SIZE = 16
# TILE_SIZE = 8
TILE_RECT = (TILE_SIZE, TILE_SIZE)

CHUNK_SIZE = 16

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 1, \
    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 1
# WINDOW_CHUNK_SIZE = (3, 3)
print("WINDOW_CHUNK_SIZE", WINDOW_CHUNK_SIZE)

random.seed(12321)

# INIT TIME ================================================================

clock = pygame.time.Clock()
EVENT_100_MSEC = USEREVENT+1
pygame.time.set_timer(EVENT_100_MSEC, 100, False)

# INIT TEXT ==================================================

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.SysFont("Fenix", 19)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10)

# texframe = font.render(text, False, text_color)
text_color = "#1C1917"
text_color_dark = "#1C1917"
text_color_light = "#F5F5F4"

# STRUCTS OF DINAMIC ==========================================

cloud_struct = [["my_x, my_y"], [["tile_x, tile_y, density(0;1)"],...]]

# CREATING TILE IMAGES ========================================

BORDER_COLOR = "#1C1917"
def create_tile_image(color, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    img = pygame.Surface(size)
    img.fill(bd_color)
    pygame.draw.rect(img, color, ((bd, bd), (size[0]-bd*2, size[0]-bd*2)), border_radius=bd*2)
    return img


COLORKEY = (0, 255, 0)
sky = "#A5F3FC"

player_img = create_tile_image("#E7E5E4", bd=2)

dirt_img = create_tile_image("#694837")

grass_img = create_tile_image("#16A34A")

stone_img = create_tile_image("#57534E")

blore_img = create_tile_image("#155E75") # blue ore

bush_img = pygame.image.load("data/sprites/tiles/bush.png")
bush_img = pygame.transform.scale(bush_img, TILE_RECT)

smalltree_img = pygame.image.load("data/sprites/tiles/small_tree.png").convert()
smalltree_img = pygame.transform.scale(smalltree_img, TILE_RECT)
smalltree_img.set_colorkey(COLORKEY)

cloud_img = create_tile_image("#CBD5E1")
cloud_img_2 = create_tile_image("#94A3B8")
cloud_img_3 = create_tile_image("#64748B")
cloud_imgs = [cloud_img,cloud_img_2,cloud_img_3]

group_img = pygame.image.load("data/sprites/tiles/group.png")
group_img = pygame.transform.scale(group_img, TILE_RECT)
group_img.set_colorkey(COLORKEY)


chunk_img = create_tile_image(sky, bd=1, size=(CHUNK_SIZE*TILE_SIZE, CHUNK_SIZE*TILE_SIZE), bd_color="red")

tile_imgs = {1: grass_img, 
             2: dirt_img, 
             3: stone_img,
             4: blore_img,
             101: bush_img,
             102: smalltree_img,
             151: group_img,
             201: cloud_img,
             202: cloud_img_2,
             203: cloud_img_3,             
             }
count_tiles = len(tile_imgs)
PHYSBODY_TILES = (1, 2, 3, 4)

# CLASS GAMEMAP===================================================

def random_plant_selection():
    plant_tile_type = None
    if random.randint(0, 10) == 0:
        plant_tile_type = 101
    elif random.randint(0, 10) == 0:
        plant_tile_type = 102
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
        chunk = self.chunk((x // self.chunk_size, y // self.chunk_size), default=default)
        if chunk == default:
            return chunk
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
        if chunk:
            ochunk = self.chunk((chunk_x, chunk_y))
            if ochunk is not None and obj in ochunk[2]:
                    ochunk[2].remove(obj)
                    chunk[2].append(obj)
                    return True
            else:
                raise Exception(f"Ошибка передвижения динамики. Объект {obj} не находится в чанке {(chunk_x, chunk_y)}")        
            return False
        return

    def del_group_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk and obj in chunk[2]:        
            chunk[2].remove(obj)                    
            return True
        return False

    def add_group_obj(self, chunk_x, chunk_y, obj):
        chunk = self.chunk((chunk_x, chunk_y))
        if chunk:        
            chunk[2].append(obj)                    
            return True
        return False

    def convert_pos_to_i(self, x, y):
        #cx, cy = x % self.chunk_size, y % self.chunk_size
        #i = (cy * self.chunk_size + cx) * self.tile_data_size        
        return ((y % self.chunk_size) * self.chunk_size + (x % self.chunk_size)) * self.tile_data_size

    def set_chunk_arr2(self, arr):
        pass

    def create_pass_chunk(self, xy):
        # self.game_map[xy] = [bytearray([0]*self.chunk_arr_size), [], []]
        self.game_map[xy] = [[0]*self.chunk_arr_size, [], []]
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
        # cloud_objs = [] # objects of class Cloud
        cloud_tiles = {} # position tile cloud: object of class Cloud
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
                                    static_tiles[tile_index-self.chunk_arr_width] = plant_tile_type
                else:
                    # пусто  
                    # ставим растение     
                    if y_pos == CHUNK_SIZE-1 and\
                        self.get_static_tile(tile_x, tile_y+1, default=0)==1:
                        tile_type = random_plant_selection()            
                    if tile_type is None:
                        # ставим облака
                        v201 = pnoise2(tile_x / 15, (tile_y) / 10-20, 5, persistence=0.3)
                        # if 0 <= x_pos <= 2 and 0 <= y_pos <= 2 and x == 0 and y == 0:
                        if v201 > 0.33:
                            tile_type = 201 # cloud_1
                            o_tile_index = tile_index - self.tile_data_size if tile_index % self.chunk_arr_width > 0 else -1
                            if o_tile_index in cloud_tiles:
                                cloud_obj = cloud_tiles[o_tile_index]                                
                            else:                            
                                cloud_obj = Cloud((tile_x, tile_y), (x, y))
                                group_handlers.append(cloud_obj)
                            cloud_tiles[tile_index] = cloud_obj
                            cloud_obj.add_to_line(tile_x, tile_y, 1) # x, y, weight                
                if tile_type is not None:
                    static_tiles[tile_index] = tile_type
                tile_x += 1
                tile_index += self.tile_data_size
            tile_y += 1
        return static_tiles, dinamic_tiles, group_handlers

# gm = GameMap(2)
# gm.generate_chunk_noise_island(0, 0)
# gm.generate_chunk_noise_island(1, 0)
# gm.generate_chunk_noise_island(0, 1)
# gm.generate_chunk_noise_island(1, 1)
# pass
# GENERATING MAP OR CHANK ========================================

game_map = [['1','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['0','0','0','0','0','0','0','0','0','0','0','0','2','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['0','0','0','3','3','0','0','0','0','0','0','0','1','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['0','0','0','0','0','0','0','2','2','2','2','2','1','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0',"0","0","0","0"]*4,
            ['2','2','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0','2','2',"0","0","0","0"]*4,
            ['1','1','2','3','3','2','2','2','2','2','2','2','1','2','2','2','2','1','1',"1","1","1","2"]*4,
            ['1','1','1','3','3','1','1','1','1','1','1','1','1','1','1','1','1','1','1',"1","1","1","2"]*4,
            ['1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1',"1","1","1","2"]*4,
            ['1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1','1',"1","1","1","2"]*4,
            ['1','2','1','0','1','1','1','2','1','2','1','1','2','1','0','0','2','0','1',"1","1","1","2"]*4,
            ['1','0','1','2','1','2','1','1','1','0','1','1','0','1','1','1','1','1','1',"1","1","1","2"]*4]
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

class Cloud:
    def __init__(self, pos, chunk_pos) -> None:
        self.x, self.y = pos # left x
        self.rx = self.x # right x        
        self.tiles_w = [] # объемы(состояние) тайлов в облаке
        self.last_tact_update = 0
        self.chunk_x, self.chunk_y = chunk_pos
        self.tiles_count = 0 # ширина облака
        

    def update(self, tact):
        if self.tiles_count > 0:
            if tact - self.last_tact_update > wind_to_one:
                self.last_tact_update = tact
                wind_vector_x = DIRECTION_VECTORS[wind_direction][0]
                i = 0
                for x in range(self.x, self.rx+1):
                    i += 1
                    tile_type = game_map.get_static_tile_type(x, self.y, 0)
                    if tile_type != 201:
                        # головыу остовляем, хвост отрезвем @### N###
                        if i < self.tiles_count:                            
                            cloud = None
                            ci = i + 1
                            for cx in range(x + 1, self.rx+1):
                                if cloud is None:                                    
                                    if game_map.get_static_tile_type(cx, self.y, 0) is not 0:
                                        cloud = Cloud((cx, self.y), (cx // game_map.chunk_size, self.chunk_y))
                                        game_map.add_group_obj(cloud.chunk_x, cloud.chunk_y, cloud)
                                        cloud.add_to_line(cx, self.y, self.tiles_w[ci-1])
                                else:                                
                                    cloud.add_to_line(cx, self.y, self.tiles_w[ci-1])
                                ci += 1
                                print(ci)                                                                                            
                            
                        self.rx = x - 1                            
                        if not self.set_tiles_count(i - 1):
                            return
                        del self.tiles_w[i:]
                        break
                # if 1:
                #     pass
                if wind_vector_x > 0:                    
                    # wind ------>
                    if game_map.get_static_tile_type(self.rx + 1, self.y) is 0:
                        self.rx += 1
                        self.x += 1
                        game_map.set_static_tile(self.rx, self.y, [201, self.tiles_w[-1], 0, 0])                        
                        game_map.set_static_tile(self.x - 1, self.y, None)
                elif wind_vector_x < 0:                   
                    # wind <------- 
                    if game_map.get_static_tile_type(self.x - 1, self.y) is 0:
                        self.rx -= 1
                        self.x -= 1
                        game_map.set_static_tile(self.x, self.y, [201, self.tiles_w[-1], 0, 0])                        
                        game_map.set_static_tile(self.rx + 1, self.y, None)


                chunk_x = self.x // game_map.chunk_size
                if chunk_x != self.chunk_x:
                    game_map.move_group_obj(self.chunk_x, self.chunk_y, chunk_x, self.chunk_y, self)
                    self.chunk_x = chunk_x

    def add_to_line(self, tile_x, tile_y, weight) -> bool:        
        if self.y != tile_y:
            return False                
        tile = [tile_x, tile_y, weight]
        self.rx = max(self.rx, tile_x)
        self.tiles_w.append(weight)
        
        self.tiles_count += 1
        return True

    def set_tiles_count(self, count):
        self.tiles_count = count
        if count <= 0:
            game_map.del_group_obj(self.chunk_x, self.chunk_y, self)
            return False
        return True

            
# CREATING PLAYER ==========================================================

def dig_tile(x, y):
    tile = game_map.get_static_tile_type(x, y, 0)    
    if tile == 0:
        return
    i = 0
    while i < inventory_size:
        if inventory[i] is None:
            inventory[i] = [tile, 1]
            redraw_top()
            break
        if inventory[i][1] < cell_size and inventory[i][0] == tile:
            inventory[i][1] += 1
            redraw_top()
            break
        i += 1
    else:
        print("Перепонен инвентарь", tile)
    
    game_map.set_static_tile(x, y, None)

global player
player = PhiscalObject(0, 0, TILE_SIZE-1, TILE_SIZE-1)    
inventory_size = 16
inventory = [None] * inventory_size
cell_size = 100

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
        pygame.draw.rect(top_surface, "#000000", 
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
    text_pos = textfont_info.render(f" pos: {player.rect.x//game_map.tile_size, player.rect.y//game_map.tile_size}", False, "white")
    info_surface.blit(text_fps, (8, 5))
    info_surface.blit(text_pos_real, (8, 25))
    info_surface.blit(text_pos, (8, 45))
    
# MAIN LOOP =================================================================

def update_fps():
    global true_fps
    true_fps = clock.get_fps()    

def main():    
    tact = 0
    true_scroll = [player.rect.x, player.rect.y]
    on_wall = False
    jump_on_wall = False
    moving_right = False
    moving_left = False
    dig = False 
    on_up = False
    on_down = False
    vertical_momentum= 0
    jump_speed = 10
    jump_count = 0
    max_jump_count = 5
    fall_speed = 0.3 #* (60 / FPS)
    max_fall_speed = 7 #* (60 / FPS)
    player_speed = 4.1 * (WINDOW_SIZE[0] / 700) * (60 / FPS)
    running = True
    air_timer = 0
    while running:     
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
        group_handlers = []
        scroll_chunk_x = ((scroll[0])//(TILE_SIZE)+ CHUNK_SIZE-1)//CHUNK_SIZE-1
        chunk_y = ((scroll[1])//(TILE_SIZE)+ CHUNK_SIZE-1)//CHUNK_SIZE-1   
        for cy in range(WINDOW_CHUNK_SIZE[1]):                
            chunk_x = scroll_chunk_x
            for cx in range(WINDOW_CHUNK_SIZE[0]):
                if DEBUG:
                    display.blit(chunk_img, (chunk_x*CHUNK_SIZE*TILE_SIZE-scroll[0], chunk_y*CHUNK_SIZE*TILE_SIZE-scroll[1]))
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
                    group_handlers += chunk[2]            
                    index = 0        
                    tile_y = chunk_y*CHUNK_SIZE
                    for y in range(game_map.chunk_size):
                        tile_x = chunk_x*CHUNK_SIZE
                        for x in range(game_map.chunk_size):
                            tile = chunk[0][index:index+game_map.tile_data_size]
                            tile_type = tile[0]
                            if tile_type > 0:
                                # print(tile_xy)
                                display.blit(tile_imgs[tile_type], (tile_x*TILE_SIZE-scroll[0], tile_y*TILE_SIZE-scroll[1]))
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

        # PROCESSING GROUP TILES =======================================

        for i in range(len(group_handlers)):
            tile = group_handlers[i]            
            tile.update(tact)            
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
        
        if dig:
            px, py = player.rect.centerx // TILE_SIZE, player.rect.centery // TILE_SIZE
            if moving_right:
                dig_tile(px + 1, py)
            if moving_left:
                dig_tile(px - 1, py)
            if on_down:
                dig_tile(px, py + 1)
            if on_up:
                dig_tile(px, py - 1)


        display.blit(player_img, (player.rect.x-scroll[0], player.rect.y-scroll[1]))


        # PROCESSING PYGAME EVENTS =======================================

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_RIGHT:
                    moving_right = True
                elif event.key == K_LEFT:
                    moving_left = True
                elif event.key == K_UP:
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
                elif event.key in (K_LCTRL, K_RCTRL):
                    dig = True
                    
            elif event.type == KEYUP:
                if event.key == K_RIGHT:
                    moving_right = False
                elif event.key == K_LEFT:
                    moving_left = False
                elif event.key == K_UP:
                    on_up = False                
                elif event.key == K_DOWN:
                    on_down = False
                elif event.key in (K_LCTRL, K_RCTRL):
                    dig = False
            elif event.type == EVENT_100_MSEC:
                redraw_info()
         
        # DRAW DISPLAY GAME TO WINDOW ========================================
        display.blit(top_surface, (0, 0))        
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
