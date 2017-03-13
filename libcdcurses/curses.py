import curses
from abc import ABCMeta, abstractmethod
from time import sleep

class Curses():

    def main(self, stdsrc):
        self.stdsrc = stdsrc
        self.titlewin = self.stdsrc.subwin(1, 0)
        self.statuswin = self.stdsrc.subwin(50, 0)
        self.stdsrc.nodelay(True)

        self.loop()

    def resize(self):
        y, x = self.stdsrc.getmaxyx()
        if not curses.is_term_resized(y, x): return
        self.stdsrc.clear()
        curses.resizeterm(y, x)
        self.stdsrc.refresh()

    def wait(self):
        ev = self.stdsrc.getch()
        if   ev == -1: sleep(.3)
        elif ev == ord('q'):
            self.quit()
            return False
        elif ev == curses.KEY_RESIZE: pass

        return True

    def loop(self):
        while(self.wait()): pass

    def start(self): curses.wrapper(self.main)

    @abstractmethod
    def quit(self): raise NotImplementedError()

    @abstractmethod
    def play(self): raise NotImplementedError()

    @abstractmethod
    def stop(self): raise NotImplementedError()

    @abstractmethod
    def pause(self): raise NotImplementedError()

    @abstractmethod
    def next(self): raise NotImplementedError()

    @abstractmethod
    def prev(self): raise NotImplementedError()

    @abstractmethod
    def trackselected(self, num): raise NotImplementedError()
