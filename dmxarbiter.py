#!/usr/bin/python3

import os
import socket
import numpy as np
import artdmx
import time

MAXCH = 76
UNIVERSES = 16
RANGE = np.arange(MAXCH)

serv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serv.bind(('', 6454))

recv_buf = bytearray(b'\0' * (artdmx.HEADER.itemsize + MAXCH))
recv_header = np.ndarray(shape=1, dtype=artdmx.HEADER, buffer=recv_buf)
recv_channels = np.ndarray(shape=MAXCH, dtype='u1', buffer=recv_buf,
                           offset=artdmx.HEADER.itemsize)

client = artdmx.Client(81, '172.31.97.40')

# 75 color channels
mapping = np.arange(0, 75)

# insert a gap every 15 channels (16 channels control 3x5 color leds)
mapping += np.arange(0, 75)//15

# offset by 1 because the gap comes first
mapping += 1

# then rotate by 30 to start in the room corner
mapping = np.roll(mapping, 30)

# add the garden gnome as channel 75
mapping = np.concatenate((mapping, [64]))

open('/dev/shm/dmxmasks', 'a').close()
masks = np.memmap('/dev/shm/dmxmasks', mode='r+', shape=(MAXCH, UNIVERSES), dtype=bool)

heads = np.zeros(shape=MAXCH, dtype='u2')
heads[:] = np.argmax(masks, axis=1)

open('/dev/shm/dmxchannels', 'a').close()
channels = np.memmap('/dev/shm/dmxchannels', mode='r+', shape=(MAXCH, UNIVERSES), dtype='u1')

while True:
    serv.recv_into(recv_buf)
    u = int(recv_header['universe'])
    c, u = u & 0xf000, u & 0x0fff

    if c & 0x8000:
        if c == 0x8000:
            masks[:, u] = recv_channels
        elif c == 0xa000:  # think "alternate"
            masks[:, u] ^= recv_channels
        elif c == 0xc000:  # think "combine"
            masks[:, u] |= recv_channels
        elif c == 0xd000:  # think "delete"
            masks[:, u] &= ~recv_channels
        elif c == 0xf000:  # think "force"
            pass
        heads[:] = np.argmax(masks, axis=1)
    else:
        channels[:, u] = recv_channels

    client.channels[mapping] = channels[RANGE, heads]
    client.push()
