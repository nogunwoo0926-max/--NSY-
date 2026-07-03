"""
Plotly 다크/라이트 테마 차트
- 5대 지표 레이더 차트
- 5대 지표 점수 bar 차트
- 컬럼별 결측 / 문제 유형 비율 / 컬럼 품질 점수 / 컬럼별 이상치 / 이력 트렌드
"""
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List

# ── 테마 색상 팔레트 ─────────────────────────────────────────────────
_THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "bg":      "#0E1117",
        "panel":   "#1F2937",
        "font":    "#E5E7EB",
        "grid":    "#374151",
        "accent":  "#00D4FF",
        "accent2": "#C77DFF",
    },
    "light": {
        "bg":      "#F1F5F9",
        "panel":   "#FFFFFF",
        "font":    "#1F2937",
        "grid":    "#E2E8F0",
        "accent":  "#0EA5E9",
        "accent2": "#7B2CBF",
    },
}

# 지표명 한글 매핑
DIM_LABELS = {
    "completeness": "완전성",
    "validity":     "유효성",
    "consistency":  "일관성",
    "accuracy":     "이상치",
    "uniqueness":   "유일성",
}


def _t(theme: str) -> Dict[str, str]:
    return _THEMES.get(theme, _THEMES["dark"])


def _apply_layout(fig: go.Figure, title: str = "", theme: str = "dark") -> go.Figure:
    c = _t(theme)
    fig.update_layout(
        template="plotly_dark" if theme == "dark" else "plotly_white",
        title=dict(text=title, font=dict(color=c["font"], size=16)),
        paper_bgcolor=c["bg"],
        plot_bgcolor=c["panel"],
        font=dict(color=c["font"], family="Segoe UI, sans-serif"),
        legend=dict(
            font=dict(color=c["font"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=c["panel"],
            bordercolor=c["grid"],
            font=dict(color=c["font"]),
        ),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_xaxes(
        gridcolor=c["grid"],
        zerolinecolor=c["grid"],
        linecolor=c["grid"],
        tickcolor=c["grid"],
        tickfont=dict(color=c["font"]),
        title_font=dict(color=c["font"]),
        showline=True,
    )
    fig.update_yaxes(
        gridcolor=c["grid"],
        zerolinecolor=c["grid"],
        linecolor=c["grid"],
        tickcolor=c["grid"],
        tickfont=dict(color=c["font"]),
        title_font=dict(color=c["font"]),
        showline=True,
    )
    fig.update_traces(textfont=dict(color=c["font"]))
    fig.update_traces(
        insidetextfont=dict(color=c["font"]),
        outsidetextfont=dict(color=c["font"]),
        selector=dict(type="bar"),
    )
    return fig


# ====================================================================
# 1) 5대 지표 레이더 차트
# ====================================================================
def plot_dimension_radar(dimension_scores: Dict[str, float], theme: str = "dark") -> go.Figure:
    c = _t(theme)
    labels = [DIM_LABELS[k] for k in DIM_LABELS.keys()]
    values = [dimension_scores.get(k, 0) for k in DIM_LABELS.keys()]

    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        line=dict(color=c["accent"], width=3),
        fillcolor=f"rgba({int(c['accent'][1:3],16)}, {int(c['accent'][3:5],16)}, {int(c['accent'][5:7],16)}, 0.2)",
        marker=dict(size=10, color=c["accent2"]),
        hovertemplate="<b>%{theta}</b><br>점수: %{r:.1f}점<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark" if theme == "dark" else "plotly_white",
        title=dict(text="🎯 5대 품질 지표 레이더", font=dict(color=c["font"], size=16)),
        polar=dict(
            bgcolor=c["panel"],
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor=c["grid"],
                linecolor=c["grid"],
                tickcolor=c["grid"],
                tickfont=dict(color=c["font"], size=10),
            ),
            angularaxis=dict(
                gridcolor=c["grid"],
                linecolor=c["grid"],
                tickcolor=c["grid"],
                tickfont=dict(color=c["font"], size=12),
            ),
        ),
        paper_bgcolor=c["bg"],
        font=dict(color=c["font"]),
        hoverlabel=dict(
            bgcolor=c["panel"],
            bordercolor=c["grid"],
            font=dict(color=c["font"]),
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=80, b=40),
    )
    return fig


# ====================================================================
# 2) 5대 지표 점수 bar 차트
# ====================================================================
def plot_dimension_bar(dimension_scores: Dict[str, float], weights: Dict[str, float], theme: str = "dark") -> go.Figure:
    c = _t(theme)
    labels = [DIM_LABELS[k] for k in DIM_LABELS.keys()]
    values = [dimension_scores.get(k, 0) for k in DIM_LABELS.keys()]
    weight_labels = [f"가중치 {weights.get(k, 0)*100:.0f}%" for k in DIM_LABELS.keys()]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker=dict(
            color=values,
            colorscale=[[0, "#EF4444"], [0.5, "#F59E0B"], [1, "#10B981"]],
            showscale=False,
        ),
        text=[f"{v:.1f}점<br><span style='font-size:0.8em;color:{c['grid']};'>{wl}</span>"
              for v, wl in zip(values, weight_labels)],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>점수: %{y:.2f}점<extra></extra>",
    ))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="점수", range=[0, 115])
    return _apply_layout(fig, "📊 5대 지표 점수 (가중치 표시)", theme)


# ====================================================================
# 3) 컬럼별 결측치 bar chart
# ====================================================================
def plot_missing_by_column(completeness_info: Dict[str, Any], theme: str = "dark") -> go.Figure:
    per_col = completeness_info.get("per_column", {})
    if not per_col:
        return _apply_layout(go.Figure(), "컬럼별 결측률 (데이터 없음)", theme)

    df_plot = (
        pd.DataFrame({"column": list(per_col.keys()),
                     "missing_ratio": list(per_col.values())})
        .assign(missing_pct=lambda d: d["missing_ratio"] * 100)
        .sort_values("missing_pct", ascending=True)
    )

    fig = go.Figure(go.Bar(
        x=df_plot["missing_pct"],
        y=df_plot["column"],
        orientation="h",
        marker=dict(
            color=df_plot["missing_pct"],
            colorscale=[[0, "#10B981"], [0.5, "#F59E0B"], [1, "#EF4444"]],
            showscale=False,
        ),
        text=[f"{v:.1f}%" for v in df_plot["missing_pct"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>결측률: %{x:.2f}%<extra></extra>",
    ))
    fig.update_xaxes(title_text="결측률 (%)")
    return _apply_layout(fig, "컬럼별 결측률", theme)


# ====================================================================
# 4) 문제 유형 비율 pie chart
# ====================================================================
def plot_problem_ratio_pie(diagnosis: Dict[str, Any], theme: str = "dark") -> go.Figure:
    c = _t(theme)
    values = [
        diagnosis["completeness"]["total_missing"],
        diagnosis["validity"]["invalid_count"],
        diagnosis["consistency"]["inconsistent_count"],
        diagnosis["accuracy"]["total_row_count"],
        diagnosis["uniqueness"]["count"],
    ]
    labels = ["결측", "무효(타입오류)", "비일관", "이상치", "중복"]
    colors = ["#EF4444", "#F97316", "#FBBF24", "#7B2CBF", "#3B82F6"]

    if sum(values) == 0:
        fig = go.Figure(go.Pie(
            labels=["문제 없음"], values=[1], hole=0.5,
            marker=dict(colors=["#10B981"]),
        ))
        return _apply_layout(fig, "데이터 품질 문제 건수 구성 (이상 없음)", theme)

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>건수: %{value:,}<br>비율: %{percent}<extra></extra>",
    ))
    return _apply_layout(fig, "데이터 품질 문제 건수 구성", theme)


# ====================================================================
# 5) 컬럼별 품질 점수 bar
# ====================================================================
def plot_column_quality_bar(col_scores: Dict[str, float], theme: str = "dark") -> go.Figure:
    c = _t(theme)
    if not col_scores:
        return _apply_layout(go.Figure(), "컬럼별 품질 점수 (데이터 없음)", theme)

    df_plot = (
        pd.DataFrame({"column": list(col_scores.keys()),
                     "score": list(col_scores.values())})
        .sort_values("score", ascending=False)
    )

    fig = go.Figure(go.Bar(
        x=df_plot["column"],
        y=df_plot["score"],
        marker=dict(
            color=df_plot["score"],
            colorscale=[[0, "#EF4444"], [0.5, "#F59E0B"], [1, "#10B981"]],
            showscale=True,
            colorbar=dict(
                title=dict(text="점수", font=dict(color=c["font"])),
                tickfont=dict(color=c["font"]),
            ),
        ),
        text=[f"{v:.1f}" for v in df_plot["score"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>품질 점수: %{y:.2f}점<extra></extra>",
    ))
    fig.update_xaxes(title_text="컬럼", tickangle=-30)
    fig.update_yaxes(title_text="품질 점수", range=[0, 110])
    return _apply_layout(fig, "컬럼별 품질 점수", theme)


# ====================================================================
# 6) 컬럼별 이상치 (앙상블)
# ====================================================================
def plot_column_outliers(accuracy_info: Dict[str, Any], theme: str = "dark") -> go.Figure:
    per_col = {k: v for k, v in accuracy_info.get("per_column", {}).items() if v > 0}
    if not per_col:
        return _apply_layout(go.Figure(), "컬럼별 이상치 (없음)", theme)

    df_plot = (
        pd.DataFrame({"column": list(per_col.keys()),
                     "count": list(per_col.values())})
        .sort_values("count", ascending=True)
    )

    fig = go.Figure(go.Bar(
        x=df_plot["count"],
        y=df_plot["column"],
        orientation="h",
        marker=dict(color="#F59E0B"),
        text=df_plot["count"],
        textposition="outside",
    ))
    fig.update_xaxes(title_text="이상치 개수 (앙상블 다수결)")
    return _apply_layout(fig, "컬럼별 이상치 개수", theme)


# ====================================================================
# 7) 이상치 알고리즘별 탐지 결과 비교
# ====================================================================
def plot_outlier_method_compare(accuracy_info: Dict[str, Any], theme: str = "dark") -> go.Figure:
    pm = accuracy_info.get("per_method_count", {})
    if not pm or sum(pm.values()) == 0:
        return _apply_layout(go.Figure(), "이상치 탐지 알고리즘 비교 (데이터 없음)", theme)

    methods = ["IQR", "Z-Score", "Isolation Forest", "Ensemble (≥2표)"]
    keys = ["iqr", "zscore", "isoforest", "ensemble"]
    values = [pm.get(k, 0) for k in keys]
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#7B2CBF"]

    fig = go.Figure(go.Bar(
        x=methods,
        y=values,
        marker=dict(color=colors),
        text=[f"{v:,}" for v in values],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>탐지 개수: %{y:,}<extra></extra>",
    ))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="탐지 개수")
    return _apply_layout(fig, "🔬 이상치 탐지 알고리즘 비교", theme)


# ====================================================================
# 8) 진단 이력 트렌드
# ====================================================================
def plot_history_trend(history: List[Dict[str, Any]], theme: str = "dark") -> go.Figure:
    c = _t(theme)
    if not history:
        return _apply_layout(go.Figure(), "진단 이력 (데이터 없음)", theme)

    df = pd.DataFrame(history).sort_values("checked_at")

    def _get(row, col):
        v = row.get(col)
        return f"{v:.1f}" if v is not None else "-"

    hover_texts = [
        (
            f"<b>{row.get('filename', '')}</b><br>"
            f"종합 점수: {row.get('quality_score', 0):.1f}점 ({row.get('grade', '')})<br>"
            f"─────────────<br>"
            f"완전성: {_get(row, 'completeness_score')} / "
            f"유효성: {_get(row, 'validity_score')}<br>"
            f"일관성: {_get(row, 'consistency_score')} / "
            f"이상치: {_get(row, 'accuracy_score')} / "
            f"유일성: {_get(row, 'uniqueness_score')}"
        )
        for row in df.to_dict("records")
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["checked_at"],
        y=df["quality_score"],
        name="종합 점수",
        mode="lines+markers",
        line=dict(color=c["accent"], width=3),
        marker=dict(size=10, color=c["accent2"]),
        text=hover_texts,
        hovertemplate="%{text}<extra></extra>",
    ))

    fig.update_xaxes(title_text="진단 일시")
    fig.update_yaxes(title_text="종합 점수", range=[0, 105])
    return _apply_layout(fig, "📈 진단 이력 추이", theme)
