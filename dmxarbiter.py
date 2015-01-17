#!/usr/bin/python3

import socket
import numpy as np
import artdmx
import time

MAXCH = 75
UNIVERSES = 256

serv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serv.bind(('', 6454))

recv_buf = bytearray(b'\0' * (artdmx.HEADER.itemsize + MAXCH))
recv_header = np.ndarray(shape=1, dtype=artdmx.HEADER, buffer=recv_buf)
recv_channels = np.ndarray(shape=MAXCH, dtype='u1', buffer=recv_buf,
                           offset=artdmx.HEADER.itemsize)

client = artdmx.Client(81, '172.31.97.40')

mapping = np.concatenate((
    np.arange(49, 64),
    np.arange(65, 80),
    np.arange(1, 16),
    np.arange(17, 32),
    np.arange(33, 48),
))

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
