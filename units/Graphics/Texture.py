import os
import sys

import pygame

pygame.init()
pygame.font.init()

GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = pygame.color.Color("gray")

COLORKEY = GREEN

TEXTFONT = pygame.font.SysFont('Roboto', 32)
TEXTFONT_BTN = pygame.font.SysFont('Roboto', 40)
FPSFONT = pygame.font.SysFont('Roboto', 15)


def get_color_of_gradient(width, startcolor, endcolor, x):
    x = min(x, width)
    dd = 1.0 / width
    sr, sg, sb, sa = startcolor
    er, eg, eb, ea = endcolor
    rm = (er - sr) * dd
    gm = (eg - sg) * dd
    bm = (eb - sb) * dd
    am = (ea - sa) * dd
    return (int(sr + rm * x),
            int(sg + gm * x),
            int(sb + bm * x),
            int(sa + am * x))



def get_texture(texture, colorkey=None):
    if texture is None:
        return None
    if type(texture) is str and texture[0] != "#":
        return load_image(texture, colorkey)
    # if type(texture) is pygame.Color:
    #     return
    return texture


def get_texture_size(texture, size=None, colorkey=None):
    if texture is None:
        return None
    if type(texture) is str and texture[0] != "#":
        image = load_image(texture, colorkey)
        if size is not None:
            image = pygame.transform.scale(image, size)
            # image = image.convert_alpha()
        return image
    if type(texture) is not pygame.Surface and size is not None:
        surf = pygame.Surface(size)
        surf.fill(texture)
        texture = surf
    return texture


def load_image(name, colorkey=None):
    fullname = name  # os.path.join('data', name)
    # если файл не существует, то выходим
    # fullname = r"BetaIMG.png"
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()

    image = pygame.image.load(fullname)

    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    # else:
    #   image = image.convert_alpha()
    return image


def load_animation(path, frame_durations, size=None, colorkey=COLORKEY):
    animation_frames = []
    n = 0
    for count_frame in frame_durations:
        img_loc = path + '_' + str(n) + '.png'
        # player_animations/idle/idle_0.png
        animation_image = get_texture_size(img_loc, colorkey=colorkey, size=size)
        for i in range(count_frame):
            animation_frames.append(animation_image)
        n += 1
    return animation_frames


