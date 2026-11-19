#!/bin/bash

LOGDIR="TEMP"
MILESTONE="TEMP"
IP="10.221.202.131 10.221.202.80"
CHAPTER="1"
RTCP="125us"

python main.py \
--logdir $LOGDIR \
--milestone $MILESTONE \
--ip $IP \
--chapter $CHAPTER \
--rtcp $RTCP --stress
