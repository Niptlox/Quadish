"""Структуры, привязанные к биомам и зонам (docs/STRUCTURES.md).

Все схемы — ASCII (см. units/Map/structure_builder.py): '.' не трогает
рельеф, пробел расчищает воздух, цифра ставит плиту с надписью нужного
варианта (units/Lore.py).

Описание структуры: (имя, шанс, схема, биомы). Биомы — кортеж номеров
(см. biome_names в units/biomes.py) либо None = любой биом своей зоны:
0 desert, 1 savanna, 2 tropical_woodland, 3 tundra, 4 seasonal_forest,
5 rainforest, 6 temperate_forest, 7 temperate_rainforest,
8 boreal_forest, 9 hell.

Постройки задуманы как следы ушедшей цивилизации, поэтому почти в каждой
стоит плита с надписью — это основной канал подачи сюжета.
"""
from units.Map.structure_builder import build_ascii

# --- Поверхность -------------------------------------------------------

# Пустыня: путевой камень к «приёмной площадке» (алтарю).
DESERT_MARKER = build_ascii([
    "..o..",
    ".o8o.",
    ".ooo.",
    ".._..",
])

# Пустыня: занесённый песком склеп с припасами.
DESERT_CRYPT = build_ascii([
    "ooooooooo",
    "o       o",
    "o C   W o",
    "o       o",
    "o 8   F o",
    "o       o",
    "ooooDoooo",
    "=..=..=.=",
])

# Саванна: дозорный пост — смотрит вверх, а не по сторонам.
SAVANNA_WATCHPOST = build_ascii([
    "...ppp...",
    "...p p...",
    "...p1p...",
    "...ppp...",
    "...p p...",
    "...p p...",
    "...ppp...",
    "...=.=...",
])

# Тундра: брошенная стоянка. Холод пришёл после добычи блора.
TUNDRA_CAMP = build_ascii([
    ".ppppp.",
    ".p   p.",
    ".p z p.",
    ".p 9 p.",
    ".pFCKp.",
    ".ppDpp.",
    ".=...=.",
])

# Тропический лес: затопленный храм, заросший лианами.
TROPICAL_TEMPLE = build_ascii([
    "mmmmmmmmmmm",
    "m v     v m",
    "m  ~~~~~  m",
    "m  ~~~~~  m",
    "m 2~~~~~C m",
    "mmmmmmmmmmm",
    "=..=...=..=",
])

# Джунгли: оранжерея — семена брали с собой, землю нет.
RAINFOREST_GREENHOUSE = build_ascii([
    "ppppppppp",
    "p       p",
    "p qqqqq p",
    "p ddddd p",
    "p 5   C p",
    "pppDppppp",
    "=..=...=.",
])

# Лес (умеренный/сезонный): обсерватория, где спорили — уйти или позвать.
FOREST_OBSERVATORY = build_ascii([
    "....###....",
    "...##A##...",
    "...#   #...",
    "...# 3 #...",
    "...#   #...",
    "...## ##...",
    "...#   #...",
    "...#C t#...",
    "...##D##...",
    "...=...=...",
])

# Тайга: лесопилка, брошенная на середине работы.
BOREAL_SAWMILL = build_ascii([
    "..w.....w..",
    "..w.....w..",
    "pppppppppp.",
    "p  t   C p.",
    "p        p.",
    "ppppDppppp.",
    "=..=...=.=.",
])

# --- Пещеры (глубина) --------------------------------------------------

# Забой: норма на смену — двенадцать мер блора.
DEEP_MINE = build_ascii([
    "ooooooooooo",
    "o    *    o",
    "o 4  -  C o",
    "obb     bbo",
    "obb  !  bbo",
    "ooooooooooo",
])

# Подземный знак: «дальше не копать, дальше оно слушает».
CAVE_SHRINE = build_ascii([
    "..GGG..",
    ".G   G.",
    ".G 7 G.",
    ".G   G.",
    "..GGG..",
])


# Описания: (имя, шанс, схема, биомы, якорь)
#
# Якорь "surface" — структура опускается на землю (GameMap._snap_to_surface),
# а просвет под ней на склоне добирает фундамент ('=' / '_' в схеме).
# Якорь None — как раньше: случайная высота внутри блока структур; так и
# нужно пещерным постройкам, они должны стоять в камне.
Structures_biome_middleworld = {
    10020: ("desert marker", 0.20, DESERT_MARKER, (0,), "surface"),
    10021: ("desert crypt", 0.08, DESERT_CRYPT, (0,), "surface"),
    10022: ("savanna watchpost", 0.12, SAVANNA_WATCHPOST, (1,), "surface"),
    10023: ("tundra camp", 0.12, TUNDRA_CAMP, (3,), "surface"),
    10024: ("tropical temple", 0.07, TROPICAL_TEMPLE, (2,), "surface"),
    10025: ("rainforest greenhouse", 0.10, RAINFOREST_GREENHOUSE, (5,), "surface"),
    10026: ("forest observatory", 0.06, FOREST_OBSERVATORY, (4, 6, 7), "surface"),
    10027: ("boreal sawmill", 0.12, BOREAL_SAWMILL, (8,), "surface"),
    # пещерные постройки — без привязки к поверхности, они стоят в камне
    10028: ("deep mine", 0.10, DEEP_MINE, None, None),
    10029: ("cave shrine", 0.06, CAVE_SHRINE, None, None),
}
