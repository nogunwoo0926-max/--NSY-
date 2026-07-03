"""
FastAPI 애플리케이션 진입점
실행: uvicorn backend.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router as diagnosis_router
from backend.db.database import init_db

app = FastAPI(
    title="AI 스마트 데이터 품질 진단 API",
    description="CSV/Excel 업로드 → 자동 품질 진단 → MySQL 저장",
    version="1.0.0",
)

# CORS: Streamlit(다른 포트)에서 호출 가능하도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 운영 시엔 도메인 명시 권장
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(diagnosis_router)


@app.on_event("startup")
def on_startup():
    """앱 시작 시 테이블 자동 생성"""
    init_db()


@app.get("/")
def root():
    return {
        "service": "Data Quality Diagnosis API",
        "version": "1.0.0",
        "docs": "/docs",
    }
