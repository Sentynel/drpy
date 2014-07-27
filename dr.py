#! /usr/bin/env python3
import argparse
import math
import struct
import wave

parser = argparse.ArgumentParser()
parser.add_argument("file", help="file to parse")
args = parser.parse_args()

to_db = lambda x: round(20*math.log(x, 10), 2)

NORM = 2**15
with wave.open(args.file, "rb") as f:
    channels = f.getnchannels()
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
        samples = struct.unpack("<{}h".format(framerate*3*channels), block)
        chansamples = [samples[i::2] for i in range(channels)]
        for i, chan in enumerate(chansamples):
            peak = 0
            ssum = []
            for val in chan:
                val = abs(val) / NORM
                if val > peak:
                    peak = val
                ssum.append(val**2)
            rms = math.sqrt(2*sum(ssum) / (3*framerate))
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
    print("\nDR:", fdr)
