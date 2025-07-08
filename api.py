from fastapi import FastAPI, HTTPException
import sqlite3

app = FastAPI()

def to_sqlite_interval(shorthand: str) -> str:
    unit_map = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }

    if not shorthand or len(shorthand) < 2:
        raise ValueError("Invalid time format")
    try:
        num = int(shorthand[:-1])
    except ValueError:
        raise ValueError("Invalid time format")

    unit = shorthand[-1]

    if unit not in unit_map:
        raise ValueError(f"Unsupported time unit: {unit}")

    return f"-{num} {unit_map[unit]}"

@app.get("/")
async def root():
    stats = {}
    try:
        with sqlite3.connect("/tmp/metrics.db") as con:
            cur = con.cursor()
            res = cur.execute("select host, avg(memory_usage) from memory_usage group by host")
            for host, value in res.fetchall():
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                stats[host]["memory"] = value if value is not None else 0
            res = cur.execute("select host, avg(cpu_usage) from cpu_usage group by host")
            for host, value in res.fetchall():
                stats[host]["cpu"] = value if value is not None else 0
            res = cur.execute("select host, avg(read), avg(write) from disk_usage group by host")
            for host, value_read, value_write in res.fetchall():
                stats[host]["disk_read"] = value_read if value_read is not None else 0
                stats[host]["disk_write"] = value_write if value_write is not None else 0
            res = cur.execute("select host, avg(received), avg(sent) from network_usage group by host")
            for host, value_rcv, value_sent in res.fetchall():
                stats[host]["network_read"] = value_rcv if value_rcv is not None else 0
                stats[host]["network_write"] = value_sent if value_sent is not None else 0
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail="Database error")
    return stats

@app.get("/limit/{limit}")
async def filter(limit: str):
    stats = {}
    try:
        with sqlite3.connect("/tmp/metrics.db") as con:
            cur = con.cursor()
            res = cur.execute("select host from memory_usage group by host;")
            hosts = res.fetchall()
            limit_time = to_sqlite_interval(limit)
            for host_tuple in hosts:
                host = host_tuple[0]
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                res = cur.execute("select avg(memory_usage) from memory_usage where host=? and timestamp >= datetime('now', 'localtime', ?)", (host, limit_time))

                memory_result = res.fetchone()
                stats[host]["memory"] = memory_result[0] if memory_result and memory_result[0] is not None else 0

                res = cur.execute("select avg(cpu_usage) from cpu_usage where host=? and timestamp >= datetime('now', 'localtime', ?)", (host, limit_time))
                cpu_result = res.fetchone()
                stats[host]["cpu"] = cpu_result[0] if cpu_result and cpu_result[0] is not None else 0

                res = cur.execute("select avg(read), avg(write) from disk_usage where host=? and timestamp >= datetime('now', 'localtime', ?)", (host, limit_time))
                disk_data = res.fetchone()
                if disk_data:
                    stats[host]["disk_read"] = disk_data[0] if disk_data[0] is not None else 0
                    stats[host]["disk_write"] = disk_data[1] if disk_data[1] is not None else 0
                else:
                    stats[host]["disk_read"] = 0
                    stats[host]["disk_write"] = 0

                res = cur.execute("select avg(received), avg(sent) from network_usage where host=? and timestamp >= datetime('now', 'localtime', ?)", (host, limit_time))
                network_data = res.fetchone()
                if network_data:
                    stats[host]["network_read"] = network_data[0] if network_data[0] is not None else 0
                    stats[host]["network_write"] = network_data[1] if network_data[1] is not None else 0
                else:
                    stats[host]["network_read"] = 0
                    stats[host]["network_write"] = 0
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail="Database error")
    return stats
