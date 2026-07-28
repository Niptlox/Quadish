"""Предметы транспортных средств: правый клик ставит средство в мир.

Средство — сущность, а не блок, поэтому его нельзя «положить» обычной
установкой тайла. Инструмент здесь — самый дешёвый способ дать предмету
своё действие: тот же приём уже использован призывателем босса
(ToolsSummoner). Один базовый класс на все средства, наследники отличаются
только индексом и классом средства — добавить шестое будет четыре строки.
"""
from units.Objects.Vehicles import Raft, AirBoat, MineCrawler, LavaBarge, VoidSkiff
from pygame import Vector2

from units.Tools.Tools import Tool
from units.Tiles import tile_imgs
from units.common import *


class ToolVehicle(Tool):
    """Поставить средство перед игроком и убрать предмет из инвентаря."""
    tool_cls = CLS_COMMON
    speed = 2
    vehicleCls = None
    # Дальше этого не ставим: средство должно появляться там, куда игрок
    # реально показывает, а не за стеной на другом конце экрана.
    place_distance = 4 * TSIZE

    def right_button_click(self, vector_to_mouse: Vector2):
        if self.owner is None or self.vehicleCls is None:
            return False
        vtm = Vector2(vector_to_mouse)
        if vtm.length() > self.place_distance:
            vtm = vtm.normalize() * self.place_distance
        pos = Vector2(self.owner.vector) + vtm
        game_map = self.owner.game_map
        vehicle = self.vehicleCls(self.owner.game, (pos.x, pos.y))
        game_map.add_dinamic_obj(*game_map.to_chunk_xy(int(pos.x) // TSIZE, int(pos.y) // TSIZE),
                                 vehicle)
        # Предмет тратится: средство теперь живёт в мире и разбирается обратно
        # ударом по нему (Vehicle.kill возвращает предмет).
        self.owner.inventory.get_from_inventory(self.index, 1)
        return True


class ToolRaft(ToolVehicle):
    index = 611
    sprite = tile_imgs[index]
    vehicleCls = Raft


class ToolAirBoat(ToolVehicle):
    index = 612
    sprite = tile_imgs[index]
    vehicleCls = AirBoat


class ToolMineCrawler(ToolVehicle):
    index = 613
    sprite = tile_imgs[index]
    vehicleCls = MineCrawler


class ToolLavaBarge(ToolVehicle):
    index = 614
    sprite = tile_imgs[index]
    vehicleCls = LavaBarge


class ToolVoidSkiff(ToolVehicle):
    index = 615
    sprite = tile_imgs[index]
    vehicleCls = VoidSkiff
