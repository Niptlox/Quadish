import random

from units.Image import *

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

player_img = create_tile_image("#E7E5E4", size=(TSIZE - 10, TSIZE - 2), bd=2)
live_imgs = load_imgs("data/sprites/player/lives_{}.png", 5, size=(20, 20))
bg_live_img = load_img("data/sprites/player/bg_live.png", size=(20, 20))

# hand_pass_img = pygame.transform.smoothscale(player_img, HAND_RECT)
hand_pass_img = None
player_hand_img = hand_pass_img

break_imgs_cnt = 4
break_imgs = load_imgs("data/sprites/tiles/break/break_{}.png", 4, alpha=180)

dig_rect_img = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA, 32)
pygame.draw.rect(dig_rect_img, "#FDE047", ((0, 0), (TILE_SIZE - 1, TILE_SIZE - 1)), width=2, border_radius=-2)

none_img = create_tile_image("#FFAAFF")

dirt_img = load_img("data/sprites/tiles/dirt.png")
grass_img = (load_img("data/sprites/tiles/grass/grass.png"))
grass_L_img = (load_img("data/sprites/tiles/grass/grass_L.png"))
grass_R_img = (load_img("data/sprites/tiles/grass/grass_R.png"))
grass_LR_img = (load_img("data/sprites/tiles/grass/grass_LR.png"))
bioms = (0, 1, 2, 3)
grass_imgs = {i: ((load_img(f"data/sprites/tiles/grass/grass_{i}.png")),
                  (load_img(f"data/sprites/tiles/grass/grass_L_{i}.png")),
                  (load_img(f"data/sprites/tiles/grass/grass_R_{i}.png")),
                  (load_img(f"data/sprites/tiles/grass/grass_LR_{i}.png")),
                  ) for i in bioms}

stone_img = load_img("data/sprites/tiles/stone.png")
# create_tile_image("#57534E")

ore_img = (load_img("data/sprites/tiles/ore.png"))

purore_img = create_tile_image("#9333EA")  # purple ore

tnt_img = create_tile_image("#B91C1C")  # tnt

# granite_img = create_tile_image("#09070A")
granite_img = create_border(load_img("data/sprites/tiles/granite.png"))

tnt_1_img = create_tile_image("#F87171")  # tnt activ
tnt_imgs = [tnt_1_img, create_tile_image("#FECACA")]  # tnt activ

wood_img = load_img("data/sprites/tiles/wood.png", colorkey=None)
plank_img = load_img("data/sprites/tiles/plank.png", colorkey=None)

cactus_img = load_img("data/sprites/tiles/cactus.png")

bush_img = load_img("data/sprites/tiles/bush/bush.png")  # куст
bush_imgs = [load_img(f"data/sprites/tiles/bush/bush_{i}.png") for i in range(4)]  # кустs

smalltree_img = load_img("data/sprites/tiles/small_tree.png")
leave_img = load_img(f"data/sprites/tiles/bush/bush_0.png")

door_img = load_img("data/sprites/tiles/door.png")
close_door_img = load_img("data/sprites/tiles/close_door.png")
trapdoor_img = load_img("data/sprites/tiles/trapdoor.png")
close_trapdoor_img = load_img("data/sprites/tiles/close_trapdoor.png")

table_img = load_img("data/sprites/tiles/table.png")
chear_img = load_img("data/sprites/tiles/chear.png")  # стул
rack_img = load_img("data/sprites/tiles/rack.png")  # шкаф
cauldron_img = load_img("data/sprites/tiles/cauldron.png")
water_img = load_img("data/sprites/tiles/water.png")

cloud_img = create_tile_image("#CBD5E1")
cloud_imgs = [create_tile_image((203 - i, 213 - i, 230 - i)) for i in range(0, 130, 30)]

bedroll_of_pelts_img = load_img("data/sprites/tiles/bedroll_of_pelts.png")
bedroll_of_pelts_item_img = load_img("data/sprites/tiles/bedroll_of_pelts_item.png", None)

group_img = load_img("data/sprites/tiles/group.png")

rain_img = load_img("data/sprites/tiles/rain.png")

wildberry_item_img = load_img("data/sprites/tiles/wildberry_item.png", None)
meet_cow_item_img = load_img("data/sprites/tiles/meet_cow_item.png", None)
meet_wolf_item_img = load_img("data/sprites/tiles/meet_wolf_item.png", None)
potion_life_item_img = load_img("data/sprites/tiles/potion_life_item.png", None)

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
pickaxe_0_img, pickaxe_0_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_0/pickaxe_0_{}.png", 4)
pickaxe_1_img, pickaxe_1_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_1/pickaxe_1_{}.png", 4)
pickaxe_3_img, pickaxe_3_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_3/pickaxe_3_{}.png", 4)
pickaxe_77_img, pickaxe_77_imgs = load_round_tool_imgs("data/sprites/tools/pickaxe_77/pickaxe_77_{}.png", 4)

tile_imgs = {None: none_img,
             0: none_img,
             1: grass_img,
             2: dirt_img,
             3: stone_img,
             4: ore_img,
             5: granite_img,
             9: tnt_img,
             11: plank_img,
             12: wood_img,
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
             101: bush_img,
             102: smalltree_img,
             103: cactus_img,
             105: leave_img,
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
             130: bedroll_of_pelts_img,
             151: group_img,
             201: cloud_img,
             203: tnt_1_img,

             501: sword_1_img,
             502: sword_77_img,
             530: pickaxe_0_img,
             531: pickaxe_1_img,
             532: pickaxe_77_img,
             533: pickaxe_3_img,
             610: summonerSlimeBoss_img,

             801: stick_img,
             }
count_tiles = len(tile_imgs)

tile_many_imgs = {101: bush_imgs,
                  201: cloud_imgs,
                  203: tnt_imgs,

                  501: sword_1_imgs,
                  502: sword_77_imgs,
                  530: pickaxe_0_imgs,
                  531: pickaxe_1_imgs,
                  532: pickaxe_77_imgs,
                  533: pickaxe_3_imgs,
                  }

IDX_TOOLS = {501, 502, 530, 531, 532, 533, 610}

# блоки через которые нельзя пройти
PHYSBODY_TILES = {1, 2, 3, 4, 5, 9, 11, 12, 103, 124, 128}

SEMIPHYSBODY_TILES = {120, 127}
# блоки которые должны стоять на блоке (есть 0 т.к. на воздух ставить нельзя)
STANDING_TILES = {0, 101, 102, 103, 110, 120, 121, 122, 123, 125, 126, 130}
# предметы которые нельзя физически поставить
ITEM_TILES = {51, 52, 53, 55, 56, 58, 61, 62, 63, 64, 65, 66, 801}

# специальные каринки предметов для инвентаря
tile_hand_imgs = {k: tile_imgs[k] if k in ITEM_TILES else transform_hand(i) for k, i in tile_imgs.items()}
tile_hand_imgs[102] = load_img("data/sprites/tiles/small_tree_item.png",
                               HAND_RECT)  # тк есть прозрачность создана собственная картинка
tile_hand_imgs[121] = load_img("data/sprites/tiles/table_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[122] = load_img("data/sprites/tiles/chear_item.png", HAND_RECT)  # тк есть прозрачность
tile_hand_imgs[130] = bedroll_of_pelts_item_img

tile_words = {None: "None",
              0: "None",
              1: "Трава",
              2: "Земля",
              3: "Камень",
              4: "Блор",
              5: "Гранит",
              9: "Динамит",
              11: "Доски",
              12: "Древесина",
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
              101: "Куст",
              102: "Маленькое дерево",
              103: "Кактус",
              105: "Листва",
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
              130: "Спальный мешок из шкур",
              151: "Группа обектов",
              201: "Облако",
              202: "Облака",
              203: "Активный динамит",
              204: "Активные динамиты",

              501: "Железный меч",
              502: "Золотой меч",
              530: "Деревянная кирка",
              531: "Железная кирка",
              532: "Золотая кирка",
              533: "Медная кирка",

              610: "Призыатель босса слизней",

              801: "Палка"
              }

# INIT_TILES ====================================================

# Прочность блоков
TILES_SOLIDITY = {
    1: 15,
    2: 20,
    3: 35,
    4: 60,
    5: 80,
    9: 60,
    11: 45,
    12: 45,
    101: 25,
    102: 25,
    103: 25,
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
}

DYNAMITE_NOT_BREAK = {5, 120}  # granite water

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
    105: [(105, 1, 1), (102, 1, 0.13), (801, (1, 2), 0.25)]
}


def item_of_break_tile(tile):
    # (index, count, chance)
    ttile = tile[0]
    items = [(ttile, 1, 1)]
    if ttile in tile_drops:
        items = tile_drops[ttile]
    if ttile == 101:  # куст с ягодами
        items += item_of_right_click_tile(tile, res=False)
    res = [(i, cnt) for i, cnt, ch in items if ch == 1 or random.randint(0, 100 * 100) <= ch * 100 * 100]
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


if DEBUG_DRAW_TILES:
    clock = pg.time.Clock()
    screen_.fill("green")
    x, y = 5, 5
    for im in break_imgs:
        screen_.blit(im, (x, y))
        x += im.get_width() + 5
    pg.display.flip()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
