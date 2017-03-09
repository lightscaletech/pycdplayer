from audiotools import cdio
from audiotools import player
import queue
import threading

class AudioError(Exception): pass
class CDError(Exception): pass

class FrameCount():
    lock = threading.Lock()
    count = 0

    def add(self, f):
        self.lock.acquire()
        self.count = self.count + f
        self.lock.release()

    def rmv(self, f):
        self.lock.acquire()
        self.count = self.count - f
        self.lock.release()

    def get(self):
        self.lock.acquire()
        c = self.count
        self.lock.release()
        return c

class CDReader():

    read_rate = 75

    def __init__(self, fc, fr):
        self.cd = cdio.CDDAReader("/dev/cdrom", False)
        self.framecount = fc
        if not self.cd_inserted():
            self.loaded = False
            self.cd.close()
            return
        else: self.loaded = True

        self.tracks = self.get_tracks()
        self.current_track = 1
        self.current_frame = 0

        self.qu_frame = fr
        self.thread = None

        self.goto_start()

    def get_tracks(self):
        tracks = {}
        for t, ofs in self.cd.track_offsets.items():
            tracks[t] = (ofs, (ofs + self.cd.track_lengths[t]))
        return tracks


    def cd_inserted(self):
        return self.cd.last_sector - self.cd.first_sector > 1

    def set_out_format(self, ao):
        ao.set_format(self.cd.sample_rate, self.cd.channels,
                      self.cd.channel_mask, self.cd.bits_per_sample)

    def check_set_current_track(self):
        pos = self.current_frame - self.framecount.get()
        nextt = self.current_track + 1
        s, e = self.tracks[nextt]

        if s <= pos < e:
            self.current_track = nextt
            print (self.current_track)


    def goto_track(self, t):
        try:
            while True: self.qu_frame.get_nowait()
        except queue.Empty: pass

        pos = 10300000 #self.tracks[t][0]
        self.cd.seek(pos)
        self.current_track = t
        self.current_frame = pos
        self.check_set_current_track()

    def goto_start(self): self.goto_track(1)

    def read(self):
        data = self.cd.read(self.read_rate)
        self.current_frame = self.current_frame + data.frames

        if data.frames < 1:
            return self.goto_start()

        self.qu_frame.put(data, True)
        self.framecount.add(data.frames)
        self.check_set_current_track()

    def loop(self):
        while(True):
            self.read()

    def start_reading(self):
        thread = threading.Thread(
            name = "cd_reader",
            target = self.loop)

        thread.start()

class AudioPlayer():

    preference = [player.ALSAAudioOutput,
                  player.PulseAudioOutput,
                  player.OSSAudioOutput]

    thread = None

    def __init__(self, fc, fr):
        self.ao = self.getAudioOutput()

        if not self.ao: raise AudioError("Cannot find audio output device")

        self.framecount = fc
        self.ev_play = threading.Event()
        self.ev_stop = threading.Event()
        self.qu_frame = fr

    def getAudioOutput(self):
        av = player.available_outputs()
        for o in self.preference:
            for ao in av:
                if o == type(ao): return o()
        return None

    def _play(self):
        data = self.qu_frame.get(True, 10)
        self.framecount.rmv(data.frames)
        self.ao.play(data)

    def loop(self):
        while(self.ev_play.wait()):
            if self.ev_stop.wait(0): return
            self._play()

    def play(self):
        self.ev_play.set()

    def pause(self):
        self.ao.pause()
        self.ev_play.clear()

    def stop(self):
        self.play()
        self.ev_stop.set()
        self.thread.join()
        self.ev_stop.clear()

    def start_playing(self):
        self.play()
        self.thread = threading.Thread(
            name = "audio_output",
            target = self.loop)

        self.thread.start()


class Player():
    def __init__(self):
        self.ev_run = threading.Event()
        self.qu_frames = queue.Queue(500)
        self.framecount = FrameCount()

        self.ap = AudioPlayer(self.framecount, self.qu_frames)

        self.cd = None

        self.load_cd()

    def load_cd(self):
        self.cd = CDReader(self.framecount, self.qu_frames)
        if not self.cd.loaded: return

        self.cd.set_out_format(self.ap.ao)

    def beginning(self):
        self.cd.goto_start()

    def set_track(self, num):
        self.cd.goto_track(num)

    def play(self):
        if not self.cd.loaded: return

        self.beginning()
        self.cd.start_reading()
        self.ap.start_playing()

    def stop(self):
        self.ap.stop
