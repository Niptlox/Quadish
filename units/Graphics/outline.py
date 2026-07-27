"""Обводка (контур) вокруг непрозрачной части изображения.

Используется для читаемости текста поверх пёстрого фона (заголовки меню,
всплывающие сообщения) — см. units/UI/UI.py.
"""
import os
import sys

import pygame


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
    # Ручная проверка обводки: python -m units.Graphics.outline
    os.chdir(os.path.dirname(os.path.abspath(__file__ + "/../")))

    pygame.init()
    pygame.display.set_caption('outline test')
    screen = pygame.display.set_mode((500, 300), 0, 32)

    font = pygame.font.Font('data/fonts/xenoa.ttf', 40)
    test_img = add_outline_to_image(font.render("Hi 100", False, "red").convert(),
                                    2, (255, 255, 255))

    while True:
        screen.blit(test_img, (10, 10))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
