from time import time

from pygame import Vector2
from pygame.locals import *

from units import Entity
from units.Items import Items, ItemsTile
from units.Texture import rot_center
# from units.Tiles import PICKAXES_CAPABILITY, PICKAXES_SPEED, PICKAXES_STRENGTH, STANDING_TILES, ITEM_TILES
from units.Tiles import hand_pass_img, player_img, dig_rect_img, tile_hand_imgs
from units.Tools import ToolHand, ToolSword, ItemSword, ItemPickaxe, TOOLS, ItemGoldPickaxe
from units.common import *


# from units.Cursor import set_cursor, cursor_add_img, CURSOR_DIG, CURSOR_NORMAL, CURSOR_SET


class Player(Entity.PhysicalObject):
    width, height = TSIZE - 2, TSIZE - 2
    player_img = player_img
    dig_rect_img = dig_rect_img
    hand_img = hand_pass_img
    max_lives = 20

    def __init__(self, game, x, y) -> None:
        super().__init__(game, x, y, self.width, self.height, use_physics=True)
        self.game = game
        self.ui = game.ui

        self.alive = True
        self.lives = self.max_lives
        self.lives_surface = pg.Surface((self.rect.w, 6)).convert_alpha()
        self.eat = False

        self.tact = 0
        self.on_wall = False
        self.moving_right = False
        self.moving_left = False
        self.on_up = False
        self.dig = False
        self.dig_pos = None
        self.dig_dist = 3
        self.set = False
        self.set_dist = 5
        self.auto_block_select = True

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
        self.max_jump_count = 4
        self.fall_speed = FALL_SPEED
        self.max_fall_speed = MAX_FALL_SPEED
        self.speed = 0
        self.accelerate_x = 2  # ускорение шага
        self.max_speed = 11
        self.running = True
        self.air_timer = 0

        # INVENTORY ============================        

        self.inventory_size = 16
        self.inventory = [None] * self.inventory_size
        # self.inventory[0] = ItemSword(self.game)
        self.inventory[0] = ItemPickaxe(self.game)
        self.inventory[0].set_owner(self)
        self.active_cell = 0
        self.cell_size = 1000

        self.flip = False
        self.toolHand = ToolHand(self)
        self.tool = None
        self.vector = Vector2(0)

    def get_vars(self):
        d = self.__dict__.copy()
        d.pop("game_map")
        d.pop("game")
        d.pop("ui")
        d.pop("hand_img")
        d.pop("lives_surface")
        d.pop("inventory")
        d.pop("toolHand")
        print(d)
        return d

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.fall_speed = FALL_SPEED

    def pg_event(self, event):
        if event.type == KEYDOWN:
            if event.key in (K_RIGHT, K_d):
                self.moving_right = True
            elif event.key in (K_LEFT, K_a):
                self.moving_left = True
            elif event.key in (K_UP, K_w, K_SPACE):
                self.on_up = True
                self.jump()
                # =========================================
            elif event.key == K_j and self.on_up:
                item = ItemGoldPickaxe(self.game)
                item.set_owner(self)
                self.put_to_inventory(item)
            elif event.key == K_t:
                self.rect.center = self.spawn_point
            elif event.key == K_h:
                self.spawn_point = self.rect.center
                print("Spawnpoint set:", self.spawn_point)
            elif event.key == K_q:  # удалить все предметы в текущей ячейке инвентаря
                self.discard_item(self.active_cell)
            elif event.key == K_e:
                self.creating_item_of_i(self.active_cell)
            elif event.key in NUM_KEYS:
                self.num_down = NUM_KEYS.index(event.key)
        elif event.type == KEYUP:
            if event.key in (K_RIGHT, K_d):
                self.moving_right = False
            elif event.key in (K_LEFT, K_a):
                self.moving_left = False
            elif event.key in (K_UP, K_w, K_SPACE):
                self.on_up = False
                # =========================================
        elif event.type == MOUSEBUTTONDOWN:
            if event.button in (1, 2):
                self.dig = True
            if event.button == 3:
                self.set = True
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.dig = False
            if event.button == 3:
                self.set = False
                self.eat = True
        # ========================================
        elif event.type == MOUSEWHEEL:
            self.active_cell -= event.y
            if self.active_cell <= -1:
                self.active_cell = self.inventory_size - 1
            elif self.active_cell >= self.inventory_size:
                self.active_cell = 0
            self.choose_active_cell()

    def update(self, tact):
        self.tact = tact
        if not self.alive:
            return False

        self.moving()

        # SHOW PLAYER HAND ===============================================
        if self.num_down != -1:
            self.choose_active_cell(self.num_down)
            self.num_down = -1
        self.vector = Vector2(self.rect.center)
        vector_player_display = self.vector - Vector2(self.game.screen_map.scroll)
        vector_to_mouse = Vector2(pg.mouse.get_pos()) - vector_player_display

        item = self.inventory[self.active_cell]
        if item is None or item.class_item & CLS_TOOL == 0:
            tool = self.toolHand
        else:
            tool = item.tool
        tool.update(vector_to_mouse)
        if self.dig:
            tool.left_button(vector_to_mouse)
        elif self.set:
            tool.right_button(vector_to_mouse)
        tool.draw(self.ui.display, vector_player_display.x, vector_player_display.y)
        if self.eat and item and item.class_item == CLS_EAT:
            if item.index == 55:
                self.max_lives += 20
            self.lives = min(self.lives + item.recovery_lives, self.max_lives)
            item.count -= 1
            if item.count <= 0:
                self.inventory[self.active_cell] = None
            self.choose_active_cell()
        self.eat = False

        # find and get ground items ==========================================
        self.get_item_rect.center = self.rect.center
        for tile in self.game.screen_map.dynamic_tiles:
            if tile.class_obj & OBJ_ITEM != 0:
                if self.get_item_rect.colliderect(tile):
                    res, cnt = self.put_to_inventory(tile)
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

    def discard_item(self, num_cell=None, items=None):
        if num_cell is not None:
            items = self.inventory[num_cell]
            self.inventory[num_cell] = None
            self.choose_active_cell()
        if items:
            ix, iy = self.rect.centerx + TSIZE * 2, self.rect.centery
            items.rect.x, items.rect.y = ix, iy
            items.alive = True
            print(ix, iy, *self.game_map.to_chunk_xy(ix // TSIZE, iy // TSIZE), items)
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(ix // TSIZE, iy // TSIZE), items)

    def put_to_inventory(self, items):
        i = 0
        while i < self.inventory_size:
            if self.inventory[i] and self.inventory[i].count < self.cell_size and \
                    self.inventory[i].index == items.index:
                free_place = self.cell_size - self.inventory[i].count
                if items.count > free_place:
                    self.inventory[i].count += free_place
                    items.count -= free_place
                else:
                    self.inventory[i].count += items.count
                    break
            i += 1
        else:
            i = 0
            while i < self.inventory_size:
                if self.inventory[i] is None:

                    if items.count < self.cell_size:
                        self.inventory[i] = items
                    else:
                        self.inventory[i] = items.copy()
                        self.inventory[i].count = self.cell_size
                        items.count -= self.cell_size
                        continue
                    break
                i += 1
            else:
                # print("Перепонен инвентарь", ttile)
                self.choose_active_cell()
                # self.ui.redraw_top()
                return False, items.count
        # self.ui.redraw_top()
        self.choose_active_cell()
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
        return True

    def check_creating_item_of_i(self, rec_i):
        if rec_i < len(RECIPES):
            out, need = RECIPES[rec_i]
            for t, c in need:
                if c == -1:
                    # косаемся ли мы нужного блока
                    hit_static_lst, _ = Entity.collision_test(self.game_map, self.rect,
                                                              self.game.screen_map.static_tiles, collide_all_tiles=True)
                    if any([e[1] == t for e in hit_static_lst]):
                        continue
                elif self.find_in_inventory(t, c):
                    continue
                return False
            return True
        return False

    def creating_item_of_i(self, rec_i):
        if self.check_creating_item_of_i(rec_i):
            out, need = RECIPES[rec_i]
            [self.get_from_inventory(t, c) for t, c in need]
            if out[0] in TOOLS:
                item = TOOLS[out[0]](self.game)
                item.set_owner(self)
            else:
                item = ItemsTile(self.game, out[0], count=out[1])
            res, _ = self.put_to_inventory(item)  # дверь
            if not res:
                self.discard_item(None, item)

    def choose_active_cell(self, cell=-1):
        if cell != -1:
            self.active_cell = cell
        self.hand_img = hand_pass_img
        if self.inventory[self.active_cell]:
            if self.inventory[self.active_cell] is not None:
                self.hand_img = self.inventory[self.active_cell].sprite
        self.ui.redraw_top()

    def jump(self):
        if self.on_wall:
            self.vertical_momentum = -self.jump_speed
        elif self.air_timer < 6:
            self.jump_count += 1
            self.vertical_momentum = -self.jump_speed
        elif self.jump_count < self.max_jump_count:
            self.jump_count += 1
            self.vertical_momentum = -self.jump_speed * (self.jump_count * 0.25 + 1)

    def moving(self):
        player_movement = pg.Vector2(0, 0)
        if self.moving_right:
            if self.speed < 0:
                self.speed //= 2
            self.speed += self.accelerate_x
            if self.speed > self.max_speed:
                self.speed = self.max_speed
        elif self.moving_left:
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
        self.vertical_momentum += self.fall_speed
        if self.vertical_momentum > self.max_fall_speed:
            self.vertical_momentum = self.max_fall_speed

        collisions = self.move(player_movement, self.game.screen_map.static_tiles)

        if collisions['bottom']:
            self.air_timer = 0
            self.jump_count = 0
            self.vertical_momentum = 0
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
        scroll = self.game.screen_map.scroll
        player_display_pos = (min(WSIZE[0], max(-TSIZE, self.rect.x - scroll[0])),
                              min(WSIZE[0], max(-TSIZE, self.rect.y - scroll[1])))
        self.ui.display.blit(self.player_img, player_display_pos)
        # if self.lives != self.max_lives:
        self.draw_lives(self.ui.display, player_display_pos)

    def damage(self, lives):
        if self.max_lives == -1:
            return True
        self.lives -= lives
        if self.lives <= 0:
            self.kill()
            return False
        return True

    def kill(self):
        self.alive = False

    def discard(self, vector):
        # self.physical_vector.x += vector[0]
        # self.physical_vector.y += vector[1]
        pass
