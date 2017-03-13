from audiotools import cdio
from audiotools import player
import queue
import threading
import math

class AudioError(Exception): pass
class CDError(Exception): pass

def time_from_frames(frames, fps):
    return Time(frames / (fps / 1000))

class Time(object):
    def __init__(self, milli):
        self.update(milli)

    def fulltime(self):
        return '%i:%i:%i' % (self.minutes, self.seconds, self.millis)

    def min_seconds(self):
        return '%i:%i' % (self.minutes, self.seconds)

    def update(self, milli):
        self.length = milli

        self.minutes = math.floor(milli / 1000 / 60)
        self.seconds = math.floor(milli / 1000) - self.minutes * 60
        self.millis = (math.floor(milli) -
                       (self.minutes * 60 * 1000) - (self.seconds * 1000))

    def __str__(self): self.fulltime()

class Track(object):
    def __init__(self, n, s, e, sec):
        self.num = n
        self.start = s
        self.end = e
        self.frames = e - s
        self.time = time_from_frames(self.frames, sec)

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

    read_rate = 4048

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
        self.current_track_time = Time(0)
        self.current_cd_time = Time(0)
        self.current_frame = Time(0)

        total_t_len = 0
        for i, t in self.tracks.items(): total_t_len += t.frames
        self.time = time_from_frames(total_t_len, 44100)

        self.qu_frame = fr
        self.lk_disc = threading.Lock()
        self.ev_stop = threading.Event()
        self.thread = None

        self.goto_start()

    def get_tracks(self):
        tracks = {}
        for t, ofs in self.cd.track_offsets.items():
            tracks[t] = Track(t, ofs,
                              ofs + self.cd.track_lengths[t],
                              self.cd.sample_rate)
        return tracks


    def cd_inserted(self):
        return self.cd.last_sector - self.cd.first_sector > 1

    def set_out_format(self, ao):
        ao.set_format(self.cd.sample_rate, self.cd.channels,
                      self.cd.channel_mask, self.cd.bits_per_sample)

    def check_set_current_track(self):
        pos = self.current_frame - self.framecount.get()
        nextt = self.current_track + 1
        try:
            s = self.tracks[nextt].start
            e = self.tracks[nextt].end

            if s <= pos < e: self.current_track = nextt
        except KeyError: pass

    def set_current_times(self):
        pos = self.current_frame - self.framecount.get()
        tstart = self.tracks[self.current_track].start
        sr = self.cd.sample_rate / 1000
        self.current_track_time.update((pos - tstart) / sr)
        self.current_cd_time.update(pos / sr)

    def goto_track(self, t):
        try:
            while True: self.qu_frame.get_nowait()
        except queue.Empty: pass

        try:
            pos = self.tracks[t].start
            self.lk_disc.acquire()
            self.cd.seek(pos)
            self.current_track = t
            self.current_frame = pos
            self.check_set_current_track()
            self.lk_disc.release()
        except KeyError: pass

    def goto_start(self): self.goto_track(1)

    def read(self):
        self.lk_disc.acquire()
        data = self.cd.read(self.read_rate)
        self.current_frame = self.current_frame + data.frames
        self.framecount.add(data.frames)
        self.lk_disc.release()

        if data.frames < 1:
            return self.goto_start()

        self.qu_frame.put(data, True)

    def loop(self):
        try:
            while(True):
                if self.ev_stop.wait(0): return
                self.read()
        except KeyboardInterrupt: pass

    def stop(self):
        self.ev_stop.set()
        if self.thread != None:
            self.thread.join()
            del self.thread
            self.thread = None

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
    update_cb = None
    def __init__(self, fc, fr):
        self.ao = self.getAudioOutput()

        if not self.ao: raise AudioError("Cannot find audio output device")

        self.started = False
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
        try:
            while(self.ev_play.wait()):
                if self.ev_stop.wait(0): return
                self._play()
                if self.update_cb: self.update_cb()
        except KeyboardInterrupt: pass
        except: self.reset()

    def play(self):
        self.ao.resume()
        self.ev_play.set()

    def paused(self):
        return not self.ev_play.is_set()

    def pause(self):
        self.ao.pause()
        self.ev_play.clear()

    def reset(self):
        self.started = False

    def stop(self):
        self.reset()
        self.ev_stop.set()
        if self.thread:
            self.thread.join()
            self.thread = None
        self.ev_stop.clear()

    def start_playing(self):
        self.play()
        self.thread = threading.Thread(
            name = "audio_output",
            target = self.loop)

        self.thread.start()
        self.started = True


class Player():
    def __init__(self):
        self.ev_run = threading.Event()
        self.qu_frames = queue.Queue(500)
        self.framecount = FrameCount()

        self.ap = AudioPlayer(self.framecount, self.qu_frames)
        self.ap.update_cb = self.play_loop

        self.cd = None
        self.prev_gap = 44100

    def load_cd(self):
        self.cd = CDReader(self.framecount, self.qu_frames)
        if not self.cd.loaded: return

        self.cd.set_out_format(self.ap.ao)

    def play_loop(self):
        self.cd.check_set_current_track()
        self.cd.set_current_times()

    def beginning(self):
        self.cd.goto_start()

    def set_track(self, num):
        self.ap.ev_play.clear()
        self.cd.goto_track(num)
        self.ap.ev_play.set()

    def next_track(self): self.set_track(self.cd.current_track + 1)
    def prev_track(self):
        try:
            start = self.cd.tracks[self.cd.current_track].start
            cur = self.cd.current_frame
            diff = cur - start
            t = self.cd.current_track
            if diff < self.prev_gap: t = t - 1
            self.set_track(t)
        except KeyError: pass

    def current_track(self): return self.cd.tracks[self.cd.current_track]
    def tracks(self):        return self.cd.tracks

    def play(self):
        if (self.cd == None) or (self.cd.loaded == False):
            self.load_cd()
            if not self.cd.loaded: return

            self.beginning()
            self.cd.start_reading()

        if self.ap.started and self.ap.paused():
            self.ap.play()
        elif not self.ap.started:
            self.ap.start_playing()

    def pause(self):
        self.ap.pause()

    def stop(self):
        self.ap.stop()
        if self.cd: self.cd.stop()
