"""События мира: то, что происходит С игроком, а не по его команде.

Зачем вообще. До этого в Quadish не происходило ничего: мир был неподвижен
во времени, никто не угрожал, и база была декорацией — её строили, потому что
так принято, а не потому, что без неё плохо. Событие даёт игре второй голос:
не только «я решил пойти копать», но и «мне не дали спокойно копать».

Правила, которые держат систему:

* **Событие предупреждает о себе.** Налёт объявляется за несколько секунд до
  начала. Внезапная смерть из ниоткуда — это не сложность, а несправедливость,
  и ровно этого игра уже избегала при спавне существ (spawn_is_visible).
* **От события есть защита, и она строится заранее.** Свет отгоняет тварей
  (GameMap.lit_by_lamp), стены задерживают. Событие, от которого нельзя
  подготовиться, превращается в налог, а не в вызов.
* **Событие конечно.** У каждого есть длительность, после которой мир
  возвращается в норму — иначе это не событие, а новые правила.
"""
import random

from units.common import *


class WorldEvent:
    """База событий. Наследник задаёт условие, длительность и действие."""
    name = "событие"
    announce = ""
    # Сколько тактов идёт событие
    duration = FPS * 60
    # Минимальный промежуток между двумя запусками ЭТОГО события
    cooldown = FPS * 60 * 10
    # Насколько заранее предупреждаем игрока
    warning = FPS * 5

    def __init__(self):
        self.started_at = None
        self.warned_at = None
        self.last_end = -10 ** 9

    # ---------- расписание ----------

    def can_start(self, game, world_time):
        """Пора ли начинать. Наследник добавляет свои условия.

        Время передаётся аргументом, а не читается из карты: иначе у события
        два источника времени, и они расходятся ровно тогда, когда это трудно
        заметить."""
        return True

    def ready(self, game, world_time):
        if self.started_at is not None:
            return False
        if world_time - self.last_end < self.cooldown:
            return False
        return self.can_start(game, world_time)

    def tick(self, game, world_time):
        """Один такт жизни события: предупредить, начать, вести, закончить."""
        if self.started_at is None:
            if self.ready(game, world_time):
                if self.warned_at is None:
                    self.warned_at = world_time
                    self.on_warn(game)
                elif world_time - self.warned_at >= self.warning:
                    self.started_at = world_time
                    self.warned_at = None
                    self.on_start(game)
            elif self.warned_at is not None:
                # условие пропало, пока шло предупреждение — отменяем тихо
                self.warned_at = None
            return
        if world_time - self.started_at >= self.duration:
            self.last_end = world_time
            self.started_at = None
            self.on_end(game)
        else:
            self.on_tick(game, world_time)

    def active(self):
        return self.started_at is not None

    # ---------- что делает ----------

    def on_warn(self, game):
        if self.announce:
            self.message(game, self.announce)

    def on_start(self, game):
        pass

    def on_tick(self, game, world_time):
        pass

    def on_end(self, game):
        pass

    @staticmethod
    def message(game, text):
        ui = getattr(game, "ui", None)
        if ui is not None and hasattr(ui, "new_sys_message"):
            ui.new_sys_message(text)


class NightRaid(WorldEvent):
    """Ночной налёт: к игроку приходит волна, и приходит НЕ каждую ночь.

    Каждую ночь было бы расписанием, а не событием — игрок просто уходил бы
    под землю по часам. Раз в несколько ночей это уже риск, из-за которого
    имеет смысл держать освещённый периметр постоянно.
    """
    name = "ночной налёт"
    announce = "Тревога: что-то идёт сюда"
    duration = FPS * 50
    cooldown = FPS * 60 * 12
    # Сколько тварей за налёт и как часто они приходят
    WAVE = 6
    STEP = FPS * 6
    # Откуда приходят: за кромкой экрана, чтобы не рождались на глазах
    SPAWN_MIN = 22
    SPAWN_MAX = 34

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        # Только ночью и только на поверхности: в пещерах и в аду и так
        # хватает своих, а налёт под землёй читался бы как случайный спавн.
        if not is_night(world_time):
            return False
        ty = player.rect.centery // TSIZE
        return TOP_MIDDLE_WORLD < ty < 80

    def on_start(self, game):
        self.message(game, "Налёт начался")
        self.sent = 0

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % self.STEP:
            return
        if getattr(self, "sent", 0) >= self.WAVE:
            return
        self.sent = getattr(self, "sent", 0) + 1
        self.spawn_one(game)

    def on_end(self, game):
        self.message(game, "Стихло")

    def spawn_one(self, game):
        from units.Map.GameMap import spawn_creature
        from units.Objects.Creatures import Wolf, Slime, Snake, Bat
        player = game.player
        gm = game.game_map
        side = random.choice((-1, 1))
        tx = player.rect.centerx // TSIZE + side * random.randint(self.SPAWN_MIN, self.SPAWN_MAX)
        ty = gm.surface_top_at(tx, player.rect.centery // TSIZE)
        if ty is None:
            return
        # Свет отгоняет и налётчиков: периметр из ламп работает против события
        # так же, как против обычного ночного спавна. Иначе защита была бы
        # бессмысленной ровно тогда, когда она нужнее всего.
        if gm.lit_by_lamp(tx, ty):
            return
        Crt = random.choice((Wolf, Slime, Snake, Bat))
        creature = spawn_creature(Crt, game, tx, ty)
        creature.provoked = True            # идут именно к игроку
        gm.add_dinamic_obj(*gm.to_chunk_xy(tx, ty), creature)


class BloreRift(WorldEvent):
    """Блоровый разлом: в глубине ненадолго рвётся ткань перехода.

    По сюжету переход держится на блоре (docs/STORY.md), и разлом — это его
    сбой. Событие глубины: наверху его не бывает, поэтому оно ощущается как
    свойство места, куда игрок полез сам, а не как случайная неприятность.
    """
    name = "блоровый разлом"
    announce = "Порода гудит — где-то рядом рвётся"
    duration = FPS * 40
    cooldown = FPS * 60 * 15
    DEPTH = 400            # глубже этого

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        ty = player.rect.centery // TSIZE
        return self.DEPTH < ty < START_HELL_Y

    def on_start(self, game):
        self.message(game, "Разлом открылся")
        self.sent = 0

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % (FPS * 8):
            return
        if getattr(self, "sent", 0) >= 4:
            return
        self.sent = getattr(self, "sent", 0) + 1
        from units.Map.GameMap import spawn_creature
        from units.Objects.Creatures import Imp, Slime
        player, gm = game.player, game.game_map
        tx = player.rect.centerx // TSIZE + random.choice((-1, 1)) * random.randint(18, 28)
        ty = player.rect.centery // TSIZE + random.randint(-4, 4)
        if gm.get_static_tile_type(tx, ty, default=0, create_chunk=False):
            return                          # в породе не рождаем
        creature = spawn_creature(random.choice((Imp, Slime)), game, tx, ty)
        creature.provoked = True
        gm.add_dinamic_obj(*gm.to_chunk_xy(tx, ty), creature)

    def on_end(self, game):
        self.message(game, "Разлом затянулся")


class EventDirector:
    """Кто решает, какое событие запускать. Одно за раз.

    Одно за раз — намеренно: два наложившихся события игрок читает как «игра
    сломалась», а не как «сегодня тяжёлая ночь».
    """

    def __init__(self):
        self.events = [NightRaid(), BloreRift()]

    def current(self):
        for e in self.events:
            if e.active():
                return e
        return None

    def update(self, game):
        world_time = getattr(game.game_map, "world_time", 0)
        busy = self.current()
        for event in self.events:
            if busy is not None and event is not busy:
                continue
            event.tick(game, world_time)
