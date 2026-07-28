"""Транспортные средства: сущности, на которых игрок ездит и летает.

Второй вид транспорта в игре. Первый — блоки-носители (батут, блоровая
дорожка, столбы, портал; см. docs/TRANSPORT.md): они дёшевы, не требуют
хранения и работают сами по себе, но привязаны к месту — их надо СТРОИТЬ.
Средство едет туда, куда игрок его повёл, и в этом вся разница: линия
обслуживает маршрут, средство обслуживает разведку.

Общая рамка, чтобы пятое и десятое средство добавлялись строчкой:

* Каждое живёт в чанке (chunk[1]) как существо — значит сохраняется вместе с
  миром и не исчезает, пока игрок не вернётся.
* Каждое задаёт СРЕДУ, в которой держится (`medium`), и не работает вне её:
  плот на суше не поедет, космический скиф в атмосфере не полетит. Это и есть
  причина, по которой средств несколько, а не одно универсальное.
* Управление у всех одно: те же клавиши, что и у ходьбы. Новых жестов нет,
  кроме посадки правым кликом.
"""
from units.Objects.Entity import PhysicalObject
from units.Objects.Items import ItemsTile
from units.Tiles import PHYSBODY_TILES
from units.common import *


class Vehicle(PhysicalObject):
    """База всех средств передвижения."""
    class_obj = OBJ_VEHICLE
    not_save_vars = PhysicalObject.not_save_vars | {"driver"}
    # предмет, из которого средство ставится и в который разбирается
    index = 0
    width, height = TSIZE * 2, TSIZE
    max_lives = 40
    # Ход. Единицы — ПИКСЕЛИ ЗА КАДР, как у существ (movement_vector идёт в
    # update_physics без множителя на elapsed_time). Для сравнения: бег игрока
    # это max_speed 0.33 * 16 мс ≈ 5.3 px/кадр.
    max_speed = 7.0
    accel = 0.9
    # Среда, в которой средство держится: тип тайла под ним (вода/лава),
    # None — обычная опора (земля). AIR — держится само, без опоры.
    medium = None
    AIR = "air"
    # Насколько резво средство слушается по вертикали (доля от max_speed):
    # рулить вверх-вниз медленнее, чем разгоняться вбок, — иначе воздушная
    # лодка взлетает быстрее, чем летит.
    vertical_ratio = 0.6
    immune_tiles = frozenset()
    sprite_color = "#8B5A2B"
    # Можно ли рулить по вертикали (летающие — да, наземные — нет)
    vertical_control = False

    def __init__(self, game, pos=(0, 0)):
        super().__init__(game, pos[0], pos[1], self.width, self.height,
                         use_physics=True)
        self.lives = self.max_lives
        self.driver = None
        self.speed = 0
        self.flip = False
        self.sprite = self.build_sprite()

    # ---------- посадка ----------

    def mount(self, player):
        """Посадить игрока. Возвращает False, если средство занято."""
        if self.driver is not None or not self.alive:
            return False
        self.driver = player
        player.vehicle = self
        player.vertical_momentum = 0
        return True

    def dismount(self):
        """Высадить игрока рядом со средством."""
        player = self.driver
        self.driver = None
        if player is not None:
            player.vehicle = None
            # чуть выше средства, чтобы не застрять в его же прямоугольнике
            player.rect.midbottom = self.rect.centerx, self.rect.top
            player.vertical_momentum = 0
        return player

    # ---------- среда ----------

    def tile_under(self):
        return self.game_map.get_static_tile_type(
            self.rect.centerx // TSIZE, (self.rect.bottom + 1) // TSIZE,
            default=0, create_chunk=False)

    def tile_inside(self):
        return self.game_map.get_static_tile_type(
            self.rect.centerx // TSIZE, self.rect.centery // TSIZE,
            default=0, create_chunk=False)

    def in_medium(self):
        """Работает ли средство здесь.

        Это и есть причина, по которой средств несколько: каждое умеет ровно
        одну среду, и вне её оно мёртвый груз, а не медленный вариант.
        """
        if self.medium is None:
            # Не по collisions['bottom']: стоя на месте, средство падает на
            # доли пикселя, rect.y округляется вниз до нуля, и столкновения в
            # этом кадре нет вовсе. Опора «мигала» бы через кадр, а с ней
            # рвался бы разгон — ровно тот же дефект, что был у блоровой
            # дорожки (docs/TRANSPORT.md).
            return (bool(self.collisions.get("bottom"))
                    or self.tile_under() in PHYSBODY_TILES)
        if self.medium is self.AIR:
            return True
        return self.medium in (self.tile_under(), self.tile_inside())

    # ---------- ход ----------

    def controls(self):
        """Ввод водителя. Отдельным методом, чтобы средство без водителя
        считалось по тем же правилам, просто с нулевым вводом."""
        d = self.driver
        if d is None:
            return 0, 0
        dx = (1 if d.moving_right else 0) - (1 if d.moving_left else 0)
        dy = (1 if d.on_down else 0) - (1 if d.on_up else 0)
        return dx, dy

    def update(self, tact, elapsed_time):
        if not self.alive:
            return False
        working = self.in_medium()
        dx, dy = self.controls() if working else (0, 0)

        if dx:
            self.speed = max(-self.max_speed, min(self.max_speed, self.speed + self.accel * dx))
            self.flip = dx < 0
        else:
            self.speed *= 0.85
            if abs(self.speed) < 0.01:
                self.speed = 0
        self.movement_vector.x += self.speed

        if working:
            # В своей среде средство не падает: вода держит плот, лава баржу,
            # оболочка воздушную лодку. Вне среды сюда не попадаем вовсе, и
            # средство честно валится обычной гравитацией.
            if self.vertical_control:
                self.physical_vector.y = self.max_speed * self.vertical_ratio * dy
            else:
                self.physical_vector.y = 0.0

        self.update_physics(elapsed_time)
        self.carry_driver()
        return True

    def carry_driver(self):
        """Игрок едет вместе со средством."""
        if self.driver is None:
            return
        self.driver.rect.midbottom = self.rect.centerx, self.rect.centery + self.rect.h // 4
        self.driver.vertical_momentum = 0
        self.driver.speed = 0
        self.driver.air_timer = 0
        self.driver.update_chunk_pos()

    # ---------- разрушение ----------

    def kill(self):
        was = self.driver
        if was is not None:
            self.dismount()
        super().kill()
        x, y = self.rect.topleft
        item = ItemsTile(self.game, self.index, (x, y), 1)
        self.game_map.add_dinamic_obj(*self.game_map.to_chunk_xy(x // TSIZE, y // TSIZE), item)

    # ---------- вид ----------

    def build_sprite(self):
        """Простая процедурная отрисовка: корпус и деталь среды.

        Пиксель-арт для пяти средств — отдельная работа; здесь важнее, чтобы
        средства читались как разные, а форма задавалась классом.
        """
        img = pg.Surface((self.width, self.height), pg.SRCALPHA, 32)
        w, h = self.width, self.height
        pg.draw.polygon(img, self.sprite_color,
                        [(2, h // 3), (w - 3, h // 3), (w - 7, h - 3), (6, h - 3)])
        pg.draw.polygon(img, "#00000066",
                        [(2, h // 3), (w - 3, h // 3), (w - 7, h - 3), (6, h - 3)], 2)
        self.decorate_sprite(img)
        return img

    def decorate_sprite(self, img):
        pass

    def draw(self, surface, pos):
        img = pg.transform.flip(self.sprite, True, False) if self.flip else self.sprite
        surface.blit(img, pos)


class Raft(Vehicle):
    """Плот. Самое раннее средство: брёвна и лианы, никакого металла.

    Вода в Quadish полу-физическая — в неё можно войти и в ней тонуть. Плот
    превращает реку и озеро из препятствия в дорогу, и это ровно тот же ход
    мысли, что у батута: сначала среда перестаёт наказывать, потом начинает
    возить.
    """
    index = 611
    medium = 120                      # вода
    max_speed = 6.0
    sprite_color = "#A16207"

    def decorate_sprite(self, img):
        w, h = self.width, self.height
        for x in range(4, w - 4, 6):
            pg.draw.line(img, "#78350F", (x, h // 3 + 1), (x - 2, h - 4), 1)


class AirBoat(Vehicle):
    """Воздушная лодка. Держится в воздухе сама и слушается по вертикали.

    Мир вертикальный, и до неё вертикаль всегда стоила инфраструктуры: шахта
    из столбов, лестница, батут внизу. Лодка — первый способ подняться туда,
    где ничего не построено, то есть первый инструмент разведки, а не
    маршрута. Поэтому она и стоит блора: перемещение держится на нём.
    """
    index = 612
    medium = Vehicle.AIR
    vertical_control = True
    max_speed = 6.5
    max_lives = 60
    sprite_color = "#C2A878"

    def decorate_sprite(self, img):
        w, h = self.width, self.height
        pg.draw.ellipse(img, "#E7E5E4", (w // 6, 0, w - w // 3, h // 2))
        pg.draw.ellipse(img, "#A8A29E", (w // 6, 0, w - w // 3, h // 2), 2)
        pg.draw.line(img, "#57534E", (w // 2, h // 2), (w // 2, h // 3), 2)


class MineCrawler(Vehicle):
    """Шахтный ползун. Едет по твёрдому полу, быстро и с фарой.

    Пещеры — это длинные горизонтальные ходы, по которым игрок возвращается
    десятки раз. Ползун не открывает новых мест, он убирает повторную дорогу
    к уже открытым — то же, что дорожка, но без стройки.
    """
    index = 613
    medium = None                     # обычная опора
    max_speed = 9.0
    accel = 1.2
    max_lives = 80
    sprite_color = "#57534E"

    def decorate_sprite(self, img):
        w, h = self.width, self.height
        for cx in (w // 4, w - w // 4):
            pg.draw.circle(img, "#292524", (cx, h - 3), 4)
            pg.draw.circle(img, "#78716C", (cx, h - 3), 2)
        pg.draw.circle(img, "#FDE047", (w - 5, h // 2), 3)


class LavaBarge(Vehicle):
    """Адская баржа. Держится на лаве и не горит.

    Лава в аду — сплошная преграда: полу-физическая, то есть в неё можно
    войти и в ней умереть. Баржа делает главное препятствие зоны её же
    дорогой. Требует серы — то есть собрать её заранее, не побывав в аду,
    нельзя (зональный вентиль, docs/BALANCE_SCHEME.md).
    """
    index = 614
    medium = 140                      # лава
    max_speed = 5.5
    max_lives = 100
    immune_tiles = frozenset({140})
    sprite_color = "#7F1D1D"

    def decorate_sprite(self, img):
        w, h = self.width, self.height
        pg.draw.rect(img, "#292524", (5, h // 3 - 3, w - 10, 4))
        for x in range(8, w - 8, 8):
            pg.draw.line(img, "#FB923C", (x, h // 3 - 4), (x, h // 3 - 7), 2)


class VoidSkiff(Vehicle):
    """Пустотный скиф. Летает в вакууме, где нет опоры вообще.

    В космосе не на что встать: воздушная лодка там бесполезна, потому что ей
    нечем отталкиваться. Скиф — единственный способ перемещаться между
    астероидами не прыжками. Требует космической пыли, как и всё
    космическое.
    """
    index = 615
    medium = Vehicle.AIR
    vertical_control = True
    max_speed = 11.0
    accel = 0.8
    max_lives = 70
    sprite_color = "#334155"

    def in_medium(self):
        # Только вакуум: в атмосфере скиф не работает — это его цена за
        # скорость, иначе он обесценил бы все остальные средства сразу.
        return self.rect.centery // TSIZE <= START_SPACE_Y

    def decorate_sprite(self, img):
        w, h = self.width, self.height
        pg.draw.polygon(img, "#38BDF8", [(w // 2, 1), (w - 6, h // 3), (6, h // 3)])
        pg.draw.circle(img, "#0EA5E9", (w // 2, h // 2 + 2), 3)


VEHICLES = (Raft, AirBoat, MineCrawler, LavaBarge, VoidSkiff)
VEHICLES_D = {cls.index: cls for cls in VEHICLES}
