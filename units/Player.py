from units.common import *
from pygame.locals import *
from pygame import Vector2
from units import Entitys
from time import time
from units.Tiles import PICKAXES_CAPABILITY, PICKAXES_SPEED, PICKAXES_STRENGTH, STANDING_TILES
from units.Tiles import hand_pass_img, player_img, dig_rect_img, tile_hand_imgs
from units.Cursor import set_cursor, cursor_add_img, CURSOR_DIG, CURSOR_NORMAL, CURSOR_SET


class Player(Entitys.PhiscalObject):
    width, height = TSIZE - 2, TSIZE - 2
    player_img = player_img
    dig_rect_img = dig_rect_img
    hand_img = hand_pass_img

    def __init__(self, game, x, y) -> None:
        super().__init__(game, x, y, self.width, self.height, use_physics=True)
        self.game = game
        self.ui = game.ui
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

        self.punch = False
        self.punch_tick = 0
        self.punch_speed = 0.8
        self.min_hand_space = TILE_SIZE // 1.5
        self.hand_space = self.min_hand_space
        self.num_down = -1

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
        self.active_cell = 0
        self.cell_size = 100

        self.pickaxe = 1
        self.pickaxe_time = 0
        # время последнего удара
        self.set_time = 0
        # время последнего установки блока

    def get_vars(self):
        d = self.__dict__.copy()
        d.pop("game_map")
        d.pop("game")
        d.pop("ui")
        d.pop("hand_img")
        return d

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
                self.pickaxe = 77 if self.pickaxe == 1 else 1
            elif event.key == K_t:
                self.rect.center = self.spawn_point
            elif event.key == K_h:
                self.spawn_point = self.rect.center
                print("Spawnpoint set:", self.spawn_point)
            elif event.key == K_q:  # удалить все предметы в текущей ячейке инвентаря
                self.inventory[self.active_cell] = None
                self.choose_active_cell()
            elif event.key == K_e:
                if self.get_from_inventory(11, 1):  # дерево
                    self.put_to_inventory(123, 1)  # дверь
            elif event.key == K_l:
                if self.find_in_inventory(11, 1) and self.find_in_inventory(4, 1):  # дерево and blore
                    self.get_from_inventory(11, 1), self.get_from_inventory(4, 1)
                    self.put_to_inventory(9, 2)  # tnt
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
            print(event.button)
            if event.button in (1, 2):
                self.dig = True
            if event.button == 3:
                self.set = True
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.dig = False
            if event.button == 3:
                self.set = False
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
        scroll = self.game.screen_map.scroll
        player_movement = [0, 0]
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

        self.ui.display.blit(self.player_img, (self.rect.x - scroll[0], self.rect.y - scroll[1]))

        # SHOW PLAYER HAND ===============================================

        pVec = Vector2(self.rect.centerx - scroll[0], self.rect.centery - scroll[1])
        mVec = Vector2(pygame.mouse.get_pos())
        # вектор от плеера до мышки
        hVec = mVec - pVec
        # мышь в серединк игрока
        hVec_len_sqr = hVec.length_squared()
        if hVec_len_sqr == 0:
            hVec = Vector2(1, 0)
            hVec_len_sqr = 1
        hVec_norm = hVec.normalize()

        # координаты руки для отрисовки    
        real_hVec = hVec_norm * self.hand_space + pVec - Vector2(HAND_SIZE // 2, HAND_SIZE // 2)

        if self.num_down != -1:
            self.choose_active_cell(self.num_down)
            self.num_down = -1

        self.ui.display.blit(self.hand_img, real_hVec)

        # DIG TILE =======================================================
        cursor = CURSOR_NORMAL
        cursor_block_id = -1
        dig_in_dist = set_in_dist = False
        if self.inventory[self.active_cell] is None:
            if hVec_len_sqr <= (TILE_SIZE * self.dig_dist) ** 2:
                dig_in_dist = True  # можно копать на тек растянии
                cursor = CURSOR_DIG
        else:
            if hVec_len_sqr <= (TILE_SIZE * self.set_dist) ** 2:
                set_in_dist = True  # можно ставить на тек растянии
                cursor_block_id = 1000 + self.inventory[self.active_cell][0]
                cursor = None

        new_punch = None
        if self.set:
            if set_in_dist:
                #  or hVec_len_sqr <= (TILE_SIZE * self.set_dist) ** 2 убрано тк мы ставим только если в руке есть блок
                # мышка в радиусе для копки
                set_pos = Vector2(scroll) + mVec
            elif self.auto_block_select:
                # копаем самй ближ длок в сторону мышки
                set_pos = hVec_norm * TILE_SIZE * 1.2 + Vector2(self.rect.center)
            else:
                set_pos = None

            px, py = int(set_pos.x // TILE_SIZE), int(set_pos.y // TILE_SIZE)

            new_punch = self.set_tile(px, py)
        elif self.dig:
            if dig_in_dist or hVec_len_sqr <= (TILE_SIZE * self.dig_dist) ** 2:
                # мышка в радиусе для копки
                dig_pos = Vector2(scroll) + mVec
                cursor = CURSOR_DIG
            elif self.auto_block_select:
                # копаем самй ближ длок в сторону мышки
                dig_pos = hVec_norm * TILE_SIZE * 1.2 + Vector2(self.rect.center)
                cursor = CURSOR_DIG
            else:
                dig_pos = None
            if dig_pos:
                px, py = int(dig_pos.x // TILE_SIZE), int(dig_pos.y // TILE_SIZE)
                new_punch = self.dig_tile(px, py)

        if new_punch is not None:
            self.ui.display.blit(self.dig_rect_img, (px * TILE_SIZE - scroll[0], py * TILE_SIZE - scroll[1]))

        if new_punch:
            self.punch = True
            self.punch_tick = 0
            self.hand_space = self.min_hand_space
        if self.punch:
            self.punch_tick += 1
            if self.punch_tick < 10:
                self.hand_space += self.punch_speed
            elif self.punch_tick > 20:
                self.punch = False
                self.punch_tick = 0
                self.hand_space = self.min_hand_space
            else:
                self.hand_space -= self.punch_speed
        if cursor is not None:
            set_cursor(cursor)
        elif cursor_block_id != -1:
            cursor_add_img(self.hand_img, cursor_block_id)

    def set_tile(self, x, y):
        tile = self.game_map.get_static_tile(x, y)
        if tile is None or tile[0] != 0:
            return
        cell = self.inventory[self.active_cell]
        if time() - self.set_time < 0.3 or cell is None:
            return False
        ttile = self.inventory[self.active_cell][0]
        if ttile in STANDING_TILES and self.game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
            return False
        self.inventory[self.active_cell][1] -= 1
        if ttile == 9:  # tnt
            obj = Entitys.Dynamite(self.game, x * TSIZE, y * TSIZE)
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(x, y), obj)
        else:
            self.game_map.set_static_tile(x, y, self.game_map.get_tile_ttile(ttile))
        if self.inventory[self.active_cell][1] == 0:
            self.inventory[self.active_cell] = None
        self.choose_active_cell()
        self.ui.redraw_top()
        self.set_time = time()
        return True

    def dig_tile(self, x, y):
        tile = self.game_map.get_static_tile(x, y)
        if tile is None or tile[1] == -1:
            return
        d_ttile = self.game_map.get_static_tile_type(x, y - 1)
        if d_ttile in {101, 102}:
            return False
        ttile = tile[0]
        count_items = 1
        if ttile == 0:
            return  # self.set_tile(x, y)
        sol = tile[1]  # прочность
        if time() - self.pickaxe_time < 1 / PICKAXES_SPEED[self.pickaxe]:
            # время нового удара ещё не подошло
            return False
        self.pickaxe_time = time()
        if PICKAXES_CAPABILITY[self.pickaxe] is not None and ttile not in PICKAXES_CAPABILITY[self.pickaxe]:
            # мы не можем выкопать этой киркой
            return False
        if ttile == 102:  # smalltree_img
            ttile = 11  # wood_img
            count_items = 5
        stg = PICKAXES_STRENGTH[self.pickaxe]
        sol -= stg
        if sol <= 0:

            self.put_to_inventory(ttile, count_items)
            self.game_map.set_static_tile(x, y, None)
        else:
            self.game_map.set_static_tile_solidity(x, y, sol)
        self.choose_active_cell()
        return True

    def put_to_inventory(self, ttile, count=1):
        i = 0
        while i < self.inventory_size:
            if self.inventory[i] is None:
                self.inventory[i] = [ttile, min(count, self.cell_size)]
                if count > self.cell_size:
                    count -= self.cell_size
                    continue
                break
            if self.inventory[i][1] < self.cell_size and self.inventory[i][0] == ttile:
                free_place = self.cell_size - self.inventory[i][1]
                if count > free_place:
                    self.inventory[i][1] += free_place
                    count -= free_place
                else:
                    self.inventory[i][1] += count
                    break
            i += 1
        else:
            print("Перепонен инвентарь", ttile)
        self.ui.redraw_top()

    def find_in_inventory(self, ttile, count=1):
        all_cnt = 0
        for i in filter(lambda x: x, self.inventory):
            tt, ct = i[:2]
            if tt == ttile:
                all_cnt += ct
                if all_cnt >= count:
                    return True
        return False

    def get_from_inventory(self, ttile, count):
        if not self.find_in_inventory(ttile, count):
            return False
            # мы знаем что ttile есть в инвенторе
        for i in range(self.inventory_size):
            if self.inventory[i]:
                tt, ct = self.inventory[i][:2]
                if tt == ttile:
                    if ct <= count:
                        count -= ct
                        self.inventory[i] = None
                    else:
                        self.inventory[i][1] -= count
                        break
        return True

    def choose_active_cell(self, cell=-1):
        if cell != -1:
            self.active_cell = cell
        self.hand_img = hand_pass_img
        if self.inventory[self.active_cell]:
            self.hand_img = tile_hand_imgs[self.inventory[self.active_cell][0]]
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
