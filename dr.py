#! /usr/bin/env python3
import argparse
import audioop
import math
import os
import pathlib
import random
import string
import struct
import subprocess
import tempfile
import wave

parser = argparse.ArgumentParser()
parser.add_argument("file", help="file to parse")
args = parser.parse_args()

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
            #print("got bytes:", len(block))
            expected = framerate*3*channels*framesize
            #print("expected:", expected)
            if len(block) < expected:
                # EOF
                break
            read += 3*framerate
            print("\r{}%".format(int(100*read/total)), flush=True, end="")
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
            N = int(0.2*len(peaks[c]))
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
        subprocess.check_output(["avconv", "-i", filename, tmpf], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf8"))
        raise
    return tmpf

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        if not args.file.endswith(".wav"):
            tmpf = convert_file(args.file, tmpdir)
            clean = True
        else:
            tmpf = args.file
            clean = False
        print("\rDR:", get_dr(tmpf))
        if clean:
            os.unlink(tmpf)
