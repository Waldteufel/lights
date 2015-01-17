Lights
======
[![Build Status](https://travis-ci.org/Waldteufel/lights.svg?branch=master)](https://travis-ci.org/Waldteufel/lights)

`artdmx.py` provides an ArtDMX client

`dmxarbiter.py` combines multiple DMX universes using masks and priorities

`soundvis.py` grabs audio and outputs a visualization over ArtDMX

`dmxdebug.py` shows rgb values of DMX channels


ArtDMX Arbiter
--------------

Multiple competing ArtDMX clients usually result in nasty flickering. This
arbiter forwards a value only if it is not overridden by a value in a lower
universe. Channels in universe N can be masked by setting the corresponding
channel in universe 0x8000|N (most significant bit set).
