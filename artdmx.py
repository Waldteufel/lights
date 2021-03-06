#!/usr/bin/python3
# artdmx.py - ArtDMX client

import re
import socket
import numpy


# Credit: Art-Net™ Designed by and Copyright Artistic Licence Holdings Ltd

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

    CHANSPEC_RE = re.compile('([-0-9]*)(?::([-0-9]*))?(?::([-0-9]*))?=(.*)')

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
        self._channels = numpy.ndarray(shape=length, dtype='u1',
                                       buffer=self.buf,
                                       offset=HEADER.itemsize)

    @property
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, channels):
        self._channels[:] = channels

    def push(self):
        self.socket.send(self.buf)
        self.header['sequence'] += 1

    def parse(self, *chanspec):
        for val in chanspec:
            start, stop, step, value = self.CHANSPEC_RE.match(val).groups()
            value = int(value, 0)
            if stop is None:
                index = int(start)
            else:
                start = int(start) if start else None
                stop = int(stop) if stop else None
                step = int(step) if step else None
                index = slice(start, stop, step)
            self.channels[index] = value


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Send an ArtDMX packet. ' +
                                     'Unspecified channels are set to zero.')
    parser.add_argument('chanspec', type=str, nargs='+',
                        help='specified as start:stop:step=V or index=V')
    parser.add_argument('-u', '--universe', metavar='UNIV',
                        type=lambda x: int(x, 0), default=0,
                        help='universe id (default=0)')
    parser.add_argument('-s', '--server', metavar='HOST',
                        type=str, default='localhost',
                        help='server (default=localhost)')
    parser.add_argument('-p', '--port', metavar='PORT', type=int,
                        default=6454, help='udp port (default=6454)')
    parser.add_argument('-l', '--length', metavar='N', default=512, type=int,
                        help='send N channels (default=512)')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='show values sent')
    args = parser.parse_args()

    c = Client(args.length, args.server, args.port, universe=args.universe)
    c.parse(*args.chanspec)

    if args.verbose:
        print(c.channels)
    c.push()
