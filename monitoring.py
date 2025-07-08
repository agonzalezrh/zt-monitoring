#!/usr/bin/python3
import json
import time
import os

# Try to import psutil, but continue without it if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def get_cpu_usage():
    """Get CPU usage percentage"""
    if PSUTIL_AVAILABLE:
        return psutil.cpu_percent(interval=1)
    else:
        # Fallback: read from /proc/stat
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
            cpu_times = [int(x) for x in line.split()[1:]]
            idle_time = cpu_times[3]  # idle time
            total_time = sum(cpu_times)

            # Take a second measurement for calculation
            time.sleep(1)

            with open('/proc/stat', 'r') as f:
                line = f.readline()
            cpu_times2 = [int(x) for x in line.split()[1:]]
            idle_time2 = cpu_times2[3]
            total_time2 = sum(cpu_times2)

            # Calculate CPU usage
            idle_delta = idle_time2 - idle_time
            total_delta = total_time2 - total_time

            if total_delta == 0:
                return 0.0

            cpu_usage = 100.0 * (1.0 - idle_delta / total_delta)
            return round(cpu_usage, 2)
        except (IOError, ValueError, IndexError):
            return 0.0

def get_memory_usage():
    """Get memory usage - returns available memory as percentage of total"""
    if PSUTIL_AVAILABLE:
        vm = psutil.virtual_memory()
        return round(vm.available * 100 / vm.total, 2)
    else:
        # Fallback: read from /proc/meminfo
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(':')
                    meminfo[key.strip()] = int(value.split()[0]) * 1024  # Convert kB to bytes

            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', 0)

            # If MemAvailable is not available, calculate it
            if available == 0:
                free = meminfo.get('MemFree', 0)
                buffers = meminfo.get('Buffers', 0)
                cached = meminfo.get('Cached', 0)
                available = free + buffers + cached

            if total == 0:
                return 0.0

            return round(available * 100 / total, 2)
        except (IOError, ValueError, KeyError):
            return 0.0

def get_disk_io():
    """Get disk I/O counters"""
    if PSUTIL_AVAILABLE:
        disk_io = psutil.disk_io_counters(perdisk=False)
        if disk_io:
            return disk_io.read_count, disk_io.write_count
        else:
            return 0, 0
    else:
        # Fallback: read from /proc/diskstats
        try:
            read_count = 0
            write_count = 0

            with open('/proc/diskstats', 'r') as f:
                for line in f:
                    fields = line.split()
                    if len(fields) >= 14:
                        # Skip partitions (look for devices like sda, nvme0n1, etc.)
                        device = fields[2]
                        if not any(char.isdigit() for char in device[-1:]):  # Skip numbered partitions
                            read_count += int(fields[5])   # reads completed
                            write_count += int(fields[9])  # writes completed

            return read_count, write_count
        except (IOError, ValueError, IndexError):
            return 0, 0

def get_network_io():
    """Get network I/O counters"""
    if PSUTIL_AVAILABLE:
        net_io = psutil.net_io_counters(pernic=False)
        if net_io:
            return net_io.bytes_recv, net_io.bytes_sent
        else:
            return 0, 0
    else:
        # Fallback: read from /proc/net/dev
        try:
            bytes_recv = 0
            bytes_sent = 0

            with open('/proc/net/dev', 'r') as f:
                # Skip header lines
                f.readline()
                f.readline()

                for line in f:
                    fields = line.split()
                    if len(fields) >= 17:
                        interface = fields[0].rstrip(':')
                        # Skip loopback interface
                        if interface != 'lo':
                            bytes_recv += int(fields[1])   # receive bytes
                            bytes_sent += int(fields[9])   # transmit bytes

            return bytes_recv, bytes_sent
        except (IOError, ValueError, IndexError):
            return 0, 0

def main():
    """Main monitoring function"""
    # Get all metrics
    cpu_usage = get_cpu_usage()
    memory_usage = get_memory_usage()
    disk_read, disk_write = get_disk_io()
    net_recv, net_sent = get_network_io()

    # Prepare monitoring data
    monitoring = {
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_usage_read': disk_read,
        'disk_usage_write': disk_write,
        'network_usage_received': net_recv,
        'network_usage_sent': net_sent,
        'psutil_available': PSUTIL_AVAILABLE
    }

    print(json.dumps(monitoring))

if __name__ == "__main__":
    main()




























