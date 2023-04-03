from units.common import *


class Tile(SavedObject):
    not_save_vars = {"game", "game_map"} | SavedObject.not_save_vars
    index = 0
    view_interface_on_click = False

    def __init__(self, game, tile_pos):
        self.id = id(self)
        self.game = game
        self.game_map = game.game_map
        self.tx, self.ty = tile_pos
        self.rect = pg.Rect((self.tx * TSIZE, self.ty * TSIZE), (TSIZE, TSIZE))

    def items_of_break(self):
        return [(self.index, 1)]

    def update(self, elapsed_time):
        pass

    def right_click(self, mouse_local_pos):
        if self.view_interface_on_click:
            self.game.blocks_ui_manager.set_block(self)
