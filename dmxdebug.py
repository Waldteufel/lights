#!/usr/bin/python3

import argparse
from gi.repository import GLib, Gtk
import cairo
import artdmx
import socket
import numpy as np
import threading
import signal

MAXCH = 75

recv_buf = bytearray(b'\0' * (artdmx.HEADER.itemsize + MAXCH))
recv_header = np.ndarray(shape=1, dtype=artdmx.HEADER, buffer=recv_buf)
recv_channels = np.ndarray(shape=MAXCH, dtype='u1', buffer=recv_buf,
                           offset=artdmx.HEADER.itemsize)


class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)
        self.connect("delete-event", Gtk.main_quit)
        self.connect("draw", self.on_draw)
        self.set_app_paintable(True)

    def on_draw(self, widget, cr):
        cr.set_source_rgb(0, 0, 0)
        cr.paint()

        for i in range(MAXCH//3):
            cr.save()
            cr.set_source_rgb(recv_channels[i*3+0]/255,
                              recv_channels[i*3+1]/255,
                              recv_channels[i*3+2]/255)
            cr.rectangle(40*i, 0, 40, 40)
            cr.clip()
            cr.paint()
            cr.restore()


signal.signal(signal.SIGINT, signal.SIG_DFL)

parser = argparse.ArgumentParser(description='Show ArtDMX RGB lights')
parser.add_argument('--bind', default='', metavar='IP', help='bind to ip')
parser.add_argument('--port', type=int, default=6454, metavar='PORT',
                    help='bind to different udp port (default=6454)')
args = parser.parse_args()


def do_listen():
    serv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serv.bind((args.bind, args.port))

    while True:
        serv.recv_into(recv_buf)
        window.queue_draw()

threading.Thread(target=do_listen, daemon=True).start()

window = MainWindow()
window.show_all()

Gtk.main()
