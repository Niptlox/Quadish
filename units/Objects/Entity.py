from units.Map.TileFlags import TILE_FLAG_BITS, BIT_PHYSBODY, BIT_SEMIPHYSBODY
from units.Tiles import DAMAGE_TILES, WATER_TILE, water_frame_level
from units.common import *

# От чего спасает зелье несгораемости — от жара. Кактус (103) сюда не входит:
# от колючки зелье не помогает, это не огонь.
FIREPROOF_TILES = frozenset({140})


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
            ttile = static_tiles.get(v_xy_map)
            # обычные int, а не IntFlag: `&` у enum идёт через __call__/__new__
            # и в профиле был дороже самой физики (см. TileFlags.TILE_FLAG_BITS)
            flags = TILE_FLAG_BITS.get(ttile, 0)
            if flags & BIT_PHYSBODY or collide_all_tiles:
                hit_static_lst.append((v_xy_map, ttile))
            elif semiphysbody and flags & BIT_SEMIPHYSBODY:
                semiphysbody_lst.append((v_xy_map, ttile))
    if semiphysbody:
        return hit_static_lst, hit_dynamic_lst, semiphysbody_lst
    return hit_static_lst, hit_dynamic_lst


class PhysicalObject(SavedObject):
    not_save_vars = SavedObject.not_save_vars | {"game_map", "game", "sprite", "full_sprite", "inv_sprite",
                                                 "_collision_tiles", "_collision_dynamic"}
    class_obj = OBJ_NONE
    sprite = None
    max_lives = -1
    index = 0
    count = 0
    # Тайлы, урон от которых этому существу нипочём: бес живёт в аду и не
    # может гореть в лаве — иначе адские мобы вымирали бы сами, в собственном
    # биоме, ещё до встречи с игроком.
    immune_tiles = frozenset()
    # Откуда брать окружение для коллизий. None — из ScreenMap: кадр всё равно
    # строит эту карту для отрисовки, и брать её бесплатно. За экраном
    # ScreenMap про эти тайлы не знает, поэтому GameMap.tick_offscreen на время
    # вызова подставляет здесь маленькую локальную выборку вокруг сущности.
    # Классовые атрибуты, а не поля: пока их никто не подставил, в __dict__ их
    # нет и в сохранение они не попадают.
    _collision_tiles = None
    _collision_dynamic = None

    def collision_tiles(self):
        """Словарь {(tx, ty): тип} для проверки столкновений."""
        tiles = self._collision_tiles
        return self.game.screen_map.static_tiles if tiles is None else tiles

    def effect_immunity(self):
        """Опасные тайлы, от которых защищает действующий эффект.

        Через множество, а не через правку `immune_tiles`: класс общий на всех
        существ этого вида, и приписанная в него лава осталась бы у всех и
        навсегда (docs/EFFECTS в units/Effects.py — то же правило).
        """
        effects = getattr(self, "effects", None)
        if effects is None:
            return frozenset()
        from units.Effects import FIREPROOF
        return FIREPROOF_TILES if effects.has(FIREPROOF) else frozenset()

    def in_water(self, offset_y=0):
        """Погружён ли центр тела в воду (docs/WATER.md).

        Не по столкновениям, а чтением тайла: столкновение с водой
        регистрируется только в тот кадр, когда rect действительно сдвинулся, а
        висящий в воде объект двигается на доли пикселя и в половине кадров
        «воды не касается». На этой же грабле уже стояли блоровая дорожка и
        гусеничный краулер.

        Уровень заполнения учитываем: плёнка на дне тайла — это лужа, по ней
        ходят, а не плывут.
        """
        tile = self.game_map.get_static_tile(self.rect.centerx // TSIZE,
                                             (self.rect.centery + offset_y) // TSIZE,
                                             create_chunk=False)
        if tile is None or tile[0] != WATER_TILE:
            return False
        return water_frame_level(tile[2]) >= WATER_SWIM_LEVEL

    def collision_dynamic(self):
        """Список сущностей, с которыми имеет смысл сверяться."""
        dyn = self._collision_dynamic
        return self.game.screen_map.dynamic_tiles if dyn is None else dyn

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
        touched_damage = set()   # опасные тайлы, задетые за это перемещение
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
                if type_coll == 0 and block[1] in DAMAGE_TILES:
                    touched_damage.add(block[1])
        self.rect.y += my
        # блоки с которыми стлкунулись после премещения по оси y (hit_static_lst, hit_dynamic_lst )
        *collision_lsts, semiphysbody_lst = collision_test(self.game_map, self.rect, static_tiles, dynamic_tiles,
                                                           first_tile_pos, semiphysbody=True)
        collision_types["semiphysbody"] += semiphysbody_lst
        # Урон от полу-физических тайлов: в лаву (как и в воду) можно
        # ВОЙТИ, поэтому жёсткой коллизии она не даёт и проверка ниже её
        # просто не видела — лава была безобидной.
        for block in semiphysbody_lst:
            if block[1] in DAMAGE_TILES:
                touched_damage.add(block[1])
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
                if type_coll == 0 and block[1] in DAMAGE_TILES:
                    touched_damage.add(block[1])
        # Урон — ОДИН раз за перемещение, по самому опасному из задетых
        # тайлов. Раньше он начислялся на каждую касающуюся вершину, из-за
        # чего кактус бил вчетверо, а лава (8 x 4 вершины) убивала бы
        # игрока с 30 HP мгновенно.
        dangerous = touched_damage - self.immune_tiles - self.effect_immunity()
        if dangerous:
            self.damage(max(DAMAGE_TILES[t] for t in dangerous))
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
            collisions = self.move(movement, self.collision_tiles())
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
                if self.class_obj & OBJ_PARTICLE:
                    self.chunk_pos = (new_cx, new_cy)   # частицы не живут в чанках
                elif self.game_map.move_dinamic_obj(*self.chunk_pos, new_cx, new_cy, self):
                    self.chunk_pos = (new_cx, new_cy)
                # Иначе переезд не состоялся (за экраном мир не создаётся):
                # chunk_pos НЕ меняем, иначе объект числился бы в чанке, где
                # его нет, и переезд не был бы повторён никогда.
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
