#!/usr/bin/python3

from gi.repository import GObject, Gst

GObject.threads_init()
Gst.init(None)

import semitonevis, frequencyvis

pipeline = Gst.Pipeline()

src = Gst.ElementFactory.make('autoaudiosrc', None)
vis = Gst.ElementFactory.make('semitonevis', None)
conv = Gst.ElementFactory.make('autovideoconvert', None)
sink = Gst.ElementFactory.make('autovideosink', None)

pipeline.add(src)
pipeline.add(vis)
pipeline.add(conv)
pipeline.add(sink)

src.link(vis)
vis.link(conv)
conv.link(sink)

pipeline.set_state(Gst.State.PLAYING)
GObject.MainLoop().run()
