#!/usr/bin/python

from scapy.all import *

def arp_display(pkt):
#  pkt.show()
  if ARP in pkt and pkt[ARP].op in (1,2): #who-has or is-at
    print "ARP Probe from: " + pkt[ARP].hwsrc

print sniff(prn=arp_display, filter="arp", store=0, count=30)
