"""
db/connection.py

Creates the shared asyncpg connection pool. main.py's lifespan calls
create_pool() once at startup and passes the pool to queries.init_pool().
"""

import asyncpg


async def create_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(database_url, min_size=1, max_size=10)