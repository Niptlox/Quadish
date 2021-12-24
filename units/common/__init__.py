import pygame
import pygame as pg

import math

# INIT GAME ==============================================
print("INIT GAME VARS")
WINDOW_SIZE = (2200, 1100)
WINDOW_SIZE = (700*2, 400*2)
WSIZE = WINDOW_SIZE

FPS = 60

pygame.init() # initiate pygame
pygame.display.set_caption('Cubeee')

screen_ = pygame.display.set_mode(WINDOW_SIZE, flags=pygame.SCALED, vsync=2)
display_ = pygame.Surface(WINDOW_SIZE)


# TILE ==================================================

TILE_SIZE = 48
TSIZE = TILE_SIZE
# TILE_SIZE = 16
# TILE_SIZE = 8
TILE_RECT = (TILE_SIZE, TILE_SIZE)
TRECT = TILE_RECT

CHUNK_SIZE = 16
CSIZE = CHUNK_SIZE

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
CSIZEPX = CHUNK_SIZE_PX
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 1, \
    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 1
WCSIZE = WINDOW_CHUNK_SIZE

# DEBUG ====================================================
DEBUG = True
# DEBUG = False
show_chunk_grid = True
show_group_obj = True
show_info_menu = True

CHUNK_BD_COLOR = (230, 20, 20)

# GENERATING MAP OR CHANK ========================================

TGENERATE_LOAD = 0
TGENERATE_INFINITE = 1
TGENERATE_INFINITE_LANDS = 2
generate_type = 2 # 0:load map,1: autogenerate

# Player ===========================================================

NUM_KEYS = [pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5, pg.K_6, pg.K_7, pg.K_8, pg.K_9, pg.K_0]

# INIT TIME ================================================================

EVENT_100_MSEC = pg.USEREVENT+1
pygame.time.set_timer(EVENT_100_MSEC, 100, False)

