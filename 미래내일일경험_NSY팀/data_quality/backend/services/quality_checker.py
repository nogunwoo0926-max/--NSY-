"""
5대 데이터 품질 지표 진단 모듈
플로우차트 STEP 2~3 구현:
  1) 완전성 (Completeness)  : Null/결측 검사
  2) 유효성 (Validity)       : 타입/범위 검증
  3) 일관성 (Consistency)    : 형식/단위 통일
  4) 이상치 (Accuracy)       : IQR + Z-Score + Isolation Forest 다수결
  5) 유일성 (Uniqueness)     : 중복/키 검사

모든 함수는 pandas DataFrame → dict 형태의 순수 함수 (DB/HTTP 의존 없음).
"""
import re
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.ensemble import IsolationForest

ISSUE_LOCATION_LIMIT = 500


def _to_display_value(value: Any) -> str:
    """Convert DataFrame values to JSON-friendly preview text."""
    if pd.isna(value):
        return ""
    return str(value)


def _row_position(df: pd.DataFrame, row_index: Any) -> int:
    """Return a 1-based data row position for a DataFrame index label."""
    loc = df.index.get_loc(row_index)
    if isinstance(loc, slice):
        return int(loc.start) + 1
    if isinstance(loc, np.ndarray):
        return int(np.flatnonzero(loc)[0]) + 1
    return int(loc) + 1


def _make_location(
    df: pd.DataFrame,
    row_index: Any,
    column: str | None,
    issue_type: str,
    message: str,
    value: Any = None,
) -> Dict[str, Any]:
    data_row = _row_position(df, row_index)
    if column is not None and value is None:
        value = df.at[row_index, column]
    return {
        "type": issue_type,
        "row": data_row,
        "excel_row": data_row + 1,
        "index": _to_display_value(row_index),
        "column": column or "-",
        "value": _to_display_value(value),
        "message": message,
    }


def _append_cell_locations(
    locations: List[Dict[str, Any]],
    df: pd.DataFrame,
    row_indices: List[Any],
    column: str,
    issue_type: str,
    message: str,
    values: pd.Series | None = None,
) -> None:
    remaining = ISSUE_LOCATION_LIMIT - len(locations)
    if remaining <= 0:
        return
    for row_index in row_indices[:remaining]:
        value = values.loc[row_index] if values is not None else None
        locations.append(_make_location(df, row_index, column, issue_type, message, value))


def _append_row_locations(
    locations: List[Dict[str, Any]],
    df: pd.DataFrame,
    row_indices: List[Any],
    issue_type: str,
    message: str,
) -> None:
    remaining = ISSUE_LOCATION_LIMIT - len(locations)
    if remaining <= 0:
        return
    for row_index in row_indices[:remaining]:
        locations.append(_make_location(df, row_index, None, issue_type, message, "-"))


def clamp_score(score: float) -> float:
    """점수를 0~100 범위로 강제 고정 (음수/100초과 방지)"""
    return round(max(0.0, min(100.0, score)), 2)


def clamp_ratio(ratio: float) -> float:
    """비율을 0~1 범위로 강제 고정 (중복 카운트로 인한 비율 1 초과 방지)"""
    return max(0.0, min(1.0, ratio))


def _is_string_col(series: pd.Series) -> bool:
    """object/string dtype이면서 수치형이 아닌 컬럼 여부 판단."""
    return (
        series.dtype == "object" or pd.api.types.is_string_dtype(series)
    ) and not pd.api.types.is_numeric_dtype(series)


def _safe_to_datetime(series: pd.Series) -> pd.Series:
    """format='mixed' 미지원 환경을 대비한 pd.to_datetime 래퍼 (1회 호출)."""
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return pd.to_datetime(series, errors="coerce")


# ====================================================================
# 유효성 - 컬럼명 패턴 기반 허용 범위 규칙
# 사용자 입력이나 데이터셋별 하드코딩 없이, 컬럼명에 포함된 키워드로
# 상식적인 허용 범위를 자동 추론한다. 매칭되는 패턴이 없는 컬럼은
# 범위 체크를 생략한다 (모르는 컬럼을 임의로 단정하지 않기 위함).
# min/max가 None이면 그 방향은 제한하지 않음을 의미한다.
# ====================================================================
RANGE_RULES: List[Dict[str, Any]] = [
    {"keywords": ["위도", "lat", "latitude"],
        "min": -90, "max": 90, "label": "위도"},
    {"keywords": ["경도", "lng", "lon", "longitude"],
        "min": -180, "max": 180, "label": "경도"},
    {"keywords": ["비율", "퍼센트", "percent", "rate", "ratio", "률"],
        "min": 0, "max": 100, "label": "비율(%)"},
    {"keywords": ["나이", "연령", "age"], "min": 0, "max": 150, "label": "나이"},
    {"keywords": ["연도", "년도", "year"],
        "min": 1900, "max": 2100, "label": "연도"},
    {"keywords": ["가격", "금액", "price", "cost", "amount", "비용"],
        "min": 0, "max": None, "label": "금액(음수 불가)"},
    {"keywords": ["면적", "넓이", "area"], "min": 0,
        "max": None, "label": "면적(음수 불가)"},
    {"keywords": ["개수", "수량", "count", "건수", "횟수"],
        "min": 0, "max": None, "label": "개수(음수 불가)"},
    {"keywords": ["거리", "distance"], "min": 0,
        "max": None, "label": "거리(음수 불가)"},
]


def _match_range_rule(col_name: str) -> Dict[str, Any] | None:
    """컬럼명에 포함된 키워드로 적용할 범위 규칙을 찾는다. 매칭 없으면 None."""
    name_lower = str(col_name).lower()
    for rule in RANGE_RULES:
        for kw in rule["keywords"]:
            if kw.lower() in name_lower:
                return rule
    return None


def _count_out_of_range(values: pd.Series, rule: Dict[str, Any]) -> int:
    """주어진 값들 중 rule의 허용 범위를 벗어난 개수를 센다 (NaN은 미리 제외하고 전달해야 함)."""
    if len(values) == 0:
        return 0
    mask = pd.Series(False, index=values.index)
    if rule["min"] is not None:
        mask |= values < rule["min"]
    if rule["max"] is not None:
        mask |= values > rule["max"]
    return int(mask.sum())


# ====================================================================
# 기본 정보
# ====================================================================
def get_basic_info(df: pd.DataFrame) -> Dict[str, Any]:
    """데이터프레임 기본 메타 정보"""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(
        include=["object", "category"]).columns.tolist()

    return {
        "rows": len(df),
        "cols": len(df.columns),
        "numeric_cols": len(numeric_cols),
        "categorical_cols": len(categorical_cols),
        "numeric_col_names": numeric_cols,
        "categorical_col_names": categorical_cols,
    }


# ====================================================================
# 1) 완전성 (Completeness) - Null/결측 검사
# ====================================================================
_MISSING_STRINGS = { 
    "",
    "-",
    "—",
    "n/a",
    "na",
    "null",
    "none",
    "nan",
    "?",
    "unknown",
}


def _build_missing_mask(df: pd.DataFrame) -> pd.DataFrame:
    """NaN 외 공백·결측 대체 문자열까지 포함한 결측 마스크."""
    basic = df.isna()
    string_missing = df.astype(str).apply(
        lambda col: col.str.strip().str.lower().isin(_MISSING_STRINGS)
    )
    return basic | string_missing


def check_completeness(df: pd.DataFrame) -> Dict[str, Any]:
    """
    완전성: 결측치가 적을수록 좋음
    점수 = (1 - 결측셀/전체셀) × 100
    NaN 외 공백·"-"·"N/A"·"NULL"·"None" 등 결측 대체 문자열도 포함.
    """
    total_cells = df.size if df.size > 0 else 1
    missing_mask = _build_missing_mask(df)
    missing_per_col = missing_mask.sum()
    total_missing = int(missing_mask.sum().sum())
    overall_ratio = clamp_ratio(total_missing / total_cells)
    empty_record_count = int(missing_mask.all(axis=1).sum())
    locations: List[Dict[str, Any]] = []

    row_positions, col_positions = np.where(missing_mask.values)
    for row_pos, col_pos in zip(row_positions[:ISSUE_LOCATION_LIMIT], col_positions[:ISSUE_LOCATION_LIMIT]):
        row_index = df.index[row_pos]
        col = df.columns[col_pos]
        locations.append(_make_location(df, row_index, col, "missing", "Missing value"))

    per_column_ratio = (missing_per_col / len(df)
                        ).to_dict() if len(df) > 0 else {}

    return {
        "score": clamp_score((1 - overall_ratio) * 100),
        "overall_ratio": float(overall_ratio),
        "total_missing": total_missing,
        "empty_record_count": empty_record_count,
        "per_column": per_column_ratio,
        "per_column_count": {k: int(v) for k, v in missing_per_col.to_dict().items()},
        "locations": locations,
        "location_count": total_missing,
        "location_limit": ISSUE_LOCATION_LIMIT,
    }


# ====================================================================
# 2) 유효성 (Validity) - 타입/범위 검증
# ====================================================================
def check_validity(df: pd.DataFrame) -> Dict[str, Any]:
    """
    유효성: 데이터가 올바른 타입과 범위 내에 있는가
    - object 컬럼이지만 숫자/날짜로 변환 가능한 셀 → 타입 불일치 카운트
    - 수치형 컬럼에서 inf, -inf → 무효 값
    - 컬럼명 패턴(위도/비율/나이/연도/금액 등)에 매칭되면 해당 상식적 범위를
      벗어난 값을 무효로 카운트 (RANGE_RULES, 매칭 안 되면 생략)
    점수 = (1 - 무효셀/전체셀) × 100
    """
    invalid_count = 0
    invalid_per_col: Dict[str, int] = {}
    issues: List[Dict[str, str]] = []
    locations: List[Dict[str, Any]] = []

    THRESHOLD = 0.85  # 85% 이상이 숫자/날짜면 해당 타입으로 간주 (지번 등 혼합 식별자 오판 방지)

    for col in df.columns:
        col_invalid = 0

        if _is_string_col(df[col]):
            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                invalid_per_col[col] = 0
                continue

            # 숫자형으로 변환 가능한 비율 ("142,000" 같은 천 단위 구분자 제거 후 변환)
            numeric_converted = pd.to_numeric(
                series.str.replace(",", "", regex=False), errors="coerce"
            )
            numeric_ratio = numeric_converted.notna().sum() / len(series)

            # 날짜형 변환 가능한 비율 (소규모 샘플로 빠르게 체크, 1회 호출)
            sample_size = min(100, len(series))
            sample = series.head(sample_size)
            date_converted_sample = _safe_to_datetime(sample)
            date_ratio = date_converted_sample.notna().sum() / sample_size

            # 숫자 vs 날짜 중 비율 높은 쪽으로 판정
            if numeric_ratio >= THRESHOLD and numeric_ratio >= date_ratio:
                numeric_invalid_mask = numeric_converted.isna()
                col_invalid = int(numeric_invalid_mask.sum())
                if col_invalid > 0:
                    issues.append({
                        "column": col,
                        "current_dtype": "object",
                        "suggested_dtype": "numeric",
                        "convertible_ratio": f"{numeric_ratio*100:.1f}%",
                        "issue": f"숫자형이어야 할 컬럼에 비숫자 값 {col_invalid}개 존재",
                    })
                    _append_cell_locations(
                        locations,
                        df,
                        numeric_converted.index[numeric_invalid_mask].tolist(),
                        col,
                        "invalid_numeric",
                        "Expected numeric value",
                        series,
                    )

                # 범위 검증: 숫자 변환에 성공한 값들만 대상 (변환 실패값은 이미 위에서 카운트됨)
                range_rule = _match_range_rule(col)
                if range_rule is not None:
                    converted_valid = numeric_converted.dropna()
                    range_mask = pd.Series(False, index=converted_valid.index)
                    if range_rule["min"] is not None:
                        range_mask |= converted_valid < range_rule["min"]
                    if range_rule["max"] is not None:
                        range_mask |= converted_valid > range_rule["max"]
                    range_invalid = int(range_mask.sum())
                    if range_invalid > 0:
                        col_invalid += range_invalid
                        rng_label = f"{range_rule['min'] if range_rule['min'] is not None else '-'}~{range_rule['max'] if range_rule['max'] is not None else '-'}"
                        issues.append({
                            "column": col,
                            "current_dtype": "object",
                            "suggested_dtype": "-",
                            "convertible_ratio": "-",
                            "issue": f"허용 범위({range_rule['label']}: {rng_label}) 밖의 값 {range_invalid}개 존재",
                        })
                        _append_cell_locations(
                            locations,
                            df,
                            converted_valid.index[range_mask].tolist(),
                            col,
                            "invalid_range",
                            f"Out of allowed range ({rng_label})",
                            series,
                        )
            elif date_ratio >= THRESHOLD:
                # 100행 이하면 샘플 결과 재사용, 초과면 전체 1회 파싱
                full_date = (
                    date_converted_sample
                    if len(series) <= sample_size
                    else _safe_to_datetime(series)
                )
                date_invalid_mask = full_date.isna()
                col_invalid = int(date_invalid_mask.sum())
                if col_invalid > 0:
                    issues.append({
                        "column": col,
                        "current_dtype": "object",
                        "suggested_dtype": "datetime",
                        "convertible_ratio": f"{date_ratio*100:.1f}%",
                        "issue": f"날짜형이어야 할 컬럼에 비날짜 값 {col_invalid}개 존재",
                    })
                    _append_cell_locations(
                        locations,
                        df,
                        full_date.index[date_invalid_mask].tolist(),
                        col,
                        "invalid_datetime",
                        "Expected date/datetime value",
                        series,
                    )

        elif pd.api.types.is_numeric_dtype(df[col]):
            # 수치형: inf 검출
            inf_mask = np.isinf(df[col].fillna(0))
            inf_count = int(inf_mask.sum())
            if inf_count > 0:
                col_invalid = inf_count
                issues.append({
                    "column": col,
                    "current_dtype": str(df[col].dtype),
                    "suggested_dtype": "-",
                    "convertible_ratio": "-",
                    "issue": f"무한대(inf) 값 {inf_count}개 포함",
                })
                _append_cell_locations(
                    locations,
                    df,
                    df.index[inf_mask].tolist(),
                    col,
                    "invalid_infinite",
                    "Infinite numeric value",
                )

            # 범위 검증: 컬럼명 패턴에 매칭되는 경우만 (inf/NaN은 제외하고 검사)
            range_rule = _match_range_rule(col)
            if range_rule is not None:
                finite_values = df[col].dropna()
                finite_values = finite_values[~np.isinf(finite_values)]
                range_mask = pd.Series(False, index=finite_values.index)
                if range_rule["min"] is not None:
                    range_mask |= finite_values < range_rule["min"]
                if range_rule["max"] is not None:
                    range_mask |= finite_values > range_rule["max"]
                range_invalid = int(range_mask.sum())
                if range_invalid > 0:
                    col_invalid += range_invalid
                    rng_label = f"{range_rule['min'] if range_rule['min'] is not None else '-'}~{range_rule['max'] if range_rule['max'] is not None else '-'}"
                    issues.append({
                        "column": col,
                        "current_dtype": str(df[col].dtype),
                        "suggested_dtype": "-",
                        "convertible_ratio": "-",
                        "issue": f"허용 범위({range_rule['label']}: {rng_label}) 밖의 값 {range_invalid}개 존재",
                    })
                    _append_cell_locations(
                        locations,
                        df,
                        finite_values.index[range_mask].tolist(),
                        col,
                        "invalid_range",
                        f"Out of allowed range ({rng_label})",
                    )

        invalid_per_col[col] = col_invalid
        invalid_count += col_invalid

    total_cells = df.size if df.size > 0 else 1
    invalid_ratio = clamp_ratio(invalid_count / total_cells)

    return {
        "score": clamp_score((1 - invalid_ratio) * 100),
        "invalid_count": invalid_count,
        "invalid_ratio": float(invalid_ratio),
        "per_column": invalid_per_col,
        "issues": issues,
        "locations": locations,
        "location_count": invalid_count,
        "location_limit": ISSUE_LOCATION_LIMIT,
    }


# ====================================================================
# 3) 일관성 (Consistency) - 형식/단위 통일
# ====================================================================
def check_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """
    일관성: 문자열 컬럼에서 형식이 통일되어 있는가
    검사 항목:
      - 앞뒤 공백 있는 셀
      - 동일 값이지만 대소문자 다른 셀 (예: 'KOREA' vs 'korea')
      - 혼합된 표기 (예: '2024-01-01' vs '2024/01/01')
    한 셀이 여러 검사에 동시 해당해도 1회만 카운트 (OR 마스크 방식)
    점수 = (1 - 비일관셀/전체셀) × 100
    """
    inconsistent_count = 0
    per_column: Dict[str, int] = {}
    locations: List[Dict[str, Any]] = []

    for col in df.columns:
        if not _is_string_col(df[col]):
            per_column[col] = 0
            continue

        series = df[col].dropna().astype(str)
        if len(series) == 0:
            per_column[col] = 0
            continue

        # 셀 단위 비일관 여부를 누적하는 boolean mask (중복 카운트 방지의 핵심)
        error_mask = pd.Series(False, index=series.index)

        # ① 앞뒤 공백 검사 - 셀 단위
        whitespace_mask = series != series.str.strip()
        error_mask |= whitespace_mask

        # ② 대소문자 변형 검사 - 정규화 후 동일한 값을 가진 셀들 중
        #    가장 많이 등장하는 표기와 다른 셀만 True
        stripped = series.str.strip()
        normalized = stripped.str.lower()

        # 그룹별 대표 표기(최빈값)를 pandas 내부에서 한 번에 계산
        top_forms = stripped.groupby(normalized).agg(
            lambda g: g.value_counts().index[0]
        )
        # 각 셀에 자기 그룹의 대표 표기 매핑
        mapped_top = normalized.map(top_forms)
        # 그룹 크기 > 1이면서 대표 표기와 다른 셀만 비일관으로 마킹
        group_sizes = normalized.map(normalized.value_counts())
        error_mask |= (stripped != mapped_top) & (group_sizes > 1)

        # ③ 날짜/숫자 형식 혼용 검사 (구분자 통일성)
        #    소수 형식에 해당하는 셀만 비일관으로 마킹
        date_dash_mask = series.str.match(r"^\d{4}-\d{2}-\d{2}")
        date_slash_mask = series.str.match(r"^\d{4}/\d{2}/\d{2}")
        date_dash_count = int(date_dash_mask.sum())
        date_slash_count = int(date_slash_mask.sum())
        if date_dash_count > 0 and date_slash_count > 0:
            # 둘 다 존재하면 더 적은 쪽(소수 형식)의 실제 셀들을 비일관으로 마킹
            minority_date_mask = date_slash_mask if date_slash_count <= date_dash_count else date_dash_mask
            error_mask |= minority_date_mask

        col_inconsistent = int(error_mask.sum())
        per_column[col] = col_inconsistent
        inconsistent_count += col_inconsistent
        if col_inconsistent > 0:
            _append_cell_locations(
                locations,
                df,
                error_mask.index[error_mask].tolist(),
                col,
                "inconsistent",
                "Inconsistent format or spacing",
                series,
            )

    total_cells = df.size if df.size > 0 else 1
    inconsistent_ratio = clamp_ratio(inconsistent_count / total_cells)

    return {
        "score": clamp_score((1 - inconsistent_ratio) * 100),
        "inconsistent_count": inconsistent_count,
        "inconsistent_ratio": float(inconsistent_ratio),
        "per_column": per_column,
        "locations": locations,
        "location_count": inconsistent_count,
        "location_limit": ISSUE_LOCATION_LIMIT,
    }


# ====================================================================
# 4) 이상치 (Accuracy) - IQR + Z-Score + Isolation Forest 다수결
# ====================================================================
def _detect_outliers_iqr(series: pd.Series) -> np.ndarray:
    """IQR 기반 이상치 탐지 → boolean mask 반환"""
    if len(series) < 4:
        return np.zeros(len(series), dtype=bool)
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return np.zeros(len(series), dtype=bool)
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return ((series < lower) | (series > upper)).values


def _detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> np.ndarray:
    """Z-Score 기반 이상치 탐지 → |Z| >= 3"""
    if len(series) < 2:
        return np.zeros(len(series), dtype=bool)
    std = series.std()
    if std == 0 or pd.isna(std):
        return np.zeros(len(series), dtype=bool)
    z = np.abs((series - series.mean()) / std)
    return (z >= threshold).values


def _detect_outliers_isoforest(series: pd.Series, contamination: float = 0.05) -> np.ndarray:
    """
    Isolation Forest 기반 이상치 탐지
    대용량 데이터 대응: max_samples로 학습에 쓰는 표본 수를 제한해 속도 확보
    (전체 데이터에 대한 예측은 그대로 수행)
    """
    n = len(series)
    if n < 10:
        return np.zeros(n, dtype=bool)
    try:
        # 학습 표본 수 제한: 데이터가 커도 최대 25,600개 표본만으로 트리 구성
        max_samples = min(n, 2048) if n <= 10000 else min(n, 25600)
        model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=50,
            max_samples=max_samples,
            n_jobs=-1,  # 멀티코어 병렬 처리
        )
        preds = model.fit_predict(series.values.reshape(-1, 1))
        return (preds == -1)
    except Exception:
        return np.zeros(len(series), dtype=bool)


def check_outliers_ensemble(df: pd.DataFrame) -> Dict[str, Any]:
    """
    이상치 탐지 - 3개 알고리즘 다수결
    플로우차트: "2개 이상 검출 시 이상치"

    각 수치형 컬럼에 대해:
      - IQR
      - Z-Score
      - Isolation Forest
    위 3가지 중 2개 이상에서 이상치로 판정한 셀만 최종 이상치로 카운트.

    점수 산정은 "행" 기준 (명세서 기준과 일치):
      - 한 행에 이상치 셀이 1개 이상 있으면 해당 행 전체를 이상치 행으로 판정
      - 점수 = (1 - 이상치 행 수 / 전체 행 수) × 100
    """
    numeric_df = df.select_dtypes(include="number")
    # 키/식별자 컬럼은 이상치 탐지 대상에서 제외 (NO, 본번, 부번 등은 측정값이 아님)
    key_cols = set(_infer_key_columns(df))
    numeric_df = numeric_df[[c for c in numeric_df.columns if c not in key_cols]]

    per_column: Dict[str, int] = {}
    per_method_count = {"iqr": 0, "zscore": 0, "isoforest": 0, "ensemble": 0}
    total_outlier_cells = 0
    outlier_row_indices: set = set()  # 이상치가 발생한 행 인덱스 집합 (행 기준 점수 산출용)
    locations: List[Dict[str, Any]] = []

    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        if len(series) < 4:
            per_column[col] = 0
            continue

        mask_iqr = _detect_outliers_iqr(series)
        mask_z = _detect_outliers_zscore(series)
        mask_iso = _detect_outliers_isoforest(series)

        # 셀별로 몇 개 알고리즘이 이상치라고 판정했는지 합산
        vote_sum = mask_iqr.astype(
            int) + mask_z.astype(int) + mask_iso.astype(int)
        ensemble_mask = vote_sum >= 2  # 다수결: 2표 이상

        per_method_count["iqr"] += int(mask_iqr.sum())
        per_method_count["zscore"] += int(mask_z.sum())
        per_method_count["isoforest"] += int(mask_iso.sum())
        per_method_count["ensemble"] += int(ensemble_mask.sum())

        per_column[col] = int(ensemble_mask.sum())
        total_outlier_cells += int(ensemble_mask.sum())
        if int(ensemble_mask.sum()) > 0:
            _append_cell_locations(
                locations,
                df,
                series.index[ensemble_mask].tolist(),
                col,
                "outlier",
                "Outlier detected by ensemble vote",
                series,
            )

        # 이상치로 판정된 셀의 원본 행 인덱스를 누적 (여러 컬럼에서 겹쳐도 set이라 중복 제거됨)
        outlier_row_indices.update(series.index[ensemble_mask].tolist())

    total_numeric_cells = numeric_df.size if numeric_df.size > 0 else 1
    cell_based_ratio = clamp_ratio(total_outlier_cells / total_numeric_cells)

    # 행 기준 비율 (명세서 기준 점수 산출에 사용)
    total_rows = len(df) if len(df) > 0 else 1
    outlier_row_count = len(outlier_row_indices)
    row_based_ratio = clamp_ratio(outlier_row_count / total_rows)

    return {
        "score": clamp_score((1 - row_based_ratio) * 100),
        "total_count": total_outlier_cells,
        "total_row_count": outlier_row_count,
        "overall_ratio": float(row_based_ratio),
        "cell_based_ratio": float(cell_based_ratio),
        "per_column": per_column,
        "per_method_count": per_method_count,
        "method": "ensemble (IQR + Z-Score + IsolationForest, majority vote ≥ 2, row-based scoring)",
        "row_indices": sorted([_to_display_value(i) for i in outlier_row_indices]),
        "locations": locations,
        "location_count": total_outlier_cells,
        "location_limit": ISSUE_LOCATION_LIMIT,
    }


# ====================================================================
# 5) 유일성 (Uniqueness) - 중복/키 검사
# ====================================================================
_KEY_KEYWORDS = ["id", "no", "번호", "관리번호", "사고번호", "코드", "code", "key"]


def _infer_key_columns(df: pd.DataFrame) -> List[str]:
    """컬럼명에 키 관련 키워드가 포함된 컬럼을 고유 키 후보로 반환."""
    result = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(k in col_lower for k in _KEY_KEYWORDS):
            result.append(col)
    return result


def check_uniqueness(df: pd.DataFrame) -> Dict[str, Any]:
    """
    유일성: 중복 행 + 키 컬럼 중복 검사
    점수 = (1 - 문제행/전체행) × 100
    문제행 = 전체 행 중복 OR 키 컬럼 중복이 발생한 행
    """
    if len(df) == 0:
        return {
            "score": 100.0,
            "count": 0,
            "ratio": 0.0,
            "row_duplicate_count": 0,
            "key_duplicate_count": 0,
            "key_columns": [],
            "locations": [],
            "location_count": 0,
            "location_limit": ISSUE_LOCATION_LIMIT,
        }

    row_duplicate_mask = df.duplicated()
    row_duplicate_count = int(row_duplicate_mask.sum())

    key_columns = _infer_key_columns(df)
    key_duplicate_mask = pd.Series(False, index=df.index)

    for col in key_columns:
        col_missing = _build_missing_mask(df[[col]])[col]
        key_dup_mask = (~col_missing) & df[col].duplicated()
        key_duplicate_mask |= key_dup_mask

    key_duplicate_count = int(key_duplicate_mask.sum())

    duplicate_mask = row_duplicate_mask | key_duplicate_mask
    total_duplicate_count = int(duplicate_mask.sum())
    ratio = clamp_ratio(total_duplicate_count / len(df))
    locations: List[Dict[str, Any]] = []

    _append_row_locations(
        locations,
        df,
        df.index[row_duplicate_mask].tolist(),
        "duplicate_row",
        "Duplicated full row",
    )
    for col in key_columns:
        col_missing = _build_missing_mask(df[[col]])[col]
        key_dup_mask = (~col_missing) & df[col].duplicated()
        _append_cell_locations(
            locations,
            df,
            df.index[key_dup_mask].tolist(),
            col,
            "duplicate_key",
            "Duplicated key value",
        )

    return {
        "score": clamp_score((1 - ratio) * 100),
        "count": total_duplicate_count,
        "ratio": float(ratio),
        "row_duplicate_count": row_duplicate_count,
        "key_duplicate_count": key_duplicate_count,
        "key_columns": key_columns,
        "locations": locations,
        "location_count": total_duplicate_count,
        "location_limit": ISSUE_LOCATION_LIMIT,
    }


# ====================================================================
# 통합 진단 (5개 지표 한 번에)
# ====================================================================
def run_all_checks(df: pd.DataFrame) -> Dict[str, Any]:
    """5대 지표를 한 번에 진단하여 dict로 반환"""
    return {
        "completeness": check_completeness(df),
        "validity":     check_validity(df),
        "consistency":  check_consistency(df),
        "accuracy":     check_outliers_ensemble(df),
        "uniqueness":   check_uniqueness(df),
    }
