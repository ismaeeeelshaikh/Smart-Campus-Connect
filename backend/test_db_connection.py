import asyncio
import asyncpg
from app.config import settings

async def test_connection():
    # asyncpg wants a plain postgresql:// URL, without the SQLAlchemy "+asyncpg" driver part
    url = settings.database_url.replace("+asyncpg", "")
    try:
        conn = await asyncpg.connect(url)
        result = await conn.fetch("SELECT version()")
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {result[0][0]}")
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
