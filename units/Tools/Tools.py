from random import randint
from time import time

from units import Entities
from units.Creatures import SlimeBigBoss
from units.Items import ItemsTile, Items
from units.Tools.AnimationTool import *

from units.Tiles import item_of_break_tile, item_of_right_click_tile, STANDING_TILES, ITEM_TILES, tile_imgs, \
    tile_many_imgs
from units.common import *


class Tool:
    tool_cls = CLS_NONE
    Animation = AnimationTool
    speed = 1
    index = 0
    sprite = tile_imgs[index]

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
        vp: Vector2 = self.owner.vector  # player
        v_tile = (vtm + vp) // TSIZE
        v_local_pos_tile = (vtm + vp) - v_tile * TSIZE
        x, y = int(v_tile.x), int(v_tile.y)
        return tile_click(self.owner.game_map, None, x, y, v_local_pos_tile, self.owner)


def tile_click(game_map, tile, x, y, local_pos_tile, player):
    if tile is None:
        tile = game_map.get_static_tile(x, y)
    ttile = tile[0]
    if ttile == 9:
        obj = Entities.Dynamite(game_map.game, x * TSIZE, y * TSIZE)
        game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
        game_map.set_static_tile(x, y, None)
    elif ttile == 126:
        tile = game_map.get_static_tile(x, y)
        if tile[3] == 0:
            tile[3] = [None] * 4
        items = tile[3]
        i = int((local_pos_tile[0] // 16) + (local_pos_tile[1] // 16) * 2)
        if items[i] is None:
            item = player.inventory.get_cell_from_inventory(player.active_cell)
            if item:
                items[i] = (item.index, item.count)
        else:
            game_map.add_item_of_index(items[i][0], items[i][1], x, y)
            items[i] = None
        game_map.set_static_tile(x, y, tile)
    elif ttile == 123:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(124))
    elif ttile == 124:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(123))
    elif ttile == 127:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(128))
    elif ttile == 128:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(127))
    elif ttile == 101:
        if tile[2] > 0:
            item = item_of_right_click_tile(tile)[0]
            game_map.add_item_of_index(*item, x, y)
            tile[2], tile[3] = 0, 0
            game_map.set_static_tile(x, y, tile)
    elif ttile == 130:
        point = (x + 0.5) * TSIZE, (y + 0.5) * TSIZE
        game_map.game.player.set_spawn_point(point)


def check_dig_tile(game_map, x, y, tool):
    tile = game_map.get_static_tile(x, y)
    if tile is None:  # or tile[1] == -1:
        return
    d_ttile = game_map.get_static_tile_type(x, y - 1)
    if d_ttile in {101, 102, 103}:
        return
    ttile = tile[0]
    count_items = 1
    if ttile == 0:
        return  # self.set_tile(x, y)
    if tool.capability is not None and ttile not in tool.capability:
        # мы не можем выкопать этой киркой
        return False
    return tile


def dig_tile(game_map, x, y, tool, check=True):
    if not check:
        tile = check_dig_tile(game_map, x, y, tool)
        if not tile:
            return tile
    else:
        tile = game_map.get_static_tile(x, y)
    sol = tile[1]  # прочность
    sol -= tool.strength
    if sol <= 0:
        res = item_of_break_tile(tile)
        for ttile, count_items in res:
            game_map.add_item_of_index(ttile, count_items, x, y)
        game_map.set_static_tile(x, y, None)
    else:
        game_map.set_static_tile_solidity(x, y, sol)
    return True


def check_set_tile(game_map, x, y, inventory_cell):
    if inventory_cell is None:
        return
    tile = game_map.get_static_tile(x, y)  # ground
    if tile is None or tile[0] != 0:
        return
    # id предмета в руке
    cell_ttile = inventory_cell.index
    # id блока под местом куда ставим
    bottom_ttile = game_map.get_static_tile_type(x, y + 1, 0)
    if cell_ttile == 126 and bottom_ttile == 126:
        return tile
    if cell_ttile in STANDING_TILES and bottom_ttile in STANDING_TILES:
        return False
    if cell_ttile == 101 and not bottom_ttile == 1:
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
    player.game_map.set_static_tile(x, y, player.game_map.get_tile_ttile(inventory_cell.index))
    if inventory_cell.count <= 0:
        return 0
    return inventory_cell.count

