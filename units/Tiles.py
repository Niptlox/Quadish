import random

from units.Graphics.Image import *
from units.UI.Translate import get_translated_tiles
from units.ItemSprites import (create_sulfur_img, create_chitin_img, create_hide_img,
                               create_raw_meat_img, create_cooked_meat_img,
                               create_space_dust_img, create_stick_img)

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

player_img = create_player_sprite(size=(TSIZE - 10, TSIZE - 2))
live_imgs = load_imgs("data/sprites/player/lives_{}.png", 5, size=(20, 20))
goldlive_imgs = load_imgs("data/sprites/player/goldherts_{}.png", 5, size=(20, 20))
bg_live_img = load_img("data/sprites/player/bg_live.png", size=(20, 20))
bg_livecreative_img = load_img("data/sprites/player/bg_livecreative.png", size=(24, 24))

hand_pass_img = create_hand_sprite(HAND_SIZE)
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

# Готовых спрайтов земли (ground_{i}.png) хватает только на 4 биома
# (desert=0, savanna=1, tropical_woodland=2, tundra=3 — см. biome_names в
# units/biomes.py). Остальные 5 наземных биомов красились как None
# (дефолт) и визуально не отличались друг от друга. Вместо новых
# ассетов подкрашиваем базовую текстуру земли цветом биома (тем же,
# которым биом обозначен на карте биомов) — дёшево и не требует арта.
_extra_biome_ground_colors = {
    4: (106, 144, 38),   # seasonal_forest
    5: (33, 77, 41),     # rainforest
    6: (86, 179, 106),   # temperate_forest
    7: (34, 61, 53),     # temperate_rainforest
    8: (35, 114, 94),    # boreal_forest
}


def _is_grass_pixel(r, g, b, a):
    """Травяной ли это пиксель спрайта земли.

    Границу травы и земли берём по самому пикселю, а не по номеру строки:
    в спрайте она неровная — на правом краю земля начинается на строку
    выше, чем в середине. У травы зелёный канал старше красного и синего,
    у земли наоборот (104,73,55 против 96,178,49).
    """
    return bool(a) and g > r and g > b


def _grass_tint_overlay(img, color, alpha):
    """Накладка цвета биома ТОЛЬКО по травяным пикселям."""
    overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA, 32)
    overlay.fill((0, 0, 0, 0))
    w, h = img.get_size()
    tint = (*color, alpha)
    for y in range(h):
        for x in range(w):
            if _is_grass_pixel(*img.get_at((x, y))):
                overlay.set_at((x, y), tint)
    return overlay


def _tinted_ground_set(color, alpha=90):
    """Земля биома: красится трава, а не весь блок.

    Раньше накладка заливала тайл целиком, и в лесных биомах «земля с травой»
    зеленела вся — вместе с землёй под дёрном, хотя цвет биома относится
    только к траве.
    """
    tinted = []
    for img in (ground_img, ground_L_img, ground_R_img, ground_LR_img):
        t = img.copy()
        t.blit(_grass_tint_overlay(img, color, alpha), (0, 0))
        tinted.append(t)
    return tuple(tinted)


for _biome_id, _color in _extra_biome_ground_colors.items():
    ground_imgs[_biome_id] = _tinted_ground_set(_color)
stone_img = load_img("data/sprites/tiles/Stone.png")
back_stone_img = load_img("data/sprites/backtiles/BackStone2.png")
# create_tile_image("#57534E")

ore_img = (load_img("data/sprites/tiles/ore.png"))
stone_brick_img = (load_img("data/sprites/tiles/blocksstoun0.png"))
stone_brick_1_img = (load_img("data/sprites/tiles/blocksstoun1.png"))
stone_brick_2_img = (load_img("data/sprites/tiles/blocksstoun2.png"))

# Ресурсы: пиксель-арт (units/ItemSprites.py). Раньше это были плоские
# квадраты одного цвета — в инвентаре сера от жареного мяса отличалась
# только оттенком.
sulfur_item_img = create_sulfur_img()          # сера (добыча бесов)
chitin_item_img = create_chitin_img()          # хитин (скорпионы/крабы)
hide_item_img = create_hide_img()              # шкура (общий ресурс зверей)
raw_meat_item_img = create_raw_meat_img()      # сырое мясо (общее)
cooked_meat_item_img = create_cooked_meat_img()  # жареное мясо (общее)
space_dust_item_img = create_space_dust_img()  # космическая пыль (пришельцы)


def create_timer_block_img():
    """Таймер: часовой циферблат со стрелками поверх обычного блока."""
    img = create_tile_image("#78716C")
    cx, cy = img.get_width() // 2, img.get_height() // 2
    r = min(img.get_width(), img.get_height()) // 2 - 4
    pygame.draw.circle(img, "#F5F5F4", (cx, cy), r)
    pygame.draw.circle(img, "#1C1917", (cx, cy), r, width=1)
    pygame.draw.line(img, "#1C1917", (cx, cy), (cx, cy - r + 2), 2)
    pygame.draw.line(img, "#1C1917", (cx, cy), (cx + r // 2, cy), 2)
    return img


def create_pressure_plate_img():
    """Нажимная плита: тонкая жёлтая плашка на обычном блоке."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pad = 4
    pygame.draw.rect(img, "#FDE047", (pad, pad, w - pad * 2, h - pad * 2), border_radius=3)
    pygame.draw.rect(img, "#1C1917", (pad, pad, w - pad * 2, h - pad * 2), width=1, border_radius=3)
    return img


timer_block_img = create_timer_block_img()
pressure_plate_img = create_pressure_plate_img()


def create_wire_img():
    """Провод: тонкий медный крест поверх обычного блока."""
    img = create_tile_image("#44403C")
    w, h = img.get_size()
    cx, cy = w // 2, h // 2
    pygame.draw.line(img, "#EA580C", (2, cy), (w - 3, cy), 3)
    pygame.draw.line(img, "#EA580C", (cx, 2), (cx, h - 3), 3)
    pygame.draw.circle(img, "#FDBA74", (cx, cy), 2)
    return img


def create_lever_img(on):
    """Рычаг: диагональная планка на подставке — наклон меняется вкл/выкл."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pygame.draw.rect(img, "#3F3A36", (w // 3, h - 8, w // 3, 6), border_radius=1)
    color = "#22C55E" if on else "#71717A"
    base = (w // 2, h - 8)
    tip = (w // 2 + (6 if on else -6), 6)
    pygame.draw.line(img, color, base, tip, 3)
    pygame.draw.circle(img, color, base, 3)
    return img


def create_lamp_img(on):
    """Лампа: колба, светится жёлтым во включённом состоянии."""
    img = create_tile_image("#3F3A36")
    w, h = img.get_size()
    cx, cy = w // 2, h // 2
    r = min(w, h) // 2 - 5
    color = "#FDE047" if on else "#57534E"
    pygame.draw.circle(img, color, (cx, cy), r)
    pygame.draw.circle(img, "#1C1917", (cx, cy), r, width=1)
    if on:
        pygame.draw.circle(img, (255, 255, 255, 90), (cx - r // 3, cy - r // 3), max(1, r // 3))
    return img


def create_not_gate_img():
    """НЕ: классический символ инвертора — треугольник с кружком на выходе."""
    img = create_tile_image("#78716C")
    w, h = img.get_size()
    tri = [(4, 5), (4, h - 5), (w - 9, h // 2)]
    pygame.draw.polygon(img, "#F5F5F4", tri)
    pygame.draw.polygon(img, "#1C1917", tri, width=1)
    pygame.draw.circle(img, "#F5F5F4", (w - 5, h // 2), 3)
    pygame.draw.circle(img, "#1C1917", (w - 5, h // 2), 3, width=1)
    return img


def create_and_gate_img():
    """И: D-образная форма — классический символ вентиля И."""
    img = create_tile_image("#78716C")
    w, h = img.get_size()
    rect = pygame.Rect(4, 5, w // 2, h - 10)
    pygame.draw.rect(img, "#F5F5F4", rect, border_top_right_radius=0, border_bottom_right_radius=0)
    pygame.draw.circle(img, "#F5F5F4", (rect.right, h // 2), (h - 10) // 2)
    pygame.draw.rect(img, "#1C1917", rect, width=1)
    return img


def create_or_gate_img():
    """ИЛИ: форма "щита" с выпуклой передней гранью — символ вентиля ИЛИ."""
    img = create_tile_image("#78716C")
    w, h = img.get_size()
    pygame.draw.polygon(img, "#F5F5F4", [(4, 5), (w // 2, 5), (w // 2, h - 5), (4, h - 5)])
    pygame.draw.circle(img, "#F5F5F4", (w // 2, h // 2), (h - 10) // 2 + 2)
    pygame.draw.circle(img, "#1C1917", (w // 2, h // 2), (h - 10) // 2 + 2, width=1)
    return img


wire_img = create_wire_img()
lever_on_img = create_lever_img(True)
lever_off_img = create_lever_img(False)
lamp_on_img = create_lamp_img(True)
lamp_off_img = create_lamp_img(False)
not_gate_img = create_not_gate_img()
and_gate_img = create_and_gate_img()
or_gate_img = create_or_gate_img()


def create_chunk_loader_img(on):
    """Прогрузчик чанка: маячок-антенна, светится, пока держит область
    вокруг себя от выгрузки."""
    img = create_tile_image("#3F3A36")
    w, h = img.get_size()
    cx = w // 2
    pygame.draw.rect(img, "#57534E", (cx - 2, h // 3, 4, h - h // 3 - 4))
    pygame.draw.polygon(img, "#78716C", [(cx - w // 3, h - 4), (cx + w // 3, h - 4),
                                         (cx + 3, h // 3), (cx - 3, h // 3)])
    color = "#22D3EE" if on else "#44403C"
    pygame.draw.circle(img, color, (cx, h // 3 - 2), 4)
    pygame.draw.circle(img, "#1C1917", (cx, h // 3 - 2), 4, width=1)
    if on:
        pygame.draw.circle(img, (34, 211, 238, 110), (cx, h // 3 - 2), 6, width=1)
    return img


chunk_loader_on_img = create_chunk_loader_img(True)
chunk_loader_off_img = create_chunk_loader_img(False)


def create_delay_block_img():
    """Задержка сигнала: песочные часы поверх обычного блока."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pad = 6
    top = [(pad, pad), (w - pad, pad), (w // 2, h // 2)]
    bottom = [(pad, h - pad), (w - pad, h - pad), (w // 2, h // 2)]
    pygame.draw.polygon(img, "#FDBA74", top)
    pygame.draw.polygon(img, "#FDBA74", bottom)
    pygame.draw.polygon(img, "#1C1917", top, width=1)
    pygame.draw.polygon(img, "#1C1917", bottom, width=1)
    pygame.draw.line(img, "#1C1917", (pad, pad), (w - pad, pad), 2)
    pygame.draw.line(img, "#1C1917", (pad, h - pad), (w - pad, h - pad), 2)
    return img


delay_block_img = create_delay_block_img()


def create_music_block_img(flash=False):
    """Муз-блок: деревянная панель с нотой, вспыхивает при срабатывании."""
    base_color = "#FDE047" if flash else "#8B6D4C"
    img = create_tile_image(base_color)
    w, h = img.get_size()
    note_color = "#1C1917" if flash else "#F5F5F4"
    stem_x = int(w * 0.55)
    pygame.draw.line(img, note_color, (stem_x, int(h * 0.2)), (stem_x, int(h * 0.65)), 2)
    pygame.draw.line(img, note_color, (stem_x, int(h * 0.2)), (int(w * 0.75), int(h * 0.28)), 2)
    pygame.draw.ellipse(img, note_color, (int(w * 0.3), int(h * 0.55), int(w * 0.28), int(h * 0.22)))
    return img


music_block_img = create_music_block_img(False)
music_block_flash_img = create_music_block_img(True)


def create_receiver_img():
    """Приёмник рации: спутниковая тарелка (вогнутая дуга)."""
    img = create_tile_image("#3F3A36")
    w, h = img.get_size()
    cx, cy = w // 2, int(h * 0.65)
    r = int(min(w, h) * 0.42)
    pygame.draw.arc(img, "#A8A29E", (cx - r, cy - r, r * 2, r * 2), 3.4, 6.0, 4)
    pygame.draw.line(img, "#78716C", (cx, cy), (cx, int(h * 0.2)), 2)
    pygame.draw.circle(img, "#22D3EE", (cx, int(h * 0.2)), 2)
    return img


receiver_img = create_receiver_img()


def create_transmitter_img():
    """Передатчик рации: мачта с расходящимися волнами сигнала."""
    img = create_tile_image("#3F3A36")
    w, h = img.get_size()
    cx = w // 2
    pygame.draw.line(img, "#78716C", (cx, h - 4), (cx, int(h * 0.25)), 2)
    pygame.draw.circle(img, "#F87171", (cx, int(h * 0.2)), 2)
    for r in (5, 9):
        pygame.draw.arc(img, "#F87171", (cx - r, int(h * 0.2) - r, r * 2, r * 2), 0.6, 2.6, 1)
    return img


transmitter_img = create_transmitter_img()


def create_lore_tablet_img():
    """Плита с надписью: тёмный камень со строками незнакомых знаков.

    Основной канал подачи сюжета (docs/STORY.md) — читается правым кликом.
    Знаки рисуем штрихами, а не текстом: во-первых, шрифт не обязан иметь
    нужные глифы, во-вторых, «непонятная письменность» и должна читаться
    как узор, пока скафандр её не перевёл."""
    img = create_tile_image("#44403C")
    w, h = img.get_size()
    pygame.draw.rect(img, "#57534E", (3, 3, w - 6, h - 6), border_radius=2)
    pygame.draw.rect(img, "#292524", (3, 3, w - 6, h - 6), width=1, border_radius=2)
    ink = "#FDE047"
    # четыре строки «письма» разной длины — похоже на текст, не на орнамент
    for row, dashes in enumerate(((2, 5, 3), (4, 2, 4), (3, 6), (2, 3, 2))):
        y = 7 + row * 5
        x = 6
        for length in dashes:
            if x + length > w - 6:
                break
            pygame.draw.line(img, ink, (x, y), (x + length, y), 1)
            x += length + 3
    return img


lore_tablet_img = create_lore_tablet_img()


def create_lava_img(phase=0):
    """Лава: тёмно-красная порода с пузырями. Кадры сдвигают пузыри, из-за
    чего лава «кипит» (см. ANIMATED_TILES ниже)."""
    img = create_tile_image("#7F1D1D", bd=0)
    w, h = img.get_size()
    # горячие прожилки
    for i, y in enumerate(range(3, h, 7)):
        off = (phase * 3 + i * 5) % w
        pygame.draw.line(img, "#EA580C", (0, y), (w, y), 2)
        pygame.draw.line(img, "#FDE047", (off, y), (min(w, off + 6), y), 1)
    # пузыри
    bubbles = ((6, 22, 3), (17, 9, 2), (25, 26, 2), (12, 16, 2))
    for i, (bx, by, r) in enumerate(bubbles):
        if (i + phase) % 4 != 3:            # пузырь то есть, то лопнул
            cy = (by + phase * 2) % (h - 2) + 1
            pygame.draw.circle(img, "#FB923C", (bx, cy), r)
            pygame.draw.circle(img, "#FEF08A", (bx, cy), max(1, r - 1))
    return img


lava_imgs = [create_lava_img(p) for p in range(4)]
lava_img = lava_imgs[0]


def create_hopper_img():
    """Воронка: сужающийся книзу жёлоб."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pygame.draw.polygon(img, "#3F3A36", [(3, 5), (w - 4, 5), (w - 9, h - 10), (8, h - 10)])
    pygame.draw.polygon(img, "#1C1917", [(3, 5), (w - 4, 5), (w - 9, h - 10), (8, h - 10)], width=1)
    pygame.draw.rect(img, "#292524", (w // 2 - 3, h - 10, 6, 7))
    pygame.draw.rect(img, "#1C1917", (w // 2 - 3, h - 10, 6, 7), width=1)
    return img


def create_conveyor_img(to_right=True):
    """Конвейер: лента со стрелками направления."""
    img = create_tile_image("#44403C")
    w, h = img.get_size()
    pygame.draw.rect(img, "#292524", (0, 6, w, h - 12))
    for x in range(2, w - 4, 8):
        pts = [(x, 11), (x + 5, h // 2), (x, h - 12)] if to_right else \
              [(x + 5, 11), (x, h // 2), (x + 5, h - 12)]
        pygame.draw.polygon(img, "#FDE047", pts)
    pygame.draw.line(img, "#78716C", (0, 6), (w, 6))
    pygame.draw.line(img, "#78716C", (0, h - 6), (w, h - 6))
    return img


def create_dropper_img():
    """Дропер: короб с раструбом вниз."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pygame.draw.rect(img, "#3F3A36", (4, 4, w - 8, h - 12), border_radius=2)
    pygame.draw.rect(img, "#1C1917", (4, 4, w - 8, h - 12), width=1, border_radius=2)
    pygame.draw.polygon(img, "#292524", [(w // 2 - 6, h - 8), (w // 2 + 6, h - 8),
                                         (w // 2 + 2, h - 2), (w // 2 - 2, h - 2)])
    pygame.draw.circle(img, "#FDE047", (w // 2, h // 2 - 2), 3)
    return img


def create_chopper_img():
    """Лесоруб: топор на станине."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pygame.draw.rect(img, "#3F3A36", (2, h - 9, w - 4, 7), border_radius=2)
    pygame.draw.line(img, "#A16207", (w // 2 - 6, h - 10), (w // 2 + 4, 6), 3)
    pygame.draw.polygon(img, "#D6D3D1", [(w // 2 + 2, 4), (w - 4, 9), (w // 2 + 6, 14)])
    pygame.draw.polygon(img, "#1C1917", [(w // 2 + 2, 4), (w - 4, 9), (w // 2 + 6, 14)], width=1)
    return img


def create_asteroid_img():
    """Астероидный камень: тёмная порода с кратерами. Тело астероидов —
    единственная твердь в космосе, до неё в вакууме встать не на что."""
    img = create_tile_image("#3F3A36")
    w, h = img.get_size()
    for cx, cy, r in ((8, 9, 4), (21, 7, 3), (14, 21, 5), (26, 22, 3)):
        pygame.draw.circle(img, "#292524", (cx, cy), r)
        pygame.draw.circle(img, "#57534E", (cx - 1, cy - 1), max(1, r - 2))
    return img


def create_dust_vein_img():
    """Пылевая жила: астероидная порода с прожилками космической пыли —
    первый источник пыли до того, как игрок соберёт пылеуловитель."""
    img = create_asteroid_img()
    w, h = img.get_size()
    for x0, y0, x1, y1 in ((4, 22, 13, 12), (13, 12, 20, 17), (18, 4, 26, 11)):
        pygame.draw.line(img, "#38BDF8", (x0, y0), (x1, y1), 2)
        pygame.draw.line(img, "#E0F2FE", (x0, y0), (x1, y1), 1)
    for cx, cy in ((6, 6), (25, 26)):
        pygame.draw.circle(img, "#7DD3FC", (cx, cy), 2)
    return img


def create_star_crystal_img():
    """Звёздный кристалл: гранёный самоцвет в астероиде. Даёт рубины —
    чтобы в космосе было что копать не только ради пыли."""
    img = create_asteroid_img()
    w, h = img.get_size()
    cx, cy = w // 2, h // 2
    body = [(cx, 4), (w - 6, cy - 3), (cx + 4, h - 5), (cx - 4, h - 5), (6, cy - 3)]
    pygame.draw.polygon(img, "#C084FC", body)
    pygame.draw.polygon(img, "#F5D0FE", [(cx, 4), (cx + 4, cy), (cx, h - 6), (cx - 4, cy)])
    pygame.draw.polygon(img, "#1C1917", body, width=1)
    return img


def create_dust_collector_img(on):
    """Пылеуловитель: раскрытая сеть-парус на мачте. Ловит пыль только в
    вакууме — под крышей парусу нечего ловить (см. DustCollector)."""
    img = create_tile_image("#1E293B")
    w, h = img.get_size()
    pygame.draw.rect(img, "#334155", (w // 2 - 2, h // 2, 4, h // 2 - 3))
    net = "#38BDF8" if on else "#475569"
    pygame.draw.arc(img, net, (3, 2, w - 6, h - 6), 0.2, 2.95, 3)
    for x in range(6, w - 5, 5):
        pygame.draw.line(img, net, (x, 5), (w // 2, h // 2), 1)
    pygame.draw.circle(img, "#E0F2FE" if on else "#334155", (w // 2, h // 2), 3)
    return img


def create_engine_img(body, flywheel, on):
    """Двигатель: корпус с маховиком и выхлопом. Все четыре двигателя —
    один силуэт в разных цветах: игроку важно с первого взгляда отличить
    двигатель от вентиля, а уже потом — какой именно."""
    img = create_tile_image(body)
    w, h = img.get_size()
    # станина
    pygame.draw.rect(img, "#292524", (2, h - 8, w - 4, 6), border_radius=1)
    # корпус
    pygame.draw.rect(img, "#3F3A36", (4, 6, w - 8, h - 15), border_radius=2)
    pygame.draw.rect(img, "#1C1917", (4, 6, w - 8, h - 15), width=1, border_radius=2)
    # маховик: светится, когда двигатель даёт импульсы
    cx, cy = w // 2, (6 + h - 9) // 2
    r = max(3, (h - 17) // 2)
    pygame.draw.circle(img, flywheel if on else "#44403C", (cx, cy), r)
    pygame.draw.circle(img, "#1C1917", (cx, cy), r, width=1)
    pygame.draw.line(img, "#1C1917", (cx - r + 1, cy), (cx + r - 1, cy), 1)
    # выхлоп сверху — есть только на ходу
    if on:
        pygame.draw.rect(img, flywheel, (w - 9, 1, 3, 5))
    else:
        pygame.draw.rect(img, "#44403C", (w - 9, 1, 3, 5))
    return img


def create_portal_img(phase=0):
    """Портал: тёмная рама с воронкой-вихрем внутри. Кадры проворачивают
    вихрь, поэтому портал видно даже боковым зрением."""
    img = create_tile_image("#1C1917", bd=0)
    w, h = img.get_size()
    pygame.draw.rect(img, "#3F3A36", (0, 0, w, h), width=3)
    cx, cy = w // 2, h // 2
    colors = ("#7C3AED", "#A855F7", "#C084FC", "#E9D5FF")
    for i, r in enumerate(range(max(2, min(w, h) // 2 - 3), 1, -3)):
        color = colors[(i + phase) % len(colors)]
        pygame.draw.circle(img, color, (cx, cy), r, width=2)
    pygame.draw.circle(img, "#FAF5FF", (cx, cy), 2)
    return img


def create_nest_img(on):
    """Гнездо голема: каменная чаша; под сигналом внутри разогревается
    камень — из него и вылезает голем (docs/FARMS_CONCEPT.md)."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    pygame.draw.polygon(img, "#44403C", [(3, 6), (w - 4, 6), (w - 8, h - 3), (7, h - 3)])
    pygame.draw.polygon(img, "#1C1917", [(3, 6), (w - 4, 6), (w - 8, h - 3), (7, h - 3)], width=1)
    core = "#F97316" if on else "#78716C"
    pygame.draw.circle(img, core, (w // 2, h // 2 + 2), 5)
    pygame.draw.circle(img, "#FDE047" if on else "#A8A29E", (w // 2, h // 2 + 2), 2)
    if on:
        for x in (w // 3, w // 2, w - w // 3):
            pygame.draw.line(img, "#FB923C", (x, 5), (x, 2), 1)
    return img


def create_blore_column_img(up=True):
    """Блоровый столб: шахта с жилой блора внутри.

    Два отдельных блока вместо одного «универсального лифта» — направление
    видно по самой шахте, а не по тому, зажата ли клавиша. Из этого сразу
    строится нормальный двухполосный подъёмник: слева вверх, справа вниз.

    Идея из сюжета (docs/STORY.md): переход держится на блоре, то есть
    блор — это и есть вещество перемещения. Подъём стоит блора, спуск —
    дешевле: падать планета помогает и так.
    """
    img = create_tile_image("#3F3A36", bd=0)
    w, h = img.get_size()
    pygame.draw.rect(img, "#292524", (5, 0, w - 10, h))
    for side in (3, w - 6):
        pygame.draw.rect(img, "#78716C", (side, 0, 3, h))
    # жила блора вдоль шахты
    pygame.draw.line(img, "#4C1D95", (w // 2, 0), (w // 2, h), 3)
    arrow = "#22D3EE" if up else "#FBBF24"
    for y in range(2, h, 8):
        if up:
            pts = [(w // 2 - 4, y + 5), (w // 2 + 4, y + 5), (w // 2, y)]
        else:
            pts = [(w // 2 - 4, y), (w // 2 + 4, y), (w // 2, y + 5)]
        pygame.draw.polygon(img, arrow, pts)
    return img


def create_echo_img():
    """Отголосок: подвешенная в воздухе блоровая искра.

    Не человек и не статуя — намеренно: соплеменников не осталось, и НПС в
    этой истории может быть только записью (docs/STORYBOOK.md).
    """
    img = create_tile_image("#00000000", bd=0)
    w, h = img.get_size()
    pygame.draw.circle(img, (76, 29, 149, 90), (w // 2, h // 2), w // 2 - 3)
    pygame.draw.circle(img, (139, 92, 246, 200), (w // 2, h // 2), w // 3)
    pygame.draw.circle(img, (221, 214, 254, 240), (w // 2, h // 2), w // 6)
    for i in range(0, 360, 60):
        import math as _m
        a = _m.radians(i)
        pygame.draw.line(img, (167, 139, 250, 160),
                         (w // 2 + int(_m.cos(a) * w // 4), h // 2 + int(_m.sin(a) * h // 4)),
                         (w // 2 + int(_m.cos(a) * (w // 2 - 3)), h // 2 + int(_m.sin(a) * (h // 2 - 3))), 2)
    return img


echo_img = create_echo_img()


def create_trampoline_img():
    """Слизневый батут: доски, натянутые слизью.

    Самый ранний транспорт в игре — по сюжету слизни это первое живое, что
    герой встречает (docs/STORY.md), а слизь в рецептах уже означает прыжок
    (зелье прыжка 351). Батут собирается из досок и слизи, то есть из того,
    что есть у игрока на пятой минуте, и решает ровно ту задачу, из-за
    которой вертикальный мир враждебен с самого начала: подняться на уступ
    и не разбиться, спрыгнув с него.
    """
    img = create_tile_image("#6B4423", bd=0)
    w, h = img.get_size()
    for x in range(2, w - 2, 6):        # доски рамы
        pygame.draw.rect(img, "#8B5A2B", (x, h - 7, 5, 5))
    pygame.draw.rect(img, "#4D7C0F", (2, 3, w - 4, h - 9), border_radius=4)
    pygame.draw.rect(img, "#84CC16", (2, 3, w - 4, h - 9), width=2, border_radius=4)
    pygame.draw.arc(img, "#BEF264", (4, 1, w - 8, h - 10), 0.3, 2.9, 2)
    return img


def create_blore_track_img(right=True):
    """Блоровая дорожка: та же жила блора, что в столбах, но положенная вбок.

    Одна идея на весь транспорт: блор — вещество перемещения, и он несёт всё,
    что в нём стоит, — и игрока, и лежащие предметы. Поэтому дорожка это
    одновременно горизонталь для игрока и логистика: отдельный «рельс» и
    отдельный «конвейер» были бы двумя блоками про одно и то же.
    """
    img = create_tile_image("#3F3A36", bd=0)
    w, h = img.get_size()
    pygame.draw.rect(img, "#292524", (0, 5, w, h - 10))
    for side in (3, h - 6):
        pygame.draw.rect(img, "#78716C", (0, side, w, 3))
    pygame.draw.line(img, "#4C1D95", (0, h // 2), (w, h // 2), 3)
    for x in range(2, w, 8):
        if right:
            pts = [(x, h // 2 - 4), (x, h // 2 + 4), (x + 5, h // 2)]
        else:
            pts = [(x + 5, h // 2 - 4), (x + 5, h // 2 + 4), (x, h // 2)]
        pygame.draw.polygon(img, "#22D3EE", pts)
    return img


trampoline_img = create_trampoline_img()
blore_track_imgs = [create_blore_track_img(True), create_blore_track_img(False)]
blore_track_img = blore_track_imgs[0]

hopper_img = create_hopper_img()
conveyor_imgs = [create_conveyor_img(True), create_conveyor_img(False)]
conveyor_img = conveyor_imgs[0]
dropper_img = create_dropper_img()
chopper_img = create_chopper_img()

engine_fuel_on_img = create_engine_img("#57534E", "#FB923C", True)
engine_fuel_off_img = create_engine_img("#57534E", "#FB923C", False)
engine_creative_img = create_engine_img("#4C1D95", "#C084FC", True)
engine_space_on_img = create_engine_img("#334155", "#38BDF8", True)
engine_space_off_img = create_engine_img("#334155", "#38BDF8", False)
engine_hell_on_img = create_engine_img("#7F1D1D", "#FDE047", True)
engine_hell_off_img = create_engine_img("#7F1D1D", "#FDE047", False)

portal_imgs = [create_portal_img(p) for p in range(4)]
portal_img = portal_imgs[0]

nest_on_img = create_nest_img(True)
nest_off_img = create_nest_img(False)

lift_up_img = create_blore_column_img(True)
lift_down_img = create_blore_column_img(False)

asteroid_img = create_asteroid_img()
dust_vein_img = create_dust_vein_img()
star_crystal_img = create_star_crystal_img()
dust_collector_on_img = create_dust_collector_img(True)
dust_collector_off_img = create_dust_collector_img(False)


def create_dynamite_img(lit=False, spark_bright=False):
    """Динамит: пучок из 3 шашек с бандажами и фитилём (раньше был просто
    закрашенный красный квадрат). lit — фитиль подожжён (анимация мигания
    после активации, см. Dynamite в units/Objects/Entities.py)."""
    img = create_tile_image("#57534E")
    w, h = img.get_size()
    stick_w = max(2, w // 4)
    gap = 1
    total_w = stick_w * 3 + gap * 2
    x0 = (w - total_w) // 2
    top, bottom = 5, h - 3
    for i in range(3):
        x = x0 + i * (stick_w + gap)
        pygame.draw.rect(img, "#B91C1C", (x, top, stick_w, bottom - top), border_radius=1)
        pygame.draw.rect(img, "#78350F", (x, top + 2, stick_w, 2))
        pygame.draw.rect(img, "#78350F", (x, bottom - 4, stick_w, 2))
        pygame.draw.rect(img, "#1C1917", (x, top, stick_w, bottom - top), width=1, border_radius=1)
    fuse_x = w // 2
    fuse_color = "#FDBA74" if lit else "#78716C"
    pygame.draw.line(img, fuse_color, (fuse_x, top), (fuse_x + 3, max(0, top - 5)), 2)
    if lit:
        spark_r = 3 if spark_bright else 2
        spark_color = "#FDE047" if spark_bright else "#F97316"
        pygame.draw.circle(img, spark_color, (fuse_x + 3, max(0, top - 5)), spark_r)
    return img


tnt_img = create_dynamite_img(lit=False)  # tnt

# granite_img = create_tile_image("#09070A")
granite_img = load_img("data/sprites/tiles/Granite.PNG")

tnt_1_img = create_dynamite_img(lit=True, spark_bright=True)  # tnt activ
tnt_imgs = [tnt_1_img, create_dynamite_img(lit=True, spark_bright=False)]  # tnt activ

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
def create_water_img(level=4, deep=False):
    """Вода с уровнем заполнения 1..4 (4 — полный тайл).

    Рисуем процедурно, а не одной картинкой, ради двух вещей сразу:

    * **Уровни.** Вода в тайле может стоять не до потолка — из этого получается
      видимая многоуровневость: у берега мелко, к середине глубоко, и озеро
      перестаёт выглядеть залитым по линейке прямоугольником.
    * **Кромка.** У поверхности воды нужен светлый блик, а в глубине —
      затемнение. Одной текстурой это не получить: тайл не знает, где он.
    """
    img = pygame.Surface(TILE_RECT, pygame.SRCALPHA, 32)
    w, h = img.get_size()
    fill_h = max(4, h * level // 4)
    top = h - fill_h
    body = (36, 108, 168, 190) if not deep else (20, 62, 112, 215)
    # тело воды: вертикальный градиент — сверху светлее
    for y in range(top, h):
        k = (y - top) / max(1, fill_h)
        col = (int(body[0] * (1 - k * 0.35)), int(body[1] * (1 - k * 0.3)),
               int(body[2] * (1 - k * 0.2)), body[3])
        pygame.draw.line(img, col, (0, y), (w, y))
    # блик на кромке: две волны, чтобы поверхность читалась как поверхность
    crest = (150, 214, 245, 230)
    pygame.draw.line(img, crest, (0, top), (w, top), 2)
    for x in range(0, w, 8):
        pygame.draw.line(img, (200, 236, 252, 190), (x + 1, top + 2), (x + 4, top + 2))
    # блики в толще: редкие короткие штрихи, читаются как игра света
    for i, (bx, by) in enumerate(((5, 9), (19, 14), (11, 22), (25, 27))):
        if by <= top:
            continue
        pygame.draw.line(img, (120, 190, 230, 90), (bx, by), (bx + 5, by), 1)
    return img


# Кадры воды в ОДНОМ наборе: 0..3 — обычная вода от полного тайла к плёнке,
# 4..7 — то же для глубинной. Один набор, а не два, потому что кадр выбирается
# полем tile[2], а оно одно: держать глубокую воду отдельным ТАЙЛОМ значило бы
# второй индекс с той же физикой, теми же правилами и вдвое большим числом
# мест, где о нём надо помнить.
#
# Порядок «полная → мельче» обязателен: state_img по умолчанию 0, а воду
# ставит не только генератор (игрок ставит её из инвентаря, старые миры хранят
# 0). При порядке 1..4 вся уже существующая вода превратилась бы в плёнку.
WATER_TILE = 120
WATER_LEVELS = 4
water_imgs = ([create_water_img(level) for level in (4, 3, 2, 1)]
              + [create_water_img(level, deep=True) for level in (4, 3, 2, 1)])
water_deep_imgs = water_imgs[WATER_LEVELS:]
water_img = water_imgs[0]


def water_frame(level=WATER_LEVELS, deep=False):
    """Кадр тайла воды: уровень заполнения 1..4 и глубинный вариант."""
    level = max(1, min(WATER_LEVELS, level))
    return (WATER_LEVELS - level) + (WATER_LEVELS if deep else 0)
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
def create_activator_img():
    """Активатор: металлическая панель с большой красной кнопкой-триггером
    (раньше была декоративная жёлто-оранжевая розетка без связи с ролью
    блока — не читалось как "нажми, чтобы сработало")."""
    img = create_tile_image("#44403C")
    w, h = img.get_size()
    cx, cy = w // 2, h // 2
    r = min(w, h) // 2 - 3
    pygame.draw.circle(img, "#78716C", (cx, cy), r)
    pygame.draw.circle(img, "#1C1917", (cx, cy), r, width=1)
    pygame.draw.circle(img, "#DC2626", (cx, cy), r - 3)
    pygame.draw.circle(img, "#1C1917", (cx, cy), r - 3, width=1)
    pygame.draw.circle(img, "#F87171", (cx - r // 4, cy - r // 4), max(1, r // 4))
    for bx, by in ((5, 5), (w - 5, 5), (5, h - 5), (w - 5, h - 5)):
        pygame.draw.circle(img, "#292524", (bx, by), 2)
    return img


activator_img = create_activator_img()
commandblock_img = load_img("data/sprites/tiles/commandblock.png")
commandblock_imgs = load_imgs("data/sprites/tiles/CommandBlock/commandblock_{}.png", 14)

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

stick_img = create_stick_img()
blore_ore_img = load_img(r"data\sprites\items\blore_ore.png", None)  # blue ore
copper_ore_img = load_img(r"data\sprites\items\copper_ore.png", None)
gold_ore_img = load_img(r"data\sprites\items\gold_ore.png", None)
iron_ore_img = load_img(r"data\sprites\items\iron_ore.png", None)
silver_ore_img = load_img(r"data\sprites\items\silver_ore.png", None)

ruby_item_img = load_img(r"data\sprites\items\ruby.png", None)

summonerSlimeBoss_img = load_img(r"data/sprites/tools/SummonerSlimeBoss/SummonerSlimeBoss.png", None)


def create_vehicle_item_img(body, detail):
    """Иконка транспортного средства в инвентаре.

    Средство в мире — сущность вдвое шире тайла, в клетку инвентаря она не
    влезает, поэтому иконка рисуется отдельно: силуэт корпуса и цветная
    деталь, по которой средства различаются в хотбаре."""
    img = pygame.Surface(TILE_RECT, pygame.SRCALPHA, 32)
    w, h = img.get_size()
    pygame.draw.polygon(img, body, [(3, h // 2), (w - 4, h // 2), (w - 8, h - 5), (7, h - 5)])
    pygame.draw.polygon(img, "#00000088", [(3, h // 2), (w - 4, h // 2), (w - 8, h - 5), (7, h - 5)], 2)
    pygame.draw.ellipse(img, detail, (w // 4, h // 5, w // 2, h // 3))
    return img


raft_item_img = create_vehicle_item_img("#A16207", "#78350F")
airboat_item_img = create_vehicle_item_img("#C2A878", "#E7E5E4")
crawler_item_img = create_vehicle_item_img("#57534E", "#FDE047")
lava_barge_item_img = create_vehicle_item_img("#7F1D1D", "#FB923C")
void_skiff_item_img = create_vehicle_item_img("#334155", "#38BDF8")

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
             402: sulfur_item_img,
             403: chitin_item_img,
             404: hide_item_img,
             405: raw_meat_item_img,
             406: cooked_meat_item_img,
             408: space_dust_item_img,
             211: timer_block_img,
             212: pressure_plate_img,
             213: wire_img,
             214: lever_off_img,
             215: lamp_off_img,
             216: not_gate_img,
             217: and_gate_img,
             218: or_gate_img,
             219: chunk_loader_off_img,
             220: delay_block_img,
             221: music_block_img,
             222: receiver_img,
             223: transmitter_img,
             300: lore_tablet_img,
             140: lava_img,
             224: hopper_img,
             225: conveyor_img,
             226: dropper_img,
             227: chopper_img,
             228: engine_fuel_off_img,
             229: engine_creative_img,
             230: engine_space_off_img,
             231: engine_hell_off_img,
             232: portal_img,
             233: nest_off_img,
             234: lift_up_img,
             236: lift_down_img,
             239: echo_img,
             237: trampoline_img,
             238: blore_track_img,
             26: asteroid_img,
             27: dust_vein_img,
             28: star_crystal_img,
             235: dust_collector_off_img,
             501: sword_1_img,
             502: sword_77_img,
             503: sword_2_img,
             530: pickaxe_0_img,
             531: pickaxe_1_img,
             532: pickaxe_77_img,
             533: pickaxe_3_img,
             581: spatula_1_img,
             610: summonerSlimeBoss_img,
             611: raft_item_img,
             612: airboat_item_img,
             613: crawler_item_img,
             614: lava_barge_item_img,
             615: void_skiff_item_img,

             801: stick_img,

             1003: back_stone_img,
             }
count_tiles = len(tile_imgs)
print("Count_tiles imgs", count_tiles)
tile_many_imgs = {225: conveyor_imgs,
                  # Вода: кадр = уровень заполнения (см. create_water_img)
                  120: water_imgs,
                  238: blore_track_imgs,
                  101: bush_imgs,
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

# 611-615 — транспортные средства (units/Objects/Vehicles.py): предмет
# ставит средство в мир, поэтому он инструмент, а не блок.
IDX_TOOLS = {501, 502, 503, 530, 531, 532, 533, 581, 610,
             611, 612, 613, 614, 615}

# EATS = {52: 10, 53: 2, 56: 8, 55: 100, 401: 8}

# растения растущее друг на друге например кактус
MULTI_BLOCK_PLANTS = {103, }
# растения растущее только на земле с травой
ON_EARTHEN_PLANTS = {101, 102, 103, 104}

# блоки через которые нельзя пройти
PHYSBODY_TILES = {1, 2, 3, 4, 5, 9, 11, 12, 21, 22, 23, 24, 25, 31, 32, 33, 103, 124, 128, 251,
                  26, 27, 28,
                  # Конвейер (225) — сплошной: предметы должны ЛЕЖАТЬ на нём.
                  # Пока он был полуфизическим, предмет проваливался сквозь
                  # ленту и переставал находиться в тайле над ней — конвейер
                  # выглядел сломанным.
                  225,
                  # Батут (237) и блоровая дорожка (238) — сплошные по той же
                  # причине, что и конвейер: на них надо стоять, а не проваливаться.
                  237, 238}
# полуфизические блоки например мебель листва вода
SEMIPHYSBODY_TILES = {106, 120, 127, 126, 125, 121, 129, 131, 122, 104, 300, 140, 224, 226, 227,
                      228, 229, 230, 231, 232, 233, 234, 235, 236, 239}
# блоки которые должны стоять на блоке (есть 0 т.к. на воздух ставить нельзя)
# STANDING_TILES = {0, 101, 102, 103, 104, 110, 120, 121, 122, 123, 125, 126, 130, 129, 251}
STANDING_TILES = {0, 110, 120, 121, 122, 123, 125, 126, 130, 129, 131} | ON_EARTHEN_PLANTS
# Задние панельки
BACKTILES = {1003, }
# предметы которые нельзя физически поставить
ITEM_TILES = {None, 51, 52, 53, 55, 56, 58, 61, 62, 63, 64, 65, 66, 301, 351,
             401, 402, 403, 404, 405, 406, 408, 801, 81, 82, 86}

STONE_TILES = {3, 4, 5, 31, 32, 33, 21, 22, 23, 24, 25, 131}
WOOD_TILES = {12, 110, 11, 121, 122, 123, 124, 126, 127, 128, 129, 131, 251}

# блоки у которых есть прграммный класс
CLASS_TILE = {131, 129, 200, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223,
              300, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 238,
              # Шкаф — контейнер, а не мебель: структуры кладут в него находки
              126,
              # Отголосок — единственный НПС (units/Objects/TileClasses.py Echo)
              239}
# которые надо обновлять (213 провод не входит — у него нет своей логики)
CLASS_UPDATING_TILES = {131, 200, 210, 211, 212, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223,
                        224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 238}
# CLASS_UPDATING_TILES_IN_UI = {131}
# которые надо обновлять не зависимо от загрузки чанка те всегда
CLASS_ALLWAYS_UPDATING_TILES = {200, }
# блоки-узлы сети активации (участвуют в bfs_activate как проводники) —
# 211 таймер (авто-клокер), 212 нажимная плита (датчик игрока),
# 213 провод, 214 рычаг, 215 лампа, 219 прогрузчик чанка, 221 муз-блок,
# 222 приёмник, 223 передатчик рации. Вентили и задержка (216-218, 220)
# намеренно НЕ входят сюда — иначе чужой bfs_activate "затапливал" бы их
# напрямую, как ещё один провод; вместо этого они сами читают соседей и
# решают, включаться ли (см. LogicGate в units/Objects/TileClasses.py).
ACTIVATE_TILES = {200, 210, 9, 211, 212, 213, 214, 215, 219, 221, 222, 223, 226, 227,
                  228, 229, 230, 231, 233, 235}
# то же самое + вентили/задержка — только для того, чтобы они могли
# читать состояние соседей (включая друг друга), не участвуя в самом обходе
SIGNAL_TILES = ACTIVATE_TILES | {216, 217, 218, 220}

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
        81: 14, 82: 20, 86: 16, 405: 8, 406: 16}

# PICKAXE ===============================================================

iron_capability = {1, 2, 3, 4, 9, 11, 12, 21, 22, 23, 24, 25, 31, 32, 33, 101, 102, 103, 104, 105, 106, 110, 121, 122,
                   123, 124, 125, 126, 131,
                   127, 251,
                   128, 130, 300, 224, 225, 226, 227,
                   228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239,
                   26, 27, 28}
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
# Растительность по биомам (см. units/biomes.py biome_names для соответствия
# id -> название). Раньше был расклад только на 4 из 10 биомов (desert,
# winter, hell, None-фолбэк) — остальные 6 (savanna, tropical_woodland,
# seasonal_forest, rainforest, temperate_forest, temperate_rainforest,
# boreal_forest) молча получали дефолтный (None) набор растений и ничем не
# отличались друг от друга по флоре.
biomes_plants_chance = {
    None: {101: 0.1, 102: 0.2, 104: 1, 120: 0.05, 251: 0.005},
    0: {101: 0.1, 103: 0.2, 104: 0.2, None: 0.5},              # desert
    1: {104: 0.6, 101: 0.05, 102: 0.03, None: 0.32},           # savanna
    2: {101: 0.25, 102: 0.15, 104: 0.5, 251: 0.02, None: 0.08},  # tropical_woodland
    3: {101: 0.3, 102: 0.1, None: 0.5},                        # tundra
    4: {102: 0.3, 101: 0.15, 104: 0.4, None: 0.15},            # seasonal_forest
    5: {102: 0.35, 101: 0.25, 104: 0.3, 251: 0.03, None: 0.07},  # rainforest
    6: {102: 0.25, 101: 0.2, 104: 0.45, None: 0.1},            # temperate_forest
    7: {102: 0.3, 101: 0.2, 104: 0.4, 251: 0.02, None: 0.08},  # temperate_rainforest
    8: {102: 0.35, 104: 0.35, 101: 0.1, None: 0.2},            # boreal_forest
    9: {},                                                     # hell
}

def _covers_whole_tile(img):
    """Закрывает ли спрайт клетку целиком, без прозрачных пикселей.

    Нужно, чтобы не рисовать задние панельки под сплошным блоком: замер
    показал, что 100% отрисованных задних панелей были полностью скрыты
    передним тайлом — это 44% всех блитов кадра впустую.

    Проверяем пиксели, а не «список опасных id»: список пришлось бы угадывать
    и одна ошибка давала бы дырки в мире. Неизвестный случай считаем
    прозрачным — тогда оптимизация просто не срабатывает.
    """
    if img.get_width() < TILE_SIZE or img.get_height() < TILE_SIZE:
        return False
    if img.get_alpha() not in (None, 255):
        return False                     # полупрозрачный целиком
    try:
        colorkey = img.get_colorkey()
        if colorkey is not None:
            # Colorkey стоит почти на всех загруженных спрайтах по умолчанию
            # (см. load_img), но у камня и земли этого цвета в пикселях нет —
            # значит спрайт всё равно сплошной. Проверяем сами пиксели.
            rgb = pygame.surfarray.array3d(img)[:TILE_SIZE, :TILE_SIZE]
            key = colorkey[:3]
            if ((rgb[:, :, 0] == key[0]) & (rgb[:, :, 1] == key[1]) &
                    (rgb[:, :, 2] == key[2])).any():
                return False
        if img.get_flags() & pygame.SRCALPHA:
            alpha = pygame.surfarray.array_alpha(img)[:TILE_SIZE, :TILE_SIZE]
            if not bool((alpha == 255).all()):
                return False
    except Exception:
        return False                     # не смогли проверить — считаем прозрачным
    return True


def _all_frames_of(idx):
    """Все картинки, которыми тайл может нарисоваться.

    Одной tile_imgs[idx] недостаточно: у куста, конвейера, арбуза и прочих
    кадр берётся из tile_many_imgs по state_img, а у лавы и портала кадры
    подменяются анимацией. Если хоть один кадр прозрачный, тайл нельзя
    считать сплошным.
    """
    frames = []
    img = tile_imgs.get(idx)
    if img is not None:
        frames.append(img)
    frames += list(tile_many_imgs.get(idx, ()))
    if idx == 1:
        # Дёрн рисуется вариантами из ground_imgs (обычный/левый/правый/оба
        # края), и у краевых спрайтов прозрачность своя.
        for variants in ground_imgs.values():
            frames += list(variants)
    return frames


def tile_strip(tile_type, length):
    """Готовая полоса из length одинаковых тайлов.

    В сплошной породе строка экрана — это десятки одинаковых блитов подряд.
    Одна полоса вместо тридцати двух блитов даёт ровно те же пиксели (спрайт
    один и тот же), но в разы меньше вызовов. Полосы создаются по требованию
    и кэшируются: в мире реально встречается несколько типов породы, а не все
    шестьдесят.
    """
    key = (tile_type, length)
    strip = _tile_strips.get(key)
    if strip is None:
        img = tile_imgs[tile_type]
        strip = pygame.Surface((TILE_SIZE * length, TILE_SIZE)).convert()
        for k in range(length):
            strip.blit(img, (k * TILE_SIZE, 0))
        _tile_strips[key] = strip
    return strip


_tile_strips = {}
# Длины полос: степени двойки, чтобы кэш не разрастался, а любой пробег
# набирался жадно из нескольких полос.
STRIP_LENGTHS = (8, 4, 2)
STRIP_MAX = STRIP_LENGTHS[0]

# Тайлы, годные для склейки в полосу
# (заполняется ниже, когда известны все флаги)

# Тайлы, которым вообще есть что делать в свой такт: у остальных вызов
# update_tile был чистой потерей. Замер в глубоких пещерах: 1043 вызова за
# кадр, из которых осмысленных — единицы.
NEEDS_TICK = CLASS_UPDATING_TILES | PLANT_WITH_TIMER

# Тайлы, под которыми задняя панелька заведомо не видна.
# Тайлы со смещением спрайта (TILE_WITH_LOCAL_POS) исключены по определению:
# они рисуются сдвинутыми и клетку целиком не закрывают, каким бы плотным ни
# был сам спрайт.
OPAQUE_TILES = frozenset(
    idx for idx in tile_imgs
    if idx not in TILE_WITH_LOCAL_POS
    and all(not isinstance(f, list) and _covers_whole_tile(f) for f in _all_frames_of(idx))
)

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
                       402: "Сера",
                       403: "Хитин",
                       404: "Шкура",
                       405: "Сырое мясо",
                       406: "Жареное мясо",
                       408: "Космическая пыль",
                       211: "Таймер",
                       212: "Нажимная плита",
                       213: "Провод",
                       214: "Рычаг",
                       215: "Лампа",
                       216: "Вентиль НЕ",
                       217: "Вентиль И",
                       218: "Вентиль ИЛИ",
                       219: "Прогрузчик чанка",
                       220: "Задержка сигнала",
                       221: "Муз-блок",
                       222: "Приёмник",
                       223: "Передатчик",
                       300: "Плита с надписью",
                       140: "Лава",
                       224: "Воронка",
                       225: "Конвейер",
                       226: "Дропер",
                       227: "Лесоруб",
                       228: "Топливный двигатель",
                       229: "Креативный двигатель",
                       230: "Космический двигатель",
                       231: "Адский двигатель",
                       232: "Портал",
                       233: "Гнездо голема",
                       239: "Отголосок",
                       237: "Слизневый батут",
                       238: "Блоровая дорожка",
                       234: "Восходящий столб",
                       236: "Нисходящий столб",
                       26: "Астероидный камень",
                       27: "Пылевая жила",
                       28: "Звёздный кристалл",
                       235: "Пылеуловитель",
                       501: "Железный меч",
                       502: "Золотой меч",
                       503: "Ядовитый меч",
                       530: "Деревянная кирка",
                       531: "Железная кирка",
                       532: "Золотая кирка",
                       533: "Медная кирка",
                       581: "Шпатель",

                       610: "Призыатель босса слизней",
                       611: "Плот",
                       612: "Воздушная лодка",
                       613: "Шахтный ползун",
                       614: "Адская баржа",
                       615: "Пустотный скиф",

                       801: "Палка",
                       1003: "Панелька камня"
                       }
tile_words = get_translated_tiles(original_tile_words)

all_tiles = set(tile_words)

# Прочность блоков
TILES_SOLIDITY = {
    224: 55, 225: 45, 226: 55, 227: 60,
    228: 65, 229: 65, 230: 70, 231: 70,
    232: 85, 233: 80, 234: 50, 235: 60, 236: 50,
    237: 30, 238: 50, 239: 40,
    26: 55, 27: 65, 28: 70,
    140: 100,  # лава — как вода, руками не убрать
    300: 90,  # плита с надписью — крепче кирпича, но выкопать можно
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

DYNAMITE_NOT_BREAK = {5, 120, 200, 210, 140}  # гранит, вода, лава

# Урон при касании тайла. Раньше был зашит константой прямо в
# units/Objects/Entity.py (`if block[1] == 103: self.damage(1)`), из-за чего
# новый опасный блок было некуда добавить.
DAMAGE_TILES = {
    103: 1,    # кактус — царапина
    140: 8,    # лава — в ней не выжить без спешки
}

# Анимированные тайлы: {tile_id: {"frames": [...], "speed": кадров/с}}.
# Реестр общий для ванильных тайлов и модов: кадр подменяется прямо в
# tile_imgs по такту (см. units/mods.update_tile_animations), а ScreenMap
# читает tile_imgs заново каждый кадр и ничего не кэширует.
ANIMATED_TILES = {
    140: {"frames": lava_imgs, "speed": 3, "fps": FPS},
    232: {"frames": portal_imgs, "speed": 6, "fps": FPS},
}

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
    # Космос: пыль и рубины добываются руками — это стартовый запас, на
    # который игрок и собирает пылеуловитель.
    26: [(26, 1, 1), (408, 1, 0.04)],
    27: [(26, 1, 0.6), (408, (1, 2), 1)],
    28: [(26, 1, 0.6), (66, (1, 2), 1)],
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



# MODS ==================================================================
# Регистрация контента модов в те же структуры, что и у ванильных блоков:
# так мод получает копание, крафт, выпадение предметов и отрисовку без
# единой правки в игровом цикле. Делается в конце файла — к этому моменту
# все словари/множества выше уже собраны, а модули, которые импортируют
# units.Tiles (инвентарь, ScreenMap), увидят уже полный набор блоков.
from units import mods as _mods  # noqa: E402 — нужен собранный tile_imgs выше

_mods.load_mods()

for _spec in _mods.mod_blocks():
    _idx, _frames = _spec["id"], _spec["frames"]
    tile_imgs[_idx] = _frames[0]
    original_tile_words[_idx] = _spec["name"]
    # ScreenMap индексирует TILES_SOLIDITY[tile_type] напрямую при отрисовке
    # трещин — без записи здесь мод-блок ронял бы отрисовку KeyError.
    TILES_SOLIDITY[_idx] = _spec["solidity"]

    if _spec["is_item"]:
        ITEM_TILES.add(_idx)
    elif _spec["physical"]:
        PHYSBODY_TILES.add(_idx)
    # без этого мод-блок нельзя выкопать ни рукой, ни киркой:
    # Pickaxes_capability ссылается на этот же объект-множество
    iron_capability.add(_idx)

    if _spec["eat"] is not None:
        Eats[_idx] = _spec["eat"]
    if _spec["drops"]:
        tile_drops[_idx] = tuple(_spec["drops"])
    if len(_frames) > 1:
        ANIMATED_TILES[_idx] = {"frames": _frames, "speed": _spec["speed"], "fps": FPS}

if _mods.MODS:
    # пересобрать производные структуры с учётом мод-блоков
    tile_words = get_translated_tiles(original_tile_words)
    all_tiles = set(tile_words)
    tile_hand_imgs.update({_spec["id"]: (tile_imgs[_spec["id"]] if _spec["is_item"]
                                         else transform_hand(tile_imgs[_spec["id"]]))
                           for _spec in _mods.mod_blocks()})


# Тайлы, которые можно склеивать в полосу: один и тот же спрайт РОВНО в
# клетку, без своей логики, без смещения, без вариантов кадра и без биомных
# вариантов (дёрн 1 и шкаф 126 рисуются особым образом).
#
# Два условия, найденные сравнением кадров по пикселям:
# * ровно TILE_SIZE: спрайт крупнее клетки при отдельной отрисовке заходил на
#   соседей, а внутри полосы обрезался — картинка расходилась;
# * не анимированный: полоса кэшируется, а у лавы кадр подменяется в
#   tile_imgs каждый такт, и в полосе он застыл бы навсегда.
STRIP_TILES = frozenset(
    idx for idx in OPAQUE_TILES
    if idx not in tile_many_imgs and idx not in NEEDS_TICK
    and idx not in TILE_WITH_LOCAL_POS and idx not in (1, 126)
    and idx not in ANIMATED_TILES
    and idx in TILES_SOLIDITY
    and tile_imgs[idx].get_size() == (TILE_SIZE, TILE_SIZE)
)
