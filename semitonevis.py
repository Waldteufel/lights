#!/usr/bin/python3

import numpy as np
import scipy.signal
from gi.repository import GObject, Gst, GstBase

def get_class(t, k):
    element_class = GObject.type_class_peek(t.__gtype__)
    element_class.__class__ = k
    return element_class

XR = 7*12
YR = 16

class SemitoneVis(GstBase.BaseTransform):

    def __init__(self):
        GstBase.BaseTransform.__init__(self)
        self.obuf_array = bytearray(3*XR*YR)
        self.obuf = np.ndarray(shape=(YR, XR, 3), buffer=self.obuf_array, dtype='uint8')

    def my_stft(self, signal, n):
        res = abs(np.fft.rfft(signal[-n:] * self.windows[n])[1:])
        res /= n
        return res

    def do_set_caps(self, incaps, outcaps):
        _, self.rate = incaps.get_structure(0).get_int('rate')
        self.buf = np.zeros(dtype='float64', shape=2**15)
        self.upper = 1e-7

        self.windows = dict()
        self.freqs = dict()
        for i in range(1, 17):
            self.windows[2**i] = scipy.signal.hann(2**i)
            self.freqs[2**i] = np.fft.rfftfreq(2**i, 1/self.rate)

        return True

    def do_transform_caps(self, direction, caps, flt):
        if direction == Gst.PadDirection.SRC:
            return Gst.caps_from_string('audio/x-raw, format=S16LE, channels=1')
        elif direction == Gst.PadDirection.SINK:
            ok, rate = caps.get_structure(0).get_int('rate')
            if ok:
                return Gst.caps_from_string('video/x-raw, format=RGB, width={}, height={}, framerate=1/{}'.format(XR, YR, 50))
            else:
                return Gst.caps_from_string('video/x-raw')

    def do_transform(self, gst_ibuf, gst_obuf):
        ibuf = np.frombuffer(gst_ibuf.extract_dup(0, gst_ibuf.get_size()), dtype='short') / 65535

        self.buf[:-len(ibuf)] = self.buf[len(ibuf):]
        self.buf[-len(ibuf):] = ibuf

        C = 20

        bins = np.zeros(shape=7*12, dtype=np.float64)
        f = 440 * 2 ** (np.arange(-3*12, 4*12)/12) * len(self.buf) / self.rate
        for k in range(0, 8):
            tmp = self.my_stft(self.buf, 2**(15-k))
            tmp[:C] = 0
            bins += tmp[(f / 2**k).astype(int)]

        bins = bins[:XR]

        #ov = np.zeros(shape=12, dtype='float64')
        #for i in range(12):
        #    ov[i] = sum(bins[i::12])

        self.upper = 0.995 * self.upper + 0.005 * max(bins)
        if self.upper != 0:
            bins /= self.upper

        for y in range(YR):
            v = (bins - y/(YR-1))
            self.obuf[YR-y-1,:,1] = np.where(v >= 0, np.exp(-v) * 128 + 127, 0)
            #self.obuf[YR-y-1,:12,1] = np.where(v >= 0, np.exp(-v) * 128 + 127, 0)
            #self.obuf[YR-y-1,12:,1] = self.obuf[YR-y-1,:12,1]

        gst_obuf.fill(0, memoryview(self.obuf_array))
        return Gst.FlowReturn.OK


SemitoneVisT = GObject.type_register(SemitoneVis)
SemitoneVisC = get_class(SemitoneVisT, Gst.ElementClass)
SemitoneVisC.set_metadata('Semitone Visualization', 'Converter/Visualisation', 'Display a frequency analysis with semitone precision', 'Benjamin Richter <br@waldteufel.eu>')
SemitoneVisC.add_pad_template(Gst.PadTemplate.new('sink', Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.caps_from_string('audio/x-raw')))
SemitoneVisC.add_pad_template(Gst.PadTemplate.new('src', Gst.PadDirection.SRC, Gst.PadPresence.ALWAYS, Gst.caps_from_string('video/x-raw')))

Gst.Element.register(None, 'semitonevis', 0, SemitoneVis)
