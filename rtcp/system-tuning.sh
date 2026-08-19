#!/bin/bash
#
# System performance tuning for real-time KPI testing.
#

set -e

IFACE="$1"

if [ -z "$IFACE" ]; then
  IFACE=$(sudo lshw -class network | grep -A 5 "I226" | awk '/logical name:/ {print $3; exit}')
fi

if [ -z "$IFACE" ]; then
    echo "I226 interface not found"
    exit 1
fi

echo "Using interface: $IFACE"

systemctl stop sysstat-collect.timer 2>/dev/null || true
systemctl disable sysstat-collect.timer 2>/dev/null || true
systemctl stop systemd-tmpfiles-clean.timer 2>/dev/null || true
systemctl stop fwupd-refresh.timer 2>/dev/null || true
systemctl stop fwupd.service 2>/dev/null || true
systemctl stop motd-news.timer 2>/dev/null || true
systemctl stop snapd.socket 2>/dev/null || true
systemctl stop snapd 2>/dev/null || true

echo -1 > /proc/sys/kernel/sched_rt_runtime_us
echo 0 > /proc/sys/kernel/timer_migration
sudo sysctl -w kernel.nmi_watchdog=0 > /dev/null
sudo sysctl -w kernel.watchdog=0 > /dev/null
sudo sysctl -w kernel.softlockup_all_cpu_backtrace=0 > /dev/null

# Prevent NetworkManager from auto-activating test interface during startup
if command -v nmcli >/dev/null 2>&1; then
  set -x
  nmcli dev set "${IFACE}" managed no 2>/dev/null || true
  { set +x; } 2>/dev/null
fi

if systemctl is-enabled irqbalance >/dev/null 2>&1 || systemctl is-active irqbalance >/dev/null 2>&1; then
  set -x
  systemctl stop irqbalance || true
  systemctl disable irqbalance || true
  { set +x; } 2>/dev/null
fi

echo "Configuring CPU 1 for performance mode:"
set -x
cpupower -c 1 idle-set -d 0
cpupower -c 1 idle-set -d 1
cpupower -c 1 idle-set -d 2
cpupower -c 1 idle-set -d 3
cpupower -c 1 frequency-set --min 2900M --max 2900M -g performance
{ set +x; } 2>/dev/null
if tuna --help 2>&1 | grep -q -e "--isolate"; then
    set -x
    tuna --cpus=1 --isolate
else
    set -x
    tuna isolate --cpus=1
fi
{ set +x; } 2>/dev/null

TOTAL_CPUS=$(nproc --all)
echo -e "\nConfiguring ${TOTAL_CPUS} CPUs for powersave mode (excluding CPU 1):"
for ((cpu = 0; cpu < TOTAL_CPUS; cpu++)); do
  if [ "$cpu" -ne 1 ]; then
    BASE_FREQ_PATH="/sys/devices/system/cpu/cpu${cpu}/cpufreq/base_frequency"
    if [ -r "$BASE_FREQ_PATH" ]; then
      BASE_FREQ_KHZ=$(cat "$BASE_FREQ_PATH")
      BASE_FREQ_MHZ=$((BASE_FREQ_KHZ / 1000))
      set -x
      cpupower -c "$cpu" frequency-set --max "${BASE_FREQ_MHZ}M" -g powersave
      { set +x; } 2>/dev/null
    else
      echo "Warning: Could not read ${BASE_FREQ_PATH}, skipping CPU ${cpu}"
    fi
  fi
done

echo -e "\nSetting (${IFACE}-TxRx-1) affinity to CPU 1:"
IRQ_NUM=$(grep "${IFACE}-TxRx-1" /proc/interrupts | awk '{print $1}' | sed 's/://')
if [ -n "$IRQ_NUM" ]; then
  echo "echo 1 >/proc/irq/${IRQ_NUM}/smp_affinity_list"
  echo 1 >/proc/irq/${IRQ_NUM}/smp_affinity_list
else
  echo "Warning: Could not find IRQ for ${IFACE}-TxRx-1"
fi

echo -e "\nFixing Uncore Frequency to 3.4 GHz:"
set -x
wrmsr -p 1 0x620 0x2222
{ set +x; } 2>/dev/null

echo -e "\nIsolating L3 cache for CPU 1:"
set -x
wrmsr 0xc91 0xfc0
wrmsr 0xc90 0x03f
wrmsr -p 1 0xc8f 0x100000000
{ set +x; } 2>/dev/null

# --- Verify ---
echo ""
echo "=== Active timers remaining ==="
systemctl list-timers --no-pager | grep -v "^$" | head -10

echo ""
echo "=== Processes on CPU1 ==="
ps -eo pid,psr,cls,rtprio,comm | awk '$2==1'

echo ""
echo "=== Done ==="

exit 0
