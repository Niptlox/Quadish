from units.CommandBlock.CommandBlock import CommandBlock
from units.Graphics.Animation import Animation
from units.Inventory import Inventory
from units.Objects import Entities
from units.Objects.Items import Items, ItemsTile
from units.Objects.TileClass import Tile
from units.Tiles import WOOD_TILES, furnace_imgs, ACTIVATE_TILES
from units.common import *


class Chest(Tile):
    not_save_vars = {"inventory"} | Tile.not_save_vars
    index = 129
    view_interface_on_click = True
    size_table = Chest_size_table

    def __init__(self, game, tile_pos):
        super(Chest, self).__init__(game, tile_pos)
        self.inventory = Inventory(self.game_map, self, self.size_table)

    def get_vars(self):
        d = super(Chest, self).get_vars()
        d.update(self.inventory.get_vars())
        return d

    def set_vars(self, d):
        # tile_pos уже установлен и удлен из списка
        self.inventory.set_vars(d)

    def items_of_break(self):
        return self.inventory.items_of_break()

cccc = 0
class Activator(Tile):
    index = 210

    def __init__(self, game, tile_pos):
        super().__init__(game, tile_pos)
        self.activating = False

    def activate_nearby_tiles(self):
        global cccc
        print("activate_nearby_tiles", cccc)
        cccc += 1
        self.activating = True
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                x, y = self.tx + i, self.ty + j
                tile, tile_obj = self.game_map.get_tile_and_obj(x, y)
                if tile[0] in ACTIVATE_TILES:
                    if tile_obj:
                        tile_obj.activate()
                    elif tile[0] == 9:
                        Entities.activate_dynamite(self.game_map, x, y, tile[0])

    def activate(self):
        if not self.activating:
            self.activate_nearby_tiles()

    def update(self, elapsed_time):
        self.activating = False

    def right_click(self, mouse_local_pos):
        self.activate_nearby_tiles()


furnace_burn_tiles = {
    52: 82,
    56: 86,
    401: 81,
    21: 61,
    22: 62,
    23: 63,
    24: 64,
    25: 65,
}
fuel_tiles = {idx: 1 for idx in WOOD_TILES}


class Furnace(Tile):
    not_save_vars = Tile.not_save_vars | {"animation"}
    index = 131
    burn_time = FPS
    view_interface_on_click = True

    def __init__(self, game, tile_pos):
        super(Furnace, self).__init__(game, tile_pos)
        self.fuel_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        self.fuel_cell.filter_items = set(fuel_tiles)
        self.input_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        self.result_cell = Inventory(self.game_map, self, [1, 1], items_update_event=self.check_cells_and_start)
        # self.result_cell.flag_not_put_in = True
        self.burning = None
        self.progress = 0
        self.timer = 0
        self.animation = Animation(furnace_imgs[1:], looped=True, fps=30)

    def __start_burning(self):
        self.progress = 0
        self.burning = self.input_cell[0].index
        self.fuel_cell.get_from_inventory(self.fuel_cell[0].index, 1)
        self.timer = 0
        self.animation.start()
        # self.game.add_timer_handler(self.__finish_burning, self.burn_time)

    def __finish_burning(self):
        self.animation.stop()
        # if self.check_cells(fuel_is_getting=True):
        self.result_cell.put_to_inventory(ItemsTile(self.game, furnace_burn_tiles[self.burning], count=1))
        self.input_cell.get_from_inventory(self.input_cell[0].index, 1)
        self.progress = 0
        self.burning = None
        self.check_cells_and_start()

    def check_cells_and_start(self):
        if self.check_cells():
            if self.burning != self.input_cell[0].index:
                self.__start_burning()
        else:
            self.burning = False

    def check_cells(self):
        if self.burning or (self.fuel_cell[0] and self.fuel_cell[0].index in fuel_tiles):
            if self.input_cell[0] and self.input_cell[0].index in furnace_burn_tiles:
                if (self.result_cell[0] and self.result_cell[0].count < Items.cell_size and
                    self.result_cell[0].index == furnace_burn_tiles[self.input_cell[0].index]) or \
                        (not self.result_cell[0]):
                    return True
        return False

    def update(self, elapsed_time):
        if self.burning:
            self.timer += 0.5
            self.progress = self.timer / self.burn_time
            if self.timer >= self.burn_time:
                self.__finish_burning()
            self.animation.update(elapsed_time * 0.5)
            return self.animation.get_frame()

    def items_of_break(self):
        inventories = [self.fuel_cell, self.input_cell, self.result_cell]
        return sum([inv.items_of_break() for inv in inventories], [])


classes = {Chest, Furnace, CommandBlock, Activator}
tiles_class = {cls.index: cls for cls in classes}
