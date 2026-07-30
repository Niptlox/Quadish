"""Удочка: единственное занятие в воде, кроме драки.

Зачем. В воде теперь есть жизнь — рыба, стаи, глубинник, — но единственный
способ с ней взаимодействовать это меч. Рыбалка даёт водоёму мирное занятие и
источник еды, не требующий ни оружия, ни брони: садись у берега и лови.

Устройство. Никакого отдельного экрана и никакой мини-игры: правый клик по воде
ставит поплавок, через несколько секунд клюёт, и добыча падает в воду у
поплавка. Причина — та же, что у всей игры: механика должна читаться без
объяснений и не забирать управление у игрока.

Состояние (где поплавок и когда клюнет) живёт на самом инструменте: удочка
существует ровно пока лежит в инвентаре, и вместе с ней исчезает недоловленная
рыба. Ни в мир, ни в сейв рыбалка ничего не кладёт.
"""
import random

from pygame import Vector2

from units.Tools.Tools import Tool
from units.Tiles import tile_imgs, WATER_TILE, water_frame_level
from units.common import *

ROD_INDEX = 520
# Дальше не забросить: как и у ведра, действие должно происходить там, куда
# игрок реально показывает.
CAST_REACH = 6 * TSIZE
# Сколько ждать поклёвки. Разброс обязателен: постоянное время превращает
# рыбалку в счёт до пяти, а не в ожидание.
BITE_MIN, BITE_MAX = FPS * 3, FPS * 8
# Отпустило дальше этого — леска рвётся. Иначе можно было бы забросить и уйти.
LEASH = 10 * TSIZE

# Что клюёт. Веса, а не проценты: добавить строчку не значит пересчитать
# остальные. Основа — рыба (еда), остальное делает улов не всегда одинаковым.
CATCH_TABLE = [
    (405, (1, 2), 60),   # сырое мясо (рыба)
    (51, (1, 2), 10),    # слизь
    (107, (1, 2), 8),    # камыш
    (12, (1, 1), 8),     # коряга
    (423, (1, 1), 6),    # жгучая слизь
    (66, (1, 1), 4),     # рубин — редкая удача
    (425, (1, 1), 4),    # светящаяся чешуя
]


def roll_catch(rnd=random):
    """Что попалось: (индекс, количество)."""
    total = sum(w for _, _, w in CATCH_TABLE)
    roll = rnd.uniform(0, total)
    for index, count, weight in CATCH_TABLE:
        roll -= weight
        if roll <= 0:
            return index, rnd.randint(*count)
    index, count, _ = CATCH_TABLE[0]
    return index, rnd.randint(*count)


class ToolFishingRod(Tool):
    """Правый клик по воде — забросить; повторный — смотать."""
    tool_cls = CLS_COMMON
    index = ROD_INDEX
    sprite = tile_imgs[index]
    speed = 2

    def __init__(self, owner):
        super().__init__(owner)
        self.float_tile = None      # (tx, ty) поплавка
        self.bite_tact = 0          # такт, на котором клюнет

    # ---------- заброс ----------

    def right_button_click(self, vector_to_mouse):
        if self.owner is None:
            return False
        if self.float_tile is not None:
            self.reel_in()
            return True
        vtm = Vector2(vector_to_mouse)
        if vtm.length() > CAST_REACH:
            return False
        pos = Vector2(self.owner.vector) + vtm
        tx, ty = int(pos.x) // TSIZE, int(pos.y) // TSIZE
        if not self._is_water(tx, ty):
            return False
        self.float_tile = (tx, ty)
        self.bite_tact = self._tact() + random.randint(BITE_MIN, BITE_MAX)
        return True

    def reel_in(self):
        self.float_tile = None
        self.bite_tact = 0

    # ---------- ожидание ----------

    def update(self, vector_to_mouse):
        super().update(vector_to_mouse)
        if self.float_tile is None or self.owner is None:
            return
        tx, ty = self.float_tile
        # Вода могла уйти (её слили или выпил котёл) — тогда ловить негде.
        if not self._is_water(tx, ty):
            self.reel_in()
            return
        # Ушёл далеко — леска рвётся: рыбалка не должна работать в фоне, пока
        # игрок занимается чем-то другим на другом конце карты.
        if (Vector2(self.owner.rect.center) - Vector2(tx * TSIZE, ty * TSIZE)).length() > LEASH:
            self.reel_in()
            return
        if self._tact() >= self.bite_tact:
            self.catch()

    def catch(self):
        tx, ty = self.float_tile
        index, count = roll_catch()
        game_map = self.owner.game_map
        game_map.add_item_of_index(index, count, tx, ty)
        ui = getattr(self.owner.game, "ui", None)
        if ui is not None:
            from units.Tiles import tile_words
            ui.new_sys_message(f"Клюнуло: {tile_words.get(index, index)} x{count}")
        self.reel_in()

    # ---------- мелочи ----------

    def _tact(self):
        return getattr(self.owner.game, "tact", 0)

    def _is_water(self, tx, ty):
        tile = self.owner.game_map.get_static_tile(tx, ty, create_chunk=False)
        if tile is None or tile[0] != WATER_TILE:
            return False
        return water_frame_level(tile[2]) >= WATER_SWIM_LEVEL
