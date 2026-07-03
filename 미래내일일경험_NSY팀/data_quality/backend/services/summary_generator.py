"""
Claude API 기반 데이터 품질 진단 요약 및 개선 가이드 생성
5대 지표 진단 결과를 Claude에게 전달하여 자연어 분석 및 개선 방향을 생성합니다.
"""
import os
from typing import Dict, Any
from anthropic import Anthropic

from backend.services.quality_score import get_grade_description

# Claude API 클라이언트 초기화 (ANTHROPIC_API_KEY 환경변수에서 자동 로드)
_client = None


def _get_client() -> Anthropic:
    """Claude API 클라이언트 싱글턴 반환"""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 ANTHROPIC_API_KEY를 입력해 주세요."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def _build_prompt(
    total_score: float,
    grade: str,
    diagnosis: Dict[str, Any],
) -> str:
    """Claude에게 전달할 진단 결과 프롬프트 구성"""
    grade_desc = get_grade_description(grade)

    cm = diagnosis["completeness"]
    vd = diagnosis["validity"]
    cs = diagnosis["consistency"]
    ac = diagnosis["accuracy"]
    un = diagnosis["uniqueness"]

    # 컬럼별 결측률 상위 3개
    top_missing = sorted(cm["per_column"].items(),
                         key=lambda x: x[1], reverse=True)
    top_missing = [(c, r) for c, r in top_missing if r > 0][:3]
    top_missing_str = ", ".join(
        [f"{c}({r*100:.1f}%)" for c, r in top_missing]) or "없음"

    # 유효성 이슈 컬럼
    validity_issues = [i["column"] + ": " + i["issue"]
                       for i in vd.get("issues", [])[:3]]
    validity_issues_str = "\n".join(validity_issues) or "없음"

    # 이상치 상위 컬럼
    top_outliers = sorted(ac["per_column"].items(),
                          key=lambda x: x[1], reverse=True)
    top_outliers = [(c, n) for c, n in top_outliers if n > 0][:3]
    top_outliers_str = ", ".join(
        [f"{c}({n}개)" for c, n in top_outliers]) or "없음"

    pm = ac.get("per_method_count", {})
    location_examples = []
    for label, key in [
        ("결측", "completeness"),
        ("유효성", "validity"),
        ("일관성", "consistency"),
        ("이상치", "accuracy"),
        ("중복", "uniqueness"),
    ]:
        for item in diagnosis.get(key, {}).get("locations", [])[:3]:
            location_examples.append(
                f"{label}: Excel {item.get('excel_row')}행, "
                f"{item.get('column')} 컬럼, 값 '{item.get('value')}' - {item.get('message')}"
            )
            if len(location_examples) >= 10:
                break
        if len(location_examples) >= 10:
            break
    location_examples_str = "\n".join(location_examples) or "없음"

    prompt = f"""당신은 데이터 품질 전문가입니다. 아래는 사용자가 업로드한 CSV 데이터셋의 자동 품질 진단 결과입니다. 이를 바탕으로 전문적이고 실용적인 분석 요약과 개선 가이드를 한국어로 작성해 주세요. 단 상대가 비전문가여도 이해할 수 있도록 명확하게 설명하고, 개선 방법은 구체적이고 실행 가능한 조치로 제시해 주세요.

## 진단 결과 데이터

**종합 점수:** {total_score:.1f}점 / 100점
**AI-Ready 등급:** {grade}등급 ({grade_desc})

### 5대 품질 지표 점수
- 완전성 (Completeness): {cm["score"]:.1f}점 — 결측 셀 {cm["total_missing"]:,}개 (결측률 {cm["overall_ratio"]*100:.2f}%)
- 유효성 (Validity): {vd["score"]:.1f}점 — 타입/형식 오류 {vd["invalid_count"]:,}개
- 일관성 (Consistency): {cs["score"]:.1f}점 — 형식 불일치 {cs["inconsistent_count"]:,}개
- 이상치 (Accuracy): {ac["score"]:.1f}점 — 이상치 행 {ac["total_row_count"]:,}건 (IQR: {pm.get("iqr", 0):,} / Z-Score: {pm.get("zscore", 0):,} / IsolationForest: {pm.get("isoforest", 0):,})
- 유일성 (Uniqueness): {un["score"]:.1f}점 — 중복 행 {un["count"]:,}개 ({un["ratio"]*100:.2f}%)

### 세부 문제 현황
**주요 결측 컬럼:** {top_missing_str}
**유효성 오류 상세:**
{validity_issues_str}
**이상치 주요 컬럼:** {top_outliers_str}
**문제 위치 예시:**
{location_examples_str}
**일관성 불일치:** 공백/대소문자/날짜 구분자 혼용 {cs["inconsistent_count"]:,}건

## 작성 지침

다음 구조로 HTML 형식으로 작성해 주세요. 실용적이고 구체적인 내용으로 500~700자 분량으로 작성하세요.

1. **종합 평가** (2~3문장): 등급과 점수를 언급하며 데이터의 전반적인 AI 활용 가능성 평가
2. **주요 문제 분석** (문제가 있는 지표만, 각 1~2문장): 수치를 근거로 구체적인 문제 설명
3. **개선 우선순위 및 방법** (3~4가지): 가장 시급한 것부터 실행 가능한 구체적 조치 제시
4. **개선 후 기대 효과** (1~2문장): 조치 완료 시 예상되는 등급/점수 향상

HTML 태그 사용 규칙:
- 섹션 제목: <b>[제목]</b>
- 강조: <b>텍스트</b>
- 컬럼명/코드: <code>텍스트</code>
- 섹션 구분: <br><br>
- 목록: • 기호 사용 (ul/li 태그 사용 금지)
"""
    return prompt


def generate_summary(
    total_score: float,
    grade: str,
    diagnosis: Dict[str, Any],
) -> str:
    """
    Claude API를 호출하여 데이터 품질 진단 요약 및 개선 가이드 생성

    Args:
        total_score: 종합 품질 점수 (0~100)
        grade: S/A/B/C/F 등급
        diagnosis: {"completeness":{...}, "validity":{...}, ...}

    Returns:
        HTML 형식의 AI 진단 요약 문자열
    """
    try:
        client = _get_client()
        prompt = _build_prompt(total_score, grade, diagnosis)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=(
                "당신은 데이터 품질 관리 전문가입니다. "
                "진단 결과를 분석하여 명확하고 실용적인 개선 가이드를 제공합니다. "
                "항상 한국어로 응답하며, 지정된 HTML 형식을 정확히 따릅니다."
                "비전문가도 이해할 수 있도록 명확하게 작성하고, 개선 방법은 구체적이고 실행 가능한 조치로 제시합니다."
            ),
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        return message.content[0].text

    except ValueError as e:
        # API 키 미설정 시 규칙 기반 폴백
        return _fallback_summary(total_score, grade, diagnosis, error=str(e))
    except Exception as e:
        # API 호출 실패 시 규칙 기반 폴백
        return _fallback_summary(total_score, grade, diagnosis, error=str(e))


def _fallback_summary(
    total_score: float,
    grade: str,
    diagnosis: Dict[str, Any],
    error: str = "",
) -> str:
    """
    Claude API 호출 실패 시 규칙 기반 요약으로 대체
    (API 키 미설정 또는 네트워크 오류 등)
    """
    grade_desc = get_grade_description(grade)
    sentences = []

    if error:
        sentences.append(
            f'<b>[AI 요약 오류]</b> Claude API 연결에 실패하여 기본 요약으로 대체합니다. '
            f'<code>.env</code> 파일의 <code>ANTHROPIC_API_KEY</code>를 확인해 주세요.'
        )

    sentences.append(
        f"현재 데이터셋은 <b>AI-Ready 등급 {grade} (점수 {total_score:.1f}점)</b>으로 평가됩니다. "
        f"{grade_desc}."
    )

    cm = diagnosis["completeness"]
    if cm["overall_ratio"] > 0:
        sentences.append(
            f"<b>[완전성]</b> 결측률 {cm['overall_ratio']*100:.2f}%, "
            f"총 {cm['total_missing']:,}개 결측 셀이 존재합니다."
        )

    vd = diagnosis["validity"]
    if vd["invalid_count"] > 0:
        sentences.append(
            f"<b>[유효성]</b> 타입/형식 오류 {vd['invalid_count']:,}개가 발견되었습니다."
        )

    cs = diagnosis["consistency"]
    if cs["inconsistent_count"] > 0:
        sentences.append(
            f"<b>[일관성]</b> 형식 불일치 {cs['inconsistent_count']:,}건이 감지되었습니다."
        )

    ac = diagnosis["accuracy"]
    if ac["total_row_count"] > 0:
        sentences.append(
            f"<b>[이상치]</b> 앙상블 기반 이상치 행 {ac['total_row_count']:,}건이 탐지되었습니다."
        )

    un = diagnosis["uniqueness"]
    if un["count"] > 0:
        sentences.append(
            f"<b>[유일성]</b> 중복 행 {un['count']:,}건({un['ratio']*100:.2f}%)을 제거하는 것을 권장합니다."
        )

    return "<br><br>".join(sentences)
