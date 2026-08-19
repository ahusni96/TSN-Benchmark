#!/bin/bash

# os = [ubuntu, yocto]
# platform = [adln, adls, asl, ehl, rplp, rpls, tglh, tglu]
# controller = [811E1512, 811E2110, GPY115, GPY211, GPY215, DP83867E, I225]

logdir="PTL-H"
milestone="MR1"
os="ubuntu ubuntu"
ip="10.221.202.137 10.221.202.97"
controller="I225 I225"
interface="enp1s0 enp1s0"
chapter="1 2 3 4 5"

python main.py \
--logdir $logdir \
--milestone $milestone \
--os $os \
--ip $ip \
--controller $controller \
--interface $interface \
--chapter $chapter
