"""
SQLAlchemy 엔진 및 세션 관리
- create_engine, SessionLocal, Base 정의
- DB 의존성 주입 함수 get_db
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import settings

# MySQL 엔진 생성 (커넥션 풀)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # 끊긴 커넥션 자동 감지
    pool_recycle=3600,    # 1시간마다 커넥션 재활용 (MySQL wait_timeout 대응)
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 모델의 베이스 클래스
Base = declarative_base()


def get_db():
    """
    FastAPI 의존성: 요청마다 새 세션 발급 후 종료 시 닫음.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    앱 시작 시 호출: 정의된 모델들의 테이블을 생성합니다.
    """
    # models를 import해야 Base.metadata에 등록됨
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
