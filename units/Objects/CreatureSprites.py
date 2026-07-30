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

# --- Птица: 11x7 -> 22x14, два кадра (крылья вверх / вниз) -----------
# Два кадра, а не один: птица без взмаха читается как висящий в воздухе
# камешек. Тело в обоих кадрах одно и то же — меняются только крылья, иначе
# при подмене кадра птица «дёргалась» бы целиком.
BIRD_UP = [
    "..K.....K..",
    ".KBK...KBK.",
    ".KBBK.KBBK.",
    "KKBBBKBBBKK",
    "KBBBBBBBeBK",
    ".KKBBBBBnnK",
    "...KKKKKK..",
]

BIRD_DOWN = [
    "...KKKKK...",
    "..KBBBBBBK.",
    ".KBBBBBBBeK",
    "KKBBBBBBBnn",
    ".KBBK.KBBK.",
    "KBBK...KBBK",
    "K.........K",
]

# --- Ястреб: 13x8 -> 26x16, два кадра ---------------------------------
# Крылья длиннее и острее, чем у мелкой птицы: хищника надо отличать от стаи
# ещё до того, как он начал снижаться.
HAWK_UP = [
    "K.........K..",
    ".KK.....KK...",
    "..KBK.KBK....",
    "..KBBKKBBKKK.",
    ".KBBBBBBBBBeK",
    ".KKBBBBBBBBnn",
    "...KKBBBBKK..",
    "....KhKKhK...",
]

HAWK_DOWN = [
    "....KKKKKK...",
    "..KBBBBBBBK..",
    ".KBBBBBBBBBeK",
    ".KKBBBBBBBBnn",
    "..KBBKKBBKK..",
    ".KBBK.KBBK...",
    "KBK.....KBK..",
    "K.........K..",
]

# --- Рыба: 11x7 -> 22x14 ---------------------------------------------
# Хвост слева, глаз справа — как у всех: все существа смотрят вправо.
FISH = [
    "K....KKK...",
    "KK.KBBBBK..",
    "KBKBBBBBBK.",
    "KBBBBBBeBBK",
    "KBKBBBBBBK.",
    "KK.KBBBBK..",
    "K....KKK...",
]

# --- Хищная рыба: 12x8 -> 24x16 --------------------------------------
# Отличается от мирной ровно одним читаемым признаком — зубами (w).
PIRANHA = [
    "............",
    "K....KKKK...",
    "KK.KBBBBBK..",
    "KBKBBBBBBBK.",
    "KBBBBBBBeBBK",
    "KBKBBBBBwwwK",
    "KK.KBBBBBK..",
    "K....KKKK...",
]

# --- Медуза: 9x11 -> 18x22 -------------------------------------------
# Купол и щупальца. Единственное существо, смотрящее не вправо, а вниз:
# у медузы нет «переда».
JELLY = [
    "..KKKKK..",
    ".KBBBBBK.",
    "KBBBBBBBK",
    "KBBeBeBBK",
    "KBBBBBBBK",
    ".KKKKKKK.",
    ".K.K.K.K.",
    ".K.K.K.K.",
    "..K.K.K..",
    "..K.K.K..",
    "...K.K...",
]

# --- Глубинник: 14x9 -> 28x18 ----------------------------------------
# Обитатель полостей с водой: тёмный, крупный, со светящимся глазом (y).
LURKER = [
    "..............",
    "K.....KKKKK...",
    "KK..KBBBBBBK..",
    "KBK.KBBBBBBBK.",
    "KBBKKBBBBBByBK",
    "KBBKKBBBBBBBnK",
    "KBK.KBBBBBBBK.",
    "KK..KBBBBBBK..",
    "K.....KKKKK...",
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


# --- Пылевой рой: 11x9 -> сгусток пыли с глазами --------------------
DUST_SWARM = [
    "..K.....K..",
    ".KBK.K.KBK.",
    "KBBBKBKBBBK",
    "KBBeBBBeBBK",
    "KBBBBBBBBBK",
    ".KBBBBBBBK.",
    "..KBBBBBK..",
    "...KBBBK...",
    "....KKK....",
]

# --- Пустотный страж: 13x15 -> тяжёлая фигура из пустотного камня ----
VOID_SENTINEL = [
    "....KKKKK....",
    "...KBBBBBK...",
    "...KBrBrBK...",
    "...KBBBBBK...",
    "....KBBBK....",
    "..KKKKKKKKK..",
    ".KBBKBBBKBBK.",
    "KBBBKBBBKBBBK",
    "KBBBKBBBKBBBK",
    ".KKKKBBBKKKK.",
    "....KBBBK....",
    "....KBBBK....",
    "....KBBBK....",
    "...KBBKBBK...",
    "...KKK.KKK...",
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
_bird_up = _maker(BIRD_UP, "#57534E")
_bird_down = _maker(BIRD_DOWN, "#57534E")


def create_bird_sprites(color=None, size=None):
    """Два кадра взмаха. Возвращает список — существо листает его по такту."""
    return [_bird_up(color, size), _bird_down(color, size)]


_hawk_up = _maker(HAWK_UP, "#78350F")
_hawk_down = _maker(HAWK_DOWN, "#78350F")


def create_hawk_sprites(color=None, size=None):
    """Кадры взмаха ястреба — своя сетка: крылья длиннее и острее."""
    return [_hawk_up(color, size), _hawk_down(color, size)]


create_fish_sprite = _maker(FISH, "#38BDF8")
create_piranha_sprite = _maker(PIRANHA, "#65A30D")
create_jelly_sprite = _maker(JELLY, "#C084FC")
create_lurker_sprite = _maker(LURKER, "#1E3A5F")
create_golem_sprite = _maker(GOLEM, "#78716C")
create_space_drifter_sprite = _maker(DRIFTER, "#818CF8")
create_dust_swarm_sprite = _maker(DUST_SWARM, "#7DD3FC")
create_void_sentinel_sprite = _maker(VOID_SENTINEL, "#312E81")
