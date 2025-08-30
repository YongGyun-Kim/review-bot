#!/bin/bash

# AI 코드 리뷰 봇 설치 스크립트
# 사용법: curl -sSL https://raw.githubusercontent.com/your-username/code-review-bot/main/install.sh | bash

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
echo -e "${BLUE}"
echo "🤖 AI 코드 리뷰 봇 설치 스크립트"
echo "=================================="
echo -e "${NC}"

# 함수 정의
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 확인
log_info "시스템 요구사항 확인 중..."

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    log_error "Python 3이 설치되어 있지 않습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
REQUIRED_VERSION="3.11"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    log_success "Python $PYTHON_VERSION 감지됨"
else
    log_error "Python 3.11+ 가 필요합니다. 현재 버전: $PYTHON_VERSION"
    exit 1
fi

# Git 확인
if ! command -v git &> /dev/null; then
    log_error "Git이 설치되어 있지 않습니다."
    exit 1
fi
log_success "Git 설치 확인됨"

# 설치 디렉토리 설정
INSTALL_DIR="$HOME/.local/share/review-bot"
BIN_DIR="$HOME/.local/bin"

# 기존 설치 확인
if [ -d "$INSTALL_DIR" ]; then
    log_warning "기존 설치가 발견되었습니다. 업데이트 중..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    log_info "저장소 클론 중..."
    mkdir -p "$HOME/.local/share"
    git clone https://github.com/your-username/code-review-bot.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Poetry 확인 및 설치
if command -v poetry &> /dev/null; then
    log_success "Poetry 설치 확인됨"
else
    log_info "Poetry 설치 중..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# 의존성 설치
log_info "의존성 설치 중..."
poetry install --without dev

# 실행 스크립트 생성
log_info "실행 스크립트 생성 중..."
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/review-bot" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$HOME/.local/share/review-bot"
cd "$SCRIPT_DIR"
poetry run python -m cli.main "$@"
EOF

chmod +x "$BIN_DIR/review-bot"

# PATH 설정 확인
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    log_warning "PATH에 $BIN_DIR 추가 필요"
    
    # 셸에 따라 적절한 RC 파일 선택
    if [[ $SHELL == *"zsh"* ]]; then
        RC_FILE="$HOME/.zshrc"
    elif [[ $SHELL == *"bash"* ]]; then
        RC_FILE="$HOME/.bashrc"
    else
        RC_FILE="$HOME/.profile"
    fi
    
    echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$RC_FILE"
    export PATH="$PATH:$BIN_DIR"
    log_info "PATH가 $RC_FILE에 추가되었습니다."
fi

# 설치 완료
log_success "설치가 완료되었습니다!"
echo ""
echo -e "${GREEN}사용법:${NC}"
echo "  1. 새 터미널을 열거나 다음 명령어 실행:"
echo "     source ~/.zshrc  (또는 ~/.bashrc)"
echo ""
echo "  2. 설정 초기화:"
echo "     review-bot config init"
echo ""
echo "  3. API 키 설정:"
echo "     review-bot config set provider claude"
echo "     review-bot config set api_key YOUR_API_KEY"
echo ""
echo "  4. 첫 리뷰 실행:"
echo "     review-bot run"
echo ""
echo -e "${YELLOW}추가 정보:${NC}"
echo "  - 설치 위치: $INSTALL_DIR"
echo "  - 설정 위치: ~/.review-bot/"
echo "  - 문서: https://github.com/your-username/code-review-bot"
echo ""
log_success "즐거운 코드 리뷰 되세요! 🚀"