from random import randint

from units.Entity import PhysicalObject, collision_test
from units.Tiles import tile_hand_imgs
from units.common import *

eats = {52: 5, 53: 2, 55: 100}


class Items(PhysicalObject):
    class_obj = OBJ_ITEM
    class_item = CLS_NONE
    width, height = HAND_SIZE, HAND_SIZE
    sprite = pg.Surface((width, height))
    sprite.fill("#FF00FF")

    def __init__(self, game, index=None, count=1, pos=(0, 0)):
        self.index = index
        if index in eats:
            self.class_item = CLS_EAT
            self.recovery_lives = eats[index]
        if type(count) is tuple:
            count = randint(*count)
        self.count = count
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True)

    def __copy__(self):
        obj = self.__class__(self.game, self.index, self.count, self.rect.topleft)
        return obj

    def copy(self):
        return self.__copy__()

    def update(self, tact):
        if not super().update(tact):
            return False
        if self.physical_vector.xy != (0, 0):
            _, dynamic = collision_test(self.game_map, self.rect, {}, self.game.screen_map.dynamic_tiles)
            for obj in dynamic:
                if obj is not self and obj.class_obj == OBJ_ITEM:
                    if obj.alive and self.index == obj.index:
                        self.count += obj.count
                        obj.alive = False


class ItemsTile(Items):
    class_item = CLS_TILE

    def __init__(self, game, index=None, count=1, pos=(0, 0)):
        super().__init__(game, index, count, pos)
        self.sprite = tile_hand_imgs.get(index, self.sprite)

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.sprite = tile_hand_imgs.get(self.index, self.sprite)

