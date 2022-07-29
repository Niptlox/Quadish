import os

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser  # ver. < 3.0

config_filename = os.getcwd()+'\settings.ini'

config = ConfigParser()
config.read(config_filename)


def config_save():
    with open(config_filename, 'w') as configfile:
        config.write(configfile)


class Window:
    config = config
    section = 'window'
    size = tuple(map(int, config.get(section, 'size').split(",")))
    fullscreen = config.getboolean(section, 'fullscreen')

    @classmethod
    def set_fullscreen(cls, value):
        config.set(cls.section, 'fullscreen', str(value))
        config_save()


class GameSettings:
    config = config
    section = 'game'
    clouds = config.getboolean(section, 'clouds')
    creatures = config.getboolean(section, 'creatures')
    vertical_tunel = config.getboolean(section, 'vertical_tunel')
    start_pos = tuple(map(int, config.get(section, 'start_pos').split(",")))

    @classmethod
    def set_clouds_state(cls, state):
        config.set(cls.section, "clouds", state)

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
