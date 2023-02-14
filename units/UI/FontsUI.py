import pygame
from units.common import CWDIR

MAIN_FONT_PATH = CWDIR + 'data/fonts/xenoa.ttf'

pygame.font.init()
# textfont = pygame.font.SysFont('Jokerman', 19)
textfont = pygame.font.Font(MAIN_FONT_PATH, 12, )  # yes rus
textfont_sys_msg = pygame.font.Font(MAIN_FONT_PATH, 21, )  # yes rus
# textfont = pygame.font.Font('data/fonts/Teletactile.ttf', 10, bold=True)
textfont_info = pygame.font.Font('data/fonts/Teletactile.ttf', 10, )  # no rus
textfont_btn = pygame.font.SysFont("Fenix", 35, )

textfont_btn = pygame.font.Font(MAIN_FONT_PATH, 28, )  # rus

font_end = pygame.font.Font(MAIN_FONT_PATH, 28, )  # rus

# texframe = font.render(text, False, text_color)
