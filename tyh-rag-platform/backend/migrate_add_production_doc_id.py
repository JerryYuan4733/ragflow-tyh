"""Add production_document_id column to document_meta table"""
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def migrate():
    async with engine.begin() as conn:
        # Check if column already exists
        result = await conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = 'document_meta' AND COLUMN_NAME = 'production_document_id'"
        ))
        if result.fetchone():
            print("Column production_document_id already exists, skipping.")
            return
        await conn.execute(text(
            "ALTER TABLE document_meta ADD COLUMN production_document_id VARCHAR(100) NULL"
        ))
        print("Column production_document_id added successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
