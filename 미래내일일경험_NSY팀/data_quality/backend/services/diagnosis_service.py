"""
진단 오케스트레이션 서비스
- 업로드된 CSV/Excel → 5대 지표 진단 → 종합 점수/등급 산출 → DB 저장 → 응답 구성
"""
import io
from pathlib import Path
import pandas as pd
from typing import Dict, Any
from sqlalchemy.orm import Session

from backend.services.quality_checker import (
    get_basic_info, run_all_checks,
)
from backend.services.quality_score import (
    calculate_total_score, get_quality_grade,
    normalize_weights, calculate_column_quality_scores,
    DEFAULT_WEIGHTS,
)
from backend.services.summary_generator import generate_summary
from backend.db import crud


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def load_csv_from_bytes(content: bytes) -> pd.DataFrame:
    """업로드된 바이트 → DataFrame. 한글/UTF-8 인코딩 자동 감지."""
    encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=enc)
        except Exception as e:
            last_error = e
            continue
    raise ValueError(f"CSV 파싱 실패: {last_error}")


def load_excel_from_bytes(content: bytes, filename: str = "") -> pd.DataFrame:
    """업로드된 Excel 바이트를 첫 번째 시트 기준 DataFrame으로 변환합니다."""
    suffix = Path(filename).suffix.lower()
    engine = "openpyxl" if suffix in {".xlsx", ".xlsm"} else None
    try:
        return pd.read_excel(io.BytesIO(content), sheet_name=0, engine=engine)
    except ImportError as e:
        raise ValueError(
            "Excel 파일을 읽으려면 openpyxl 또는 xlrd 패키지가 필요합니다. "
            "requirements.txt 설치를 다시 확인해 주세요."
        ) from e
    except Exception as e:
        raise ValueError(f"Excel 파싱 실패: {e}") from e


def load_tabular_file_from_bytes(filename: str, content: bytes) -> pd.DataFrame:
    """확장자에 따라 CSV 또는 Excel 파일을 DataFrame으로 변환합니다."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return load_csv_from_bytes(content)
    if suffix in EXCEL_EXTENSIONS:
        return load_excel_from_bytes(content, filename)
    supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    raise ValueError(f"지원하지 않는 파일 형식입니다. 지원 형식: {supported}")


def run_full_diagnosis(
    db: Session,
    filename: str,
    df: pd.DataFrame,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    품질 진단 파이프라인 실행
      1. 기본 정보 추출
      2. 5대 지표 진단 (완전성·유효성·일관성·이상치·유일성)
      3. 종합 점수 + 등급 산출
      4. 컬럼별 점수
      5. AI 요약 생성
      6. DB 저장
      7. 응답 dict 구성
    """
    # ① 기본 정보
    basic_info = get_basic_info(df)

    # ② 5대 지표 진단
    diagnosis = run_all_checks(df)

    # ③ 종합 점수 산출
    norm_weights = normalize_weights(weights)
    dimension_scores = {
        "completeness": diagnosis["completeness"]["score"],
        "validity":     diagnosis["validity"]["score"],
        "consistency":  diagnosis["consistency"]["score"],
        "accuracy":     diagnosis["accuracy"]["score"],
        "uniqueness":   diagnosis["uniqueness"]["score"],
    }
    total_score = calculate_total_score(dimension_scores, norm_weights)
    grade = get_quality_grade(total_score)

    # ④ 컬럼별 점수
    column_scores = calculate_column_quality_scores(
        df, diagnosis, norm_weights)

    # ⑤ AI 요약
    summary_text = generate_summary(total_score, grade, diagnosis)

    # ⑥ DB 저장 (5개 지표 점수 모두 영구 저장)
    history = crud.create_diagnosis(db, {
        "filename": filename,
        # 기본 메트릭
        "total_rows": basic_info["rows"],
        "missing_count": diagnosis["completeness"]["total_missing"],
        "duplicate_count": diagnosis["uniqueness"]["count"],
        "outlier_count": diagnosis["accuracy"]["total_row_count"],
        # 5대 지표 점수
        "completeness_score": dimension_scores["completeness"],
        "validity_score":     dimension_scores["validity"],
        "consistency_score":  dimension_scores["consistency"],
        "accuracy_score":     dimension_scores["accuracy"],
        "uniqueness_score":   dimension_scores["uniqueness"],
        # 종합
        "quality_score": total_score,
        "grade": grade,
    })

    # ⑦ 응답 구성
    return {
        "history": history,
        "detail": {
            "basic_info": basic_info,
            "diagnosis":  diagnosis,
            "dimension_scores": dimension_scores,
            "weights_used": norm_weights,
            "default_weights": DEFAULT_WEIGHTS,
        },
        "summary_text": summary_text,
        "column_scores": column_scores,
    }
