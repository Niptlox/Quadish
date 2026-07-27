"""Загрузка модификаций (модов) из data/modifications/<имя>/mod.json.

Мод может добавлять блоки, предметы, существа и анимации, не трогая код
игры. Регистрация идёт в те же самые структуры, что и у ванильного
контента (`tile_imgs`, `TILES_SOLIDITY`, `CREATURES`, `RECIPES` и т.д.),
поэтому моды получают всё поведение базовой игры бесплатно: копание,
крафт, выпадение предметов, спавн по биомам.

Модуль намеренно не импортирует ни units.common, ни units.Tiles — только
pygame и units.config. Иначе получился бы цикл импортов: units.Tiles
должен уметь спросить у нас список блоков ещё во время своей загрузки.

Ошибка в одном моде никогда не роняет игру: мод помечается сломанным,
причина пишется в MOD_ERRORS и печатается в консоль, остальные моды
продолжают грузиться.
"""
import json
import os

import pygame

import units.config as config

# Пути ниже относительны корня проекта — units.config при импорте уже
# сделал chdir в корень (в т.ч. для собранной exe-версии).
MODS_PATH = os.path.join("data", "modifications")

# id ниже этого зарезервированы ванильной игрой (максимум базы — 1003).
# Мод, который попробует занять базовый id, будет отклонён — иначе он
# молча переопределил бы, например, камень.
MOD_ID_MIN = 2000

TILE_RECT = (32, 32)

MODS = []          # успешно загруженные моды
MOD_ERRORS = []    # [(имя папки, текст ошибки)] — показываем в настройках

# Реестр анимаций общий с ванильными тайлами и живёт в units/Tiles.py
# (там же лава). Держать здесь свою копию значило бы, что мод и ваниль
# анимируются двумя разными механизмами.


class ModError(Exception):
    """Мод описан неверно; текст сообщения показывается пользователю."""


def _require(cond, message):
    if not cond:
        raise ModError(message)


def _parse_color(value, where):
    """Цвет как '#RRGGBB' или [r, g, b]."""
    try:
        if isinstance(value, str):
            return pygame.Color(value)
        if isinstance(value, (list, tuple)) and 3 <= len(value) <= 4:
            return pygame.Color(*[int(c) for c in value])
    except (ValueError, TypeError):
        pass
    raise ModError(f"{where}: цвет должен быть '#RRGGBB' или [r, g, b], а не {value!r}")


def _parse_id(value, where, used_ids):
    _require(isinstance(value, int) and not isinstance(value, bool),
             f"{where}: 'id' должен быть целым числом, а не {value!r}")
    _require(value >= MOD_ID_MIN,
             f"{where}: id {value} занят базовой игрой — используйте id от {MOD_ID_MIN}")
    _require(value not in used_ids,
             f"{where}: id {value} уже занят другим модом или блоком этого же мода")
    used_ids.add(value)
    return value


def _parse_count(value, where):
    """Количество: число или [минимум, максимум]."""
    if isinstance(value, int) and not isinstance(value, bool):
        _require(value >= 0, f"{where}: количество не может быть отрицательным")
        return value
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lo, hi = value
        _require(all(isinstance(v, int) for v in (lo, hi)) and 0 <= lo <= hi,
                 f"{where}: диапазон количества должен быть [мин, макс], мин <= макс")
        return (lo, hi)
    raise ModError(f"{where}: количество — число или [мин, макс], а не {value!r}")


def _parse_drops(raw, where):
    """[[id, количество, шанс], ...] — шанс необязателен (по умолчанию 1)."""
    drops = []
    for i, entry in enumerate(raw or ()):
        w = f"{where}: выпадение #{i + 1}"
        _require(isinstance(entry, (list, tuple)) and 2 <= len(entry) <= 3,
                 f"{w}: ожидается [id, количество] или [id, количество, шанс]")
        idx, count = entry[0], _parse_count(entry[1], w)
        chance = entry[2] if len(entry) == 3 else 1
        _require(isinstance(idx, int), f"{w}: id должен быть числом")
        _require(isinstance(chance, (int, float)) and 0 < chance <= 1,
                 f"{w}: шанс должен быть в диапазоне (0, 1]")
        drops.append((idx, count, chance))
    return drops


def _parse_recipe(raw, where):
    """[[id_ингредиента, количество], ...]; количество -1 = "нужен рядом"
    (верстак/котёл), как в units/creating_items.py."""
    if raw is None:
        return None
    items = []
    for i, entry in enumerate(raw):
        w = f"{where}: ингредиент #{i + 1}"
        _require(isinstance(entry, (list, tuple)) and len(entry) == 2,
                 f"{w}: ожидается [id, количество]")
        idx, count = entry
        _require(isinstance(idx, int), f"{w}: id должен быть числом")
        _require(isinstance(count, int) and (count > 0 or count == -1),
                 f"{w}: количество > 0, либо -1 (предмет должен быть рядом)")
        items.append((idx, count))
    _require(items, f"{where}: рецепт не может быть пустым")
    return items


def _parse_sprite(spec, mod_dir, where, size=TILE_RECT):
    """Спрайт: либо файл ('sprite'), либо процедурный по цвету ('color').

    Возвращает (кадры, скорость). Кадров больше одного — тайл анимирован.
    """
    from units.Graphics.Image import create_tile_image, load_img

    speed = spec.get("animation", {}).get("speed", 6) if isinstance(spec.get("animation"), dict) else 6
    _require(isinstance(speed, (int, float)) and speed > 0,
             f"{where}: 'animation.speed' должен быть положительным числом")

    anim = spec.get("animation")
    if anim is not None:
        _require(isinstance(anim, dict), f"{where}: 'animation' должен быть объектом")
        colors, files = anim.get("colors"), anim.get("frames")
        _require(bool(colors) != bool(files),
                 f"{where}: в 'animation' задайте либо 'colors', либо 'frames' (что-то одно)")
        if colors:
            _require(len(colors) >= 2, f"{where}: 'animation.colors' — минимум 2 цвета")
            frames = [create_tile_image(_parse_color(c, where), size=size) for c in colors]
        else:
            _require(len(files) >= 2, f"{where}: 'animation.frames' — минимум 2 файла")
            frames = [_load_mod_image(f, mod_dir, where, size, load_img) for f in files]
        return frames, speed

    if spec.get("sprite"):
        return [_load_mod_image(spec["sprite"], mod_dir, where, size, load_img)], speed

    # Пиксель-арт: своя сетка ('pixels') или готовая форма по имени ('shape').
    # Без этого мод мог задать только плоский квадрат цветом.
    if spec.get("pixels") or spec.get("shape"):
        return [_build_mod_pixels(spec, where, size)], speed

    _require("color" in spec, f"{where}: нужен 'color', 'sprite', 'pixels', 'shape' или 'animation'")
    return [create_tile_image(_parse_color(spec["color"], where), size=size)], speed


def _build_mod_pixels(spec, where, size):
    """Спрайт из сетки пикселей (как у ванильных предметов и существ).

    'pixels' — свои строки, 'shape' — имя готовой формы (см. ItemSprites.SHAPES),
    чтобы мод мог взять «кристалл» или «мясо», не рисуя их заново. Базовый
    цвет берётся из 'color', от него считаются оттенки."""
    from units.Graphics.PixelArt import build_sprite, PixelArtError
    from units.ItemSprites import SHAPES

    rows = spec.get("pixels")
    if rows is None:
        shape = spec["shape"]
        _require(isinstance(shape, str) and shape in SHAPES,
                 f"{where}: 'shape' должен быть одним из {', '.join(sorted(SHAPES))}, а не {shape!r}")
        rows = SHAPES[shape]
    else:
        _require(isinstance(rows, list) and rows and all(isinstance(r, str) for r in rows),
                 f"{where}: 'pixels' — список строк одинаковой длины")

    base = spec.get("color", "#FFFFFF")
    try:
        return build_sprite(rows, base=_parse_color(base, where), size=size)
    except PixelArtError as exc:
        raise ModError(f"{where}: {exc}")


def _load_mod_image(rel_path, mod_dir, where, size, load_img):
    _require(isinstance(rel_path, str), f"{where}: путь к спрайту должен быть строкой")
    # Не выпускаем мод за пределы его папки (никаких '../../secrets.png').
    full = os.path.normpath(os.path.join(mod_dir, rel_path))
    _require(os.path.commonpath([os.path.abspath(full), os.path.abspath(mod_dir)]) == os.path.abspath(mod_dir),
             f"{where}: путь '{rel_path}' выходит за пределы папки мода")
    _require(os.path.isfile(full), f"{where}: файл спрайта не найден: {rel_path}")
    try:
        return load_img(full, size=size)
    except pygame.error as exc:
        raise ModError(f"{where}: не удалось загрузить спрайт '{rel_path}': {exc}")


def _parse_block(spec, mod_dir, used_ids, is_item):
    kind = "предмет" if is_item else "блок"
    _require(isinstance(spec, dict), f"{kind}: описание должно быть объектом")
    name = spec.get("name")
    _require(isinstance(name, str) and name.strip(), f"{kind}: нужно непустое 'name'")
    where = f"{kind} '{name}'"
    tile_id = _parse_id(spec.get("id"), where, used_ids)

    frames, speed = _parse_sprite(spec, mod_dir, where)
    solidity = spec.get("solidity", 30)
    _require(isinstance(solidity, int) and solidity > 0,
             f"{where}: 'solidity' (прочность) должна быть положительным числом")

    eat = spec.get("eat")
    if eat is not None:
        _require(isinstance(eat, int) and eat > 0, f"{where}: 'eat' — сколько лечит, положительное число")

    return {
        "id": tile_id,
        "name": name,
        "frames": frames,
        "speed": speed,
        "solidity": solidity,
        "is_item": is_item,
        "physical": bool(spec.get("physical", not is_item)),
        "eat": eat,
        "drops": _parse_drops(spec.get("drops"), where),
        "recipe": _parse_recipe(spec.get("recipe"), where),
        "recipe_count": spec.get("recipe_count", 1),
    }


# Существу мода нужен базовый класс из ванили — он задаёт поведение
# (Slime прыгает, Wolf ходит и агрится). Список закрытый: так мод не
# может подставить произвольный класс игры.
CREATURE_BASES = ("Slime", "Cow", "Wolf", "Snake", "Imp", "Scorpion",
                  "Rabbit", "Deer", "Fox", "Camel", "Penguin", "Boar",
                  "Crab", "Bat", "StoneGolem", "SpaceDrifter")

# Куда существо может спавниться — те же зоны, что у ванильного
# random_creature_selection (units/Map/GameMap.py).
SPAWN_ZONES = ("space", "hell", "caves", "surface")


def _parse_creature(spec, used_names):
    _require(isinstance(spec, dict), "существо: описание должно быть объектом")
    name = spec.get("name")
    _require(isinstance(name, str) and name.strip(), "существо: нужно непустое 'name'")
    where = f"существо '{name}'"

    id_name = spec.get("id_name")
    _require(isinstance(id_name, str) and id_name.isidentifier(),
             f"{where}: 'id_name' должен быть латинским идентификатором (например AzureSlime)")
    _require(id_name not in used_names, f"{where}: 'id_name' {id_name} уже занят")
    used_names.add(id_name)

    base = spec.get("base", "Slime")
    _require(base in CREATURE_BASES,
             f"{where}: 'base' должен быть одним из {', '.join(CREATURE_BASES)}, а не {base!r}")

    lives = spec.get("lives", 20)
    _require(isinstance(lives, int) and lives > 0, f"{where}: 'lives' — положительное число")
    damage = spec.get("damage", 0)
    _require(isinstance(damage, int) and damage >= 0, f"{where}: 'damage' — неотрицательное число")

    size = spec.get("size", [32, 32])
    _require(isinstance(size, (list, tuple)) and len(size) == 2
             and all(isinstance(v, int) and v > 0 for v in size),
             f"{where}: 'size' — [ширина, высота] в пикселях, положительные числа")

    spawn = spec.get("spawn") or {}
    _require(isinstance(spawn, dict), f"{where}: 'spawn' должен быть объектом")
    zone = spawn.get("zone", "surface")
    _require(zone in SPAWN_ZONES,
             f"{where}: 'spawn.zone' — одно из {', '.join(SPAWN_ZONES)}, а не {zone!r}")
    biomes = spawn.get("biomes")
    if biomes is not None:
        _require(isinstance(biomes, (list, tuple)) and biomes
                 and all(isinstance(b, int) for b in biomes),
                 f"{where}: 'spawn.biomes' — список номеров биомов (0..9)")
        biomes = tuple(biomes)
    weight = spawn.get("weight", 3)
    _require(isinstance(weight, (int, float)) and weight > 0,
             f"{where}: 'spawn.weight' — положительное число (вес в жеребьёвке)")

    return {
        "id_name": id_name,
        "name": name,
        "base": base,
        "color": str(spec.get("color", "#38BDF8")),
        "lives": lives,
        "damage": damage,
        "enemy": bool(spec.get("enemy", damage > 0)),
        "size": tuple(size),
        "speed": spec.get("speed", 3),
        "drops": _parse_drops(spec.get("drops"), where),
        "zone": zone,
        "biomes": biomes,
        "weight": weight,
    }


def _load_one(mod_dir, used_ids, used_names):
    manifest = os.path.join(mod_dir, "mod.json")
    _require(os.path.isfile(manifest), "нет файла mod.json")
    try:
        with open(manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ModError(f"mod.json — некорректный JSON: {exc}")
    except OSError as exc:
        raise ModError(f"не удалось прочитать mod.json: {exc}")
    _require(isinstance(data, dict), "mod.json должен содержать объект")

    name = data.get("name") or os.path.basename(mod_dir)
    blocks = [_parse_block(b, mod_dir, used_ids, is_item=False) for b in data.get("blocks", [])]
    items = [_parse_block(b, mod_dir, used_ids, is_item=True) for b in data.get("items", [])]
    creatures = [_parse_creature(c, used_names) for c in data.get("creatures", [])]
    _require(blocks or items or creatures,
             "мод ничего не добавляет — нужен хотя бы один блок, предмет или существо")
    return {
        "name": str(name),
        "version": str(data.get("version", "1.0")),
        "author": str(data.get("author", "")),
        "dir": mod_dir,
        "blocks": blocks + items,
        "creatures": creatures,
    }


def load_mods(path=None):
    """Прочитать все моды. Возвращает (моды, ошибки) и заполняет MODS/MOD_ERRORS."""
    MODS.clear()
    MOD_ERRORS.clear()

    if not config.ModSettings.enabled:
        print("Моды: загрузка отключена в настройках")
        return MODS, MOD_ERRORS

    root = path or MODS_PATH
    if not os.path.isdir(root):
        return MODS, MOD_ERRORS

    used_ids, used_names = set(), set()
    for entry in sorted(os.listdir(root)):
        mod_dir = os.path.join(root, entry)
        if not os.path.isdir(mod_dir):
            continue
        try:
            MODS.append(_load_one(mod_dir, used_ids, used_names))
        except ModError as exc:
            MOD_ERRORS.append((entry, str(exc)))
            print(f"Мод '{entry}' не загружен: {exc}")
        except Exception as exc:  # noqa: BLE001 — мод не должен ронять игру
            MOD_ERRORS.append((entry, f"неожиданная ошибка: {exc}"))
            print(f"Мод '{entry}' не загружен (неожиданная ошибка): {exc}")

    for mod in MODS:
        print(f"Мод загружен: {mod['name']} {mod['version']} — "
              f"блоков/предметов: {len(mod['blocks'])}, существ: {len(mod['creatures'])}")
    return MODS, MOD_ERRORS


def mod_blocks():
    for mod in MODS:
        for block in mod["blocks"]:
            yield block


def mod_creatures():
    for mod in MODS:
        for creature in mod["creatures"]:
            yield creature


def update_tile_animations(tile_imgs, tact, animated=None):
    """Подменить кадры анимированных тайлов прямо в tile_imgs.

    Вызывается раз в игровой такт из GameScene.update(). Мутируем словарь
    по месту — все модули сделали `from units.Tiles import *` и держат
    ссылку на этот же объект, так что новый кадр видят все.
    """
    if animated is None:
        from units.Tiles import ANIMATED_TILES as animated
    for tile_id, anim in animated.items():
        frames = anim["frames"]
        # speed — кадров в секунду; FPS-такт игры даёт номер кадра
        i = int(tact * anim["speed"] / max(1, anim["fps"])) % len(frames)
        tile_imgs[tile_id] = frames[i]
