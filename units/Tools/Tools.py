from time import time

from units.Objects import Entities
from units.Tiles import item_of_break_tile, item_of_right_click_tile, STANDING_TILES, ITEM_TILES, tile_imgs, \
    tile_drops, ON_EARTHEN_PLANTS, MULTI_BLOCK_PLANTS, \
    PLANT_STAND_ON_DIRT, PLANT_STAND_ON_PLANT, BACKTILES, CLASS_TILE
from units.Tools.AnimationTool import *
from units.common import *


class Tool:
    tool_cls = CLS_NONE
    Animation = AnimationTool
    speed = 1
    index = 0
    sprite = tile_imgs[index]

    click_tile_distance = 5 * TSIZE
    click_tile_distance2 = click_tile_distance ** 2

    def __init__(self, owner):
        self.owner = owner
        self.last_action_time = 0
        self.animation = self.Animation(self)
        self.flip = False
        self.action = False
        self.reload_time = 1 / self.speed

    def draw(self, surface, x, y):
        self.animation.draw(surface, x, y)

    def update(self, vector_to_mouse):
        if not self.animation.animation:
            self.flip = vector_to_mouse.x < 0
        self.animation.update()
        if self.animation.animation and time() > self.reload_time + self.last_action_time:
            self.animation.end()

    def left_button(self, vector_to_mouse):
        pass

    def right_button(self, vector_to_mouse):
        pass

    def right_button_click(self, vector_to_mouse):
        vtm = vector_to_mouse
        dist2 = vtm.length_squared()
        if dist2 < self.click_tile_distance2:
            vp: Vector2 = self.owner.vector  # player
            v_tile = (vtm + vp) // TSIZE
            v_local_pos_tile = (vtm + vp) - v_tile * TSIZE
            x, y = int(v_tile.x), int(v_tile.y)
            return tile_click(self.owner.game_map, None, x, y, v_local_pos_tile, self.owner)
        return False


def tile_click(game_map, tile, x, y, local_pos_tile, player):
    if tile is None:
        tile = game_map.get_static_tile(x, y)
    ttile = tile[0]
    if ttile == 0:
        return False
    elif ttile == 9:
        Entities.activate_dynamite(game_map, x, y, ttile)
    elif ttile == 126:
        tile = game_map.get_static_tile(x, y)
        if not tile[3]:
            tile[3] = [None] * 4
        items = tile[3]
        i = int((local_pos_tile[0] // 16) + (local_pos_tile[1] // 16) * 2)
        if items[i] is None:
            item = player.inventory.get_cell_from_inventory(player.inventory.active_cell)
            if item:
                items[i] = (item.index, item.count)
        else:
            game_map.add_item_of_index(items[i][0], items[i][1], x, y)
            items[i] = None
        game_map.set_static_tile(x, y, tile)
    elif ttile == 122:  # стул
        sx, sy = x * TSIZE - 3, y * TSIZE + 16
        player.sit((sx, sy))
    elif ttile == 123:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(124))
    elif ttile == 124:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(123))
    elif ttile == 127:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(128))
    elif ttile == 128:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(127))
    elif ttile in CLASS_TILE:
        obj = game_map.get_tile_obj(x // CHUNK_SIZE, y // CHUNK_SIZE, tile[3])
        obj.right_click(local_pos_tile)
    elif ttile == 101:
        if tile[2] > 0:
            item = item_of_right_click_tile(tile)[0]
            game_map.add_item_of_index(*item, x, y)
            tile[2], tile[3][TILE_TIMER] = 0, 0
            game_map.set_static_tile(x, y, tile)
    elif ttile == 130:
        point = (x + 0.5) * TSIZE, (y + 0.5) * TSIZE
        game_map.game.player.set_spawn_point(point)
    return True


def check_dig_tile(game_map, x, y, tool):
    tile = game_map.get_static_tile(x, y)
    backtile = game_map.get_backtile(x, y)
    if not tool.can_dig_this_tile(backtile) or not tool.tool_cls & CLS_SPATULA:
        backtile = False
    if tile is None:  # or tile[1] == -1:
        return None, None
    ttile = tile[0]
    d_ttile = game_map.get_static_tile_type(x, y - 1)
    if d_ttile in {101, 103, 110} and ttile != 110:
        return None, None
    count_items = 1
    if ttile == 0:
        return None, backtile  # self.set_tile(x, y)
    if not tool.can_dig_this_tile(ttile):
        # мы не можем выкопать этой киркой
        return False, backtile
    return tile, backtile


def dig_tile(game_map, x, y, tool, check=True):
    if not check:
        tile, backtile = check_dig_tile(game_map, x, y, tool)
        if not (tile or backtile):
            return tile
    else:
        tile, backtile = check
    print(tile, backtile)
    if not tile:
        game_map.set_backtile(x, y, 0)
        game_map.add_item_of_index(backtile, 1, x, y)
        return True
    sol = tile[1]  # прочность
    if tool is None:
        sol = 0
    else:
        sol -= tool.strength
    if sol <= 0:
        if tile[0] == 110 and tool.tool_cls & CLS_PICKAXE:
            dig_tree(game_map, x, y, tool)
        else:
            break_tile(game_map, x, y, tile)
            tile_up = game_map.get_static_tile(x, y - 1)
            if tile_up[0] in STANDING_TILES and tile_up[0] not in {0, None, 110}:
                break_tile(game_map, x, y - 1, tile_up)
    else:
        game_map.set_static_tile_solidity(x, y, sol)
    return True


def dig_tree(game_map, x, y, tool):
    ttile = game_map.get_static_tile_type(x, y)
    while ttile == 110:
        if game_map.get_static_tile_type(x + 1, y) == 105:
            break_tile(game_map, x + 1, y, game_map.get_static_tile(x + 1, y))
        if game_map.get_static_tile_type(x - 1, y) == 105:
            break_tile(game_map, x - 1, y, game_map.get_static_tile(x - 1, y))
        itm_ttile, itm_count_items, ch = tile_drops[ttile][0]
        game_map.add_item_of_index(itm_ttile, itm_count_items, x, y)
        game_map.set_static_tile(x, y, None)
        y -= 1
        ttile = game_map.get_static_tile_type(x, y)
    if ttile == 105:
        break_tile(game_map, x, y, game_map.get_static_tile(x, y))


def check_set_tile(game_map, x, y, inventory_cell):
    if inventory_cell is None:
        return
    cell_ttile = inventory_cell.index
    if cell_ttile in BACKTILES:
        if game_map.get_backtile(x, y) == 0:
            return True
    tile = game_map.get_static_tile(x, y)  # ground
    if tile is None or tile[0] != 0:
        return
    # id предмета в руке

    # id блока под местом куда ставим
    bottom_ttile = game_map.get_static_tile_type(x, y + 1, 0)
    if cell_ttile in PLANT_STAND_ON_PLANT and cell_ttile == bottom_ttile:
        return tile
    if cell_ttile in MULTI_BLOCK_PLANTS and bottom_ttile == cell_ttile:
        return tile
    if cell_ttile in ON_EARTHEN_PLANTS and bottom_ttile != 1 and bottom_ttile != 2:
        return False
    if cell_ttile in STANDING_TILES and bottom_ttile == 0:
        return False
    if cell_ttile in PLANT_STAND_ON_DIRT and bottom_ttile != 1 and bottom_ttile != 2:
        return False
    if cell_ttile in ITEM_TILES:
        return False
    return tile


def set_tile(player, x, y, inventory_cell, check=True):
    if not check:
        tile = check_set_tile(player.game_map, x, y, inventory_cell)
        if tile:
            return
    if not player.creative_mode:
        inventory_cell.count -= 1
    # if inventory_cell.index == 9:  # tnt
    #     obj = Entities.Dynamite(game_map.game, x * TSIZE, y * TSIZE)
    #     game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
    # else:
    if inventory_cell.index in BACKTILES:
        player.game_map.set_backtile(x, y, inventory_cell.index)
    else:
        tile = player.game_map.get_tile_ttile_tpos(inventory_cell.index, (x, y))
        player.game_map.set_static_tile(x, y, tile)
    if inventory_cell.count <= 0:
        return 0
    return inventory_cell.count


def break_tile(game_map, x, y, tile):
    res = item_of_break_tile(tile, game_map, (x, y))
    for ttile, count_items in res:
        game_map.add_item_of_index(ttile, count_items, x, y)
    game_map.set_static_tile(x, y, None)
