# ZeroTouch Monitoring

A containerized system monitoring solution that collects metrics from multiple hosts and provides a REST API for querying performance data.

## Overview

ZeroTouch Monitoring uses Ansible automation to collect system metrics from remote hosts via SSH and stores them in a SQLite database. It provides a FastAPI-based REST API to query collected metrics with time-based filtering capabilities.

## Features

- **Multi-host monitoring**: Monitor multiple remote hosts through a bastion host
- **Comprehensive metrics**: CPU usage, memory usage, disk I/O, and network I/O
- **Time-based queries**: Filter metrics by time periods (seconds, minutes, hours, days, weeks)
- **Containerized deployment**: Runs in a UBI9-based container with Python 3.11
- **Fallback support**: Works with or without psutil library using /proc filesystem
- **Error handling**: Robust error handling with proper HTTP status codes
- **Input validation**: Time format validation with error messages

## Architecture

- **monitoring.py**: Core monitoring script that collects system metrics
- **api.py**: FastAPI REST API server for querying metrics
- **main.yml**: Ansible playbook for orchestrating monitoring across hosts
- **SQLite database**: Stores collected metrics with timestamps

## API Endpoints

### GET /
Returns average metrics for all monitored hosts.

**Response format:**
```json
{
  "hostname": {
    "memory": 45.2,
    "cpu": 12.5,
    "disk_read": 1024,
    "disk_write": 512,
    "network_read": 2048,
    "network_write": 1536
  }
}
```

**Error responses:**
- `500`: Database error

### GET /limit/{limit}
Returns metrics filtered by time period.

**Time units:**
- `s` - seconds
- `m` - minutes
- `h` - hours
- `d` - days
- `w` - weeks

**Examples:**
- `/limit/5m` - Last 5 minutes
- `/limit/1h` - Last hour
- `/limit/24h` - Last 24 hours

**Error responses:**
- `422`: Invalid time format (e.g., invalid unit or non-numeric value)
- `500`: Database error

**Notes:**
- Missing or null values default to 0
- Time format must be numeric followed by unit (e.g., "5m", "1h")

## Environment Variables

- `BASTION_HOST`: SSH bastion host address
- `BASTION_PORT`: SSH port (default: 22)
- `BASTION_USER`: SSH username
- `BASTION_PASSWORD`: SSH password
- `OTHER_HOSTS`: Space-separated list of additional hosts to monitor

## Usage

### Container Deployment
```bash
# Build the container
podman build -t zt-monitoring .

# Run with environment variables
podman run -d \
  -e BASTION_HOST=your-bastion-host \
  -e BASTION_PORT=22 \
  -e BASTION_USER=your-user \
  -e BASTION_PASSWORD=your-password \
  -e OTHER_HOSTS="host1 host2 host3" \
  -p 9999:9999 \
  zt-monitoring
```

### API Access
The API runs on port 9999 and can be accessed at:
- `http://localhost:9999/` - All metrics
- `http://localhost:9999/limit/1h` - Last hour's metrics

## Database Schema

The SQLite database contains four tables:
- `cpu_usage`: Host CPU utilization percentages
- `memory_usage`: Host memory availability percentages
- `disk_usage`: Host disk read/write operations
- `network_usage`: Host network bytes received/sent

All tables include `host`, `timestamp`, and metric-specific columns.

## Dependencies

- Python 3.11+
- Ansible 11.3.0+
- FastAPI
- SQLite3
- sshpass (for SSH automation)
- psutil (optional, with /proc fallback)
