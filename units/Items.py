from units.common import *
from units.Entity import PhiscalObject
from units.Tiles import tile_hand_imgs

CLS_NONE = 0
CLS_TILE = 2
CLS_WEAPON = 4
CLS_PICKAXE = 8


class Items(PhiscalObject):
    class_item = CLS_NONE
    width, height = HAND_SIZE, HAND_SIZE
    sprite = pg.Surface((width, height))
    sprite.fill("#FF00FF")

    def __init__(self, game, type_obj, count=1, pos=(0, 0)):
        self.type_obj = type_obj
        self.count = count
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True)


class ItemsTile(Items):
    def __init__(self, game, type_obj, count=1, pos=(0, 0)):
        super().__init__(game, type_obj, count, pos)
        self.sprite = tile_hand_imgs.get(type_obj, self.sprite)

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.sprite = tile_hand_imgs.get(self.type_obj, self.sprite)
