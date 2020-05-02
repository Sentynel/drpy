#! /usr/bin/env python3

# Copyright (C) 2014 Sam Lade
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import audioop
import csv
import functools
import math
import os
import pathlib
import queue
import random
import string
import struct
import subprocess
import sys
import tempfile
import threading
import wave

import tabulate
try:
    import taglib
except ImportError:
    taglib = None

class TooShortError(Exception):
    pass
class SilentTrackError(Exception):
    pass

to_db = lambda x: round(20*math.log(x, 10), 2)

NORM = 2**15
def get_dr(filename, floats=False):
    with wave.open(filename, "rb") as f:
        channels = f.getnchannels()
        if channels not in (1,2):
            # TODO unpack n channels
            raise NotImplementedError("We only handle mono or stereo at the moment")
        framesize = f.getsampwidth()
        if framesize != 2:
            # TODO map framesize to struct module constants
            raise NotImplementedError("We only handle 16 bit formats at the moment")
        framerate = f.getframerate()
        total = f.getnframes()
        read = 0
        peaks = [[] for i in range(channels)]
        rmss = [[] for i in range(channels)]
        while True:
            # read three seconds of data
            block = f.readframes(framerate * 3)
            expected = framerate*3*channels*framesize
            if len(block) < expected:
                # EOF
                break
            read += 3*framerate
            # unpack
            if channels == 2:
                chansamples = [audioop.tomono(block, framesize, 1, 0), audioop.tomono(block, framesize, 0, 1)]
            else:
                chansamples = [block]
            for i, chan in enumerate(chansamples):
                peak = audioop.max(chan, framesize) / NORM
                rms = math.sqrt(2) * audioop.rms(chan, framesize) / NORM
                peaks[i].append(peak)
                rmss[i].append(rms)

        drs = []
        for c in range(channels):
            peaks[c].sort()
            rmss[c].sort()
            p2 = peaks[c][-2]
            if p2 == 0:
                raise SilentTrackError
            N = int(0.2*len(peaks[c]))
            if N == 0:
                raise TooShortError
            r = math.sqrt(sum(i**2 for i in rmss[c][-N:]) / N)
            dr = -to_db(r/p2)
            drs.append(dr)
        
        if not floats:
            fdr = round(sum(drs) / len(drs))
        else:
            fdr = sum(drs) / len(drs)
        return fdr

def convert_file(filename, tmpdir):
    d = pathlib.Path(tmpdir)
    while True:
        tmpf = "".join(random.sample(string.ascii_lowercase, 6)) + ".wav"
        if not (d / tmpf).exists():
            break
    tmpf = str(d / tmpf)
    try:
        subprocess.check_output(["ffmpeg", "-i", filename, tmpf], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf8"))
        raise
    return tmpf

def simple_summary(songs):
    drs = [i[-1] for i in songs]
    return round(sum(drs) / len(drs))

def get_single_tag(tags, tag):
    res = tags.get(tag)
    if not res:
        return "Unknown"
    return res[0]

def get_tag(filename):
    if taglib:
        f = taglib.File(str(filename))
        tags = f.tags
        if not tags:
            return ("Unknown", "Unknown", "Unknown", "Unknown", filename)
        items = [get_single_tag(tags, i) for i in ("ARTIST", "DATE", "ALBUM", "TRACKNUMBER", "TITLE")]
        items[3] = int(items[3])
        return tuple(items)
    return (filename.name,)

def format_results(errs, results):
    res = ""
    if errs:
        res = "\n".join(errs) + "\n\n"
    if taglib:
        hdrs = ["Artist", "Date", "Album", "Track", "Title", "DR"]
    else:
        hdrs = ["File", "DR"]
    res += tabulate.tabulate(results, headers=hdrs)
    overall = simple_summary(results)
    res += "\n\nOverall: DR{}".format(overall)
    return res

def get_results(items, progress, floats=False):
    res = []
    errs = []
    n = 0
    with tempfile.TemporaryDirectory() as td:
        for i in items:
            t = get_tag(i)
            rm = None
            if i.suffix != ".wav":
                try:
                    p = convert_file(i, td)
                except subprocess.CalledProcessError:
                    errs.append("Warning: decoding failed on: " + str(i))
                    continue
                rm = p
            else:
                p = str(i)
            try:
                dr = get_dr(p, floats)
            except TooShortError:
                errs.append("Warning: too short: " + str(i))
                continue
            except SilentTrackError:
                errs.append("Warning: silent track: " + str(i))
                continue
            except NotImplementedError as e:
                errs.append("Warning: " + str(e) + ": " + str(i))
                continue
            finally:
                if rm:
                    os.unlink(rm)
            n += 1
            progress(n, len(items))
            res.append(t + (dr,))
    return errs, sorted(res)

def get_files(path, recurse=False):
    res = []
    for i in path.iterdir():
        if i.is_dir():
            if recurse:
                res.extend(get_files(i, True))
        elif i.suffix in (".flac", ".wav", ".mp3", ".ogg", ".m4a"):
            res.append(i)
    return res

def do_cmdline(args):
    path = pathlib.Path(args.path)
    if not path.exists():
        print("error: path does not exist")
        return
    if path.is_file():
        items = [path]
    else:
        items = get_files(path)
    prog = lambda i, n: print(".", end="", flush=True)
    errs, results = get_results(items, prog, args.float)
    print()
    fmt = format_results(errs, results)
    print(fmt)

def proc_thread(path, q):
    items = get_files(path)
    prog = lambda i, n: q.put((n, i))
    errs, results = get_results(items, prog, args.float)
    fmt = format_results(errs, results)
    q.put("\n" + fmt)

def gui_get_path(q):
    import plyer
    d = plyer.filechooser.choose_dir()
    if not d:
        return
    path = pathlib.Path(d[0])
    thread = threading.Thread(target=proc_thread, args=(path, q))
    thread.start()

def gui_check_queue(q, app, dt):
    try:
        msg = q.get(False)
    except queue.Empty:
        pass
    else:
        if isinstance(msg, tuple):
            app.prog.max = msg[0]
            app.prog.value = msg[1]
        elif isinstance(msg, str):
            app.text.text += msg
            app.layout.do_layout()

def do_gui(args):
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.textinput import TextInput
    from kivy.uix.progressbar import ProgressBar
    class GUI(App):
        def build(self):
            self.title = "DR tool"
            self.layout = BoxLayout(orientation="vertical")
            self.prog = ProgressBar(size_hint=(1,.1))
            self.layout.add_widget(self.prog)
            self.text = TextInput(readonly=True, font_name="RobotoMono-Regular")
            self.layout.add_widget(self.text)
            return self.layout

    q = queue.Queue()
    gui_get_path(q)
    app = GUI()
    Clock.schedule_interval(functools.partial(gui_check_queue, q, app), 0.1)
    app.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="file or directory to measure", nargs="?", default=None)
    parser.add_argument("-f", "--float", action="store_true", help="floating point results (nonstandard)")
    args = parser.parse_args()

    if args.path is None:
        do_gui(args)
    else:
        do_cmdline(args)
