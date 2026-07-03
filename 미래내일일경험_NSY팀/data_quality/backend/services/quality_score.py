"""
종합 품질 점수 산출 및 등급 판정 모듈
플로우차트 STEP 4~5 구현

종합점수 = 완전성×0.30 + 유효성×0.25 + 일관성×0.20 + 이상치×0.15 + 유일성×0.10
등급:
  S: 97점 이상   → 즉시 학습 가능
  A: 90 ~ 97점   → Class A 기준
  B: 80 ~ 90점   → 경미한 보완
  C: 70 ~ 80점   → 전처리 필요
  F: 70점 미만   → 학습 부적합
"""
import pandas as pd
from typing import Dict, Any

# 플로우차트 기본 가중치 (Scorecard 가중치)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "completeness": 0.30,
    "validity":     0.25,
    "consistency":  0.20,
    "accuracy":     0.15,
    "uniqueness":   0.10,
}


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """가중치 합이 1이 되도록 정규화. 합이 0이면 기본값 반환."""
    total = sum(weights.values())
    if total <= 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v / total for k, v in weights.items()}


def calculate_total_score(
    dimension_scores: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """
    5개 지표 점수를 가중평균하여 종합 점수 산출.

    Args:
        dimension_scores: {"completeness": 95.2, "validity": 88.1, ...}
        weights:           정규화된 가중치 (diagnosis_service에서 사전 정규화)

    Returns:
        0~100 사이 종합 점수
    """
    score = sum(
        dimension_scores.get(k, 0) * weights.get(k, 0)
        for k in DEFAULT_WEIGHTS.keys()
    )
    return round(max(0.0, min(100.0, score)), 2)


def get_quality_grade(score: float) -> str:
    """
    종합점수 → AI-Ready 등급
      S (97+) / A (90~97) / B (80~90) / C (70~80) / F (<70)
    """
    if score >= 97:
        return "S"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "F"


def get_grade_description(grade: str) -> str:
    """등급 설명"""
    return {
        "S": "즉시 학습 가능 — 매우 우수",
        "A": "Class A 기준 — 우수",
        "B": "경미한 보완 필요",
        "C": "전처리 필요",
        "F": "학습 부적합 — 광범위한 정제 필요",
    }.get(grade, "")


def calculate_column_quality_scores(
    df: pd.DataFrame,
    diagnosis: Dict[str, Any],
    weights: Dict[str, float],
) -> Dict[str, float]:
    """
    컬럼별 품질 점수 (5개 지표 중 컬럼별로 측정 가능한 4개 사용)
    - 완전성: per_column 결측률
    - 유효성: per_column 무효 셀
    - 일관성: per_column 비일관 셀
    - 이상치: per_column 이상치 개수
    - 유일성: 컬럼 단위 측정 불가 → 제외하고 나머지 4개 가중치 재정규화
    """
    n_rows = max(len(df), 1)

    # 유일성을 제외한 4개 지표 가중치 재정규화
    sub_w = {
        "completeness": weights["completeness"],
        "validity":     weights["validity"],
        "consistency":  weights["consistency"],
        "accuracy":     weights["accuracy"],
    }
    sub_total = sum(sub_w.values())
    if sub_total == 0:
        sub_w = {k: 0.25 for k in sub_w}
    else:
        sub_w = {k: v / sub_total for k, v in sub_w.items()}

    completeness = diagnosis["completeness"]["per_column"]
    validity = diagnosis["validity"]["per_column"]
    consistency = diagnosis["consistency"]["per_column"]
    accuracy = diagnosis["accuracy"]["per_column"]

    scores: Dict[str, float] = {}
    for col in df.columns:
        # 각 지표 컬럼 점수 (1 - 비율) * 100
        c_score = (1 - min(1.0, completeness.get(col, 0.0))) * 100
        v_score = (1 - min(1.0, validity.get(col, 0) / n_rows)) * 100
        s_score = (1 - min(1.0, consistency.get(col, 0) / n_rows)) * 100
        a_score = (1 - min(1.0, accuracy.get(col, 0) / n_rows)) * 100

        total = (
            c_score * sub_w["completeness"]
            + v_score * sub_w["validity"]
            + s_score * sub_w["consistency"]
            + a_score * sub_w["accuracy"]
        )
        scores[col] = round(max(0.0, min(100.0, total)), 2)

    return scores
