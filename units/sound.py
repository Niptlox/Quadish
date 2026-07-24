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


class _DummyChannel:
    """Пустой канал воспроизведения (когда аудио недоступно)."""
    def set_endevent(self, *a, **k):
        pass

    def set_volume(self, *a, **k):
        pass

    def stop(self, *a, **k):
        pass

    def get_busy(self):
        return False


_DUMMY_CHANNEL = _DummyChannel()


class _DummySound:
    """Заглушка звука: игра без аудиоустройства (WSL/сервер) не падает."""
    def play(self, *a, **k):
        return _DUMMY_CHANNEL

    def set_volume(self, *a, **k):
        pass

    def stop(self, *a, **k):
        pass


def load_sound(path):
    if not AUDIO_ENABLED:
        return _DummySound()
    return pg.mixer.Sound(path)


def load_sounds(path, count, index_start=0):
    ar = Sounds()
    for i in range(index_start, index_start + count):
        ar.append(_DummySound() if not AUDIO_ENABLED else pygame.mixer.Sound(path.format(i)))
    return ar


def get_random_sound_of(sounds_list) -> pg.mixer.Sound:
    return choice(sounds_list)


def sounds_set_volume(lst_sounds, volume):
    for snd in lst_sounds:
        snd.set_volume(float(volume) * VolumeSettings.game_volume)


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
sounds_set_volume(sounds_creatures, VolumeSettings.creatures_volume)

# ====== GAME ======
sounds_game = Sounds()

# ====== МУЗ-БЛОК: синтез нот ======
# Без файлов-сэмплов на каждую ноту — один короткий синус, растянутый под
# нужную частоту (та же идея, что и процедурные спрайты вместо арта).
NOTE_SCALE = (261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25)
_note_sound_cache = {}


def _synth_tone(freq, duration=0.28, volume=0.35):
    if not AUDIO_ENABLED:
        return _DummySound()
    try:
        import numpy as np
        rate = pg.mixer.get_init()[0]
        n = int(rate * duration)
        t = np.linspace(0, duration, n, False)
        envelope = np.linspace(1, 0, n) ** 2  # плавное затухание — без щелчка на конце
        wave = np.sin(freq * t * 2 * np.pi) * envelope * volume * 32767
        return pg.sndarray.make_sound(np.ascontiguousarray(wave.astype(np.int16)))
    except Exception:
        return _DummySound()


def note_sound_for_item(item_index):
    """Разные предметы — разные ноты (по модулю гаммы, без отдельного
    счётчика/ползунка настройки высоты)."""
    key = 0 if item_index is None else item_index
    snd = _note_sound_cache.get(key)
    if snd is None:
        snd = _synth_tone(NOTE_SCALE[key % len(NOTE_SCALE)])
        snd.set_volume(VolumeSettings.game_volume)
        _note_sound_cache[key] = snd
    return snd


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
        categories_sounds[category].set_volume(volume )
        name_var = category + "_volume"
        VolumeSettings.set(name_var, volume)
