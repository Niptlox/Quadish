from units.common import *
from units.Tiles import PHYSBODY_TILES


def collision_test(game_map, rect: pygame.Rect, static_tiles: dict, dynamic_tiles: list=[], first_tile_pos=(0, 0)):
    # rect_x_map, rect_y_map = rect.x // TILE_SIZE, rect. // 
    hit_dynamic_lst = []

    for tile in dynamic_tiles:
        if rect.colliderect(tile):
            hit_dynamic_lst.append(tile)

    hit_static_lst = []
    rect = rect.move(-first_tile_pos[0], -first_tile_pos[1])
    vertexes = rect.topleft, (rect.left, rect.bottom-1), (rect.right-1, rect.top), (rect.right-1, rect.bottom-1)
    
    for vertex in vertexes:
        # координаты угла в перещёте на блоки
        v_xy_map = v_x_map, v_y_map = (vertex[0] // TILE_SIZE, vertex[1] // TILE_SIZE)
        # if not(0 <= v_x_map < game_map.map_size[0] and 0 <= v_y_map < game_map.map_size[1]):
        #     hit_static_lst.append((v_xy_map, -1)) 
        if static_tiles.get(v_xy_map) in PHYSBODY_TILES:
            hit_static_lst.append((v_xy_map, static_tiles.get(v_xy_map)))
    return hit_static_lst, hit_dynamic_lst


class PhiscalObject:
    def __init__(self, game_map, x, y, width, height) -> None:
        self.rect: pygame.Rect = pygame.Rect(x, y, width, height)
        self.game_map = game_map
    
    def set_vars(self, vrs):
        for k, i in vrs.items():
            self.__dict__[k] = i

    def move(self, movement, static_tiles: dict, dynamic_tiles: list=[], first_tile_pos=(0, 0)):
        collision_types = {'top':False,'bottom':False,'right':False,'left':False}
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

    def draw(self):
        pygame.draw.rect(self.screen,(255,255,0),self.rect)
