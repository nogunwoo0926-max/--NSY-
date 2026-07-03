"""
SQLAlchemy ORM 모델 정의
- DiagnosisHistory: 데이터 품질 진단 이력 (5대 지표 점수 포함)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger

from backend.db.database import Base


class DiagnosisHistory(Base):
    """
    데이터 품질 진단 이력 테이블 (5대 지표 Scorecard 저장)

    저장 항목:
      - 파일명, 검사 일시, 전체 행 수
      - 기본 카운트: 결측 / 중복 / 이상치
      - 5대 지표 점수: completeness / validity / consistency / accuracy / uniqueness
      - 종합 점수 + 등급 (S/A/B/C/F)
    """
    __tablename__ = "diagnosis_history"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="진단 ID")
    filename = Column(String(255), nullable=False, comment="업로드 CSV/Excel 파일명")
    checked_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True,
        comment="진단 수행 시각",
    )

    # 기본 카운트 (요구사항 명시 7개 항목 중 카운트들)
    total_rows = Column(BigInteger, nullable=False, comment="전체 행 수")
    missing_count = Column(BigInteger, nullable=False,
                           default=0, comment="결측치 총 개수")
    duplicate_count = Column(BigInteger, nullable=False,
                             default=0, comment="중복 행 개수")
    outlier_count = Column(BigInteger, nullable=False,
                           default=0, comment="이상치 총 개수 (앙상블)")

    # 5대 지표 점수 (각 0~100)
    completeness_score = Column(
        Float, nullable=False, default=0, comment="완전성 점수")
    validity_score = Column(Float, nullable=False, default=0, comment="유효성 점수")
    consistency_score = Column(
        Float, nullable=False, default=0, comment="일관성 점수")
    accuracy_score = Column(Float, nullable=False,
                            default=0, comment="이상치(정확성) 점수")
    uniqueness_score = Column(Float, nullable=False,
                              default=0, comment="유일성 점수")

    # 종합
    quality_score = Column(Float, nullable=False, comment="종합 품질 점수 (0~100)")
    grade = Column(String(2), nullable=False,
                   comment="AI-Ready 등급 (S/A/B/C/F)")

    def __repr__(self) -> str:
        return (
            f"<DiagnosisHistory id={self.id} file={self.filename} "
            f"score={self.quality_score} grade={self.grade}>"
        )
