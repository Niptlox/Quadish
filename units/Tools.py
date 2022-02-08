from random import randint
from time import time

from pygame import Vector2

from units import Entities
from units.Items import ItemsTile, Items
from units.Texture import rot_center
from units.Tiles import item_of_break_tile, STANDING_TILES, ITEM_TILES, sword_1_img, pickaxe_1_img, tile_imgs, \
    sword_77_img
from units.common import *


class AnimationTool:
    def __init__(self, tool):
        self.tool = tool
        self.animation = False
        self.sprite = tool.sprite

    def draw(self, surface, x, y):
        if self.animation:
            surface.blit(self.sprite, (x, y))

    def update(self):
        pass

    def start(self):
        self.animation = True

    def end(self):
        self.animation = False


class AnimationHand(AnimationTool):
    distance_norm = TSIZE * 0.7
    distance_start = TSIZE * 0.6
    max_distance = TSIZE * 1
    speed = 1

    def __init__(self, tool):
        super().__init__(tool)
        self.dist = self.distance_norm
        self.direction = 1

    def start(self):
        super().start()
        self.dist = self.distance_start
        self.direction = 1

    def draw(self, surface, x, y):
        if self.sprite:
            vec: Vector2 = Vector2(self.tool.vector_to_mouse)
            if vec.x == vec.y == 0:
                vec = Vector2(self.dist, 0)
            else:
                vec.scale_to_length(self.dist)
            vec -= Vector2(HAND_SIZE // 2, HAND_SIZE // 2)
            surface.blit(self.sprite, (x + int(vec.x), y + int(vec.y)))

    def update(self):
        if self.animation:
            self.dist += self.speed * self.direction
            if self.dist >= self.max_distance:
                self.direction *= -1
            elif self.dist <= self.distance_norm:
                self.animation = False
                self.dist = self.distance_norm


class AnimationSword(AnimationTool):
    def __init__(self, tool):
        super().__init__(tool)
        self.rotate = 0
        self.rotate_speed = 5 * tool.speed
        self.rotate_end = 75
        self.set_sprite(tool.sprite)

    def start(self):
        super().start()
        self.rotate = -45

    def set_sprite(self, sprite: pg.Surface):
        w, h = sprite.get_size()
        surf = pg.Surface((w*2, h * 2)).convert_alpha()
        surf.fill((0, 0, 0, 0))
        surf.blit(sprite, (w, 0))
        self.sprite = pygame.transform.scale(surf, (w*3, h*3))

    def draw(self, surface, x, y):
        if self.animation:
            sprite, new_rect = rot_center(self.sprite, -self.rotate, x, y)
            sprite = pygame.transform.flip(sprite, self.tool.flip, False)
            surface.blit(sprite, new_rect)
        # else:
        #     sprite = pygame.transform.flip(self.sprite, self.tool.flip, False)
        #     x, y = x - self.sprite.get_width() // 2, y - self.sprite.get_height() // 2
        #     surface.blit(sprite, (x, y))
        # rx, ry = self.tool.action_rect.x - self.tool.owner.vector.x, self.tool.action_rect.y - self.tool.owner.vector.y
        # pg.draw.rect(surface, "red", ((rx + x, ry + y), self.tool.action_rect.size), width=2)

    def update(self):
        if self.animation:
            self.rotate = (self.rotate + self.rotate_speed)
            if self.rotate > self.rotate_end:
                self.end()


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
    damage = 77
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
    capability = [1, 2, 3, 4, 9, 11, 101, 102, 121, 122, 123]

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
    capability = [1, 2, 101, 102, 121, 122, 123]
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
                ttile = game_map.get_static_tile_type(x, y)
                if ttile == 9:
                    obj = Entities.Dynamite(game_map.game, x * TSIZE, y * TSIZE)
                    game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
                    game_map.set_static_tile(x, y, None)
        return result

    def update(self, vector_to_mouse: Vector2):
        self.vector_to_mouse = vector_to_mouse
        super().update(vector_to_mouse)


def check_dig_tile(game_map, x, y, tool: ToolHand):
    tile = game_map.get_static_tile(x, y)
    if tile is None or tile[1] == -1:
        return
    d_ttile = game_map.get_static_tile_type(x, y - 1)
    if d_ttile in {101, 102}:
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
        res = item_of_break_tile(tile[0])
        for ttile, count_items in res:
            items = ItemsTile(game_map.game, ttile, count_items, (x * TSIZE + randint(0, TSIZE - HAND_SIZE), y * TSIZE))
            game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), items)
            # self.put_to_inventory(ttile, count_items)
        game_map.set_static_tile(x, y, None)
    else:
        game_map.set_static_tile_solidity(x, y, sol)
    return True


def check_set_tile(game_map, x, y, inventory_cell):
    if inventory_cell is None:
        return
    tile = game_map.get_static_tile(x, y)
    if tile is None or tile[0] != 0:
        return
    if inventory_cell.index in STANDING_TILES and game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
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

    def __init__(self, game, tool, pos=(0, 0)):
        super().__init__(game, tool.index, 1, pos)
        self.sprite = tool.sprite
        self.tool = tool

    def set_owner(self, owner):
        self.tool.owner = owner


class ItemSword(ItemTool):
    class_item = CLS_TOOL + CLS_SWORD
    _Tool = ToolSword

    def __init__(self, game, pos=(0, 0)):
        tool = self._Tool(None)
        super().__init__(game, tool, pos)


class ItemPickaxe(ItemTool):
    class_item = CLS_TOOL + CLS_PICKAXE
    _Tool = ToolPickaxe

    def __init__(self, game, pos=(0, 0)):
        tool = self._Tool(None)
        super().__init__(game, tool, pos)


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
