"""
Pydantic 스키마 (요청/응답 직렬화)
"""
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field


class DiagnosisHistoryOut(BaseModel):
    """DB 저장된 진단 이력 응답 모델 (5대 지표 포함)"""
    id: int
    filename: str
    checked_at: datetime
    total_rows: int
    missing_count: int
    duplicate_count: int
    outlier_count: int

    # 5대 지표 점수
    completeness_score: float
    validity_score: float
    consistency_score: float
    accuracy_score: float
    uniqueness_score: float

    # 종합
    quality_score: float
    grade: str

    class Config:
        from_attributes = True


class DiagnosisResult(BaseModel):
    """POST /api/diagnose 응답"""
    history: DiagnosisHistoryOut
    detail: Dict[str, Any]
    summary_text: str
    column_scores: Dict[str, float]
