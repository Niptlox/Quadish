"""Ведро: набрать воду и вылить её.

Зачем предмет, а не блок. Вода в игре теперь течёт (`units/Map/WaterFlow.py`),
но запустить поток мог только тот, кто копает рядом с водоёмом. Ведро — это
единственный способ ПРИНЕСТИ воду туда, где её нет: залить лаву, наполнить
котёл (`units/Objects/TileClasses.py Cauldron`), сделать себе пруд у базы.

Устройство: два предмета, а не один с полем «полное». Ведро (410) и ведро с
водой (411) — разные индексы, и это осознанно:

* иконку в тулбаре видно сразу, без цифр и подсказок;
* пустое и полное не сливаются в один стак, то есть нельзя случайно потерять
  воду, подобрав пустое ведро;
* обмен идёт через обычный инвентарь (убрать одно, положить другое), поэтому
  никакого особого состояния предмета в сейве не появилось.

Из воды берётся ровно один тайл — тот, по которому щёлкнули. Не «бесконечный
источник»: воды в мире ограниченное количество (объём сохраняется, см.
`WaterFlow`), и ведро не должно быть дыркой в этом правиле.
"""
from pygame import Vector2

from units.Tools.Tools import Tool
from units.Tiles import tile_imgs, WATER_TILE, WATER_LEVELS, water_frame, water_frame_level
from units.common import *

BUCKET_EMPTY = 410
BUCKET_WATER = 411
# Дальше этого ведром не достать. Как у транспорта: действие должно
# происходить там, куда игрок реально показывает.
REACH = 5 * TSIZE


class ToolBucketBase(Tool):
    tool_cls = CLS_COMMON
    speed = 2

    def _target_tile(self, vector_to_mouse):
        """Тайл под курсором в пределах вытянутой руки или None."""
        if self.owner is None:
            return None
        vtm = Vector2(vector_to_mouse)
        if vtm.length() > REACH:
            return None
        pos = Vector2(self.owner.vector) + vtm
        return int(pos.x) // TSIZE, int(pos.y) // TSIZE

    def _swap(self, new_index):
        """Заменить ведро в руке на другое его состояние."""
        inv = self.owner.inventory
        inv.get_from_inventory(self.index, 1)
        from units.Tools import TOOLS
        item = TOOLS[new_index](self.owner.game, pos=self.owner.rect.topleft)
        ok, _ = inv.put_to_inventory(item)
        if not ok:
            # Инвентарь полон — бросаем под ноги, а не теряем предмет.
            gm = self.owner.game_map
            gm.add_dinamic_obj(*gm.to_chunk_xy(self.owner.rect.centerx // TSIZE,
                                               self.owner.rect.centery // TSIZE), item)
        self.owner.choose_active_cell()
        return True


class ToolBucket(ToolBucketBase):
    """Пустое ведро: щелчок по воде набирает её."""
    index = BUCKET_EMPTY
    sprite = tile_imgs[index]

    def right_button_click(self, vector_to_mouse):
        target = self._target_tile(vector_to_mouse)
        if target is None:
            return False
        tx, ty = target
        gm = self.owner.game_map
        tile = gm.get_static_tile(tx, ty, create_chunk=False)
        if tile is None or tile[0] != WATER_TILE:
            return False
        # Черпаем целый тайл, даже если он неполный: ведро — это ведро, а не
        # мензурка. Иначе пришлось бы держать уровень внутри предмета и
        # объяснять игроку, что у него «ведро на три четверти».
        gm.set_static_tile(tx, ty, 0, create_chunk=False)
        return self._swap(BUCKET_WATER)


class ToolBucketWater(ToolBucketBase):
    """Полное ведро: щелчок выливает воду.

    Вылитая вода — обычный тайл воды, поэтому дальше ей занимается поток: она
    сама стечёт вниз и растечётся. Отдельной «пролитой воды» в игре нет.
    """
    index = BUCKET_WATER
    sprite = tile_imgs[index]

    def right_button_click(self, vector_to_mouse):
        target = self._target_tile(vector_to_mouse)
        if target is None:
            return False
        tx, ty = target
        gm = self.owner.game_map
        tile = gm.get_static_tile(tx, ty, create_chunk=False)
        if tile is None:
            return False
        # Наливать можно в пустоту и в неполную воду. В породу — нет: вода не
        # вытесняет блоки (то же правило, что и у потока).
        if tile[0] == WATER_TILE:
            if water_frame_level(tile[2]) >= WATER_LEVELS:
                return False
            gm.set_static_tile(tx, ty, [WATER_TILE, 0, water_frame(WATER_LEVELS), 0],
                               create_chunk=False)
        elif tile[0] == 0:
            gm.set_static_tile(tx, ty, [WATER_TILE, 0, water_frame(WATER_LEVELS), 0],
                               create_chunk=False)
        else:
            return False
        return self._swap(BUCKET_EMPTY)
