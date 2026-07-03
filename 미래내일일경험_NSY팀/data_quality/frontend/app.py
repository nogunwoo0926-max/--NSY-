"""
AI 스마트 데이터 품질 진단 시스템 - Streamlit 클라이언트 (v2: 5대 지표)
- 5개 가중치 슬라이더 (완전성/유효성/일관성/이상치/유일성)
- 5지표 KPI + 레이더 차트
- S/A/B/C/F 등급
- 탭 UI
"""
from visualization.charts import (
    plot_dimension_radar, plot_dimension_bar,
    plot_missing_by_column, plot_problem_ratio_pie,
    plot_column_quality_bar, plot_column_outliers,
    plot_outlier_method_compare, plot_history_trend,
)
from utils.api_client import api_client
import html
import json
import re
import tempfile
from pathlib import Path
import streamlit as st
import pandas as pd
import os
import sys

# frontend 폴더를 import 경로에 추가 (streamlit run frontend/app.py 실행 대응)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ====================================================================
# 페이지 설정
# ====================================================================
st.set_page_config(
    page_title="AI 스마트 데이터 품질 진단 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 테마 초기화 (사이드바 전에 결정해야 CSS에 반영됨) ──────────────
st.session_state.setdefault("_is_dark", True)
_THEME = "dark" if st.session_state["_is_dark"] else "light"


# ====================================================================
# CSS (테마 기반 동적 생성)
# ====================================================================
def _get_css(theme: str) -> str:
    d = (theme == "dark")
    return f"""
<style>
    .stApp {{ background-color: {"#0E1117" if d else "#F1F5F9"}; }}
    [data-testid="stSidebar"] {{ background-color: {"#111827" if d else "#E8EEF4"}; }}

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{ color: {"#F9FAFB" if d else "#1E293B"}; }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {"#D1D5DB" if d else "#374151"};
    }}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] small {{ color: {"#9CA3AF" if d else "#6B7280"} !important; }}

    [data-testid="stFileUploader"] section {{
        background-color: {"#1F2937" if d else "#FFFFFF"};
        border: 1px dashed {"#4B5563" if d else "#CBD5E1"};
        border-radius: 8px;
    }}
    [data-testid="stFileUploader"] section small {{ color: {"#9CA3AF" if d else "#6B7280"}; }}
    [data-testid="stFileUploaderDropzone"] {{ background-color: transparent; }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {{
        background: {"#1F2937" if d else "#F8FAFC"} !important;
        border: 1px solid {"#4B5563" if d else "#CBD5E1"} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] small {{
        color: {"#E5E7EB" if d else "#0F172A"} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] svg {{
        color: {"#E5E7EB" if d else "#334155"} !important;
        fill: {"#E5E7EB" if d else "#334155"} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
        background: {"#374151" if d else "#E0F2FE"} !important;
        color: {"#F9FAFB" if d else "#075985"} !important;
        border: 1px solid {"#4B5563" if d else "#7DD3FC"} !important;
    }}

    [data-testid="stMetricLabel"] {{ color: {"#D1D5DB" if d else "#475569"}; }}
    [data-testid="stMetricValue"] {{
        color: {"#FFFFFF" if d else "#1E293B"}; font-weight: 700;
        font-size: clamp(1.1rem, 2vw, 1.8rem) !important;
        overflow-wrap: break-word;
    }}

    .main-title {{
        font-size: 2.3rem; font-weight: 700;
        background: linear-gradient(90deg, {"#00D4FF" if d else "#0EA5E9"} 0%, #C77DFF 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }}
    .sub-title {{ color: {"#D1D5DB" if d else "#475569"}; font-size: 0.95rem; margin-bottom: 1rem; }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px; background: {"#111827" if d else "#E2E8F0"};
        padding: 8px; border-radius: 10px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {"#1F2937" if d else "#FFFFFF"}; color: {"#D1D5DB" if d else "#374151"};
        border-radius: 8px; padding: 10px 24px; font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, #0EA5E9, #7B2CBF);
        color: #FFFFFF !important;
    }}

    .kpi-card {{
        background: {"linear-gradient(135deg, #1F2937 0%, #111827 100%)" if d else "linear-gradient(135deg, #FFFFFF 0%, #F1F5F9 100%)"};
        border: 1px solid {"#4B5563" if d else "#CBD5E1"};
        padding: 1rem 0.6rem; border-radius: 12px;
        text-align: center; min-height: 140px;
        display: flex; flex-direction: column; justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,{"0.4" if d else "0.08"});
        overflow: hidden;
    }}
    .kpi-label {{
        color: {"#D1D5DB" if d else "#475569"}; font-size: clamp(0.72rem, 1.1vw, 0.88rem); font-weight: 500;
        margin-bottom: 0.5rem;
        white-space: normal; word-break: keep-all; line-height: 1.3;
    }}
    .kpi-value {{
        color: {"#FFFFFF" if d else "#1E293B"}; font-size: clamp(1.1rem, 2.2vw, 1.75rem); font-weight: 700;
        line-height: 1.2; word-break: break-all;
    }}
    .kpi-sub {{ color: {"#9CA3AF" if d else "#6B7280"}; font-size: clamp(0.68rem, 1vw, 0.8rem); margin-top: 0.3rem; }}
    .kpi-value.grade-S {{ color: #A78BFA; }}
    .kpi-value.grade-A {{ color: #34D399; }}
    .kpi-value.grade-B {{ color: #60A5FA; }}
    .kpi-value.grade-C {{ color: #FBBF24; }}
    .kpi-value.grade-F {{ color: #F87171; }}

    .dim-card {{ padding: 0.9rem 0.6rem; border-radius: 10px; text-align: center; min-height: 110px;
                display: flex; flex-direction: column; justify-content: center;
                border: 1px solid {"#4B5563" if d else "#CBD5E1"}; overflow: hidden; }}
    .dim-card .label {{ font-size: clamp(0.72rem, 1.1vw, 0.85rem); color: {"#D1D5DB" if d else "#374151"}; margin-bottom: 0.3rem;
                       white-space: normal; word-break: keep-all; line-height: 1.3; }}
    .dim-card .value {{ font-size: clamp(1.05rem, 2vw, 1.6rem); font-weight: 700; color: {"#FFFFFF" if d else "#1E293B"};
                       word-break: break-all; }}
    .dim-card .weight {{ font-size: clamp(0.65rem, 0.9vw, 0.75rem); color: {"#9CA3AF" if d else "#6B7280"}; margin-top: 0.2rem; }}
    .dim-completeness {{ background: {"linear-gradient(135deg, #064E3B 0%, #1F2937 100%)" if d else "linear-gradient(135deg, #D1FAE5 0%, #F8FAFC 100%)"}; }}
    .dim-validity     {{ background: {"linear-gradient(135deg, #7C2D12 0%, #1F2937 100%)" if d else "linear-gradient(135deg, #FEE2E2 0%, #F8FAFC 100%)"}; }}
    .dim-consistency  {{ background: {"linear-gradient(135deg, #1E3A8A 0%, #1F2937 100%)" if d else "linear-gradient(135deg, #DBEAFE 0%, #F8FAFC 100%)"}; }}
    .dim-accuracy     {{ background: {"linear-gradient(135deg, #581C87 0%, #1F2937 100%)" if d else "linear-gradient(135deg, #EDE9FE 0%, #F8FAFC 100%)"}; }}
    .dim-uniqueness   {{ background: {"linear-gradient(135deg, #831843 0%, #1F2937 100%)" if d else "linear-gradient(135deg, #FCE7F3 0%, #F8FAFC 100%)"}; }}

    .section-header {{
        color: {"#F9FAFB" if d else "#1E293B"}; font-size: 1.25rem; font-weight: 600;
        margin-top: 1.5rem; margin-bottom: 1rem;
        border-left: 4px solid {"#00D4FF" if d else "#0EA5E9"}; padding-left: 0.8rem;
    }}

    .summary-box {{
        background: {"linear-gradient(135deg, #1E3A8A 0%, #312E81 100%)" if d else "linear-gradient(135deg, #EFF6FF 0%, #EDE9FE 100%)"};
        border-left: 5px solid {"#00D4FF" if d else "#0EA5E9"};
        padding: 1.3rem 1.6rem; border-radius: 10px;
        color: {"#F3F4F6" if d else "#1E293B"}; line-height: 1.8; margin: 1rem 0; font-size: 0.98rem;
    }}
    .summary-box b   {{ color: {"#FBBF24" if d else "#B45309"}; }}
    .summary-box code {{
        background: {"rgba(255,255,255,0.12)" if d else "rgba(0,0,0,0.07)"}; color: {"#FDE68A" if d else "#92400E"};
        padding: 2px 6px; border-radius: 4px; font-size: 0.9em;
    }}

    .api-status-ok  {{ color: #34D399; font-weight: 600; font-size: 1.05rem; }}
    .api-status-err {{ color: #F87171; font-weight: 600; font-size: 1.05rem; }}

    [data-testid="stAlert"] {{ background-color: {"#064E3B" if d else "#F0FDF4"}; border: 1px solid {"#10B981" if d else "#22C55E"}; }}

    .st-key-theme_toggle_box {{
        background: {"linear-gradient(135deg, #1F2937 0%, #111827 100%)" if d else "linear-gradient(135deg, #F8FAFC 0%, #E0F2FE 100%)"};
        border: 1px solid {"#374151" if d else "#38BDF8"};
        border-radius: 12px;
        padding: 0.85rem 0.9rem;
        margin: 0.25rem 0 0.35rem 0;
        box-shadow: 0 4px 12px rgba(15,23,42,{"0.32" if d else "0.12"});
    }}
    .st-key-theme_toggle_box [data-testid="stToggle"] {{
        background: transparent !important;
        border: 0 !important;
        padding: 0 !important;
        margin-top: 0.55rem !important;
        box-shadow: none !important;
    }}
    .theme-toggle-title {{
        color: {"#F9FAFB" if d else "#0F172A"};
        font-weight: 800;
        font-size: 0.95rem;
        line-height: 1.2;
    }}
    .theme-toggle-sub {{
        color: {"#9CA3AF" if d else "#475569"};
        font-size: 0.78rem;
        margin-top: 0.25rem;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] {{
        background: {"rgba(31,41,55,0.72)" if d else "#E0F2FE"};
        border: 1px solid {"#374151" if d else "#38BDF8"};
        border-radius: 10px;
        padding: 0.6rem 0.7rem;
        box-shadow: 0 2px 8px rgba(15,23,42,{"0.25" if d else "0.08"});
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] label,
    [data-testid="stSidebar"] [data-testid="stToggle"] p {{
        color: {"#F9FAFB" if d else "#0F172A"} !important;
        font-weight: 700;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] [role="switch"] {{
        background: {"#334155" if d else "#BAE6FD"} !important;
        border: 1px solid {"#60A5FA" if d else "#0284C7"} !important;
        box-shadow: 0 0 0 2px {"rgba(96,165,250,0.18)" if d else "rgba(14,165,233,0.20)"};
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] [role="switch"][aria-checked="true"] {{
        background: {"#0EA5E9" if d else "#0284C7"} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] [role="switch"] div {{
        background-color: {"#F8FAFC" if d else "#FFFFFF"} !important;
        border: 1px solid {"#CBD5E1" if d else "#7DD3FC"} !important;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        background: {"linear-gradient(135deg, #1F2937 0%, #111827 100%)" if d else "linear-gradient(135deg, #FFFFFF 0%, #E0F2FE 100%)"} !important;
        color: {"#F9FAFB" if d else "#075985"} !important;
        border: 1px solid {"#4B5563" if d else "#7DD3FC"} !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(15,23,42,{"0.35" if d else "0.10"});
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: {"#374151" if d else "#BAE6FD"} !important;
        border-color: {"#60A5FA" if d else "#0EA5E9"} !important;
        color: {"#FFFFFF" if d else "#0F172A"} !important;
    }}

    [data-testid="stDataFrame"] {{
        background: {"#111827" if d else "#FFFFFF"};
        border: 1px solid {"#374151" if d else "#CBD5E1"};
        border-radius: 10px;
        box-shadow: 0 3px 12px rgba(15,23,42,{"0.28" if d else "0.08"});
        overflow: hidden;
    }}
    [data-testid="stDataFrame"] div {{
        color: {"#E5E7EB" if d else "#1E293B"};
    }}
</style>
"""


st.markdown(_get_css(_THEME), unsafe_allow_html=True)


# ====================================================================
# 진단 결과 디스크 캐시 (새로고침 후 복원용)
# ====================================================================
_CACHE_DIR = Path(tempfile.gettempdir()) / "dq_diagnosis_cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(diag_id: int) -> Path:
    return _CACHE_DIR / f"diag_{diag_id}.json"


def _save_cache(diag_id: int, result: dict):
    try:
        with open(_cache_path(diag_id), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, default=str)
    except Exception:
        pass


def _load_cache(diag_id: int) -> dict | None:
    try:
        p = _cache_path(diag_id)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _clear_cache(diag_id: int):
    try:
        _cache_path(diag_id).unlink(missing_ok=True)
    except Exception:
        pass


# ====================================================================
# 헬퍼
# ====================================================================
_ALLOWED_TAGS = re.compile(
    r'&lt;(/?(?:b|br|code))&gt;',
    re.IGNORECASE,
)


def sanitize_summary_html(text: str) -> str:
    """<b>, <br>, <code>만 허용하고 나머지 태그는 이스케이프."""
    escaped = html.escape(text)
    return _ALLOWED_TAGS.sub(lambda m: f'<{m.group(1)}>', escaped)


def render_dataframe(df: pd.DataFrame, **kwargs):
    """라이트 모드에서 표가 다크 배경으로 보이지 않도록 Styler를 적용."""
    if _THEME != "light":
        st.dataframe(df, **kwargs)
        return

    styled = (
        df.style
        .set_properties(**{
            "background-color": "#FFFFFF",
            "color": "#1E293B",
            "border-color": "#CBD5E1",
        })
        .set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("background-color", "#E0F2FE"),
                    ("color", "#075985"),
                    ("font-weight", "700"),
                    ("border-color", "#CBD5E1"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("background-color", "#FFFFFF"),
                    ("color", "#1E293B"),
                    ("border-color", "#E2E8F0"),
                ],
            },
        ])
    )
    st.dataframe(styled, **kwargs)


def render_kpi_card(label: str, value: str, sub: str = "", extra_class: str = ""):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    card_html = (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value {extra_class}">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_dim_card(label: str, score: float, weight_pct: float, dim_class: str):
    card_html = (
        f'<div class="dim-card {dim_class}">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{score:.1f}</div>'
        f'<div class="weight">가중치 {weight_pct:.0f}%</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


# ====================================================================
# 헤더
# ====================================================================
st.markdown('<div class="main-title">📊 AI-Ready 데이터 품질 스코어카드</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">5대 지표 진단 (완전성·유효성·일관성·이상치·유일성) | FastAPI + MySQL + Streamlit</div>',
    unsafe_allow_html=True,
)


# ====================================================================
# 사이드바 렌더링 전 캐시 복원 (사이드바에서 파일명 표시를 위해 먼저 실행)
# ====================================================================
if "_diag_result" not in st.session_state:
    _qp_id = st.query_params.get("diag_id")
    if _qp_id:
        try:
            _cached = _load_cache(int(_qp_id))
            if _cached:
                st.session_state["_diag_result"] = _cached
                st.session_state["_last_diag_id"] = int(_qp_id)
            else:
                st.query_params.clear()
        except Exception:
            st.query_params.clear()


# ====================================================================
# 사이드바
# ====================================================================
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    api_ok = api_client.health()
    if api_ok:
        st.markdown('<div class="api-status-ok">🟢 API 서버 정상</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="api-status-err">🔴 API 서버 연결 실패</div>',
                    unsafe_allow_html=True)
        st.caption("`uvicorn backend.main:app --reload`")

    st.markdown("---")
    with st.container(border=True, key="theme_toggle_box"):
        st.markdown(
            """
            <div class="theme-toggle-title">화면 모드</div>
            <div class="theme-toggle-sub">대시보드 색상 테마 전환</div>
            """,
            unsafe_allow_html=True,
        )
        st.toggle("🌙 다크 모드", key="_is_dark")

    st.markdown("---")
    st.markdown("### 📁 데이터 업로드")
    uploaded_file = st.file_uploader(
        "CSV 또는 Excel 파일", type=["csv", "xlsx", "xls", "xlsm"], label_visibility="collapsed")

    # 새로고침으로 복원된 경우 초기화 버튼 (업로더 위젯은 초기화되므로)
    if uploaded_file is None and "_diag_result" in st.session_state:
        if st.button("✕ 결과 초기화", use_container_width=True):
            _last_id = st.session_state.get("_last_diag_id")
            if _last_id:
                _clear_cache(_last_id)
            for _k in ["_diag_result", "_diag_file_key", "_last_diag_id", "_had_file"]:
                st.session_state.pop(_k, None)
            st.query_params.clear()

    st.markdown("---")
    st.markdown("### 🎚️ 5대 지표 가중치")
    st.caption("총합 1.0이 되도록 서버에서 자동 정규화됩니다.")

    if st.button("🔄 기본값 복원 (30/25/20/15/10)", use_container_width=True):
        for k in ["w_comp", "w_vali", "w_cons", "w_acc", "w_uniq"]:
            st.session_state.pop(k, None)
        st.rerun()

    w_comp = st.slider("완전성 (Completeness)", 0.0,
                       1.0, 0.30, 0.05, key="w_comp")
    w_vali = st.slider("유효성 (Validity)",     0.0,
                       1.0, 0.25, 0.05, key="w_vali")
    w_cons = st.slider("일관성 (Consistency)",  0.0,
                       1.0, 0.20, 0.05, key="w_cons")
    w_acc = st.slider("이상치 (Accuracy)",     0.0, 1.0, 0.15, 0.05, key="w_acc")
    w_uniq = st.slider("유일성 (Uniqueness)",   0.0,
                       1.0, 0.10, 0.05, key="w_uniq")

    weights = {
        "completeness": w_comp, "validity": w_vali,
        "consistency":  w_cons, "accuracy": w_acc, "uniqueness": w_uniq,
    }
    total_w = sum(weights.values())
    if total_w == 0:
        st.warning("⚠️ 가중치 합 0 — 기본값을 사용합니다.")
    else:
        st.caption(
            f"정규화 후: 완전 {w_comp/total_w*100:.0f}% / 유효 {w_vali/total_w*100:.0f}% / "
            f"일관 {w_cons/total_w*100:.0f}% / 이상치 {w_acc/total_w*100:.0f}% / 중복 {w_uniq/total_w*100:.0f}%"
        )

    st.markdown("---")
    st.markdown("### 📚 메뉴")
    menu = st.radio("보기 선택", ["진단 실행", "진단 이력 (DB)"],
                    label_visibility="collapsed")

    st.markdown("---")
    st.caption("v2.0 | 5대 지표 Scorecard | S/A/B/C/F 등급")


# ====================================================================
# 서버 미연결 시 안내
# ====================================================================
if not api_ok:
    st.error("⚠️ FastAPI 서버에 연결할 수 없습니다.")
    st.code("uvicorn backend.main:app --reload --port 8000", language="bash")
    st.stop()


# ====================================================================
# 메뉴 1: 진단 실행
# ====================================================================
if menu == "진단 실행":

    # ---- 파일 업로더 X 클릭 감지 ----
    # 이전 rerun에서 파일이 있었는데 지금 없으면 = 사용자가 X를 클릭
    _prev_had_file = st.session_state.get("_had_file", False)
    _curr_has_file = uploaded_file is not None
    st.session_state["_had_file"] = _curr_has_file

    if _prev_had_file and not _curr_has_file:
        _last_id = st.session_state.get("_last_diag_id")
        if _last_id:
            _clear_cache(_last_id)
        for _k in ["_diag_result", "_diag_file_key", "_last_diag_id"]:
            st.session_state.pop(_k, None)
        st.query_params.clear()

    # ---- 파일도 없고 캐시도 없으면 → 안내 화면 ----
    if not _curr_has_file and "_diag_result" not in st.session_state:
        st.info("👈 좌측 사이드바에서 CSV 또는 Excel 파일을 업로드하세요.")

        st.markdown('<div class="section-header">📐 5대 품질 지표</div>',
                    unsafe_allow_html=True)
        cols = st.columns(5)
        intro = [
            ("완전성",   "Null/결측 검사",       "30%", "dim-completeness"),
            ("유효성",   "타입/범위 검증",       "25%", "dim-validity"),
            ("일관성",   "형식/단위 통일",       "20%", "dim-consistency"),
            ("이상치",   "IQR+Z+IForest 다수결", "15%", "dim-accuracy"),
            ("유일성",   "중복/키 검사",         "10%", "dim-uniqueness"),
        ]
        for col, (label, desc, w, klass) in zip(cols, intro):
            with col:
                card_html = (
                    f'<div class="dim-card {klass}">'
                    f'<div class="label">{label}</div>'
                    f'<div class="value" style="font-size:1.2rem;">{desc}</div>'
                    f'<div class="weight">기본 가중치 {w}</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

        st.markdown(
            '<div class="section-header">🏆 AI-Ready 등급 체계</div>', unsafe_allow_html=True)
        gcols = st.columns(5)
        grades = [
            ("S", "97점 이상",  "즉시 학습 가능",  "grade-S"),
            ("A", "90 ~ 97점",  "Class A 기준",    "grade-A"),
            ("B", "80 ~ 90점",  "경미한 보완",     "grade-B"),
            ("C", "70 ~ 80점",  "전처리 필요",     "grade-C"),
            ("F", "70점 미만",  "학습 부적합",     "grade-F"),
        ]
        for col, (g, r, d, cls) in zip(gcols, grades):
            with col:
                render_kpi_card(d, g, sub=r, extra_class=cls)

        st.stop()

    # ---- 파일이 업로드된 경우 → 진단 버튼 ----
    if _curr_has_file:
        file_bytes = uploaded_file.getvalue()
        file_key = f"{uploaded_file.name}_{len(file_bytes)}"
        if st.session_state.get("_diag_file_key") != file_key:
            _prev_id = st.session_state.get("_last_diag_id")
            if _prev_id:
                _clear_cache(_prev_id)
            for _k in ["_diag_result", "_last_diag_id"]:
                st.session_state.pop(_k, None)
            st.session_state["_diag_file_key"] = file_key
            st.query_params.clear()

        file_mb = len(file_bytes) / (1024 * 1024)
        run_btn = st.button("🔍 진단 시작", type="primary", use_container_width=True)

        if run_btn:
            if file_mb > 100:
                st.info(
                    f"📦 대용량 파일({file_mb:.0f}MB) 진단 중입니다. 데이터 크기에 따라 수 분이 소요될 수 있습니다.")
            with st.spinner(f"🔄 5대 지표 진단 수행 중... (파일 {file_mb:.1f}MB, IsolationForest 학습 포함)"):
                try:
                    _diag_result = api_client.diagnose(
                        uploaded_file.name, file_bytes, weights)
                    st.session_state["_diag_result"] = _diag_result
                    _diag_id = _diag_result["history"]["id"]
                    st.session_state["_last_diag_id"] = _diag_id
                    _save_cache(_diag_id, _diag_result)
                    st.query_params["diag_id"] = str(_diag_id)
                except Exception as e:
                    st.error(f"❌ 진단 실패: {e}")
                    st.stop()

        if "_diag_result" not in st.session_state:
            st.info("👆 파일을 확인한 후 '진단 시작' 버튼을 눌러 주세요.")
            st.stop()
    else:
        # 파일 없음 + 캐시 복원된 상태 → 안내 배너
        st.info(
            "🔄 새로고침 후 이전 진단 결과를 복원했습니다. "
            "새 파일을 진단하려면 사이드바에서 파일을 업로드하세요. "
            "결과를 초기화하려면 파일 업로더의 **✕** 버튼을 누르세요."
        )

    result = st.session_state["_diag_result"]
    history = result["history"]
    detail = result["detail"]
    summary_text = result["summary_text"]
    column_scores = result["column_scores"]
    diagnosis = detail["diagnosis"]
    basic_info = detail["basic_info"]
    dimension_scores = detail["dimension_scores"]
    weights_used = detail["weights_used"]

    st.success(
        f"✅ 진단 완료 및 MySQL 저장됨 "
        f"(진단 ID: **{history['id']}** / 파일: **{history['filename']}** / "
        f"종합 **{history['quality_score']:.1f}점 등급 {history['grade']}**)"
    )

    # ====================================================================
    # 탭 UI
    # ====================================================================
    tab_overview, tab_dimensions, tab_charts, tab_drill, tab_issues = st.tabs([
        "📌 개요 & 종합",
        "🎯 5대 지표 상세",
        "📈 시각화",
        "🔍 컬럼 Drill-down",
        "⚠️ 데이터 이슈",
    ])

    # --- 탭 1: 개요 ---
    with tab_overview:
        st.markdown('<div class="section-header">📌 종합 평가</div>',
                    unsafe_allow_html=True)

        kpi_cols = st.columns(5)
        with kpi_cols[0]:
            render_kpi_card("종합 품질 점수", f"{history['quality_score']:.1f}점")
        with kpi_cols[1]:
            render_kpi_card(
                "AI-Ready 등급", history["grade"], extra_class=f"grade-{history['grade']}")
        with kpi_cols[2]:
            render_kpi_card("결측치", f"{history['missing_count']:,}개",
                            sub=f"({diagnosis['completeness']['overall_ratio']*100:.2f}%)")
        with kpi_cols[3]:
            render_kpi_card("이상치 (앙상블)", f"{history['outlier_count']:,}행",
                            sub="다수결 2표 이상")
        with kpi_cols[4]:
            render_kpi_card("중복 데이터", f"{history['duplicate_count']:,}건",
                            sub=f"({diagnosis['uniqueness']['ratio']*100:.2f}%)")

        key_dup = diagnosis["uniqueness"]["key_duplicate_count"]
        key_cols_found = diagnosis["uniqueness"]["key_columns"]
        if key_dup > 0 and key_cols_found:
            st.warning(
                f"⚠️ 키 컬럼 중복 감지: **{', '.join(key_cols_found)}** 컬럼에서 "
                f"중복값 **{key_dup:,}건** 발견 (점수에는 미반영 — 참고용)"
            )

        st.markdown('<div class="section-header">📋 데이터셋 개요</div>',
                    unsafe_allow_html=True)
        info_cols = st.columns(4)
        info_cols[0].metric("총 행 수", f"{basic_info['rows']:,}")
        info_cols[1].metric("총 컬럼 수", f"{basic_info['cols']:,}")
        info_cols[2].metric("수치형 컬럼", f"{basic_info['numeric_cols']}")
        info_cols[3].metric("범주형 컬럼", f"{basic_info['categorical_cols']}")

        st.markdown('<div class="section-header">🤖 AI 진단 요약</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<div class="summary-box">{sanitize_summary_html(summary_text)}</div>', unsafe_allow_html=True)

    # --- 탭 2: 5대 지표 상세 ---
    with tab_dimensions:
        st.markdown('<div class="section-header">🎯 5대 품질 지표 점수</div>',
                    unsafe_allow_html=True)

        dim_cols = st.columns(5)
        dim_info = [
            ("완전성", dimension_scores["completeness"],
             weights_used["completeness"]*100, "dim-completeness"),
            ("유효성", dimension_scores["validity"],
             weights_used["validity"]*100,     "dim-validity"),
            ("일관성", dimension_scores["consistency"],
             weights_used["consistency"]*100,  "dim-consistency"),
            ("이상치", dimension_scores["accuracy"],
             weights_used["accuracy"]*100,     "dim-accuracy"),
            ("유일성", dimension_scores["uniqueness"],
             weights_used["uniqueness"]*100,   "dim-uniqueness"),
        ]
        for col, (label, score, w_pct, klass) in zip(dim_cols, dim_info):
            with col:
                render_dim_card(label, score, w_pct, klass)

        st.markdown('<div class="section-header">📊 레이더 차트</div>',
                    unsafe_allow_html=True)
        r1, r2 = st.columns([1, 1])
        with r1:
            st.plotly_chart(plot_dimension_radar(
                dimension_scores, theme=_THEME), use_container_width=True)
        with r2:
            st.plotly_chart(plot_dimension_bar(
                dimension_scores, weights_used, theme=_THEME), use_container_width=True)

        # 지표별 상세 카운트
        st.markdown('<div class="section-header">📐 지표별 측정 결과</div>',
                    unsafe_allow_html=True)
        detail_data = [
            {"지표": "완전성", "점수": f"{dimension_scores['completeness']:.2f}",
             "측정 대상": f"{basic_info['rows']*basic_info['cols']:,}개 셀",
             "문제 수": f"{diagnosis['completeness']['total_missing']:,}개"},
            {"지표": "유효성", "점수": f"{dimension_scores['validity']:.2f}",
             "측정 대상": "타입/범위 검증",
             "문제 수": f"{diagnosis['validity']['invalid_count']:,}개"},
            {"지표": "일관성", "점수": f"{dimension_scores['consistency']:.2f}",
             "측정 대상": "형식/공백/대소문자",
             "문제 수": f"{diagnosis['consistency']['inconsistent_count']:,}개"},
            {"지표": "이상치", "점수": f"{dimension_scores['accuracy']:.2f}",
             "측정 대상": f"{basic_info['rows']:,}개 행",
             "문제 수": f"{diagnosis['accuracy']['total_row_count']:,}행"},
            {"지표": "유일성", "점수": f"{dimension_scores['uniqueness']:.2f}",
             "측정 대상": f"{basic_info['rows']:,}개 행",
             "문제 수": f"{diagnosis['uniqueness']['count']:,}건"},
        ]
        render_dataframe(pd.DataFrame(detail_data),
                         use_container_width=True, hide_index=True)

    # --- 탭 3: 시각화 ---
    with tab_charts:
        st.markdown('<div class="section-header">📈 데이터 품질 시각화</div>',
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plot_missing_by_column(
                diagnosis["completeness"], theme=_THEME), use_container_width=True)
        with c2:
            st.plotly_chart(plot_problem_ratio_pie(
                diagnosis, theme=_THEME), use_container_width=True)

        st.plotly_chart(plot_column_quality_bar(
            column_scores, theme=_THEME), use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(plot_column_outliers(
                diagnosis["accuracy"], theme=_THEME), use_container_width=True)
        with c4:
            st.plotly_chart(plot_outlier_method_compare(
                diagnosis["accuracy"], theme=_THEME), use_container_width=True)

    # --- 탭 4: Drill-down ---
    with tab_drill:
        st.markdown('<div class="section-header">🔍 컬럼별 상세 분석</div>',
                    unsafe_allow_html=True)

        all_columns = list(column_scores.keys())
        if not all_columns:
            st.info("분석할 컬럼이 없습니다.")
        else:
            selected_col = st.selectbox("상세 분석할 컬럼", all_columns)
            if selected_col:
                col_miss = diagnosis["completeness"]["per_column"].get(
                    selected_col, 0)
                col_miss_count = diagnosis["completeness"]["per_column_count"].get(
                    selected_col, 0)
                col_inval = diagnosis["validity"]["per_column"].get(
                    selected_col, 0)
                col_incon = diagnosis["consistency"]["per_column"].get(
                    selected_col, 0)
                col_out = diagnosis["accuracy"]["per_column"].get(
                    selected_col, 0)
                col_score = column_scores.get(selected_col, 0)

                d_cols = st.columns(5)
                with d_cols[0]:
                    render_kpi_card(
                        "결측", f"{col_miss_count:,}", sub=f"({col_miss*100:.2f}%)")
                with d_cols[1]:
                    render_kpi_card("유효성 오류", f"{col_inval:,}개")
                with d_cols[2]:
                    render_kpi_card("일관성 오류", f"{col_incon:,}개")
                with d_cols[3]:
                    render_kpi_card("이상치", f"{col_out:,}개", sub="앙상블 다수결")
                with d_cols[4]:
                    render_kpi_card("컬럼 점수", f"{col_score:.1f}")

                st.markdown(
                    '<div class="section-header">📝 컬럼 상세 정보</div>', unsafe_allow_html=True)
                detail_df = pd.DataFrame([
                    {"항목": "컬럼명", "값": selected_col},
                    {"항목": "결측 셀 개수",
                        "값": f"{col_miss_count:,} ({col_miss*100:.4f}%)"},
                    {"항목": "유효성 오류 (타입 불일치)", "값": f"{col_inval:,}개"},
                    {"항목": "일관성 오류 (형식 불일치)", "값": f"{col_incon:,}개"},
                    {"항목": "이상치 (앙상블)", "값": f"{col_out:,}개"},
                    {"항목": "컬럼 품질 점수", "값": f"{col_score:.2f} / 100"},
                ])
                render_dataframe(detail_df, use_container_width=True,
                                 hide_index=True)

    # --- 탭 5: 이슈 ---
    with tab_issues:
        st.markdown(
            '<div class="section-header">⚠️ 유효성 이슈 (타입 불일치)</div>', unsafe_allow_html=True)
        issues = diagnosis["validity"].get("issues", [])
        if issues:
            st.warning(f"총 {len(issues)}개 컬럼에서 타입/형식 이슈 감지")
            render_dataframe(pd.DataFrame(issues),
                             use_container_width=True, hide_index=True)
        else:
            st.success("✅ 유효성 이슈가 감지되지 않았습니다.")

        st.markdown(
            '<div class="section-header">문제 위치 미리보기</div>', unsafe_allow_html=True)
        location_rows = []
        display_location_limit = 500
        for label, key in [
            ("결측", "completeness"),
            ("유효성", "validity"),
            ("일관성", "consistency"),
            ("이상치", "accuracy"),
            ("중복", "uniqueness"),
        ]:
            info = diagnosis.get(key, {})
            for item in info.get("locations", []):
                if len(location_rows) >= display_location_limit:
                    break
                location_rows.append({
                    "진단": label,
                    "유형": item.get("type", ""),
                    "데이터 행": item.get("row", ""),
                    "Excel 행": item.get("excel_row", ""),
                    "컬럼": item.get("column", ""),
                    "값": item.get("value", ""),
                    "설명": item.get("message", ""),
                })
            if len(location_rows) >= display_location_limit:
                break

        total_location_count = sum(
            int(diagnosis.get(key, {}).get("location_count", 0))
            for key in ["completeness", "validity", "consistency", "accuracy", "uniqueness"]
        )
        if location_rows:
            if total_location_count > len(location_rows):
                st.caption(
                    f"총 {total_location_count:,}개 문제 위치 중 상위 {len(location_rows):,}개만 표시합니다.")
            render_dataframe(pd.DataFrame(location_rows),
                             use_container_width=True, hide_index=True, height=360)
        else:
            st.success("표시할 문제 위치가 없습니다.")

        st.markdown('<div class="section-header">📊 종합 진단 요약</div>',
                    unsafe_allow_html=True)
        total_cells = basic_info['rows'] * basic_info['cols']
        summary_df = pd.DataFrame([
            {"진단 항목": "총 행 수",         "값": f"{basic_info['rows']:,}"},
            {"진단 항목": "총 컬럼 수",       "값": f"{basic_info['cols']:,}"},
            {"진단 항목": "총 셀 수",         "값": f"{total_cells:,}"},
            {"진단 항목": "결측 셀",
                "값": f"{history['missing_count']:,} ({diagnosis['completeness']['overall_ratio']*100:.2f}%)"},
            {"진단 항목": "유효성 오류 셀",
                "값": f"{diagnosis['validity']['invalid_count']:,} ({diagnosis['validity']['invalid_ratio']*100:.2f}%)"},
            {"진단 항목": "일관성 오류 셀",
                "값": f"{diagnosis['consistency']['inconsistent_count']:,} ({diagnosis['consistency']['inconsistent_ratio']*100:.2f}%)"},
            {"진단 항목": "이상치 (앙상블, 행 기준)",
             "값": f"{diagnosis['accuracy']['total_row_count']:,} ({diagnosis['accuracy']['overall_ratio']*100:.2f}%)"},
            {"진단 항목": "중복 행",
                "값": f"{history['duplicate_count']:,} ({diagnosis['uniqueness']['ratio']*100:.2f}%)"},
            {"진단 항목": "키 컬럼 중복 (참고)",
                "값": f"{diagnosis['uniqueness']['key_duplicate_count']:,}건 / 대상 컬럼: {', '.join(diagnosis['uniqueness']['key_columns']) or '없음'}"},
            {"진단 항목": "종합 점수",
                "값": f"{history['quality_score']:.2f} / 100"},
            {"진단 항목": "AI-Ready 등급",    "값": history['grade']},
        ])
        render_dataframe(summary_df, use_container_width=True, hide_index=True)


# ====================================================================
# 메뉴 2: 진단 이력
# ====================================================================
else:
    st.markdown('<div class="section-header">🗄️ MySQL 진단 이력</div>',
                unsafe_allow_html=True)

    try:
        history_list = api_client.list_history(limit=100)
    except Exception as e:
        st.error(f"❌ 이력 조회 실패: {e}")
        st.stop()

    if not history_list:
        st.info("아직 저장된 진단 이력이 없습니다.")
        st.stop()

    h_tab1, h_tab2, h_tab3 = st.tabs(["📊 이력 요약", "📋 전체 목록", "🗑️ 이력 관리"])

    with h_tab1:
        total = len(history_list)
        avg_score = sum(h["quality_score"] for h in history_list) / total
        max_score = max(h["quality_score"] for h in history_list)
        min_score = min(h["quality_score"] for h in history_list)

        # 등급 분포
        grade_counts = {}
        for h in history_list:
            grade_counts[h["grade"]] = grade_counts.get(h["grade"], 0) + 1
        grade_summary = " / ".join([f"{g}:{c}" for g,
                                   c in sorted(grade_counts.items())])

        k_cols = st.columns(4)
        with k_cols[0]:
            render_kpi_card("저장된 진단 수", f"{total:,}")
        with k_cols[1]:
            render_kpi_card("평균 종합 점수", f"{avg_score:.1f}점")
        with k_cols[2]:
            render_kpi_card("최고/최저", f"{max_score:.1f} / {min_score:.1f}")
        with k_cols[3]:
            render_kpi_card("등급 분포", grade_summary, sub="S/A/B/C/F")

        st.plotly_chart(plot_history_trend(history_list, theme=_THEME),
                        use_container_width=True)

    with h_tab2:
        history_df = pd.DataFrame(history_list)
        display_cols = ["id", "filename", "checked_at",
                        "completeness_score", "validity_score", "consistency_score",
                        "accuracy_score", "uniqueness_score",
                        "quality_score", "grade"]
        col_rename = {
            "id":                 "진단 ID",
            "filename":           "파일명",
            "checked_at":         "진단 일시",
            "completeness_score": "완전성",
            "validity_score":     "유효성",
            "consistency_score":  "일관성",
            "accuracy_score":     "이상치",
            "uniqueness_score":   "유일성",
            "quality_score":      "종합 점수",
            "grade":              "등급",
        }
        # 존재하는 컬럼만 표시 (구버전 데이터 호환)
        display_cols = [c for c in display_cols if c in history_df.columns]
        display_df = (
            history_df[display_cols]
            .rename(columns=col_rename)
            .reset_index(drop=True)
        )
        display_df.index = display_df.index + 1
        display_df.index.name = "순번"
        render_dataframe(display_df, use_container_width=True, height=500)

    with h_tab3:
        st.markdown("##### 🗑️ 진단 이력 삭제")
        st.caption("진단 ID를 입력하면 해당 레코드가 MySQL에서 영구 삭제됩니다.")
        d1, d2 = st.columns([3, 1])
        with d1:
            delete_id = st.number_input("삭제할 진단 ID", min_value=1, step=1)
        with d2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ 삭제", use_container_width=True, type="primary"):
                if api_client.delete_history(int(delete_id)):
                    st.success(f"진단 ID {delete_id} 삭제 완료")
                    st.rerun()
                else:
                    st.error("삭제 실패: 해당 ID가 없습니다.")
