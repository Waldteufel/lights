#!/usr/bin/python3
# artdmx.py - ArtDMX client

import socket
import numpy


HEADER = numpy.dtype([
    ('ident', 'a8'),
    ('opcode', '<u2'),
    ('version', '>u2'),
    ('sequence', 'u1'),
    ('physical', 'u1'),
    ('universe', '<u2'),
    ('length', '>u2'),
])


class Client(object):
    def __init__(self, length, host, port=6454, universe=0):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((host, port))
        self.buf = bytearray(b'\0' * (HEADER.itemsize + length))
        self.header = numpy.ndarray(shape=1, dtype=HEADER, buffer=self.buf)
        self.header['ident'] = 'Art-Net\0'
        self.header['opcode'] = 0x5000
        self.header['version'] = 14
        self.header['sequence'] = 0
        self.header['universe'] = universe
        self.header['length'] = length
        self._values = numpy.ndarray(shape=length, dtype='u1', buffer=self.buf,
                                     offset=HEADER.itemsize)

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values[:] = values

    def push(self):
        self.socket.send(self.buf)
        self.header['sequence'] += 1


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Send an ArtDMX packet')
    parser.add_argument('values', metavar='V', type=int,
                        nargs='+', help='channel values')
    parser.add_argument('-u', '--universe', metavar='UNIV',
                        type=lambda x: int(x, 0), default=0,
                        help='universe id (default=0)')
    parser.add_argument('-s', '--server', metavar='HOST',
                        type=str, default='localhost',
                        help='server (default=localhost)')
    parser.add_argument('-p', '--port', metavar='PORT', type=int,
                        default=6454, help='udp port (default=6454)')

    args = parser.parse_args()

    c = Client(len(args.values), args.server, args.port,
               universe=args.universe)
    c.values[:] = args.values
    c.push()
