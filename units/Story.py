"""Акты сюжета и текущая цель игрока.

Сюжет в Quadish был написан (docs/STORY.md) и даже частично лежал в мире:
плиты с надписями, GameMap.read_inscriptions честно копил прочитанное. Не
хватало одного — читателя. Игрок находил плиту, читал строчку, и она уходила
в никуда: ни журнала, ни цели, ни ощущения, что он куда-то продвинулся.

Здесь это замыкается. Правила, на которых стоит система:

* **Цель проверяется по состоянию мира, а не по скрипту.** Ни одного «этап
  засчитан, потому что игрок нажал». Прочитал плиту — состояние изменилось,
  акт закрылся. Поэтому сюжет невозможно рассинхронизировать с игрой.
* **Прогресс необратим.** Выполненный акт остаётся выполненным, даже если
  условие потом перестало соблюдаться (предмет потрачен, инвентарь очищен).
  Иначе цель на экране прыгала бы назад, и это читалось бы как поломка.
* **Цель — подсказка, а не приказ.** Игру можно проходить мимо всех актов;
  сюжет ничего не запирает. Он отвечает на вопрос «а что вообще делать?»,
  который у песочницы без него не имеет ответа.
"""
from units.common import START_HELL_Y, START_SPACE_Y, DAY_LENGTH


class Act:
    """Один акт: заголовок, цель одной строкой и проверка выполнения."""

    def __init__(self, act_id, title, goal, check):
        self.id = act_id
        self.title = title
        self.goal = goal
        self._check = check

    def done(self, game):
        try:
            return bool(self._check(game))
        except Exception:
            # Сюжет не должен ронять игру: мир мог быть создан другой
            # версией и не иметь поля, на которое смотрит проверка.
            return False


def _read(game):
    return getattr(game.game_map, "read_inscriptions", None) or []


def _survived_night(game):
    """Пережита хотя бы одна полная ночь — считаем по часам мира."""
    return getattr(game.game_map, "world_time", 0) >= DAY_LENGTH


def _has_deep_blore(game):
    """Побывал на глубине и держал блоровую руду."""
    return "blore_deep" in _flags(game)


def _reached_edge(game):
    return "hell" in _flags(game) or "space" in _flags(game)


def _flags(game):
    gm = game.game_map
    flags = getattr(gm, "story_flags", None)
    if not isinstance(flags, list):
        flags = []
        gm.story_flags = flags
    return flags


def note_flag(game, flag):
    """Отметить необратимое событие сюжета. Возвращает True, если впервые."""
    flags = _flags(game)
    if flag in flags:
        return False
    flags.append(flag)
    return True


def _has_tile(game, ttile, radius=60):
    """Стоит ли такой блок где-то рядом с игроком.

    Радиусом, а не по всему миру: обход всей карты ради строчки на экране
    неоправдан, а «поставил у себя на базе» — именно то, что проверяется.
    """
    player = getattr(game, "player", None)
    if player is None:
        return False
    gm = game.game_map
    px, py = player.rect.centerx // 32, player.rect.centery // 32
    for cxy in {gm.to_chunk_xy(px + dx, py + dy)
                for dx in (-radius, 0, radius) for dy in (-radius, 0, radius)}:
        chunk = gm.game_map.get(cxy)
        if chunk is None:
            continue
        static = chunk[0]
        for i in range(0, len(static), 4):
            if static[i] == ttile:
                return True
    return False


ACTS = (
    Act("arrival", "Акт I. Где я",
        "Прочитай плиту алтаря — с неё всё начинается",
        lambda g: "altar" in _read(g)),
    Act("first_night", "Акт I. Где я",
        "Переживи первую ночь",
        _survived_night),
    Act("settle", "Акт I. Где я",
        "Обживись: поставь верстак и печку",
        lambda g: _has_tile(g, 121) and _has_tile(g, 131)),
    Act("traces", "Акт II. Их здесь не осталось",
        "Найди ещё две записи тех, кто жил здесь до тебя",
        lambda g: len(_read(g)) >= 3),
    Act("dispute", "Акт II. Их здесь не осталось",
        "Найди обсерваторию: там они спорили, уйти или позвать",
        lambda g: "observatory" in _read(g)),
    Act("shift_norm", "Акт II. Их здесь не осталось",
        "Найди забой и спустись глубже 300 — там писали норму на смену",
        lambda g: "mine_deep" in _read(g) and _depth(g) > 300),
    Act("blore", "Акт III. Чистый блор",
        "Спустись глубже и добудь блоровую руду — канал держится на ней",
        _has_deep_blore),
    Act("vault", "Акт III. Чистый блор",
        "Найди их шахту под землёй и дойди до сокровищницы",
        lambda g: "vault_looted" in _flags(g)),
    Act("last_ones", "Акт III. Чистый блор",
        "Найди бункер: последние держали канал с этой стороны",
        lambda g: "bunker_last" in _read(g)),
    Act("edge", "Акт IV. Уйти",
        "Дойди до края мира: вниз в ад или вверх в космос",
        _reached_edge),
    Act("portal", "Акт IV. Уйти",
        "Собери портал — повтори их работу",
        lambda g: _has_tile(g, 232)),
    Act("weight", "Акт IV. Уйти",
        "Оно приближается. Дождись, пока почувствуешь вес",
        lambda g: "weight_felt" in _flags(g)),
)


def _depth(game):
    player = getattr(game, "player", None)
    return 0 if player is None else player.rect.centery // 32

# Глубина, начиная с которой блор считается «чистым» (docs/STORY.md:
# «чем глубже — тем чище»)
DEEP_BLORE_Y = 500
BLORE_ORE_ITEM = 61


def check_world_flags(game):
    """Отметить необратимые события по текущему состоянию мира.

    Вызывается редко (раз в секунду), потому что смотрит в инвентарь: делать
    это каждый кадр ради строчки на экране незачем.
    """
    player = getattr(game, "player", None)
    if player is None:
        return
    ty = player.rect.centery // 32
    if ty >= START_HELL_Y:
        note_flag(game, "hell")
    if ty <= START_SPACE_Y:
        note_flag(game, "space")
    if ty >= DEEP_BLORE_Y and _has_item(player, BLORE_ORE_ITEM):
        note_flag(game, "blore_deep")
    # «Дошёл до сокровищницы» — по факту нахождения в ней, а не по открытию
    # сундука. Так же, как весь остальной сюжет: состояние мира, а не событие
    # интерфейса. Заодно не требует особого класса сундука — он был бы вторым
    # классом на тот же индекс тайла.
    if _in_vault(game, player):
        note_flag(game, "vault_looted")
    # «Вес» — финальная отметка: оно подошло достаточно близко, чтобы его
    # можно было почувствовать. Условие сюжетное, а не механическое: игрок
    # прошёл всё остальное и провёл в мире достаточно времени.
    if ("portal" in _done_ids(game)
            and getattr(game.game_map, "world_time", 0) > DAY_LENGTH * 6):
        note_flag(game, "weight_felt")


def _in_vault(game, player):
    """Стоит ли игрок в сокровищнице подземелья."""
    from units.Map.Dungeons import dungeon_at
    gm = game.game_map
    tx, ty = player.rect.centerx // 32, player.rect.centery // 32
    site = dungeon_at(tx, ty, gm.base_generation, getattr(gm, "dungeon_sites", None))
    return site is not None and site.room_at(tx, ty) == site.vault


def _has_item(player, index):
    inventory = getattr(player, "inventory", None)
    if inventory is None:
        return False
    return any(cell is not None and cell.index == index for cell in inventory)


def update_story(game):
    """Продвинуть сюжет. Возвращает акт, закрывшийся именно сейчас, или None."""
    check_world_flags(game)
    done = _done_ids(game)
    for act in ACTS:
        if act.id in done:
            continue
        if act.done(game):
            done.append(act.id)
            return act
        break          # акты идут по порядку: следующий не проверяем
    return None


def _done_ids(game):
    gm = game.game_map
    done = getattr(gm, "story_done", None)
    if not isinstance(done, list):
        done = []
        gm.story_done = done
    return done


def current_act(game):
    """Акт, над которым игрок работает сейчас. None — сюжет пройден."""
    done = _done_ids(game)
    for act in ACTS:
        if act.id not in done:
            return act
    return None


def current_goal(game):
    """Строка цели для HUD или None."""
    act = current_act(game)
    return act.goal if act is not None else None


def journal_entries(game):
    """Что показывать в журнале: акты с отметкой и прочитанные надписи."""
    from units.Lore import get_inscription
    done = set(_done_ids(game))
    acts = [(act.title, act.goal, act.id in done) for act in ACTS]
    notes = [get_inscription(i) for i in _read(game)]
    return acts, notes
