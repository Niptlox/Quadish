import os

from pygame.event import event_name
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import math
import random
from copy import deepcopy

from noise import snoise2, pnoise2

import pygame
from pygame.locals import *


random.seed(50, 1)

WINDOW_SIZE = (700*2, 400*2)
FPS = 60

pygame.init() # initiate pygame
pygame.display.set_caption('Pygame Window')

screen = pygame.display.set_mode(WINDOW_SIZE, flags=pygame.SHOWN, vsync=2)

display = pygame.Surface(WINDOW_SIZE)

TILE_SIZE = 48, 48
# TILE_SIZE = 18, 18
CHUNK_SIZE = 16
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE[0] * CHUNK_SIZE)) + 2, \
    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE[1] * CHUNK_SIZE)) + 2

print("WINDOW_CHUNK_SIZE", WINDOW_CHUNK_SIZE)


# cloud_struct = [["my_x, my_y"], [["tile_x, tile_y"],...]]

BORDER_COLOR = "#1C1917"
def create_tile_image(color, bd=1, size=TILE_SIZE, bd_color=BORDER_COLOR):
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
bush_img = pygame.transform.scale(bush_img, TILE_SIZE)

smalltree_img = pygame.image.load("data/sprites/tiles/small_tree.png").convert()
smalltree_img = pygame.transform.scale(smalltree_img, TILE_SIZE)
smalltree_img.set_colorkey(COLORKEY)

chunk_img = create_tile_image(sky, bd=1, size=(CHUNK_SIZE*TILE_SIZE[0], CHUNK_SIZE*TILE_SIZE[1]), bd_color="red")



tile_imgs = {1: grass_img, 
             2: dirt_img, 
             3: stone_img,
             4: blore_img,
             101: bush_img,
             102: smalltree_img,}
PHYSBODY_TILES = (1, 2, 3, 4)

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
        return tile_type
    else:
        return 

def random_plant_selection():
    plant_tile_type = None
    if random.randint(0, 10) == 0:
        plant_tile_type = 101
    elif random.randint(0, 10) == 0:
        plant_tile_type = 102
    return plant_tile_type

def generate_chunk_noise_island(x,y):    
    static_tiles = [[0]*CHUNK_SIZE for i in range(CHUNK_SIZE)]    
    dinamic_tiles = []
    # emptys = []
    
    octaves = 6
    freq_x = 35
    freq_y = 15
    for y_pos in range(CHUNK_SIZE):        
        # now_empty = 0
        # emptys.append([])
        # last_tile = None
        for x_pos in range(CHUNK_SIZE):
            tile_type = None
            tile_x = x * CHUNK_SIZE + x_pos
            tile_y = y * CHUNK_SIZE + y_pos

            # v = pnoise2(tile_x / freq, tile_y / freq*2, octaves, persistence=0.35)
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
            # if tile_type is None:
            #     # пусто 
            #     if last_tile is None:
            #         emptys[-1].append([0, 0])
            #     emptys[-1][-1] += 1
            # elif (last_tile is None or x_pos == CHUNK_SIZE-1):
            #     c = emptys[-1][-1]
            #     x1 = x_pos - c
            #     emptys[-1][-1] = []
                            
            if tile_type is not None:
                static_tiles[y_pos][x_pos] = tile_type
            # last_tile = tile_type
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
        v_xy_map = v_x_map, v_y_map = (vertex[0] // TILE_SIZE[0], vertex[1] // TILE_SIZE[1])
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
                        self.rect.right = block[0][0] * TILE_SIZE[0] + first_tile_pos[0]
                    elif type_coll == 1:
                        self.rect.right = block.left
                    collision_types['right'] = True
                elif mx < 0:
                    if type_coll == 0:
                        self.rect.left = block[0][0] * TILE_SIZE[0] + first_tile_pos[0] + TILE_SIZE[0]
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
                        self.rect.bottom = block[0][1] * TILE_SIZE[1] + first_tile_pos[1]
                    elif type_coll == 1:
                        self.rect.bottom = block.top
                    collision_types['bottom'] = True
                elif my < 0:
                    if type_coll == 0:
                        self.rect.top = block[0][1] * TILE_SIZE[1] + first_tile_pos[1] + TILE_SIZE[1]
                    elif type_coll == 1:
                        self.rect.top = block.bottom
                    collision_types['top'] = True     
        return collision_types  

    def draw(self):
        pygame.draw.rect(screen,(255,255,0),self.rect)

player = PhiscalObject(CHUNK_SIZE*TILE_SIZE[0]*2, WINDOW_SIZE[1]//2 - TILE_SIZE[1]*3.5, TILE_SIZE[0]-1, TILE_SIZE[1]-1)


def main():    
    
    clock = pygame.time.Clock()
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

        true_scroll[0] += (player.rect.x - true_scroll[0] - WINDOW_SIZE[0] // 2) / 20
        true_scroll[1] += (player.rect.y - true_scroll[1] - WINDOW_SIZE[1] // 2) / 20
        if map_generate_type == TGENERATE_LOAD:
            true_scroll = [max(map_rect[0], true_scroll[0]), max(map_rect[1], true_scroll[1])]
            if true_scroll[0] > map_size[0] * TILE_SIZE[0] - WINDOW_SIZE[0]:
                true_scroll[0] = map_size[0] * TILE_SIZE[0] - WINDOW_SIZE[0]
        scroll = [int(true_scroll[0]), int(true_scroll[1])]
        # scroll = player.rect.x, player.rect.y
        static_tiles = {}
        for cx in range(WINDOW_CHUNK_SIZE[0]):                
            for cy in range(WINDOW_CHUNK_SIZE[1]):
                chunk_x = cx + int((scroll[0]/(CHUNK_SIZE*TILE_SIZE[0])))
                chunk_y = cy + int((scroll[1]/(CHUNK_SIZE*TILE_SIZE[1])))
                # display.blit(chunk_img, (chunk_x*CHUNK_SIZE*TILE_SIZE[0]-scroll[0], chunk_y*CHUNK_SIZE*TILE_SIZE[1]-scroll[1]))
                if map_generate_type != TGENERATE_LOAD:
                    chunk_x -= 1
                    chunk_y -= 1
                chunk_pos = (chunk_x, chunk_y)
                
                if chunk_pos not in game_map:
                    if map_generate_type != TGENERATE_LOAD:
                        # генериует статические и динамичские
                        game_map[chunk_pos] = generate_chunk(*chunk_pos) # [static_lst, dinamic_lst]
                chunk = game_map.get(chunk_pos)
                if chunk:
                    # if cx  + cy == 0:
                    #     print("chunk_pos", chunk_pos)
                    chunk_size = len(chunk[0][0]) if chunk else 0, len(chunk[0])
                    for x in range(chunk_size[0]):
                        for y in range(chunk_size[1]):
                            tile = chunk[0][y][x]
                            tile_xy = ((chunk_x*CHUNK_SIZE+x), (chunk_y*CHUNK_SIZE+y))
                            if tile > 0:
                                # print(tile_xy)
                                display.blit(tile_imgs[tile], (tile_xy[0]*TILE_SIZE[0]-scroll[0], tile_xy[1]*TILE_SIZE[1]-scroll[1]))
                            if tile in PHYSBODY_TILES:                                
                                static_tiles[tile_xy] = (tile)
                            if chunk_pos[1] > 0:
                                pass
     
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
            px, py = player.rect.centerx // TILE_SIZE[0], player.rect.centery // TILE_SIZE[1]
            if moving_right:
                set_static_tile(px + 1, py, 0)
            if moving_left:
                set_static_tile(px - 1, py, 0)
            if on_down:
                set_static_tile(px, py + 1, 0)
            if on_up:
                set_static_tile(px, py - 1, 0)


        display.blit(player_img, (player.rect.x-scroll[0], player.rect.y-scroll[1]))

        jump_on_wall = False
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
         
        screen.blit(display, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == '__main__':
    pygame.init()
    main()
