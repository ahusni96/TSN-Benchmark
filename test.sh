#!/bin/bash

# os = [ubuntu, yocto]
# platform = [adln, adls, asl, ehl, rplp, rpls, tglh, tglu]
# controller = [811E1512, 811E2110, GPY115, GPY211, GPY215, DP83867E, I225]

logdir="BTL-S"
milestone="PV"
os="ubuntu ubuntu"
ip="10.158.87.98 10.158.87.102"
controller="I225 I225"
interface="enp2s0 enp1s0"
chapter="6"

python main.py \
--logdir $logdir \
--milestone $milestone \
--os $os \
--ip $ip \
--controller $controller \
--interface $interface \
--chapter $chapter
