import random

from units.Graphics.Image import *
from units.UI.Translate import get_translated_dict_text, get_translated_tiles

DEBUG_DRAW_TILES = False


# CREATING TILE IMAGES ========================================


def transform_hand(surf, size=HAND_RECT, colorkey=COLORKEY):
    if type(surf) is list:
        surf = [pygame.transform.scale(s, size) for s in surf]
        [s.set_colorkey(colorkey) for s in surf]
    else:
        surf = pygame.transform.scale(surf, size)
        surf.set_colorkey(colorkey)
    return surf


sky = "#A5F3FC"

title_background = pg.image.load("data/sprites/title_back.png")
title_background_layer_2 = pg.image.load("data/sprites/title_back layer 2.png")
title_text = pg.image.load("data/sprites/title_text.png")

cloud_images = load_imgs("data/sprites/clouds/cloud-{}.png", 7, size=None, scale=2)
star_images = load_imgs("data/sprites/stars/star-{}.png", 5, size=None, scale=2)
star_chances = [i for i in range(len(star_images))], [(i + 1) / 10 for i in range(len(star_images))]

player_img = create_tile_image("#E7E5E4", size=(TSIZE - 10, TSIZE - 2), bd=2)
live_imgs = load_imgs("data/sprites/player/lives_{}.png", 5, size=(20, 20))
goldlive_imgs = load_imgs("data/sprites/player/goldherts_{}.png", 5, size=(20, 20))
bg_live_img = load_img("data/sprites/player/bg_live.png", size=(20, 20))
bg_livecreative_img = load_img("data/sprites/player/bg_livecreative.png", size=(24, 24))

# hand_pass_img = pygame.transform.smoothscale(player_img, HAND_RECT)
hand_pass_img = None
player_hand_img = hand_pass_img

break_imgs_cnt = 4
break_imgs = load_imgs("data/sprites/tiles/break/break_{}.png", 4, alpha=180)

dig_rect_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA, 32)
pygame.draw.rect(dig_rect_img, "#FDE047", ((0, 0), (TILE_SIZE - 1, TILE_SIZE - 1)), width=2, border_radius=-2)

none_img = create_tile_image("#FFAAFF")

grass_i_img = load_img("data/sprites/tiles/grass/grass_i.png")
grass_i_imgs = load_imgs("data/sprites/tiles/grass/grass_{}.png", 4, start_num=1)
dirt_img = load_img("data/sprites/tiles/dirt.png")
ground_img = (load_img("data/sprites/tiles/ground/ground.png"))
ground_L_img = (load_img("data/sprites/tiles/ground/ground_L.png"))
ground_R_img = (load_img("data/sprites/tiles/ground/ground_R.png"))
ground_LR_img = (load_img("data/sprites/tiles/ground/ground_LR.png"))
bioms = (0, 1, 2, 3)
ground_imgs = {i: ((load_img(f"data/sprites/tiles/ground/ground_{i}.png")),
                   (load_img(f"data/sprites/tiles/ground/ground_L_{i}.png")),
                   (load_img(f"data/sprites/tiles/ground/ground_R_{i}.png")),
                   (load_img(f"data/sprites/tiles/ground/ground_LR_{i}.png")),
                   ) for i in bioms}
ground_imgs[None] = (ground_img,
                     ground_L_img,
                     ground_R_img,
                     ground_LR_img)
stone_img = load_img("data/sprites/tiles/stone.png")
back_stone_img = load_img("data/sprites/backtiles/BackStone2.png")
# create_tile_image("#57534E")

ore_img = (load_img("data/sprites/tiles/ore.png"))
stone_brick_img = (load_img("data/sprites/tiles/blocksstoun0.png"))
stone_brick_1_img = (load_img("data/sprites/tiles/blocksstoun1.png"))
stone_brick_2_img = (load_img("data/sprites/tiles/blocksstoun2.png"))

purore_img = create_tile_image("#9333EA")  # purple ore

tnt_img = create_tile_image("#B91C1C")  # tnt

# granite_img = create_tile_image("#09070A")
granite_img = load_img("data/sprites/tiles/granite.png")

tnt_1_img = create_tile_image("#F87171")  # tnt activ
tnt_imgs = [tnt_1_img, create_tile_image("#FECACA")]  # tnt activ

wood_img = load_img("data/sprites/tiles/wood.png", colorkey=None)
plank_img = load_img("data/sprites/tiles/plank.png", colorkey=None)

cactus_img = load_img("data/sprites/tiles/cactus.png")
watermelon_img = load_img("data/sprites/tiles/watermelon/watermelon_0.png", SIZE_2X, is_tile=True)
watermelon_imgs = load_imgs("data/sprites/tiles/watermelon/watermelon_{}.png", 5, SIZE_2X, is_tile=True)

lean_img = load_img("data/sprites/tiles/lean.png")

bush_img = load_img("data/sprites/tiles/bush/bush.png")  # куст
bush_imgs = [load_img(f"data/sprites/tiles/bush/bush_{i}.png") for i in range(4)]  # кустs

smalltree_img = load_img("data/sprites/tiles/oak_saginer.png", SIZE_2X, is_tile=True)
leave_img = load_img(f"data/sprites/tiles/leave.png")

door_img = load_img("data/sprites/tiles/door.png")
close_door_img = load_img("data/sprites/tiles/close_door.png")
trapdoor_img = load_img("data/sprites/tiles/trapdoor.png")
close_trapdoor_img = load_img("data/sprites/tiles/close_trapdoor.png")

table_img = load_img("data/sprites/tiles/table.png")
chear_img = load_img("data/sprites/tiles/chear.png")  # стул
rack_img = load_img("data/sprites/tiles/rack.png")  # шкаф
chest_img = load_img("data/sprites/tiles/chest.png")  # сундук
cauldron_img = load_img("data/sprites/tiles/cauldron.png")
water_img = load_img("data/sprites/tiles/water.png")
furnace_img = load_img("data/sprites/tiles/furnace/furnace0.png")
furnace_imgs = load_imgs("data/sprites/tiles/furnace/furnace{}.png", 5)

stone_blore_ore_img = load_img(r"data/sprites/tiles/Ore/StoneBloreOre.png")  # blue ore
stone_copper_ore_img = load_img(r"data/sprites/tiles/Ore/StoneCopperOre.png")
stone_gold_ore_img = load_img(r"data/sprites/tiles/Ore/StoneGoldOre.png")
stone_iron_ore_img = load_img(r"data/sprites/tiles/Ore/StoneIronOre.png")
stone_silver_ore_img = load_img(r"data/sprites/tiles/Ore/StoneSilverOre.png")

cloud_img = create_tile_image("#CBD5E1")
cloud_imgs = [create_tile_image((203 - i, 213 - i, 230 - i)) for i in range(0, 130, 30)]

bedroll_of_pelts_img = load_img("data/sprites/tiles/bedroll_of_pelts.png")
bedroll_of_pelts_item_img = load_img("data/sprites/tiles/bedroll_of_pelts_item.png", None)

group_img = load_img("data/sprites/tiles/group.png")
build_img = load_img("data/sprites/tiles/build.png")
structure_pass_img = load_img("data/sprites/tiles/structure_pass.png")
activator_img = load_img("data/sprites/tiles/activator.png")
commandblock_img = load_img("data/sprites/tiles/commandblock.png")
commandblock_imgs = load_imgs("data/sprites/tiles/commandblock/commandblock_{}.png", 14)

rain_img = load_img("data/sprites/tiles/rain.png")

wildberry_item_img = load_img("data/sprites/tiles/wildberry_item.png", None)
meet_cow_item_img = load_img("data/sprites/tiles/meet_cow_item.png", None)
meet_wolf_item_img = load_img("data/sprites/tiles/meet_wolf_item.png", None)
meet_snake_item_img = load_img("data/sprites/items/meet_snake_item.png", None)
cooked_meet_cow_item_img = load_img("data/sprites/tiles/cooked_meet_cow_item.png", None)
cooked_meet_wolf_item_img = load_img("data/sprites/tiles/cooked_meet_wolf_item.png", None)
cooked_meet_snake_item_img = load_img("data/sprites/items/cooked_meet_snake_item.png", None)
poison_item_img = load_img("data/sprites/items/poison_item.png", None)
potion_life_item_img = load_img("data/sprites/tiles/potion_life_item.png", None)
potion_jump_item_img = load_img("data/sprites/tiles/potion_jump_item.png", None)

slime_item_img = load_img("data/sprites/tiles/slime_item.png", None)
pelt_wolf_item_img = load_img("data/sprites/tiles/pelt_wolf_item.png", None)

stick_img = load_img("data/sprites/items/stick.png", None)
blore_ore_img = load_img(r"data\sprites\items\blore_ore.png", None)  # blue ore
copper_ore_img = load_img(r"data\sprites\items\copper_ore.png", None)
gold_ore_img = load_img(r"data\sprites\items\gold_ore.png", None)
iron_ore_img = load_img(r"data\sprites\items\iron_ore.png", None)
silver_ore_img = load_img(r"data\sprites\items\silver_ore.png", None)

ruby_item_img = load_img(r"data\sprites\items\ruby.png", None)

summonerSlimeBoss_img = load_img(r"data/sprites/tools/SummonerSlimeBoss/SummonerSlimeBoss.png", None)

sword_77_img, sword_77_imgs = load_round_tool_imgs("data/sprites/tools/sword_77/sword_77_{}.png", 4)

sword_1_img, sword_1_imgs = load_round_tool_imgs("data/sprites/tools/sword_1/sword_1_{}.png", 4)
sword_2_img, sword_2_imgs = load_round_tool_imgs("data/sprites/tools/sword_2/sword_2_{}.png", 4)
pickaxe_0_img, pickaxe_0_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_0/pickaxe_0_{}.png", 4)
pickaxe_1_img, pickaxe_1_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_1/pickaxe_1_{}.png", 4)
pickaxe_3_img, pickaxe_3_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_3/pickaxe_3_{}.png", 4)
pickaxe_77_img, pickaxe_77_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_77/pickaxe_77_{}.png", 4)

spatula_1_img, spatula_1_imgs = load_round_tool_imgs("data/sprites/tools/spatula_1/pickaxe_1_{}.png", 4)

tile_imgs = {None: none_img,
             0: none_img,
             1: ground_img,
             2: dirt_img,
             3: stone_img,
             4: ore_img,
             5: granite_img,
             9: tnt_img,
             11: plank_img,
             12: wood_img,
             21: stone_blore_ore_img,
             22: stone_copper_ore_img,
             23: stone_gold_ore_img,
             24: stone_iron_ore_img,
             25: stone_silver_ore_img,

             31: stone_brick_img,
             32: stone_brick_1_img,
             33: stone_brick_2_img,
             51: slime_item_img,
             52: meet_cow_item_img,
             53: wildberry_item_img,
             55: potion_life_item_img,
             56: meet_wolf_item_img,
             58: pelt_wolf_item_img,
             61: blore_ore_img,
             62: copper_ore_img,
             63: gold_ore_img,
             64: iron_ore_img,
             65: silver_ore_img,
             66: ruby_item_img,
             81: cooked_meet_snake_item_img,
             82: cooked_meet_cow_item_img,
             86: cooked_meet_wolf_item_img,
             101: bush_img,
             102: smalltree_img,
             103: cactus_img,
             104: grass_i_img,
             105: leave_img,
             106: lean_img,
             110: wood_img,
             120: water_img,
             121: table_img,
             122: chear_img,
             123: door_img,
             124: close_door_img,
             125: cauldron_img,  # котёл
             126: rack_img,
             127: trapdoor_img,
             128: close_trapdoor_img,
             129: chest_img,
             130: bedroll_of_pelts_img,
             131: furnace_img,
             150: structure_pass_img,
             151: group_img,
             152: build_img,
             181: cloud_img,
             200: commandblock_img,
             210: activator_img,
             251: watermelon_img,
             # 203: tnt_1_img,
             301: poison_item_img,
             351: potion_jump_item_img,
             401: meet_snake_item_img,
             501: sword_1_img,
             502: sword_77_img,
             503: sword_2_img,
             530: pickaxe_0_img,
             531: pickaxe_1_img,
             532: pickaxe_77_img,
             533: pickaxe_3_img,
             581: spatula_1_img,
             610: summonerSlimeBoss_img,

             801: stick_img,

             1003: back_stone_img,
             }
count_tiles = len(tile_imgs)
print("Count_tiles imgs", count_tiles)
tile_many_imgs = {101: bush_imgs,
                  104: grass_i_imgs,
                  131: furnace_imgs,
                  181: cloud_imgs,
                  203: tnt_imgs,
                  251: watermelon_imgs,
                  501: sword_1_imgs,
                  502: sword_77_imgs,
                  503: sword_2_imgs,
                  530: pickaxe_0_imgs,
                  531: pickaxe_1_imgs,
                  532: pickaxe_77_imgs,
                  533: pickaxe_3_imgs,
                  581: spatula_1_imgs,
                  }

IDX_TOOLS = {501, 502, 503, 530, 531, 532, 533, 581, 610}

# EATS = {52: 10, 53: 2, 56: 8, 55: 100, 401: 8}

# растения растущее друг на друге например кактус
MULTI_BLOCK_PLANTS = {103, }
# растения растущее только на земле с травой
ON_EARTHEN_PLANTS = {101, 102, 103, 104}

# блоки через которые нельзя пройти
PHYSBODY_TILES = {1, 2, 3, 4, 5, 9, 11, 12, 21, 22, 23, 24, 25, 31, 32, 33, 103, 124, 128, 251}
# полуфизические блоки например мебель листва вода
SEMIPHYSBODY_TILES = {106, 120, 127, 126, 125, 121, 129, 131, 122, 104}
# блоки которые должны стоять на блоке (есть 0 т.к. на воздух ставить нельзя)
# STANDING_TILES = {0, 101, 102, 103, 104, 110, 120, 121, 122, 123, 125, 126, 130, 129, 251}
STANDING_TILES = {0, 110, 120, 121, 122, 123, 125, 126, 130, 129, 131} | ON_EARTHEN_PLANTS
# Задние панельки
BACKTILES = {1003, }
# предметы которые нельзя физически поставить
ITEM_TILES = {None, 51, 52, 53, 55, 56, 58, 61, 62, 63, 64, 65, 66, 301, 351, 401, 801, 81, 82, 86}

STONE_TILES = {3, 4, 5, 31, 32, 33, 21, 22, 23, 24, 25, 131}
WOOD_TILES = {12, 110, 11, 121, 122, 123, 124, 126, 127, 128, 129, 131, 251}

# блоки у которых есть прграммный класс
CLASS_TILE = {131, 129, 200, 210}
# которые надо обновлять
CLASS_UPDATING_TILES = {131, 200, 210}
# CLASS_UPDATING_TILES_IN_UI = {131}
# которые надо обновлять не зависимо от загрузки чанка те всегда
CLASS_ALLWAYS_UPDATING_TILES = {200, }
# блоки которые можно активировать
ACTIVATE_TILES = {200, 210, 9}

# Блоки у которых state это массив
ITEM_WITH_STATE_IS_LIST = {126}
# Растения у которых есть таймер
PLANT_WITH_TIMER = {101, 102}
# растетет только на земле
PLANT_STAND_ON_DIRT = {101, 102, 103, 104, 251}
# растет в высоту например кактус
PLANT_STAND_ON_PLANT = {103}
# Растения у которых есть рандомная картинка {tID: count}
PLANT_WITH_RANDOM_SPRITE = {251: 5, 104: len(grass_i_imgs)}
PLANT_WITH_RANDOM_LOCAL_POS = {251, 102}
TILE_WITH_LOCAL_POS = {251, } | PLANT_WITH_RANDOM_LOCAL_POS
# EAT ===================================================================

Eats = {52: 10, 53: 2, 56: 8, 55: 100, 401: 7, 251: 7, 351: 1,
        81: 14, 82: 20, 86: 16}

# PICKAXE ===============================================================

iron_capability = {1, 2, 3, 4, 9, 11, 12, 21, 22, 23, 24, 25, 31, 32, 33, 101, 102, 103, 104, 105, 106, 110, 121, 122,
                   123, 124, 125, 126, 131,
                   127, 251,
                   128, 130}
spatula_iron_capability = {1003}
Pickaxes_capability = {
    530: iron_capability,
    531: iron_capability,
    532: None,
    533: iron_capability,
    # spatula
    581: spatula_iron_capability,
    # hand
    -1: iron_capability
}
# PLANTS ===================================================================


# plants_chance = {101: 0.1, 102: 0.2, 104: 1, 120: 0.05, 251: 0.005}
biomes_plants_chance = {
    None: {101: 0.1, 102: 0.2, 104: 1, 120: 0.05, 251: 0.005},
    #     desert
    0: {101: 0.1, 103: 0.2, 104: 0.2, None: 0.5},
    #     winter
    3: {101: 0.3, 102: 0.1, None: 0.5},
    9: {},
}
# desert_plants_chance = {101: 0.1, 103: 0.2, 104: 0.2, None: 0.5}
# winter_plants_chance = {101: 0.3, 102: 0.1, None: 0.5}

# специальные каринки предметов для инвентаря
tile_hand_imgs = {k: tile_imgs[k] if k in ITEM_TILES else transform_hand(i) for k, i in tile_imgs.items()}
# tile_hand_imgs[102] = load_img("data/sprites/tiles/small_tree_item.png",
#                                HAND_RECT)  # тк есть прозрачность создана собственная картинка
tile_hand_imgs[121] = load_img("data/sprites/tiles/table_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[122] = load_img("data/sprites/tiles/chear_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[130] = bedroll_of_pelts_item_img

# INIT_TILES ====================================================

original_tile_words = {None: "None",
                       0: "None",
                       1: "Дёрн",
                       2: "Земля",
                       3: "Камень",
                       4: "Блор",
                       5: "Гранит",
                       9: "Динамит",
                       11: "Доски",
                       12: "Древесина",
                       21: "Блок блоровой руды",
                       22: "Блок медной руды",
                       23: "Блок золотой руды",
                       24: "Блок железной руды",
                       25: "Блок серебряной руды",
                       31: "Каменный кирпич",
                       32: "Замшелый каменный кирпич",
                       33: "Старый каменный кирпич",
                       51: "Слизь",
                       52: "Мясо коровы",
                       53: "Лесные ягоды",
                       55: "Зелье жизни",
                       56: "Мясо волка",
                       58: "Шкура волка",
                       61: "Блоровая руда",
                       62: "Медная руда",
                       63: "Золотая руда",
                       64: "Железная руда",
                       65: "Серебряная руда",
                       66: "Рубин",
                       81: "Приготовленное мясо коровы",
                       82: "Приготовленное мясо волка",
                       86: "Приготовленное мясо змеи",
                       101: "Куст",
                       102: "Саженец дуба",
                       103: "Кактус",
                       104: "Трава",
                       105: "Листва",
                       106: "Лианы",
                       110: "Живое дерево",
                       120: "Вода",
                       121: "Стол",
                       122: "Стул",
                       123: "Дверь",
                       124: "Закрытая дверь",
                       125: "Котёл",
                       126: "Шкаф",
                       127: "Люк",
                       128: "Закрытый люк",
                       129: "Сундук",
                       130: "Спальный мешок из шкур",
                       131: "Печка",
                       150: "Структурная пустота",
                       151: "Группа обектов",
                       181: "Облако",
                       200: "Командный блок",
                       210: "Активационный блок",
                       251: "Арбуз",
                       301: "Ядовитая железа",
                       351: "Зелье нового прыжка",
                       401: "Мясо змеи",
                       501: "Железный меч",
                       502: "Золотой меч",
                       503: "Ядовитый меч",
                       530: "Деревянная кирка",
                       531: "Железная кирка",
                       532: "Золотая кирка",
                       533: "Медная кирка",
                       581: "Шпатель",

                       610: "Призыатель босса слизней",

                       801: "Палка",
                       1003: "Панелька камня"
                       }
tile_words = get_translated_tiles(original_tile_words)

all_tiles = set(tile_words)

# Прочность блоков
TILES_SOLIDITY = {
    1: 15,
    2: 20,
    3: 35,
    4: 60,
    5: 100,
    9: 60,
    11: 45,
    12: 45,
    21: 60,
    22: 50,
    23: 50,
    24: 60,
    25: 50,
    31: 75,
    32: 70,
    33: 60,
    101: 25,
    102: 25,
    103: 25,
    104: 5,
    105: 15,
    110: 45,
    120: 100,
    121: 100,
    122: 100,
    123: 45,
    125: 55,
    126: 45,
    127: 45,
    128: 45,
    130: 80,
    131: 80,
    251: 45,
}

DYNAMITE_NOT_BREAK = {5, 120, 200, 210}  # granite water

# INIT PICKAXE ==================================================
# 61: "Блоровая руда",
# 62: "Медная руда",
# 63: "Золотая руда",
# 64: "Железная руда",
# 65: "Серебряная руда",
# 66: "Рубин",

# специальные шансы выпадения предметов
tile_drops = {
    # 102: [(12, 5, 1)],  # smalltree_img
    4: ((3, 1, 1),  # ore
        (64, (1, 2), 0.35),
        (61, (1, 2), 0.35),
        (62, (1, 2), 0.2),
        (65, 1, 0.1),
        (63, 1, 0.03)),
    3: ((3, 1, 1),  # stone
        (61, 1, 0.005),
        (62, 1, 0.01),
        (64, 1, 0.01),
        (65, 1, 0.001),
        (63, 1, 0.0005),
        (66, 1, 0.0001)),
    124: [(123, 1, 1)],  # close door
    128: [(127, 1, 1)],  # close door
    110: [(12, 1, 1)],  # из дерева древесина
    105: [(105, 1, 1), (102, 1, 0.13), (801, (1, 2), 0.25)],
    21: [(3, 1, 0.95),
         (61, (1, 2), 1)],
    22: [(3, 1, 0.95),
         (62, (1, 2), 1)],
    23: [(3, 1, 0.95),
         (63, (1, 2), 1)],
    24: [(3, 1, 0.95),
         (64, (1, 2), 1)],
    25: [(3, 1, 0.95),
         (65, (1, 2), 1)],
}


def item_of_break_tile(tile, game_map, tile_xy):
    # (index, count, chance)
    ttile = tile[0]
    items = [(ttile, 1, 1)]
    if ttile in tile_drops:
        items = tile_drops[ttile]
    if ttile == 101:  # куст с ягодами
        items += item_of_right_click_tile(tile, res=False)
    res = [(i, cnt) for i, cnt, ch in items if ch == 1 or random.randint(0, 100 * 100) <= ch * 100 * 100]
    if ttile == 126:  # шкаф
        res += [i for i in tile[3] if i]
    elif ttile in CLASS_TILE:
        tile_obj = game_map.get_tile_obj(tile_xy[0] // CHUNK_SIZE, tile_xy[1] // CHUNK_SIZE, tile[3])
        res += tile_obj.items_of_break()
    return res


def item_of_right_click_tile(tile, res=True):
    items = []
    ttile = tile[0]
    if ttile == 101:  # куст с ягодами
        if tile[2] > 0:  # степень выроста куста
            items = [(53, (tile[2] + 1, tile[2] + 2), 1)]  # ягоды
    if res:
        res = [(i, cnt) for i, cnt, ch in items if ch == 1 or random.randint(0, 100 * 100) <= ch * 100 * 100]
        return res
    return items


def debug_draw():
    clock = pg.time.Clock()
    screen_.fill("green")

    x, y = 5, 5
    for im in pickaxe_0_imgs:
        screen_.blit(im, (x, y))
        x += im.get_width() + 5
    pg.display.flip()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False


if DEBUG_DRAW_TILES:
    debug_draw()
