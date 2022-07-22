import json


def to_int(string: str, param=None):
    if string.isdigit():
        return int(string)
    else:
        raise Exception(f"Ошибка загрузки мода. Параметр {param} должен быть числом")


def get_int(d, param, default=0):
    return to_int(d.get(param, default), param)


def load_mod(mod_path):
    data_objs = json.load(mod_path + "/objects.json")
    language = data_objs["language"]
    last_id = 5000
    if language == "ru":
        plants = data_objs["блоки"]["растения"]
        for plant in plants:
            last_id += 1
            id_obj = last_id
            id_name = plant.get("id_name", f"id-{id_obj}")
            name = plant.get("имя")
            capability = get_int(plant, "прочность", 0)
            name = plant.get("имя")
            name = plant.get("имя")
            name = plant.get("имя")


load_mod(mod_path="data/modifications/first")
