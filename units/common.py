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
last_versions = ["0.9.1", "0.1.3-alpha", "0.1.5-alpha", "0.1.6-alpha", "0.1.7-alpha",
                 "0.2.16-alpha", "0.2.17-alpha", "0.2.18-alpha", "0.2.19-alpha", "0.2.20-alpha"]
# Версия игры. Отставала от тегов релизов (0.1.7 против v0.2.x) — из-за
# этого проверка обновлений (units/Updater.py) считала бы новым любой
# опубликованный релиз. Держим синхронной с тегом.
GAME_VERSION = "0.2.21-alpha"

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


# Номер «поколения экрана»: растёт при каждом ресайзе/переключении режима.
# Список, а не int, по той же причине, что и SCREEN_SIZE: модули делают
# "from units.common import *", и переприсваивание они бы не увидели.
#
# Нужен для ЛЕНИВОГО пересчёта раскладки. Пересчитывать только активный UI
# недостаточно: сцена держит несколько экранов (титул, настройки, звук), и
# растянув окно на титуле, игрок получал корректный титул и разъехавшиеся
# настройки. А события ресайза приходят вообще только в активную сцену.
SCREEN_GENERATION = [0]


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
    SCREEN_GENERATION[0] += 1
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

# Множитель размера ячеек инвентаря/хотбара от настройки "Размер меню".
# Отличается от UI_SCALE тем, что "авто" здесь ровно 1.0, а не эвристика от
# ширины экрана: ячейка привязана к ЭКРАННОМУ размеру блока (см.
# screen_tile_size) и подстраивается под разрешение сама. Домножать её ещё и
# на ширину экрана значило бы учесть разрешение дважды — на 1366 ячейка
# выходила бы заметно мельче блока, хотя должна быть с ним вровень.
UI_CELL_SCALE = _MENU_SIZE_SCALE.get(config.Window.menu_size, 1.0)


def screen_tile_size():
    """Размер блока в ЭКРАННЫХ пикселях.

    Мир рисуется в WSIZE и растягивается до SCREEN_SIZE, поэтому мировой
    TSIZE — это НЕ то, что видит игрок: на 2560x1440 при 50 блоках в ширину
    блок занимает 51 px, а TSIZE так и остаётся 32. Любой элемент интерфейса,
    который должен совпадать с блоками по размеру (ячейка инвентаря, хотбар),
    обязан считать отсюда, иначе на узком экране он крупнее блока, а на
    широком — мельче.
    """
    return TSIZE * SCREEN_SIZE[0] / WSIZE[0]

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
# Транспортное средство (units/Objects/Vehicles.py) — ездит и возит игрока
OBJ_VEHICLE = 64

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

# Астероиды в космосе. До этого выше START_ATMO_Y мир был абсолютно пуст:
# встать не на что, копать нечего, существам негде спавниться — космос
# существовал только как координата. Отступ от границы космоса нужен,
# чтобы астероиды не начинались вплотную к атмосфере.
ASTEROID_MARGIN = 60
ASTEROID_THRESHOLD = -0.42
# Доля жил внутри астероида (шум отдельным сидом, поэтому жилы связные).
# Пороги подобраны по КВАНТИЛЯМ реального шума (пакет noise, на нём собираются
# релизы), а не на глаз: с прежними значениями жила приходилась на 0.26%
# астероида — чтобы добыть первую пыль, пришлось бы срыть весь астероид.
# Сейчас примерно 12% жил и 3% кристаллов от объёма породы.
ASTEROID_DUST_THRESHOLD = -0.42
ASTEROID_CRYSTAL_THRESHOLD = -0.57

# Озёра. Вода (120) в игре была, но ставилась как «растение» с шансом 0.05 —
# то есть одиночными тайлами на склонах, а не водоёмами.
#
# Сначала пробовал ИСКАТЬ котловину (дно снизу, берега с двух сторон, небо
# сверху). Замер показал, почему это не работает: в этом рельефе на 800
# колонок нашлось 8 подходящих тайлов — широких естественных впадин здесь
# почти не бывает, отсев съедала проверка берегов. Поэтому котловину не ищем,
# а ВЫРЕЗАЕМ: озеро — это чаша заданного размера в решётке возможных мест.
# Так есть контроль над размером и гарантия, что вода стоит ровным зеркалом,
# а не мажется по склону.
LAKE_CELL = 150            # шаг решётки мест под озёра (тайлов по горизонтали)
LAKE_CHANCE = 0.5          # доля клеток, где озеро действительно есть
LAKE_MIN_R, LAKE_MAX_R = 7, 22   # полуширина чаши
LAKE_DEPTH_FACTOR = 0.3    # глубина чаши = полуширина * этот коэффициент
LAKE_MAX_DEPTH = 7         # глубже озеро не роем: это водоём, а не колодец
# Берег тоже вырезается. Без этого озеро на склоне превращалось в узкую
# шахту: вода оставалась лишь в тех колонках, где рельеф сам оказался на
# уровне зеркала, — замер давал полосу в 5 тайлов при радиусе 20.
LAKE_RIM_CLEAR = 5         # сколько тайлов породы снять над зеркалом

CNT_BUILDS_OF_STRUCTURE_BLOCK = 400

START_SPACE_Y = -1000
START_ATMO_Y = START_SPACE_Y + 200
TOP_MIDDLE_WORLD = START_ATMO_Y + 150
BOTTOM_MIDDLE_WORLD = 1000
START_HELL_Y = BOTTOM_MIDDLE_WORLD + 350

# Кривая сложности =========================================================
# Раньше сила существ была одинаковой везде: у спавна на первой минуте мог
# появиться слайм-босс (250 HP, 35 урона), а в аду бегали те же волки, что и
# на лугу. Ни начала, ни развития — просто ровная линия. Теперь сила зависит
# от того, куда игрок забрался: горизонтально от спавна, вниз к аду и вверх
# к космосу. Множитель применяется к HP и урону при спавне
# (см. GameMap.spawn_creature).
DIFFICULTY_SAFE_RADIUS = 300     # тайлов от спавна: тут заведомо легче
DIFFICULTY_FULL_RADIUS = 5000    # где горизонтальная надбавка выходит в максимум
DIFFICULTY_MIN = 0.7
DIFFICULTY_MAX = 2.0


def _clamp01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def difficulty_scale(tile_x, tile_y):
    """Во сколько раз существо в этой точке сильнее базового.

    Берём МАКСИМУМ из трёх составляющих, а не сумму: спуск в ад не должен
    складываться с уходом на восток — иначе край карты давал бы неберущихся
    мобов просто за счёт координаты.
    """
    if tile_x is None or tile_y is None:
        return 1.0
    start_x = config.GameSettings.start_pos[0] // 32
    horizontal = _clamp01((abs(tile_x - start_x) - DIFFICULTY_SAFE_RADIUS) /
                          max(1, DIFFICULTY_FULL_RADIUS - DIFFICULTY_SAFE_RADIUS))
    # Глубина считается от уровня поверхности (y ≈ 0), а не от верхней
    # границы среднего мира: иначе точка спавна сама по себе оказывалась бы
    # на трети шкалы, и «легко» не было бы нигде.
    depth = _clamp01(tile_y / max(1, START_HELL_Y))
    height = _clamp01((TOP_MIDDLE_WORLD - tile_y) /
                      max(1, TOP_MIDDLE_WORLD - (START_SPACE_Y - 500)))
    part = max(horizontal, depth, height)
    return DIFFICULTY_MIN + (DIFFICULTY_MAX - DIFFICULTY_MIN) * part


# Пороги шума для руд: базовый (у поверхности) и прибавка на полной глубине.
# Чем выше порог, тем руда чаще. Числа подобраны замером по 15 000 тайлов
# породы, см. docs/BALANCE_SCHEME.md — там же, почему лестница именно такая.
# Железо — рабочая лошадка, оно и так везде, поэтому прибавка у него самая
# скромная. Золото и серебро до этого не встречались практически НИКОГДА
# (0 находок на 15 000 тайлов), из-за чего 7 рецептов на золоте были
# недостижимы иначе как с босса.
ORE_IRON_T, ORE_IRON_DEEP = -0.84, 0.03
ORE_COPPER_T, ORE_COPPER_DEEP = -0.90, 0.02
ORE_BLORE_T, ORE_BLORE_DEEP = -0.925, 0.055
ORE_SILVER_T, ORE_SILVER_DEEP = -0.94, 0.06
ORE_GOLD_T, ORE_GOLD_DEEP = -0.965, 0.067


# СУТКИ ============================================================
#
# До этого мир был неподвижен во времени: ни ночи, ни ритма, ни причины
# строить убежище и вешать лампы. Свет в игре был чисто декоративным.
#
# Полный цикл — 8 минут реального времени. Короче, чем «реалистично», и это
# осознанно: игра про исследование, а ждать рассвет пять минут в яме скучнее,
# чем выйти в него.
DAY_LENGTH = FPS * 60 * 8
# Доля суток, которую занимает ночь. Меньше половины: ночь — событие, а не
# состояние по умолчанию.
NIGHT_PART = 0.35
# Доля суток на рассвет и на закат по отдельности. Нужны, чтобы темнота
# наступала заметно, но не мгновенно — мгновенная выглядит как баг.
TWILIGHT_PART = 0.07
# Насколько темно в самую глубокую ночь: 0 — чернота, в которой ничего не
# видно и играть нельзя. 0.28 оставляет силуэты.
NIGHT_LIGHT = 0.28
# Во сколько раз гуще населяется мир ночью. Не «вдвое страшнее», а «вдвое
# больше поводов не выходить»: сила существ по-прежнему от МЕСТА
# (difficulty_scale), ночь добавляет количество, а не ломает кривую.
NIGHT_SPAWN_MULT = 2.2


def day_phase(world_time):
    """Фаза суток: 0 — рассвет, растёт до 1 и снова к рассвету."""
    return (world_time % DAY_LENGTH) / DAY_LENGTH


def daylight(world_time):
    """Освещённость неба: 1 — день, NIGHT_LIGHT — глубокая ночь.

    Сутки начинаются ДНЁМ, а не рассветом: world_time == 0 у каждого нового
    мира, и при порядке «сначала рассвет» игрок появлялся бы в темноте на
    первой же секунде — первое, что он видел бы, это ночь.
    """
    phase = day_phase(world_time)
    day_part = 1.0 - NIGHT_PART
    if phase < day_part - TWILIGHT_PART:           # день
        k = 1.0
    elif phase < day_part:                         # закат
        k = (day_part - phase) / TWILIGHT_PART
    elif phase < 1.0 - TWILIGHT_PART:              # ночь
        k = 0.0
    else:                                          # рассвет
        k = (phase - (1.0 - TWILIGHT_PART)) / TWILIGHT_PART
    return NIGHT_LIGHT + (1.0 - NIGHT_LIGHT) * k


def is_night(world_time):
    """Ночь ли сейчас — по этому решают спавн и события.

    Считаем по СВЕТУ, а не по фазе суток: рассвет ещё тёмный, и твари,
    исчезающие ровно тогда, когда небо всё ещё чёрное, читались бы как
    выключенные по таймеру, а не как разбежавшиеся от солнца.
    """
    return daylight(world_time) < 0.5


def surface_daylight(world_time, tile_y):
    """Освещённость с поправкой на глубину.

    Под землёй и в аду смена суток ничего не значит — там и так свой свет,
    а мигающая с ночью пещера читалась бы как баг. Поэтому эффект гаснет по
    мере ухода вниз и полностью исчезает к нижней границе среднего мира.
    """
    if tile_y is None or tile_y > BOTTOM_MIDDLE_WORLD:
        return 1.0
    light = daylight(world_time)
    if tile_y <= 0:
        return light
    fade = _clamp01(tile_y / max(1, BOTTOM_MIDDLE_WORLD))
    return light + (1.0 - light) * fade


def depth_reward(tile_y):
    """Насколько «глубоко» этот тайл — 0 у поверхности, 1 у ада.

    Та же величина, из которой difficulty_scale берёт составляющую глубины,
    вынесенная отдельно НАМЕРЕННО: риск и награда обязаны идти по одной
    кривой. До этого руды раздавались порогами шума без всякой связи с
    глубиной — замер по 15 000 тайлов породы давал железо 1 на 98 у
    поверхности и 1 на 60 на глубине 1000, то есть спуск не окупался ничем,
    хотя мобы там уже были вдвое сильнее.
    """
    if tile_y is None:
        return 0.0
    return _clamp01(tile_y / max(1, START_HELL_Y))
# Player ===========================================================

NUM_KEYS = [pg.K_1, pg.K_2, pg.K_3, pg.K_4, pg.K_5, pg.K_6, pg.K_7, pg.K_8, pg.K_9, pg.K_0]

HAND_SIZE = int(TILE_SIZE // 2)
HAND_RECT = (HAND_SIZE, HAND_SIZE)

FALL_SPEED = 0.021
FALL_SPEED = 0.017
MAX_FALL_SPEED = 50
# Блоровые столбы: 234 — вверх, 236 — вниз. Спуск медленнее подъёма и
# держится ниже порога урона от падения (0.75, см. Player.moving), чтобы
# приезд на дно шахты не бил игрока.
# Транспорт (см. docs/TRANSPORT.md). Одна идея: блок, который несёт того, кто
# в нём стоит, — так же, как блоровые столбы.
# Батут: примерно вдвое выше обычного прыжка (jump_speed 0.275) — этого хватает
# на уступ в 4-5 блоков, то есть на подъём, который иначе стоил бы лестницы.
TRAMPOLINE_SPEED = 0.55
# Дорожка: заметно быстрее бега (max_speed 0.33), но не мгновенно — иначе
# пропадает смысл в поздних порталах.
BLORE_TRACK_SPEED = 0.5
ELEVATOR_UP_SPEED = 0.9
ELEVATOR_DOWN_SPEED = 0.7
# Запас (в тайлах) вокруг экрана, внутри которого считаются коллизии и
# обновляются существа/предметы. Раньше и то и другое делалось для всех
# загруженных чанков — это ~12000 тайлов за кадр при 960 на экране.
COLLIDE_MARGIN = 10

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
