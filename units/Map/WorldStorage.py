"""Хранилище миров: один мир = одна папка data/maps/<world_id>/
с meta.json (имя, даты, наигранное время — читается быстро для списка)
и world.dat (данные мира).

Старые сейвы game_map-N.pclv автоматически переносятся в новый формат.
"""
import glob
import json
import os
import shutil
import time

from units.common import GAMEMAPS_PATH, GAME_VERSION

META_FILE = "meta.json"
DATA_FILE = "world.dat"


def world_dir(world_id):
    return os.path.join(GAMEMAPS_PATH, world_id)


def data_path(world_id):
    return os.path.join(world_dir(world_id), DATA_FILE)


def load_meta(world_id):
    try:
        with open(os.path.join(world_dir(world_id), META_FILE), encoding="utf-8") as f:
            meta = json.load(f)
        meta["id"] = world_id
        return meta
    except (OSError, ValueError):
        return None


def save_meta(meta):
    os.makedirs(world_dir(meta["id"]), exist_ok=True)
    with open(os.path.join(world_dir(meta["id"]), META_FILE), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def touch_meta(world_id, playtime=None):
    """Обновить мету после сохранения мира."""
    meta = load_meta(world_id) or {"id": world_id, "name": world_id,
                                   "created": time.time(), "playtime": 0}
    meta["last_played"] = time.time()
    if playtime is not None:
        meta["playtime"] = playtime
    meta["game_version"] = GAME_VERSION
    save_meta(meta)
    return meta


def list_worlds():
    """Список миров (словари меты), самые свежие первыми."""
    migrate_legacy()
    worlds = []
    if not os.path.isdir(GAMEMAPS_PATH):
        return worlds
    for name in os.listdir(GAMEMAPS_PATH):
        if os.path.isdir(world_dir(name)):
            meta = load_meta(name)
            if meta is not None and os.path.exists(data_path(name)):
                worlds.append(meta)
    worlds.sort(key=lambda m: m.get("last_played", 0), reverse=True)
    return worlds


def new_world_meta(name=None):
    """Создать папку и мету нового мира с автоименем 'Мир N'."""
    i = 1
    while os.path.exists(world_dir(f"world-{i}")):
        i += 1
    world_id = f"world-{i}"
    if name is None:
        name = f"Мир {i}"
    meta = {"id": world_id, "name": name, "created": time.time(),
            "last_played": time.time(), "playtime": 0, "game_version": GAME_VERSION}
    save_meta(meta)
    return meta


def delete_world(world_id):
    d = world_dir(world_id)
    if os.path.isdir(d):
        shutil.rmtree(d)


def migrate_legacy():
    """Перенос старых сейвов game_map-N.pclv в папки миров."""
    for path in glob.glob(os.path.join(GAMEMAPS_PATH, "game_map-*.pclv")):
        num = os.path.basename(path)[len("game_map-"):-len(".pclv")]
        if "None" in num:
            os.remove(path)
            continue
        meta = new_world_meta(name=f"Мир #{num} (старый)")
        shutil.move(path, data_path(meta["id"]))
        print(f"WorldStorage: '{path}' перенесён в мир '{meta['id']}'")


def format_playtime(seconds):
    seconds = int(seconds or 0)
    h, m = seconds // 3600, seconds % 3600 // 60
    if h:
        return f"{h} ч {m} мин"
    return f"{m} мин"


def format_last_played(ts):
    if not ts:
        return ""
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts))
