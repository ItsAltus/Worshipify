# db_test.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()  # reads .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, echo=True)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.scalar())