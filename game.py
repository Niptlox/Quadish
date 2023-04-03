import os

from units.App.Game import GameApp

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    game = GameApp()
    game.main()


if __name__ == "__main__":
    main()
