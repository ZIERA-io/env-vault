"""
ENV Vault - 데이터베이스 연결
SQLite (로컬 단일 파일, 외부 DB 불필요)
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# data 디렉토리 생성
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{settings.DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 15,
    },
    pool_pre_ping=True,
)

# SQLite WAL 모드 + 외래 키 활성화
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   # 동시 읽기 성능 향상
    cursor.execute("PRAGMA foreign_keys=ON")    # FK 제약 강제
    cursor.execute("PRAGMA synchronous=NORMAL") # 성능/안전 균형
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 의존성 주입용 DB 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
