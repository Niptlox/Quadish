from random import randint
from time import time

from units import Entities
from units.Items import ItemsTile, Items
from units.AnimationTool import *

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
        self.tile_click = False

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
        vtm = vector_to_mouse
        vp: Vector2 = self.owner.vector  # player
        v_tile = (vtm + vp) // TSIZE
        x, y = int(v_tile.x), int(v_tile.y)
        if self.tile_click:
            tile_click(self.owner.game_map, None, x, y)
            self.tile_click = False


class ToolSword(Tool):
    tool_cls = CLS_WEAPON + CLS_SWORD
    damage = 12
    speed = 2
    distance = 1.5 * TSIZE
    Animation = AnimationSword
    discard_distance = 10
    index = 501
    sprite = tile_imgs[index]

    def __init__(self, owner):
        super().__init__(owner)
        self.reload_half_time = self.reload_time / 2
        self.action_rect = pg.Rect((0, 0, self.distance, self.distance * 2 - 1))

    def left_button(self, vector_to_mouse):
        if time() < self.reload_time + self.last_action_time:
            return False
        self.last_action_time = time()
        self.action = True
        self.animation.start()
        return True

    def update(self, vector_to_mouse):
        super().update(vector_to_mouse)
        if self.action:
            if time() >= self.reload_half_time + self.last_action_time:
                self.punch()

    def punch(self):
        # смещение удара в ту сторону куда смотрит мышь
        self.action_rect.centery = self.owner.rect.centery
        if self.flip:
            self.action_rect.right = self.owner.rect.centerx
        else:
            self.action_rect.left = self.owner.rect.centerx
        for tile in self.owner.game.screen_map.dynamic_tiles:
            if tile.class_obj == OBJ_CREATURE:
                if self.action_rect.colliderect(tile):
                    tile.damage(self.damage)
                    disc_vector = [0, 0]
                    if tile.rect.x != self.owner.rect.x:
                        disc_vector[0] += self.discard_distance * (-1 if self.flip else 1)
                    if tile.rect.y != self.owner.rect.y:
                        disc_vector[1] += self.discard_distance * (
                            1 if tile.rect.centery > self.owner.rect.bottom else -1) // 2
                    tile.discard(disc_vector)
        self.action = False
        # время окончания удара уже подошло


class ToolGoldSword(ToolSword):
    damage = 7 * 7
    speed = 7
    distance = 3 * TSIZE
    Animation = AnimationSword
    discard_distance = 10
    index = 502
    sprite = tile_imgs[index]


class ToolPickaxe(ToolSword):
    tool_cls = CLS_WEAPON + CLS_PICKAXE
    strength = 20  # dig
    damage = 8  # punch
    speed = 2
    distance = 1.5 * TSIZE  # punch
    Animation = AnimationSword
    discard_distance = 10  # отбрасывание
    index = 531
    sprite = tile_imgs[index]
    dig_distance = 3 * TSIZE
    dig_distance2 = dig_distance ** 2
    capability = [1, 2, 3, 4, 9, 11, 12, 101, 102, 103, 121, 122, 123, 125]

    def __init__(self, owner):
        super().__init__(owner)
        self.stroke_rect = pg.Rect((0, 0, TSIZE, TSIZE))
        self.stroke = False

    def draw(self, surface, x, y):
        super().draw(surface, x, y)
        if self.stroke:
            pg.draw.rect(surface, "#FDE047", ((self.stroke_rect.x + x, self.stroke_rect.y + y), self.stroke_rect.size),
                         width=2)
            self.stroke = False

    def left_button(self, vector_to_mouse: Vector2):
        # dig tile
        result = False
        vtm = vector_to_mouse
        vp: Vector2 = self.owner.vector  # player
        dist2 = vtm.length_squared()
        if AUTO_BUILD and dist2 > self.dig_distance2:
            vtm.scale_to_length(TSIZE)
            dist2 = TSIZE ** 2
        if dist2 <= self.dig_distance2:
            v_tile = (vtm + vp) // TSIZE
            x, y = int(v_tile.x), int(v_tile.y)
            check = check_dig_tile(self.owner.game_map, x, y, self)
            if check:
                if time() > self.reload_time + self.last_action_time:
                    dig_tile(self.owner.game_map, x, y, self, True)
                    result = True
                    self.owner.choose_active_cell()
                self.stroke_rect.x = x * TSIZE - vp.x
                self.stroke_rect.y = y * TSIZE - vp.y
                self.stroke = True
            else:
                self.stroke = False
                # start punch
        if time() > self.reload_time + self.last_action_time:
            self.action = True
            self.flip = vector_to_mouse.x < 0
            self.animation.start()
            self.last_action_time = time()
        return result


class ToolGoldPickaxe(ToolPickaxe):
    strength = 777  # dig
    damage = 777  # punch
    speed = 7
    distance = 7 * TSIZE  # punch
    discard_distance = 17  # отбрасывание
    index = 532
    sprite = tile_imgs[index]
    dig_distance = 77 * TSIZE
    dig_distance2 = dig_distance ** 2
    capability = None


class ToolHand(ToolPickaxe):
    tool_cls = CLS_WEAPON + CLS_PICKAXE + CLS_SWORD
    damage = 4  # punch
    strength = 8  # dig
    speed = 1.5  # dig
    speed_set = 8  # set tile
    distance = 1.1 * TSIZE  # punch
    dig_distance = 3 * TSIZE
    set_distance = 4 * TSIZE
    dig_distance2 = dig_distance ** 2
    set_distance2 = set_distance ** 2
    capability = [1, 2, 11, 12, 101, 102, 103, 121, 122, 123, 125]
    Animation = AnimationHand
    discard_distance = 5

    def __init__(self, owner):
        super().__init__(owner)
        self.hand_vector = Vector2(0, 0)
        self.last_action_time_set = 0
        self.reload_time_set = 1 / self.speed_set
        self.stroke_rect = pg.Rect((0, 0, TSIZE, TSIZE))
        self.stroke = False
        self.vector_to_mouse = Vector2(0)
        self.tile_click = False

    def draw(self, surface, x, y):
        self.animation.sprite = self.owner.hand_img
        super().draw(surface, x, y)

    def right_button(self, vector_to_mouse: Vector2):
        # set tile
        result = False
        vtm = vector_to_mouse
        vp: Vector2 = self.owner.vector  # player
        dist2 = vtm.length_squared()
        if AUTO_BUILD and dist2 > self.set_distance2:
            vtm.scale_to_length(TSIZE)
            dist2 = TSIZE ** 2
        if dist2 <= self.set_distance2:
            v_tile = (vtm + vp) // TSIZE
            x, y = int(v_tile.x), int(v_tile.y)
            game_map = self.owner.game_map
            check = check_set_tile(game_map, x, y, self.owner.inventory[self.owner.active_cell])
            if check:
                if time() > self.reload_time_set + self.last_action_time_set:
                    self.last_action_time_set = time()
                    self.animation.start()
                    res = set_tile(self.owner.game_map, x, y, self.owner.inventory[self.owner.active_cell], True)
                    if res == 0:
                        self.owner.inventory[self.owner.active_cell] = None
                    self.owner.choose_active_cell()
                    result = True
                self.stroke_rect.x = x * TSIZE - vp.x
                self.stroke_rect.y = y * TSIZE - vp.y
                self.stroke = True
            else:
                self.stroke = False
                if self.tile_click:
                    tile_click(game_map, None, x, y)
                    self.tile_click = False

        return result

    def update(self, vector_to_mouse: Vector2):
        self.vector_to_mouse = vector_to_mouse
        super().update(vector_to_mouse)


def tile_click(game_map, tile, x, y):
    if tile is None:
        tile = game_map.get_static_tile(x, y)
    ttile = tile[0]
    if ttile == 9:
        obj = Entities.Dynamite(game_map.game, x * TSIZE, y * TSIZE)
        game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
        game_map.set_static_tile(x, y, None)
    elif ttile == 123:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(124))
    elif ttile == 124:
        game_map.set_static_tile(x, y, game_map.get_tile_ttile(123))
    elif ttile == 101:
        if tile[2] > 0:
            item = item_of_right_click_tile(tile)[0]
            game_map.add_item_of_index(*item, x, y)
            tile[2], tile[3] = 0, 0
            game_map.set_static_tile(x, y, tile)


def check_dig_tile(game_map, x, y, tool: ToolHand):
    tile = game_map.get_static_tile(x, y)
    if tile is None or tile[1] == -1:
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
    if inventory_cell.index in STANDING_TILES and game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
        return False
    if inventory_cell.index == 101 and not game_map.get_static_tile_type(x, y + 1, 0) == 1:
        return False
    if inventory_cell.index in ITEM_TILES:
        return False
    return tile


def set_tile(game_map, x, y, inventory_cell, check=True):
    if not check:
        tile = check_set_tile(game_map, x, y, inventory_cell)
        if tile:
            return
    inventory_cell.count -= 1
    # if inventory_cell.index == 9:  # tnt
    #     obj = Entities.Dynamite(game_map.game, x * TSIZE, y * TSIZE)
    #     game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
    # else:
    game_map.set_static_tile(x, y, game_map.get_tile_ttile(inventory_cell.index))
    if inventory_cell.count <= 0:
        return 0
    return inventory_cell.count


class ItemTool(Items):
    class_item = CLS_TOOL
    _Tool = Tool

    def __init__(self, game, pos=(0, 0)):
        tool = self._Tool(None)
        super().__init__(game, tool.index, 1, pos)
        self.sprite = tool.sprite
        self.tool = tool

    def set_owner(self, owner):
        self.tool.owner = owner

    def get_vars(self):
        d = super().get_vars()
        d.pop("tool")
        # d["_tool"] = d.pop("tool")
        return d


class ItemSword(ItemTool):
    class_item = CLS_TOOL + CLS_SWORD
    _Tool = ToolSword


class ItemPickaxe(ItemTool):
    class_item = CLS_TOOL + CLS_PICKAXE
    _Tool = ToolPickaxe


class ItemGoldSword(ItemSword):
    _Tool = ToolGoldSword


class ItemGoldPickaxe(ItemPickaxe):
    _Tool = ToolGoldPickaxe


TOOLS = {
    501: ItemSword,
    502: ItemGoldSword,
    531: ItemPickaxe,
    532: ItemGoldPickaxe,
}
