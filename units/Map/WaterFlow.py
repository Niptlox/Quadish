"""Физика воды: перетекание по уровням заполнения.

До этого вода была рельефом. Генератор ставил её ровным зеркалом, и на этом
всё заканчивалось: прокопал дно озера — вода осталась висеть над дырой;
поставил блок воды в воздухе — он там и стоял. Уровни заполнения
(`Tiles.water_frame`) уже были, но менять их было некому.

Устройство — клеточный автомат с **активным множеством**, а не тик каждого
тайла воды. Это главное решение, и оно вынужденное: озеро радиусом 20 — это
несколько сотен тайлов воды, а водоём в равновесии не должен стоить ни одного
такта. Поэтому:

* тикают только «неуспокоенные» клетки (`GameMap.water_flow`);
* клетка, которой некуда течь, из множества **выпадает** и больше не платит;
* обратно её кладёт только изменение по соседству — правка тайла игроком
  (`set_static_tile`) или перетекание в соседней клетке.

Из этого следует то, чего игрок и ждёт: озеро, сгенерированное в равновесии,
не тикает вообще, а прокоп в его дне вызывает поток ровно в том месте, где
копали, и поток затухает сам.

Три правила, каждое со своей причиной:

* **Вниз — всем объёмом.** Вода падает, а не сползает: сползающая вода
  выглядит как желе.
* **В стороны — по одной единице и только если у соседа заметно меньше**
  (`SPREAD_GAP`). Без порога две соседние клетки перекидывают единицу
  туда-обратно вечно и множество никогда не пустеет.
* **Только в воздух и в воду.** Растения, породу и постройки вода не
  вытесняет: вытеснение блока — это разрушение мира потоком, а такого решения
  никто не принимал.
"""
from collections import deque

from units.Tiles import WATER_TILE, WATER_LEVELS, water_frame, water_frame_level, water_frame_deep

AIR = 0

# Сколько клеток обслуживаем за один такт воды и как часто он бывает.
# 4 кадра между тактами — вода течёт заметно, но не мгновенно; 64 клетки —
# граница цены кадра: поток шире этого просто доливается следующим тактом.
WATER_PERIOD = 4
WATER_BUDGET = 64
# Разница уровней, при которой вода ещё растекается в сторону. 2 — минимум,
# при котором нет вечного качания единицы между двумя клетками.
SPREAD_GAP = 2
# Предел активного множества. Нужен на случай, если игрок вскроет дно большого
# озера: поток всё равно пойдёт, просто фронт будет обслуживаться порциями, а
# память не вырастет на весь водоём.
MAX_ACTIVE = 4096


class WaterFlow:
    """Состояние потока для одной карты. Живёт в GameMap, в сейв не идёт."""

    def __init__(self, game_map):
        self.game_map = game_map
        self.queue = deque()
        self.pending = set()

    # ---------- пометки ----------

    def touch(self, tx, ty):
        """Разбудить клетку: у неё что-то изменилось по соседству."""
        if len(self.pending) >= MAX_ACTIVE or (tx, ty) in self.pending:
            return
        self.pending.add((tx, ty))
        self.queue.append((tx, ty))

    def touch_around(self, tx, ty):
        """Разбудить клетку и её соседей — вызывается при правке тайла.

        Соседей тоже: воду разбудить надо не в том тайле, который изменили
        (там теперь дырка), а в тех, откуда в эту дырку потечёт.
        """
        self.touch(tx, ty)
        self.touch(tx, ty - 1)
        self.touch(tx, ty + 1)
        self.touch(tx - 1, ty)
        self.touch(tx + 1, ty)

    # ---------- такт ----------

    def tick(self, tact):
        """Обслужить порцию клеток. Возвращает, сколько из них потекло."""
        if tact % WATER_PERIOD or not self.queue:
            return 0
        moved = 0
        # Пока пишет сам поток, set_static_tile не будит окрестность: поток
        # делает это сам и точнее — иначе каждая перелитая единица воды
        # стоила бы пяти лишних пометок.
        self.game_map._water_writing = True
        try:
            for _ in range(min(WATER_BUDGET, len(self.queue))):
                tx, ty = self.queue.popleft()
                self.pending.discard((tx, ty))
                if self._flow(tx, ty):
                    moved += 1
        finally:
            self.game_map._water_writing = False
        return moved

    # ---------- правила ----------

    def _read(self, tx, ty):
        """(тип, уровень, глубинная) или None, если чанка нет в памяти."""
        tile = self.game_map.get_static_tile(tx, ty, create_chunk=False)
        if tile is None:
            return None
        ttile = tile[0]
        if ttile == WATER_TILE:
            return ttile, water_frame_level(tile[2]), water_frame_deep(tile[2])
        return ttile, 0, False

    def _put(self, tx, ty, level, deep):
        if level <= 0:
            self.game_map.set_static_tile(tx, ty, AIR, create_chunk=False)
        else:
            self.game_map.set_static_tile(
                tx, ty, [WATER_TILE, 0, water_frame(min(WATER_LEVELS, level), deep), 0],
                create_chunk=False)

    def _flow(self, tx, ty):
        """Один шаг для клетки. True — вода сдвинулась."""
        here = self._read(tx, ty)
        if here is None or here[0] != WATER_TILE:
            return False
        _, level, deep = here
        if level <= 0:
            return False

        below = self._read(tx, ty + 1)
        if below is not None:
            if below[0] == AIR:
                # Падение всем объёмом: сползающая вода выглядит как желе.
                self._put(tx, ty + 1, level, deep)
                self._put(tx, ty, 0, deep)
                self._wake(tx, ty)
                self._wake(tx, ty + 1)
                return True
            if below[0] == WATER_TILE and below[1] < WATER_LEVELS:
                room = WATER_LEVELS - below[1]
                give = min(level, room)
                self._put(tx, ty + 1, below[1] + give, below[2])
                self._put(tx, ty, level - give, deep)
                self._wake(tx, ty)
                self._wake(tx, ty + 1)
                return True

        # Вниз некуда — растекаемся в стороны, по одной единице за такт.
        for dx in (-1, 1):
            side = self._read(tx + dx, ty)
            if side is None:
                continue
            if side[0] == AIR and level >= SPREAD_GAP:
                self._put(tx + dx, ty, 1, deep)
                self._put(tx, ty, level - 1, deep)
                self._wake(tx, ty)
                self._wake(tx + dx, ty)
                return True
            if side[0] == WATER_TILE and side[1] <= level - SPREAD_GAP:
                self._put(tx + dx, ty, side[1] + 1, side[2])
                self._put(tx, ty, level - 1, deep)
                self._wake(tx, ty)
                self._wake(tx + dx, ty)
                return True
        return False

    def _wake(self, tx, ty):
        """После сдвига разбудить окрестность: фронт потока идёт дальше."""
        self.touch_around(tx, ty)
