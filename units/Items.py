from random import randint

from units.Entity import PhysicalObject, collision_test
from units.Tiles import tile_hand_imgs, EATS
from units.common import *


class Items(PhysicalObject):
    class_obj = OBJ_ITEM
    class_item = CLS_NONE
    width, height = HAND_SIZE, HAND_SIZE
    sprite = pg.Surface((width, height))
    sprite.fill("#FF00FF")
    cell_size = 999

    def __init__(self, game, index=None, pos=(0, 0), count: int or tuple = 1):
        self.index = index
        if index in EATS:
            self.class_item = CLS_EAT
            self.recovery_lives = EATS[index]
        if isinstance(count, tuple):
            count = randint(*count)
            if count <= 0:
                self.kill()
        self.count = count
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True)

    def __copy__(self):
        obj = self.__class__(self.game, self.index, self.rect.topleft, self.count)
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
                        #  объеденение в один, двух рядом леж предметов одного типа
                        free_place = self.cell_size - self.count
                        if obj.count > free_place:
                            self.count += free_place
                            obj.count -= free_place
                        else:
                            self.count += obj.count
                            obj.alive = False


class ItemsTile(Items):
    class_item = CLS_TILE

    def __init__(self, game, index=None, pos=(0, 0), count=1):
        super().__init__(game, index, pos, count)
        self.sprite = tile_hand_imgs.get(index, self.sprite)
        self.rect.size = self.sprite.get_size()

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.sprite = tile_hand_imgs.get(self.index, self.sprite)
