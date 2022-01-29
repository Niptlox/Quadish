from units.common import *

# CREATING TILE IMAGES ========================================

BORDER_COLOR = "#1C1917"


def create_tile_image(color, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    img = pygame.Surface(size)
    img.fill(bd_color)
    pygame.draw.rect(img, color, ((bd, bd), (size[0] - bd * 2, size[0] - bd * 2)), border_radius=bd * 2)
    return img


def create_border(surface, bd=1, size=TILE_RECT, bd_color=BORDER_COLOR):
    pygame.draw.rect(surface, bd_color, ((0, 0), (size[0], size[1])), width=bd)
    return surface


COLORKEY = (0, 255, 0)


def load_img(path, size=TILE_RECT, colorkey=COLORKEY):
    img = pygame.image.load(path).convert()
    if size:
        img = pygame.transform.scale(img, size)
    if colorkey:
        img.set_colorkey(colorkey)
    return img


def transform_hand(surf, size=HAND_RECT):
    if type(surf) is list:
        surf = [pygame.transform.smoothscale(s, size) for s in surf]
    else:
        surf = pygame.transform.smoothscale(surf, size)
    return surf


sky = "#A5F3FC"

player_img = create_tile_image("#E7E5E4", bd=2)

hand_pass_img = pygame.transform.smoothscale(player_img, HAND_RECT)
player_hand_img = hand_pass_img

none_img = create_tile_image("#FFAAFF")

dirt_img = create_tile_image("#694837")

grass_img = create_tile_image("#16A34A")

stone_img = create_tile_image("#57534E")

blore_img = create_tile_image("#155E75")  # blue ore

tnt_img = create_tile_image("#B91C1C")  # tnt

# granite_img = create_tile_image("#09070A")
granite_img = create_border(load_img("data/sprites/tiles/granite.png"))

tnt_1_img = create_tile_image("#F87171")  # tnt activ
tnt_imgs = [tnt_1_img, create_tile_image("#FECACA")]  # tnt activ

wood_img = load_img("data/sprites/tiles/wood.png")

bush_img = load_img("data/sprites/tiles/bush.png")  # куст

smalltree_img = load_img("data/sprites/tiles/small_tree.png")

door_img = load_img("data/sprites/tiles/door.png")
table_img = load_img("data/sprites/tiles/table.png")
chear_img = load_img("data/sprites/tiles/chear.png")
water_img = load_img("data/sprites/tiles/water.png")

cloud_img = create_tile_image("#CBD5E1")
cloud_imgs = [create_tile_image((203 - i, 213 - i, 230 - i)) for i in range(0, 130, 30)]

break_1_img = load_img("data/sprites/tiles/break_1.png")
break_1_img.set_alpha(100)  # прозрачность 100 из 255
break_2_img = load_img("data/sprites/tiles/break_2.png")
break_2_img.set_alpha(100)
break_3_img = load_img("data/sprites/tiles/break_3.png")
break_3_img.set_alpha(100)
break_imgs = [break_1_img, break_2_img, break_3_img]

dig_rect_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA, 32)
pygame.draw.rect(dig_rect_img, "#FDE047", ((0, 0), (TILE_SIZE - 1, TILE_SIZE - 1)), width=2, border_radius=-2)

group_img = load_img("data/sprites/tiles/group.png")

rain_img = load_img("data/sprites/tiles/rain.png")

slime_item_img = load_img("data/sprites/tiles/slime_item.png", HAND_RECT)

tile_imgs = {0: none_img,
             1: grass_img,
             2: dirt_img,
             3: stone_img,
             4: blore_img,
             5: granite_img,
             9: tnt_img,
             11: wood_img,
             51: slime_item_img,
             101: bush_img,
             102: smalltree_img,
             120: water_img,
             121: table_img,
             122: chear_img,
             123: door_img,
             151: group_img,
             201: cloud_img,
             202: cloud_imgs,
             203: tnt_1_img,
             204: tnt_imgs
             }
count_tiles = len(tile_imgs)

tile_hand_imgs = {k: transform_hand(i) for k, i in tile_imgs.items()}
tile_hand_imgs[102] = load_img("data/sprites/tiles/small_tree_item.png",
                               HAND_RECT)  # тк есть прозрачность создана собственная картинка
tile_hand_imgs[121] = load_img("data/sprites/tiles/table_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[122] = load_img("data/sprites/tiles/chear_item.png", HAND_RECT)  # тк есть прозрачность

# INIT_TILES ====================================================

# блоки через которые нельзя пройти
PHYSBODY_TILES = {1, 2, 3, 4, 5, 9, 11, 124}
# блоки которые должны стоять на блоке
STANDING_TILES = {101, 102, 120, 121, 122, 123}
# блоки которые должны стоять на блоке
ITEM_TILES = {51, }
# Ппочность блоков
TILES_SOLIDITY = {
    1: 15,
    2: 20,
    3: 35,
    4: 60,
    5: 80,
    9: 60,
    11: 45,
    123: 45,
    101: 25,
    102: 25,
    120: 100,
    121: 100,
    122: 100,
}

DYNAMITE_NOT_BREAK = {5, 120}  # granite water
# INIT PICKAXE ==================================================

PICKAXES_STRENGTH = {
    1: 5,
    77: 777
}
PICKAXES_SPEED = {
    1: 8,
    77: 777
}
PICKAXES_CAPABILITY = {
    1: [1, 2, 3, 4, 9, 11, 101, 102, 123],
    77: None
}


def item_of_break_tile(ttile):
    count_items = 1
    if ttile == 102:  # smalltree_img
        ttile = 11  # wood_img
        count_items = 5
    return ttile, count_items


# Swords ========================================================

SWORD_STRENGTH = {
    1: 10,
    77: 777
}
SWORD_SPEED = {
    1: 1,
    77: 777
}
