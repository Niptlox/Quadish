"""Случайно генерируемые подземелья.

Чем отличается от структуры (`docs/STRUCTURES.md`). Структура — заранее
нарисованная схема: она всегда одна и та же, её можно выучить, и второй раз
она уже не место, а декорация. Подземелье **строится генератором**: комнаты,
проходы и добыча раскладываются из сида, поэтому оно каждый раз другое, и
единственный способ узнать, что внутри, — войти.

Как это устроено технически — тем же приёмом, что и озёра
(`GameMap.lake_tile_at`): **чистая функция от (тайл, сид)**. Никакого
глобального состояния и никакой «постройки целиком»: любой чанк может
спросить «что у меня в этом тайле из-за подземелья» и получить ответ, не
трогая соседей. Иначе подземелье, пересекающее границу чанков, порвалось бы
пополам — а они заведомо больше чанка.

Что здесь специфично для Quadish, а не взято из любой игры с данжами:

* **Вертикальные связи — это блоровые столбы** (234/236). Мир вертикальный,
  и переход в нём держится на блоре (`docs/STORY.md`); подземелье построено
  тем же способом, которым игрок сам строит шахты. Заодно это лучший способ
  показать блок тому, кто его ещё не крафтил.
* **Награда — плотность, а не редкость.** В сокровищнице лежат блоки руды,
  которые в породе встречаются раз на сотни тайлов (`docs/BALANCE_SCHEME.md`).
  Подземелье не даёт того, чего нет в мире, — оно даёт то, что в мире
  добывается часами.
* **Чем глубже, тем богаче и злее.** Награда идёт по той же кривой, что и
  опасность, — общее правило игры, а не отдельное правило подземелий.
"""
import random

from units.common import (TSIZE, BOTTOM_MIDDLE_WORLD, START_HELL_Y,
                          START_SPACE_Y, depth_reward)

# Решётка подземелий. Клетка широкая: подземелье должно быть событием на
# карте, а не встречаться за каждым поворотом.
DUNGEON_CELL_W = 300
DUNGEON_CELL_H = 200
DUNGEON_CHANCE = 0.35
# Выше этого подземелий не бывает: они должны быть НАЙДЕНЫ под землёй, а не
# торчать из холма рядом со спавном.
MIN_DEPTH = 90

# Толщина стены между комнатами. 2 — чтобы стену было видно как стену и
# чтобы её нельзя было пробить одним ударом насквозь.
WALL = 2
ROOM_MIN_W, ROOM_MAX_W = 9, 15
ROOM_MIN_H, ROOM_MAX_H = 6, 9
COLS_MIN, COLS_MAX = 3, 5
ROWS_MIN, ROWS_MAX = 2, 4

# Тайлы
AIR = 0
BRICK = 31
MOSSY = 32
OLD = 33
LIFT_UP = 234
LIFT_DOWN = 236
CHEST = 129
LAMP = 215
# Плита с надписью (units/Lore.py): вариант выбирается кадром тайла
TABLET = 300
# Отголосок — единственный НПС (units/Objects/TileClasses.py Echo)
ECHO = 239
ORE_GOLD, ORE_SILVER, ORE_BLORE, ORE_IRON = 23, 25, 21, 24


class DungeonKind:
    """Вид подземелья: из чего сложено и что в сокровищнице."""

    def __init__(self, name, wall, floor, vault_ores, guards):
        self.name = name
        self.wall = wall
        self.floor = floor
        self.vault_ores = vault_ores
        self.guards = guards


KINDS = {
    "crypt": DungeonKind(
        "склеп", MOSSY, BRICK,
        (ORE_SILVER, ORE_IRON, ORE_GOLD),
        ("Slime", "Bat", "StoneGolem")),
    "forge": DungeonKind(
        "кузня", OLD, BRICK,
        (ORE_GOLD, ORE_BLORE, ORE_SILVER),
        ("Imp", "StoneGolem")),
    "station": DungeonKind(
        "станция", BRICK, OLD,
        (ORE_SILVER, ORE_GOLD),
        ("SpaceDrifter", "DustSwarm")),
}


def kind_for_depth(ty):
    """Какой вид подземелья уместен на этой глубине."""
    if ty <= START_SPACE_Y + 400:
        return "station"
    if ty >= START_HELL_Y:
        return "forge"
    return "crypt"


class Dungeon:
    """Разложенное подземелье: комнаты, проходы, шахты, сокровищница.

    Раскладка считается один раз на клетку и кэшируется вызывающим: она
    дешёвая, но не настолько, чтобы делать её на каждый тайл.
    """

    def __init__(self, cell_x, cell_y, base):
        rnd = random.Random(f"dungeon:{base}:{cell_x}:{cell_y}")
        self.ok = rnd.random() < DUNGEON_CHANCE
        if not self.ok:
            return
        self.cols = rnd.randint(COLS_MIN, COLS_MAX)
        self.rows = rnd.randint(ROWS_MIN, ROWS_MAX)
        self.rw = rnd.randint(ROOM_MIN_W, ROOM_MAX_W)
        self.rh = rnd.randint(ROOM_MIN_H, ROOM_MAX_H)
        self.w = self.cols * (self.rw + WALL) + WALL
        self.h = self.rows * (self.rh + WALL) + WALL
        # Начало — внутри клетки, с запасом, чтобы подземелье целиком лежало
        # в своей клетке: иначе два соседних могли бы наложиться, и раскладка
        # перестала бы быть функцией одной клетки.
        self.x = cell_x * DUNGEON_CELL_W + rnd.randint(4, max(4, DUNGEON_CELL_W - self.w - 4))
        self.y = cell_y * DUNGEON_CELL_H + rnd.randint(4, max(4, DUNGEON_CELL_H - self.h - 4))
        self.kind = KINDS[kind_for_depth(self.y)]
        # Сокровищница — самая дальняя комната нижнего ряда: до неё надо идти
        self.vault = (self.rows - 1, self.cols - 1)
        self.entrance = (0, 0)
        # Вход. Без него подземелье наглухо запечатано собственной стеной, и
        # игрок не найдёт его никогда — а «случайно генерируемое подземелье,
        # которое нельзя найти» это просто потраченная генерация. Коридор
        # уходит наружу и обрывается в породе: если рядом пещера — они
        # сойдутся, если нет — игрок наткнётся на кладку, копая.
        self.entry_len = rnd.randint(6, 14)
        self.entry_side = rnd.choice((-1, 1))
        # Связи. Верхний ряд и левый столбец связаны всегда — это гарантия,
        # что подземелье проходимо целиком; остальное решает жребий, и от
        # этого раскладка каждый раз разная.
        self.links_right = set()
        self.links_down = set()
        for r in range(self.rows):
            for c in range(self.cols - 1):
                # Верхний ряд и НИЖНИЙ связаны всегда. Нижний — потому что в
                # нём сокровищница: пока он собирался жребием, до неё нельзя
                # было дойти в 8 подземельях из 25, и снаружи это не видно.
                if r == 0 or r == self.rows - 1 or rnd.random() < 0.65:
                    self.links_right.add((r, c))
        for r in range(self.rows - 1):
            for c in range(self.cols):
                if c == 0 or rnd.random() < 0.5:
                    self.links_down.add((r, c))
        self.rnd_tag = f"{base}:{cell_x}:{cell_y}"

    # ---------- геометрия ----------

    def room_rect(self, r, c):
        """Прямоугольник комнаты (x, y, w, h) в мировых тайлах."""
        x = self.x + WALL + c * (self.rw + WALL)
        y = self.y + WALL + r * (self.rh + WALL)
        return x, y, self.rw, self.rh

    def contains(self, tx, ty):
        if self.x <= tx < self.x + self.w and self.y <= ty < self.y + self.h:
            return True
        return self._in_entry(tx, ty)

    def _in_entry(self, tx, ty):
        """Тайл во входном коридоре снаружи стены."""
        _, ry, _, rh = self.room_rect(*self.entrance)
        if not (ry + rh - 4 <= ty <= ry + rh - 1):
            return False
        # Захватываем и саму внешнюю стену (WALL тайлов), иначе коридор
        # упирается в кладку и вход остаётся нарисованным, но непроходимым.
        if self.entry_side < 0:
            return self.x - self.entry_len <= tx < self.x + WALL
        return self.x + self.w - WALL <= tx < self.x + self.w + self.entry_len

    def room_at(self, tx, ty):
        """Какая комната содержит тайл, или None (стена/проход)."""
        lx, ly = tx - self.x - WALL, ty - self.y - WALL
        if lx < 0 or ly < 0:
            return None
        c, inx = divmod(lx, self.rw + WALL)
        r, iny = divmod(ly, self.rh + WALL)
        if c >= self.cols or r >= self.rows or inx >= self.rw or iny >= self.rh:
            return None
        return r, c

    # ---------- содержимое ----------

    def tile_at(self, tx, ty):
        """Что стоит в этом тайле из-за подземелья, или None."""
        if not self.contains(tx, ty):
            return None
        if self._in_entry(tx, ty):
            _, ry, _, rh = self.room_rect(*self.entrance)
            return self.kind.floor if ty == ry + rh - 1 else AIR
        room = self.room_at(tx, ty)
        if room is not None:
            return self._room_tile(room, tx, ty)
        return self._wall_tile(tx, ty)

    def _room_tile(self, room, tx, ty):
        r, c = room
        rx, ry, rw, rh = self.room_rect(r, c)
        floor_y = ry + rh - 1
        shaft = rx + rw // 2
        # Столбы шахты пробивают пол комнаты и входят в комнату снизу.
        # Без этого шахта упиралась в пол, и нижние этажи оказывались
        # отрезаны: проверка связности показала, что сокровищница была
        # недостижима во ВСЕХ 25 проверенных подземельях. Данж при этом
        # выглядел целым — такое ушло бы в релиз незамеченным.
        if tx in (shaft, shaft - 1):
            if ty == floor_y and (r, c) in self.links_down:
                return LIFT_DOWN if tx == shaft else LIFT_UP
            if ty <= ry + 1 and (r - 1, c) in self.links_down:
                return LIFT_DOWN if tx == shaft else LIFT_UP
        if ty == floor_y:
            return self.kind.floor
        if room == self.vault:
            return self._vault_tile(tx, ty, rx, ry, rw, rh)
        if room == self.entrance:
            # Лампы под потолком: подземелье должно быть видно изнутри, а
            # заодно это показывает игроку, что лампа вообще существует.
            if ty == ry and (tx - rx) % 4 == 2:
                return LAMP
            # Плита с надписью у входа: подземелье попадает в журнал сюжета
            # (units/Story.py) — то есть находка ещё и продвигает историю.
            if ty == floor_y - 1 and tx == rx + 1:
                return TABLET
            # И отголосок рядом: он говорит про ту главу, в которой игрок
            # сейчас, поэтому найденное подземелье само даёт направление.
            if ty == floor_y - 1 and tx == rx + 3:
                return ECHO
        return AIR

    def _vault_tile(self, tx, ty, rx, ry, rw, rh):
        """Сокровищница: плотная кладка руды и сундук.

        Плотность и есть награда: золото в породе встречается раз на 917
        тайлов (`docs/BALANCE_SCHEME.md`), а тут его столбик.
        """
        rnd = random.Random(f"vault:{self.rnd_tag}:{tx}:{ty}")
        if ty == ry + rh - 2 and tx == rx + rw // 2:
            return CHEST
        # Руда лежит ВЫШЕ прохода, а не в нём. Когда она занимала нижние
        # ряды, она забивала и дверной проём: горизонтальный вход в комнату
        # идёт как раз по трём тайлам над полом, и сокровищница оказывалась
        # замурована собственным сокровищем — проверка связности ловила это
        # как «недостижима» в 8 подземельях из 25.
        if ty > ry + rh - 4 or rnd.random() > 0.45:
            return AIR
        # Состав кладки: самое ценное — редкое и здесь. Ровный слой золота
        # давал бы за одно подземелье три золотые кирки, то есть обесценивал
        # бы всю верхнюю часть лестницы материалов (docs/BALANCE_SCHEME.md).
        ores = self.kind.vault_ores
        roll = rnd.random()
        if roll < 0.55:
            return ores[0]
        if roll < 0.85:
            return ores[1 % len(ores)]
        return ores[-1]

    def _wall_tile(self, tx, ty):
        """Стена, проход или шахта."""
        # Горизонтальный проход: в стене между связанными комнатами
        passage = self._passage_tile(tx, ty)
        if passage is not None:
            return passage
        return self.kind.wall

    def _passage_tile(self, tx, ty):
        lx, ly = tx - self.x - WALL, ty - self.y - WALL
        if lx < 0 or ly < 0:
            return None
        c, inx = divmod(lx, self.rw + WALL)
        r, iny = divmod(ly, self.rh + WALL)
        if r >= self.rows or c >= self.cols:
            return None
        rx, ry, rw, rh = self.room_rect(r, c)
        # проход вправо: полоса в 3 тайла у пола
        if inx >= self.rw and (r, c) in self.links_right:
            if ry + rh - 4 <= ty <= ry + rh - 1:
                return self.kind.floor if ty == ry + rh - 1 else AIR
        # шахта вниз: два столба блора, вверх и вниз — как игрок строит сам
        if iny >= self.rh and (r, c) in self.links_down:
            shaft = rx + rw // 2
            if tx == shaft:
                return LIFT_DOWN
            if tx == shaft - 1:
                return LIFT_UP
        return None

    # ---------- обитатели ----------

    def chest_spots(self, chunk_x, chunk_y, chunk_size):
        """Где в этом чанке стоят сундуки подземелья."""
        r, c = self.vault
        rx, ry, rw, rh = self.room_rect(r, c)
        tx, ty = rx + rw // 2, ry + rh - 2
        if (chunk_x * chunk_size <= tx < (chunk_x + 1) * chunk_size and
                chunk_y * chunk_size <= ty < (chunk_y + 1) * chunk_size):
            return [(tx, ty)]
        return []

    def guard_spots(self, chunk_x, chunk_y, chunk_size):
        """Где в этом чанке должны стоять стражи.

        Возвращает [(имя_класса, tx, ty)]. Считается от сида, поэтому чанк,
        сгенерированный дважды, даёт тех же стражей и не плодит толпу.
        """
        spots = []
        for r in range(self.rows):
            for c in range(self.cols):
                rx, ry, rw, rh = self.room_rect(r, c)
                if not (chunk_x * chunk_size <= rx < (chunk_x + 1) * chunk_size and
                        chunk_y * chunk_size <= ry < (chunk_y + 1) * chunk_size):
                    continue
                rnd = random.Random(f"guard:{self.rnd_tag}:{r}:{c}")
                # Чем глубже подземелье, тем больше стражи — та же кривая,
                # что у награды и у силы существ.
                limit = 1 + int(2 * depth_reward(ry))
                if (r, c) == self.vault:
                    limit += 1
                for i in range(limit):
                    if rnd.random() > 0.7:
                        continue
                    name = rnd.choice(self.kind.guards)
                    spots.append((name, rx + rnd.randint(1, max(1, rw - 2)), ry + rh - 2))
        return spots


def dungeon_site(cell_x, cell_y, base):
    """Подземелье в клетке решётки или None."""
    d = Dungeon(cell_x, cell_y, base)
    return d if d.ok else None


def in_dungeon_band(ty):
    """Может ли на этой высоте вообще быть подземелье.

    Две полосы: под землёй (глубже MIN_DEPTH и до дна ада) и в космосе.
    Поверхность исключена намеренно — подземелье должно быть НАЙДЕНО.
    """
    return MIN_DEPTH < ty < START_HELL_Y + 300 or ty <= START_SPACE_Y + 400


def dungeon_at(tx, ty, base, cache=None):
    """Подземелье, накрывающее этот тайл, или None."""
    if not in_dungeon_band(ty):
        return None
    cell = (tx // DUNGEON_CELL_W, ty // DUNGEON_CELL_H)
    if cache is None:
        cache = {}
    if cell not in cache:
        cache[cell] = dungeon_site(cell[0], cell[1], base)
    site = cache[cell]
    if site is None or not site.contains(tx, ty):
        return None
    return site


def dungeon_tile_at(tx, ty, base, cache=None):
    """Что стоит в тайле из-за подземелья: тип тайла или None.

    Чистая функция от (тайл, сид) — как lake_tile_at и terrain_is_solid.
    """
    site = dungeon_at(tx, ty, base, cache)
    if site is None:
        return None
    return site.tile_at(tx, ty)


def chunk_touches_dungeon(base_x, base_y, chunk_size, base, cache=None):
    """Есть ли шанс, что подземелье задевает этот чанк.

    Дешёвая проверка перед дорогой: платить за раскладку в чанках, где
    подземелий нет вовсе, незачем — та же логика, что у озёр.
    """
    if cache is None:
        cache = {}
    if not (in_dungeon_band(base_y) or in_dungeon_band(base_y + chunk_size)):
        return False
    for cx in range(base_x // DUNGEON_CELL_W - 1, (base_x + chunk_size) // DUNGEON_CELL_W + 1):
        for cy in range(base_y // DUNGEON_CELL_H, (base_y + chunk_size) // DUNGEON_CELL_H + 1):
            if (cx, cy) not in cache:
                cache[(cx, cy)] = dungeon_site(cx, cy, base)
            site = cache[(cx, cy)]
            if site is None:
                continue
            if (site.x < base_x + chunk_size and base_x < site.x + site.w and
                    site.y < base_y + chunk_size and base_y < site.y + site.h):
                return True
    return False
