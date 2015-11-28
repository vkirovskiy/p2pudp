
# What is it

This script demonstrates how to connect using UDP hole punching.
If you want completed tool to make udp hole use p2ptool instead.

# How it works

This script is a part of p2p service that uses UDP to connect to other clients.

Script requires server udphelper.lua runned on somewhere in internet.
Server helps clients to find each other by sending them its real ip addressed and ports.
Then clients need to use UDP Hole Punching method to connect.

udphepler.lua must runs on server with real IP but clients do not require it and
can run behind firewall with NAT.

