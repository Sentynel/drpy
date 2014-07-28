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
import collections
import csv
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("infile", help="csv to read")
parser.add_argument("outfile", help="png to write")
args = parser.parse_args()

f = open(args.infile)
r = csv.DictReader(f)
tree = collections.defaultdict(collections.Counter)
for row in r:
    try:
        tree[int(row["Date"][:4])][int(row["DR"])] += 1
    except ValueError:
        continue

yearmin, yearmax = min(tree), max(tree)
alldr = set()
for year, drs in tree.items():
    for dr in drs:
        alldr.add(dr)
drmin, drmax = min(alldr), max(alldr)

data = []
for y in range(yearmin, yearmax+1):
    for d in range(drmin, drmax+1):
        data.append("{} {} {}".format(y, d, tree[y][d]))
    data.append("")
data = "\n".join(data)

script = """set view map
unset surface
set style data pm3d
set style function pm3d
set pm3d implicit at b
set pm3d flush begin noftriangles scansforward
set xrange [{} : {}]
set yrange [{} : {}]
set ticslevel 0
set xlabel "Year"
set ylabel "DR"
set title "DR count by year"
set terminal pngcairo size 1000,600
set output "{}"
splot "{{}}" """.format(yearmin, yearmax, drmin, drmax, args.outfile)

with tempfile.NamedTemporaryFile("w") as f, tempfile.NamedTemporaryFile("w") as g:
    g.write(data)
    g.flush()
    f.write(script.format(g.name))
    f.flush()
    subprocess.check_call(["gnuplot", f.name])
