from units.CommandBlock.CommandBlock import CommandBlock
from units.Graphics.Animation import Animation
from units.Inventory import Inventory
from units.Objects import Entities
from units.Objects.Items import Items, ItemsTile
from units.Objects.TileClass import Tile
from units.Tiles import (WOOD_TILES, furnace_imgs, ACTIVATE_TILES, SIGNAL_TILES,
                         lever_on_img, lever_off_img, lamp_on_img, lamp_off_img,
                         chunk_loader_on_img, chunk_loader_off_img,
                         music_block_img, music_block_flash_img,
                         receiver_img, transmitter_img, conveyor_imgs, blore_track_imgs,
                         item_of_break_tile,
                         engine_fuel_on_img, engine_fuel_off_img, engine_creative_img,
                         engine_space_on_img, engine_space_off_img,
                         engine_hell_on_img, engine_hell_off_img,
                         nest_on_img, nest_off_img,
                         dust_collector_on_img, dust_collector_off_img)
from units.sound import note_sound_for_item
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

class Echo(Tile):
    """Отголосок: оставленная в блоровом канале запись, отвечающая один раз.

    Единственный «НПС» в игре, и он намеренно не человек: соплеменников не
    осталось — это несущая часть истории (docs/STORYBOOK.md), и живой
    болтливый спутник отменил бы весь тон брошенного мира одной репликой.

    Отголосок говорит то, что относится к главе, в которой игрок находится
    СЕЙЧАС, и говорит про то, что делали ОНИ, а не что должен делать игрок.
    Направление без приказа.
    """
    index = 239
    view_interface_on_click = True

    def inscription(self):
        from units.Lore import echo_for_act
        from units.Story import current_act
        act = current_act(self.game)
        return echo_for_act(act.id if act is not None else None)

    def right_click(self, mouse_local_pos):
        # Отголосок не отмечается как «прочитанная надпись»: он не запись, а
        # ответ, и в журнал записей ему попадать незачем.
        return True


class Cupboard(Chest):
    """Шкаф: контейнер поменьше сундука.

    До этого шкаф был чистой мебелью — блок без инвентаря. Структуры ставили
    его как обстановку, и открыть его было нельзя. Теперь это контейнер: в
    жилых постройках наполнение логичнее держать в шкафу, а не в сундуке,
    который по игровой логике игрок делает сам.
    """
    index = 126
    # Меньше сундука: шкаф — это находка «по мелочи», а не клад
    size_table = [5, 2]


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
    # Кто зажёг тайл в этот такт. Нужно, чтобы вентиль не считал ВХОДОМ то,
    # что сам же и запитал: сеть связна по восьми соседям и не имеет
    # направления, поэтому вентиль питал собственные входные провода и
    # залипал навсегда — включившись один раз, И и ИЛИ больше не гасли.
    activated_sources = ()
    # id объектов живут только в текущем запуске — в сейв их класть нельзя
    not_save_vars = Tile.not_save_vars | {"activated_sources"}

    def is_active(self):
        return self.activated_tact >= self.game.tact - 1

    def refresh_activating(self):
        self.activating = self.is_active()

    def note_activation(self, tact, source_id):
        if self.activated_tact != tact or not isinstance(self.activated_sources, set):
            self.activated_sources = set()
        self.activated_tact = tact
        self.activating = True
        self.activated_sources.add(source_id)

    def powered_by_other_than(self, tact, owner_id):
        """Активен ли тайл усилиями кого-то, кроме owner_id."""
        if self.activated_tact < tact - 1:
            return False
        sources = self.activated_sources
        if not sources:
            return True          # зажёгся до появления учёта источников
        return any(src != owner_id for src in sources)


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
        current.note_activation(tact, origin.id)
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
            if tile[0] in SIGNAL_TILES and neighbor is not None and \
                    neighbor.powered_by_other_than(tact, tile_obj.id):
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
        self.timer += self.steps
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
    """НЕ: включён, когда нет ни одного активного соседа.

    Собственный выход входом не считается (см. activated_sources в
    SignalTile), поэтому НЕ без внешнего входа просто горит, а не мигает.
    Раньше он в такой схеме работал автогенератором — но это была та же
    самая ошибка самозапитки, из-за которой И и ИЛИ залипали навсегда.
    Ровный клокер даёт таймер (211), для этого он и есть."""
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


class DelayBlock(LogicGate):
    """Задержка сигнала: bfs_activate распространяется мгновенно на весь
    связный участок сети (провода/активаторы не тормозят сигнал по
    расстоянию), поэтому задержку нельзя собрать из уже существующих
    блоков — нужен отдельный узел с собственной памятью. Получив фронт
    сигнала (сосед стал активен), запоминает такт "выстрела" на delay
    тактов вперёд и лишь тогда сам становится источником. Пока сигнал
    держится или пока ждём отложенный выстрел — повторно не планирует
    (один фронт - один отложенный импульс)."""
    index = 220
    delay = FPS  # тактов задержки (~1с при 60 FPS)

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.pending_tact = None
        self._had_input = False

    def evaluate(self, active_neighbors):
        has_input = active_neighbors > 0
        if has_input and not self._had_input:
            self.pending_tact = self.game.tact + self.delay
        self._had_input = has_input
        if self.pending_tact is not None and self.game.tact >= self.pending_tact:
            self.pending_tact = None
            return True
        return False


class ChunkLoader(SignalTile):
    """Прогрузчик чанка: пока получает сигнал от сети (провод/рычаг/датчик/
    таймер), удерживает от выгрузки чанки в радиусе вокруг себя даже когда
    игрок ушёл далеко (см. GameMap.unload_far_chunks) — держать автоматику
    (фермы триггеров, авто-клокеры) работающей без игрока рядом. Без
    сигнала — обычный чанк, выгружается по общим правилам. Сам является
    узлом сети (ACTIVATE_TILES), сигнал через него можно вести дальше."""
    index = 219
    view_interface_on_click = True
    not_save_vars = Tile.not_save_vars | {"inventory"}
    # Без топлива прогрузчик держит только ближайшие чанки — этого хватает,
    # чтобы ферма у базы не вставала, пока игрок рядом копает. Большой
    # радиус — самая сильная способность в игре (мир тикает без игрока), и
    # она должна что-то стоить: космическая пыль.
    BASE_RADIUS = 1
    FUELED_RADIUS = 3
    FUEL_ITEM = 408              # космическая пыль
    FUEL_PERIOD = FPS * 90       # одна пыль на полторы минуты работы

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, [3, 1])
        self.inventory.filter_items = {self.FUEL_ITEM}
        self.timer = 0
        self.fueled = False

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        # Миры, созданные до появления топлива, не содержат ключа
        # "inventory" — грузим их обычным путём, иначе загрузка падала бы
        # на KeyError у каждого старого прогрузчика.
        if "inventory" in d:
            self.inventory.set_vars(d)
        else:
            super().set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

    @property
    def radius(self):
        return self.FUELED_RADIUS if self.fueled else self.BASE_RADIUS

    def take_fuel(self):
        for i, cell in enumerate(self.inventory):
            if cell is not None and cell.index == self.FUEL_ITEM:
                cell.count -= 1
                if cell.count <= 0:
                    self.inventory.set_cell(i, None)
                return True
        return False

    def update(self, elapsed_time):
        self.refresh_activating()
        if not self.activating:
            self.fueled = False
            return chunk_loader_off_img
        self.timer += self.steps
        if self.timer >= self.FUEL_PERIOD or not self.fueled:
            if self.take_fuel():
                self.fueled = True
                self.timer = 0
            elif self.timer >= self.FUEL_PERIOD:
                self.fueled = False
                self.timer = 0
        return chunk_loader_on_img


class MusicBlock(SignalTile):
    """Муз-блок: играет ноту, когда получает сигнал от сети — высота ноты
    зависит от предмета, положенного в единственную ячейку (правый клик,
    как топливо у печки), а не от отдельного счётчика/ползунка. Играет
    один раз на фронт сигнала (переход выкл->вкл), а не на каждый такт,
    пока сигнал держится — иначе вместо ноты был бы жужжащий треск."""
    index = 221
    not_save_vars = Tile.not_save_vars | {"inventory"}
    view_interface_on_click = True

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, [1, 1])
        self._was_active = False

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

    def update(self, elapsed_time):
        self.refresh_activating()
        just_triggered = self.activating and not self._was_active
        if just_triggered:
            item = self.inventory[0]
            note_sound_for_item(item.index if item else None).play()
        self._was_active = self.activating
        return music_block_flash_img if just_triggered else music_block_img


class Receiver(SignalTile):
    """Приёмник рации: цель для Передатчика с такой же 4-предметной
    "частотой" (см. docs/SIGNAL_NETWORK_CONCEPT.md). Сам по себе пассивен —
    обычный узел сети (ACTIVATE_TILES), просто регистрирует себя в
    GameMap.signal_receivers по своей комбинации, чтобы Передатчик находил
    его без перебора всего загруженного мира."""
    index = 222
    view_interface_on_click = True
    not_save_vars = Tile.not_save_vars | {"inventory"}

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self._registered_code = None
        self.inventory = Inventory(self.game_map, self, [2, 2], items_update_event=self._reregister)
        self._reregister()

    def code(self):
        return tuple(sorted(item.index for item in self.inventory.inventory if item))

    def _reregister(self):
        if self._registered_code is not None:
            self.game_map.unregister_receiver(self._registered_code, self)
        self._registered_code = self.code()
        self.game_map.register_receiver(self._registered_code, self)

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        if self._registered_code is not None:
            self.game_map.unregister_receiver(self._registered_code, self)
            self._registered_code = None
        return self.inventory.items_of_break()

    def update(self, elapsed_time):
        self.refresh_activating()
        return receiver_img


class Transmitter(SignalTile):
    """Передатчик рации: пока сам получает сигнал от локальной проводной
    сети (провод/рычаг/активатор рядом), каждый такт ищет все Приёмники с
    такой же 4-предметной "частотой" в радиусе TRANSMITTER_RANGE и держит
    их включёнными — без физического провода между ними. Обычный узел сети
    (ACTIVATE_TILES), локальную сеть после себя тоже продолжает."""
    index = 223
    view_interface_on_click = True
    not_save_vars = Tile.not_save_vars | {"inventory"}
    range = TRANSMITTER_RANGE

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, [2, 2])

    def code(self):
        return tuple(sorted(item.index for item in self.inventory.inventory if item))

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

    def update(self, elapsed_time):
        self.refresh_activating()
        if self.activating:
            self._broadcast()
        return transmitter_img

    def _broadcast(self):
        code = self.code()
        if not code:
            return
        for receiver in tuple(self.game_map.signal_receivers.get(code, ())):
            dx, dy = receiver.tx - self.tx, receiver.ty - self.ty
            if max(abs(dx), abs(dy)) <= self.range:
                bfs_activate(self.game_map, receiver)


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
            self.timer += 0.5 * self.steps
            self.progress = self.timer / self.burn_time
            if self.timer >= self.burn_time:
                self.__finish_burning()
            self.animation.update(elapsed_time * 0.5)
            return self.animation.get_frame()

    def items_of_break(self):
        inventories = [self.fuel_cell, self.input_cell, self.result_cell]
        return sum([inv.items_of_break() for inv in inventories], [])


# Зельеварение: ({ингредиент: сколько, ...}, (что получится, сколько)).
#
# Ингредиентных ячеек три, и рецепт сверяется с их содержимым КАК С НАБОРОМ:
# порядок не важен, лишний ингредиент рецепт не подходит. Порядок был бы
# угадыванием, а «лишнее не мешает» превращало бы котёл в мусорку, куда
# сваливают всё подряд.
#
# Простые рецепты (один ингредиент) остались — с них начинают. Составные дают
# БОЛЬШЕ порций из тех же трав: за возню с тремя ячейками надо платить, но
# платить выгодой, а не обязанностью.
#
# Ингредиенты — это трофеи существ и растения (docs/BALANCE_SCHEME.md): зелье
# оплачивается охотой или походом в биом, а не запасами руды.
CAULDRON_RECIPES = [
    ({53: 6}, (55, 1)),          # ягоды -> зелье жизни
    ({422: 3}, (351, 1)),        # крыло мыши -> зелье нового прыжка
    ({109: 3}, (413, 1)),        # лунный цвет -> скорость
    ({420: 2}, (414, 1)),        # клык -> сила
    ({424: 1}, (415, 1)),        # ядро голема -> каменная кожа
    ({108: 3}, (416, 1)),        # огнецвет -> несгораемость
    ({423: 2}, (417, 1)),        # жгучая слизь -> дыхание
    # Составные: те же зелья, но по две порции и с добавкой из другого мира.
    ({109: 2, 421: 2}, (413, 2)),        # лунный цвет + перо
    ({420: 2, 52: 2}, (414, 2)),         # клык + мясо
    ({108: 2, 402: 2}, (416, 2)),        # огнецвет + сера
    ({423: 2, 107: 2}, (417, 2)),        # жгучая слизь + камыш
    ({53: 4, 111: 2}, (55, 2)),          # ягоды + пещерный гриб
    # Усиленная таблетка: варится, а не собирается руками, и лечит дольше.
    ({412: 2, 51: 2, 53: 4}, (418, 2)),
]
# Ведро с водой (units/Tools/ToolBucket.py) — обязательная часть варки.
BUCKET_WATER_INDEX = 411
BUCKET_EMPTY_INDEX = 410
# Сколько ячеек под ингредиенты
CAULDRON_INPUT_CELLS = 3


def cauldron_ingredients(cells):
    """Что лежит в ячейках ингредиентов: {индекс: количество}."""
    have = {}
    for cell in cells:
        if cell is not None:
            have[cell.index] = have.get(cell.index, 0) + cell.count
    return have


def match_cauldron_recipe(have):
    """Найти рецепт по набору ингредиентов или None.

    Совпадение ТОЧНОЕ по составу: лишний вид ингредиента рецепт не подходит.
    Из двух подошедших берём тот, где ингредиентов больше — иначе составной
    рецепт был бы недостижим (его набор всегда содержит простой)."""
    best = None
    for need, out in CAULDRON_RECIPES:
        if set(need) != set(have):
            continue
        if all(have.get(idx, 0) >= cnt for idx, cnt in need.items()):
            if best is None or len(need) > len(best[0]):
                best = (need, out)
    return best


class Cauldron(Tile):
    """Котёл: топливо + ведро воды + ингредиент -> зелье.

    Раньше котёл был просто «столом с огоньком»: рецепты зелий требовали
    КАСАНИЯ котла (`(125, -1)` в units/creating_items.py), то есть варка ничем
    не отличалась от сборки стула — те же ресурсы, тот же мгновенный крафт.
    Зельеварения как занятия не было.

    Теперь это машина, как печка, и три её ячейки — это три разных походa:
    дрова (лес), вода (водоём, и её надо принести ведром), ингредиент (трофей
    существа или растение своего биома). Варка занимает время и тратит воду:
    ведро остаётся в ячейке, но становится пустым — это самый понятный способ
    показать, что воду израсходовали.
    """
    not_save_vars = Tile.not_save_vars
    index = 125
    brew_time = FPS * 4
    view_interface_on_click = True

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.fuel_cell = Inventory(self.game_map, self, [1, 1],
                                   items_update_event=self.check_cells_and_start)
        self.fuel_cell.filter_items = set(fuel_tiles)
        self.water_cell = Inventory(self.game_map, self, [1, 1],
                                    items_update_event=self.check_cells_and_start)
        self.water_cell.filter_items = {BUCKET_WATER_INDEX, BUCKET_EMPTY_INDEX}
        # Три ячейки ингредиентов одной строкой, а не три отдельных инвентаря:
        # рецепт всё равно смотрит на них как на набор.
        self.input_cell = Inventory(self.game_map, self, [CAULDRON_INPUT_CELLS, 1],
                                    items_update_event=self.check_cells_and_start)
        self.result_cell = Inventory(self.game_map, self, [1, 1],
                                     items_update_event=self.check_cells_and_start)
        self.brewing = None
        self.progress = 0
        self.timer = 0

    # ---------- проверки ----------

    def recipe(self):
        """Рецепт по содержимому ячеек ингредиентов или None."""
        have = cauldron_ingredients(self.input_cell)
        if not have:
            return None
        return match_cauldron_recipe(have)

    def has_water(self):
        item = self.water_cell[0]
        return item is not None and item.index == BUCKET_WATER_INDEX

    def has_fuel(self):
        item = self.fuel_cell[0]
        return item is not None and item.index in fuel_tiles

    def result_fits(self, result_index):
        out = self.result_cell[0]
        return out is None or (out.index == result_index and out.count < Items.cell_size)

    def check_cells(self):
        rec = self.recipe()
        if rec is None:
            return False
        return self.has_fuel() and self.has_water() and self.result_fits(rec[1][0])

    def check_cells_and_start(self):
        if self.check_cells():
            if self.brewing is None:
                self.__start()
        elif self.brewing is not None:
            # Забрали воду, топливо или ингредиент — варка отменяется, и
            # прогресс сбрасывается. Иначе можно было бы «долить» котёл в
            # последний момент и получить зелье бесплатно.
            self.brewing = None
            self.timer = 0
            self.progress = 0

    # ---------- варка ----------

    def __start(self):
        self.brewing = self.recipe()
        self.timer = 0
        self.progress = 0

    def __finish(self):
        rec = self.recipe()
        self.brewing = None
        self.timer = 0
        self.progress = 0
        if rec is None:
            return
        need, (result_index, result_count) = rec
        for index, count in need.items():
            self.input_cell.get_from_inventory(index, count)
        self.fuel_cell.get_from_inventory(self.fuel_cell[0].index, 1)
        # Вода израсходована: ведро в ячейке пустеет.
        self.water_cell.get_from_inventory(BUCKET_WATER_INDEX, 1)
        from units.Tools import TOOLS
        self.water_cell.put_to_inventory(TOOLS[BUCKET_EMPTY_INDEX](self.game, pos=self.rect.topleft))
        self.result_cell.put_to_inventory(ItemsTile(self.game, result_index, count=result_count))
        # Сюжет отмечает первую сваренную порцию (units/Story.py, акт V):
        # отметка по факту события мира, а не по нажатию в интерфейсе.
        from units.Story import note_flag
        note_flag(self.game, "brewed")
        self.check_cells_and_start()

    def update(self, elapsed_time):
        if self.brewing is None:
            return
        if not self.check_cells():
            self.brewing = None
            self.timer = 0
            self.progress = 0
            return
        self.timer += self.steps
        self.progress = min(1.0, self.timer / self.brew_time)
        if self.timer >= self.brew_time:
            self.__finish()

    def items_of_break(self):
        inventories = [self.fuel_cell, self.water_cell, self.input_cell, self.result_cell]
        return sum([inv.items_of_break() for inv in inventories], [])


# Домашнее хозяйство. Кто что даёт, если его кормить: вид -> (предмет, период).
# Вид, а не класс: то же правило, что у охоты (hunts) — мод-корова со species
# "cow" должна доиться без правок здесь.
LIVESTOCK_PRODUCTS = {
    "cow": (426, FPS * 90),        # молоко
    "rabbit": (428, FPS * 120),    # пух
    "penguin": (427, FPS * 120),   # яйцо
    "deer": (404, FPS * 150),      # шкура (линька)
}
# Чем кормят. Ягоды и трава — то, что и так собирают по дороге.
TROUGH_FOOD = {53, 104, 405, 107}


class Trough(Tile):
    """Кормушка: превращает диких травоядных в домашних.

    Зачем это, а не «приручение с руки». Хозяйство — это МЕСТО, а не список
    ручных зверей: игрок ставит кормушку, кладёт в неё еду, и рядом заводится
    стадо, которое там и живёт. Из этого само собой получается загон, и его не
    надо объяснять.

    Кормушка ест еду и раздаёт её по одному существу за раз, а не «кормит всех
    бесплатно»: иначе хозяйство было бы бесконечным источником еды из ничего.
    """
    index = 113
    view_interface_on_click = True
    FEED_PERIOD = FPS * 5          # как часто проверяет, кого покормить
    FEED_RADIUS = 8                # тайлов вокруг
    TAMED_TACTS = FPS * 300        # сколько существо помнит кормушку

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, [1, 1])
        self.inventory.filter_items = set(TROUGH_FOOD)
        self.timer = 0

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        return [(self.index, 1)] + self.inventory.items_of_break()

    def food(self):
        item = self.inventory[0]
        return item if item is not None and item.index in TROUGH_FOOD else None

    def nearby_livestock(self):
        """Травоядные вокруг кормушки — те, кого вообще можно держать."""
        cxy = self.game_map.to_chunk_xy(self.tx, self.ty)
        out = []
        for dx in (-1, 0, 1):
            chunk = self.game_map.game_map.get((cxy[0] + dx, cxy[1]))
            if chunk is None:
                continue
            for obj in chunk[1]:
                if not (obj.alive and obj.class_obj & OBJ_CREATURE):
                    continue
                if getattr(obj, "bio_species", None) not in LIVESTOCK_PRODUCTS:
                    continue
                if abs(obj.rect.centerx // TSIZE - self.tx) <= self.FEED_RADIUS and \
                        abs(obj.rect.centery // TSIZE - self.ty) <= self.FEED_RADIUS:
                    out.append(obj)
        return out

    def update(self, elapsed_time):
        self.timer += self.steps
        if self.timer < self.FEED_PERIOD:
            return
        self.timer = 0
        tact = self.game.tact
        for animal in self.nearby_livestock():
            product, period = LIVESTOCK_PRODUCTS[animal.bio_species]
            fed_until = getattr(animal, "fed_until", 0)
            if fed_until <= tact:
                food = self.food()
                if food is None:
                    continue
                self.inventory.get_from_inventory(food.index, 1)
                animal.fed_until = tact + self.TAMED_TACTS
                animal.home = (self.tx, self.ty)
                animal.tamed = True
                continue
            # Сытое животное даёт продукт — но не чаще своего периода.
            if tact - getattr(animal, "produced_tact", 0) >= period:
                animal.produced_tact = tact
                self.game_map.add_item_of_index(product, 1,
                                                animal.rect.centerx // TSIZE,
                                                animal.rect.centery // TSIZE)


class LoreTablet(Tile):
    """Плита с надписью — основной канал подачи сюжета (docs/STORY.md).

    В мире хранится только номер варианта надписи (кадр тайла), сам текст
    лежит в units/Lore.py. Поэтому сохранения не распухают от текста, а
    тексты можно править и переводить, не ломая старые миры.
    """
    index = 300
    view_interface_on_click = True

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        # Кадр читаем лениво, а не здесь: set_static_tile создаёт объект
        # тайла ДО того, как запишет его данные в чанк, так что в момент
        # __init__ вариант ещё не виден.
        self._variant = None

    @property
    def variant(self):
        if self._variant is None:
            tile = self.game_map.get_static_tile(self.tx, self.ty)
            self._variant = tile[2] if tile else 0
        return self._variant

    def inscription_id(self):
        from units.Lore import inscription_by_variant
        return inscription_by_variant(self.variant)

    def inscription(self):
        from units.Lore import get_inscription
        return get_inscription(self.inscription_id())

    def right_click(self, mouse_local_pos):
        # отметить прочитанным до открытия интерфейса: журнал должен
        # пополниться даже если игрок сразу закроет окно
        self.game_map.mark_inscription_read(self.inscription_id())
        super().right_click(mouse_local_pos)


class ItemMover(Tile):
    """Общая часть блоков логистики: поиск лежащих предметов и передача в
    соседние контейнеры.

    Предметы в мире — динамические объекты в чанке (chunk[1]), поэтому
    искать их приходится по чанку, а не по тайлам.
    """
    # тайлы, в которые можно класть предметы
    CONTAINER_TILES = {129, 131, 224, 226}

    def items_in_tile(self, tx, ty):
        """Лежащие предметы, попадающие в тайл (tx, ty)."""
        chunk = self.game_map.chunk(self.game_map.to_chunk_xy(tx, ty))
        if not chunk:
            return []
        rect = pg.Rect(tx * TSIZE, ty * TSIZE, TSIZE, TSIZE)
        return [o for o in chunk[1]
                if o.class_obj & OBJ_ITEM and o.alive and rect.colliderect(o.rect)]

    def container_at(self, tx, ty):
        """Инвентарь соседнего контейнера или None."""
        tile = self.game_map.get_static_tile(tx, ty)
        if not tile or tile[0] not in self.CONTAINER_TILES:
            return None
        obj = self.game_map.get_tile_obj(*self.game_map.to_chunk_xy(tx, ty), tile[3])
        return getattr(obj, "inventory", None)

    def take_item_from_world(self, item):
        """Убрать подобранный предмет из мира."""
        self.game_map.del_dinamic_obj(*self.game_map.to_chunk_xy(item.rect.x // TSIZE,
                                                                 item.rect.y // TSIZE), item)
        item.kill()


class Hopper(ItemMover):
    """Воронка: подбирает лежащие сверху предметы и отдаёт их в контейнер
    снизу. Пассивна — сигнал не нужен, иначе простейшая ферма требовала бы
    электросети ещё до того, как игрок её изучит."""
    not_save_vars = {"inventory"} | Tile.not_save_vars
    index = 224
    view_interface_on_click = True
    size_table = [3, 1]
    PERIOD = FPS // 2      # как часто подбирать/передавать

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.timer = 0
        self.inventory = Inventory(self.game_map, self, self.size_table)

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        # Сам блок уже кладёт item_of_break_tile (units/Tiles.py) — здесь
        # только содержимое, иначе блок выпадал бы дважды.
        return self.inventory.items_of_break()

    def update(self, elapsed_time):
        # Свой счётчик, а не сверка с ГЛОБАЛЬНЫМ тактом: иначе выработка за
        # экраном зависит от НОК периода блока и периода тика — замер давал
        # втрое меньше при периоде тика 31 вместо 30 (см. Tile.tick).
        self.timer += self.steps
        if self.timer < self.PERIOD:
            return
        self.timer = 0
        # 1) подобрать всё, что лежит в самой воронке и на тайле над ней
        for ty in (self.ty, self.ty - 1):
            for item in self.items_in_tile(self.tx, ty):
                ok, _left = self.inventory.put_to_inventory(item)
                if ok:
                    self.take_item_from_world(item)
        # 2) отдать один предмет вниз
        target = self.container_at(self.tx, self.ty + 1)
        if target is not None:
            for i, cell in enumerate(self.inventory):
                if cell is not None:
                    one = cell.copy()
                    one.count = 1
                    ok, _left = target.put_to_inventory(one)
                    if ok:
                        cell.count -= 1
                        if cell.count <= 0:
                            self.inventory.set_cell(i, None)
                    break


class Conveyor(ItemMover):
    """Конвейер: толкает лежащие на нём предметы вбок. Направление
    переключается правым кликом (кадр тайла), чтобы не плодить два блока."""
    index = 225
    PERIOD = max(1, FPS // 10)
    PUSH = max(2, TSIZE // 8)

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.timer = 0

    def direction(self):
        tile = self.game_map.get_static_tile(self.tx, self.ty)
        return -1 if (tile and tile[2]) else 1

    def right_click(self, mouse_local_pos):
        tile = self.game_map.get_static_tile(self.tx, self.ty)
        if tile:
            self.game_map.set_static_tile_state_img(self.tx, self.ty, 0 if tile[2] else 1)

    def update(self, elapsed_time):
        self.timer += self.steps
        if self.timer < self.PERIOD:
            return conveyor_imgs[0 if self.direction() > 0 else 1]
        self.timer = 0
        dx = self.direction() * self.PUSH
        # предметы едут по ВЕРХУ конвейера, поэтому смотрим тайл над собой
        for item in self.items_in_tile(self.tx, self.ty - 1):
            item.rect.x += dx
        return conveyor_imgs[0 if self.direction() > 0 else 1]


class Dropper(SignalTile, ItemMover):
    """Дропер: по сигналу выбрасывает один предмет из себя в мир.

    В отличие от воронки — активный: нужен именно как исполнительный
    механизм в схеме (выдать корм, семена, камень в гнездо)."""
    not_save_vars = {"inventory"} | Tile.not_save_vars
    index = 226
    view_interface_on_click = True
    size_table = [3, 1]

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)
        self._was_active = False

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        # Сам блок уже кладёт item_of_break_tile (units/Tiles.py) — здесь
        # только содержимое, иначе блок выпадал бы дважды.
        return self.inventory.items_of_break()

    def drop_one(self):
        for i, cell in enumerate(self.inventory):
            if cell is None:
                continue
            self.game_map.add_item_of_index(cell.index, 1, self.tx, self.ty - 1)
            cell.count -= 1
            if cell.count <= 0:
                self.inventory.set_cell(i, None)
            return True
        return False

    def update(self, elapsed_time):
        self.refresh_activating()
        # только по фронту сигнала: иначе дропер вывалил бы весь запас за
        # секунду, пока рычаг включён
        if self.activating and not self._was_active:
            self.drop_one()
        self._was_active = self.activating


class Chopper(SignalTile):
    """Лесоруб: по сигналу срубает дерево над собой.

    Главный блок фермы дерева (docs/FARMS_CONCEPT.md): таймер + лесоруб +
    воронка = дрова без участия игрока."""
    index = 227
    REACH = 6      # насколько высоко достаёт по стволу

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self._was_active = False

    def chop(self):
        """Срубить ствол над собой; возвращает, сколько блоков срублено."""
        cut = 0
        for dy in range(1, self.REACH + 1):
            ty = self.ty - dy
            ttile = self.game_map.get_static_tile_type(self.tx, ty, default=0)
            if ttile in WOOD_TILES or ttile == 105:   # ствол/листва
                items = item_of_break_tile(self.game_map.get_static_tile(self.tx, ty),
                                           self.game_map, (self.tx, ty))
                self.game_map.set_static_tile(self.tx, ty, 0)
                for idx, cnt in items:
                    self.game_map.add_item_of_index(idx, cnt, self.tx, ty)
                cut += 1
            elif ttile != 0:
                break
        return cut

    def update(self, elapsed_time):
        self.refresh_activating()
        if self.activating and not self._was_active:
            self.chop()
        self._was_active = self.activating


class Engine(SignalTile):
    """Двигатель — источник сигнала, работающий на топливе.

    Отличие от таймера: таймер бесплатен, но медленный (раз в 3 с). Чтобы
    автоматика работала быстро, нужен двигатель, а он ест топливо — так у
    скорости появляется цена, и фермы не становятся бесплатными.
    """
    not_save_vars = {"inventory"} | Tile.not_save_vars
    view_interface_on_click = True
    size_table = [3, 1]
    period = FPS               # тактов между импульсами
    pulses_per_fuel = 8        # сколько импульсов даёт одна единица топлива
    fuel_items = ()            # что принимает как топливо (пусто = не нужно)
    img_on = img_off = None

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)
        if self.fuel_items:
            self.inventory.filter_items = set(self.fuel_items)
        self.timer = 0
        self.charge = 0        # оставшиеся импульсы от сожжённого топлива

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        # Сам блок уже кладёт item_of_break_tile (units/Tiles.py) — здесь
        # только содержимое, иначе блок выпадал бы дважды.
        return self.inventory.items_of_break()

    def take_fuel(self):
        """Сжечь единицу топлива. True, если получилось."""
        if not self.fuel_items:
            return True                      # креативному топливо не нужно
        for i, cell in enumerate(self.inventory):
            if cell is not None and cell.index in self.fuel_items:
                cell.count -= 1
                if cell.count <= 0:
                    self.inventory.set_cell(i, None)
                return True
        return False

    def update(self, elapsed_time):
        self.refresh_activating()
        self.timer += self.steps
        if self.timer < self.period:
            return self.img_on if self.charge > 0 else self.img_off
        self.timer = 0
        if self.charge <= 0:
            if not self.take_fuel():
                return self.img_off
            self.charge = self.pulses_per_fuel
        self.charge -= 1
        bfs_activate(self.game_map, self)
        return self.img_on


class FuelEngine(Engine):
    """Топливный двигатель: работает на дереве, как печка."""
    index = 228
    period = FPS
    pulses_per_fuel = 8
    fuel_items = tuple(WOOD_TILES)

    @property
    def img_on(self):
        return engine_fuel_on_img

    @property
    def img_off(self):
        return engine_fuel_off_img


class CreativeEngine(Engine):
    """Креативный двигатель: без топлива и самый быстрый. Для отладки схем
    и творческого режима — крафта у него нет."""
    index = 229
    period = max(1, FPS // 5)
    fuel_items = ()

    @property
    def img_on(self):
        return engine_creative_img

    @property
    def img_off(self):
        return engine_creative_img


class SpaceEngine(Engine):
    """Космический двигатель: топливо — космическая пыль. Пыль редкая,
    поэтому одной единицы хватает надолго."""
    index = 230
    period = max(1, int(FPS * 0.4))
    pulses_per_fuel = 20
    fuel_items = (408,)

    @property
    def img_on(self):
        return engine_space_on_img

    @property
    def img_off(self):
        return engine_space_off_img


class HellEngine(Engine):
    """Адский двигатель: топливо — сера. Самый быстрый из топливных, но
    сера добывается только в аду."""
    index = 231
    period = max(1, FPS // 4)
    pulses_per_fuel = 12
    fuel_items = (402,)

    @property
    def img_on(self):
        return engine_hell_on_img

    @property
    def img_off(self):
        return engine_hell_off_img


class Portal(SignalTile):
    """Портал: связывает два места по «частоте» — набору предметов внутри,
    ровно как рация. Мир огромен по горизонтали, а ад и космос лежат за
    тысячами блоков по вертикали: без переноса туда просто не дойти.

    Пара ищется по индексу в GameMap.portals (тот же приём, что и у
    приёмников рации), а не перебором загруженного мира.
    """
    not_save_vars = Tile.not_save_vars | {"inventory"}
    index = 232
    view_interface_on_click = True
    # Иначе портал-пара мгновенно перекидывала бы игрока обратно: он
    # появляется внутри второго портала и сразу снова его касается.
    COOLDOWN = FPS * 2

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self._registered_code = None
        self._last_use = float("-inf")
        self.inventory = Inventory(self.game_map, self, [2, 2],
                                   items_update_event=self._reregister)
        self._reregister()

    def code(self):
        return tuple(sorted(item.index for item in self.inventory.inventory if item))

    def _reregister(self):
        if self._registered_code is not None:
            self.game_map.unregister_portal(self._registered_code, self)
        self._registered_code = self.code()
        self.game_map.register_portal(self._registered_code, self)

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)
        self._reregister()

    def items_of_break(self):
        if self._registered_code is not None:
            self.game_map.unregister_portal(self._registered_code, self)
            self._registered_code = None
        # Сам блок уже кладёт item_of_break_tile (units/Tiles.py) — здесь
        # только содержимое, иначе блок выпадал бы дважды.
        return self.inventory.items_of_break()

    def pair(self):
        """Другой портал с той же частотой (первый попавшийся).

        Пустая частота парой не считается: иначе два только что
        поставленных пустых портала уже связывали бы друг друга, и игрока
        кидало бы туда, куда он не собирался.
        """
        code = self.code()
        if not code:
            return None
        for other in self.game_map.portals.get(code, ()):
            if other is not self:
                return other
        return None

    def update(self, elapsed_time):
        self.refresh_activating()
        if self.game.tact - self._last_use < self.COOLDOWN:
            return
        if not self.rect.colliderect(self.game.player.rect):
            return
        other = self.pair()
        if other is None:
            return
        # Отметку ставим обоим: иначе портал назначения тут же сработает
        # сам и отправит игрока обратно.
        self._last_use = other._last_use = self.game.tact
        self.game.player.tp_to((other.tx * TSIZE, other.ty * TSIZE))


class GolemNest(SignalTile):
    """Гнездо голема — ферма железа (docs/FARMS_CONCEPT.md).

    Кладёшь камень, гнездо под сигналом греется и выпускает каменного
    голема: планета возвращает камень и немного железа. Железо тут —
    «проценты» с тепла, а не подарок: тратятся камень, топливо и время, а
    голема ещё надо убить.
    """
    not_save_vars = {"inventory"} | Tile.not_save_vars
    index = 233
    view_interface_on_click = True
    size_table = [3, 1]
    STONE = 3
    STONE_PER_GOLEM = 8
    HEAT_TACTS = FPS * 90     # сколько греться до появления голема
    MAX_NEARBY = 2            # больше двух голенов рядом не плодим

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)
        self.inventory.filter_items = {self.STONE}
        self.heat = 0

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        # Сам блок уже кладёт item_of_break_tile (units/Tiles.py) — здесь
        # только содержимое, иначе блок выпадал бы дважды.
        return self.inventory.items_of_break()

    def stone_count(self):
        return sum(c.count for c in self.inventory if c is not None and c.index == self.STONE)

    def take_stone(self):
        left = self.STONE_PER_GOLEM
        for i, cell in enumerate(self.inventory):
            if cell is None or cell.index != self.STONE:
                continue
            take = min(cell.count, left)
            cell.count -= take
            left -= take
            if cell.count <= 0:
                self.inventory.set_cell(i, None)
            if left <= 0:
                return True
        return left <= 0

    def golems_nearby(self):
        chunk = self.game_map.chunk(self.game_map.to_chunk_xy(self.tx, self.ty))
        if not chunk:
            return 0
        from units.Objects.Creatures import StoneGolem
        return sum(1 for o in chunk[1] if isinstance(o, StoneGolem) and o.alive)

    def spawn_golem(self):
        from units.Objects.Creatures import StoneGolem
        golem = StoneGolem(self.game, ((self.tx) * TSIZE, (self.ty - 2) * TSIZE))
        self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(self.tx, self.ty - 2), golem)
        return golem

    def update(self, elapsed_time):
        self.refresh_activating()
        if not self.activating:
            return nest_off_img
        if self.stone_count() < self.STONE_PER_GOLEM:
            return nest_off_img
        if self.golems_nearby() >= self.MAX_NEARBY:
            return nest_on_img
        self.heat += self.steps
        if self.heat >= self.HEAT_TACTS:
            self.heat = 0
            if self.take_stone():
                self.spawn_golem()
        return nest_on_img


class DustCollector(SignalTile):
    """Пылеуловитель — ферма космической пыли (docs/SPACE.md).

    Работает только в вакууме: тайл должен быть выше границы космоса, и
    вокруг него должно быть пусто. Это и есть механика фермы — не «поставил
    и ушёл», а «построй в космосе разрежённую сетку парусов»: заложишь
    сеть блоками — она перестанет ловить.
    """
    not_save_vars = Tile.not_save_vars | {"inventory"}
    index = 235
    view_interface_on_click = True
    size_table = [3, 1]
    PERIOD = FPS * 30          # такт сбора
    OPEN_NEEDED = 6            # сколько из 8 соседей должно быть вакуумом
    DUST_ITEM = 408

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)
        self.timer = 0

    def get_vars(self):
        d = super().get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        self.inventory.set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

    def open_neighbors(self):
        """Сколько соседних тайлов — вакуум."""
        n = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                if self.game_map.get_static_tile_type(self.tx + i, self.ty + j,
                                                      default=0, create_chunk=False) == 0:
                    n += 1
        return n

    def works(self):
        return self.ty < START_SPACE_Y and self.open_neighbors() >= self.OPEN_NEEDED

    def update(self, elapsed_time):
        self.refresh_activating()
        if not self.activating or not self.works():
            self.timer = 0
            return dust_collector_off_img
        self.timer += self.steps
        if self.timer >= self.PERIOD:
            self.timer = 0
            self.inventory.put_to_inventory(ItemsTile(self.game, self.DUST_ITEM, count=1))
        return dust_collector_on_img


class BloreTrack(ItemMover):
    """Блоровая дорожка: горизонталь для игрока и для лежащих предметов.

    Одна идея на весь транспорт: блор — вещество перемещения (docs/STORY.md),
    и он несёт всё, что в нём стоит. Поэтому дорожка не «рельс отдельно,
    конвейер отдельно», а один блок: игрока разгоняет Player.update_physics
    (по типу тайла, как у блоровых столбов), предметы двигает этот класс.

    Направление переключается правым кликом — так же, как у конвейера, чтобы
    не заводить два блока на одно и то же и не изобретать второй жест.
    """
    index = 238
    PERIOD = max(1, FPS // 10)
    PUSH = max(2, TSIZE // 6)      # предметы чуть быстрее, чем на конвейере

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.timer = 0

    def direction(self):
        tile = self.game_map.get_static_tile(self.tx, self.ty)
        return -1 if (tile and tile[2]) else 1

    def right_click(self, mouse_local_pos):
        tile = self.game_map.get_static_tile(self.tx, self.ty)
        if tile:
            self.game_map.set_static_tile_state_img(self.tx, self.ty, 0 if tile[2] else 1)

    def update(self, elapsed_time):
        self.timer += self.steps
        if self.timer < self.PERIOD:
            return blore_track_imgs[0 if self.direction() > 0 else 1]
        self.timer = 0
        dx = self.direction() * self.PUSH
        # предметы едут по ВЕРХУ дорожки — как и на конвейере
        for item in self.items_in_tile(self.tx, self.ty - 1):
            item.rect.x += dx
        return blore_track_imgs[0 if self.direction() > 0 else 1]


classes = {Chest, Furnace, CommandBlock, Activator, TimerBlock, PressurePlate,
          Wire, Lever, Lamp, NotGate, AndGate, OrGate, DelayBlock, ChunkLoader, MusicBlock,
          Receiver, Transmitter, LoreTablet,
          Hopper, Conveyor, Dropper, Chopper,
          FuelEngine, CreativeEngine, SpaceEngine, HellEngine, Portal, GolemNest,
          DustCollector, BloreTrack, Cupboard, Echo, Cauldron, Trough}
tiles_class = {cls.index: cls for cls in classes}
