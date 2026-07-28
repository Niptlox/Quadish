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


class MeteorShower(WorldEvent):
    """Метеоритный дождь: с неба падает то, за чем иначе надо лететь в космос.

    Событие-награда, а не только угроза, и это осознанно. Если КАЖДОЕ событие
    бьёт, они сливаются в один ровный стресс, и игрок начинает пережидать их
    все одинаково — в яме. Дождь опасен только там, куда падает, зато
    оставляет космическую пыль на поверхности: единственный способ увидеть
    материал верхней зоны, ещё не добравшись до неё.
    """
    name = "метеоритный дождь"
    announce = "Небо чертят полосы"
    duration = FPS * 45
    cooldown = FPS * 60 * 14
    STEP = FPS * 4
    SPREAD = 26            # в скольких тайлах вокруг игрока падают
    CRATER = 2             # радиус воронки

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        if not is_night(world_time):
            return False
        ty = player.rect.centery // TSIZE
        return TOP_MIDDLE_WORLD < ty < 60

    def on_start(self, game):
        self.message(game, "Метеоритный дождь")

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % self.STEP:
            return
        self.drop_one(game)

    def drop_one(self, game):
        gm, player = game.game_map, game.player
        tx = player.rect.centerx // TSIZE + random.randint(-self.SPREAD, self.SPREAD)
        ty = gm.surface_top_at(tx, player.rect.centery // TSIZE)
        if ty is None:
            return
        r = self.CRATER
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy > r * r:
                    continue
                # create_chunk=False: событие не должно создавать мир —
                # то же правило, что и у обслуживания за экраном
                if gm.get_static_tile_type(tx + dx, ty + dy, 0, create_chunk=False):
                    gm.set_static_tile(tx + dx, ty + dy, 0, create_chunk=False)
        # На дне воронки — то, ради чего это стоит пережидать не в яме
        prize = 408 if random.random() < 0.7 else 66        # пыль или рубин
        gm.add_item_of_index(prize, random.randint(1, 2), tx, ty)


class Migration(WorldEvent):
    """Миграция: мимо проходит стадо. Не угроза вообще.

    Нужна ровно затем, чтобы «событие» не стало синонимом «нападение». Игра,
    в которой мир подаёт голос только чтобы ударить, читается как враждебная
    целиком; здесь мир иногда просто идёт мимо, и это даёт передышку и еду.
    """
    name = "миграция"
    announce = "Издалека слышен топот"
    duration = FPS * 40
    cooldown = FPS * 60 * 10
    STEP = FPS * 3
    HERD = 8

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        if is_night(world_time):
            return False                    # днём: это не ночное явление
        ty = player.rect.centery // TSIZE
        return TOP_MIDDLE_WORLD < ty < 60

    def on_start(self, game):
        self.message(game, "Мимо идёт стадо")
        self.sent = 0
        self.side = random.choice((-1, 1))

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % self.STEP:
            return
        if getattr(self, "sent", 0) >= self.HERD:
            return
        self.sent = getattr(self, "sent", 0) + 1
        from units.Map.GameMap import spawn_creature
        from units.Objects.Creatures import Cow, Deer, Boar, Rabbit
        gm, player = game.game_map, game.player
        tx = player.rect.centerx // TSIZE + self.side * random.randint(20, 30)
        ty = gm.surface_top_at(tx, player.rect.centery // TSIZE)
        if ty is None:
            return
        creature = spawn_creature(random.choice((Cow, Deer, Boar, Rabbit)), game, tx, ty)
        gm.add_dinamic_obj(*gm.to_chunk_xy(tx, ty), creature)


class GolemAwakening(WorldEvent):
    """Гон големов: в глубоких пещерах порода начинает шевелиться.

    Событие места, а не времени: оно бывает только там, куда игрок полез сам.
    И оно выгодное — лут существ считается с поправкой на опасность места
    (docs/BALANCE_SCHEME.md), так что глубокий голем стоит боя.
    """
    name = "гон големов"
    announce = "Камень вокруг гудит"
    duration = FPS * 45
    cooldown = FPS * 60 * 16
    DEPTH = 600

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        ty = player.rect.centery // TSIZE
        return self.DEPTH < ty < START_HELL_Y

    def on_start(self, game):
        self.message(game, "Големы просыпаются")
        self.sent = 0

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % (FPS * 12):
            return
        if getattr(self, "sent", 0) >= 3:
            return
        self.sent = getattr(self, "sent", 0) + 1
        _spawn_near(game, "StoneGolem", 14, 22)

    def on_end(self, game):
        self.message(game, "Порода затихла")


class SolarFlare(WorldEvent):
    """Солнечная вспышка: в космосе прилетает волна.

    В вакууме прятаться негде — там нет ни рельефа, ни ночи. Поэтому у
    космоса своё событие: единственная защита от него это уйти в тень
    астероида, то есть место, а не постройка.
    """
    name = "вспышка"
    announce = "Приборы слепнут: идёт вспышка"
    duration = FPS * 35
    cooldown = FPS * 60 * 13

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        return player.rect.centery // TSIZE <= START_ATMO_Y

    def on_start(self, game):
        self.message(game, "Вспышка")
        self.sent = 0

    def on_tick(self, game, world_time):
        if (world_time - self.started_at) % (FPS * 7):
            return
        if getattr(self, "sent", 0) >= 4:
            return
        self.sent = getattr(self, "sent", 0) + 1
        _spawn_near(game, "DustSwarm", 16, 26)


class VoidTide(WorldEvent):
    """Прилив пустоты: в глубоком космосе приходит Страж.

    Босс по месту, а не по расписанию: Страж пустоты — самое сильное, что
    есть в верхней зоне, и встретить его можно только забравшись туда, где
    он и живёт. Один, а не волна: это встреча, а не осада.
    """
    name = "прилив пустоты"
    announce = "Пустота уплотняется"
    duration = FPS * 30
    cooldown = FPS * 60 * 20

    def can_start(self, game, world_time):
        player = getattr(game, "player", None)
        if player is None or not player.alive:
            return False
        return player.rect.centery // TSIZE <= START_SPACE_Y - 200

    def on_start(self, game):
        self.message(game, "Страж пустоты близко")
        _spawn_near(game, "VoidSentinel", 18, 24)


def _spawn_near(game, creature_name, near, far):
    """Породить существо в стороне от игрока, но не в породе и не на свету."""
    import units.Objects.Creatures as C
    from units.Map.GameMap import spawn_creature
    cls = getattr(C, creature_name, None)
    if cls is None:
        return None
    gm, player = game.game_map, game.player
    tx = player.rect.centerx // TSIZE + random.choice((-1, 1)) * random.randint(near, far)
    ty = player.rect.centery // TSIZE + random.randint(-4, 4)
    if gm.get_static_tile_type(tx, ty, default=0, create_chunk=False):
        return None                          # в камне не рождаем
    if gm.lit_by_lamp(tx, ty):
        return None                          # свет отгоняет и здесь
    creature = spawn_creature(cls, game, tx, ty)
    creature.provoked = True
    gm.add_dinamic_obj(*gm.to_chunk_xy(tx, ty), creature)
    return creature


class EventDirector:
    """Кто решает, какое событие запускать. Одно за раз.

    Одно за раз — намеренно: два наложившихся события игрок читает как «игра
    сломалась», а не как «сегодня тяжёлая ночь».
    """

    def __init__(self):
        # Порядок важен только для разрешения одновременности: первое
        # готовое и запускается. Ставим редкие и «крупные» раньше.
        self.events = [VoidTide(), SolarFlare(), GolemAwakening(),
                       NightRaid(), MeteorShower(), BloreRift(), Migration()]

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
