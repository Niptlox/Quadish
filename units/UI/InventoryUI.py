from math import ceil

from pygame import Surface

from units.Objects.Items import ItemsTile
from units.Tiles import tile_words, tile_imgs
from units.Tools import TOOLS
from units.common import *
from units.UI.ClassUI import SurfaceUI, ScrollSurface
from units.UI.ItemInMouse import *
from units.UI.ColorsUI import *
from units.UI.FontsUI import *
from units.creating_items import RECIPES

cell_size = int(TSIZE * 1.5)  # in interface


class InventoryUI(SurfaceUI):
    cell_size = cell_size

    def __init__(self, inventory, size_table, margin_table=10, ui_owner=None):
        self.ui_owner = ui_owner
        self.inventory = inventory
        self.margin = margin_table
        super(InventoryUI, self).__init__(((0, 0), WSIZE))
        self.convert_alpha()
        self.fill((0, 0, 0, 0))

        self.table_inventory = SurfaceUI((0, 0, size_table[0] * self.cell_size + self.margin * 2,
                                          size_table[1] * self.cell_size + self.margin * 2)).convert_alpha()
        self.table_inventory.rect.center = self.rect.center
        self.work_rect = self.table_inventory.rect

        self.inventory_info_index = None
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)

    def set_work_rect(self, value):
        self.work_rect = value

    def redraw_table_inventory(self):
        self.table_inventory.fill(bg_color)
        self.table_inventory.fill(bg_color_dark,
                                  (self.margin, self.margin, self.table_inventory.rect.w - self.margin * 2,
                                   self.table_inventory.rect.h - self.margin * 2))
        # pg.draw.rect(self.table_inventory, self.top_bg_color,)
        x = self.margin
        y = self.margin
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.inventory_size):
            if i > 0 and i % self.inventory.size_table[0] == 0:
                y += cell_size
                x = self.margin
            color = "#000000"
            # if i == self.inventory.active_cell:
            #     color = "#FFFFFF"
            pygame.draw.rect(self.table_inventory, color,
                             (x, y, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.table_inventory.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.table_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.table_inventory.blit(text, (tx, ty))
            x += cell_size

    def redraw_inventory_info(self):
        item = self.inventory[self.inventory_info_index]
        if item is None:
            self.inventory_info_index = -1
            return
        string = tile_words[item.index]
        if config.GameSettings.view_item_index:
            string += f" #{item.index}"
        text = textfont.render(string, True, text_color_light)
        w, h = text.get_size()
        self.inventory_info_index_surface = pygame.Surface((w + 6, h + 4)).convert_alpha()
        self.inventory_info_index_surface.fill(self.top_bg_color)
        self.inventory_info_index_surface.blit(text, (3, 2))

    def get_draw_rect(self):
        return self.table_inventory.rect

    def draw(self, surface):
        self.redraw_table_inventory()
        self.fill(color_none)
        self.table_inventory.draw(self)
        if get_obj_mouse():
            self.blit(get_obj_mouse().sprite, pg.mouse.get_pos())
        elif self.inventory_info_index != -1:
            mx, my = pg.mouse.get_pos()
            self.blit(self.inventory_info_index_surface, (mx, my + 26))
        surface.blit(self, self.rect)

    def convert_table_mpos_to_i(self, pos):
        offset = self.margin
        if self.ui_owner:
            offset_ui = self.ui_owner.get_onscreen_pos()
            pos = pos[0] - offset_ui[0], pos[1] - offset_ui[1]
        if self.table_inventory.rect.collidepoint(pos):
            i = (pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size + \
                (pos[1] - (self.table_inventory.rect.y + offset)) // self.cell_size * self.inventory.size_table[0]
            return i
        return -1

    def pg_event(self, event: pg.event.Event) -> Union[bool, None]:
        if event.type == pg.MOUSEBUTTONDOWN:
            if get_obj_mouse() and not self.work_rect.collidepoint(event.pos):
                # DISCARD ITEM
                discard_vector = (TSIZE * (2 if event.pos[0] > self.rect.centerx else -2), 10)
                self.inventory.discard_item(items=get_obj_mouse(), discard_vector=discard_vector)
                set_obj_mouse(None)
                return True
            i = self.convert_table_mpos_to_i(event.pos)
            if 0 <= i < self.inventory.inventory_size:

                if get_obj_mouse():
                    if self.inventory.flag_not_put_in:
                        return True
                    if self.inventory.filter_items:
                        if get_obj_mouse().index not in self.inventory.filter_items:
                            return True
                    # положить объект из мыши
                    put_item = get_obj_mouse()
                    if event.button == pg.BUTTON_RIGHT:
                        # положить один предмет при нажатии првой кнопкой мыши
                        put_item = put_item.copy()
                        put_item.count = 1
                        get_obj_mouse().count -= 1
                        if get_obj_mouse().count <= 0:
                            set_obj_mouse(None)
                    else:
                        set_obj_mouse(None)
                    item = self.inventory.get_cell_from_inventory(i)
                    if item and item.index == put_item.index and item.count < item.cell_size:
                        put_item.add(item)
                        if item.count <= 0:
                            item = get_obj_mouse()
                    elif item is None:
                        item = get_obj_mouse()
                    else:
                        if get_obj_mouse():
                            put_item.add(get_obj_mouse())
                    self.inventory.set_cell(i, put_item)
                    set_obj_mouse(item)
                    self.inventory.redraw()
                else:
                    # взять объект в мышь
                    item = None
                    if event.button == pg.BUTTON_LEFT:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=True)
                    elif event.button == pg.BUTTON_RIGHT:
                        _item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False)
                        if _item is None:
                            return True
                        item = _item.copy()
                        _item.count //= 2
                        item.count -= _item.count
                        if _item.count == 0:
                            self.inventory[i] = None
                        self.inventory.redraw()
                    elif event.button == pg.BUTTON_MIDDLE and self.inventory.game_map.creative_mode:
                        item = self.inventory.get_cell_from_inventory(i, del_in_inventory=False)
                        if item is None:
                            return True
                        item = item.copy()
                        item.count = item.cell_size
                    set_obj_mouse(item, place=(self, i))
                return True
        elif event.type == pg.MOUSEMOTION:
            i = self.convert_table_mpos_to_i(event.pos)
            if self.rect.collidepoint(event.pos) and 0 <= i < self.inventory.inventory_size:
                self.inventory_info_index = i
                self.redraw_inventory_info()
            else:
                self.inventory_info_index = -1
        return False


class InventoryPlayerUI(InventoryUI):
    cell_size = cell_size

    def __init__(self, inventory):
        super(InventoryPlayerUI, self).__init__(inventory, inventory.size_table)
        self.convert_alpha()
        self.fill((0, 0, 0, 0))

        # self.info_surface = SurfaceUI((0, 0, 250, 80)).convert_alpha()

        self.work_inventory = SurfaceUI((15, 15, self.inventory.size_table[0] * self.cell_size,
                                         self.cell_size)).convert_alpha()
        self.table_inventory = SurfaceUI((0, 0, self.inventory.size_table[0] * self.cell_size + 40,
                                          self.inventory.size_table[1] * self.cell_size + 10 + 40)).convert_alpha()
        self.work_inventory.rect.centerx = self.rect.centerx
        self.table_inventory.rect.center = self.rect.center
        self.work_rect = self.table_inventory.rect

        self.inventory_info_index = -1
        self.inventory_info_index_surface = pygame.Surface((1, 1))
        self.top_bg_color = (82, 82, 91, 150)
        self.recipes = ScrollSurfaceRecipes(self.inventory,
                                            pg.Rect((0, 0, self.cell_size * 5, self.table_inventory.rect.h)))
        self.recipes.rect.y = self.table_inventory.rect.y
        self.recipes.rect.left = self.table_inventory.rect.right + 20

        self.all_tiles = ScrollSurfaceAllTiles(self.inventory, self.recipes.rect)

        self.opened_full_inventory = False

    def redraw_table_inventory(self):
        self.table_inventory.fill(bg_color)
        self.table_inventory.fill(bg_color_dark,
                                  (20, 20, self.table_inventory.rect.w - 40, self.table_inventory.rect.h - 40))
        x = 20
        y = 20
        i = 0
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.inventory_size):
            if i == self.inventory.size_table[0]:
                y += 10
            if i > 0 and i % self.inventory.size_table[0] == 0:
                y += cell_size
                x = 20
            color = "#000000"
            if i == self.inventory.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.table_inventory, color,
                             (x, y, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.table_inventory.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.table_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.table_inventory.blit(text, (tx, ty))
            x += cell_size

    def redraw_top(self):
        self.recipes.redraw()
        self.redraw_table_inventory()
        self.work_inventory.fill(self.top_bg_color)
        x = 0
        y = 0
        i = 0
        cell_size = self.cell_size
        cell_size_2 = cell_size // 2
        for i in range(self.inventory.size_table[0]):
            color = "#000000"
            if i == self.inventory.active_cell:
                color = "#FFFFFF"
            pygame.draw.rect(self.work_inventory, color,
                             (x, 0, self.cell_size, self.cell_size), 1)
            cell = self.inventory[i]
            if cell is not None:
                img = cell.sprite
                iw, ih = img.get_size()
                self.work_inventory.blit(img, (x + cell_size_2 - iw // 2, cell_size_2 - ih // 2))
                res = str(cell.count)
                tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)
                text = textfont.render(res, True, text_color_dark)
                self.work_inventory.blit(text, (tx + 1, ty + 1))
                text = textfont.render(res, True, text_color_light)
                self.work_inventory.blit(text, (tx, ty))
            x += cell_size

    def draw(self, surface):
        self.redraw_table_inventory()

        self.fill(color_none)

        self.work_inventory.draw(self)
        if self.opened_full_inventory:
            # pg.draw.rect(self, bg_color, self.rect)
            self.table_inventory.draw(self)
            if self.inventory.owner.creative_mode:
                self.all_tiles.draw(self)
            else:
                self.recipes.draw(self)
            if get_obj_mouse():
                self.blit(get_obj_mouse().sprite, pg.mouse.get_pos())
            elif self.inventory_info_index != -1:
                mx, my = pg.mouse.get_pos()
                self.blit(self.inventory_info_index_surface, (mx, my + 26))
        else:
            if self.inventory_info_index != -1:
                self.blit(self.inventory_info_index_surface,
                          (self.work_inventory.rect.x + self.inventory_info_index * self.cell_size,
                           self.work_inventory.rect.y + self.cell_size))

        surface.blit(self, self.rect)

    def convert_table_mpos_to_i(self, pos):
        if not self.table_inventory.rect.collidepoint(pos):
            return -1
        offset = 20
        sy = (self.table_inventory.rect.y + offset + self.cell_size + 10)
        i = -1
        if pos[1] > sy:
            i = self.inventory.size_table[0] + (
                    pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size + (
                        pos[1] - sy) // self.cell_size * self.inventory.size_table[0]
        else:
            if (self.table_inventory.rect.y + offset) < pos[1] < (
                    self.table_inventory.rect.y + offset + self.cell_size):
                i = (pos[0] - (self.table_inventory.rect.x + offset)) // self.cell_size
        return i

    def pg_event(self, event: pg.event.Event):
        if self.opened_full_inventory:
            if self.inventory.owner.creative_mode:
                if self.all_tiles.pg_event(event):
                    return True
            else:
                if self.recipes.pg_event(event):
                    return True
        if event.type == pg.KEYDOWN and event.key == pg.K_e:
            # OPEN OR CLOSE  full INVENTORY
            self.opened_full_inventory = not self.opened_full_inventory
            self.recipes.info_index = None
            self.inventory_info_index = -1
            return True
        if self.opened_full_inventory:
            if super(InventoryPlayerUI, self).pg_event(event):
                return True
        else:
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == pg.BUTTON_LEFT:
                    if self.work_inventory.rect.collidepoint(event.pos):
                        i = (event.pos[0] - self.work_inventory.rect.x) // self.cell_size
                        self.inventory.choose_active_cell(i)
                        return True
            elif event.type == pg.MOUSEMOTION:
                if self.work_inventory.rect.collidepoint(event.pos):
                    i = (event.pos[0] - self.work_inventory.rect.x) // self.cell_size
                    self.inventory_info_index = i
                    self.redraw_inventory_info()
                else:
                    self.inventory_info_index = -1
        return False



class ScrollSurfaceRecipes(ScrollSurface):
    cell_size = cell_size
    count_cells = len(RECIPES)

    def __init__(self, inventory, rect, scroll_size=(5 * cell_size, ceil(len(RECIPES) / 5) * cell_size)):
        super(ScrollSurfaceRecipes, self).__init__(rect, scroll_size=scroll_size, background=bg_color)
        self.info_index = None
        self.info_index_surface = None
        self.inventory = inventory

    def redraw_recipes_info(self):
        out, recipe = RECIPES[self.info_index]
        tx = 3
        ty = 3
        name = tile_words[out[0]]
        if config.GameSettings.view_item_index:
            name += f" #{out[0]}"

        name_surface = textfont.render(name, True, text_color_light)
        span = textfont.get_height()
        self.info_index_surface = pygame.Surface(
            (max(140, name_surface.get_width() + 6), span * (len(recipe) + 3) + 3),
            pygame.SRCALPHA,
            32)
        self.info_index_surface.fill(bg_color)
        self.info_index_surface.blit(name_surface, (tx, ty))
        ty += span
        self.info_index_surface.blit(textfont.render("-" * 50, True, text_color_light), (0, ty))
        ty += span
        for index, cnt in recipe:
            res = f"{tile_words[index]}: {cnt if cnt > 0 else ''}"
            text = textfont.render(res, True, text_color_light)
            self.info_index_surface.blit(text, (tx, ty))
            ty += span
        self.info_index_surface.blit(textfont.render("-" * 50, True, text_color_light), (0, ty))

    def redraw(self):
        gray_cell = Surface((self.cell_size, self.cell_size - 1)).convert_alpha()
        gray_cell.fill("#A3A3A3AA")
        self.scroll_surface.fill(color_none)
        x = 0
        y = 0
        i = 0
        cell_size_2 = self.cell_size // 2
        for i in range(len(RECIPES)):
            if i % 5 == 0 and i > 0:
                y += cell_size
                x = 0
            color = "#000000"
            pygame.draw.rect(self.scroll_surface, color,
                             (x, y, self.cell_size, self.cell_size - 1), 1)
            cell = RECIPES[i][0]
            img = tile_imgs[cell[0]]
            iw, ih = img.get_size()
            self.scroll_surface.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
            res = str(cell[1])
            tx, ty = (x + self.cell_size - 4 - 7 * len(res), y + self.cell_size - 15)

            text = textfont.render(res, True, text_color_dark)
            self.scroll_surface.blit(text, (tx + 1, ty + 1))
            text = textfont.render(res, True, text_color_light)
            self.scroll_surface.blit(text, (tx, ty))
            if cell[0] not in self.inventory.available_create_items:
                self.scroll_surface.blit(gray_cell, (x, y))
            x += self.cell_size

    def draw(self, surface):
        self.main_scrolling()
        self.fill(bg_color)
        self.inventory.update_available_create_items()
        self.redraw()
        self.blit(self.scroll_surface, self.scroll_surface.rect)
        surface.blit(self, self.rect)
        if self.info_index is not None:
            mx, my = pg.mouse.get_pos()
            surface.blit(self.info_index_surface, (mx, my + 26))

    def creating_item_of_i(self, i, cnt=1):
        self.inventory.creating_item_of_i(i, cnt=cnt)

    def pg_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                event.pos = (event.pos[0] - self.scroll_surface.rect.x, event.pos[1] - self.scroll_surface.rect.y)
                if event.button in (pg.BUTTON_LEFT, pg.BUTTON_MIDDLE):
                    i = (event.pos[0] - self.rect.x) // self.cell_size + (
                            event.pos[1] - self.rect.y) // self.cell_size * 5
                    if i < self.count_cells:
                        cnt = 1
                        if self.inventory.owner.creative_mode and event.button == pg.BUTTON_MIDDLE:
                            cnt = 999
                        self.creating_item_of_i(i, cnt=cnt)
                    return True
        elif event.type == pg.MOUSEWHEEL:
            if self.rect.collidepoint(pg.mouse.get_pos()):
                self.mouse_scroll(dy=event.y * self.cell_size // 3)
                self.info_index = None
                return True
        elif event.type == pg.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                event.pos = (event.pos[0] - self.scroll_surface.rect.x, event.pos[1] - self.scroll_surface.rect.y)
                i = (event.pos[0] - self.rect.x) // self.cell_size + (
                        event.pos[1] - self.rect.y) // self.cell_size * 5
                if 0 <= i < self.count_cells:
                    if i != self.info_index:
                        self.info_index = i
                        self.redraw_recipes_info()
                else:
                    self.info_index = None
            else:
                self.info_index = None


class ScrollSurfaceAllTiles(ScrollSurfaceRecipes):
    cell_size = cell_size
    count_cells = len(tile_words)

    def __init__(self, inventory, rect):
        scroll_size = (5 * cell_size, ceil(len(tile_words) / 5) * cell_size)
        super(ScrollSurfaceAllTiles, self).__init__(inventory, rect, scroll_size=scroll_size)
        self.redraw()

    def redraw_recipes_info(self):
        ttile, name = list(tile_words.items())[self.info_index]
        if config.GameSettings.view_item_index:
            name += f" #{ttile}"
        name_surface = textfont.render(name, True, text_color_light)
        self.info_index_surface = pygame.Surface(
            (name_surface.get_width() + 6, textfont.get_height() + 3),
            pygame.SRCALPHA,
            32)
        self.info_index_surface.fill(bg_color)
        self.info_index_surface.blit(name_surface, (3, 3))

    def redraw(self):
        self.scroll_surface.fill(color_none)
        x, y = 0, 0
        cell_size_2 = cell_size // 2
        for i in range(len(tile_words)):
            if i % 5 == 0 and i > 0:
                y += cell_size
                x = 0
            color = "#000000"
            pygame.draw.rect(self.scroll_surface, color,
                             (x, y, self.cell_size, self.cell_size - 1), 1)
            ttile = list(tile_words.keys())[i]
            img = tile_imgs[ttile]
            iw, ih = img.get_size()
            self.scroll_surface.blit(img, (x + cell_size_2 - iw // 2, y + cell_size_2 - ih // 2))
            x += cell_size

    def creating_item_of_i(self, i, cnt=1):
        ttile = list(tile_words.keys())[i]
        if ttile in TOOLS:
            item = TOOLS[ttile](self.inventory.owner.game)
            item.set_owner(self)
        else:
            item = ItemsTile(self.inventory.owner.game, ttile, count=cnt)
        self.inventory.put_to_inventory(item)
