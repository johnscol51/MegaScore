#!/usr/bin/env python
with open("MegaScore.py", "rb") as f:
    data = f.read()

for i, b in enumerate(data):
    if b > 127:
        print(i, hex(b))

