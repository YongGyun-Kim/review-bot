# 프로젝트에서 AI 코드 리뷰 봇 사용하기

## 🎯 프로젝트 설정 가이드

### 1. 프로젝트 루트에서 설정

```bash
# 개발 중인 프로젝트로 이동
cd /path/to/your/project

# 프로젝트별 설정 디렉토리 생성
mkdir -p .review-bot/prompts

# 프로젝트별 설정 파일 생성
cat > .review-bot/config.yaml << EOF
provider: claude
model: claude-3-5-sonnet-20241022
output_dir: reviews
max_files_per_review: 20
temperature: 0.1
auto_review:
  on_commit: false  # 원하는 경우 true로 설정
  on_push: false
file_filters:
  - "*.py"
  - "*.js"
  - "*.ts" 
  - "*.jsx"
  - "*.tsx"
  # 프로젝트에 맞게 수정
EOF
```

### 2. 프로젝트별 커스텀 프롬프트 생성

```bash
# 프로젝트 특화 리뷰 프롬프트 생성
cat > .review-bot/prompts/project-specific.md << 'EOF'
---
description: "우리 프로젝트 전용 코드 리뷰"
author: "개발팀"
---

# 프로젝트 코드 리뷰

다음 코드 변경사항을 우리 프로젝트 컨텍스트에서 검토해주세요:

{{ code_diff }}

## 우리 프로젝트 특별 요구사항

### 🔍 코딩 스타일
- ESLint/Prettier 규칙 준수
- TypeScript strict 모드 준수
- 함수형 프로그래밍 스타일 선호
- React Hooks 패턴 사용

### 🛡️ 보안 체크포인트
- API 키나 민감정보 하드코딩 금지
- 사용자 입력 검증 필수
- SQL 인젝션 방지

### ⚡ 성능 고려사항
- 불필요한 리렌더링 방지
- 메모리 누수 체크
- 번들 사이즈 최적화

### 📚 문서화
- JSDoc 주석 작성
- README 업데이트 필요 여부
- API 문서 반영

## 변경 요약
- 브랜치: {{ branch }}
- 파일 수: {{ files_changed }}
- 추가 라인: {{ lines_added }}
- 삭제 라인: {{ lines_deleted }}

변경된 파일들:
{% for file in files_list %}
- {{ file }}
{% endfor %}

피드백은 구체적이고 실행 가능한 조언으로 부탁드립니다.
EOF

# 보안 중심 프롬프트
cat > .review-bot/prompts/security.md << 'EOF'
---
description: "보안 취약점 중심 리뷰"
author: "보안팀"
---

# 🔒 보안 코드 리뷰

{{ code_diff }}

## 보안 체크리스트

### 인증 및 인가
- [ ] 인증 토큰 검증
- [ ] 권한 확인 로직
- [ ] 세션 관리

### 입력 검증
- [ ] 사용자 입력 sanitization
- [ ] SQL 인젝션 방지
- [ ] XSS 방지

### 데이터 보안
- [ ] 민감정보 암호화
- [ ] 로그에 민감정보 노출 방지
- [ ] API 키 하드코딩 방지

심각도별 분류하여 피드백 부탁드립니다.
EOF
```

### 3. Git 훅 설정 (선택사항)

```bash
# 프로젝트에 Git 훅 설치
review-bot hooks install

# 커밋 시 자동 리뷰 활성화
review-bot config set auto_review.on_commit true

# 특정 브랜치에서만 자동 리뷰 (선택사항)
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# 현재 브랜치 확인
current_branch=$(git branch --show-current)

# main, master, develop 브랜치에서는 리뷰 필수
if [[ "$current_branch" =~ ^(main|master|develop)$ ]]; then
    echo "🤖 코드 리뷰 실행 중..."
    review-bot run --staged --format json > /tmp/review-result.json
    
    if [ $? -ne 0 ]; then
        echo "❌ 코드 리뷰에서 심각한 문제가 발견되었습니다."
        echo "커밋을 진행하시겠습니까? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ 코드 리뷰 완료"
    fi
fi
EOF

chmod +x .git/hooks/pre-commit
```

### 4. 팀 워크플로우 통합

#### package.json에 스크립트 추가 (Node.js 프로젝트)
```json
{
  "scripts": {
    "review": "review-bot run --staged",
    "review:security": "review-bot run --prompt security",
    "review:commit": "review-bot run --commit HEAD~1",
    "pre-commit": "npm run lint && npm run test && review-bot run --staged"
  }
}
```

#### Makefile 추가 (Python/기타 프로젝트)
```makefile
.PHONY: review review-security review-staged

review:
	review-bot run

review-security:
	review-bot run --prompt security

review-staged:
	review-bot run --staged

pre-commit: lint test review-staged
	@echo "✅ 모든 체크 통과"
```

### 5. CI/CD 통합

#### GitHub Actions 워크플로우
```yaml
# .github/workflows/code-review.yml
name: AI Code Review

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Review Bot
      run: |
        curl -sSL https://raw.githubusercontent.com/your-username/code-review-bot/main/install.sh | bash
        export PATH="$PATH:$HOME/.local/bin"
    
    - name: Run AI Code Review
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        review-bot run --staged --format json > review-result.json
        
    - name: Comment PR
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const review = JSON.parse(fs.readFileSync('review-result.json', 'utf8'));
          
          const comment = `## 🤖 AI 코드 리뷰 결과
          
          ${review.review}
          
          **리뷰 정보:**
          - 제공자: ${review.provider}
          - 토큰 사용량: ${review.tokens_used}
          - 예상 비용: $${review.estimated_cost}
          `;
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### 6. 일상적인 사용법

#### 개발 워크플로우에 통합
```bash
# 1. 코드 작성
git add .

# 2. 리뷰 실행
review-bot run --staged

# 3. 리뷰 결과 확인 후 필요시 수정
# reviews/ 디렉토리에서 결과 확인

# 4. 최종 커밋
git commit -m "feat: 새 기능 추가"

# 5. TODO 항목 확인
review-bot todo list

# 6. 웹 대시보드로 종합 확인
review-bot dashboard
```

#### 정기적인 코드베이스 리뷰
```bash
# 지난 주 변경사항 리뷰
git log --since="1 week ago" --pretty=format:"%h" | while read commit; do
    review-bot run --commit $commit --prompt security
done

# 특정 파일들만 리뷰
review-bot run --file-filters "src/**/*.py" "tests/**/*.py"
```

### 7. 팀 설정 공유

#### 프로젝트에 설정 파일 커밋
```bash
# 팀원들과 공유할 설정들을 Git에 추가
git add .review-bot/
git commit -m "chore: AI 코드 리뷰 봇 설정 추가"

# .gitignore에 개인 설정은 제외
echo "/.review-bot/config.yaml" >> .gitignore
echo "/reviews/*.json" >> .gitignore
```

#### 팀 가이드 문서 작성
```markdown
# 팀 코드 리뷰 가이드

## AI 리뷰 봇 사용법

1. **설치**: `curl -sSL ... | bash`
2. **API 키 설정**: 개인 Slack에서 확인
3. **사용법**: 
   - 일반 리뷰: `npm run review`
   - 보안 리뷰: `npm run review:security`
4. **PR 전 필수**: 스테이징 리뷰 실행

## 리뷰 기준

- Critical/Major 이슈는 반드시 수정
- Minor 이슈는 판단에 따라 수정
- 보안 관련 이슈는 무조건 수정
```

### 8. 모니터링 및 분석

```bash
# 리뷰 통계 확인
review-bot todo progress

# 비용 분석
find reviews/ -name "*.json" -exec jq '.estimated_cost' {} + | awk '{sum+=$1} END {print "Total cost: $"sum}'

# 가장 많이 리뷰된 파일 분석
find reviews/ -name "*.json" -exec jq -r '.files_reviewed[]' {} + | sort | uniq -c | sort -nr
```

이제 개발 중인 프로젝트에서 AI 코드 리뷰 봇을 체계적으로 활용할 수 있습니다! 🚀