from units.common import *


class Achievements:
    def __init__(self, owner):
        self.owner = owner
        self.completed = []
        self.murder_statistic = {}

    def new_completed(self, id_title):
        if id_title in achievements:
            if not self.is_completed(id_title):
                self.completed.append(id_title)
                self.owner.ui.new_achievement_completed(id_title)
                return True
        else:
            raise Exception(f"Not exist achievement {id_title}")

    def is_completed(self, id_title) -> bool:
        return id_title in self.completed

    def add_murder(self, obj):
        if obj.class_obj & OBJ_CREATURE:
            self.murder_statistic.setdefault(obj.bio_kingdom, 0)
            self.murder_statistic[obj.bio_kingdom] += 1
            self.murder_statistic.setdefault(obj.bio_species, 0)
            self.murder_statistic[obj.bio_species] += 1
            self.murder_statistic.setdefault(obj.bio_subspecies, 0)
            self.murder_statistic[obj.bio_subspecies] += 1
        else:
            self.murder_statistic.setdefault(type(obj), 0)
            self.murder_statistic[type(obj)] += 1

        if not self.is_completed("slimeI") and self.murder_statistic["slime"] == 10:
            self.new_completed("slimeI")
        elif not self.is_completed("slimeII") and self.murder_statistic["slime"] == 100:
            self.new_completed("slimeII")
        elif not self.is_completed("slimeIII") and self.murder_statistic["slime"] == 1000:
            self.new_completed("slimeIII")


achievements = {
    "space": {"title": "5 минут полёт нормальный...", "description": "Вы в открытом космосе",
              "action": "Вы должны попасть в открытый космос"},
    "hell": {"title": "Попасть в пекло", "description": "Вы попали в самый ад", "action": "Вы должны попасть в ад"},
    "killer": {"title": "Первое убийство", "description": "Вы впервые убили в этом мире",
               "action": "Вы должны убить любое существо"},
    "slimeI": {"title": "Уничтожитель слаймов I", "description": "Вы убили 10 слизней",
               "action": "Вы должны убить 10 слизней"},
    "slimeII": {"title": "Уничтожитель слаймов II", "description": "Вы убили 100 слаймов",
                "action": "Вы должны убить 100 слаймов"},
    "slimeIII": {"title": "Уничтожитель слаймов III", "description": "Вы убили 1000 слаймов",
                 "action": "Вы должны убить 1000 слаймов"},

}
