from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

DATABASE_URL = f"sqlite:///{settings.SQLITE_PATH}"

# check_same_thread=False 允许 FastAPI 多线程上下文安全共享 sqlite 连接
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_sqlite_migrations():
    """轻量级向后兼容迁移：为既有 SQLite 表补充新增列"""
    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(diaries)")).fetchall()]
        if cols and "mood_color" not in cols:
            conn.execute(text("ALTER TABLE diaries ADD COLUMN mood_color VARCHAR(20)"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
