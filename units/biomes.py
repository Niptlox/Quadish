# https://github.com/BilHim/minecraft-world-generation/blob/main/src/Minecraft%20Terrain%20Generation%20in%20Python%20-%20By%20Bilal%20Himite.ipynb

import numpy as np
from PIL import Image
from noise import snoise2
from units.Tiles import create_tile_image, grass_img

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
    "boreal_forest"
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
    [35, 114, 94]
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
    j = snoise2(x / cof, y / cof, 2, persistence=0.75, base=123, lacunarity=1)
    t = int(i * 25) + 10
    p = int(i * 50) + 50
    noise_val_t = int(i * 128 + 128)
    noise_val_p = int(j * 128 + 128)
    return int(biomes[noise_val_t, noise_val_p]), t, p
