"""Полости с водой внутри островов.

Зачем они есть. Вода в Quadish была только на поверхности — озеро в чаше
острова (`GameMap.lake_tile_at`). Под землёй воды не было вообще, и это
слышно по игре: спуск в шахту — это восемьсот тайлов однородной породы с
рудными пятнами, и единственное, что там меняется, — цвет камня. Полость с
водой — находка, которая ничего не требует от игрока и при этом меняет
картинку: пустота там, где её быть не должно, и в ней зеркало.

Как устроено — тем же приёмом, что озёра и подземелья: **чистая функция от
(тайл, сид)**. Любой чанк спрашивает «что у меня в этом тайле из-за полости»
и получает ответ, не зная соседей и не требуя генерации.

Три решения, которые здесь не случайны:

* **Полость обязана быть запечатана в породе.** Иначе она вскрывается сбоку
  и вода висит стеной над пустотой — вода в игре не течёт, её никто не
  сольёт. Проверяем кольцо вокруг полости через `terrain_is_solid`: не
  «похоже на камень», а тот же самый предикат, которым генератор кладёт
  породу.
* **Вода стоит не под потолок.** Над зеркалом остаётся воздух, а сам ряд
  зеркала — неполный уровень воды (`water_frame`). Именно это делает
  многоуровневость воды видимой: линия воды не совпадает с сеткой блоков, и
  полость читается как подземное озеро, а не как синий прямоугольник.
* **Линза, а не шар.** Вертикально полость сжата: шар радиуса 9 — это
  колодец в породе, а вытянутая по горизонтали каверна выглядит вымытой
  водой, то есть тем, чем она и должна быть.
"""
import random

from units.common import TOP_MIDDLE_WORLD, BOTTOM_MIDDLE_WORLD
from units.Tiles import WATER_TILE, WATER_LEVELS, water_frame

# Решётка мест. Клетка небольшая: полость — не событие масштаба подземелья, а
# деталь породы, и встречаться она должна регулярно, иначе её просто никто
# никогда не увидит.
POCKET_CELL_W = 50
POCKET_CELL_H = 40
POCKET_CHANCE = 0.9
POCKET_MIN_R, POCKET_MAX_R = 4, 10
# Вертикальное сжатие: полуось по Y = полуось по X * это.
POCKET_FLAT = 0.55
# Породы вокруг полости должно быть не меньше этого — иначе полость вскроется
# соседней пещерой и вода будет висеть стеной.
POCKET_WALL = 3
# Ниже этого не роем: воде в аду не место (там лава), а верх ограничен полосой
# среднего мира.
POCKET_MIN_Y = TOP_MIDDLE_WORLD + 40

AIR = 0


class Pocket:
    """Одна полость: линза породы, вымытая водой, с зеркалом внутри."""

    __slots__ = ("cx", "cy", "rx", "ry", "mirror", "fill")

    def __init__(self, cx, cy, rx, ry, mirror, fill):
        self.cx, self.cy = cx, cy
        self.rx, self.ry = rx, ry
        self.mirror = mirror        # ряд зеркала (верхний ряд воды)
        self.fill = fill            # уровень заполнения ряда зеркала, 1..4

    @property
    def bounds(self):
        """(x0, y0, x1, y1) — включительно, для дешёвой проверки чанка."""
        return (self.cx - self.rx, self.cy - self.ry,
                self.cx + self.rx, self.cy + self.ry)

    def tile_at(self, tx, ty):
        """(тайл, кадр) или None, если тайл вне полости."""
        dx = (tx - self.cx) / self.rx
        dy = (ty - self.cy) / self.ry
        if dx * dx + dy * dy > 1:
            return None
        if ty > self.mirror:
            return WATER_TILE, water_frame(WATER_LEVELS, deep=True)
        if ty == self.mirror:
            return WATER_TILE, water_frame(self.fill, deep=True)
        return AIR, 0                       # воздух над зеркалом


def _sealed(cx, cy, rx, ry, base):
    """Запечатана ли полость в породе.

    Пробуем кольцо чуть шире полости в восьми направлениях. Восемь точек, а
    не полный обход границы: обход стоил бы под сотню вызовов шума на каждую
    клетку решётки, а задача проверки — отсеять полость, попавшую в готовую
    пещеру, и для этого хватает выборки.
    """
    from units.Map.GameMap import terrain_is_solid
    ox, oy = rx + POCKET_WALL, ry + POCKET_WALL
    for dx, dy in ((0, -oy), (0, oy), (-ox, 0), (ox, 0),
                   (-ox * 7 // 10, -oy * 7 // 10), (ox * 7 // 10, -oy * 7 // 10),
                   (-ox * 7 // 10, oy * 7 // 10), (ox * 7 // 10, oy * 7 // 10)):
        if not terrain_is_solid(cx + dx, cy + dy, base):
            return False
    return True


def pocket_site(cell_x, cell_y, base):
    """Полость в клетке решётки или None. Детерминирована по (сид, клетка)."""
    rnd = random.Random(f"pocket:{base}:{cell_x}:{cell_y}")
    if rnd.random() >= POCKET_CHANCE:
        return None
    rx = rnd.randint(POCKET_MIN_R, POCKET_MAX_R)
    ry = max(2, int(rx * POCKET_FLAT))
    margin_x = rx + POCKET_WALL
    margin_y = ry + POCKET_WALL
    cx = cell_x * POCKET_CELL_W + rnd.randint(margin_x, POCKET_CELL_W - margin_x)
    cy = cell_y * POCKET_CELL_H + rnd.randint(margin_y, POCKET_CELL_H - margin_y)
    if not (POCKET_MIN_Y < cy - margin_y and cy + margin_y < BOTTOM_MIDDLE_WORLD):
        return None
    if not _sealed(cx, cy, rx, ry, base):
        return None
    # Зеркало: вода занимает большую часть высоты, но НЕ всю — сверху должен
    # остаться воздух, иначе неполный ряд воды окажется под потолком и никакой
    # линии воды не будет видно.
    rows = 2 * ry + 1
    water_rows = max(1, int(rows * rnd.uniform(0.5, 0.8)))
    mirror = cy + ry - water_rows + 1
    if mirror <= cy - ry:
        mirror = cy - ry + 1
    return Pocket(cx, cy, rx, ry, mirror, rnd.randint(2, WATER_LEVELS))


def water_pocket_tile_at(tx, ty, base, cache=None):
    """Что стоит в тайле из-за полости: (тайл, кадр) или None.

    Чистая функция от (тайл, сид) — как lake_tile_at и dungeon_tile_at.
    """
    cell = (tx // POCKET_CELL_W, ty // POCKET_CELL_H)
    if cache is None:
        cache = {}
    if cell not in cache:
        cache[cell] = pocket_site(cell[0], cell[1], base)
    site = cache[cell]
    if site is None:
        return None
    return site.tile_at(tx, ty)


def chunk_touches_pocket(base_x, base_y, chunk_size, base, cache=None):
    """Есть ли шанс, что полость задевает чанк.

    Дешёвая проверка перед дорогой, как у озёр и подземелий: `pocket_site`
    считает пробы породы, и платить за них в чанках без полостей незачем.
    """
    if not (POCKET_MIN_Y < base_y + chunk_size and base_y < BOTTOM_MIDDLE_WORLD):
        return False
    if cache is None:
        cache = {}
    for cx in range(base_x // POCKET_CELL_W, (base_x + chunk_size) // POCKET_CELL_W + 1):
        for cy in range(base_y // POCKET_CELL_H, (base_y + chunk_size) // POCKET_CELL_H + 1):
            if (cx, cy) not in cache:
                cache[(cx, cy)] = pocket_site(cx, cy, base)
            site = cache[(cx, cy)]
            if site is None:
                continue
            x0, y0, x1, y1 = site.bounds
            if x0 < base_x + chunk_size and base_x <= x1 and \
                    y0 < base_y + chunk_size and base_y <= y1:
                return True
    return False
