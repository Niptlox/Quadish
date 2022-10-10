# https://github.com/BilHim/minecraft-world-generation/blob/main/src/Minecraft%20Terrain%20Generation%20in%20Python%20-%20By%20Bilal%20Himite.ipynb

import numpy as np
from PIL import Image
from noise import snoise2

from units.Tiles import create_tile_image
from units.common import *

im = np.array(Image.open("data/sprites/biomes/TP_map.png"))[:, :, :3]
biomes = np.zeros((256, 256))

biome_names = [
    "desert",
    "savanna",
    "tropical_woodland",
    "tundra",
    "seasonal_forest",
    "rainforest",
    "temperate_forest",
    "temperate_rainforest",
    "boreal_forest",
    "hell"
]
biome_colors = [
    [255, 255, 178],
    [184, 200, 98],
    [188, 161, 53],
    [190, 255, 242],
    [106, 144, 38],
    [33, 77, 41],
    [86, 179, 106],
    [34, 61, 53],
    [35, 114, 94],
    [200, 15, 15]
]

biome_tiles = [create_tile_image(c, bd=0) for c in biome_colors]

for i, color in enumerate(biome_colors):
    indices = np.where(np.all(im == color, axis=-1))
    biomes[indices] = i

biomes = np.flip(biomes, axis=0).T


def biome_of_pos(x, y):
    """биом, Температура, влажность"""
    cof = 240
    i = snoise2(x / cof, y / cof, 2, persistence=0.75, base=123, lacunarity=1)
    j = snoise2(x / cof, y / cof, 2, persistence=0.75, base=13, lacunarity=1)
    k = snoise2(x / 100, y / 100, 2, persistence=0.75, base=113, lacunarity=2)
    j -= (j - i) * k
    i -= (i - j) * k
    if y < TOP_MIDDLE_WORLD:
        iy = y - TOP_MIDDLE_WORLD - 15
        i -= -iy / 100
        j -= -y / 10
    t = int(i * 25) + 10
    t = max(t, -273)
    p = int(j * 50) + 50
    if (snoise2(x / freq_x, y / freq_y) * 20 + y) > START_HELL_Y:
        t += 100
        p //= 5
        return 9, t, p  # HELL

    noise_val_t = max(0, min(255, int(i * 128 + 128)))
    noise_val_p = max(0, min(255, int(j * 128 + 128)))
    return int(biomes[noise_val_t, noise_val_p]), t, p
