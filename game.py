import os

from units.App.Game import Game

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    game = Game()
    game.main()


if __name__ == "__main__":
    main()
