# 📊 AI-Ready 데이터 품질 스코어카드 시스템

CSV/Excel 데이터를 업로드하면 **5대 품질 지표**로 자동 진단하여 점수(0~100)와 등급(S/A/B/C/F)을 매기고,
결과를 **MySQL 데이터베이스에 저장**하는 웹 대시보드입니다.

공공데이터 등 AI 학습용 데이터의 품질을 진단하는 것을 목표로 합니다.

```
┌────────────┐   HTTP   ┌────────────┐   SQLAlchemy   ┌────────┐
│ Streamlit  │ ───────> │  FastAPI   │ ─────────────> │ MySQL  │
│  (화면/UI)  │ <─────── │  (서버)     │ <───────────── │  (DB)   │
└────────────┘  JSON    └────────────┘                └────────┘
   :8501                    :8000                       :3306
```

- **Streamlit**: 사용자가 보는 화면 (파일 업로드, 차트, 결과)
- **FastAPI**: 진단 로직을 수행하는 서버
- **MySQL**: 진단 결과를 영구 저장하는 데이터베이스

---

## 📐 5대 품질 지표

| 지표 | 가중치 | 측정 방법 |
|---|:---:|---|
| **완전성 (Completeness)** | 30% | 결측치(빈 칸) 비율 |
| **유효성 (Validity)**      | 25% | 타입 오류 (숫자 칸에 문자 등) |
| **일관성 (Consistency)**   | 20% | 형식 통일성 (공백, 대소문자, 날짜 구분자) |
| **이상치 (Accuracy)**      | 15% | **IQR + Z-Score + Isolation Forest 다수결** |
| **중복성 (Uniqueness)**    | 10% | 중복 행 비율 |

**종합점수 = Σ(각 지표 점수 × 가중치)** → 가중치는 화면에서 조절 가능

## 🏆 AI-Ready 등급

| 등급 | 점수 | 의미 |
|:---:|:---:|---|
| **S** | 97점 이상 | 즉시 학습 가능 |
| **A** | 90 ~ 97점 | 우수 |
| **B** | 80 ~ 90점 | 경미한 보완 필요 |
| **C** | 70 ~ 80점 | 전처리 필요 |
| **F** | 70점 미만 | 학습 부적합 |

---

## 🚀 설치 및 실행 (처음 하는 경우)

### STEP 0. 사전 준비물
- Python 3.10+ (Anaconda 권장)
- **MySQL 8.0** 설치 + MySQL Workbench
- MySQL root 비밀번호를 알고 있어야 함

### STEP 1. 패키지 설치
프로젝트 폴더(`data_quality_app`)에서 터미널 열고:
```bash
pip install -r requirements.txt
```

### STEP 2. MySQL 데이터베이스 생성
**MySQL Workbench**를 열고, `init_db.sql` 파일 내용을 복사해서 실행합니다.
(또는 터미널에서 `mysql -u root -p < init_db.sql`)

이러면 `data_quality_db` 데이터베이스와 `diagnosis_history` 테이블이 만들어집니다.

> ⚠️ `init_db.sql`에는 `DROP TABLE`이 있어 **재실행 시 기존 진단 기록이 삭제**됩니다.
> 처음 설치할 때만 실행하세요.

### STEP 3. 환경변수 설정
`.env.example` 파일을 복사해서 `.env` 파일을 만듭니다:
```bash
# Windows
copy .env.example .env
# Mac/Linux
cp .env.example .env
```
그리고 `.env` 파일을 열어 **MYSQL_PASSWORD를 본인 MySQL 비밀번호로** 수정하세요.

### STEP 4. 백엔드(FastAPI) 실행 — 터미널 ①
```bash
uvicorn backend.main:app --reload --port 8000
```
- 성공 시: `Application startup complete.` 표시
- 확인: 브라우저에서 http://localhost:8000/docs (API 문서가 보이면 OK)

### STEP 5. 프론트엔드(Streamlit) 실행 — 터미널 ② (새 창)
```bash
streamlit run frontend/app.py
```
- 브라우저에서 http://localhost:8501 자동 열림
- 사이드바에 🟢 **API 서버 정상** 표시되면 성공

> 💡 **터미널 2개**가 동시에 켜져 있어야 합니다. 백엔드를 먼저 실행하세요.

---

## ⏹️ 종료 방법

1. **터미널 2개** 각각 클릭 후 `Ctrl + C` (또는 VS Code 통째로 닫기)
2. **브라우저 탭** 닫기
3. **MySQL은 끌 필요 없음** — Windows 백그라운드 서비스로 자동 실행됨

> 진단 결과는 MySQL에 영구 저장되므로, 프로그램을 꺼도 데이터는 사라지지 않습니다.

## 🔁 재시작 방법 (2번째부터)

> ⚠️ **`init_db.sql`을 다시 실행하지 마세요!**
> `DROP TABLE`이 포함돼 있어 그동안 저장된 진단 기록이 모두 삭제됩니다.
> 한 번 DB를 만든 뒤에는 아래 2개만 실행하면 됩니다.

```bash
# 터미널 ① — 백엔드
uvicorn backend.main:app --reload --port 8000

# 터미널 ② — 프론트엔드
streamlit run frontend/app.py
```

→ 브라우저에서 http://localhost:8501 접속. 이전 진단 기록도 그대로 남아있습니다.

## 👥 팀원에게 공유할 때

DB는 컴퓨터마다 따로 존재하므로, **팀원은 자기 컴퓨터에서 처음 설치(STEP 1~5)를 모두 수행**해야 합니다.

| 항목 | 주의사항 |
|---|---|
| MySQL | 팀원 컴퓨터에 **MySQL 8.0 먼저 설치** 필요 |
| `init_db.sql` | 팀원은 **처음이니 반드시 실행** (없으면 작동 안 함) |
| `.env` | **본인 MySQL 비밀번호**로 수정 (내 비번 X) |
| 압축 공유 시 | `.streamlit/`, `.env.example` 등 **숨김 파일 누락 주의** / `.env`는 제외 |

---

## 📁 프로젝트 구조

```
data_quality_app/
│
├── .streamlit/
│   └── config.toml                  # 업로드 한도 2GB, 다크 테마 설정
│
├── backend/                         # FastAPI 서버 (포트 8000)
│   ├── main.py                      # 서버 진입점
│   ├── config.py                    # 환경변수(.env) 로드
│   ├── api/
│   │   └── routes.py                # API 엔드포인트 정의
│   ├── db/
│   │   ├── database.py              # MySQL 연결 설정
│   │   ├── models.py                # 테이블 구조 정의 (ORM)
│   │   └── crud.py                  # DB 저장/조회/삭제 함수
│   ├── schemas/
│   │   └── diagnosis.py             # 데이터 형식 정의 (Pydantic)
│   └── services/                    # 핵심 진단 로직
│       ├── diagnosis_service.py     # 전체 진단 흐름 조율
│       ├── quality_checker.py       # 5대 지표 진단
│       ├── quality_score.py         # 점수/등급 계산
│       └── summary_generator.py     # AI 요약문 생성
│
├── frontend/                        # Streamlit 화면 (포트 8501)
│   ├── app.py                       # 화면 진입점
│   ├── utils/
│   │   └── api_client.py            # 백엔드 호출 담당
│   └── visualization/
│       └── charts.py                # Plotly 차트 (레이더 등)
│
├── requirements.txt                 # 설치할 패키지 목록
├── .env.example                     # 환경변수 템플릿
├── init_db.sql                      # DB 생성 스크립트
└── README.md
```

---

## 🖥️ 화면 구성

### 진단 실행 (5개 탭)
1. **📌 개요 & 종합** — 종합 점수, 등급, KPI 카드, AI 요약
2. **🎯 5대 지표 상세** — 지표별 점수, 레이더 차트
3. **📈 시각화** — 결측/이상치/문제유형 차트, 알고리즘 비교
4. **🔍 컬럼 Drill-down** — 컬럼별 상세 분석
5. **⚠️ 데이터 이슈** — 타입 오류, 종합 요약 테이블

### 진단 이력 (DB 조회) — 3개 탭
1. **📊 이력 요약** — 저장된 진단들의 점수 추이
2. **📋 전체 목록** — MySQL에 저장된 모든 진단 기록
3. **🗑️ 이력 관리** — 기록 삭제

> 💡 진단할 때마다 결과가 자동으로 MySQL에 저장됩니다.
> "진단 이력 (DB)" 메뉴에서 저장된 데이터를 표로 확인할 수 있습니다.

---

## 🗄️ 저장되는 데이터 (diagnosis_history 테이블)

진단 1건당 아래 14개 항목이 한 줄로 저장됩니다.

| 컬럼 | 설명 |
|---|---|
| id | 진단 번호 (자동 증가) |
| filename | 업로드한 파일명 |
| checked_at | 진단한 시각 |
| total_rows | 전체 행 수 |
| missing_count | 결측치 개수 |
| duplicate_count | 중복 행 개수 |
| outlier_count | 이상치 개수 |
| completeness_score | 완전성 점수 |
| validity_score | 유효성 점수 |
| consistency_score | 일관성 점수 |
| accuracy_score | 이상치 점수 |
| uniqueness_score | 중복성 점수 |
| quality_score | 종합 점수 |
| grade | 등급 (S/A/B/C/F) |

**MySQL Workbench에서 직접 보려면:**
```sql
USE data_quality_db;
SELECT * FROM diagnosis_history;
```

---

## 🔌 REST API

| 메서드 | 경로 | 설명 |
|------|------|-----|
| POST   | `/api/diagnose`       | CSV/Excel 업로드 + 진단 + DB 저장 |
| GET    | `/api/history`        | 진단 이력 전체 조회 |
| GET    | `/api/history/{id}`   | 진단 이력 단건 조회 |
| DELETE | `/api/history/{id}`   | 진단 이력 삭제 |
| GET    | `/api/health`         | 서버 상태 확인 |

API 문서(Swagger): http://localhost:8000/docs

---

## 🛠️ 자주 발생하는 문제

| 증상 | 해결 |
|------|------|
| `ModuleNotFoundError: No module named 'frontend'` | 프로젝트 루트(`data_quality_app/`)에서 실행하세요 |
| `ModuleNotFoundError: sklearn` | `pip install scikit-learn` |
| `Access denied for user 'root'` | `.env`의 MYSQL_PASSWORD 확인 |
| 🔴 API 서버 연결 실패 | 백엔드(터미널 ①)를 먼저 실행했는지 확인 |
| 500 Server Error | DB 테이블이 없거나 컬럼 부족 → `init_db.sql` 재실행 |
| 카드에 `</div>` 표시됨 | `frontend/app.py`를 최신본으로 교체 |
| 업로드 여전히 200MB | `.streamlit/config.toml`이 프로젝트 루트에 있는지 확인 후 재시작 |
| 대용량 파일 진단이 느림 | 정상 (Isolation Forest 학습). 수십만 행은 수십 초 소요 |
| 한글 CSV 깨짐 | UTF-8로 저장하거나 CP949 자동 감지에 의존 |

---

## ⚙️ 주요 설정

- **업로드 한도**: 200MB (`.streamlit/config.toml`에서 `maxUploadSize` 조정)
- **가중치**: 화면 사이드바 슬라이더로 조절 (기본 30/25/20/15/10)
- **이상치 판정**: 3개 알고리즘 중 2개 이상이 이상치로 판정한 경우만 최종 이상치

## 📚 기술 스택

- **Backend**: FastAPI, SQLAlchemy, PyMySQL
- **ML**: scikit-learn (Isolation Forest)
- **Data**: pandas, NumPy
- **DB**: MySQL 8.0
- **Frontend**: Streamlit, Plotly

---

## 🔮 향후 확장 (수 GB급 대용량 대응 시)

현재는 파일을 통째로 메모리에 올려 처리합니다. 수백만~수천만 행의 초대용량
데이터를 다룰 경우 아래 방식이 추가로 필요합니다.

- CSV 청크 단위 읽기 (`pd.read_csv(chunksize=...)`)
- 데이터를 DB에 먼저 적재 후 쿼리 기반 분석
- 진단 결과 PDF/Excel 리포트 다운로드 기능
