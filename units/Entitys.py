from units.common import *
from units.Tiles import PHYSBODY_TILES, tnt_imgs
from math import sin, cos, pi

from units.map.GameMap import GameMap


def collision_test(game_map, rect: pygame.Rect, static_tiles: dict = {}, dynamic_tiles: list = [], first_tile_pos=(0, 0)):
    # rect_x_map, rect_y_map = rect.x // TILE_SIZE, rect. // 
    hit_dynamic_lst = []

    for tile in dynamic_tiles:
        if rect.colliderect(tile):
            hit_dynamic_lst.append(tile)

    hit_static_lst = []
    if static_tiles:
        rect = rect.move(-first_tile_pos[0], -first_tile_pos[1])
        vertexes = rect.topleft, (rect.left, rect.bottom - 1), (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1)

        for vertex in vertexes:
            # координаты угла в перещёте на блоки
            v_xy_map = v_x_map, v_y_map = (vertex[0] // TILE_SIZE, vertex[1] // TILE_SIZE)
            # if not(0 <= v_x_map < game_map.map_size[0] and 0 <= v_y_map < game_map.map_size[1]):
            #     hit_static_lst.append((v_xy_map, -1))
            if static_tiles.get(v_xy_map) in PHYSBODY_TILES:
                hit_static_lst.append((v_xy_map, static_tiles.get(v_xy_map)))
    return hit_static_lst, hit_dynamic_lst


class PhiscalObject:
    def __init__(self, game_map, x, y, width, height, use_physics=False) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.game_map: GameMap = game_map
        self.use_physics = use_physics
        if use_physics:
            self.fall_speed = FALL_SPEED
            self.max_fall_speed = MAX_FALL_SPEED
            self.vertical_momentum = 0
            self.movement_vector = pg.Vector2(0, 0)

    def set_vars(self, vrs):
        for k, i in vrs.items():
            self.__dict__[k] = i

    def move(self, movement, static_tiles: dict, dynamic_tiles: list = [], first_tile_pos=(0, 0)):
        collision_types = {'top': False, 'bottom': False, 'right': False, 'left': False}
        mx, my = movement
        self.rect.x += mx
        # блоки с которыми стлкунулись после премещения по оси x (hit_static_lst, hit_dynamic_lst )
        collision_lsts = collision_test(self.game_map, self.rect, static_tiles, dynamic_tiles, first_tile_pos)
        for type_coll in range(2):
            for block in collision_lsts[type_coll]:
                if mx > 0:
                    if type_coll == 0:
                        self.rect.right = block[0][0] * TILE_SIZE + first_tile_pos[0]
                    elif type_coll == 1:
                        self.rect.right = block.left
                    collision_types['right'] = True
                elif mx < 0:
                    if type_coll == 0:
                        self.rect.left = block[0][0] * TILE_SIZE + first_tile_pos[0] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.left = block.right
                    collision_types['left'] = True
        self.rect.y += my
        # блоки с которыми стлкунулись после премещения по оси y (hit_static_lst, hit_dynamic_lst )
        collision_lsts = collision_test(self.game_map, self.rect, static_tiles, dynamic_tiles, first_tile_pos)
        for type_coll in range(2):
            for block in collision_lsts[type_coll]:
                if my >= 0:
                    if type_coll == 0:
                        self.rect.bottom = block[0][1] * TILE_SIZE + first_tile_pos[1]
                    elif type_coll == 1:
                        self.rect.bottom = block.top
                    collision_types['bottom'] = True
                elif my < 0:
                    if type_coll == 0:
                        self.rect.top = block[0][1] * TILE_SIZE + first_tile_pos[1] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.top = block.bottom
                    collision_types['top'] = True
        return collision_types

    def update(self, tact):
        if self.use_physics:
            self.update_physics()

    def update_physics(self):
        cy = self.rect.y // (TSIZE * CSIZE)
        cx = self.rect.x // (TSIZE * CSIZE)
        self.movement_vector.y += self.fall_speed
        if self.movement_vector.y > self.max_fall_speed:
            self.movement_vector.y = self.max_fall_speed

        movement = (self.movement_vector.x, self.movement_vector.y)
        collisions = self.move(movement, self.game.screen_map.static_tiles)
        if collisions['bottom']:
            self.vertical_momentum = 0
            self.movement_vector.x //= 1.5
            self.movement_vector.y = 0
        if collisions['top']:
            self.movement_vector.y = 0
            self.movement_vector.x //= 1.5
        if collisions["left"] or collisions["right"]:
            self.movement_vector.x = 0
        new_cy = self.rect.y // (TSIZE * CSIZE)
        new_cx = self.rect.x // (TSIZE * CSIZE)
        if new_cy != cy or new_cx != cx:
            # print(self.rect.y, cy, new_cy)
            self.game_map.move_dinamic_obj(cx, cy, new_cx, new_cy, self)

    def draw(self, surface, pos):
        pygame.draw.rect(surface, (255, 255, 0), pos)


def create_circle_pattern(radius):
    r = radius
    a = [[0] * (2 * r + 1) for i in range(r * 2 + 1)]
    ar = set(())
    for ri in range(r + 1):
        i = 0
        while i < pi * 2:
            x, y = int(cos(i) * ri) + r, int(sin(i) * ri * 0.70) + r
            # print(x, y)
            a[y][x] = 1
            i += pi / (r * 10)
            ar.add((x, y))
    return ar


class Dynamite(PhiscalObject):
    boom_radius = 5
    pattern = create_circle_pattern(boom_radius)

    def __init__(self, game, game_map, x, y):
        print("d", x, y)
        super().__init__(game_map, x, y, TSIZE, TSIZE, use_physics=True)
        self.game = game
        self.arise_tact = -1  # такт повления
        self.last_tact = 0
        self.period = 10  # период мигания
        self.boom_tact = FPS * 2
        self.image_state = 0

    def draw(self, surface, pos):
        surface.blit(tnt_imgs[self.image_state], pos)

    def update(self, tact):
        if self.arise_tact == -1:
            self.arise_tact = tact
        if tact - self.arise_tact >= self.boom_tact:
            self.detonation_obj()
            return False
        if tact - self.last_tact >= self.period:
            self.last_tact = tact
            self.image_state ^= 1
            self.period -= 1
        self.update_physics()
        return True

    def detonation_obj(self):
        tx, ty = self.rect.x // TSIZE, self.rect.y // TSIZE
        d = self.boom_radius * 2 + 1
        for x, y in self.pattern:
            ix, iy = tx + x - self.boom_radius, ty + y - self.boom_radius
            if self.game_map.get_static_tile_type(ix, iy) == 9:  #tnt
                obj = Dynamite(self.game, self.game_map, ix * TSIZE, iy * TSIZE)
                self.game_map.add_dinamic_obj(*GameMap.to_chunk_xy(ix, iy), obj)
            self.game_map.set_static_tile(ix, iy, None)
        boom_rect = pg.Rect(0, 0, d*TSIZE, d*TSIZE)
        boom_rect.center = self.rect.center
        _, hit_dynamic_lst = collision_test(self.game_map, boom_rect, {}, self.game.screen_map.dynamic_tiles)
        # print(hit_dynamic_lst, self)
        for obj in hit_dynamic_lst:
            if obj is not self:
                if obj.rect.x != self.rect.x:
                    obj.movement_vector.x += 1 / ((obj.rect.x - self.rect.x) / TSIZE) * d
                if obj.rect.y != self.rect.y:
                    obj.movement_vector.y += 1 / ((obj.rect.y - self.rect.y) / TSIZE) * d
                else:
                    obj.movement_vector.y -= 2


