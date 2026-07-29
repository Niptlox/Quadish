"""Наполнение контейнеров: что лежит в сундуках и шкафах.

Задача. Структуры и подземелья ставят сундуки и шкафы, но пустые: тайл
создаётся вместе с объектом-инвентарём, а положить в него что-то никто не
успевал. Игрок находил склеп в песках, открывал сундук и получал ничего —
самое разочаровывающее, что может сделать находка.

Почему отдельным модулем, а не «списком предметов у структуры». Три причины:

* **Наполнение зависит от МЕСТА, а не от схемы.** Один и тот же сундук в
  забое на глубине 900 и в стоянке на поверхности должен давать разное:
  награда идёт по той же кривой, что и опасность (`docs/BALANCE_SCHEME.md`).
  Список у схемы этого не умеет.
* **Таблицы переиспользуются.** Подземелья не рисуются схемами вообще, а
  контейнер у них тот же самый.
* **Наполнение — это баланс, а не декорация.** Держать его в одном файле
  значит иметь одно место, где видно всю выдачу игры целиком.

Устройство: таблица `LootTable` = список (предмет, мин, макс, шанс).
Разыгрывается детерминированно по позиции контейнера — сундук, найденный
дважды (например после выгрузки и повторной генерации чанка), даёт то же
самое, а не новую порцию каждый раз.
"""
import random

from units.common import depth_reward

# Предметы (units/Tiles.py tile_words)
PLANKS, WOOD, STICK = 11, 12, 801
STONE, BRICK = 3, 31
SLIME, HIDE, WOLF_HIDE = 51, 56, 58
BERRY, MEAT = 53, 401
COPPER, IRON, GOLD, SILVER, RUBY, BLORE = 62, 64, 63, 65, 66, 61
SULFUR, DUST = 402, 408
TORCH_LAMP, WIRE, LEVER = 215, 213, 214
POTION, JUMP_POTION = 55, 351
PICKAXE_IRON, SWORD_IRON = 531, 501
BLORE_UP, BLORE_DOWN = 234, 236
TRAMPOLINE, TRACK = 237, 238


class LootTable:
    """Что и с какой вероятностью лежит в контейнере этого вида."""

    def __init__(self, name, entries, rolls=(2, 4)):
        self.name = name
        self.entries = entries          # (индекс, мин, макс, шанс)
        self.rolls = rolls              # сколько попыток выдачи

    def roll(self, rnd, deep=0.0):
        """Разыграть содержимое. deep 0..1 — поправка на глубину места.

        Глубина влияет на КОЛИЧЕСТВО, а не на состав: подменять состав значило
        бы иметь две несвязанные таблицы под одним именем, и отладить выдачу
        стало бы нельзя.
        """
        out = []
        for _ in range(rnd.randint(*self.rolls)):
            for index, low, high, chance in self.entries:
                if rnd.random() > chance:
                    continue
                count = rnd.randint(low, high)
                if deep:
                    count = max(count, int(round(count * (1 + deep))))
                out.append((index, count))
                break
        if not out:
            # Пустой контейнер — худший исход находки: игрок дошёл, открыл и
            # получил ничего. Все шансы могут не сработать разом, поэтому
            # минимум одну позицию выдаём принудительно.
            index, low, high, _ = self.entries[0]
            out.append((index, rnd.randint(low, high)))
        return out


# --- таблицы по видам мест ---------------------------------------------

SURFACE_HUT = LootTable("жильё", [
    (PLANKS, 4, 10, 0.40),
    (BERRY, 2, 5, 0.30),
    (STICK, 3, 8, 0.30),
    (HIDE, 1, 3, 0.20),
    (SLIME, 2, 5, 0.20),
    (COPPER, 1, 3, 0.15),
])

WATCHPOST = LootTable("дозор", [
    (IRON, 2, 5, 0.35),
    (COPPER, 2, 4, 0.30),
    (WIRE, 2, 6, 0.25),
    (TORCH_LAMP, 1, 2, 0.20),
    (POTION, 1, 1, 0.10),
])

MINE = LootTable("забой", [
    (IRON, 2, 5, 0.40),
    (BLORE, 1, 3, 0.30),
    (STONE, 6, 14, 0.30),
    (PICKAXE_IRON, 1, 1, 0.08),
    (SILVER, 1, 2, 0.15),
], rolls=(2, 4))

TEMPLE = LootTable("храм", [
    (BLORE, 2, 5, 0.35),
    (RUBY, 1, 2, 0.20),
    (GOLD, 1, 3, 0.20),
    (BLORE_UP, 2, 4, 0.15),
    (BLORE_DOWN, 2, 4, 0.15),
])

GREENHOUSE = LootTable("оранжерея", [
    (BERRY, 3, 8, 0.45),
    (WOOD, 4, 10, 0.30),
    (JUMP_POTION, 1, 1, 0.10),
    (SLIME, 3, 6, 0.25),
])

BUNKER = LootTable("бункер", [
    (IRON, 4, 8, 0.35),
    (SWORD_IRON, 1, 1, 0.12),
    (POTION, 1, 2, 0.20),
    (WIRE, 4, 10, 0.25),
    (LEVER, 1, 3, 0.20),
    (BLORE, 2, 4, 0.20),
], rolls=(3, 5))

# Сокровищницы: броски скромные. В самой комнате уже лежит рудная кладка
# (~6 блоков золота), и сундук должен быть приятной добавкой, а не второй
# наградой того же размера — иначе одно подземелье закрывает всю верхнюю
# часть лестницы материалов (docs/BALANCE_SCHEME.md).
CRYPT_VAULT = LootTable("сокровищница", [
    (SILVER, 2, 4, 0.35),
    (GOLD, 1, 3, 0.30),
    (RUBY, 1, 2, 0.25),
    (BLORE, 2, 4, 0.25),
    (PICKAXE_IRON, 1, 1, 0.08),
], rolls=(2, 3))

FORGE_VAULT = LootTable("кузня", [
    (SULFUR, 2, 5, 0.40),
    (BLORE, 2, 5, 0.30),
    (GOLD, 1, 3, 0.25),
    (RUBY, 1, 2, 0.20),
], rolls=(2, 3))

STATION_VAULT = LootTable("станция", [
    (DUST, 3, 6, 0.45),
    (SILVER, 2, 4, 0.30),
    (RUBY, 1, 2, 0.20),
    (TRACK, 2, 4, 0.15),
], rolls=(2, 3))

# Что положить, если про место ничего не известно. Не пусто: пустой сундук —
# худший исход находки, лучше скромно, но что-то.
DEFAULT = SURFACE_HUT

TABLES = {t.name: t for t in (SURFACE_HUT, WATCHPOST, MINE, TEMPLE, GREENHOUSE,
                              BUNKER, CRYPT_VAULT, FORGE_VAULT, STATION_VAULT)}

# Какая таблица какому виду подземелья соответствует (units/Map/Dungeons.py)
DUNGEON_TABLES = {"склеп": CRYPT_VAULT, "кузня": FORGE_VAULT, "станция": STATION_VAULT}


def table_for_place(kind_name=None, tile_y=0):
    """Таблица по названию места; если места нет — по глубине.

    Глубина как запасной признак нужна для контейнеров, о которых ничего не
    известно: сундук в схеме структуры не знает, в какой структуре он стоит.
    """
    if kind_name and kind_name in TABLES:
        return TABLES[kind_name]
    if kind_name and kind_name in DUNGEON_TABLES:
        return DUNGEON_TABLES[kind_name]
    if tile_y > 500:
        return MINE
    if tile_y > 120:
        return WATCHPOST
    return SURFACE_HUT


def fill_container(game, inventory, tx, ty, base, kind_name=None):
    """Наполнить инвентарь контейнера, стоящего в (tx, ty).

    Розыгрыш детерминирован по (сид, позиция): чанк выгружается и создаётся
    заново на ходу (`dynamic_dump`), и «новая порция при каждом заходе» была
    бы бесконечным источником золота.
    """
    if inventory is None:
        return []
    from units.Objects.Items import ItemsTile
    from units.Tools import TOOLS
    table = table_for_place(kind_name, ty)
    rnd = random.Random(f"loot:{base}:{tx}:{ty}")
    put = []
    for index, count in table.roll(rnd, depth_reward(ty)):
        if index in TOOLS:
            item = TOOLS[index](game, pos=(tx * 32, ty * 32))
        else:
            item = ItemsTile(game, index, (tx * 32, ty * 32), count)
        ok, _ = inventory.put_to_inventory(item)
        if ok:
            put.append((index, count))
    return put
