from units.common import *
from random import choice
from units.config import *


def load_sounds(path, count, index_start=0):
    ar = []
    for i in range(index_start, index_start + count):
        ar.append(pygame.mixer.Sound(path.format(i)))
    return ar


def get_random_sound_of(sounds_list) -> pg.mixer.Sound:
    return choice(sounds_list)


def sounds_set_volume(lst_sounds, volume):
    for snd in lst_sounds:
        snd.set_volume(volume)


sound_click = pygame.mixer.Sound("data/audio/UI/click.wav")
sound_click.set_volume(VolumeSettings.ui_volume)

# sound_step_dry_1 = pygame.mixer.Sound("data/audio/steps/FootstepsDry-1.ogg")
# sound_step_dry_2 = pygame.mixer.Sound("data/audio/steps/FootstepsDry-2.ogg")
# sound_step_dry_3 = pygame.mixer.Sound("data/audio/steps/FootstepsDry-3.ogg")

sounds_step_dry = load_sounds("data/audio/steps/FootstepsDry-{}.ogg", 3, 1)
sounds_set_volume(sounds_step_dry, VolumeSettings.player_volume)

sounds_pickaxe = load_sounds("data/audio/tools/Pickaxe-{}.ogg", 4, 1)
sounds_set_volume(sounds_pickaxe, VolumeSettings.player_volume)

sounds_axe = load_sounds("data/audio/tools/Axe-{}.ogg", 2, 1)
sounds_set_volume(sounds_axe, VolumeSettings.player_volume)

sounds_eat = load_sounds("data/audio/food/EatingFood{}.ogg", 2, 1)
sounds_set_volume(sounds_eat, VolumeSettings.player_volume)

sounds_drink = load_sounds("data/audio/food/Drink-{}.ogg", 1, 1)
sounds_set_volume(sounds_drink, VolumeSettings.player_volume)
