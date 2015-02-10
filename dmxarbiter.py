#!/usr/bin/python3

import socket
import numpy as np
import artdmx
import time

MAXCH = 76
UNIVERSES = 16

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

masks = np.zeros(shape=(MAXCH, UNIVERSES), dtype=bool)
heads = np.zeros(shape=MAXCH, dtype='u2')

channels = np.zeros(shape=MAXCH, dtype='u1')

while True:
    serv.recv_into(recv_buf)
    u = int(recv_header['universe'])

    if u >= 0x8000:
        masks[:, u & 0x7fff] = recv_channels > 0
        heads[:] = np.argmax(masks, axis=1)
        with open('/dev/shm/dmxmasks', 'wb') as f:
            for i in range(UNIVERSES):
                f.write(masks[:, i].choose('01'))
                f.write(b'\n')
    else:
        m = (heads == u)
        channels[m] = recv_channels[m]
        client.channels[mapping] = channels
        client.push()
