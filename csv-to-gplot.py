#! /usr/bin/env python3
import collections
import csv
import sys

f = open(sys.argv[1])
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

for y in range(yearmin, yearmax+1):
    for d in range(drmin, drmax+1):
        print("{} {} {}".format(y, d, tree[y][d]))
    print()
