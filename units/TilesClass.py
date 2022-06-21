from units.Inventory import Inventory
from units.common import *


class Tile:
    index = 0

    def __init__(self, game, tile_pos):
        self.id = id(self)
        self.game = game
        self.game_map = game.game_map
        self.tx, self.ty = tile_pos
        self.rect = pg.Rect((self.tx * TSIZE, self.ty * TSIZE), (TSIZE, TSIZE))


class Chest(Tile):
    index = 129
    size_table = Chest_size_table

    def __init__(self, game, tile_pos):
        super(Chest, self).__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)

    def get_vars(self):
        d = self.__dict__.copy()
        d.pop("game")
        d.pop("game_map")
        d.pop("inventory")
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        # tile_pos уже установлен и удлен из списка
        self.inventory.set_vars(d)

    def right_click(self, mouse_local_pos):
        self.game.player.chest_ui.set_chest_inventory(self.inventory)
        self.game.player.chest_ui.opened = True

    def items_of_break(self):
        return [(item.index, item.count) for item in self.inventory if item]


