import math

import pygame
import pygame as pg

import units.config as config

# используетсЯ ы других модулях

# INIT GAME ==============================================
pygame.init()  # initiate pygame
FPS = 30
flags = 0
desktop_size = pygame.display.get_desktop_sizes()[0]
print("INIT GAME VARS")
GAME_VERSION = "0.9.1"

WINDOW_SIZE = config.Window.size
FULLSCREEN = config.Window.fullscreen
if FULLSCREEN:
    WINDOW_SIZE = desktop_size
    # flags |= pygame.FULLSCREEN

# WINDOW_SIZE = WINDOW_SIZE[0] * 2, WINDOW_SIZE[1] - 10
WSIZE = WINDOW_SIZE
# WINDOW_SIZE = (1920, 1080)


flags |= pygame.SCALED
pygame.display.set_caption('Quadish')
screen_ = pygame.display.set_mode(WINDOW_SIZE, flags=flags, vsync=1)
display_ = pygame.Surface(WINDOW_SIZE)

screen_.blit(pygame.font.SysFont("", 40, ).render("Загрузка...", True, "white"), (35, WSIZE[1] - 50))
pygame.display.flip()

print(pg.display.get_allow_screensaver())

# TILE ==================================================

TILE_SIZE = 32
# TILE_SIZE = 10
TSIZE = TILE_SIZE

# TILE_SIZE = 16
TILE_RECT = (TILE_SIZE, TILE_SIZE)
TRECT = TILE_RECT

CHUNK_SIZE = 32
CSIZE = CHUNK_SIZE

STRUCTURE_CHUNKS_SIZE = 100  # чанков
CNT_BUILDS_OF_STRUCTURE_BLOCK = 1000
SCSIZE = STRUCTURE_CHUNKS_SIZE

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
CSIZEPX = CHUNK_SIZE_PX
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 1, \
                    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 1
WCSIZE = WINDOW_CHUNK_SIZE


# DEBUG ====================================================
# DEBUG = True
DEBUG = False
show_chunk_grid = False
show_entity_border = False
show_group_obj = True
show_info_menu = True
show_biomes = False

CHUNK_BD_COLOR = (230, 20, 20)

# PhiscalObject ==================================================

OBJ_NONE = 0
OBJ_CREATURE = 2
OBJ_ITEM = 4
OBJ_TILE = 8
OBJ_PLAYER = 16

# ITEMS ==========================================================

CLS_NONE = 0
CLS_TILE = 2
CLS_TOOL = 4
CLS_WEAPON = 8
CLS_SWORD = 16
CLS_PICKAXE = 32
CLS_EAT = 64
CLS_COMMON = 128

# STATES OF TILE ================================================

TILE_TIMER = "t"
TILE_LOCAL_POS = "p"

# GENERATING MAP OR CHANK ========================================

TGENERATE_LOAD = 0
TGENERATE_INFINITE = 1
TGENERATE_INFINITE_LANDS = 2
Generate_type = 2  # 0:load map,1: autogenerate

CHUNK_CREATURE_LIMIT = 4
CHUNK_CREATURE_CHANCE = 0.2

START_SPACE_Y = -1000
START_ATMO_Y = START_SPACE_Y + 200
TOP_MIDDLE_WORLD = START_ATMO_Y + 150
BOTTOM_MIDDLE_WORLD = 2000
START_HELL_Y = BOTTOM_MIDDLE_WORLD + 500
# Player ===========================================================

NUM_KEYS = [pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5, pg.K_6, pg.K_7, pg.K_8, pg.K_9, pg.K_0]

HAND_SIZE = int(TILE_SIZE // 1.5)
HAND_RECT = (HAND_SIZE, HAND_SIZE)

FALL_SPEED = 0.7
MAX_FALL_SPEED = 100000
AUTO_BUILD = True  # копать ближайший если мышка далеко

CREATIVE_MODE = False
# INIT TIME ================================================================

EVENT_100_MSEC = pg.USEREVENT + 1
pygame.time.set_timer(EVENT_100_MSEC, 100, False)

# COLORS ==================================================================
colors = ['#CD5C5C', '#F08080', '#FA8072', '#E9967A', '#FFA07A', '#DC143C', '#FF0000', '#B22222', '#8B0000', '#FFC0CB',
          '#FFB6C1', '#FF69B4', '#FF1493', '#C71585', '#DB7093', '#FFA07A', '#FF7F50', '#FF6347', '#FF4500', '#FF8C00',
          '#FFA500', '#FFD700', '#FFFF00', '#FFFFE0', '#FFFACD', '#FAFAD2', '#FFEFD5', '#FFE4B5', '#FFDAB9', '#EEE8AA',
          '#F0E68C', '#BDB76B', '#E6E6FA', '#D8BFD8', '#DDA0DD', '#EE82EE', '#DA70D6', '#FF00FF', '#FF00FF', '#BA55D3',
          '#9370DB', '#8A2BE2', '#9400D3', '#9932CC', '#8B008B', '#800080', '#4B0082', '#6A5ACD', '#483D8B', '#FFF8DC',
          '#FFEBCD', '#FFE4C4', '#FFDEAD', '#F5DEB3', '#DEB887', '#D2B48C', '#BC8F8F', '#F4A460', '#DAA520', '#B8860B',
          '#CD853F', '#D2691E', '#8B4513', '#A0522D', '#A52A2A', '#800000', '#000000', '#808080', '#C0C0C0', '#FFFFFF',
          '#FF00FF', '#800080', '#FF0000', '#800000', '#FFFF00', '#808000', '#00FF00', '#008000', '#00FFFF', '#008080',
          '#0000FF', '#000080', '#ADFF2F', '#7FFF00', '#7CFC00', '#00FF00', '#32CD32', '#98FB98', '#90EE90', '#00FA9A',
          '#00FF7F', '#3CB371', '#2E8B57', '#228B22', '#008000', '#006400', '#9ACD32', '#6B8E23', '#808000', '#556B2F',
          '#66CDAA', '#8FBC8F', '#20B2AA', '#008B8B', '#008080', '#00FFFF', '#00FFFF', '#E0FFFF', '#AFEEEE', '#7FFFD4',
          '#40E0D0', '#48D1CC', '#00CED1', '#5F9EA0', '#4682B4', '#B0C4DE', '#B0E0E6', '#ADD8E6', '#87CEEB', '#87CEFA',
          '#00BFFF', '#1E90FF', '#6495ED', '#7B68EE', '#4169E1', '#0000FF', '#0000CD', '#00008B', '#000080', '#191970',
          '#FFFFFF', '#FFFAFA', '#F0FFF0', '#F5FFFA', '#F0FFFF', '#F0F8FF', '#F8F8FF', '#F5F5F5', '#FFF5EE', '#F5F5DC',
          '#FDF5E6', '#FFFAF0', '#FFFFF0', '#FAEBD7', '#FAF0E6', '#FFF0F5', '#FFE4E1', '#DCDCDC', '#D3D3D3', '#D3D3D3',
          '#C0C0C0', '#A9A9A9', '#A9A9A9', '#808080', '#808080', '#696969', '#696969', '#778899', '#778899', '#708090',
          '#708090', '#2F4F4F', '#2F4F4F', '#000000']

Chest_size_table = 5, 4