"""
CRUD 작업 분리 모듈
- 모든 DB 접근은 이 파일을 통해 수행 (서비스 레이어와 DB 분리)
"""
from typing import List
from sqlalchemy.orm import Session

from backend.db.models import DiagnosisHistory


def create_diagnosis(db: Session, data: dict) -> DiagnosisHistory:
    """
    진단 이력을 DB에 저장합니다.
    """
    record = DiagnosisHistory(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_diagnosis_by_id(db: Session, diagnosis_id: int) -> DiagnosisHistory | None:
    """
    ID로 진단 이력 단건 조회
    """
    return db.query(DiagnosisHistory).filter(DiagnosisHistory.id == diagnosis_id).first()


def list_diagnoses(db: Session, skip: int = 0, limit: int = 50) -> List[DiagnosisHistory]:
    """
    진단 이력 목록 조회 (최신순)
    """
    return (
        db.query(DiagnosisHistory)
        .order_by(DiagnosisHistory.checked_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_diagnosis(db: Session, diagnosis_id: int) -> bool:
    """
    진단 이력 삭제
    """
    record = get_diagnosis_by_id(db, diagnosis_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
