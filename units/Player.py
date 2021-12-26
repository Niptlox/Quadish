from units.common import *
from pygame.locals import *
from pygame import Vector2
from units import Entitys
from time import time
from units.Tiles import PICKAXES_CAPABILITY, PICKAXES_SPEED, PICKAXES_STRENGTH, STANDING_TILES
from units.Tiles import hand_pass_img, player_img, dig_rect_img, tile_hand_imgs



class Player(Entitys.PhiscalObject):
    width, height = TILE_RECT
    player_img = player_img
    dig_rect_img = dig_rect_img
    hand_img = hand_pass_img

    def __init__(self, game, game_map, x, y) -> None:
        super().__init__(game_map, x, y, self.width, self.height)
        self.game = game
        self.ui = game.ui
        self.on_wall = False
        self.moving_right = False
        self.moving_left = False
        self.on_up = False                
        self.dig = False 
        self.dig_pos = None
        self.punch = False
        self.punch_tick = 0
        self.punch_speed = 0.8
        self.min_hand_space = TILE_SIZE // 1.5
        self.hand_space = self.min_hand_space
        self.num_down = -1

        self.vertical_momentum= 0
        self.jump_speed = 10
        self.jump_count = 0
        self.max_jump_count = 5
        self.fall_speed = 0.3 #* (60 / FPS)
        self.max_fall_speed = 7 #* (60 / FPS)
        self.player_speed = 4.1 * (WINDOW_SIZE[0] / 700) * (60 / FPS)
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
                if self.on_wall:
                    self.vertical_momentum = -self.jump_speed
                    
                elif self.air_timer < 6:
                    self.jump_count += 1
                    self.vertical_momentum = -self.jump_speed
                elif self.jump_count < self.max_jump_count:
                    self.jump_count += 1
                    self.vertical_momentum = -self.jump_speed
            # =========================================
            elif event.key == K_j and self.on_up:                    
                self.pickaxe = 77 if self.pickaxe == 1 else 1
            elif event.key == K_t:
                self.rect.center = (0, 0)
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
            if event.button == 1:
                self.dig = True
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.dig = False
        # ========================================
        elif event.type == MOUSEWHEEL:
            self.active_cell += event.y
            if self.active_cell == -1:
                self.active_cell = self.inventory_size - 1
            elif self.active_cell == self.inventory_size:
                self.active_cell = 0
            self.choose_active_cell()            

    def update(self):
        scroll = self.game.screen_map.scroll
        player_movement = [0,0]
        if self.moving_right:
            player_movement[0] += self.player_speed
        if self.moving_left:
            player_movement[0] -= self.player_speed
 
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
        
        self.ui.display.blit(self.player_img, (self.rect.x-scroll[0], self.rect.y-scroll[1]))

        # SHOW PLAYER HAND ===============================================

        pVec = Vector2(self.rect.centerx-scroll[0], self.rect.centery-scroll[1])
        mVec = Vector2(pygame.mouse.get_pos())
        
        hVec = mVec - pVec
        if self.dig:
            if hVec.length_squared() <= (TILE_SIZE * 2.5) ** 2:
                dig_pos = Vector2(scroll) + mVec
            else: 
                dig_pos = hVec.normalize() * TILE_SIZE * 1.2 + Vector2(self.rect.center)
        if hVec.length_squared() == 0:
            hVec = Vector2(1, 0)
            
        hVec.scale_to_length(self.hand_space)
        real_hVec = hVec + pVec - Vector2(HAND_SIZE//2, HAND_SIZE//2)

        if self.num_down != -1:
            self.choose_active_cell(self.num_down)
            self.num_down = -1
            
        self.ui.display.blit(self.hand_img, real_hVec)
        
        # DIG TILE =======================================================

        if self.dig:
            # dig = False
            px, py = int(dig_pos.x // TILE_SIZE), int(dig_pos.y // TILE_SIZE)
            
            new_punch = self.dig_tile(px, py)
            if new_punch is not None:
                self.ui.display.blit(self.dig_rect_img, (px * TILE_SIZE-scroll[0], py * TILE_SIZE-scroll[1]))
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

        

    def set_tile(self, x, y):        
        cell = self.inventory[self.active_cell]
        if time() - self.pickaxe_time < 1 or time() - self.set_time < 0.6 or cell is None:        
            return False
        ttile = self.inventory[self.active_cell][0]
        if ttile in STANDING_TILES and self.game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
            return False
        self.inventory[self.active_cell][1] -= 1
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
        d_ttile = self.game_map.get_static_tile_type(x, y-1)    
        if d_ttile in {101, 102}:
            return False
        ttile = tile[0]
        if ttile == 0:
            return self.set_tile(x, y)
        sol = tile[1] # прочность
        if time() - self.set_time < 1 or time() - self.pickaxe_time < 1 / PICKAXES_SPEED[self.pickaxe]:
            # время нового удара ещё не подошло
            return False
        self.pickaxe_time = time()
        if PICKAXES_CAPABILITY[self.pickaxe] is not None and ttile not in PICKAXES_CAPABILITY[self.pickaxe]:
            # мы не можем выкопать этой киркой
            return False
        stg = PICKAXES_STRENGTH[self.pickaxe]
        sol -= stg
        if sol <= 0:
            i = 0
            while i < self.inventory_size:
                if self.inventory[i] is None:
                    self.inventory[i] = [ttile, 1]
                    self.ui.redraw_top()
                    break
                if self.inventory[i][1] < self.cell_size and self.inventory[i][0] == ttile:
                    self.inventory[i][1] += 1
                    self.ui.redraw_top()
                    break
                i += 1
            else:
                print("Перепонен инвентарь", ttile)
            
            self.game_map.set_static_tile(x, y, None)
        else:
            self.game_map.set_static_tile_solidity(x, y, sol)
        self.choose_active_cell()
        return True

    def choose_active_cell(self, cell=-1):
        if cell != -1:
            self.active_cell = cell
        self.hand_img = hand_pass_img
        if self.inventory[self.active_cell]:
            self.hand_img = tile_hand_imgs[self.inventory[self.active_cell][0]]
        self.ui.redraw_top()

