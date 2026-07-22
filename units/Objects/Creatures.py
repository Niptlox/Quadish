import random
from time import time

from units.Graphics.Animation import get_death_animation
from units.Objects.Entity import PhysicalObject
from units.Objects.Items import ItemsTile
from units.Graphics.Particle import DamageParticle
from units.common import *


def checking_abyss(pos, game_map, height_of_abyss=3, convert_to_tile_pos=False):
    """Проверка на пропасть (не считая tile_pos)"""
    if convert_to_tile_pos:
        tx, _ty = pos[0] // TSIZE, (pos[1] - 3) // TSIZE
    else:
        tx, _ty = pos
    for ty in range(_ty + 1, _ty + height_of_abyss + 1):
        if game_map.get_static_tile_type(tx, ty):
            return False
    return True


class Creature(PhysicalObject):
    not_save_vars = PhysicalObject.not_save_vars | {"lives_surface", "angry_player"}
    bio_kingdom = KINGDOM_CREATURAE
    bio_species = "creature"
    bio_subspecies = "ordinary creature"
    class_obj = OBJ_CREATURE
    width, height = TSIZE, TSIZE
    sprite = pg.Surface((width, height))
    max_lives = -1
    # Вещи после смерти [(item_cls, (type_obj, cnt)), (item_cls, params), ...]
    drop_items = []
    enemy = False
    punch_damage = 0
    punch_speed = 1
    punch_discard = 0

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos[0], pos[1], self.width, self.height, use_physics=True, sprite=self.sprite)
        self.lives = self.max_lives
        self.lives_surface = pg.Surface((self.rect.w, 6)).convert_alpha()
        self.punch_reload_time = 1 / self.punch_speed
        self.last_punch_time = 0
        self.death_animation = get_death_animation(self.rect.size)

    def update(self, tact, elapsed_time):
        self.update_physics(elapsed_time)
        self.death_animation.update(self.game.elapsed_time)
        if self.enemy:
            if self.rect.colliderect(self.game.player.rect):
                if time() > self.punch_reload_time + self.last_punch_time:
                    self.last_punch_time = time()
                    self.game.player.damage(self.punch_damage)

    def jump(self, y):
        self.physical_vector.y -= y

    def draw(self, surface, pos):
        super().draw(surface, pos)

        self.death_animation.draw(surface, pos)
        if self.lives != self.max_lives:
            self.draw_lives(surface, pos)

    def draw_lives(self, surface, pos_obj):
        self.lives_surface.fill(f"#78716CAA")
        w = int((self.rect.w - 2) * (self.lives / self.max_lives))
        pg.draw.rect(self.lives_surface, "#A3E635AA", ((1, 1), (w, 4)))
        surface.blit(self.lives_surface, (pos_obj[0], pos_obj[1] - 10))

    def kill(self):
        super().kill()
        for item_cls, params in self.drop_items:
            x, y = self.rect.x + random.randint(0, TSIZE - HAND_SIZE), self.rect.y
            idx, count = params
            items = item_cls(self.game, index=idx, count=count,
                             pos=(x, y))
            self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(x // TSIZE, y // TSIZE), items)

    def damage(self, lives):
        lives = min(lives, self.lives)
        particle = DamageParticle(self.game, (self.rect.centerx, self.rect.top - 25), (lives))
        self.game_map.add_particle(particle)
        self.death_animation.start()
        return super(Creature, self).damage(lives)


class MovingCreature(Creature):
    height_of_abyss = 3
    width_of_abyss = 2

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.move_direction = 0
        self.move_tact = 0

    def check_abyss(self):
        x, y = self.rect.bottomleft
        left_abyss = True
        for i in range(self.width_of_abyss):
            left_abyss = left_abyss and checking_abyss((x, y), self.game_map, height_of_abyss=self.height_of_abyss,
                                                       convert_to_tile_pos=True)
            x -= TSIZE
        x, y = self.rect.bottomright
        right_abyss = True
        for i in range(self.width_of_abyss):
            right_abyss = right_abyss and checking_abyss((x, y), self.game_map, height_of_abyss=self.height_of_abyss,
                                                         convert_to_tile_pos=True)
            x += TSIZE
        if left_abyss and right_abyss:
            pass
        elif left_abyss:
            self.move_direction = 1
        elif right_abyss:
            self.move_direction = -1


"#D9F99DAA"


def slime_animation(color, size, reduction_step, count_sprites=3):
    size = max(size[0], 1), max(size[1], 1)

    sprites = []
    for i in range(0, reduction_step * count_sprites, reduction_step):
        w, h = size[0], size[1] + i
        spr = pg.Surface((w, h)).convert_alpha()
        spr.fill((0, 0, 0, 0))
        radius = max(2, min(w, h) // 3)
        pg.draw.rect(spr, color + "AA", (0, 0, w, h), border_radius=radius)
        pg.draw.rect(spr, color + "EE", (0, 0, w, h), width=2, border_radius=radius)
        # блик и "глазки" — придают слаймy характер, а не просто закруглённый блок
        eye_y = h // 3
        eye_r = max(1, w // 12)
        pg.draw.circle(spr, "#1C1917", (w // 3, eye_y), eye_r)
        pg.draw.circle(spr, "#1C1917", (w * 2 // 3, eye_y), eye_r)
        highlight = pg.Surface((max(1, w // 3), max(1, h // 4)), pg.SRCALPHA)
        highlight.fill((255, 255, 255, 70))
        spr.blit(highlight, (w // 5, h // 6))
        sprites.append(spr)

    return sprites


class Slime(MovingCreature):
    not_save_vars = MovingCreature.not_save_vars | {"sprites", "sprite", "lives_surface"}
    width, height = max(1, TSIZE // 1.3), max(1, TSIZE // 1.3 - 6)
    bio_kingdom = KINGDOM_CREATURAE
    bio_species = "slime"
    bio_subspecies = "ordinary slime"
    reduction_step = 3
    count_sprites = 3
    colors = ['#ADFF2F', '#7FFF00', '#7CFC00', '#00FF00', '#32CD32', '#98FB98', '#90EE90', '#00FA9A', '#00FF7F',
              '#3CB371', '#2E8B57', '#228B22', '#008000', '#006400', '#9ACD32', '#6B8E23', '#808000', '#556B2F',
              '#66CDAA', '#8FBC8F', '#20B2AA', '#008B8B', '#008080']
    color_hard = "#E11D48"
    max_lives_hard = 150
    punch_damage_hard = 15
    max_lives = 20
    drop_items = [(ItemsTile, (51, (1, 2)))]
    jump_speed = 6
    move_speed = 2
    height_of_abyss = 4
    width_of_abyss = 1

    enemy = True
    punch_damage = 5
    punch_speed = 1
    punch_discard = 0

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        x, y = pos
        self.i_sprite = 0
        self.jump_state = -1
        self.color = random.choice(self.colors)

        self.is_boss = False
        if random.randint(0, 100) < 2:
            self.init_boss()
            self.lives = self.max_lives_hard

        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[0]

    def init_boss(self):
        # SLIME BOSS
        self.is_boss = True
        self.color = self.color_hard
        self.max_lives = self.max_lives_hard
        self.punch_damage = self.punch_damage_hard
        self.width, self.height = TSIZE * 2, TSIZE * 2 - 8
        self.jump_speed = 10
        self.reduction_step = 6
        self.move_speed = 4
        self.drop_items = [(ItemsTile, (51, (10, 15))), (ItemsTile, (63, (0, 2))), (ItemsTile, (66, (0, 1)))]
        super().__init__(self.game, self.rect.topleft)

    def set_vars(self, vrs):
        super(Slime, self).set_vars(vrs)
        if self.rect.width > self.width:
            self.is_boss = True
        if self.is_boss:
            self.init_boss()
        self.sprites = slime_animation(self.color, self.rect.size, self.reduction_step)
        self.sprite = self.sprites[self.i_sprite]
        self.lives_surface = pg.Surface((self.rect.width, 6)).convert_alpha()

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
        self.death_animation.set_resize(self.rect.size)
        if self.collisions["bottom"]:
            if self.jump_state == 1:
                self.rect.height += self.reduction_step
                self.rect.y -= self.reduction_step
                self.i_sprite += 1
                if self.i_sprite == self.count_sprites - 1:
                    self.jump_state = 0
            elif self.jump_state == -1:
                self.rect.height -= self.reduction_step
                self.rect.y += self.reduction_step
                self.i_sprite -= 1

                if self.i_sprite <= 0:
                    self.jump_state = 1
            elif self.jump_state == 0:
                self.jump(self.jump_speed)
                self.jump_state = -1

        self.sprite = self.sprites[self.i_sprite]
        if self.move_tact is not None:
            self.move_tact -= 1
            if self.move_tact <= 0:
                self.move_tact = random.randint(30, 205)
                self.move_direction = random.randint(-1, 1)
        self.check_abyss()
        self.movement_vector.x += self.move_direction * self.move_speed
        return True


def create_cow_sprite(color, size, outline="#1C1917"):
    """Корова примитивами (мордой вправо): туловище, пятна, голова с мордой и ушами, ноги."""
    w, h = max(size[0], 4), max(size[1], 4)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    leg_w = max(2, w // 7)
    leg_h = max(2, int(h * 0.28))
    leg_y = h - leg_h
    for lx in (int(w * 0.08), int(w * 0.32), int(w * 0.58), int(w * 0.82)):
        pg.draw.rect(s, "#44403C", (lx, leg_y, leg_w, leg_h))
    body_h = h - leg_h + 2
    pg.draw.ellipse(s, color, (0, 0, w, body_h))
    spot = "#3F3A36"
    pg.draw.ellipse(s, spot, (int(w * 0.08), int(body_h * 0.15), int(w * 0.22), int(body_h * 0.35)))
    pg.draw.ellipse(s, spot, (int(w * 0.5), int(body_h * 0.4), int(w * 0.28), int(body_h * 0.3)))
    head_w, head_h = int(w * 0.3), int(body_h * 0.7)
    hx, hy = w - head_w - 1, int(body_h * 0.05)
    pg.draw.ellipse(s, color, (hx, hy, head_w, head_h))
    ear_r = max(2, head_h // 5)
    pg.draw.circle(s, color, (hx + 2, hy), ear_r)
    pg.draw.circle(s, color, (hx + head_w - 2, hy), ear_r)
    snout_w = int(head_w * 0.55)
    pg.draw.ellipse(s, "#F5E6D3", (hx + head_w - snout_w, hy + int(head_h * 0.5), snout_w, int(head_h * 0.45)))
    pg.draw.circle(s, outline, (hx + head_w - 4, hy + int(head_h * 0.35)), max(1, w // 40 + 1))
    pg.draw.ellipse(s, outline, (0, 0, w, body_h), width=1)
    pg.draw.ellipse(s, outline, (hx, hy, head_w, head_h), width=1)
    return s


class Cow(MovingCreature):
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "cow"
    bio_subspecies = "white cow"
    width, height = int(TSIZE * 1), int(TSIZE * 0.8)
    colors = ["#FFFAFA", "#FAEBD7", "#FDF4E3", "#FAF0E6"]
    max_lives = 20
    drop_items = [(ItemsTile, (52, (1, 2)))]
    move_speed = 2

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.color = random.choice(self.colors)
        self.sprite = create_cow_sprite(self.color, self.rect.size)
        self.jump_speed = 5

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
        # if self.collisions["bottom"]:
        self.check_abyss()
        self.movement_vector.x += self.move_direction * self.move_speed
        if self.collisions["bottom"] and (self.collisions["left"] or self.collisions["right"]):
            self.jump(self.jump_speed)
        self.move_tact -= 1
        if self.move_tact <= 0:
            self.move_tact = random.randint(30, 205)
            self.move_direction = random.randint(-1, 1)
        return True


def create_wolf_sprite(color, size, outline="#1C1917"):
    """Волк/собака примитивами (мордой вправо): туловище, треугольные уши, морда, хвост, ноги."""
    w, h = max(size[0], 4), max(size[1], 4)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    leg_w = max(2, w // 8)
    leg_h = max(2, int(h * 0.3))
    leg_y = h - leg_h
    for lx in (int(w * 0.05), int(w * 0.28), int(w * 0.6), int(w * 0.83)):
        pg.draw.rect(s, "#3F3A36", (lx, leg_y, leg_w, leg_h))
    body_w = int(w * 0.78)
    body_h = h - leg_h + 2
    pg.draw.rect(s, color, (0, 0, body_w, body_h), border_radius=max(1, int(body_h * 0.3)))
    tail = [(int(w * 0.1), int(body_h * 0.2)), (0, int(body_h * 0.02)), (int(w * 0.1), int(body_h * 0.45))]
    pg.draw.polygon(s, color, tail)
    head_w, head_h = int(w * 0.34), int(body_h * 0.75)
    hx, hy = w - head_w, 0
    pg.draw.rect(s, color, (hx, hy, head_w, head_h), border_radius=max(1, int(head_h * 0.25)))
    ear_h = max(2, head_h // 3)
    pg.draw.polygon(s, color, [(hx + 2, hy), (hx + 2 + ear_h // 2, hy - ear_h), (hx + 2 + ear_h, hy)])
    pg.draw.polygon(s, color, [(hx + head_w - 2 - ear_h, hy), (hx + head_w - 2 - ear_h // 2, hy - ear_h),
                               (hx + head_w - 2, hy)])
    snout_w = max(1, int(head_w * 0.4))
    pg.draw.rect(s, color, (hx + head_w - 2, hy + int(head_h * 0.45), snout_w, int(head_h * 0.35)),
                border_top_right_radius=3, border_bottom_right_radius=3)
    pg.draw.circle(s, outline, (hx + head_w - 4, hy + int(head_h * 0.3)), max(1, w // 40 + 1))
    pg.draw.rect(s, outline, (0, 0, body_w, body_h), width=1, border_radius=max(1, int(body_h * 0.3)))
    pg.draw.rect(s, outline, (hx, hy, head_w, head_h), width=1, border_radius=max(1, int(head_h * 0.25)))
    return s


def create_snake_sprite(color, size, outline="#1C1917"):
    """Змея примитивами: волнистое тело из кружков, голова с языком."""
    w, h = max(size[0], 4), max(size[1], 3)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    body_r = max(1, h // 2)
    segs = max(3, w // max(2, body_r * 3))
    seg_w = w / segs
    for i in range(segs):
        offset = body_r // 2 if i % 2 else -(body_r // 2)
        cy = max(body_r, min(h - body_r, h // 2 + offset))
        cx = int(seg_w * (i + 0.5))
        pg.draw.circle(s, color, (cx, cy), body_r)
    head_r = max(2, body_r + 1)
    hx, hy = w - head_r, h // 2
    pg.draw.circle(s, color, (hx, hy), head_r)
    pg.draw.circle(s, outline, (min(w - 1, hx + head_r // 2), max(0, hy - head_r // 3)), 1)
    if w > 1:
        pg.draw.line(s, "#B91C1C", (w - 2, hy), (w - 1, hy), 1)
    return s


class Wolf(MovingCreature):
    not_save_vars = MovingCreature.not_save_vars | {"angry_player", "angry"}
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "wolf"
    bio_subspecies = "gray wolf"
    width, height = int(TSIZE * 1), int(TSIZE * 0.9)

    color = "#708090"
    max_lives = 35
    drop_items = [(ItemsTile, (56, (1, 3))), (ItemsTile, (58, (1)))]

    move_speed = 3.5
    jump_speed = 5

    enemy = True
    punch_damage = 8
    punch_speed = 3
    punch_discard = 8

    # агриться ли сейчас на игрока
    angry_rect_size = (int(TSIZE * 19), int(TSIZE * 19))
    move_speed_angry = 6

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_wolf_sprite(self.color, self.rect.size)
        self.angry_rect = pg.Rect((0, 0), self.angry_rect_size)
        self.angry = False

        self.angry_player = None

    def update(self, tact, elapsed_time):
        super().update(tact, elapsed_time)
        self.check_abyss()
        if self.angry:
            self.movement_vector.x += self.move_direction * self.move_speed_angry
        else:
            self.movement_vector.x += self.move_direction * self.move_speed
        if self.collisions["bottom"] and (self.collisions["left"] or self.collisions["right"]):
            self.jump(self.jump_speed)

        if self.angry:
            if self.angry_player.rect.x > self.rect.x:
                self.move_direction = 1
            else:
                self.move_direction = -1

            self.angry_rect.center = self.rect.center
            if not self.angry_rect.colliderect(self.angry_player):
                self.angry = False
                self.angry_player = None
        else:
            self.move_tact -= 1
            if self.move_tact <= 0:
                self.move_tact = random.randint(30, 205)
                self.move_direction = random.randint(-1, 1)

            self.angry_rect.center = self.rect.center
            if self.angry_rect.colliderect(self.game.player.rect):
                self.angry = True
                self.angry_player = self.game.player
                self.move_tact = 0

        return True


class Snake(Wolf):
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "snake"
    bio_subspecies = "green snake"
    width, height = int(TSIZE * 1), int(TSIZE * 0.1)
    color = "#4d7c0f"
    drop_items = [(ItemsTile, (401, (1, 2))), (ItemsTile, (301, (0, 1)))]

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_snake_sprite(self.color, self.rect.size)


def create_imp_sprite(color, size, outline="#1C1917"):
    """Бес примитивами: приземистое тело, рожки, светящийся глаз."""
    w, h = max(size[0], 4), max(size[1], 4)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    leg_w = max(2, w // 6)
    leg_h = max(2, int(h * 0.3))
    leg_y = h - leg_h
    for lx in (int(w * 0.1), int(w * 0.35), int(w * 0.6), int(w * 0.82)):
        pg.draw.rect(s, "#292524", (lx, leg_y, leg_w, leg_h))
    body_w = int(w * 0.8)
    body_h = h - leg_h + 2
    pg.draw.rect(s, color, (0, 0, body_w, body_h), border_radius=max(1, int(body_h * 0.35)))
    head_w, head_h = int(w * 0.4), int(body_h * 0.7)
    hx, hy = w - head_w, 0
    pg.draw.rect(s, color, (hx, hy, head_w, head_h), border_radius=max(1, int(head_h * 0.3)))
    horn_h = max(2, head_h // 3)
    pg.draw.polygon(s, "#78716C", [(hx + 2, hy + 2), (hx, hy - horn_h), (hx + 4, hy)])
    pg.draw.polygon(s, "#78716C", [(hx + head_w - 2, hy + 2), (hx + head_w, hy - horn_h), (hx + head_w - 4, hy)])
    eye_r = max(1, w // 30 + 1)
    pg.draw.circle(s, "#FDE047", (hx + head_w - 4, hy + int(head_h * 0.4)), eye_r)
    pg.draw.rect(s, outline, (0, 0, body_w, body_h), width=1, border_radius=max(1, int(body_h * 0.35)))
    pg.draw.rect(s, outline, (hx, hy, head_w, head_h), width=1, border_radius=max(1, int(head_h * 0.3)))
    return s


class Imp(Wolf):
    """Бес — враждебный житель Ада (спавнится глубоко под START_HELL_Y)."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "imp"
    bio_subspecies = "hell imp"
    width, height = int(TSIZE * 0.9), int(TSIZE * 0.9)
    color = "#DC2626"
    max_lives = 45
    drop_items = [(ItemsTile, (402, (1, 3)))]

    move_speed = 4
    jump_speed = 6

    enemy = True
    punch_damage = 12
    punch_speed = 2
    punch_discard = 6

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_imp_sprite(self.color, self.rect.size)


def create_scorpion_sprite(color, size, outline="#1C1917"):
    """Скорпион примитивами: приземистое тело, клешни спереди, хвост со
    жалом, изогнутый над спиной назад."""
    w, h = max(size[0], 8), max(size[1], 6)
    s = pg.Surface((w, h)).convert_alpha()
    s.fill((0, 0, 0, 0))
    body_h = int(h * 0.45)
    body_y = h - body_h - 1
    leg_len = max(1, int(h * 0.22))
    for lx in (int(w * 0.28), int(w * 0.42), int(w * 0.56)):
        pg.draw.line(s, outline, (lx, body_y + body_h - 1), (lx - 2, h - 1), 1)
        pg.draw.line(s, outline, (lx + leg_len, body_y + body_h - 1), (lx + leg_len + 2, h - 1), 1)
    pg.draw.ellipse(s, color, (int(w * 0.22), body_y, int(w * 0.55), body_h))
    claw_w, claw_h = max(2, int(w * 0.2)), max(2, int(body_h * 0.9))
    pg.draw.ellipse(s, color, (int(w * 0.66), body_y - claw_h // 4, claw_w, claw_h))
    pg.draw.ellipse(s, color, (int(w * 0.02), body_y - claw_h // 4, claw_w, claw_h))
    # хвост из сегментов, загибается вверх-назад над телом
    seg_r = max(1, body_h // 4)
    tx, ty = int(w * 0.22), body_y
    for _ in range(4):
        tx = max(seg_r, tx - int(w * 0.06))
        ty = max(seg_r, ty - int(h * 0.16))
        pg.draw.circle(s, color, (tx, ty), seg_r)
    pg.draw.polygon(s, "#7C2D12", [(tx - seg_r, ty), (tx, max(0, ty - seg_r * 2)), (tx + seg_r, ty)])
    pg.draw.ellipse(s, outline, (int(w * 0.22), body_y, int(w * 0.55), body_h), width=1)
    return s


class Scorpion(Wolf):
    """Скорпион — враждебный житель пустыни, мельче и быстрее волка."""
    not_save_vars = Wolf.not_save_vars
    bio_kingdom = KINGDOM_ANIMALIA
    bio_species = "scorpion"
    bio_subspecies = "desert scorpion"
    width, height = int(TSIZE * 0.7), int(TSIZE * 0.5)
    color = "#D4A373"
    max_lives = 18
    drop_items = [(ItemsTile, (403, (1, 2)))]

    move_speed = 5
    jump_speed = 4

    enemy = True
    punch_damage = 4
    punch_speed = 4
    punch_discard = 3

    angry_rect_size = (int(TSIZE * 12), int(TSIZE * 12))
    move_speed_angry = 7

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos)
        self.sprite = create_scorpion_sprite(self.color, self.rect.size)


class SlimeBigBoss(Slime):
    not_save_vars = Slime.not_save_vars | {"angry", "angry_player"}
    bio_subspecies = "huge slime"
    colors = ["#ff9d00"]
    max_lives = 250
    lives = 250
    punch_damage = 35
    width, height = TSIZE * 3, TSIZE * 3 - 15
    reduction_step = 12
    jump_speed = 10
    move_speed = 4
    height_of_abyss = 9
    width_of_abyss = 3
    drop_items = [(ItemsTile, (51, (20, 30))), (ItemsTile, (63, (3, 5))), (ItemsTile, (66, (2, 3))),
                  (ItemsTile, (55, (0, 1)))]

    # агриться ли сейчас на игрока
    angry = False
    angry_rect_size = (int(TSIZE * 19), int(TSIZE * 19))
    move_speed_angry = 6
    angry_player = None

    def __init__(self, game, pos=(0, 0)):
        super(SlimeBigBoss, self).__init__(game, pos)
        self.angry_rect = pg.Rect((0, 0), self.angry_rect_size)

    def update(self, tact, elapsed_time):
        super(SlimeBigBoss, self).update(tact, elapsed_time)
        self.angry_rect.center = self.rect.center

        if self.angry:
            if self.angry_player.rect.x > self.rect.x:
                self.move_direction = 1
            else:
                self.move_direction = -1
            if not self.angry_rect.colliderect(self.angry_player):
                self.angry = False
                self.angry_player = None
                self.move_tact = 0
        else:
            if self.angry_rect.colliderect(self.game.player.rect):
                self.angry = True
                self.angry_player = self.game.player
                self.move_tact = None


CREATURES = [Creature, Slime, Cow, Wolf, SlimeBigBoss, Snake, Imp, Scorpion]
CREATURES_D = {cls.__name__: cls for cls in CREATURES}
