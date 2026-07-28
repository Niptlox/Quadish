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


ACTS = (
    Act("arrival", "Акт I. Где я",
        "Прочитай плиту алтаря — с неё всё начинается",
        lambda g: "altar" in _read(g)),
    Act("first_night", "Акт I. Где я",
        "Переживи первую ночь",
        _survived_night),
    Act("traces", "Акт II. Их здесь не осталось",
        "Найди ещё две записи тех, кто жил здесь до тебя",
        lambda g: len(_read(g)) >= 3),
    Act("blore", "Акт III. Чистый блор",
        "Спустись глубже и добудь блоровую руду — канал держится на ней",
        _has_deep_blore),
    Act("edge", "Акт IV. Уйти",
        "Дойди до края мира: вниз в ад или вверх в космос",
        _reached_edge),
)

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
