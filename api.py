from fastapi import FastAPI, HTTPException
import aiosqlite
from contextlib import asynccontextmanager
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool: Optional[aiosqlite.Connection] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _connection_pool
    logger.info("Initializing database connection pool")
    _connection_pool = await aiosqlite.connect("/tmp/metrics.db")
    # Enable row factory for better data access
    if _connection_pool is not None:
        _connection_pool.row_factory = aiosqlite.Row
    yield
    # Shutdown
    if _connection_pool:
        logger.info("Closing database connection pool")
        await _connection_pool.close()

app = FastAPI(lifespan=lifespan)

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
    """Get aggregate statistics for all hosts"""
    if _connection_pool is None:
        raise HTTPException(status_code=503, detail="Database connection not available")

    stats = {}
    try:
        # Use the global connection pool instead of creating new connections
        async with _connection_pool.execute("SELECT host, avg(memory_usage) as avg_memory FROM memory_usage GROUP BY host") as cursor:
            async for row in cursor:
                host = row['host']
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                stats[host]["memory"] = row['avg_memory'] if row['avg_memory'] is not None else 0

        # CPU usage
        async with _connection_pool.execute("SELECT host, avg(cpu_usage) as avg_cpu FROM cpu_usage GROUP BY host") as cursor:
            async for row in cursor:
                host = row['host']
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                stats[host]["cpu"] = row['avg_cpu'] if row['avg_cpu'] is not None else 0

        # Disk usage
        async with _connection_pool.execute("SELECT host, avg(read) as avg_read, avg(write) as avg_write FROM disk_usage GROUP BY host") as cursor:
            async for row in cursor:
                host = row['host']
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                stats[host]["disk_read"] = row['avg_read'] if row['avg_read'] is not None else 0
                stats[host]["disk_write"] = row['avg_write'] if row['avg_write'] is not None else 0

        # Network usage
        async with _connection_pool.execute("SELECT host, avg(received) as avg_received, avg(sent) as avg_sent FROM network_usage GROUP BY host") as cursor:
            async for row in cursor:
                host = row['host']
                if host not in stats:
                    stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}
                stats[host]["network_read"] = row['avg_received'] if row['avg_received'] is not None else 0
                stats[host]["network_write"] = row['avg_sent'] if row['avg_sent'] is not None else 0

    except aiosqlite.Error as e:
        logger.error(f"Database error in root endpoint: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in root endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return stats

@app.get("/limit/{limit}")
async def filter_by_time(limit: str):
    """Get statistics filtered by time limit (e.g., '1h', '30m', '7d')"""
    if _connection_pool is None:
        raise HTTPException(status_code=503, detail="Database connection not available")

    try:
        limit_time = to_sqlite_interval(limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")

    stats = {}
    try:
        # Get all hosts first
        async with _connection_pool.execute("SELECT DISTINCT host FROM memory_usage") as cursor:
            hosts = [row['host'] async for row in cursor]

        # Process each host
        for host in hosts:
            if host not in stats:
                stats[host] = {"memory": 0, "cpu": 0, "disk_read": 0, "disk_write": 0, "network_read": 0, "network_write": 0}

            # Memory usage
            async with _connection_pool.execute(
                "SELECT avg(memory_usage) as avg_memory FROM memory_usage WHERE host=? AND timestamp >= datetime('now', 'localtime', ?)",
                (host, limit_time)
            ) as cursor:
                row = await cursor.fetchone()
                stats[host]["memory"] = row['avg_memory'] if row and row['avg_memory'] is not None else 0

            # CPU usage
            async with _connection_pool.execute(
                "SELECT avg(cpu_usage) as avg_cpu FROM cpu_usage WHERE host=? AND timestamp >= datetime('now', 'localtime', ?)",
                (host, limit_time)
            ) as cursor:
                row = await cursor.fetchone()
                stats[host]["cpu"] = row['avg_cpu'] if row and row['avg_cpu'] is not None else 0

            # Disk usage
            async with _connection_pool.execute(
                "SELECT avg(read) as avg_read, avg(write) as avg_write FROM disk_usage WHERE host=? AND timestamp >= datetime('now', 'localtime', ?)",
                (host, limit_time)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    stats[host]["disk_read"] = row['avg_read'] if row['avg_read'] is not None else 0
                    stats[host]["disk_write"] = row['avg_write'] if row['avg_write'] is not None else 0

            # Network usage
            async with _connection_pool.execute(
                "SELECT avg(received) as avg_received, avg(sent) as avg_sent FROM network_usage WHERE host=? AND timestamp >= datetime('now', 'localtime', ?)",
                (host, limit_time)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    stats[host]["network_read"] = row['avg_received'] if row['avg_received'] is not None else 0
                    stats[host]["network_write"] = row['avg_sent'] if row['avg_sent'] is not None else 0

    except aiosqlite.Error as e:
        logger.error(f"Database error in filter endpoint: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in filter endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return stats
