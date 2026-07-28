"""Единый реестр битовых флагов тайлов.

units/Tiles.py копит свойства тайла (физическое тело, класс-объект,
активируемость, еда, случайный спрайт и т.д.) в полутора десятках
самостоятельных set()/dict() — PHYSBODY_TILES, SEMIPHYSBODY_TILES,
CLASS_TILE, ACTIVATE_TILES, Eats и т.д. Каждое место в коде, которому
нужно узнать сразу несколько свойств одного тайла (типичный пример —
проверка коллизий: "это физическое тело ИЛИ полу-физическое тело?"),
делает по одному отдельному set-lookup на каждое свойство.

TILE_FLAGS сводит все эти множества в один dict {tile_id: TileFlag},
посчитанный один раз при импорте из уже существующих списков в
Tiles.py (они остаются единственным источником истины — ничего в
остальном коде ломать не нужно). Дальше вместо N обращений к N
разным set() достаточно одного обращения к TILE_FLAGS и битовой
маски: has_flag(ttile, TileFlag.PHYSBODY | TileFlag.SEMIPHYSBODY).
"""
from enum import IntFlag, auto

from units.Tiles import (
    PHYSBODY_TILES, SEMIPHYSBODY_TILES, STANDING_TILES, BACKTILES, ITEM_TILES,
    STONE_TILES, WOOD_TILES, CLASS_TILE, CLASS_UPDATING_TILES, CLASS_ALLWAYS_UPDATING_TILES,
    ACTIVATE_TILES, ITEM_WITH_STATE_IS_LIST, PLANT_WITH_TIMER, PLANT_STAND_ON_DIRT,
    PLANT_STAND_ON_PLANT, MULTI_BLOCK_PLANTS, ON_EARTHEN_PLANTS, PLANT_WITH_RANDOM_SPRITE,
    PLANT_WITH_RANDOM_LOCAL_POS, DYNAMITE_NOT_BREAK, Eats, all_tiles,
)


class TileFlag(IntFlag):
    NONE = 0
    PHYSBODY = auto()          # физическое тело (нельзя пройти)
    SEMIPHYSBODY = auto()      # полу-физическое тело (мебель, вода, листва)
    STANDING = auto()          # можно ставить растение сверху
    BACKTILE = auto()          # задняя панелька
    ITEM = auto()              # предмет, не ставится физически
    STONE = auto()
    WOOD = auto()
    CLASS_TILE = auto()        # есть программный класс-объект (Chest, Furnace, ...)
    CLASS_UPDATING = auto()    # класс-объект надо обновлять
    CLASS_ALWAYS_UPDATING = auto()
    ACTIVATABLE = auto()       # реагирует на активацию (командный/активационный блок)
    STATE_IS_LIST = auto()     # tile[3] - список (не id объекта/таймер)
    PLANT_TIMER = auto()       # tile[3] - таймер роста
    STAND_ON_DIRT = auto()     # растёт только на земле
    STAND_ON_PLANT = auto()    # растёт друг на друге (кактус)
    MULTI_BLOCK = auto()
    ON_EARTHEN = auto()
    RANDOM_SPRITE = auto()     # случайная картинка при генерации
    RANDOM_LOCAL_POS = auto()  # случайное локальное смещение спрайта в клетке
    DYNAMITE_IMMUNE = auto()   # не разрушается динамитом
    FOOD = auto()              # съедобно (см. Eats для количества хилла)


# (флаг, множество/словарь id тайлов с этим свойством) — источник истины
# по-прежнему сами списки в units/Tiles.py, здесь только их объединение.
_FLAG_SOURCES = (
    (TileFlag.PHYSBODY, PHYSBODY_TILES),
    (TileFlag.SEMIPHYSBODY, SEMIPHYSBODY_TILES),
    (TileFlag.STANDING, STANDING_TILES),
    (TileFlag.BACKTILE, BACKTILES),
    (TileFlag.ITEM, ITEM_TILES),
    (TileFlag.STONE, STONE_TILES),
    (TileFlag.WOOD, WOOD_TILES),
    (TileFlag.CLASS_TILE, CLASS_TILE),
    (TileFlag.CLASS_UPDATING, CLASS_UPDATING_TILES),
    (TileFlag.CLASS_ALWAYS_UPDATING, CLASS_ALLWAYS_UPDATING_TILES),
    (TileFlag.ACTIVATABLE, ACTIVATE_TILES),
    (TileFlag.STATE_IS_LIST, ITEM_WITH_STATE_IS_LIST),
    (TileFlag.PLANT_TIMER, PLANT_WITH_TIMER),
    (TileFlag.STAND_ON_DIRT, PLANT_STAND_ON_DIRT),
    (TileFlag.STAND_ON_PLANT, PLANT_STAND_ON_PLANT),
    (TileFlag.MULTI_BLOCK, MULTI_BLOCK_PLANTS),
    (TileFlag.ON_EARTHEN, ON_EARTHEN_PLANTS),
    (TileFlag.RANDOM_SPRITE, PLANT_WITH_RANDOM_SPRITE),
    (TileFlag.RANDOM_LOCAL_POS, PLANT_WITH_RANDOM_LOCAL_POS),
    (TileFlag.DYNAMITE_IMMUNE, DYNAMITE_NOT_BREAK),
    (TileFlag.FOOD, Eats),
)


def _build_tile_flags():
    ids = set(all_tiles)
    for _flag, members in _FLAG_SOURCES:
        ids |= set(members)
    flags = {}
    for ttile in ids:
        f = TileFlag.NONE
        for flag, members in _FLAG_SOURCES:
            if ttile in members:
                f |= flag
        flags[ttile] = f
    return flags


TILE_FLAGS = _build_tile_flags()


# Те же флаги обычными int. IntFlag читается лучше, но его `&` идёт через
# enum.__call__/__new__ и стоит дорого: в профиле обслуживания за экраном
# enum.__and__ оказался САМОЙ дорогой строкой — 28924 вызова, больше, чем сама
# физика. В горячих циклах (collision_test — а он работает и на экране, на
# каждой сущности каждый кадр) берём биты отсюда, а TileFlag остаётся для
# читаемого кода вне горячего пути.
#
# Считается после TILE_FLAGS и потому уже включает блоки модов: они
# регистрируются в конце units/Tiles.py, то есть до импорта этого модуля.
TILE_FLAG_BITS = {ttile: int(flags) for ttile, flags in TILE_FLAGS.items()}
BIT_PHYSBODY = int(TileFlag.PHYSBODY)
BIT_SEMIPHYSBODY = int(TileFlag.SEMIPHYSBODY)


def get_flags(ttile) -> TileFlag:
    return TILE_FLAGS.get(ttile, TileFlag.NONE)


def has_flag(ttile, flag: TileFlag) -> bool:
    return bool(TILE_FLAGS.get(ttile, TileFlag.NONE) & flag)
