from random import randint

from units.Objects.Entity import PhysicalObject, collision_test
from units.Tiles import tile_hand_imgs, Eats, tile_imgs
from units.common import *


class Items(PhysicalObject):
    class_obj = OBJ_ITEM
    class_item = CLS_NONE
    width, height = HAND_SIZE, HAND_SIZE
    sprite = pg.Surface((width, height))
    sprite.fill("#FF00FF")
    cell_size = 999

    def __init__(self, game, index=None, pos=(0, 0), count: int or tuple = 1):
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True)
        self.index = index

        if index in Eats:
            self.class_item = CLS_EAT
            self.recovery_lives = Eats[index]
        if isinstance(count, tuple):
            count = randint(*count)
        if count <= 0:
            self.kill()
        self.count = count

    def __copy__(self):
        obj = self.__class__(self.game, self.index, self.rect.topleft, self.count)
        return obj

    def copy(self):
        return self.__copy__()

    def update(self, tact, elapsed_time):
        if not super().update(tact, elapsed_time):
            return False
        if self.physical_vector.xy != (0, 0):
            _, dynamic = collision_test(self.game_map, self.rect, {}, self.game.screen_map.dynamic_tiles)
            for obj in dynamic:
                # проверка объекта и если он такой же то сложение в один
                self.add(obj)

    def add(self, other):
        if isinstance(other, Items) and self.index == other.index and other is not self:
            last = self.cell_size - self.count
            self.count = min(self.count + other.count, self.cell_size)
            other.count -= last
            if other.count <= 0:
                other.count = 0
                other.alive = False
            return self
        return

    def __iadd__(self, other):
        self.add(other)


class ItemsTile(Items):
    class_item = CLS_TILE

    def __init__(self, game, index=None, pos=(0, 0), count=1):
        super().__init__(game, index, pos, count)
        self.sprite = tile_hand_imgs.get(index, self.sprite)
        self.full_sprite = tile_imgs.get(index, self.sprite)
        self.rect.size = self.sprite.get_size()

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.sprite = tile_hand_imgs.get(self.index, self.sprite)
