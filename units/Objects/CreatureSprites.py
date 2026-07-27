"""Пиксель-арт спрайты существ (все смотрят вправо).

Раньше каждое существо рисовалось эллипсами и прямоугольниками с дробными
координатами от размера спрайта. На 16–35 пикселях это давало
разъезжающиеся лапы, разную толщину конечностей и сочленения, висящие в
воздухе: форму невозможно проконтролировать, когда она пересчитывается
арифметикой. Здесь каждый пиксель поставлен руками (units/Graphics/PixelArt.py).

Сетки нарисованы так, чтобы до итогового размера существа масштабироваться
целым числом (в основном ×2, у голема ×3) — тогда пиксели остаются
квадратными и одинаковыми. Размеры существ см. в units/Objects/Creatures.py.

Обозначения: B базовый цвет, M средний тон, D тень, L блик, K обводка,
e глаз, w белый, h копыто/лапа, n рог/клюв, p нос, r красный, y жёлтый,
b голубой, s камень, v сине-фиолетовый, '.' прозрачный.
"""
from units.Graphics.PixelArt import build_sprite

# --- Корова: 16x13 -> 32x25 ------------------------------------------
COW = [
    "................",
    ".....KKKKK..KKK.",
    "....KBBBBBK.KBBK",
    "...KBDDBBBBKKBBK",
    "..KBBDDBBBBBBBBK",
    ".KBBBBBBBBBBBBBK",
    ".KBBBBBBBDDBBwwK",
    ".KBBBBBBBDDBBweK",
    ".KBBBBBBBBBBBwwK",
    ".KKBKKBBBKKBKKKK",
    "..KhK.KBBK.KhK..",
    "..KhK.KhhK.KhK..",
    "..KKK.KKKK.KKK..",
]

# --- Волк: 16x14 -> 32x28 --------------------------------------------
WOLF = [
    "................",
    "K...........K.K.",
    "KK.........KBKBK",
    ".KK........KBBBK",
    "..KKKKKKKKKKBBBK",
    ".KBBBBBBBBBBBBBK",
    ".KBBBBBBBBBBBeBK",
    ".KBBBBBBBBBBBBpK",
    ".KLLBBBBBBBLLKKK",
    ".KKLLLLLLLLLLK..",
    "..KBKK.....KBK..",
    "..KhK......KhK..",
    "..KhK......KhK..",
    "..KKK......KKK..",
]

# --- Лиса: 11x8 -> 22x16 ---------------------------------------------
# Пушистый хвост слева, острые уши, лапы под корпусом.
FOX = [
    "........K.K",
    "KK.....KBKB",
    "KDK...KKBBB",
    "KDDKKKKBBeB",
    ".KBBBBBBBBp",
    ".KwwBBBBBwK",
    "..KBK..KBK.",
    "..KhK..KhK.",
]

# --- Заяц: 16x12 -> 1:1 (нативный размер) ----------------------------
# Два ОТДЕЛЬНЫХ уха с зазором (иначе сливаются в одну башню), корпус
# компактный, а не вытянутый как у хорька.
RABBIT = [
    ".........K.K....",
    "........KBKBK...",
    "........KBKBK...",
    "........KBBBK...",
    "...KKKKKKBBBK...",
    "..KBBBBBBBBeK...",
    ".KBBBBBBBBBBK...",
    ".KBBBBBBBBBpK...",
    ".KwBBBBBBBKK....",
    ".KwwBBBBBwK.....",
    "..KhhK.KhhK.....",
    "..KKKK.KKKK.....",
]

# --- Олень: 18x18 -> 35x35 -------------------------------------------
# Рога — симметричная развилка над головой, а не россыпь точек.
DEER = [
    "..........n...n...",
    "...........n.n....",
    "..........nnnnn...",
    "...........n.n....",
    "..........KKKKK...",
    ".........KBBBBBK..",
    ".........KBBBeBK..",
    "..KKKKKKKKBBBBpK..",
    ".KBBBBBBBBBBBKKK..",
    "KBBBBBBBBBBBBK....",
    "KBBBBBBBBBBBK.....",
    "KBBBBBBBBBBBK.....",
    "KwwBBBBBBwwBK.....",
    ".KKBKKKKBKKK......",
    "..KBK..KBK........",
    "..KBK..KBK........",
    "..KhK..KhK........",
    "..KKK..KKK........",
]

# --- Верблюд: 19x19 -> 38x38 -----------------------------------------
CAMEL = [
    "...................",
    ".......KK..........",
    "......KBBK.....KKK.",
    ".....KBBBBK...KBBBK",
    "....KBBBBBBK.KBBBBK",
    "...KBBBBBBBBKKBBeBK",
    "..KBBBBBBBBBBBBBBpK",
    ".KBBBBBBBBBBBBBBKKK",
    ".KBBBBBBBBBBBBBK...",
    ".KBBBBBBBBBBBBK....",
    ".KBBBBBBBBBBBK.....",
    ".KMMBBBBBBMMBK.....",
    "..KKBKKKKBKKK......",
    "...KBK...KBK.......",
    "...KBK...KBK.......",
    "...KBK...KBK.......",
    "...KhK...KhK.......",
    "...KhK...KhK.......",
    "...KKK...KKK.......",
]

# --- Кабан: 14x11 -> 28x22 -------------------------------------------
BOAR = [
    "..............",
    ".....KKK...K..",
    "..KKKBBBKKKBK.",
    ".KBLLBBBBBBBBK",
    ".KBLLBBBBBBeBK",
    ".KBBBBBBBBBBBK",
    ".KBBBBBBBBBnpK",
    ".KDDBBBBBDDKKK",
    "..KKBKKKBKK...",
    "...KhK.KhK....",
    "...KKK.KKK....",
]

# --- Змея: 32x3 -> 1:1 (нативный размер) -----------------------------
# Всего 3 пикселя в высоту, поэтому тело сплошное (пунктир читался бы как
# мусор): чешуя — светлые отметины, голова справа с глазом и языком.
SNAKE = [
    "..KKKKKKKKKKKKKKKKKKKKKKKKKKKK..",
    ".KBBLBBLBBLBBLBBLBBLBBLBBBeBBrK.",
    "..KKKKKKKKKKKKKKKKKKKKKKKKKKKK..",
]

# --- Бес: 14x14 -> 28x28 ---------------------------------------------
IMP = [
    "..............",
    "..n........n..",
    "..nn......nn..",
    "...KKKKKKKK...",
    "..KBBBBBBBBK..",
    "..KByBBBByBK..",
    "..KBBBwwBBBK..",
    "...KKBBBBKK...",
    "....KBBBBK....",
    "...KBBBBBBK...",
    "..KBKBBBBKBK..",
    "..KhK.KK.KhK..",
    "..KKK.KK.KKK..",
    ".....KhhK.....",
]

# --- Скорпион: 11x8 -> 22x16 -----------------------------------------
# Хвост с жалом загнут над спиной (слева), клешни впереди (справа),
# лапы — под корпусом.
SCORPION = [
    "....DD.....",
    "...D..D....",
    "..D.....KK.",
    ".D.....KBBK",
    ".DKBBBBBBBK",
    "..KBBBeBBBK",
    "..KBBBBBBBK",
    "..K.K.K.KK.",
]

# --- Краб: 19x12 -> 1:1 (нативный размер) ----------------------------
# Две клешни по бокам, широкий панцирь, три пары лап под ним.
CRAB = [
    ".KK.............KK.",
    "KBBK...........KBBK",
    "KBBK..KKKKKKK..KBBK",
    ".KBK.KBBBBBBBK.KBK.",
    "..KK.KBeBBBeBK.KK..",
    "...KKKBBBBBBBKKK...",
    "....KBBBBBBBBBK....",
    "....KKKKKKKKKKK....",
    "...K.K.K.K.K.K.K...",
    "...K.K.K.K.K.K.K...",
    "...K...K.....K.K...",
    "...................",
]

# --- Пингвин: 8x11 -> 16x22 ------------------------------------------
PENGUIN = [
    "..KKKK..",
    ".KBBBBK.",
    ".KBeBeK.",
    ".KBwwByK",
    "KKBwwBKK",
    "KBKwwKBK",
    "KBKwwKBK",
    ".KKwwKK.",
    "..KwwK..",
    "..KyyK..",
    "..KKKK..",
]

# --- Летучая мышь: 11x7 -> 22x14 -------------------------------------
BAT = [
    "...........",
    "KK...D...KK",
    "KDKKDDDKKDK",
    "KDDDDBDDDDK",
    ".KKDBeBDKK.",
    "...KBnBK...",
    "....KKK....",
]

# --- Каменный голем: 17x19 -> 51x57 ----------------------------------
GOLEM = [
    ".....KKKKKKK.....",
    "....KsssssssK....",
    "....KsrsssrsK....",
    "....KsssssssK....",
    ".....KsKKKsK.....",
    "..KKKKKKKKKKKKK..",
    ".KsssKsssssKsssK.",
    "KsssKKsssssKKsssK",
    "KsssKKsssssKKsssK",
    "KsssKKsssssKKsssK",
    ".KKKKKsssssKKKKK.",
    "....KsssssssK....",
    "....KsssssssK....",
    "....KsssssssK....",
    ".....KKKKKKK.....",
    "....KsssKsssK....",
    "....KsssKsssK....",
    "....KsssKsssK....",
    "....KKKKKKKKK....",
]

# --- Космический дрейфер: 12x12 -> 25x25 -----------------------------
DRIFTER = [
    "....KKKK....",
    "..KKbbbbKK..",
    ".KbbbbbbbbK.",
    ".KbbwwwwbbK.",
    "KKbbwwwwbbKK",
    "KBBBBBBBBBBK",
    "KBBeBBBBeBBK",
    "KBBBBBBBBBBK",
    ".KBBBBBBBBK.",
    "..KKBKKBKK..",
    "...KvK.KvK..",
    "...KKK.KKK..",
]


def _maker(rows, default_base):
    """Собрать функцию-фабрику спрайта с прежней сигнатурой.

    Сигнатура (color, size, outline=...) сохранена, чтобы не менять код
    существ; outline больше не используется — контур нарисован в сетке."""
    def create(color=None, size=None, outline=None):
        return build_sprite(rows, base=color or default_base, size=size)
    return create


create_cow_sprite = _maker(COW, "#FFFAFA")
create_wolf_sprite = _maker(WOLF, "#708090")
create_fox_sprite = _maker(FOX, "#EA580C")
create_rabbit_sprite = _maker(RABBIT, "#E7E5E4")
create_deer_sprite = _maker(DEER, "#A16207")
create_camel_sprite = _maker(CAMEL, "#D2B48C")
create_boar_sprite = _maker(BOAR, "#44403C")
create_snake_sprite = _maker(SNAKE, "#4d7c0f")
create_imp_sprite = _maker(IMP, "#DC2626")
create_scorpion_sprite = _maker(SCORPION, "#D4A373")
create_crab_sprite = _maker(CRAB, "#DC2626")
create_penguin_sprite = _maker(PENGUIN, "#1E293B")
create_bat_sprite = _maker(BAT, "#3F3A36")
create_golem_sprite = _maker(GOLEM, "#78716C")
create_space_drifter_sprite = _maker(DRIFTER, "#818CF8")
