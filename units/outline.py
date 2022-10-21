# Supply you own "img.png" to test outlines with. 40x40 or less is recommended.
# press A to switch the outlining method
# press S to show/hide the image
# the part that activates the Pygame 2 method has been commented out. feel free to add it back in

# Setup Python ----------------------------------------------- #
import pygame, sys, random, time, os

# Setup pygame/window ---------------------------------------- #
mainClock = pygame.time.Clock()
from pygame.locals import *


# method 1
def outline_mask(img, loc):
    mask = pygame.mask.from_surface(img)
    mask_outline = mask.outline()
    n = 0
    for point in mask_outline:
        mask_outline[n] = (point[0] + loc[0], point[1] + loc[1])
        n += 1
    pygame.draw.polygon(display, (255, 255, 255), mask_outline, 3)


# method 2
def perfect_outline(img, loc):
    mask = pygame.mask.from_surface(img)
    mask_surf = mask.to_surface()
    mask_surf.set_colorkey((0, 0, 0))
    display.blit(mask_surf, (loc[0] - 1, loc[1]))
    display.blit(mask_surf, (loc[0] + 1, loc[1]))
    display.blit(mask_surf, (loc[0], loc[1] - 1))
    display.blit(mask_surf, (loc[0], loc[1] + 1))


# method 3
def perfect_outline_2(img, loc):
    mask = pygame.mask.from_surface(img)
    mask_outline = mask.outline()
    mask_surf = pygame.Surface(img.get_size())
    for pixel in mask_outline:
        mask_surf.set_at(pixel, (255, 255, 255))
    mask_surf.set_colorkey((0, 0, 0))
    display.blit(mask_surf, (loc[0] - 1, loc[1]))
    display.blit(mask_surf, (loc[0] + 1, loc[1]))
    display.blit(mask_surf, (loc[0], loc[1] - 1))
    display.blit(mask_surf, (loc[0], loc[1] + 1))


def add_outline_to_image(image: pygame.Surface, thickness: int, color: tuple,
                         color_key: tuple = (255, 0, 255)) -> pygame.Surface:
    mask = pygame.mask.from_surface(image)
    mask_surf = mask.to_surface(setcolor=color)
    mask_surf.set_colorkey((0, 0, 0))

    new_img = pygame.Surface((image.get_width() + 2, image.get_height() + 2))
    new_img.fill(color_key)
    new_img.set_colorkey(color_key)

    for i in -thickness, thickness:
        new_img.blit(mask_surf, (i + thickness, thickness))
        new_img.blit(mask_surf, (thickness, i + thickness))
    new_img.blit(image, (thickness, thickness))

    return new_img


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__ + "/../")))

    pygame.init()
    pygame.display.set_caption('outline test')
    WINDOWWIDTH = 500
    WINDOWHEIGHT = 300
    screen = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT), 0, 32)
    display = pygame.Surface((250, 150))

    # test_img = pygame.image.load(r'').convert()
    # font = pygame.font.SysFont("", 20)
    font = pygame.font.Font('data/fonts/xenoa.ttf', 40, )
    test_img = font.render("Hi 100", False, "red").convert()
    # test_img.set_colorkey((0, 0, 0))
    test_img = add_outline_to_image(test_img, 2, (255, 255, 255))

    while True:
        screen.blit(test_img, (10, 10))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
