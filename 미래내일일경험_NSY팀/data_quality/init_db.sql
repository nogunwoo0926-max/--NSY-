-- ====================================================
-- 데이터 품질 진단 시스템 - MySQL 초기 스크립트 (v2: 5대 지표)
-- ====================================================
-- 사용법 (MySQL Workbench 또는 CLI):
--   이 파일 전체를 실행하면 DB와 테이블이 생성됩니다.
--   CLI: mysql -u root -p < init_db.sql
--
-- ⚠️ 주의: DROP TABLE 이 포함되어 있어 기존 진단 이력은 모두 삭제됩니다.
--          처음 설치하거나, 깨끗하게 다시 만들 때 사용하세요.
-- ====================================================

CREATE DATABASE IF NOT EXISTS data_quality_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE data_quality_db;

-- 기존 테이블 삭제 후 재생성 (컬럼 충돌 방지)
-- DROP TABLE IF EXISTS diagnosis_history;

CREATE TABLE diagnosis_history (
    id                 INT AUTO_INCREMENT PRIMARY KEY              COMMENT '진단 ID',
    filename           VARCHAR(255)  NOT NULL                      COMMENT '업로드 CSV/Excel 파일명',
    checked_at         DATETIME      NOT NULL                      COMMENT '진단 수행 시각',
    total_rows         BIGINT        NOT NULL                      COMMENT '전체 행 수',
    missing_count      BIGINT        NOT NULL DEFAULT 0            COMMENT '결측치 총 개수',
    duplicate_count    BIGINT        NOT NULL DEFAULT 0            COMMENT '중복 행 개수',
    outlier_count      BIGINT        NOT NULL DEFAULT 0            COMMENT '이상치 총 개수 (앙상블)',

    -- 5대 지표 점수 (0~100)
    completeness_score FLOAT         NOT NULL DEFAULT 0            COMMENT '완전성 점수',
    validity_score     FLOAT         NOT NULL DEFAULT 0            COMMENT '유효성 점수',
    consistency_score  FLOAT         NOT NULL DEFAULT 0            COMMENT '일관성 점수',
    accuracy_score     FLOAT         NOT NULL DEFAULT 0            COMMENT '이상치(정확성) 점수',
    uniqueness_score   FLOAT         NOT NULL DEFAULT 0            COMMENT '중복성(유일성) 점수',

    -- 종합
    quality_score      FLOAT         NOT NULL                      COMMENT '종합 품질 점수 (0~100)',
    grade              VARCHAR(2)    NOT NULL                      COMMENT 'AI-Ready 등급 (S/A/B/C/F)',

    INDEX idx_checked_at (checked_at),
    INDEX idx_grade (grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 확인용
DESCRIBE diagnosis_history;
