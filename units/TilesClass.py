from units.Inventory import Inventory
from units.common import *


class Chest:
    index = 129
    size_table = Chest_size_table

    def __init__(self, game, pos_real):
        self.game = game
        self.game_map = game.game_map
        self.tx, self.ty = pos_real[0] // TSIZE, pos_real[1] // TSIZE
        self.rect = pg.Rect(pos_real, (TSIZE, TSIZE))
        self.inventory = Inventory(self.game_map, self, self.size_table)

    def right_click(self, mouse_local_pos):
        self.game.player.chest_ui.set_chest_inventory(self.inventory)
        self.game.player.chest_ui.opened = True



