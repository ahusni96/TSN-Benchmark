#!/bin/bash

# os = [ubuntu, yocto]
# platform = [adln, adls, asl, ehl, rplp, rpls, tglh, tglu]
# controller = [811E1512, 811E2110, GPY115, GPY211, GPY215, DP83867E, I225]

LOGDIR="PTL-H"
MILESTONE="RTCP2.0"
OS="ubuntu ubuntu"
IP="10.221.202.72 10.221.202.123"
CONTROLLER="I225 I225"
INTERFACE="enp1s0 enp1s0"
CHAPTER="1"
RTCP="125us"

python main.py \
--logdir $LOGDIR \
--milestone $MILESTONE \
--os $OS \
--ip $IP \
--controller $CONTROLLER \
--interface $INTERFACE \
--chapter $CHAPTER \
--rtcp $RTCP
