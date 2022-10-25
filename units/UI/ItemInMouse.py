from typing import Union
from units.Objects.Items import Items

# OBJECT IN MOUSE =============================================
__object_in_mouse = None
__place_of_object_in_mouse = (None, -1)


def set_obj_mouse(obj, place=None):
    global __object_in_mouse, __place_of_object_in_mouse
    __object_in_mouse = obj
    __place_of_object_in_mouse = place


def get_obj_mouse() -> Union[Items, None]:
    return __object_in_mouse


def get_place_obj_mouse() -> tuple:
    return __place_of_object_in_mouse
