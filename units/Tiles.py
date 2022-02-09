import random

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


def transform_hand(surf, size=HAND_RECT, colorkey=COLORKEY):
    if type(surf) is list:
        surf = [pygame.transform.scale(s, size).convert() for s in surf]
        [s.set_colorkey(colorkey) for s in surf]
    else:
        surf = pygame.transform.scale(surf, size).convert()
        surf.set_colorkey(colorkey)
    return surf


sky = "#A5F3FC"

player_img = create_tile_image("#E7E5E4", size=(TSIZE - 2, TSIZE - 2), bd=2)

# hand_pass_img = pygame.transform.smoothscale(player_img, HAND_RECT)
hand_pass_img = None
player_hand_img = hand_pass_img

none_img = create_tile_image("#FFAAFF")

dirt_img = create_border(load_img("data/sprites/tiles/dirt.png"))
grass_img = create_border(load_img("data/sprites/tiles/grass/grass.png"))
grass_L_img = create_border(load_img("data/sprites/tiles/grass/grass_L.png"))
grass_R_img = create_border(load_img("data/sprites/tiles/grass/grass_R.png"))
grass_LR_img = create_border(load_img("data/sprites/tiles/grass/grass_LR.png"))
bioms = (0, 1, 2, 3)
grass_imgs = {i: (create_border(load_img(f"data/sprites/tiles/grass/grass_{i}.png")),
                  create_border(load_img(f"data/sprites/tiles/grass/grass_L_{i}.png")),
                  create_border(load_img(f"data/sprites/tiles/grass/grass_R_{i}.png")),
                  create_border(load_img(f"data/sprites/tiles/grass/grass_LR_{i}.png")),
                  ) for i in bioms}

stone_img = create_tile_image("#57534E")

ore_img = create_border(load_img("data/sprites/tiles/ore.png"))

purore_img = create_tile_image("#9333EA")  # purple ore

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
cauldron_img = load_img("data/sprites/tiles/cauldron.png")
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

wildberry_item_img = load_img("data/sprites/tiles/wildberry_item.png", None)
slime_item_img = load_img("data/sprites/tiles/slime_item.png", None)
meet_cow_item_img = load_img("data/sprites/tiles/meet_cow_item.png", None)
potion_life_item_item = load_img("data/sprites/tiles/potion_life_item.png", None)

blore_ore_img = load_img(r"data\sprites\items\blore_ore.png", None)  # blue ore
copper_ore_img = load_img(r"data\sprites\items\copper_ore.png", None)
gold_ore_img = load_img(r"data\sprites\items\gold_ore.png", None)
iron_ore_img = load_img(r"data\sprites\items\iron_ore.png", None)
silver_ore_img = load_img(r"data\sprites\items\silver_ore.png", None)

ruby_item_img = load_img(r"data\sprites\items\ruby.png", None)

sword_1_img = load_img("data/sprites/tools/sword_1.png", None)
sword_77_img = load_img("data/sprites/tools/sword_77.png", None)
pickaxe_1_img = load_img("data/sprites/tools/pickaxe_1.png", None)
pickaxe_77_img = load_img("data/sprites/tools/pickaxe_77.png", None)
tile_imgs = {0: none_img,
             1: grass_img,
             2: dirt_img,
             3: stone_img,
             4: ore_img,
             5: granite_img,
             9: tnt_img,
             11: wood_img,
             51: slime_item_img,
             52: meet_cow_item_img,
             53: wildberry_item_img,
             55: potion_life_item_item,
             61: blore_ore_img,
             62: copper_ore_img,
             63: gold_ore_img,
             64: iron_ore_img,
             65: silver_ore_img,
             66: ruby_item_img,
             101: bush_img,
             102: smalltree_img,
             120: water_img,
             121: table_img,
             122: chear_img,
             123: door_img,
             125: cauldron_img,
             151: group_img,
             201: cloud_img,
             202: cloud_imgs,
             203: tnt_1_img,
             204: tnt_imgs,

             501: sword_1_img,
             502: sword_77_img,
             531: pickaxe_1_img,
             532: pickaxe_77_img,
             }
count_tiles = len(tile_imgs)

ITEM_TILES = {51, 52, 53, 55, 61, 62, 63, 64, 65, 66}

tile_hand_imgs = {k: tile_imgs[k] if k in ITEM_TILES else transform_hand(i) for k, i in tile_imgs.items()}
tile_hand_imgs[102] = load_img("data/sprites/tiles/small_tree_item.png",
                               HAND_RECT)  # тк есть прозрачность создана собственная картинка
tile_hand_imgs[121] = load_img("data/sprites/tiles/table_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[122] = load_img("data/sprites/tiles/chear_item.png", HAND_RECT)  # тк есть прозрачность

tile_words = {0: "None",
              1: "Трава",
              2: "Земля",
              3: "Камень",
              4: "Блор",
              5: "Гранит",
              9: "Динамит",
              11: "Доски",
              51: "Слизь",
              52: "Мясо коровы",
              53: "Лесные ягоды",
              55: "Зелье жизни",
              61: "Блоровая руда",
              62: "Медная руда",
              63: "Золотая руда",
              64: "Железная руда",
              65: "Серебряная руда",
              66: "Рубин",
              101: "Куст",
              102: "Маленькое дерево",
              120: "Вода",
              121: "Стол",
              122: "Стул",
              123: "Дверь",
              125: "Котёл",
              151: "Группа обектов",
              201: "Облако",
              202: "Облака",
              203: "Активный динамит",
              204: "Активные динамиты",

              501: "Простой меч",
              502: "Золотой меч",
              531: "Простая кирка",
              532: "Золотая кирка",
              }

# INIT_TILES ====================================================

# блоки через которые нельзя пройти
PHYSBODY_TILES = {1, 2, 3, 4, 5, 9, 11, 124}
# блоки которые должны стоять на блоке (есть 0 т.к. на воздух ставить нельзя)
STANDING_TILES = {0, 101, 102, 120, 121, 122, 123, 125}
# предметы которые нельзя физически поставить
ITEM_TILES = {51, 52, 53, 55, 61, 62, 63, 64, 65, 66}
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
    125: 55,
    101: 25,
    102: 25,
    120: 100,
    121: 100,
    122: 100,
}

DYNAMITE_NOT_BREAK = {5, 120}  # granite water


# INIT PICKAXE ==================================================
# 61: "Блоровая руда",
# 62: "Медная руда",
# 63: "Золотая руда",
# 64: "Железная руда",
# 65: "Серебряная руда",
# 66: "Рубин",

def item_of_break_tile(ttile):
    # (index, count, chance)
    items = [(ttile, 1, 1)]
    if ttile == 102:  # smalltree_img
        items = [(11, 5, 1)]  # wood_img
    elif ttile == 4:  # ore
        items = ((3, 1, 1),  # stone
                 (64, (1, 2), 0.35),
                 (61, (1, 2), 0.35),
                 (62, (1, 2), 0.2),
                 (65, 1, 0.1),
                 (63, 1, 0.03))
    elif ttile == 3:  # stone
        items = ((3, 1, 1),  # stone
                 (61, 1, 0.005),
                 (62, 1, 0.01),
                 (64, 1, 0.01),
                 (65, 1, 0.001),
                 (63, 1, 0.0005),
                 (66, 1, 0.0001))
    elif ttile == 101:  # куст с ягодами
        items = [(53, (1, 3), 1)]
    res = [(i, cnt) for i, cnt, ch in items if ch == 1 or random.randint(0, 100 * 100) <= ch * 100 * 100]
    return res
