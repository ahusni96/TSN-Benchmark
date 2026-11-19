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
apt install libbpf-dev libxdp-dev clang llvm libyaml-dev rt-tests libmosquitto-dev tuna libpci-dev gettext libssl-dev xdp-tools htop stress-ng lm-sensors -y --allow-downgrades

#if (( $(echo "$KERNEL_VER >= 6.18" | bc -l) ))
#then
#    apt remove libbpf9999 -y
#    wget -P /tmp/ https://archive.ubuntu.com/ubuntu/pool/main/libb/libbpf/libbpf1_1.3.0-2build2_amd64.deb
#    wget -P /tmp/ https://archive.ubuntu.com/ubuntu/pool/main/libb/libbpf/libbpf-dev_1.3.0-2build2_amd64.deb
#    dpkg --install /tmp/libbpf*.deb
#    rm -rf /tmp/libbpf*.deb
#fi

# Install cpupower
cd && rm -rf mainline-tracking
git config --global http.version HTTP/1.1
cd && git clone --depth 1 --branch linux/v$KERNEL_VER https://github.com/intel/mainline-tracking.git
cd mainline-tracking/tools/power/cpupower
make && sudo make install

# Get gPTP config
wget https://raw.githubusercontent.com/richardcochran/linuxptp/master/configs/gPTP.cfg -O /etc/gPTP.cfg


##################################################################
##.....................Build RTC-Testbench........................
rm -rf ~/RTC-Testbench
git config --global http.version HTTP/1.1
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

# Stop services
systemctl stop apt-daily-upgrade.timer
systemctl stop apt-daily.timer
systemctl stop anacron.timer
systemctl stop anacron.service

# Disable services
systemctl disable apt-daily-upgrade.timer
systemctl disable apt-daily.timer
systemctl disable anacron.timer
systemctl disable anacron.service
