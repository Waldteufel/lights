#!/usr/bin/python3

import numpy as np
import scipy.signal
from gi.repository import GObject, Gst, GstBase

import artdmx

def get_class(t, k):
    element_class = GObject.type_class_peek(t.__gtype__)
    element_class.__class__ = k
    return element_class

class ArtDMXSink(GstBase.BaseSink):

    def __init__(self):
        GstBase.BaseTransform.__init__(self)
        self.cl = artdmx.Client(81, '172.31.97.40')
        self.cl.values[:] = 127
        self.mapping = np.concatenate((
            np.arange(49, 64),
            np.arange(65, 80),
            np.arange(1, 16),
            np.arange(17, 32),
            np.arange(33, 48),
        ))

    def do_render(self, gst_ibuf):
        ibuf = np.frombuffer(gst_ibuf.extract_dup(0, gst_ibuf.get_size()), dtype='u1')[:75]
        self.cl.values[self.mapping] = ibuf
        self.cl.push()
        return Gst.FlowReturn.OK


ArtDMXSinkT = GObject.type_register(ArtDMXSink)
ArtDMXSinkC = get_class(ArtDMXSinkT, Gst.ElementClass)
ArtDMXSinkC.set_metadata('ArtDMX Sink', 'Sink', 'Display a video on an ArtDMX device', 'Benjamin Richter <br@waldteufel.eu>')
ArtDMXSinkC.add_pad_template(Gst.PadTemplate.new('sink', Gst.PadDirection.SINK, Gst.PadPresence.ALWAYS, Gst.caps_from_string('video/x-raw, format=RGB, height=1, width=25')))

Gst.Element.register(None, 'artdmxsink', 0, ArtDMXSink)
