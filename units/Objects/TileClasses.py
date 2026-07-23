from units.CommandBlock.CommandBlock import CommandBlock
from units.Graphics.Animation import Animation
from units.Inventory import Inventory
from units.Objects import Entities
from units.Objects.Items import Items, ItemsTile
from units.Objects.TileClass import Tile
from units.Tiles import (WOOD_TILES, furnace_imgs, ACTIVATE_TILES, SIGNAL_TILES,
                         lever_on_img, lever_off_img, lamp_on_img, lamp_off_img,
                         chunk_loader_on_img, chunk_loader_off_img)
from units.common import *


class Chest(Tile):
    not_save_vars = {"inventory"} | Tile.not_save_vars
    index = 129
    view_interface_on_click = True
    size_table = Chest_size_table

    def __init__(self, game, tile_pos):
        super(Chest, self).__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)

    def get_vars(self):
        d = super(Chest, self).get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        # tile_pos уже установлен и удлен из списка
        self.inventory.set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

class SignalTile(Tile):
    """Общая база для всех тайлов схемы (активатор/таймер/датчик/провод/
    рычаг/лампа/вентили). activating сбрасывался бы "не вовремя": тайлы
    обновляются в порядке растрового обхода видимых тайлов на кадре, а не
    "сначала все источники, потом все приёмники" — если просто сбрасывать
    activating=False в update() и полагаться, что сосед успеет включить
    заново, результат кадра зависел бы от взаимного расположения тайлов
    (иногда сброс происходил бы уже ПОСЛЕ того, как сосед включил).
    Поэтому вместо "сбросить и понадеяться" храним activated_tact — номер
    такта (self.game.tact), когда тайл последний раз коснулся bfs_activate.
    "Включён" — activated_tact не старше 1 такта: допуск в 1 такт (~16мс,
    незаметно) снимает зависимость от порядка обхода тайлов на кадре."""
    activating = False
    # -inf, а не -1: "-1 >= tact - 1" случайно стало бы True в первые 1-2
    # такта свежего мира (tact == 0 или 1) — сигнальный тайл читался бы как
    # включённый, ни разу не будучи затронут bfs_activate.
    activated_tact = float("-inf")

    def is_active(self):
        return self.activated_tact >= self.game.tact - 1

    def refresh_activating(self):
        self.activating = self.is_active()


def bfs_activate(game_map, origin):
    """Обходит связную сеть активируемых блоков (Activator/TimerBlock/
    PressurePlate/Wire/Lever/Lamp) итеративно (очередь, не рекурсия) — на
    большом скоплении рекурсивный обход уходил вглубь на сотни вложенных
    вызовов и был уязвим к RecursionError; visited по id защищает от
    повторной активации того же блока (циклы/сетки). Общая логика для всех
    источников активации."""
    tact = origin.game.tact
    visited = {origin.id}
    queue = [origin]
    while queue:
        current = queue.pop()
        current.activating = True
        current.activated_tact = tact
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                x, y = current.tx + i, current.ty + j
                tile, tile_obj = game_map.get_tile_and_obj(x, y)
                if tile[0] in ACTIVATE_TILES:
                    if tile_obj:
                        if tile_obj.id not in visited:
                            visited.add(tile_obj.id)
                            queue.append(tile_obj)
                    elif tile[0] == 9:
                        Entities.activate_dynamite(game_map, x, y, tile[0])


def count_active_neighbors(game_map, tile_obj):
    """Считает соседние сигнальные тайлы (провода/рычаги/активаторы/другие
    вентили), которые сейчас включены — основа для вычисления вентилей
    (НЕ/И/ИЛИ). Читает activated_tact соседа напрямую (не is_active(),
    чтобы не требовать от Wire собственного update() только ради этого)."""
    tact = tile_obj.game.tact
    n = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue
            x, y = tile_obj.tx + i, tile_obj.ty + j
            tile, neighbor = game_map.get_tile_and_obj(x, y)
            if tile[0] in SIGNAL_TILES and neighbor is not None and neighbor.activated_tact >= tact - 1:
                n += 1
    return n


class Activator(SignalTile):
    index = 210

    def activate_nearby_tiles(self):
        bfs_activate(self.game_map, self)

    def activate(self):
        if not self.activating:
            self.activate_nearby_tiles()

    def update(self, elapsed_time):
        self.refresh_activating()

    def right_click(self, mouse_local_pos):
        if not self.activating:
            self.activate_nearby_tiles()


class TimerBlock(SignalTile):
    """Таймер: сам, без участия игрока, периодически запускает подключённую
    сеть активаторов — авто-клокер для командных блоков/активаторов/динамита
    (не нужно нажимать вручную каждый раз)."""
    index = 211
    interval = FPS * 3

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.timer = 0

    def update(self, elapsed_time):
        self.refresh_activating()
        self.timer += 1
        if self.timer >= self.interval:
            self.timer = 0
            bfs_activate(self.game_map, self)

    def right_click(self, mouse_local_pos):
        self.timer = 0
        bfs_activate(self.game_map, self)


class PressurePlate(SignalTile):
    """Нажимная плита: запускает подключённую сеть активаторов, пока на ней
    (в её клетке) стоит игрок — датчик присутствия для авто-дверей/ловушек.
    Дожигает сеть КАЖДЫЙ такт, пока игрок стоит (не только на переднем
    фронте) — иначе всё за ней (например лампа) гасло бы через 1 такт,
    хотя игрок всё ещё стоит на плите."""
    index = 212

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.pressed = False

    def update(self, elapsed_time):
        self.refresh_activating()
        self.pressed = self.rect.colliderect(self.game.player.rect)
        if self.pressed:
            bfs_activate(self.game_map, self)


class Wire(SignalTile):
    """Провод — пассивный узел сети: только передаёт сигнал дальше, своего
    поведения нет, поэтому update() не нужен (не входит в
    CLASS_UPDATING_TILES) — activated_tact ему проставляет bfs_activate
    того, кто до него дотянулся."""
    index = 213


class Lever(SignalTile):
    """Рычаг — ручной переключатель с фиксацией: в отличие от нажимной
    плиты не требует, чтобы игрок стоял на месте, включается/выключается
    правым кликом и остаётся в этом состоянии."""
    index = 214

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.on = False

    def update(self, elapsed_time):
        self.refresh_activating()
        if self.on:
            bfs_activate(self.game_map, self)
        return lever_on_img if self.on else lever_off_img

    def right_click(self, mouse_local_pos):
        self.on = not self.on


class Lamp(SignalTile):
    """Лампа — видимый индикатор сигнала: светится, пока сеть перед ней
    активна. Сама тоже сквозной узел (ACTIVATE_TILES) — можно продолжить
    провод дальше через неё."""
    index = 215

    def update(self, elapsed_time):
        self.refresh_activating()
        return lamp_on_img if self.activating else lamp_off_img


class LogicGate(SignalTile):
    """Общая база вентилей (НЕ/И/ИЛИ). В отличие от провода/лампы НЕ входит
    в ACTIVATE_TILES — чужой bfs_activate не должен "затапливать" вентиль
    напрямую, иначе он был бы просто ещё одним проводом. Вместо этого
    вентиль каждый такт сам читает соседей (count_active_neighbors) и, если
    по своей логике должен быть включён, сам становится источником —
    вызывает bfs_activate(self), продолжая сеть дальше."""

    def evaluate(self, active_neighbors: int) -> bool:
        raise NotImplementedError

    def update(self, elapsed_time):
        if self.evaluate(count_active_neighbors(self.game_map, self)):
            bfs_activate(self.game_map, self)
        self.refresh_activating()


class NotGate(LogicGate):
    """НЕ: включён, когда нет ни одного активного соседа. Замкнутый сам на
    себя через провод превращается в автогенератор (мигает раз в 2 такта,
    как и положено вентилю НЕ с обратной связью) — это следствие модели
    с допуском в 1 такт, а не отдельная фича."""
    index = 216

    def evaluate(self, active_neighbors):
        return active_neighbors == 0


class AndGate(LogicGate):
    """И: включён, когда активны минимум 2 соседних сигнальных тайла."""
    index = 217

    def evaluate(self, active_neighbors):
        return active_neighbors >= 2


class OrGate(LogicGate):
    """ИЛИ: включён, когда активен минимум 1 соседний сигнальный тайл."""
    index = 218

    def evaluate(self, active_neighbors):
        return active_neighbors >= 1


class ChunkLoader(SignalTile):
    """Прогрузчик чанка: пока получает сигнал от сети (провод/рычаг/датчик/
    таймер), удерживает от выгрузки чанки в радиусе вокруг себя даже когда
    игрок ушёл далеко (см. GameMap.unload_far_chunks) — держать автоматику
    (фермы триггеров, авто-клокеры) работающей без игрока рядом. Без
    сигнала — обычный чанк, выгружается по общим правилам. Сам является
    узлом сети (ACTIVATE_TILES), сигнал через него можно вести дальше."""
    index = 219
    radius = 2  # в чанках

    def update(self, elapsed_time):
        self.refresh_activating()
        return chunk_loader_on_img if self.activating else chunk_loader_off_img


furnace_burn_tiles = {
    52: 82,
    56: 86,
    401: 81,
    405: 406,  # сырое мясо (новые звери) -> жареное
    21: 61,
    22: 62,
    23: 63,
    24: 64,
    25: 65,
}
fuel_tiles = {idx: 1 for idx in WOOD_TILES}


class Furnace(Tile):
    not_save_vars = Tile.not_save_vars | {"animation"}
    index = 131
    burn_time = FPS
    view_interface_on_click = True

    def __init__(self, game, tile_pos):
        super(Furnace, self).__init__(game, tile_pos)
        self.fuel_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        self.fuel_cell.filter_items = set(fuel_tiles)
        self.input_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        self.result_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        # self.result_cell.flag_not_put_in = True
        self.burning = None
        self.progress = 0
        self.timer = 0
        self.animation = Animation(furnace_imgs[1:], looped=True, fps=30)

    def __start_burning(self):
        self.progress = 0
        self.burning = self.input_cell[0].index
        self.fuel_cell.get_from_inventory(self.fuel_cell[0].index, 1)
        self.timer = 0
        self.animation.start()
        # self.game.add_timer_handler(self.__finish_burning, self.burn_time)

    def __finish_burning(self):
        self.animation.stop()
        # if self.check_cells(fuel_is_getting=True):
        self.result_cell.put_to_inventory(ItemsTile(self.game, furnace_burn_tiles[self.burning], count=1))
        self.input_cell.get_from_inventory(self.input_cell[0].index, 1)
        self.progress = 0
        self.burning = None
        self.check_cells_and_start()

    def check_cells_and_start(self):
        if self.check_cells():
            if self.burning != self.input_cell[0].index:
                self.__start_burning()
        else:
            self.burning = False

    def check_cells(self):
        if self.burning or (self.fuel_cell[0] and self.fuel_cell[0].index in fuel_tiles):
            if self.input_cell[0] and self.input_cell[0].index in furnace_burn_tiles:
                if (self.result_cell[0] and self.result_cell[0].count < Items.cell_size and
                    self.result_cell[0].index == furnace_burn_tiles[self.input_cell[0].index]) or \
                        (not self.result_cell[0]):
                    return True
        return False

    def update(self, elapsed_time):
        if self.burning:
            self.timer += 0.5
            self.progress = self.timer / self.burn_time
            if self.timer >= self.burn_time:
                self.__finish_burning()
            self.animation.update(elapsed_time * 0.5)
            return self.animation.get_frame()

    def items_of_break(self):
        inventories = [self.fuel_cell, self.input_cell, self.result_cell]
        return sum([inv.items_of_break() for inv in inventories], [])


classes = {Chest, Furnace, CommandBlock, Activator, TimerBlock, PressurePlate,
          Wire, Lever, Lamp, NotGate, AndGate, OrGate, ChunkLoader}
tiles_class = {cls.index: cls for cls in classes}
