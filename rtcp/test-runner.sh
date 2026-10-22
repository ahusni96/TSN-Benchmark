#!/bin/sh

SIDE=$1
PATH=$2
cd $PATH && ../../../build/$SIDE -c $SIDE.yaml > /dev/null
