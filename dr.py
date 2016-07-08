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
import math
import os
import pathlib
import random
import string
import struct
import subprocess
import sys
import tempfile
import wave

import taglib

class TooShortError(Exception):
    pass
class SilentTrackError(Exception):
    pass

to_db = lambda x: round(20*math.log(x, 10), 2)

NORM = 2**15
def get_dr(filename):
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
        
        fdr = math.ceil(sum(drs) / len(drs))
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

errcount = 0
def dr_any(filename, tmpdir):
    global errcount
    if not filename.endswith(".wav"):
        try:
            tmpf = convert_file(filename, tmpdir)
        except subprocess.CalledProcessError:
            errcount += 1
            raise
        clean = True
    else:
        tmpf = filename
        clean = False
    dr = get_dr(tmpf)
    if clean:
        os.unlink(tmpf)
    return dr

def dr_all(path, tmpdir, n=0):
    print(n, "\r", flush=True, file=sys.stderr, end="")
    songs = {}
    p = pathlib.Path(path)
    for i in p.iterdir():
        thisdir = []
        if i.is_dir():
            s, n = dr_all(i, tmpdir, n)
            songs.update(s)
        elif i.suffix in (".flac", ".wav", ".mp3", ".ogg"):
            try:
                s = dr_any(str(i), tmpdir)
            except TooShortError:
                print("Warning: too short:", str(i))
                continue
            except SilentTrackError:
                print("Warning: silent track:", str(i))
                continue
            except subprocess.CalledProcessError:
                print("Warning: failed decode:", str(i))
                continue
            t = get_tag(str(i))
            songs[t] = s
            n += 1
    return songs, n

def gen_album_stats(songs):
    albums = {}
    for t, d in songs.items():
        ta = t[:3]
        if ta not in albums:
            albums[ta] = []
        albums[ta].append(d)
    out = {}
    for t, d in albums.items():
        out[t] = math.ceil(sum(d) / len(d))
    return out

def get_tag(filename):
    f = taglib.File(filename)
    tags = f.tags
    return (tags.get("ARTIST", ["Unknown"])[0], tags.get("DATE", ["Unknown"])[0], tags.get("ALBUM", ["Unknown"])[0], tags.get("TRACKNUMBER", ["Unknown"])[0], tags.get("TITLE", ["Unknown"])[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="file or directory to parse")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        p = pathlib.Path(args.path)
        if p.is_dir():
            songs, n = dr_all(args.path, tmpdir)
            with open("songs.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Artist", "Date", "Album", "Track", "Title", "DR"])
                for t, d in sorted(songs.items()):
                    w.writerow(t + (d,))
            albums = gen_album_stats(songs)
            with open("albums.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Artist", "Date", "Album", "DR"])
                for t, d in albums.items():
                    w.writerow(t + (d,))
            print("Decoding failed on", errcount, "files.")
        else:
            dr = dr_any(args.path, tmpdir)
            tags = get_tag(args.path)
            print(tags, dr)
