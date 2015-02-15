#!/usr/bin/python3

import artdmx
import numpy as np
import argparse
import colorsys
import time

parser = argparse.ArgumentParser(description='Show a rainbow pattern.')
parser.add_argument('-u', '--universe', metavar='UNIV', default=0,
                    type=lambda x: int(x, 0), help='universe id (default=0)')
parser.add_argument('-s', '--server', metavar='HOST', default='localhost',
                    type=str, help='server (default=localhost)')
parser.add_argument('-p', '--port', metavar='PORT', default=6454, type=int,
                    help='udp port (default=6454)')

args = parser.parse_args()

dmx = artdmx.Client(75, args.server, args.port, universe=args.universe)
dmxmasks = np.memmap('/dev/shm/dmxmasks', mode='r',
                     shape=(1, args.universe+1), dtype=bool)

S = L = 0.5
t0 = time.time()

while True:
    if dmxmasks[0, args.universe]:
        for c in range(25):
            h = (time.time() - t0)/5 + c/25
            r, g, b = colorsys.hls_to_rgb(h, S, L)
            dmx.channels[3*c+0] = 255 * r
            dmx.channels[3*c+1] = 255 * g
            dmx.channels[3*c+2] = 255 * b
        dmx.push()
        time.sleep(1/50)
    else:
        time.sleep(1)
