#!/usr/bin/python

"""
NFV Services Topology Class
"""

from mininet.topo import Topo


class NFVServiceTopo(Topo):
    "Topology of NFV Services Management Component"

    def __init__(self, scenario="none", **kwargs):
        Topo.__init__(self, **kwargs)

        # Declare Switches
        switches = [
            self.addSwitch('nfv-' + scenario + '-s0')
        ]

if __name__ == "__main__":
    print "Not Callable File."
