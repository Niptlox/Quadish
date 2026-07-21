"""Подсказки обучения (первая фаза концепта docs/TUTORIAL_CONCEPT.md).

Активны только когда game_map.tutorial_step >= 0 — то есть в мире
«Обучение», созданном через настройки. Прогресс (номер шага) хранится
в GameMap и сохраняется вместе с миром. Подсказки не блокируют игру:
сделал шаг раньше подсказки — он молча засчитывается.
"""
from units.common import FPS, TSIZE

REPEAT_TACTS = FPS * 45  # повтор подсказки, если игрок застрял
HINT_TACTS = FPS * 6     # сколько висит подсказка


class TutorialHints:
    def __init__(self, game):
        self.game = game
        self.start_pos = None
        self.seen_jump = False
        self.seen_inventory = False
        self.last_hint_tact = -10 ** 9

    def steps(self):
        """(текст подсказки, условие выполнения). Порядок = цепочка обучения."""
        p = self.game.player
        return [
            ("Обучение: [A]/[D] — движение, [Пробел] — прыжок",
             lambda: self.start_pos is not None and self.seen_jump
                     and abs(p.rect.x - self.start_pos[0]) > TSIZE * 5),
            ("Обучение: добудь дерево — зажми [ЛКМ] на стволе",
             lambda: p.inventory.find_in_inventory(12, 1)),
            ("Обучение: открой инвентарь — [E]",
             lambda: self.seen_inventory),
            ("Обучение: скрафть доски — рецепты справа в инвентаре [E]",
             lambda: p.inventory.find_in_inventory(11, 1)),
            ("Обучение: построй что-нибудь — [ПКМ] ставит блок (5 блоков)",
             lambda: p.blocks_placed_count >= 5),
            ("Обучение пройдено! Свой мир — через «Играть», справка — [F1]",
             lambda: True),
        ]

    def update(self):
        game = self.game
        step_i = game.game_map.tutorial_step
        if step_i < 0:
            return
        if self.start_pos is None:
            self.start_pos = (game.player.rect.x, game.player.rect.y)
        # трекинг разовых событий
        if game.player.jump_count > 0:
            self.seen_jump = True
        if game.player.inventory.ui.opened:
            self.seen_inventory = True

        steps = self.steps()
        if step_i >= len(steps):
            game.game_map.tutorial_step = -1
            return
        hint, done = steps[step_i]
        if done():
            game.game_map.tutorial_step = step_i + 1
            if game.game_map.tutorial_step >= len(steps):
                game.game_map.tutorial_step = -1
                return
            # сразу показываем следующий шаг
            game.ui.new_sys_message(steps[game.game_map.tutorial_step][0], count_tact=HINT_TACTS)
            self.last_hint_tact = game.tact
        elif game.tact - self.last_hint_tact >= REPEAT_TACTS:
            game.ui.new_sys_message(hint, count_tact=HINT_TACTS)
            self.last_hint_tact = game.tact
