"""Обучение (фаза 2 концепта docs/TUTORIAL_CONCEPT.md).

Активно только когда game_map.tutorial_step >= 0 — в мире «Обучение».
Прогресс (номер шага) хранится в GameMap и сохраняется вместе с миром.

Каналы: подсказка через SysMessege, постоянная задача с прогрессом
вверху экрана («Добудь дерево 1/3») и маркер цели — пульсирующая рамка
на тайле, а если цель за экраном — стрелка у края в её сторону.
"""
import math

import pygame as pg

from units.common import FPS, TSIZE, WSIZE, CWDIR
from units.UI.Translate import get_translated_text

REPEAT_TACTS = FPS * 45  # повтор подсказки, если игрок застрял
HINT_TACTS = FPS * 6     # сколько висит подсказка
WOOD_TILE = 110          # ствол дерева
WOOD_ITEM = 12           # бревно
PLANK_ITEM = 11          # доски

MARKER_COLOR = "#FDE047"

font_task = pg.font.Font(CWDIR + 'data/fonts/xenoa.ttf', 18)


def count_in_inventory(inventory, index):
    return sum(i.count for i in inventory if i is not None and i.index == index)


class Step:
    __slots__ = ("hint", "done", "task", "progress", "target")

    def __init__(self, hint, done, task=None, progress=None, target=None):
        self.hint = hint          # текст подсказки (SysMessege)
        self.done = done          # () -> bool: условие выполнения
        self.task = task or hint  # текст задачи вверху экрана
        self.progress = progress  # () -> (текущее, всего) или None
        self.target = target      # () -> (tile_x, tile_y) или None: цель маркера


class TutorialHints:
    def __init__(self, game):
        self.game = game
        self.start_pos = None
        self.seen_jump = False
        self.seen_inventory = False
        self.last_hint_tact = -10 ** 9
        self.target_tile = None
        self._steps = None
        self._task_text = None
        self._task_surf = None

    def steps(self):
        p = self.game.player
        inv = p.inventory
        return [
            Step("Обучение: [A]/[D] — движение, [Пробел] — прыжок",
                 lambda: self.start_pos is not None and self.seen_jump
                         and abs(p.rect.x - self.start_pos[0]) > TSIZE * 5,
                 task="Осмотрись и попрыгай"),
            Step("Обучение: добудь 3 дерева — зажми [ЛКМ] на стволе",
                 lambda: count_in_inventory(inv, WOOD_ITEM) >= 3,
                 task="Добудь дерево",
                 progress=lambda: (min(3, count_in_inventory(inv, WOOD_ITEM)), 3),
                 target=self._nearest_wood),
            Step("Обучение: открой инвентарь — [E]",
                 lambda: self.seen_inventory,
                 task="Открой инвентарь — [E]"),
            Step("Обучение: скрафть доски — рецепты справа в инвентаре [E]",
                 lambda: count_in_inventory(inv, PLANK_ITEM) >= 2,
                 task="Скрафть доски",
                 progress=lambda: (min(2, count_in_inventory(inv, PLANK_ITEM)), 2)),
            Step("Обучение: построй что-нибудь — [ПКМ] ставит блок",
                 lambda: p.blocks_placed_count >= 5,
                 task="Поставь блоки",
                 progress=lambda: (min(5, p.blocks_placed_count), 5)),
            Step("Обучение пройдено! Свой мир — через «Играть», справка — [F1]",
                 lambda: True),
        ]

    # ---------- логика шагов (вызывается раз в ~полсекунды) ----------

    def update(self):
        game = self.game
        step_i = game.game_map.tutorial_step
        if step_i < 0:
            self._steps = None
            return
        if self.start_pos is None:
            self.start_pos = (game.player.rect.x, game.player.rect.y)
        # трекинг разовых событий
        if game.player.jump_count > 0:
            self.seen_jump = True
        if game.player.inventory.ui.opened:
            self.seen_inventory = True

        self._steps = steps = self.steps()
        if step_i >= len(steps):
            game.game_map.tutorial_step = -1
            return
        step = steps[step_i]
        if step.done():
            game.game_map.tutorial_step = step_i + 1
            self._task_text = None
            if game.game_map.tutorial_step >= len(steps):
                game.game_map.tutorial_step = -1
                self._steps = None
                return
            # сразу показываем следующий шаг
            step = steps[game.game_map.tutorial_step]
            game.ui.new_sys_message(step.hint, count_tact=HINT_TACTS)
            self.last_hint_tact = game.tact
        elif game.tact - self.last_hint_tact >= REPEAT_TACTS:
            game.ui.new_sys_message(step.hint, count_tact=HINT_TACTS)
            self.last_hint_tact = game.tact
        self.target_tile = step.target() if step.target else None

    def _nearest_wood(self):
        """Ближайший ствол дерева в загруженной области."""
        p = self.game.player
        px, py = p.rect.centerx // TSIZE, p.rect.centery // TSIZE
        best, best_d = None, 10 ** 9
        for (tx, ty), t in self.game.screen_map.static_tiles.items():
            if t == WOOD_TILE:
                d = (tx - px) ** 2 + (ty - py) ** 2
                if d < best_d:
                    best_d, best = d, (tx, ty)
        return best

    # ---------- отрисовка (каждый кадр) ----------

    def draw(self, display):
        game = self.game
        step_i = game.game_map.tutorial_step
        if step_i < 0 or not self._steps or step_i >= len(self._steps):
            return
        step = self._steps[step_i]

        # панель задачи вверху по центру
        text = get_translated_text(step.task)
        if step.progress:
            cur, total = step.progress()
            text += f"  {cur}/{total}"
        if text != self._task_text:
            self._task_text = text
            t = font_task.render(text, True, MARKER_COLOR)
            panel = pg.Surface((t.get_width() + 24, t.get_height() + 12)).convert_alpha()
            panel.fill((39, 39, 42, 210))
            panel.blit(t, (12, 6))
            self._task_surf = panel
        display.blit(self._task_surf, ((WSIZE[0] - self._task_surf.get_width()) // 2, 8))

        # маркер цели
        if self.target_tile is None:
            return
        scroll = game.screen_map.scroll
        sx = self.target_tile[0] * TSIZE - scroll[0]
        sy = self.target_tile[1] * TSIZE - scroll[1]
        if -TSIZE < sx < WSIZE[0] and -TSIZE < sy < WSIZE[1]:
            # цель на экране: пульсирующая рамка вокруг тайла
            pulse = 2 + int(3 * abs(math.sin(game.tact / 12)))
            pg.draw.rect(display, MARKER_COLOR,
                         (sx - pulse, sy - pulse, TSIZE + pulse * 2, TSIZE + pulse * 2),
                         width=2, border_radius=4)
        else:
            # цель за экраном: стрелка у края в её сторону
            cx, cy = WSIZE[0] / 2, WSIZE[1] / 2
            dx, dy = sx + TSIZE / 2 - cx, sy + TSIZE / 2 - cy
            margin = 40
            kx = (cx - margin) / abs(dx) if dx else 10 ** 9
            ky = (cy - margin) / abs(dy) if dy else 10 ** 9
            k = min(kx, ky, 1)
            ex, ey = cx + dx * k, cy + dy * k
            ang = math.atan2(dy, dx)
            tip = (ex + math.cos(ang) * 14, ey + math.sin(ang) * 14)
            left = (ex + math.cos(ang + 2.5) * 12, ey + math.sin(ang + 2.5) * 12)
            right = (ex + math.cos(ang - 2.5) * 12, ey + math.sin(ang - 2.5) * 12)
            pg.draw.polygon(display, MARKER_COLOR, (tip, left, right))
