import os

from configparser import ConfigParser

config_filename = os.getcwd() + '\settings.ini'
print("config_filename", config_filename)
config = ConfigParser()
config.read(config_filename)


def config_save():
    with open(config_filename, 'w') as configfile:
        config.write(configfile)


class __Settings:
    config = config
    section = ""

    @classmethod
    def set(cls, var_name, var_value):
        print(cls.section, var_name, var_value)
        config.set(cls.section, var_name, str(var_value))
        config_save()
        if var_name in cls.__dict__:
            if isinstance(var_value, str):
                var_value = '"' + var_value + '"'
            exec(f"cls.{var_name} = {var_value}")
        print(cls.__dict__[var_name])


class Window(__Settings):
    section = 'window'
    size = config.get(section, 'size')
    fullscreen = config.getboolean(section, 'fullscreen')

    @classmethod
    def set_fullscreen(cls, value):
        cls.set('fullscreen', str(value))

    @classmethod
    def set_size(cls, value):
        cls.set('size', str(value))


class UISettings(__Settings):
    section = 'UI'
    show_title_menu = config.getboolean(section, 'show_title_menu')


class GameSettings(__Settings):
    section = 'game'
    clouds = config.getboolean(section, 'clouds')
    show_biomes = config.getboolean(section, 'show_biomes')
    stars = config.getboolean(section, 'stars')
    creatures = config.getboolean(section, 'creatures')
    vertical_tunel = config.getboolean(section, 'vertical_tunel')
    start_pos = tuple(map(int, config.get(section, 'start_pos').split(",")))
    view_item_index = config.getboolean(section, 'view_item_index')

    @classmethod
    def set_clouds_state(cls, state):
        cls.set("clouds", state)

    @classmethod
    def set_stars_state(cls, state):
        cls.set("stars", state)

    @classmethod
    def set_item_index_state(cls, state):
        cls.set("view_item_index", state)


class VolumeSettings(__Settings):
    section = 'sound'
    game_volume = config.getfloat(section, 'game_volume')
    ui_volume = config.getfloat(section, 'ui_volume')
    player_volume = config.getfloat(section, 'player_volume')
    creatures_volume = config.getfloat(section, 'creatures_volume')
    back_music_volume = config.getfloat(section, 'back_music_volume')


# https://stackoverflow.com/questions/8884188/how-to-read-and-write-ini-file-with-python3
# string_val = config.get('section_a', 'string_val')
# bool_val = config.getboolean('section_a', 'bool_val')
# int_val = config.getint('section_a', 'int_val')
# float_val = config.getfloat('section_a', 'pi_val')
# config.add_section('section_b')
# config.set('section_b', 'meal_val', 'spam')
# config.set('section_b', 'not_found_val', '404')
#
# # save to a file
#
