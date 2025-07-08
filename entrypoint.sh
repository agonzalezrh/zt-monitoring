#!/bin/bash
# Set the path to your SQLite database
DB_PATH="/tmp/metrics.db"
cd /app/

if [ ! -x ${DB_PATH} ]; then
# Create the database and tables
sqlite3 $DB_PATH <<EOF
CREATE TABLE IF NOT EXISTS cpu_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_usage REAL
);

CREATE TABLE IF NOT EXISTS memory_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    memory_usage REAL
);

CREATE TABLE IF NOT EXISTS disk_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read REAL,
    write REAL
);

CREATE TABLE IF NOT EXISTS network_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    received REAL,
    sent REAL
);
EOF
fi
fastapi dev --host 0.0.0.0 --port 9999 api.py  &

# Run every 5 seconds, timeout after 10 seconds.
watch -n 5 'timeout 4 ansible-playbook main.yml || echo "Playbook timed out or failed"'
