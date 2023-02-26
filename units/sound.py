from units.common import *
from random import choice
from units.config import *


class Sounds(list):
    def rplay(self):
        return self.rchoice().play()

    def rchoice(self):
        return choice(self)

    @classmethod
    def init_sounds(cls, path, count, index_start=0):
        return load_sounds(path, count, index_start=index_start)

    def set_volume(self, volume):
        sounds_set_volume(self, volume)

    def __add__(self, other):
        return self.__class__(super(Sounds, self).__add__(other))


def load_sound(path):
    return pg.mixer.Sound(path)


def load_sounds(path, count, index_start=0):
    ar = Sounds()
    for i in range(index_start, index_start + count):
        ar.append(pygame.mixer.Sound(path.format(i)))
    return ar


def get_random_sound_of(sounds_list) -> pg.mixer.Sound:
    return choice(sounds_list)


def sounds_set_volume(lst_sounds, volume):
    for snd in lst_sounds:
        snd.set_volume(float(volume))


# ====== UI ========
sound_click = load_sound("data/audio/UI/click.wav")
sound_click.set_volume(VolumeSettings.ui_volume)

sounds_ui = Sounds([sound_click])
sounds_set_volume(sounds_ui, VolumeSettings.ui_volume)

# ======= PLAYER =======
sounds_step_dry = load_sounds("data/audio/steps/StepGrassN{}.wav", 2, 1)
sounds_step_stomp = load_sounds("data/audio/steps/StompN{}.wav", 3, 1)
sounds_pickaxe = load_sounds("data/audio/tools/Pickaxe-{}.ogg", 4, 1)
sounds_axe = load_sounds("data/audio/tools/Axe-{}.ogg", 2, 1)
sounds_eat = load_sounds("data/audio/food/EatingFood{}.ogg", 2, 1)
sounds_drink = load_sounds("data/audio/food/Drink-{}.ogg", 1, 1)

sounds_brake_rock = load_sound("data/audio/tools/BrakeRock.wav")

sounds_player = sounds_step_dry + sounds_step_stomp + sounds_pickaxe + sounds_axe + sounds_eat + sounds_drink
sounds_set_volume(sounds_player, VolumeSettings.player_volume)

# ====== BACK MUSIC ======
sounds_background = Sounds([load_sound("data/audio/background/alexander-nakarada-fantasy-motion-loop-ready.mp3")])
sounds_set_volume(sounds_background, VolumeSettings.background_volume)

# ====== CREATURES ======
sound_gate = load_sound("data/audio/gate/Fire4.wav")
sounds_creatures = Sounds([sound_gate])

# ====== GAME ======
sounds_game = Sounds()

# SET VOLUME

categories_sounds = {
    "ui": sounds_ui,
    'player': sounds_player,
    'creatures': sounds_creatures,
    'game': sounds_game,
    'background': sounds_background,
}


def set_category_volume(category, volume):
    if category in categories_sounds:
        categories_sounds[category].set_volume(volume)
        name_var = category + "_volume"
        VolumeSettings.set(name_var, volume)
