import os

from pygame.event import event_name
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import math
import random
from copy import deepcopy

from noise import snoise2, pnoise2

import pygame
from pygame.locals import *

# INIT GAME ================================================

WINDOW_SIZE = (700*2, 400*2)
FPS = 60

pygame.init() # initiate pygame
pygame.display.set_caption('Pygame Window')

screen = pygame.display.set_mode(WINDOW_SIZE, flags=pygame.SHOWN, vsync=2)

display = pygame.Surface(WINDOW_SIZE)

TILE_SIZE = 48
# TILE_SIZE = 8
TILE_RECT = (TILE_SIZE, TILE_SIZE)

CHUNK_SIZE = 16

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 2, \
    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 2

print("WINDOW_CHUNK_SIZE", WINDOW_CHUNK_SIZE)

# INIT TEXT ==================================================

pygame.font.init()
# textfont = pygame.font.SysFont('Harrington', 18)
textfont = pygame.font.SysFont('Goudy Stout', 18)
# texframe = font.render(text, False, text_color)
text_color = "#374151"

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

chunk_img = create_tile_image(sky, bd=1, size=(CHUNK_SIZE*TILE_SIZE, CHUNK_SIZE*TILE_SIZE), bd_color="red")

tile_imgs = {1: grass_img, 
             2: dirt_img, 
             3: stone_img,
             4: blore_img,
             101: bush_img,
             102: smalltree_img,
             201: cloud_img,
             202: cloud_img_2,
             203: cloud_img_3,             
             }
count_tiles = len(tile_imgs)
PHYSBODY_TILES = (1, 2, 3, 4)


# GENERATING MAP OR CHANK ========================================

def static_tile_of_game_map(x, y, default=None):
    cx = x//CHUNK_SIZE
    cy = y//CHUNK_SIZE    
    chunk = game_map.get((cx, cy))
    if chunk:
        return chunk[0][y % CHUNK_SIZE][x % CHUNK_SIZE]
    else:
        return default

def set_static_tile(x, y, tile_type):
    cx = x//CHUNK_SIZE
    cy = y//CHUNK_SIZE    
    chunk = game_map.get((cx, cy))
    if chunk:        
        chunk[0][y % CHUNK_SIZE][x % CHUNK_SIZE] = tile_type
        # assert tile_type != 0 
        return tile_type
    else:      
        # assert x > 4
        return 

def move_dinamic_obj(chunk_x, chunk_y, new_chunk_x, new_chunk_y, obj):
    chunk = game_map.get((new_chunk_x, new_chunk_y))
    if chunk:
        if game_map[(chunk_x, chunk_y)][1] and obj in game_map[(chunk_x, chunk_y)][1]:
            game_map[(chunk_x, chunk_y)][1].remove(obj)
        chunk[1].append(obj)

def random_plant_selection():
    plant_tile_type = None
    if random.randint(0, 10) == 0:
        plant_tile_type = 101
    elif random.randint(0, 10) == 0:
        plant_tile_type = 102
    return plant_tile_type

def generate_chunk(x, y):
    if map_generate_type == TGENERATE_INFINITE:
        return generate_chunk_flat(x,y)
    elif map_generate_type == TGENERATE_INFINITE_LANDS:
        return generate_chunk_noise_island(x,y) #generate_chunk_island(x,y)

def generate_chunk_flat(x,y):    
    static_tiles = [[0]*CHUNK_SIZE for i in range(CHUNK_SIZE)]
    dinamic_tiles = []
    i = 0
    m_a_g = [None] * CHUNK_SIZE
    for y_pos in range(CHUNK_SIZE-1, -1, -1):        
        for x_pos in range(CHUNK_SIZE):
            tile_x = x * CHUNK_SIZE + x_pos
            tile_y = y * CHUNK_SIZE + y_pos
            tile_type = 0 # nothing
            if tile_y > 10:
                tile_type = 2 # dirt
            elif tile_y == 10:
                tile_type = random.randint(0, 1) # grass
                m_a_g[x_pos] = tile_type
            elif tile_y == 9:
                if random.randint(1,5) == 1 and m_a_g[x_pos] is not None:
                    tile_type = m_a_g[x_pos] # plant
            if tile_type != 0:
                static_tiles[y_pos][x_pos] = tile_type
            i += 1
    return static_tiles, dinamic_tiles

def generate_chunk_island(x,y):    
    static_tiles = [[0]*CHUNK_SIZE for i in range(CHUNK_SIZE)]    
    dinamic_tiles = []
    i = 0
    for y_pos in range(CHUNK_SIZE):        
        for x_pos in range(CHUNK_SIZE):
            if random.randint(1,CHUNK_SIZE**2//16) == 1:
                w = random.randint(5,15)
                h = math.ceil(w / 2)
                island_edges = ((x_pos, y_pos), (x_pos + w, y_pos), (x_pos+w, y_pos+ h), (x_pos, y_pos+h))
                for edge in island_edges:
                    if y_pos + edge[1] >= CHUNK_SIZE or x_pos + edge[0] >= CHUNK_SIZE:
                        continue
                    if static_tiles[edge[1]][edge[0]] != 0:    
                        break
                else:
                    if static_tiles[y_pos][x_pos] == 0:
                        for iy in range(h):
                            if y_pos + iy >= CHUNK_SIZE:
                                break                            
                            for ix in range(iy, w - iy * 2 + iy):
                                if x_pos + ix >= CHUNK_SIZE:
                                    break
                                if iy == 0 and y_pos > 0:
                                    d_tile_type = None
                                    if random.randint(1, 20) == 1:
                                        d_tile_type = 101
                                    elif random.randint(1, 20) == 1:
                                        d_tile_type = 102
                                    # if d_tile_type != 0:
                                    if y_pos > 1:
                                        if static_tiles[y_pos + iy - 2][x_pos + ix] < 100:
                                            if d_tile_type is None:
                                                d_tile_type = 0
                                        else:
                                            if d_tile_type is not None:
                                                d_tile_type = 0
                                            
                                    if d_tile_type is not None:
                                        static_tiles[y_pos + iy - 1][x_pos + ix] = d_tile_type


                                tile_type = 2 # dirt
                                if iy == 0:
                                    tile_type = 1 # grass
                                if iy > 2:
                                    tile_type = 3 # stone
                                    if random.randint(1, 10) == 1:
                                        tile_type = 4 # blore                                        
                                static_tiles[y_pos + iy][x_pos + ix] = tile_type
    return static_tiles, dinamic_tiles

# генерация чанка с островами на основе шумов перлинга
def generate_chunk_noise_island(x,y):    
    static_tiles = [[0]*CHUNK_SIZE for i in range(CHUNK_SIZE)]    
    dinamic_tiles = []
    
    octaves = 6
    freq_x = 35
    freq_y = 15
    # cloud_objs = [] # objects of class Cloud
    cloud_tiles = {} # position tile cloud: object of class Cloud
    for y_pos in range(CHUNK_SIZE): # local tile y in chunk (not px)
        for x_pos in range(CHUNK_SIZE): # local tile x in chunk (not px)
            tile_type = None
            tile_x = x * CHUNK_SIZE + x_pos # global tile x (not px)
            tile_y = y * CHUNK_SIZE + y_pos # global tile y (not px)

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
                        if y_pos > 1 and static_tiles[y_pos - 1][x_pos] == 0:
                            plant_tile_type = random_plant_selection() #plant
                            if plant_tile_type is not None:
                                static_tiles[y_pos-1][x_pos] = plant_tile_type
            else:
                # пусто  
                # ставим растение     
                if y_pos == CHUNK_SIZE-1 and\
                    static_tile_of_game_map(tile_x, tile_y+1, default=0)==1:
                    tile_type = random_plant_selection()            
                if tile_type is None:
                    # ставим облака
                    v201 = pnoise2(tile_x / 15, (tile_y) / 10-20, 5, persistence=0.3)
                    # if 0 <= x_pos <= 1 and y_pos == 0 and x == 0 and y == 0:
                    if v201 > 0.33:
                        tile_type = 201 # cloud_1
                        for vector in ((-1, 0),):# (0, -1)):
                            o_tile_pos = (x_pos + vector[0], y_pos + vector[1])
                            if o_tile_pos in cloud_tiles:
                                cloud_obj = cloud_tiles[o_tile_pos]
                                break
                        else:                            
                            cloud_obj = Cloud((tile_x * TILE_SIZE, tile_y * TILE_SIZE), [], (x, y))
                            dinamic_tiles.append([201, cloud_obj])
                        cloud_tiles[(x_pos, y_pos)] = cloud_obj
                        cloud_obj.append(tile_x, tile_y, 1) # x, y, weight                
            if tile_type is not None:
                static_tiles[y_pos][x_pos] = tile_type
    return static_tiles, dinamic_tiles

def create_game_map(nums_game_map):
    map_size = [len(nums_game_map[0]), len(nums_game_map)]
    chunk_map_size = math.ceil(map_size[0] / CHUNK_SIZE), math.ceil(map_size[1] / CHUNK_SIZE)
    game_map = {}    
    for chunk_y in range(chunk_map_size[1]):
        for chunk_x in range(chunk_map_size[0]):
            game_map[(chunk_x, chunk_y)] = [[[int(nums_game_map[y][x]) 
                for x in range(chunk_x * CHUNK_SIZE, min((chunk_x + 1) * CHUNK_SIZE, map_size[0]))] 
                for y in range(chunk_y * CHUNK_SIZE, min((chunk_y + 1) * CHUNK_SIZE, map_size[1]))],
                []] # static, dinamic
            print((chunk_x, chunk_y))
            print(*game_map[(chunk_x, chunk_y)], sep="\n")
            pass
    return game_map, map_size, chunk_map_size


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
map_generate_type = 2 # 0:load map,1: autogenerate
if map_generate_type == TGENERATE_LOAD:
    game_map, map_size, chunk_map_size = create_game_map(game_map)
    map_rect = [0, 0] + map_size
else:
    game_map = {}

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
        if map_generate_type == TGENERATE_LOAD and not(0 <= v_x_map < map_size[0] and 0 <= v_y_map < map_size[1]):
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
    def __init__(self, pos, tiles, chunk) -> None:
        self.x, self.y = pos
        self.tiles = tiles
        self.tiles_range = []
        self.height = len(tiles)
        self.last_tact_update = 0
        self.chunk = chunk

    def update(self, tact):
        if self.tiles:
            if tact - self.last_tact_update > 1 / wind:
                self.last_tact_update = tact
                # сдвигем облако на один блок
                wind_vectorx = 0
                if wind_direction == 1:
                    wind_vectorx = 1
                elif wind_direction == 3:
                    wind_vectorx = -1
                last_chunk_x = self.x // CHUNK_SIZE_PX
                self.x += wind_vectorx
                chunk_x = self.x // CHUNK_SIZE_PX
                chunk_y = self.y // CHUNK_SIZE_PX
                if chunk_x != last_chunk_x:
                    move_dinamic_obj(last_chunk_x, chunk_y, chunk_x, chunk_y, (201, self))
                for y in range(self.height):
                    x_left = None
                    x_right = None   
                    x_left_i, x_right_i = 0, 0
                    for i in range(len(self.tiles[y])):
                        tx, ty, tw = self.tiles[y][i]
                        if x_left is None or tx < x_left:
                            x_left = tx
                            x_left_i = i
                        if x_right is None or tx > x_right:
                            x_right = tx
                            x_right_i = i
                    if wind_direction == 1:
                        # cloud left move to right ->
                        test = static_tile_of_game_map(x_right + 1, ty, -1)
                        if test > 0:
                            w = self.tiles[y][x_right_i][2]
                            # for i in range(0, )
                            if w < 3:
                                w += 1
                                self.tiles[y][x_right_i][2] = w
                                set_static_tile(x_right, ty, 200 + w)
                        else:
                            w = self.tiles[y][x_left_i][2]
                            self.tiles[y][x_left_i][0] = x_right + 1                             
                            set_static_tile(x_right + 1, ty, 200+ w) # set new
                        set_static_tile(x_left, ty, 0) # del old
                    elif wind_direction == 3:                    
                        # cloud right
                        self.tiles[y][x_right_i][0] = x_left - 1 
                        set_static_tile(x_left - 1, ty, 201) # set new
                        set_static_tile(x_right, ty, 0) # del old
                        assert not static_tile_of_game_map(x_right, ty), "Пустая ячейка должна быть"

    def append(self, tile_x, tile_y, weight):
        tile = [tile_x, tile_y, weight]
        y = tile_y - self.y // TILE_SIZE
        if y > (self.height-1):
            self.tiles.append([]*(y-self.height+1))
            self.height = y + 1
        self.tiles[y].append(tile)

            
# CREATING PLAYER ==========================================================

def dig_tile(x, y):
    tile = static_tile_of_game_map(x, y)    
    resources[tile] = resources.get(tile, 0) + 1
    set_static_tile(x, y, 0)
    redraw_top()

global player
player = PhiscalObject(0, 0, TILE_SIZE-1, TILE_SIZE-1)    
resources = {}

# GLOBAL VARS================================================================

DIRECTION_VECTORS = [(1, 0), (0, -1), (-1, 0), (0, 1)]

global wind_direction
wind_direction = 1 # 1:right, 2:up, 3:left, 4:down, 

global wind
wind = 0.05 # speed of wind

# DRAW UI ==================================================================
top_surface = pygame.Surface(((TILE_SIZE + 1) * count_tiles, TILE_SIZE // 2 * 3))

def redraw_top():
    top_surface.fill("#E5E5E5")

    x = 0
    for k, img in tile_imgs.items():
        top_surface.blit(img, (x, 0))
        res = resources.get(k, 0)
        text = textfont.render(str(res), False, text_color)
        top_surface.blit(text, (x, TILE_SIZE + 1))
        x += TILE_SIZE + 1
redraw_top()

# MAIN LOOP =================================================================

def main():    
    clock = pygame.time.Clock()
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
    fall_speed = 0.3 * (60 / FPS)
    max_fall_speed = 7 * (60 / FPS)
    player_speed = 4.1 * (WINDOW_SIZE[0] / 700) * (60 / FPS)
    running = True
    air_timer = 0
    while running:     
        display.fill(sky)

        # CALCULATION SCROLL MAP AND PLAYER ==================================

        true_scroll[0] += (player.rect.x - true_scroll[0] - WINDOW_SIZE[0] // 2) / 20
        true_scroll[1] += (player.rect.y - true_scroll[1] - WINDOW_SIZE[1] // 2) / 20
        if map_generate_type == TGENERATE_LOAD:
            true_scroll = [max(map_rect[0], true_scroll[0]), max(map_rect[1], true_scroll[1])]
            if true_scroll[0] > map_size[0] * TILE_SIZE - WINDOW_SIZE[0]:
                true_scroll[0] = map_size[0] * TILE_SIZE - WINDOW_SIZE[0]
        scroll = [int(true_scroll[0]), int(true_scroll[1])]
        # scroll = player.rect.x, player.rect.y

        # LOAD TILES (CHUNKS) AND DRAW OF VIEW WINDOW =========================

        static_tiles = {}
        dinamic_tiles = []
        scroll_chunk_x = scroll[0]//(CHUNK_SIZE_PX)
        chunk_y = scroll[1]//(CHUNK_SIZE_PX)        
        for cx in range(WINDOW_CHUNK_SIZE[0]):                
            chunk_x = scroll_chunk_x        
            for cy in range(WINDOW_CHUNK_SIZE[1]):
                # display.blit(chunk_img, (chunk_x*CHUNK_SIZE*TILE_SIZE-scroll[0], chunk_y*CHUNK_SIZE*TILE_SIZE-scroll[1]))
                # if map_generate_type != TGENERATE_LOAD:
                #     chunk_x -= 1
                #     chunk_y -= 1
                chunk_pos = (chunk_x, chunk_y)                
                if chunk_pos not in game_map:
                    if map_generate_type != TGENERATE_LOAD:
                        # генериует статические и динамичские
                        game_map[chunk_pos] = generate_chunk(*chunk_pos) # [static_lst, dinamic_lst]
                chunk = game_map.get(chunk_pos)
                if chunk:
                    # if cx  + cy == 0:
                    #     print("chunk_pos", chunk_pos)
                    dinamic_tiles += chunk[1]
                    chunk_size = len(chunk[0][0]) if chunk else 0, len(chunk[0])
                    for x in range(chunk_size[0]):
                        for y in range(chunk_size[1]):
                            tile = chunk[0][y][x]
                            tile_xy = ((chunk_x*CHUNK_SIZE+x), (chunk_y*CHUNK_SIZE+y))
                            if tile > 0:
                                # print(tile_xy)
                                display.blit(tile_imgs[tile], (tile_xy[0]*TILE_SIZE-scroll[0], tile_xy[1]*TILE_SIZE-scroll[1]))
                            if tile in PHYSBODY_TILES:                                
                                static_tiles[tile_xy] = tile
                            if chunk_pos[1] > 0:
                                pass
                chunk_x += 1
            chunk_y += 1
     
        # PROCESSING DINAMIC TILES =======================================
        
        for i in range(len(dinamic_tiles)):
            tile = dinamic_tiles[i]
            new_tile = None
            if tile[0] == 201: #cloud
                tile[1].update(tact)
            if new_tile is not None:
                dinamic_tiles[i] = new_tile

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
         
        # DRAW DISPLAY GAME TO WINDOW ========================================
        display.blit(top_surface, (0, 0))
        screen.blit(display, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

        tact += 1
    pygame.quit()


if __name__ == '__main__':
    pygame.init()
    main()
