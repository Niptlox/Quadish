from units.Graphics.Image import load_imgs_of_animation
from units.common import *
import json
from pathlib import Path


def load_animation(path):
    path = os.path.join(CWDIR, path)
    print(path)
    data = json.load(open(path, "r"))
    if data.get("format_path", None):
        json_file_name = Path(path).stem
        path_img = data.get("format_path", "").format(json_file_name)
    else:
        path_img = data.get("path", "None")
    path_img = os.path.join(os.path.dirname(path), path_img)
    table = data.get("table", [1, 1])
    frames = load_imgs_of_animation(path_img, table, data.get("count_frames", table[0] * table[1]),
                                    colorkey=data.get("colorkey", None), convert_alpha=data.get("convert_alpha", True))
    print(frames)
    size = frames[0].get_size()
    fsize = size
    nframes = []
    for i in range(len(frames)):
        fsize = (size[0] + i * 3 - 60, size[1] + i * 3 - 60)
        nframes.append(pg.transform.scale(frames[i], fsize))
    n = 20
    for i in range(n):
        frame = pg.transform.scale(frames[i], fsize)
        frame.set_alpha(255 * (1 - i / n))
        nframes.append(frame)
    return Animation(nframes, speed=data.get("speed", 20), looped=data.get("looped", False),
                     centered=data.get("centered", False))


class Animation(SavedObject):
    is_not_saving = True

    def __init__(self, frames, speed=20, looped=False, start_frame=0, centered=False):
        self.animation = False
        # массив картинок
        self.centered = centered
        self.frames = frames
        self.frame_count = len(self.frames)
        self.frame_index = start_frame
        self.looped = looped
        # кадров в секунду
        self.speed = speed
        # кадров на тик
        self.speed_one_tick = speed / FPS
        self.resize = None

    def draw(self, surface, pos):
        if self.animation:
            if self.resize:
                if self.centered:
                    pos = (pos[0] - self.resize[0] // 2, pos[1] - self.resize[1] // 2)
                surface.blit(self.get_frame(), pos)
            else:
                if self.centered:
                    size = self.frames[int(self.frame_index)].get_size()
                    pos = (pos[0] - size[0] // 2, pos[1] - size[1] // 2)
                surface.blit(self.get_frame(), pos)

    def get_frame(self):
        if self.resize:
            return pg.transform.scale(self.frames[int(self.frame_index)], self.resize)
        return self.frames[int(self.frame_index)]

    def set_resize(self, size):
        self.resize = size

    def update(self):
        if self.animation:
            self.frame_index += self.speed_one_tick
            if self.frame_index >= self.frame_count:
                if self.looped:
                    self.frame_index %= self.frame_count
                else:
                    self.stop()

    def start(self, restart=True):
        if restart:
            self.stop()
        self.animation = True

    def pause(self):
        self.animation = False

    def stop(self):
        self.animation = False
        self.frame_index = 0


# Animation with Start Loop End
class AnimationSLE(SavedObject):
    is_not_saving = True

    def __init__(self, start_anim: Animation, loop_anim: Animation, end_anim: Animation):
        """Animation with Start Loop Stop"""
        self.start_anim = start_anim
        self.loop_anim = loop_anim
        self.end_anim = end_anim
        self.state = 0
        self.animations = [start_anim, loop_anim, end_anim]
        self.animation = False

    def draw(self, surface, pos):
        if self.animation:
            self.animations[self.state].draw(surface, pos)

    def get_frame(self):
        return self.animations[self.state].get_frame()

    def next_state(self):
        self.set_state(self.state+1)

    def update(self):
        if self.animation:
            self.animations[self.state].update()
            if not self.animations[self.state].animation:
                self.next_state()

    def start(self, restart=True):
        if restart:
            self.stop()
        self.animation = True

    def pause(self):
        self.animation = False

    def stop(self):
        self.animation = False
        self.state = 0

    def set_state(self, state):
        if state != self.state:
            self.state = state
            if self.state >= len(self.animations):
                self.stop()
            else:
                self.animations[self.state].start(restart=True)





def get_death_animation(size, color=(185, 28, 28), speed=10, time=2, start_alpha=200):
    count = FPS * time // speed
    arr = []
    for i in range(count):
        surf = pg.Surface(size)
        surf.fill(color)
        surf.set_alpha(start_alpha * i / count)
        arr.append(surf)
    return Animation(arr[::-1], speed=speed, looped=False)


def test_loop(surface):
    surface.fill("black")
    anim.update()
    # surface.blit(anim.frames[0], (0, 0))
    anim.draw(surface, (30, 30))


if __name__ == '__main__':
    anim = load_animation("data/animations/portal_anim_nebula.json")
    anim.start()
    pygame_mainloop(test_loop)
