import aiomysql
from backend.config import settings

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=True,
            cursorclass=aiomysql.DictCursor,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

class DB:
    def __init__(self):
        self.conn = None
        self.cur = None

    async def __aenter__(self):
        pool = await get_pool()
        self.conn = await pool.acquire()
        self.cur = await self.conn.cursor()
        return self.cur

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            await self.cur.close()
        if self.conn:
            await _pool.release(self.conn)
