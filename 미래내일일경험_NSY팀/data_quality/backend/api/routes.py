"""
FastAPI 라우터 (REST 엔드포인트)
- POST   /api/diagnose       : CSV/Excel 업로드 + 5지표 진단 + DB 저장
- GET    /api/history        : 진단 이력 목록
- GET    /api/history/{id}   : 진단 이력 단건
- DELETE /api/history/{id}   : 진단 이력 삭제
- GET    /api/health         : 헬스 체크
"""
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db import crud
from backend.schemas.diagnosis import DiagnosisHistoryOut, DiagnosisResult
from backend.services.diagnosis_service import (
    SUPPORTED_EXTENSIONS,
    load_tabular_file_from_bytes,
    run_full_diagnosis,
)
from backend.config import settings

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


def verify_admin_key(x_api_key: str = Header(..., description="관리자 API 키")):
    if not settings.ADMIN_API_KEY or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="유효하지 않은 API 키입니다.")

router = APIRouter(prefix="/api", tags=["diagnosis"])


@router.post("/diagnose", response_model=DiagnosisResult)
async def diagnose_file(
    file: UploadFile = File(..., description="진단할 CSV 또는 Excel 파일"),
    weight_completeness: float = Form(
        0.30, ge=0.0, le=1.0, description="완전성 가중치"),
    weight_validity:     float = Form(
        0.25, ge=0.0, le=1.0, description="유효성 가중치"),
    weight_consistency:  float = Form(
        0.20, ge=0.0, le=1.0, description="일관성 가중치"),
    weight_accuracy:     float = Form(
        0.15, ge=0.0, le=1.0, description="이상치 가중치"),
    weight_uniqueness:   float = Form(
        0.10, ge=0.0, le=1.0, description="유일성 가중치"),
    db: Session = Depends(get_db),
):
    """
    CSV 또는 Excel 파일을 받아 5대 지표 데이터 품질을 진단하고 결과를 DB에 저장합니다.

    - **file**: 업로드 CSV/Excel
    - **weight_***: 5대 지표 가중치 (자동 정규화, 기본 30/25/20/15/10)
    """
    filename = file.filename or ""
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {supported}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="파일이 비어 있습니다.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 200MB를 초과합니다. ({len(content) / 1024 / 1024:.1f}MB)",
        )

    try:
        df = load_tabular_file_from_bytes(filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if df.empty:
        raise HTTPException(status_code=400, detail="파일에 진단할 데이터가 없습니다.")

    weights = {
        "completeness": weight_completeness,
        "validity":     weight_validity,
        "consistency":  weight_consistency,
        "accuracy":     weight_accuracy,
        "uniqueness":   weight_uniqueness,
    }

    try:
        result = run_full_diagnosis(db, file.filename, df, weights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"진단 중 오류 발생: {e}")

    return result


@router.get("/history", response_model=List[DiagnosisHistoryOut])
def get_history(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """진단 이력 목록 조회 (최신순)"""
    return crud.list_diagnoses(db, skip=skip, limit=limit)


@router.get("/history/{diagnosis_id}", response_model=DiagnosisHistoryOut)
def get_history_detail(diagnosis_id: int, db: Session = Depends(get_db)):
    """진단 이력 단건 조회"""
    record = crud.get_diagnosis_by_id(db, diagnosis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="해당 ID의 진단 이력이 없습니다.")
    return record


@router.delete("/history/{diagnosis_id}")
def delete_history(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_key),
):
    """진단 이력 삭제"""
    success = crud.delete_diagnosis(db, diagnosis_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 ID의 진단 이력이 없습니다.")
    return {"deleted": True, "id": diagnosis_id}


@router.get("/health")
def health_check():
    """헬스 체크"""
    return {"status": "ok"}
