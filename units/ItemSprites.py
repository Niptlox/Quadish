"""Пиксель-арт предметов, у которых раньше стояли плоские квадраты.

Часть ресурсов добавлялась «цветом-заглушкой» (`create_tile_image("#FDE047")`
и т.п.): в инвентаре это выглядело как одноцветный квадрат, и сера от
жареного мяса отличалась только оттенком. Здесь у каждого предмета своя
форма (units/Graphics/PixelArt.py).

Сетки 16x16 и масштабируются до размера тайла ровно в 2 раза, поэтому
пиксели остаются квадратными.

Обозначения: B базовый цвет предмета, M/D/L его средний/тёмный/светлый
оттенок, K обводка, w белый, n светлая кость, p розовый, r красный,
y жёлтый, g зелёный, b голубой, o оранжевый, h тёмно-серый, '.' пусто.
"""
from units.Graphics.PixelArt import build_sprite

ITEM_SIZE = 16  # сетки квадратные 16x16 -> тайл 32x32 (ровно x2)

# --- Сера: угловатые кристаллы, а не комок --------------------------
SULFUR = [
    "................",
    "................",
    ".......KK.......",
    "......KLBK......",
    ".....KBLBK......",
    "....KKBLBKK.....",
    "...KLBBLBBLK....",
    "...KBLBBBLBK....",
    "..KKBBBLBBBKK...",
    "..KBLBBBBBLBK...",
    "..KBBLBBBLBBK...",
    "..KBBBLBBBBBK...",
    "...KDBBBBBDK....",
    "....KDDDDDK.....",
    ".....KKKKK......",
    "................",
]

# --- Хитин: изогнутая пластина панциря с рёбрами ---------------------
CHITIN = [
    "................",
    "................",
    "....KKKKKK......",
    "..KKLLLLLLKK....",
    ".KLLBBBBBBLLK...",
    ".KLBBKBBKBBBK...",
    ".KBBBKBBKBBBK...",
    ".KBBBKBBKBBBK...",
    ".KBBBKBBKBBBK...",
    ".KMBBKBBKBBMK...",
    "..KMMBBBBMMK....",
    "...KMMMMMMK.....",
    "....KKKKKK......",
    "................",
    "................",
    "................",
]

# --- Шкура: растянутая кожа с неровным краем ------------------------
HIDE = [
    "................",
    "...KK......KK...",
    "..KBBK....KBBK..",
    "..KBBBKKKKBBBK..",
    "..KBLLBBBBLLBK..",
    "..KBLBBBBBBLBK..",
    "...KBBBBBBBBK...",
    "...KBBBMMBBBK...",
    "...KBBMMMMBBK...",
    "...KBBBMMBBBK...",
    "...KBBBBBBBBK...",
    "..KBBBKKKKBBBK..",
    "..KBBK....KBBK..",
    "...KK......KK...",
    "................",
    "................",
]

# --- Сырое мясо: кусок с косточкой ----------------------------------
RAW_MEAT = [
    "................",
    "................",
    "......KKKK......",
    "....KKBBBBKK....",
    "...KBBBBBBBBK...",
    "..KBBLBBBBBBK...",
    "..KBBBBBBrBBK...",
    "..KBrBBBBBBBK...",
    "..KBBBBBrBBBK...",
    "...KBBBBBBBK....",
    "....KBBBBBK.....",
    "...nnKBBBKnn....",
    "..nwwnKKKnwwn...",
    "...nn......nn...",
    "................",
    "................",
]

# --- Жареное мясо: то же, но подрумяненное и с полосками ------------
COOKED_MEAT = [
    "................",
    "................",
    "......KKKK......",
    "....KKBBBBKK....",
    "...KBDBBBBDBK...",
    "..KBBBDBBDBBK...",
    "..KBDBBBBBDBK...",
    "..KBBBDBBDBBK...",
    "..KBDBBBBBDBK...",
    "...KBBBDBBBK....",
    "....KBBBBBK.....",
    "...nnKBBBKnn....",
    "..nwwnKKKnwwn...",
    "...nn......nn...",
    "................",
    "................",
]

# --- Космическая пыль: искры в щепотке ------------------------------
SPACE_DUST = [
    "................",
    "....w.....w.....",
    "...wLw...wLw....",
    "....w..w..w.....",
    "......wLw.......",
    "...w...w....w...",
    "..wLw......wLw..",
    "...w..KBK...w...",
    "....KBBBBBK.....",
    "...KBLBBBLBK....",
    "...KBBBLBBBK....",
    "...KBBBBBBBK....",
    "....KBBBBBK.....",
    ".....KKKKK......",
    "................",
    "................",
]

# --- Палка: обструганная ветка --------------------------------------
STICK = [
    "................",
    "...........KK...",
    "..........KBLK..",
    ".........KBLBK..",
    "........KBLBK...",
    ".......KBLBK....",
    "......KBLBK.....",
    ".....KBLBK......",
    "....KBLBK.......",
    "...KBLBK........",
    "..KBLBK.........",
    "..KBBK..........",
    "..KDK...........",
    "..KK............",
    "................",
    "................",
]

# --- Кусок арбуза: долька с корой и семечками -----------------------
WATERMELON_SLICE = [
    "................",
    "................",
    "....gggggggg....",
    "...gLLLLLLLLg...",
    "..gLwwwwwwwwLg..",
    "..gwBBBBBBBBwg..",
    ".gwBBBKBBBBBBwg.",
    ".gwBBBBBBKBBBwg.",
    ".gwBBKBBBBBBBwg.",
    "..gwBBBBBKBBwg..",
    "..gwwBBKBBBwwg..",
    "...gwwBBBBwwg...",
    "....gwwwwwwg....",
    ".....gggggg.....",
    "................",
    "................",
]

# --- Семена арбуза: несколько зёрен ---------------------------------
SEEDS = [
    "................",
    "................",
    "......KK........",
    ".....KBBK.......",
    ".....KBLK...KK..",
    "......KK...KBBK.",
    "...........KBLK.",
    "....KK......KK..",
    "...KBBK.........",
    "...KBLK....KK...",
    "....KK....KBBK..",
    "..........KBLK..",
    "...........KK...",
    "................",
    "................",
    "................",
]


def _item(rows, base):
    """Собрать спрайт предмета в размер тайла (ровно x2 от сетки)."""
    def create(size=None):
        return build_sprite(rows, base=base, size=size or (ITEM_SIZE * 2, ITEM_SIZE * 2))
    return create


create_sulfur_img = _item(SULFUR, "#FDE047")
create_chitin_img = _item(CHITIN, "#D4A373")
create_hide_img = _item(HIDE, "#A16207")
create_raw_meat_img = _item(RAW_MEAT, "#FCA5A5")
create_cooked_meat_img = _item(COOKED_MEAT, "#B45309")
create_space_dust_img = _item(SPACE_DUST, "#818CF8")
create_stick_img = _item(STICK, "#A16207")
create_watermelon_slice_img = _item(WATERMELON_SLICE, "#F87171")
create_seeds_img = _item(SEEDS, "#57534E")

# Готовые сетки под моды: мод может сослаться на них по имени, не рисуя
# свои (см. docs/MODS.md, поле "shape").
SHAPES = {
    "crystal": SULFUR,
    "plate": CHITIN,
    "hide": HIDE,
    "meat": RAW_MEAT,
    "meat_cooked": COOKED_MEAT,
    "dust": SPACE_DUST,
    "stick": STICK,
    "slice": WATERMELON_SLICE,
    "seeds": SEEDS,
}
