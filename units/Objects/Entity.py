from units.Tiles import PHYSBODY_TILES, SEMIPHYSBODY_TILES
from units.common import *


# from units.Map.GameMap import GameMap

def collision_test(game_map, rect: pygame.Rect, static_tiles: dict = {}, dynamic_tiles: list = [],
                   first_tile_pos=(0, 0), collide_all_tiles=False, semiphysbody=False):
    """collide_all_tiles: True - если надо соприкосновение не только с физическими блоками по умолч False"""
    # rect_x_map, rect_y_map = rect.x // TILE_SIZE, rect. // 
    hit_dynamic_lst = []

    for tile in dynamic_tiles:
        if rect.colliderect(tile):
            hit_dynamic_lst.append(tile)

    hit_static_lst = []
    # static_tiles = []
    semiphysbody_lst = []
    if static_tiles:
        rect = rect.move(-first_tile_pos[0], -first_tile_pos[1])

        if rect.w > TSIZE or rect.h > TSIZE:
            vertexes = [(rect.right - 1, rect.top), (
                rect.right - 1, rect.bottom - 1)]
            x, y = rect.topleft
            for i in range(0, rect.w - 1, TSIZE - 1):
                for j in range(0, rect.h - 1, TSIZE - 1):
                    vertexes.append((x + i, y + j))
            for i in range(0, rect.w - 1, TSIZE - 1):
                vertexes.append((x + i, rect.bottom - 1))
            for j in range(0, rect.h - 1, TSIZE - 1):
                vertexes.append((rect.right - 1, y + j))
        else:
            vertexes = [rect.topleft, (rect.left, rect.bottom - 1), (rect.right - 1, rect.top), (
                rect.right - 1, rect.bottom - 1)]

        for vertex in vertexes:
            # координаты угла в перещёте на блоки
            v_xy_map = v_x_map, v_y_map = (vertex[0] // TILE_SIZE, vertex[1] // TILE_SIZE)
            # if not(0 <= v_x_map < game_map.map_size[0] and 0 <= v_y_map < game_map.map_size[1]):
            #     hit_static_lst.append((v_xy_map, -1))
            if static_tiles.get(v_xy_map) in PHYSBODY_TILES or collide_all_tiles:
                hit_static_lst.append((v_xy_map, static_tiles.get(v_xy_map)))
            elif semiphysbody and static_tiles.get(v_xy_map) in SEMIPHYSBODY_TILES:
                semiphysbody_lst.append((v_xy_map, static_tiles.get(v_xy_map)))
    if semiphysbody:
        return hit_static_lst, hit_dynamic_lst, semiphysbody_lst
    return hit_static_lst, hit_dynamic_lst


class PhysicalObject(SavedObject):
    not_save_vars = SavedObject.not_save_vars | {"game_map", "game", "sprite", "full_sprite", "inv_sprite"}
    class_obj = OBJ_NONE
    sprite = None
    max_lives = -1
    index = 0
    count = 0

    def __init__(self, game, x=0, y=0, width=0, height=0, use_physics=False, sprite=None,
                 use_collisions=False, use_gravity=False) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.chunk_pos = self.update_chunk_pos()
        self.game = game
        self.game_map = game.game_map
        self.sprite = sprite
        self.lives = self.max_lives
        self.alive = True
        self.use_physics = use_physics
        self.use_collisions = use_collisions or use_physics
        self.use_gravity = use_gravity or use_physics
        # if use_physics:

        self.fall_speed = FALL_SPEED
        self.max_fall_speed = MAX_FALL_SPEED
        self.vertical_momentum = 0
        self.movement_vector = pg.Vector2(0, 0)
        self.physical_vector = pg.Vector2(0, 0)
        self.collisions = {}

    # def get_vars(self):
    #     d = self.__dict__.copy()
    #     d.pop("game_map")
    #     d.pop("game")
    #     # dell all Surfaces
    #     for k in [k for k, i in d.items() if
    #               type(i) in {pg.Surface, PhysicalObject} or (type(i) is list and i and type(i[0]) is pg.Surface)]:
    #         d.pop(k)
    #     return d

    def move(self, movement, static_tiles: dict, dynamic_tiles: list = [], first_tile_pos=(0, 0)):
        collision_types = {'top': [], 'bottom': [], 'right': [], 'left': [], 'semiphysbody': []}
        mx, my = movement
        self.rect.x += mx
        # блоки с которыми стлкунулись после премещения по оси x (hit_static_lst, hit_dynamic_lst )
        *collision_lsts, semiphysbody_lst = collision_test(self.game_map, self.rect, static_tiles, dynamic_tiles,
                                                           first_tile_pos, semiphysbody=True)
        collision_types["semiphysbody"] = semiphysbody_lst
        for type_coll in range(2):
            collision_lst_t = collision_lsts[type_coll]
            for block in collision_lsts[type_coll]:
                if mx > 0:
                    if type_coll == 0:
                        self.rect.right = block[0][0] * TILE_SIZE + first_tile_pos[0]
                    elif type_coll == 1:
                        self.rect.right = block.left
                    collision_types['right'] = collision_lst_t
                elif mx < 0:
                    if type_coll == 0:
                        self.rect.left = block[0][0] * TILE_SIZE + first_tile_pos[0] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.left = block.right
                    collision_types['left'] = collision_lst_t
                if type_coll == 0 and block[1] == 103:
                    self.damage(1)
        self.rect.y += my
        # блоки с которыми стлкунулись после премещения по оси y (hit_static_lst, hit_dynamic_lst )
        *collision_lsts, semiphysbody_lst = collision_test(self.game_map, self.rect, static_tiles, dynamic_tiles,
                                                           first_tile_pos, semiphysbody=True)
        collision_types["semiphysbody"] += semiphysbody_lst
        for type_coll in range(2):
            collision_lst_t = collision_lsts[type_coll]
            for block in collision_lsts[type_coll]:
                if my >= 0:
                    if type_coll == 0:
                        self.rect.bottom = block[0][1] * TILE_SIZE + first_tile_pos[1]
                    elif type_coll == 1:
                        self.rect.bottom = block.top
                    collision_types['bottom'] = collision_lst_t
                elif my < 0:
                    if type_coll == 0:
                        self.rect.top = block[0][1] * TILE_SIZE + first_tile_pos[1] + TILE_SIZE
                    elif type_coll == 1:
                        self.rect.top = block.bottom
                    collision_types['top'] = collision_lst_t
                if type_coll == 0 and block[1] == 103:
                    self.damage(1)
        return collision_types

    def not_collisions_move(self, movement):
        self.rect.x += movement[0]
        self.rect.y += movement[1]

    def update(self, tact, elapsed_time):
        if not self.alive:
            return False
        self.update_physics(elapsed_time)
        return True

    def update_physics(self, elapsed_time):
        if self.use_gravity:
            self.physical_vector.y += self.fall_speed * elapsed_time
            if self.physical_vector.y > self.max_fall_speed:
                self.physical_vector.y = self.max_fall_speed
        movement = (self.physical_vector + self.movement_vector).xy
        if self.use_collisions:
            collisions = self.move(movement, self.game.screen_map.static_tiles)
            self.collisions = collisions
            if collisions['bottom']:
                self.vertical_momentum = 0
                self.physical_vector.x = int(self.physical_vector.x / 2)
                self.physical_vector.y = 0
            if collisions['top']:
                self.physical_vector.y = 0
                self.physical_vector.x = int(self.physical_vector.x / 2)
            if collisions["left"] or collisions["right"]:
                self.physical_vector.x = 0
            new_cy = self.rect.y // (TSIZE * CSIZE)
            new_cx = self.rect.x // (TSIZE * CSIZE)

            if self.chunk_pos[1] != new_cy or new_cx != self.chunk_pos[0]:
                if not (self.class_obj & OBJ_PARTICLE):
                    self.game_map.move_dinamic_obj(*self.chunk_pos, new_cx, new_cy, self)
                self.chunk_pos = (new_cx, new_cy)
        else:
            self.not_collisions_move(movement)
        self.movement_vector.xy = (0, 0)

    def update_chunk_pos(self):
        self.chunk_pos = (self.rect.x // (TSIZE * CSIZE), self.rect.y // (TSIZE * CSIZE))
        return self.chunk_pos

    def draw(self, surface, pos):
        if show_entity_border:
            pygame.draw.rect(surface, "red", (pos, self.rect.size), width=1)
        surface.blit(self.sprite, pos)

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
        self.physical_vector.x += vector[0]
        self.physical_vector.y += vector[1]
