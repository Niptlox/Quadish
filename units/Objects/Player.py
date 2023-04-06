import random
from typing import Union

from pygame import Vector2
from pygame.locals import *

from units.Achievements import Achievements
from units.Graphics.Animation import get_death_animation
from units.Objects.Entity import PhysicalObject
from units.Inventory import InventoryPlayer
from units.Objects.Items import Items
from units.Graphics.Particle import DamageParticle
from units.Tiles import hand_pass_img, player_img, dig_rect_img
from units.Tools import ToolHand, ItemTool, ToolCreativeHand
from units.UI.BlocksUI import InventoryPlayerChestUI, InventoryPlayerFurnaceUI, BLOCKS_UI_SET
from units.sound import *
from units.common import *


# from units.Cursor import set_cursor, cursor_add_img, CURSOR_DIG, CURSOR_NORMAL, CURSOR_SET

class Player(PhysicalObject):
    not_save_vars = PhysicalObject.not_save_vars | {"game_map", "game", "ui", "hand_img", "lives_surface", "toolHand",
                                                    "toolCreativeHand", "tool", "chest_ui", "furnace_ui",
                                                    "inventory_ui", "achievements", "dig_rect", "dig_rect_img",
                                                    "dig_pos", "dig_dist", "set_dist", "set", "dig", "sitting", "moving_left",
                                                    "moving_right", "on_wall", "tact", "eat", "jump_speed", "max_speed",
                                                    "accelerate_x", "fall_speed", "max_fall_speed", "fly_speed"}
    class_obj = OBJ_PLAYER
    width, height = max(1, TSIZE - 10), max(1, TSIZE - 2)
    player_img = player_img
    dig_rect_img = dig_rect_img
    hand_img = hand_pass_img
    start_max_lives = 30
    max_max_lives = 600

    def __init__(self, game, x, y) -> None:

        if x == 777:
            x = random.randint(-1000 * TSIZE, 1000 * TSIZE)
        if y == 777:
            y = random.randint(-100 * TSIZE, 100 * TSIZE)
        # x = x + TSIZE // 2 - self.width // 2
        # y = y + (TSIZE - self.height) // 2
        super().__init__(game, x, y, self.width, self.height, use_physics=True)
        self.game = game
        self.active = True

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
        self.jump_speed = 0.275
        self.jump_count = 0
        self.max_jump_count = 2
        self.fall_speed = FALL_SPEED
        self.max_fall_speed = MAX_FALL_SPEED
        self.speed = 0
        self.accelerate_x = 0.06 # ускорение шага
        self.max_speed = 0.33
        self.running = True
        self.air_timer = 0
        self.first_fall = True
        self.fly_speed = 1.8
        self.flying = False
        self.on_up = False
        self.on_down = False

        self.achievements = Achievements(self)
        self.killer = ""
        # ANIMATION ============================

        self.death_animation = get_death_animation(self.rect.size)
        # INVENTORY ============================
        self.creative_mode = CREATIVE_MODE

        self.inventory = InventoryPlayer(self)
        self.inventory.redraw()

        self.flip = False
        self.toolHand = ToolHand(self)
        self.toolCreativeHand = ToolCreativeHand(self)
        self.tool = self.toolHand
        self.vector = Vector2(0)

        self.tile_ui = None

        # ====================================
        self.state_step_sound = 0

        # self.game_map.set_static_tile(0, 0, self.game_map.get_tile_ttile(131))
    def reinit(self):
        self.__init__(self.game, 0, 0)

    def set_vars(self, vrs):
        # self.inventory.set_vars(vrs.pop("inventory"))

        # vrs["max_fall_speed"] = self.max_fall_speed
        vrs["rect"].size = self.rect.size

        self.active = vrs.get("active", True)
        super().set_vars(vrs)
        self.fall_speed = FALL_SPEED
        self.inventory.redraw()
        self.game.screen_map.teleport_to_player()

    def pg_event(self, event):
        if self.inventory.pg_event(event):
            return True
        if event.type == EVENT_END_OF_STEP_SOUND:
            self.state_step_sound = 0
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
        self.tp_to((random.randint(-1e9, 1e9), random.randint(-TSIZE * 2000, TSIZE * 2000)))
        # self.tp_to((2 ** 31 - 1500, 2 ** 31 - 1500))

    def tp_to(self, pos):
        self.rect.center = pos[0] + TSIZE // 2, pos[1] + TSIZE // 2
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
        self.game_map.spawn_gate()
        self.tp_to_home()
        self.active = True
        self.death_animation.stop()
        print("relive", self.lives)

    def update(self, tact, elapsed_time):
        if not self.active:
            return True
        self.tact = tact
        self.death_animation.update(elapsed_time)
        self.draw(self.ui.display)

        if not self.alive:
            return False
        if not self.sitting:
            self.moving(elapsed_time)

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
        # self.tool.draw(self.ui.display, vector_player_display.x, vector_player_display.y)
        if self.eat and item and item.class_item == CLS_EAT:

            if item.index == 55:
                self.max_lives += 20
                get_random_sound_of(sounds_drink).play()
            elif item.index == 351:
                get_random_sound_of(sounds_drink).play()
                if self.max_jump_count < 5:
                    self.max_jump_count += 1
            else:
                get_random_sound_of(sounds_eat).play()
            if self.max_lives > self.max_max_lives:
                self.max_lives = self.max_max_lives
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
        if not self.achievements.is_completed("hell") and self.rect.y >= START_HELL_Y * TSIZE:
            self.achievements.new_completed("hell")
        if not self.achievements.is_completed("space") and self.rect.y <= START_SPACE_Y * TSIZE:
            self.achievements.new_completed("space")

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

    def moving(self, elapsed_time):
        player_movement = pg.Vector2(0, 0)
        if self.moving_right:
            # print(self.speed, self.accelerate_x)

            self.flip = False
            if self.speed < 0:
                self.speed /= 2
            self.speed += self.accelerate_x
            if self.speed > self.max_speed:
                self.speed = self.max_speed
        elif self.moving_left:
            # print("left", self.speed)
            self.flip = True
            if self.speed > 0:
                self.speed /= 2
                if self.speed == -1: self.speed = 0
            self.speed -= self.accelerate_x
            if self.speed < -self.max_speed:
                self.speed = -self.max_speed
        else:
            self.speed //= 2
            if self.speed == -1: self.speed = 0
        player_movement[0] += self.speed * elapsed_time
        player_movement[1] += self.vertical_momentum * elapsed_time
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

        # if self.game.blocks_ui_manager.opened:
        #     dist2 = (Vector2(self.game.blocks_ui_manager.opened.rect.center) - Vector2(self.rect.center)).length_squared()
        #     if dist2 > TSIZE * 16:
        #         self.game.blocks_ui_manager.close()
        #         self.inventory.ui.open()
        if collisions['bottom']:
            if not self.first_fall and self.vertical_momentum > 0.75:
                print(self.vertical_momentum)
                self.damage(int(self.vertical_momentum * 2) ** 2)
            self.air_timer = 0
            self.jump_count = 0
            self.vertical_momentum = 0
            self.first_fall = False
            if abs(self.speed) > 0 and self.state_step_sound == 0 or self.air_timer > FPS // 2:
                if 104 in self.collisions_ttile or collisions['bottom'][0][1] == 1:
                    step_sound = get_random_sound_of(sounds_step_dry).play()
                else:
                    step_sound = sounds_step_stomp.rplay()
                step_sound.set_endevent(EVENT_END_OF_STEP_SOUND)
                self.state_step_sound = 1

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

    def fin_step_sound(self):
        self.state_step_sound = 0

    def draw(self, surface):
        scroll = self.game.screen_map.scroll
        player_display_pos = (min(WSIZE[0], max(-TSIZE, self.rect.x - scroll[0])),
                              min(WSIZE[0], max(-TSIZE, self.rect.y - scroll[1])))
        surface.blit(self.player_img, player_display_pos)

        self.death_animation.draw(surface, player_display_pos)
        if self.tool:
            self.tool.draw(self.ui.display, player_display_pos[0] + self.rect.w // 2,
                           player_display_pos[1] + self.rect.h // 2)

        # if self.lives != self.max_lives:
        self.draw_lives(surface, player_display_pos)

    def damage(self, lives, owner="Unknown"):
        if self.creative_mode:
            return True
        particle = DamageParticle(self.game, (self.rect.centerx, self.rect.top - 26), (lives))
        self.game_map.add_particle(particle)
        self.death_animation.start()
        if self.max_lives == -1:
            return True
        self.lives -= lives
        if self.lives <= 0:
            self.kill()
            return False
        return True

    def kill(self, owner="Unknown"):
        self.alive = False
        self.killer = owner
        self.inventory.ui.opened = False

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
