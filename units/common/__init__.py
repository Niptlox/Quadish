import pygame
import math

print("INIT GAME VARS")
WINDOW_SIZE = (2200, 1100)
WINDOW_SIZE = (700*2, 400*2)

FPS = 60




TILE_SIZE = 48
# TILE_SIZE = 16
# TILE_SIZE = 8
TILE_RECT = (TILE_SIZE, TILE_SIZE)

CHUNK_SIZE = 16

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
# колво чанков отрисываемых на экране
WINDOW_CHUNK_SIZE = math.ceil(WINDOW_SIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 1, \
    math.ceil(WINDOW_SIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 1