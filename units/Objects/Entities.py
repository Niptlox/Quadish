from math import sin, cos, pi
from random import randint

from units.Graphics.Animation import load_animation
from units.Objects.Entity import PhysicalObject, collision_test
# from units.Items import ItemsTile
from units.Tiles import item_of_break_tile
from units.Tiles import tnt_imgs, DYNAMITE_NOT_BREAK
from units.common import *


def create_circle_pattern(radius):
    r = radius
    a = [[0] * (2 * r + 1) for i in range(r * 2 + 1)]
    ar = set(())
    for ri in range(r + 1):
        i = 0
        while i < pi * 2:
            x, y = int(cos(i) * ri) + r, int(sin(i) * ri * 0.95) + r
            # print(x, y)
            a[y][x] = 1
            i += pi / (r * 10)
            ar.add((x, y))
    return ar


def activate_dynamite(game_map, x, y, ttile):
    if ttile == 9:
        obj = Dynamite(game_map.game, x * TSIZE, y * TSIZE)
        game_map.add_dinamic_obj(*game_map.to_chunk_xy(x, y), obj)
        game_map.set_static_tile(x, y, None)


class Dynamite(PhysicalObject):
    class_obj = OBJ_TILE
    boom_radius = 5
    pattern = create_circle_pattern(boom_radius)

    def __init__(self, game, x=0, y=0):
        print("d", x, y)
        super().__init__(game, x, y, TSIZE, TSIZE, use_physics=True)
        self.game = game
        self.arise_time = -1  # время повления
        self.last_time = 0
        self.period = 10  # период мигания
        self.boom_time = 2000  # время взрыва
        self.image_state = 0
        self.detonation_state = 0

    def set_vars(self, vrs):
        super().set_vars(vrs)
        self.sprite = tnt_imgs[self.image_state]

    def update(self, tact, elapsed_time):
        if self.arise_time == -1:
            self.arise_time = self.game.total_time
        if self.game.total_time - self.arise_time >= self.boom_time:
            if self.detonation_obj():
                self.alive = False
                return False
            return True
        if self.game.total_time - self.last_time >= self.period:
            self.last_time = self.game.total_time
            self.image_state ^= 1
            self.sprite = tnt_imgs[self.image_state]
            self.period -= 1
        self.update_physics(elapsed_time)
        return True

    def detonation_obj(self):
        tx, ty = self.rect.x // TSIZE, self.rect.y // TSIZE
        if self.detonation_state == 0:
            self.detonation_state = 1
            center_tnt = self.rect.centerx // TSIZE, self.rect.centery // TSIZE
            center_ttile = self.game.screen_map.static_tiles.get(center_tnt)
            if center_ttile == 120:  # water
                return  # not break blocks
            for x, y in self.pattern:
                ix, iy = tx + x - self.boom_radius, ty + y - self.boom_radius
                ttile = self.game_map.get_static_tile_type(ix, iy, 0)
                if ttile == 0:
                    continue
                elif ttile in DYNAMITE_NOT_BREAK:
                    continue
                res = item_of_break_tile(self.game_map.get_static_tile(ix, iy), self.game_map, (ix, iy))
                self.game_map.set_static_tile(ix, iy, None)
                if ttile == 9:  # tnt
                    obj = Dynamite(self.game, ix * TSIZE, iy * TSIZE)
                    self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(ix, iy), obj)
                    continue
                for ttile, count_items in res:
                    # items = ItemsTile(self.game, ttile, count_items, (ix * TSIZE + randint(0, TSIZE - HAND_SIZE), iy * TSIZE))
                    # self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(ix, iy), items)
                    self.game_map.add_item_of_index(ttile, count_items, ix, iy)

            return
        elif self.detonation_state == 1:
            self.detonation_state = 2
            d = self.boom_radius
            dt = d * TSIZE
            boom_rect = pg.Rect(0, 0, d * TSIZE, d * TSIZE)
            boom_rect.center = self.rect.center
            _, hit_dynamic_lst = collision_test(self.game_map, boom_rect, {}, self.game.screen_map.dynamic_tiles)
            if boom_rect.colliderect(self.game.player.rect):
                hit_dynamic_lst.append(self.game.player)

            # print(hit_dynamic_lst)
            for obj in hit_dynamic_lst:
                if obj is not self:
                    if obj.rect.x != self.rect.x:
                        # 1 / ((obj.rect.x - self.rect.x) / TSIZE)* d
                        obj.physical_vector.x += dt / (obj.rect.x - self.rect.x)
                    if obj.rect.y != self.rect.y:
                        # 1 / ((obj.rect.y - self.rect.y) / TSIZE) * d
                        obj.physical_vector.y += dt / (obj.rect.y - self.rect.y)
                    else:
                        obj.physical_vector.y -= 2
                    obj.damage(randint(8, 10))
            return True


class PortalMainGate(PhysicalObject):
    not_save_vars = PhysicalObject.not_save_vars | {"animation"}

    def __init__(self, game, x=0, y=0):
        super(PortalMainGate, self).__init__(game, x, y, 1, 1, use_physics=False, use_gravity=False)
        self.animation = load_animation("data/animations/portal_anim_nebula.json")
        self.animation.start()
        self.spawn_player_tact = 20

    def draw(self, surface, pos):
        self.animation.update(self.game.elapsed_time)
        self.animation.draw(surface, pos)
        self.alive = self.animation.animation
        self.spawn_player_tact -= 1
        if self.spawn_player_tact <= 0:
            self.game.player.active = True
