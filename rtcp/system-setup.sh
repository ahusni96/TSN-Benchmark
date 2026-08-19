#!/bin/bash

# Check root
if [[ $EUID -ne 0 ]]; then
	printf "This script must be run as root\n"
	exit 1
fi



SIDE=$1
IFACE=$(sudo lshw -class network | grep -A 5 "I226" | awk '/logical name:/ {print $3; exit}')
KERNEL_VER=$(uname -r | cut -d'-' -f1 | sed 's/rt//')

printf "Setting up platform for $SIDE side...\n"



##################################################################
##..................Setting up dependencies.......................
apt install libbpf-dev libxdp-dev clang llvm libyaml-dev rt-tests libmosquitto-dev tuna libpci-dev gettext -y --allow-downgrades

if [[ "$KERNEL_VER" == "6.18" ]]
then
    apt remove libbpf9999 -y
    wget -P /tmp/ https://archive.ubuntu.com/ubuntu/pool/main/libb/libbpf/libbpf1_1.6.3-1ubuntu1_amd64.deb
    wget -P /tmp/ https://archive.ubuntu.com/ubuntu/pool/main/libb/libbpf/libbpf-dev_1.6.3-1ubuntu1_amd64.deb
    dpkg --install /tmp/libbpf*.deb
fi

# Install cpupower
cd && git clone --depth 1 --branch linux/v$KERNEL_VER https://github.com/intel/mainline-tracking.git
cd mainline-tracking/tools/power/cpupower
make && sudo make install

# Get gPTP config
wget https://raw.githubusercontent.com/richardcochran/linuxptp/master/configs/gPTP.cfg -O /etc/gPTP.cfg



##################################################################
##.....................Build RTC-Testbench........................
cd && git clone https://github.com/Linutronix/RTC-Testbench.git
mkdir -p ~/RTC-Testbench/build
cd ~/RTC-Testbench/build

if [[ $SIDE == "reference" ]]
then
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DWITH_MQTT=FALSE -DRX_TIMESTAMP=FALSE -DTX_TIMESTAMP=FALSE ..
elif [[ $SIDE == "mirror" ]]
then
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr -DWITH_MQTT=FALSE -DRX_TIMESTAMP=TRUE -DTX_TIMESTAMP=TRUE ..
fi

make && sudo make install



##################################################################
##.......................Other changes............................

# Rename interface in *.yaml config
cd ~/RTC-Testbench/tests/intel_kpi/
find . -name "*.yaml" | xargs sed -i "s/enp3s0/$IFACE/g"

# Disable services
systemctl disable --now apt-daily-upgrade.timer 2> /dev/null || true
systemctl disable --now apt-daily.timer 2> /dev/null || true
systemctl disable --now anacron.timer 2> /dev/null || true
systemctl disable --now anacron.service 2> /dev/null || true

# Change MAC address
sudo ip link set dev $IFACE down
if [[ $SIDE == "reference" ]]
then
    sudo ip link set dev $IFACE address a8:74:1d:9d:98:d8
elif [[ $SIDE == "mirror" ]]
then
    sudo ip link set dev $IFACE address a8:74:1d:9d:36:14
fi
sudo ip link set dev $IFACE up

# Change link speed
sudo ethtool -s $IFACE speed 1000 autoneg on duplex full
