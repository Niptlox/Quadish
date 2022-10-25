from units.UI.ClassUI import SurfaceUI
from units.UI.ColorsUI import *
from units.UI.InventoryUI import InventoryUI, cell_size, InventoryPlayerUI
from units.UI.ItemInMouse import *
from units.common import *


class BlockUI(SurfaceUI):
    def __init__(self, rect):
        super(BlockUI, self).__init__(rect)
        self.block_obj = None
        self.work_rect = self.rect

    def set_block(self, block_obj):
        self.block_obj = block_obj

    def set_work_rect(self, value):
        pass

    def get_draw_rect(self):
        return self.rect

    def get_onscreen_pos(self):
        return self.rect


class ChestUI(InventoryUI):
    def __init__(self):
        super(ChestUI, self).__init__(None, Chest_size_table)

    def set_chest_inventory(self, chest_inventory):
        self.inventory = chest_inventory
        self.redraw_table_inventory()

    def set_block(self, block_obj):
        self.set_chest_inventory(block_obj.inventory)


class FurnaceUI(BlockUI):
    background = bg_color

    def __init__(self):
        rect = pg.Rect(0, 0, cell_size * 6, cell_size * 4)
        super(FurnaceUI, self).__init__(rect)
        self.convert_alpha()
        self.input_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.input_inventory_ui.get_draw_rect().topleft = cell_size * 0.5, cell_size * 0.5
        self.fuel_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.fuel_inventory_ui.get_draw_rect().topleft = cell_size * 0.5, cell_size * 2.5
        self.result_inventory_ui = InventoryUI(None, [1, 1], margin_table=0, ui_owner=self)
        self.result_inventory_ui.get_draw_rect().topleft = cell_size * 4.5, cell_size * 1.5
        self.inventories = self.input_inventory_ui, self.fuel_inventory_ui, self.result_inventory_ui
        self._work_rect = None

    def set_work_rect(self, value):
        for inv in self.inventories:
            inv.work_rect = value

    def draw(self, surface):
        self.fill(self.background)
        for inv in self.inventories:
            inv.draw(self)
        h = int(self.block_obj.progress * (cell_size-4))
        if h:
            x, y = self.input_inventory_ui.get_draw_rect().bottomleft
            pg.draw.rect(self, (255, 255, 255, 200), (x+2, y-h-2, 5, h))
        surface.blit(self, self.rect)

    def set_block(self, block_obj):
        super(FurnaceUI, self).set_block(block_obj)
        self.input_inventory_ui.inventory = block_obj.input_cell
        self.fuel_inventory_ui.inventory = block_obj.fuel_cell
        self.result_inventory_ui.inventory = block_obj.result_cell

    def pg_event(self, event: pg.event.Event):
        res = False
        for inv in self.inventories:
            res = inv.pg_event(event) or res
        return res


# Player inventory with Blocks


class InventoryPlayerWithBlockUI(SurfaceUI):
    def __init__(self, player_inventory, block_ui: BlockUI):
        super(InventoryPlayerWithBlockUI, self).__init__(((0, 0), WSIZE))
        self.player_inventory_ui = InventoryPlayerUI(player_inventory)
        self.player_inventory_ui.opened_full_inventory = True
        self.player_inventory_ui.table_inventory.rect.y = 100

        self.block_ui = block_ui
        self.block_ui.get_draw_rect().y = self.player_inventory_ui.table_inventory.rect.bottom + 40
        self.block_ui.get_draw_rect().centerx = self.player_inventory_ui.table_inventory.rect.centerx

        self.work_rect = pg.Rect.union(self.block_ui.work_rect, self.player_inventory_ui.work_rect)
        self.block_ui.set_work_rect(self.work_rect)
        self.player_inventory_ui.set_work_rect(self.work_rect)
        set_obj_mouse(None)
        self.opened = False

    def set_block(self, block_obj, view=True):
        self.block_ui.set_block(block_obj)
        if view:
            self.player_inventory_ui.opened_full_inventory = True
            self.opened = True

    def draw(self, surface):
        self.block_ui.draw(surface)
        self.player_inventory_ui.draw(surface)
        if get_obj_mouse():
            mx, my = pg.mouse.get_pos()
            self.blit(get_obj_mouse().sprite, (mx, my))
        self.opened = self.player_inventory_ui.opened_full_inventory

    def pg_event(self, event: pg.event.Event):
        res = self.player_inventory_ui.pg_event(event)
        res = self.block_ui.pg_event(event) or res
        return res


class InventoryPlayerChestUI(InventoryPlayerWithBlockUI):
    def __init__(self, player_inventory):
        super(InventoryPlayerChestUI, self).__init__(player_inventory, ChestUI())


class InventoryPlayerFurnaceUI(InventoryPlayerWithBlockUI):
    def __init__(self, player_inventory):
        super(InventoryPlayerFurnaceUI, self).__init__(player_inventory, FurnaceUI())
