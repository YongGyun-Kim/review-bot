# 🚀 Review Bot v2.0 Development Plan

## 📊 Progress Overview

### ✅ Completed Tasks
- [x] **Python 버전 새로 개발 계획 수립**
- [x] **Python 프로젝트 초기 설정 및 구조 설계** 
- [x] **Pydantic 모델 및 타입 정의**
- [x] **Git 관리 모듈 개발 (GitPython 기반)**
- [x] **AI 제공자 클래스 설계 및 구현**
- [x] **TypeScript 버전 아카이브화 및 프로젝트 구조 정리**
- [x] **설정 관리 시스템 개발**

### 🔄 Current Task
- [ ] **프롬프트 템플릿 엔진 개발** (In Progress)

### 📋 Remaining Tasks
- [ ] **리뷰 처리 및 결과 저장 시스템**
- [ ] **TODO 관리 시스템**
- [ ] **Rich 기반 CLI 인터페이스 개발**
- [ ] **FastAPI 기반 Web Dashboard 개발**
- [ ] **pytest 테스트 스위트 작성**
- [ ] **PyPI 패키지 설정 및 배포**

---

## 🎯 Detailed Task Breakdown

### 1. 프롬프트 템플릿 엔진 개발 (Current)

**목표**: Jinja2 기반의 유연한 프롬프트 템플릿 시스템

**구현 내용**:
- **PromptManager 클래스**: 템플릿 로드/저장/검증
- **템플릿 변수 시스템**: `{{code_diff}}`, `{{files_changed}}` 등
- **템플릿 검증**: 필수 변수 체크, 구문 오류 검증
- **동적 변수 지원**: Git 정보, 날짜/시간, 사용자 정보

**파일 구조**:
```
core/
├── prompt_manager.py     # 메인 템플릿 관리자
└── template_engine.py    # Jinja2 엔진 래퍼

prompts/
├── default.md           # 기본 리뷰 템플릿
├── security-focused.md  # 보안 중심 템플릿
└── performance-focused.md # 성능 중심 템플릿
```

**예상 소요시간**: 4-6시간

---

### 2. 리뷰 처리 및 결과 저장 시스템

**목표**: AI 리뷰 실행 및 결과 처리 통합 시스템

**구현 내용**:
- **ReviewManager 클래스**: 리뷰 실행 오케스트레이션
- **결과 포맷터**: Markdown, JSON, HTML 출력
- **파일 저장 시스템**: 날짜별/브랜치별 조직화
- **히스토리 관리**: 이전 리뷰와 비교 분석

**핵심 기능**:
- 비동기 리뷰 실행
- 에러 복구 및 재시도
- 진행 상황 실시간 표시
- 비용 추적 및 토큰 사용량 분석

**예상 소요시간**: 6-8시간

---

### 3. TODO 관리 시스템

**목표**: 리뷰 제안사항을 추적 가능한 작업으로 변환

**구현 내용**:
- **TodoManager 클래스**: TODO 생성/수정/완료 관리
- **우선순위 시스템**: High/Medium/Low 자동 분류
- **진행 추적**: 완료율, 소요시간 분석
- **알림 시스템**: 마감일 알림, 진행 상황 리포트

**데이터 구조**:
- JSON 기반 저장
- 태그 및 카테고리 지원
- 담당자 할당 기능
- 의존성 관리

**예상 소요시간**: 4-5시간

---

### 4. Rich 기반 CLI 인터페이스 개발

**목표**: 아름답고 직관적인 터미널 사용자 경험

**구현 내용**:
- **Typer + Rich 조합**: 타입 안전한 CLI
- **실시간 진행 표시**: 프로그레스 바, 스피너
- **테이블 형태 출력**: 리뷰 결과, TODO 목록
- **대화형 메뉴**: 설정, 선택지 처리

**주요 명령어**:
```bash
review-bot run [--staged] [--commit] [--prompt]
review-bot config [init|set|get] [--global]
review-bot todo [list|complete|delete] [--priority]
review-bot hooks [install|uninstall]
review-bot dashboard [--port] [--host]
review-bot status
```

**UI 개선사항**:
- 색상 코딩으로 심각도 표시
- 트리 구조로 파일 변경사항 표시
- 라이브 로그 스트리밍
- 키보드 단축키 지원

**예상 소요시간**: 6-7시간

---

### 5. FastAPI 기반 Web Dashboard 개발

**목표**: 웹 기반 리뷰 관리 및 모니터링 대시보드

**구현 내용**:

#### 5.1 Backend API (FastAPI)
- **RESTful API**: 리뷰, TODO, 설정 관리
- **WebSocket**: 실시간 리뷰 진행 상황
- **인증 시스템**: JWT 기반 (선택적)
- **파일 업로드**: 대용량 리뷰 결과 처리

#### 5.2 Frontend (HTML/JS + Tailwind CSS)
- **대시보드 페이지**: 리뷰 통계, 진행 상황
- **리뷰 히스토리**: 필터링, 검색, 정렬
- **TODO 관리**: 칸반 보드 스타일 인터페이스
- **설정 페이지**: 프로바이더, 프롬프트 관리

#### 5.3 주요 페이지
```
/                    # 대시보드 홈
/reviews            # 리뷰 히스토리
/todos              # TODO 관리
/settings           # 설정
/api/docs          # API 문서 (Swagger)
```

#### 5.4 실시간 기능
- 리뷰 실행 중 진행률 표시
- 새 TODO 알림
- 리뷰 완료 알림

**기술 스택**:
- Backend: FastAPI + SQLite/PostgreSQL
- Frontend: Vanilla JS + Tailwind CSS
- 실시간: WebSocket + SSE
- 배포: Docker + Uvicorn

**예상 소요시간**: 12-15시간

---

### 6. pytest 테스트 스위트 작성

**목표**: 높은 품질과 안정성을 위한 종합적 테스트

**구현 내용**:

#### 6.1 Unit Tests
- **모든 클래스별 테스트**: Manager, Provider 클래스
- **모킹**: AI API 호출, Git 작업
- **에지 케이스**: 오류 상황, 경계값 테스트

#### 6.2 Integration Tests
- **전체 워크플로우**: 설정 → 리뷰 → 저장
- **AI 프로바이더 통합**: 실제 API 호출 (CI 환경)
- **파일 시스템**: 설정 파일, 리뷰 결과 저장

#### 6.3 E2E Tests
- **CLI 명령어**: 모든 주요 명령어 테스트
- **Web Dashboard**: Selenium/Playwright 기반

#### 6.4 성능 테스트
- **대용량 파일 처리**: 메모리 사용량, 처리 시간
- **동시 리뷰**: 여러 리뷰 동시 실행

**목표 커버리지**: 90%+

**예상 소요시간**: 8-10시간

---

### 7. PyPI 패키지 설정 및 배포

**목표**: 사용자가 쉽게 설치하고 사용할 수 있는 패키지 제작

**구현 내용**:

#### 7.1 패키지 최적화
- **의존성 정리**: 최소 필수 의존성만 포함
- **번들 크기 최적화**: 불필요한 파일 제외
- **플랫폼 호환성**: Windows, macOS, Linux 지원

#### 7.2 배포 자동화
- **GitHub Actions**: 자동 빌드 및 배포
- **버전 관리**: 자동 버전 태그, 릴리스 노트
- **품질 검증**: 테스트, 린팅, 보안 스캔

#### 7.3 문서 개선
- **README 업데이트**: Python 버전 정보 반영
- **CHANGELOG**: 버전별 변경사항
- **사용 가이드**: 설치부터 고급 사용까지

**배포 명령어**:
```bash
pip install code-review-bot
review-bot --help
```

**예상 소요시간**: 4-5시간

---

## 🎯 마일스톤 및 우선순위

### Phase 1: 핵심 기능 (현재 진행 중)
1. ✅ 프롬프트 템플릿 엔진
2. 🔄 리뷰 처리 시스템
3. 🔄 TODO 관리

### Phase 2: 사용자 인터페이스
4. 🔄 Rich CLI
5. 🔄 테스트 스위트

### Phase 3: 고급 기능
6. 🔄 Web Dashboard
7. 🔄 PyPI 배포

---

## 📅 예상 일정

**총 예상 소요시간**: 44-56시간
**예상 완료일**: 2-3주 (하루 4-6시간 작업 기준)

### 주간별 목표
- **1주차**: Phase 1 완료 (핵심 기능)
- **2주차**: Phase 2 완료 (UI + 테스트)
- **3주차**: Phase 3 완료 (Dashboard + 배포)

---

## 🚀 Next Steps

1. **프롬프트 템플릿 엔진 완료** - Jinja2 기반 구현
2. **기본 리뷰 플로우 구현** - 최소 동작하는 버전
3. **CLI 기본 명령어 구현** - `review-bot run` 명령
4. **점진적 기능 추가** - 우선순위에 따라 순차 구현

---

*Last updated: 2025-01-15*
*Version: 2.0.0-dev*