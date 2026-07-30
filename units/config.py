import os
import sys

from configparser import ConfigParser

# Корень проекта: рядом с exe для собранной игры, иначе на уровень выше units/
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
config_filename = os.path.join(PROJECT_ROOT, 'settings.ini')
print("config_filename", config_filename)
config = ConfigParser()
if not config.read(config_filename, encoding="utf-8"):
    raise FileNotFoundError(f"Не найден файл настроек: {config_filename}")


def config_save():
    with open(config_filename, 'w', encoding="utf-8") as configfile:
        config.write(configfile)


class __Settings:
    config = config
    section = ""

    @classmethod
    def set(cls, var_name, var_value):
        """Записать настройку в файл и в класс.

        Присваивание через setattr, а не через exec с подстановкой значения:
        exec ломался бы на любой строке с кавычкой и молча выполнял бы то, что
        в ней написано. Заодно значение кладётся КАК ЕСТЬ — а раньше строка,
        собранная из списка, так списком и не становилась (см.
        ModSettings.set_mod_disabled).
        """
        config.set(cls.section, var_name, str(var_value))
        config_save()
        if var_name in cls.__dict__:
            setattr(cls, var_name, var_value)


class Window(__Settings):
    section = 'window'
    # последний применённый размер окна — теперь обновляется автоматически
    # при живом ресайзе (units.common.apply_resize), а не через выбор
    # пресета в настройках.
    size = config.get(section, 'size')
    fullscreen = config.getboolean(section, 'fullscreen')
    # индекс монитора (для нескольких экранов)
    monitor = config.getint(section, 'monitor', fallback=0)
    # сколько тайлов должно быть видно по ширине экрана — задаёт
    # постоянный "зум" мира независимо от разрешения/монитора.
    view_tiles_width = config.getint(section, 'view_tiles_width', fallback=50)
    # "Размер меню" (GUI Scale): auto/tiny/small/medium/large/huge —
    # см. units.common.UI_SCALE.
    menu_size = config.get(section, 'menu_size', fallback="auto")

    @classmethod
    def set_fullscreen(cls, value):
        cls.set('fullscreen', str(value))

    @classmethod
    def set_size(cls, value):
        cls.set('size', str(value))

    @classmethod
    def set_monitor(cls, value):
        cls.set('monitor', int(value))

    @classmethod
    def set_view_tiles_width(cls, value):
        cls.set('view_tiles_width', int(value))

    @classmethod
    def set_menu_size(cls, value):
        cls.set('menu_size', str(value))


class ModSettings(__Settings):
    section = 'mods'
    # Загружать ли моды из data/modifications (см. units/mods.py).
    enabled = config.getboolean(section, 'enabled', fallback=True)
    # Папки модов, выключенных по отдельности. Общий выключатель оставляет
    # только «всё или ничего», а мод обычно ломает игру ровно один — нужен
    # способ выключить его, не отключая остальные.
    disabled = [n for n in config.get(section, 'disabled', fallback='').replace(' ', '').split(',') if n]

    @classmethod
    def set_enabled(cls, value):
        cls.set('enabled', bool(value))

    @classmethod
    def is_disabled(cls, folder):
        return folder in cls.disabled

    @classmethod
    def set_mod_disabled(cls, folder, value):
        """Включить/выключить один мод.

        В файл идёт строка, а в классе остаётся СПИСОК. Раньше в класс
        попадала та же строка, и на следующем вызове её перебирали по буквам:
        список выключенных превращался в набор символов, переключатель мода
        переставал работать после первого же нажатия, а settings.ini обрастал
        строкой из запятых (по запятой за каждый вызов).
        """
        names = sorted({n for n in cls.disabled if n != folder} |
                       ({folder} if value else set()))
        cls.set('disabled', ",".join(names))
        cls.disabled = names


class GameSettings(__Settings):
    section = 'game'
    clouds = config.getboolean(section, 'clouds')
    show_biomes = config.getboolean(section, 'show_biomes')
    stars = config.getboolean(section, 'stars')
    creatures = config.getboolean(section, 'creatures')
    vertical_tunel = config.getboolean(section, 'vertical_tunel')
    start_pos = tuple(map(int, config.get(section, 'start_pos').split(",")))
    view_item_index = config.getboolean(section, 'view_item_index')
    debug_open_map = config.getboolean(section, 'debug_open_map')
    all_languages = config.get(section, 'all_languages').replace(" ", "").split(",")
    language = config.get(section, 'language')
    max_fps = config.getint(section, 'max_fps', fallback=60)
    dynamic_dump = config.getboolean(section, 'dynamic_dump', fallback=True)
    vsync = config.getboolean(section, 'vsync', fallback=True)
    # Текущая цель сюжета одной строкой в углу экрана (units/Story.py).
    # Отключаемо: кому-то песочница нужна без единой подсказки.
    show_goal = config.getboolean(section, 'show_goal', fallback=True)
    # вид курсора: arrow/cross/cross_dot/corners/circle/system
    # (см. units/Graphics/Cursor.py CURSOR_KINDS)
    cursor = config.get(section, 'cursor', fallback='arrow')
    if language not in all_languages:
        language = "en"

    @classmethod
    def set_language(cls, language):
        cls.set("language", language)

    @classmethod
    def set_clouds_state(cls, state):
        cls.set("clouds", state)

    @classmethod
    def set_stars_state(cls, state):
        cls.set("stars", state)

    @classmethod
    def set_item_index_state(cls, state):
        cls.set("view_item_index", state)

    @classmethod
    def set_max_fps(cls, value):
        cls.set("max_fps", int(value))

    @classmethod
    def set_dynamic_dump(cls, state):
        cls.set("dynamic_dump", bool(state))

    @classmethod
    def set_vsync(cls, state):
        cls.set("vsync", bool(state))

    @classmethod
    def set_cursor(cls, value):
        cls.set("cursor", str(value))


class VolumeSettings(__Settings):
    section = 'sound'
    game_volume = config.getfloat(section, 'game_volume')
    ui_volume = config.getfloat(section, 'ui_volume')
    player_volume = config.getfloat(section, 'player_volume')
    creatures_volume = config.getfloat(section, 'creatures_volume')
    background_volume = config.getfloat(section, 'background_volume')
