from os import name
from units.common import *
from pygame.locals import *
from units import Entitys
from units.map import ScreenMap, GameMap
from units.UI import GameUI
from time import time
from units.Tiles import PICKAXES_CAPABILITY, PICKAXES_SPEED, PICKAXES_STRENGTH, STANDING_TILES, hand_pass_img



class Player(Entitys.PhiscalObject):
    width, height = TILE_RECT
    def __init__(self, game, game_map, x, y) -> None:
        super().__init__(game_map, x, y, self.width, self.height)
        self.game = game
        self.ui = game.ui
        self.on_wall = False
        self.moving_right = False
        self.moving_left = False
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
        

        

    def set_tile(self, x, y):        
        cell = self.inventory[self.active_cell]
        if time() - self.pickaxe_time < 1 or time() - self.set_time < 0.6 or cell is None:        
            return False
        ttile = self.inventory[active_cell][0]
        if ttile in STANDING_TILES and self.game_map.get_static_tile_type(x, y + 1, 0) in STANDING_TILES:
            return False
        self.inventory[active_cell][1] -= 1
        self.game_map.set_static_tile(x, y, self.game_map.get_tile_ttile(ttile))
        if self.inventory[active_cell][1] == 0:
            self.inventory[active_cell] = None
        self.choose_active_cell()
        self.ui.redraw_top()    
        set_time = time()
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
        pickaxe_time = time()
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
                    self.redraw_top()
                    break
                if self.inventory[i][1] < self.cell_size and self.inventory[i][0] == ttile:
                    self.inventory[i][1] += 1
                    self.redraw_top()
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
        global active_cell, player_hand_img
        if cell != -1:
            active_cell = cell
        player_hand_img = hand_pass_img
        if self.inventory[self.active_cell]:
            player_hand_img = self.tile_hand_imgs[self.inventory[active_cell][0]]
        self.ui.redraw_top()

    def pg_event(self, event):
        if event.type == KEYDOWN:
            if event.key in (K_RIGHT, K_d):
                self.moving_right = True
            elif event.key in (K_LEFT, K_a):
                self.moving_left = True
            elif event.key in (K_UP, K_w, K_SPACE):
                
                if self.on_wall:
                    self.vertical_momentum = -self.jump_speed
                    
                elif self.air_timer < 6:
                    self.jump_count += 1
                    self.vertical_momentum = -self.jump_speed
                elif self.jump_count < self.max_jump_count:
                    self.jump_count += 1
                    self.vertical_momentum = -self.jump_speed
            # =========================================
            elif event.key == K_j:                    
                self.pickaxe = 77 if self.pickaxe == 1 else 1
            elif event.key == K_t:
                self.self.rect.center = (0, 0)
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

class App:
    screen = screen_
    

class Game(App):        
    def __init__(self) -> None:
        self.clock = pg.time.Clock()
        self.game_map = GameMap.GameMap(generate_type)
        self.display = display_
        self.ui = GameUI(self)
        self.player = Player(self, self.game_map, 0, 0)        
        self.screen_map = ScreenMap.ScreenMap(self.display, self.game_map, self.player)        
        self.running= True
        self.ui.init_ui()

    def pg_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False            
            elif event.type == KEYDOWN:
                if event.key == K_u:
                    pause = not pause
                elif event.key == K_o:
                    self.game_map.load_game_map(active_cell)
                elif event.key == K_p:
                    self.game_map.save_game_map(active_cell) 
                               
            elif event.type == EVENT_100_MSEC:
                if show_info_menu:
                    self.ui.redraw_info()
            self.player.pg_event(event)


    def main(self):
        while self.running:
            self.ui.draw_sky()
            self.update()
            self.pg_events()
            self.ui.draw()
            self.clock.tick(FPS)

    def update(self):
        self.screen_map.update()



