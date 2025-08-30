FROM python:3.11-slim

# 메타데이터 설정
LABEL maintainer="AI Code Review Bot"
LABEL description="AI-powered code review bot with CLI and Web Dashboard"
LABEL version="2.0.0"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry==1.6.1

# Poetry 설정
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# 프로젝트 파일 복사
COPY pyproject.toml poetry.lock* ./

# 의존성 설치 (개발 의존성 제외)
RUN poetry install --without dev && rm -rf $POETRY_CACHE_DIR

# 소스 코드 복사
COPY . .

# 프로젝트 설치
RUN poetry install --without dev

# 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# 포트 노출 (웹 대시보드용)
EXPOSE 8000

# 볼륨 설정 (작업 디렉토리 마운트용)
VOLUME ["/workspace"]

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 기본 명령어
CMD ["poetry", "run", "review-bot", "dashboard", "--host", "0.0.0.0", "--port", "8000"]

# 사용 예시:
# docker build -t review-bot .
# docker run -p 8000:8000 -v $(pwd):/workspace -e ANTHROPIC_API_KEY=your_key review-bot