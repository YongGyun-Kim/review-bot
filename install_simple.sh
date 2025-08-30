#!/bin/bash

# 간단한 설치 스크립트 (Poetry 없이)
# 가상환경을 사용한 설치

set -e

echo "🤖 AI 코드 리뷰 봇 - 간단 설치"
echo "==============================="

# 설치 디렉토리
INSTALL_DIR="$HOME/review-bot"
BIN_DIR="$HOME/.local/bin"

# 저장소 클론
if [ -d "$INSTALL_DIR" ]; then
    echo "기존 설치 업데이트 중..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "저장소 클론 중..."
    git clone https://github.com/your-username/code-review-bot.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# 가상환경 생성
echo "가상환경 설정 중..."
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
echo "의존성 설치 중..."
pip install -r requirements.txt

# 패키지를 개발 모드로 설치
pip install -e .

# 실행 스크립트 생성
echo "실행 스크립트 생성 중..."
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/review-bot" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
cd "$INSTALL_DIR"
python -m cli.main "\$@"
EOF

chmod +x "$BIN_DIR/review-bot"

# PATH 추가 안내
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️  다음 명령어를 실행하여 PATH를 업데이트하세요:"
    echo "   export PATH=\"\$PATH:$BIN_DIR\""
    echo "   또는 ~/.zshrc (또는 ~/.bashrc)에 추가하세요"
fi

echo ""
echo "✅ 설치 완료!"
echo "사용법: review-bot --help"