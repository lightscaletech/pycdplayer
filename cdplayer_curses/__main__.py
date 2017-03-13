from libcdcurses import curses
from libcdplayer import libcdplayer

class CdPlayer(curses.Curses):
    def __init__(self):
        self.player = libcdplayer.Player()

    def quit(self): self.player.stop()

    def wait(self):
        return curses.Curses.wait(self)

player = CdPlayer()
try:
    player.start()
except KeyboardInterrupt:
    player.quit()
