from pygame import KEYDOWN, MOUSEWHEEL

from units.Objects.Items import ItemsTile, Items
from units.Tools import TOOLS
from units.UI.UI import InventoryPlayerUI
from units.common import *
from units.creating_items import RECIPES


class Inventory(SavedObject):
    not_save_vars = SavedObject.not_save_vars | {"owner", "game_map", "items_update_event", "inventory"}
    # cell_size = 1000

    def __init__(self, game_map, owner, size_table=(10, 5), items_update_event=None):
        self.game_map = game_map
        self.owner = owner
        self.size_table = size_table
        self.inventory_size = self.size_table[0] * self.size_table[1]
        self.inventory = [None] * self.inventory_size
        # self.inventory[0] = ItemSword(self.game)
        self.active_cell = 0
        self.items_update_event = items_update_event
        self.flag_not_put_in = False
        self.filter_items = None

    def set_vars(self, vrs):
        self.update_inventory_from_lst(vrs.pop("inventory"))
        super(Inventory, self).set_vars(vrs)

    def get_vars(self):
        d = super(Inventory, self).get_vars()
        d["inventory"] = [(type(i), i.get_vars()) if i else None for i in self.inventory]
        return d

    def __getitem__(self, pos):
        """[index] - получение ячейки по индексу в масиве
        [(row, column)] - получение ячейки по стлолбцу и строке в таблице"""
        if type(pos) is int:
            return self.inventory[pos]
        elif type(pos) is tuple:
            x, y = pos
            return self.inventory[y * self.size_table[0] + x]

    def __setitem__(self, key, value):
        if type(key) is int:
            self.inventory[key] = value
        elif type(key) is tuple:
            x, y = key
            self.inventory[y * self.size_table[0] + x] = value

    def __iter__(self):
        for item in self.inventory:
            yield item

    def update_inventory_from_lst(self, _inventory):
        for i in range(len(_inventory)):
            if _inventory[i] is None:
                self.inventory[i] = None
            else:
                type_obj, vrs_obj = _inventory[i]

                obj = type_obj(self.game_map.game)
                obj.set_vars(vrs_obj)
                if obj.class_obj & OBJ_ITEM and obj.class_item & CLS_TOOL:
                    obj.set_owner(self.owner)
                self.inventory[i] = obj
        self.items_updated()

    @property
    def row_work(self) -> list:
        return self.inventory[:self.size_table[0]]

    def discard_item(self, num_cell=None, items: Items = None, discard_vector=(TSIZE * 2, 10)):
        if num_cell is not None:
            items = self.inventory[num_cell]
            self.inventory[num_cell] = None
            self.redraw()
        if items:
            ix, iy = self.owner.rect.centerx + discard_vector[0], self.owner.rect.centery + discard_vector[1]
            items.rect.x, items.rect.y = ix, iy
            items.update_chunk_pos()
            items.alive = True
            # print(ix, iy, *self.game_map.to_chunk_xy(ix // TSIZE, iy // TSIZE), items)
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(ix // TSIZE, iy // TSIZE), items)
        self.items_updated()

    def discard_all_items(self):
        for i in range(len(self.inventory)):
            self.discard_item(i, None, discard_vector=(0, 0))

    def put_to_inventory(self, items):
        if self.flag_not_put_in:
            return False, items.count
        if items.count <= 0:
            return True, None
        i = 0
        while i < self.inventory_size:
            cell = self.inventory[i]
            if cell and cell.index == items.index and cell.count < cell.cell_size:
                free_place = cell.cell_size - cell.count
                if items.count > free_place:
                    cell.count += free_place
                    items.count -= free_place
                else:
                    self.inventory[i].count += items.count
                    break
            i += 1
        else:
            i = 0
            while i < self.inventory_size:
                cell = self.inventory[i]
                if cell is None:
                    if items.count <= items.cell_size:
                        self.set_cell(i, items)
                    else:
                        self.inventory[i] = items.copy()
                        self.inventory[i].count = items.cell_size
                        items.count -= items.cell_size
                        continue
                    break
                i += 1
            else:
                # print("Перепонен инвентарь", ttile)
                self.redraw()
                # self.ui.redraw_top()
                self.items_updated()
                return False, items.count
        # self.ui.redraw_top()
        self.redraw()
        self.items_updated()
        return True, None

    def find_in_inventory(self, ttile, count=1):
        all_cnt = 0
        for i in filter(lambda x: x, self.inventory):
            if i.index == ttile:
                all_cnt += i.count
                if all_cnt >= count:
                    return True
        return False

    def get_from_inventory(self, ttile, count):
        if not self.find_in_inventory(ttile, count):
            return False
            # мы знаем что ttile есть в инвенторе
        for i in range(self.inventory_size):
            if self.inventory[i]:
                item = self.inventory[i]
                if item.index == ttile:
                    if item.count <= count:
                        count -= item.count
                        self.inventory[i] = None
                    else:
                        self.inventory[i].count -= count
                        break
        self.redraw()
        self.items_updated()
        return True

    def get_cell_from_inventory(self, num_cell, del_in_inventory=True):
        item = self.inventory[num_cell]
        if del_in_inventory:
            self.inventory[num_cell] = None
        self.redraw()
        self.items_updated()
        return item

    def items_updated(self):
        if self.items_update_event:
            self.items_update_event()

    def set_cell(self, num_cell, item):

        if item is not None:
            if item.count <= 0:
                item = None
            elif item.class_item & CLS_TOOL:
                item.set_owner(self.owner)

        self.inventory[num_cell] = item
        self.items_updated()

    def redraw(self):
        pass

    def items_of_break(self):
        return [(item.index, item.count) for item in self.inventory if item]



class InventoryPlayer(Inventory):
    not_save_vars = Inventory.not_save_vars | {"ui", }

    def __init__(self, owner):
        super(InventoryPlayer, self).__init__(owner.game_map, owner=owner, size_table=(10, 5))
        self.ui = InventoryPlayerUI(self)
        self.active_cell = 0
        self.available_create_items = []

    def pg_event(self, event):
        if self.ui.pg_event(event):
            return True
        if event.type == KEYDOWN:
            if event.key in NUM_KEYS:
                self.active_cell = NUM_KEYS.index(event.key)
                self.redraw()
        elif event.type == MOUSEWHEEL:
            self.active_cell -= event.y
            if self.active_cell <= -1:
                self.active_cell = self.size_table[0] - 1
            elif self.active_cell >= self.size_table[0]:
                self.active_cell = 0
            self.redraw()

    def update_available_create_items(self):
        self.available_create_items = []
        for i in range(len(RECIPES)):
            if self.check_creating_item_of_i(i):
                self.available_create_items.append(RECIPES[i][0][0])
        # print(self.available_create_items)
        return self.available_create_items

    def check_creating_item_of_i(self, rec_i):
        
        if 0 <= rec_i < len(RECIPES):
            if self.owner.creative_mode:
                return True
            
            out, need = RECIPES[rec_i]
            for t, c in need:
                # t - ttile, c - count
                if c == -1:
                    # косаемся ли мы нужного блока
                    if t in self.owner.collisions_ttile:
                        continue
                elif self.find_in_inventory(t, c):
                 
                    continue
                return False
            return True
        return False

    def creating_item_of_i(self, rec_i, cnt=1):
        if self.check_creating_item_of_i(rec_i):
            out, need = RECIPES[rec_i]
            [self.get_from_inventory(t, c) for t, c in need]
            if out[0] in TOOLS:
                item = TOOLS[out[0]](self.owner.game)
                item.set_owner(self)
            else:
                item = ItemsTile(self.owner.game, out[0], count=out[1])
            res, _ = self.put_to_inventory(item)  # дверь
            if not res:
                self.discard_item(None, item)
            self.owner.achievements.new_created(item.index)

    def choose_active_cell(self, i):
        self.owner.choose_active_cell(i)

    def redraw(self):
        self.update_available_create_items()
        self.owner.choose_active_cell()

    def find_in_inventory(self, ttile, count=1):
        if self.owner.creative_mode:
            return True
        return super(InventoryPlayer, self).find_in_inventory(ttile, count)

    def get_from_inventory(self, ttile, count):
        if self.owner.creative_mode:
            return True
        return super(InventoryPlayer, self).get_from_inventory(ttile, count)


class InventoryChest(Inventory):
    size_table = (10, 5)

    def __init__(self, tile_obj):
        super(InventoryChest, self).__init__(tile_obj, self.size_table)
