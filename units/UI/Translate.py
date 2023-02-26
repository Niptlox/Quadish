import json
import units.config as config
import os

# =============================== Translations ===============================
CWDIR = os.getcwd() + "/"
TRANSLATIONS_PATH = CWDIR + "data/translations/"


class Translate:
    def __init__(self):
        self.lang = config.GameSettings.language
        self.path_to_translate = os.path.join(TRANSLATIONS_PATH, self.lang + ".json")
        self.translates = {}
        self.load_translates()

    def load_translates(self):
        with open(self.path_to_translate, "r") as f:
            self.translates = json.load(f)
        pass

    def get_translated_text(self, text):
        return self.translates.get(text, text)


def load_translates(path_to_translate):
    with open(path_to_translate, "r", encoding="utf-8") as f:
        txt = f.read().encode("utf-8")
        _translates = json.loads(txt)
    return _translates


def get_translated_tiles(tiles):
    _path_to_translate = os.path.join(TRANSLATIONS_PATH, "game_" + lang + ".json")
    _translates_tiles = load_translates(_path_to_translate)["tiles"]
    return {i: _translates_tiles.get(text, text) for i, text in tiles.items()}


def get_translated_text_to_lang(text, lang):
    _path_to_translate = os.path.join(TRANSLATIONS_PATH, lang + ".json")
    _translates = load_translates(_path_to_translate)
    return _translates.get(text, text)


def get_translated_text(text):
    return translates.get(text, text)


def get_translated_lst_text(lst_text):
    return [get_translated_text(text) for text in lst_text]


def get_translated_dict_text(dict_text):
    return {i: get_translated_text(text) for i, text in dict_text.items()}


def get_translated_help():
    _path_to_file = os.path.join(TRANSLATIONS_PATH, "help_" + lang + ".md")
    with open(_path_to_file, "r", encoding="utf-8") as f:
        return f.read()


lang = config.GameSettings.language
print("Language:", lang)
path_to_translate = os.path.join(TRANSLATIONS_PATH, lang + ".json")
translates = load_translates(path_to_translate)
print(translates)
