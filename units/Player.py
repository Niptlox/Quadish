import random
from typing import Union

from pygame import Vector2
from pygame.locals import *

from units.Entity import PhysicalObject
from units.Inventory import InventoryPlayer
from units.Items import Items
from units.Tiles import hand_pass_img, player_img, dig_rect_img
from units.Tools import ToolHand, TOOLS, ItemTool, \
    ToolCreativeHand  # ToolSword, ItemSword, ItemPickaxe, TOOLS, ItemGoldPickaxe, ItemTool
from units.UI.UI import InventoryPlayerChestUI
from units.common import *


# from units.Cursor import set_cursor, cursor_add_img, CURSOR_DIG, CURSOR_NORMAL, CURSOR_SET

class Player(PhysicalObject):
    class_obj = OBJ_PLAYER
    width, height = TSIZE - 10, TSIZE - 2
    player_img = player_img
    dig_rect_img = dig_rect_img
    hand_img = hand_pass_img
    start_max_lives = 20

    def __init__(self, game, x, y) -> None:
        super().__init__(game, x, y, self.width, self.height, use_physics=True)
        self.game = game
        self.ui = game.ui

        self.alive = True
        self.max_lives = self.start_max_lives
        self.lives = self.max_lives
        self.lives_surface = pg.Surface((self.rect.w, 6)).convert_alpha()
        self.eat = False

        self.tact = 0
        self.on_wall = False
        self.moving_right = False
        self.moving_left = False
        self.sitting = False
        self.dig = False
        self.dig_pos = None
        self.dig_dist = 3
        self.set = False
        self.set_dist = 5
        self.auto_block_select = True
        self.collisions_ttile = set()

        self.punched = False
        self.punch_tick = 0
        self.punch_speed = 0.8
        self.min_hand_space = TILE_SIZE // 1.5
        self.hand_space = self.min_hand_space
        self.num_down = -1
        self.get_item_rect = pg.Rect((0, 0, self.width * 3, self.height * 3))
        self.punch_rect = pg.Rect((0, 0, self.width * 3, self.height * 3))
        self.punch_damage = 10

        self.spawn_point = (0, 0)
        self.vertical_momentum = 0
        self.jump_speed = 10
        self.jump_count = 0
        self.max_jump_count = 2
        self.fall_speed = FALL_SPEED
        self.max_fall_speed = MAX_FALL_SPEED
        self.speed = 0
        self.accelerate_x = 2  # ускорение шага
        self.max_speed = 11
        self.running = True
        self.air_timer = 0
        self.first_fall = True
        self.fly_speed = 60
        self.flying = False
        self.on_up = False
        self.on_down = False

        # INVENTORY ============================
        self.creative_mode = CREATIVE_MODE

        self.inventory = InventoryPlayer(self)
        self.inventory.redraw()

        self.flip = False
        self.toolHand = ToolHand(self)
        self.toolCreativeHand = ToolCreativeHand(self)
        self.tool = None
        self.vector = Vector2(0)

        self.chest_ui = InventoryPlayerChestUI(self.inventory)
        self.tile_ui = None

    def get_vars(self):
        d = self.__dict__.copy()
        d.pop("game_map")
        d.pop("game")
        d.pop("ui")
        d.pop("hand_img")
        d.pop("lives_surface")
        # d.pop("inventory")
        d["inventory"] = self.inventory.get_vars()
        d.pop("toolHand")
        d.pop("toolCreativeHand")
        d.pop("tool")
        d.pop("chest_ui")
        print(d)
        return d

    def set_vars(self, vrs):
        self.inventory.set_vars(vrs.pop("inventory"))
        self.chest_ui = InventoryPlayerChestUI(self.inventory)
        # vrs["max_fall_speed"] = self.max_fall_speed
        vrs["rect"].size = self.rect.size

        super().set_vars(vrs)
        self.fall_speed = FALL_SPEED
        self.inventory.redraw()

    def pg_event(self, event):
        if self.chest_ui.opened and self.chest_ui.pg_event(event):
            return True
        if self.inventory.pg_event(event):
            return True
        if event.type == KEYDOWN:
            if event.key in (K_RIGHT, K_d):
                self.moving_right = True
            elif event.key in (K_LEFT, K_a):
                self.moving_left = True
            elif event.key in (K_UP, K_w, K_SPACE):
                self.on_up = True
                if pg.key.get_mods() & KMOD_ALT and self.creative_mode:
                    self.flying = not self.flying
                if not self.flying:
                    self.jump()
                # =========================================
            elif event.key in (K_DOWN, K_s) or pg.key.get_mods() & KMOD_SHIFT:
                self.on_down = True
            elif event.key == K_j and pg.key.get_mods() & KMOD_ALT:
                self.set_game_mode(not self.creative_mode)
            elif event.key == K_t and pg.key.get_mods() & KMOD_CTRL:
                self.tp_to_home()
            elif event.key == K_r and pg.key.get_mods() & KMOD_CTRL:
                self.tp_random()
            elif event.key == K_q:  # выкинуть все предметы в текущей ячейке инвентаря
                self.inventory.discard_item(self.inventory.active_cell,
                                            discard_vector=(TSIZE * (-2 if self.flip else 2), 10))
            elif event.key == K_f:
                self.inventory.creating_item_of_i(self.inventory.active_cell)
            elif event.key in NUM_KEYS:
                self.num_down = NUM_KEYS.index(event.key)
            if event.key in (K_DOWN, K_f, K_s, K_SPACE, K_w, K_UP):
                self.sitting = False
        elif event.type == KEYUP:
            if event.key in (K_RIGHT, K_d):
                self.moving_right = False
            elif event.key in (K_LEFT, K_a):
                self.moving_left = False
            elif event.key in (K_UP, K_w, K_SPACE):
                self.on_up = False
            elif event.key in (K_DOWN, K_s) or pg.key.get_mods() & KMOD_SHIFT:
                self.on_down = False
                # =========================================
        elif event.type == MOUSEBUTTONDOWN:
            if event.button in (1, 2):
                self.dig = True
            if event.button == 3:
                self.vector = Vector2(self.rect.center)
                vector_player_display = self.vector - Vector2(self.game.screen_map.scroll)
                vector_to_mouse = Vector2(event.pos) - vector_player_display
                if not self.tool.right_button_click(vector_to_mouse):
                    self.set = True

        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.dig = False
            if event.button == 3:
                self.set = False
                self.eat = True
        # ========================================

    def set_spawn_point(self, point):
        self.spawn_point = point
        self.ui.new_sys_message("Точка дома установлена")

    def tp_to_home(self):
        self.tp_to(self.spawn_point)

    def tp_random(self):
        self.tp_to((random.randint(-1e9, 1e9), random.randint(-1e9, 1e9)))
        self.tp_to((random.randint(-1e9, 1e9), random.randint(-TSIZE*10000, TSIZE*10000)))
        # self.tp_to((2 ** 31 - 1500, 2 ** 31 - 1500))

    def tp_to(self, pos):
        self.rect.center = pos
        self.game.screen_map.teleport_to_player()
        self.vertical_momentum = 0

    def relive(self):
        self.alive = True
        self.inventory.discard_all_items()
        self.lives = self.max_lives
        self.rect.center = self.spawn_point
        self.jump_count = 0
        self.vertical_momentum = 0
        self.physical_vector = pg.Vector2(0, 0)
        self.first_fall = True
        self.moving_right = False
        self.moving_left = False
        print("relive", self.lives)

    def update(self, tact):
        self.tact = tact
        self.draw(self.ui.display)

        if not self.alive:
            return False
        if not self.sitting:
            self.moving()

        if not self.creative_mode:
            self.flying = False
        # SHOW PLAYER HAND ===============================================
        if self.num_down != -1:
            self.choose_active_cell(self.num_down)
            self.num_down = -1
        self.vector = Vector2(self.rect.center)
        vector_player_display = self.vector - Vector2(self.game.screen_map.scroll)
        vector_to_mouse = Vector2(pg.mouse.get_pos()) - vector_player_display

        item: Union[Items, ItemTool] = self.inventory[self.inventory.active_cell]
        if item is None or item.class_item & CLS_TOOL == 0:
            if self.creative_mode:
                self.tool = self.toolCreativeHand
            else:
                self.tool = self.toolHand
        else:
            self.tool = item.tool
        self.tool.update(vector_to_mouse)
        if self.dig:
            self.tool.left_button(vector_to_mouse)
        elif self.set:
            self.tool.right_button(vector_to_mouse)
        self.tool.draw(self.ui.display, vector_player_display.x, vector_player_display.y)
        if self.eat and item and item.class_item == CLS_EAT:
            if item.index == 55:
                self.max_lives += 20
            elif item.index == 351:
                if self.max_jump_count < 5:
                    self.max_jump_count += 1
            self.lives = min(self.lives + item.recovery_lives, self.max_lives)
            item.count -= 1
            if item.count <= 0:
                self.inventory[self.inventory.active_cell] = None
            self.inventory.redraw()
        self.eat = False

        # find and get ground items ==========================================
        self.get_item_rect.center = self.rect.center
        for tile in self.game.screen_map.dynamic_tiles:
            if tile.class_obj & OBJ_ITEM != 0:
                if self.get_item_rect.colliderect(tile):
                    res, cnt = self.inventory.put_to_inventory(tile)
                    if res:
                        tile.alive = False
                    else:
                        tile.count = cnt

        return True

    def draw_lives(self, surface, pos_obj):
        self.lives_surface.fill(f"#78716CAA")
        w = int((self.rect.w - 2) * (self.lives / self.max_lives))
        pg.draw.rect(self.lives_surface, "#A3E635AA", ((1, 1), (w, 4)))
        surface.blit(self.lives_surface, (pos_obj[0], pos_obj[1] - 10))

    def choose_active_cell(self, cell=-1):
        """Рисуем новую руку для игрока а также перерисвываем верхнее табло"""
        if cell != -1:
            self.inventory.active_cell = cell
        self.hand_img = hand_pass_img
        if self.inventory[self.inventory.active_cell]:
            if self.inventory[self.inventory.active_cell] is not None:
                self.hand_img = self.inventory[self.inventory.active_cell].sprite
        self.inventory.ui.redraw_top()

    def jump(self):
        if self.on_wall:
            self.vertical_momentum = -self.jump_speed
        elif self.air_timer < 6:
            self.jump_count += 1
            self.vertical_momentum = -self.jump_speed
        elif self.jump_count < self.max_jump_count:
            self.jump_count += 1
            self.vertical_momentum = -self.jump_speed * (self.jump_count * 0.25 + 1)
        elif self.creative_mode:
            self.vertical_momentum = -self.jump_speed * (self.jump_count * 0.25 + 1)

    def sit(self, pos=None):
        self.sitting = True
        self.vertical_momentum = 0
        if pos:
            self.rect.x, self.rect.bottom = pos

    def moving(self):
        player_movement = pg.Vector2(0, 0)
        if self.moving_right:
            self.flip = False
            if self.speed < 0:
                self.speed //= 2
            self.speed += self.accelerate_x
            if self.speed > self.max_speed:
                self.speed = self.max_speed
        elif self.moving_left:
            self.flip = True
            if self.speed > 0:
                self.speed //= 2
                if self.speed == -1: self.speed = 0
            self.speed -= self.accelerate_x
            if self.speed < -self.max_speed:
                self.speed = -self.max_speed
        else:
            self.speed //= 2
            if self.speed == -1: self.speed = 0
        player_movement[0] += self.speed
        player_movement[1] += self.vertical_momentum
        if self.flying:
            if self.on_up:
                self.vertical_momentum = -self.fly_speed
            elif self.on_down:
                self.vertical_momentum = self.fly_speed
            else:
                self.vertical_momentum = 0

        else:
            self.vertical_momentum += self.fall_speed

        # print(self.vertical_momentum)

        if self.vertical_momentum > self.max_fall_speed:
            self.vertical_momentum = self.max_fall_speed

        collisions = self.move(player_movement, self.game.screen_map.static_tiles)
        self.collisions_ttile = {col[1] for arrow in collisions for col in collisions[arrow]}
        if 120 in self.collisions_ttile:
            self.air_timer = 0
            self.jump_count = 0
            self.vertical_momentum /= 1.5
        elif {121, 125} & self.collisions_ttile:
            self.inventory.update_available_create_items()
        if collisions['bottom']:
            if not self.first_fall and self.vertical_momentum > 25:
                self.damage(int(self.vertical_momentum // 5))
            self.air_timer = 0
            self.jump_count = 0
            self.vertical_momentum = 0
            self.first_fall = False
        else:
            self.air_timer += 1
        if collisions['top']:
            self.vertical_momentum = 0
        self.on_wall = False
        if (collisions['left'] and self.moving_left) or (collisions['right'] and self.moving_right):
            if self.vertical_momentum > 0:
                self.vertical_momentum = 0
                self.jump_count = min(self.max_jump_count, self.jump_count)
                self.on_wall = True

    def draw(self, surface):
        scroll = self.game.screen_map.scroll
        player_display_pos = (min(WSIZE[0], max(-TSIZE, self.rect.x - scroll[0])),
                              min(WSIZE[0], max(-TSIZE, self.rect.y - scroll[1])))
        surface.blit(self.player_img, player_display_pos)
        # if self.lives != self.max_lives:
        self.draw_lives(surface, player_display_pos)

    def damage(self, lives):
        if self.creative_mode:
            return True
        if self.max_lives == -1:
            return True
        self.lives -= lives
        if self.lives <= 0:
            self.kill()
            return False
        return True

    def kill(self):
        self.alive = False
        self.inventory.ui.opened_full_inventory = False

    def discard(self, vector):
        # self.physical_vector.x += vector[0]
        # self.physical_vector.y += vector[1]
        pass

    def set_game_mode(self, creative_mode=False):
        # global self.creative_mode
        self.creative_mode = creative_mode
        self.game_map.creative_mode = creative_mode
        self.jump_count = 0
        if self.creative_mode:
            self.ui.new_sys_message("Режим создателя включен")
        else:
            self.ui.new_sys_message("Режим создателя выключен")
