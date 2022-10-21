from units.Texture import get_texture_size, GREEN
from units.common import *
from units.Entity import *
from units.outline import add_outline_to_image

NONE_PARTICLE_SPRITE = get_texture_size(GREEN, (10, 10))


class Particle(PhysicalObject):
    class_obj = OBJ_PARTICLE

    def __init__(self, game, rect, sprite=NONE_PARTICLE_SPRITE, use_collisions=False, use_gravity=False,
                 start_movement=pg.Vector2(0, 0), lifetime=FPS // 5*2, animation=None):
        start_movement = pg.Vector2(start_movement)
        self.animation = animation
        self.lifetime = lifetime
        rect = pg.Rect(rect)
        x, y = rect.topleft
        width, height = rect.size
        if width == 0:
            width, height = sprite.get_size()
        super(Particle, self).__init__(game, x, y, width, height, use_collisions=use_collisions,
                                       use_gravity=use_gravity,
                                       sprite=sprite)
        self.start_movement = start_movement

    def update(self, *args):
        # self.movement = self.start_movement
        # self.start_movement /= 1.2
        # super(Particle, self).update(*args)
        if self.animation:
            self.animation.update()
        self.not_collisions_move(self.start_movement)
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        if not self.alive:
            return False
        return True

    def draw(self, surface, pos):
        if self.animation:
            self.animation.draw()
        super(Particle, self).draw(surface, pos)


font_number = pygame.font.Font('data/fonts/xenoa.ttf', 20, )  # rus


class TextParticle(Particle):
    def __init__(self, game, pos, text, color="#DC2626", font=font_number, start_movement=pg.Vector2(0, -2),
                 outline=(255, 255, 255)):
        rect = (pos, (0, 0))
        sprite = font.render(text, True, color)
        if outline:
            sprite = add_outline_to_image(sprite, 1, outline)
        super(TextParticle, self).__init__(game, rect, sprite, start_movement=start_movement)


class DamageParticle(TextParticle):
    def __init__(self, game, pos, lives):
        text = str(lives)
        size = min(30, 18 + lives // 10)
        font = pygame.font.Font('data/fonts/xenoa.ttf', size, )
        super(DamageParticle, self).__init__(game, pos, text, color="#DC2626", font=font,
                                             start_movement=pg.Vector2(0, -2),
                                             outline=(255, 255, 255))
