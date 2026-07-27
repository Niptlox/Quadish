import os

# units.config при импорте выставляет рабочую директорию в корень проекта
from units.UI.Translate import get_translated_text

import math
import sys
from logging import warning

import pygame
import pygame as pg

# используется в других модулях
import units.config as config

# DEBUG ====================================================

CHUNK_BD_COLOR = (230, 20, 20)

#  current working directory.

CWDIR = os.getcwd() + "/"
print(CWDIR)

# INIT GAME ==============================================
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()  # initiate pygame

# Аудиоустройства может не быть (WSL, сервер, headless) — тогда игра
# работает без звука вместо падения на pygame.mixer.Sound(...).
try:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()
    AUDIO_ENABLED = pygame.mixer.get_init() is not None
except pygame.error:
    AUDIO_ENABLED = False
if not AUDIO_ENABLED:
    print("Аудиоустройство недоступно — звук отключён")

# Лимит кадров: настраивается в settings.ini ([game] max_fps) и в меню настроек.
# 60 по умолчанию — вдвое меньше работы на слабом железе, чем прежние 120.
FPS = config.GameSettings.max_fps
print("INIT GAME VARS")
last_versions = ["0.9.1", "0.1.3-alpha", "0.1.5-alpha", "0.1.6-alpha"]
GAME_VERSION = "0.1.7-alpha"

FULLSCREEN = config.Window.fullscreen

# Мониторы (для нескольких экранов): выбираем нужный по индексу, но помним
# про все — если выбранного нет, берём первый.
MONITORS = pygame.display.get_desktop_sizes()
MONITOR_INDEX = config.Window.monitor if 0 <= config.Window.monitor < len(MONITORS) else 0
desktop_size = MONITORS[MONITOR_INDEX]

# ==========================================================================
# Два независимых размера — в этом весь фикс размытого текста после ресайза:
#
# SCREEN_SIZE — реальное окно/экран в физических пикселях. Здесь рисуется
#   ВЕСЬ текст и UI (меню, HUD, инвентарь) — напрямую, без масштабирования,
#   поэтому шрифт всегда чёткий, независимо от размера окна.
# WSIZE       — логическое разрешение МИРА (тайлы/небо/игрок). Может быть
#   меньше SCREEN_SIZE — тогда игра считает меньше видимых тайлов (дешевле
#   рендерить) и подросток-кадр растягивается на весь экран (transform.scale,
#   блочно, без блюра — это просто тайлы с плоской заливкой, не текст).
#
# Раньше был один общий "логический" размер, который SDL (флаг SCALED)
# тянул на весь монитор одним махом — из-за этого замыливался и текст, и
# мир. Теперь ресайзится (масштабируется) только мир, а меню — никогда.
# ==========================================================================
# SCREEN_SIZE — список (не кортеж!) намеренно: apply_resize() ниже мутирует
# его ПО МЕСТУ (SCREEN_SIZE[:] = ...), а не переприсваивает — это даёт
# всем модулям, сделавшим "from units.common import *", видеть текущий
# размер без необходимости что-либо у себя менять (общая ссылка на один
# и тот же список).
if FULLSCREEN:
    SCREEN_SIZE = list(desktop_size)
else:
    SCREEN_SIZE = list(map(int, config.Window.size.split(",")))

# Размер тайла в мировых пикселях — вынесен сюда (а не в раздел TILE ниже),
# т.к. нужен уже для расчёта WSIZE.
_WORLD_TILE_SIZE = 32


def _compute_wsize(screen_size):
    """WSIZE подбирается так, чтобы по ширине экрана было видно ровно
    view_tiles_width тайлов ("50 блоков в ширину" и т.п.) — одинаковый
    "зум" мира на любом разрешении/мониторе. Не больше screen_size (иначе
    был бы апскейл вместо честного даунскейла — блюр вместо экономии
    рендера)."""
    view_w = max(10, config.Window.view_tiles_width) * _WORLD_TILE_SIZE
    view_w = min(view_w, screen_size[0])
    view_h = round(view_w * screen_size[1] / screen_size[0])
    return [view_w, view_h]


WSIZE = _compute_wsize(SCREEN_SIZE)
print("SCREEN_SIZE (экран/UI)", SCREEN_SIZE, "WSIZE (мир)", WSIZE,
     "monitor", MONITOR_INDEX, "of", MONITORS)

# Коэффициент для перевода координат мыши из экранных (SCREEN_SIZE) в мировые
# (WSIZE) — нужен только там, где мышь целится по тайлам (копка/постройка);
# все UI-клики остаются в экранных координатах без пересчёта.
WORLD_SCALE = (WSIZE[0] / SCREEN_SIZE[0], WSIZE[1] / SCREEN_SIZE[1])


def screen_to_world_pos(pos):
    return pos[0] * WORLD_SCALE[0], pos[1] * WORLD_SCALE[1]


# Оконный режим теперь растягивается мышью (RESIZABLE) — раньше окно
# намеренно создавалось без этого флага, т.к. свободное перетаскивание
# рамки не пересчитывало раскладку меню (кэшировалась при запуске).
# apply_resize() ниже это чинит: пересчитывает раскладку активного UI и
# держит SCREEN_SIZE/WORLD_SCALE в актуальном состоянии.
flags = pygame.FULLSCREEN if FULLSCREEN else pygame.RESIZABLE

pygame.display.set_caption('Quadish')
Icon = pg.image.load("data/sprites/Icon.png")
pygame.display.set_icon(Icon)

# vsync можно отключить: при включённом vsync слабое железо в фуллскрине
# нередко «залипает» на половине развёртки (60→30 FPS).
try:
    screen_ = pygame.display.set_mode(SCREEN_SIZE, flags=flags, display=MONITOR_INDEX,
                                      vsync=1 if config.GameSettings.vsync else 0)
except pygame.error:
    # display= может не поддерживаться — откат на монитор по умолчанию
    screen_ = pygame.display.set_mode(SCREEN_SIZE, flags=flags,
                                      vsync=1 if config.GameSettings.vsync else 0)
# Мир рендерится в собственную (возможно, уменьшенную) поверхность и
# растягивается на экран только этим слоем — см. GameUI.blit_world().
# Этот Surface НЕ пересоздаётся при ресайзе окна (см. apply_resize) —
# blit_world() масштабирует его под текущий self.screen.get_size() каждый
# кадр в любом случае, так что несовпадение размеров не баг, а норма.
display_ = pygame.Surface(WSIZE).convert()

print(pg.display.get_allow_screensaver())


def apply_resize(size=None, fullscreen=None):
    """Применить новый размер окна и/или режим экрана. Единая точка входа
    и для живого перетаскивания рамки (VIDEORESIZE), и для F11/переключателя
    "Режим экрана" в настройках — раньше оба применялись только через
    перезапуск игры.

    Пересоздаёт screen_ (реальный display Surface) и обновляет SCREEN_SIZE/
    WORLD_SCALE по месту, чтобы уже импортированные (from units.common import *)
    ссылки увидели новые значения без правок на своей стороне. WSIZE/display_
    (мировой рендер) намеренно не трогает — см. комментарий у display_ выше."""
    global FULLSCREEN, flags, screen_, WORLD_SCALE
    if fullscreen is not None:
        FULLSCREEN = bool(fullscreen)
        config.Window.set_fullscreen(FULLSCREEN)
    if FULLSCREEN:
        new_size = tuple(desktop_size)
        new_flags = pygame.FULLSCREEN
    else:
        new_size = tuple(size) if size else tuple(SCREEN_SIZE)
        new_flags = pygame.RESIZABLE
    try:
        new_screen = pygame.display.set_mode(new_size, flags=new_flags, display=MONITOR_INDEX,
                                             vsync=1 if config.GameSettings.vsync else 0)
    except pygame.error:
        new_screen = pygame.display.set_mode(new_size, flags=new_flags,
                                             vsync=1 if config.GameSettings.vsync else 0)
    screen_ = new_screen
    flags = new_flags
    SCREEN_SIZE[:] = new_screen.get_size()
    WORLD_SCALE = (WSIZE[0] / SCREEN_SIZE[0], WSIZE[1] / SCREEN_SIZE[1])
    if not FULLSCREEN:
        config.Window.set_size(f"{SCREEN_SIZE[0]},{SCREEN_SIZE[1]}")
    return new_screen


# "Размер меню" (Minecraft-style GUI Scale): множитель нативного размера
# шрифтов/кнопок меню — НЕ postfactum-растяжение картинки (как WSIZE->
# SCREEN_SIZE у мира), иначе текст меню размывался бы ровно так же, как до
# фикса SCREEN_SIZE/WSIZE. "Авто" — эвристика от ширины экрана.
_MENU_SIZE_SCALE = {"tiny": 0.8, "small": 0.9, "medium": 1.0, "large": 1.15, "huge": 1.3}
MENU_SIZES = ["auto", "tiny", "small", "medium", "large", "huge"]


def _compute_ui_scale():
    menu_size = config.Window.menu_size
    if menu_size in _MENU_SIZE_SCALE:
        return _MENU_SIZE_SCALE[menu_size]
    return max(0.8, min(1.3, SCREEN_SIZE[0] / 1600))


UI_SCALE = _compute_ui_scale()

# TILE ==================================================

TILE_SIZE = _WORLD_TILE_SIZE
TSIZE = TILE_SIZE

# TILE_SIZE = 16
TILE_RECT = (TILE_SIZE, TILE_SIZE)
TRECT = TILE_RECT

CHUNK_SIZE = 32
CSIZE = CHUNK_SIZE

STRUCTURE_CHUNKS_SIZE = 100  # чанков

SCSIZE = STRUCTURE_CHUNKS_SIZE

CHUNK_SIZE_PX = CHUNK_SIZE * TILE_SIZE
CSIZEPX = CHUNK_SIZE_PX
# колво чанков отрисовываемых на экране — считается от WSIZE (мировой,
# возможно уменьшенный размер), а не от SCREEN_SIZE
WINDOW_CHUNK_SIZE = math.ceil(WSIZE[0] / (TILE_SIZE * CHUNK_SIZE)) + 2, \
                    math.ceil(WSIZE[1] / (TILE_SIZE * CHUNK_SIZE)) + 2
print("WINDOW_CHUNK_SIZE", WINDOW_CHUNK_SIZE, WSIZE[0] / (TILE_SIZE * CHUNK_SIZE))
WCSIZE = WINDOW_CHUNK_SIZE

# DEBUG ====================================================
# DEBUG = True
DEBUG = False
show_chunk_grid = False
show_entity_border = False
show_group_obj = True
show_info_menu = True

CHUNK_BD_COLOR = (230, 20, 20)

# PhiscalObject ==================================================

OBJ_NONE = 0
OBJ_CREATURE = 2
OBJ_ITEM = 4
OBJ_TILE = 8
OBJ_PLAYER = 16
OBJ_PARTICLE = 32

# ITEMS ==========================================================

CLS_NONE = 0
CLS_TILE = 2
CLS_TOOL = 4
CLS_WEAPON = 8
CLS_SWORD = 16
CLS_PICKAXE = 32
CLS_EAT = 64
CLS_COMMON = 128
CLS_SPATULA = 256

# STATES OF TILE ================================================

TILE_TIMER = "t"
TILE_LOCAL_POS = "p"

# GENERATING MAP OR CHANK ========================================

TGENERATE_LOAD = 0
TGENERATE_INFINITE = 1
TGENERATE_INFINITE_LANDS = 2
Generate_type = 2  # 0:load Map,1: autogenerate

cof = 4.5
freq_x = 49 * cof
freq_y = 14 * cof

CHUNK_CREATURE_LIMIT = 4
CHUNK_CREATURE_CHANCE = 0.2

# Дальность дистанционного передатчика (в тайлах) — рация должна работать
# в пределах обжитой базы, а не телепортировать сигнал в любую точку
# загруженного мира (см. docs/SIGNAL_NETWORK_CONCEPT.md).
TRANSMITTER_RANGE = CHUNK_SIZE * 4

# Лава в аду: не сразу от границы ада, чтобы вход в него не был мгновенной
# смертью, и порогом шума — лужи выходят связными, а не рассыпанными.
LAVA_DEPTH_MARGIN = 40
LAVA_THRESHOLD = -0.35

CNT_BUILDS_OF_STRUCTURE_BLOCK = 400

START_SPACE_Y = -1000
START_ATMO_Y = START_SPACE_Y + 200
TOP_MIDDLE_WORLD = START_ATMO_Y + 150
BOTTOM_MIDDLE_WORLD = 1000
START_HELL_Y = BOTTOM_MIDDLE_WORLD + 350
# Player ===========================================================

NUM_KEYS = [pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5, pg.K_6, pg.K_7, pg.K_8, pg.K_9, pg.K_0]

HAND_SIZE = int(TILE_SIZE // 2)
HAND_RECT = (HAND_SIZE, HAND_SIZE)

FALL_SPEED = 0.021
FALL_SPEED = 0.017
MAX_FALL_SPEED = 50
# Лифт (тайл 234). Спуск медленнее подъёма и держится ниже порога урона от
# падения (0.75, см. Player.moving), чтобы приезд на дно шахты не бил.
ELEVATOR_UP_SPEED = 0.9
ELEVATOR_DOWN_SPEED = 0.7
AUTO_BUILD = True  # копать ближайший если мышка далеко

CREATIVE_MODE = False
# INIT TIME ================================================================

EVENT_100_MSEC = pg.USEREVENT + 1
pygame.time.set_timer(EVENT_100_MSEC, 100, False)

EVENT_END_OF_STEP_SOUND = pg.USEREVENT + 10

# CREATURES ===============================================================

KINGDOM_CREATURAE = "Creaturae"
KINGDOM_ANIMALIA = "Animalia"
KINGDOM_PLANTAE = "Plantae"
KINGDOMS = (KINGDOM_CREATURAE, KINGDOM_ANIMALIA, KINGDOM_PLANTAE)

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


# DEFS ======================================================================

def pygame_mainloop(f_iter_loop, f_pgevent=None, rect=WSIZE, fps=FPS):
    # screen = pygame.display.set_mode((rect[0], rect[1]), 0, 32)
    clock = pg.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pg.QUIT:
                pygame.quit()
                sys.exit()
            if f_pgevent:
                f_pgevent(event)
        clock.tick(fps)
        f_iter_loop(screen_)
        pygame.display.flip()


# CLASSES ===================================================================

class SavedObject:
    not_save_vars = {"", }
    is_not_saving = False

    def get_vars(self):
        # print(self.not_save_vars)
        d = self.__dict__.copy()
        d["__class__"] = self.__class__
        for key, value in list(d.items()):
            if key in self.not_save_vars:
                d.pop(key)
            elif isinstance(value, SavedObject):
                if not value.is_not_saving:
                    d[key] = value.get_vars()
                else:
                    d.pop(key)
            elif isinstance(value, pg.Surface) or (
                    isinstance(value, (list, tuple)) and value and isinstance(value[0], pg.Surface)):
                warning(f"Не контроллируемый {key}: {value}, удален из сохранения!")
                d.pop(key)
            elif isinstance(value, (list, tuple)) and value and isinstance(value[0], SavedObject):
                warning(f"В {self}. Не контроллируемый списочный SavedObject {key}: {value}, удален из сохранения!")
                d.pop(key)
        # print(self.__class__, d)
        # pickle.dumps(d)
        return d

    def set_vars(self, vrs):
        if "__class__" in vrs:
            vrs.pop("__class__")
        for var_name, var_value in vrs.items():
            if var_name in self.not_save_vars:
                continue
            if isinstance(var_value, dict) and var_value.get("__class__"):
                self.__dict__[var_name].set_vars(var_value)
            else:
                self.__dict__[var_name] = var_value


#  =============================== GameMap ===============================

GAMEMAPS_PATH = CWDIR + "data/maps/"

if not os.path.exists(GAMEMAPS_PATH):
    os.mkdir(GAMEMAPS_PATH)

# Loadings screen ==================================================================
text = get_translated_text("Загрузка...")
screen_.blit(pygame.font.SysFont("", 40).render(text, True, "white"), (35, SCREEN_SIZE[1] - 50))
pygame.display.flip()
