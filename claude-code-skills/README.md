# Claude Code Skills 실습

Claude Code의 Skills 기능을 직접 만들어보며 익힌 실습 기록. 설치부터 스킬 생성, 확인, 테스트, 개선까지 전체 흐름을 실제로 따라가봤다.

## 1단계 — skill-creator 플러그인 설치

VSCode 확장(Claude Code) 안에서는 `/plugin`, `/plugins` 명령이 아예 지원되지 않아서, 표준 터미널 CLI로 옮겨서 진행했다.

**터미널에 Claude Code 네이티브 설치** (Node/npm 불필요):

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

설치 직후 `claude: command not found`가 났는데, `~/.local/bin`이 PATH에 없어서였다. 아래로 해결:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

이후 `claude --version`으로 설치 확인, `playground` 폴더에서 `claude` 실행 → `/plugin` 명령으로 marketplace를 통해 skill-creator 설치 완료 (`.claude/settings.json`의 `enabledPlugins`에 `skill-creator@claude-plugins-official` 등록됨).

## 2단계 — 구조 이해용 연습: `playground-log` 스킬

skill-creator를 실제로 쓰기 전에, SKILL.md 구조가 뭔지 감을 잡기 위해 간단한 스킬을 하나 먼저 설계해봤다.

- **목적**: 이 playground 저장소에 새 실험을 시작할 때, 실험 폴더 생성 + 루트 `README.md`의 실험 목록 표 갱신을 자동화
- **트리거 표현**: "새 실험 시작해줘", "실험 목록에 추가해줘", "실험 기록해줘"
- 위치: `playground/.claude/skills/playground-log/SKILL.md`

> 스킬은 `.claude/skills/`가 있는 위치를 "프로젝트 루트"로 인식해서 동작한다. `playground-log`는 저장소 전체에서 작동해야 하므로, 개별 실험 폴더가 아니라 **playground 루트**의 `.claude/skills/`에 위치시켰다.

## 3단계 — 실전 스킬 제작: `meeting-minutes`

처음엔 견적서 자동 생성 스킬로 시도해보려 했는데, 마침 갖고 있던 회의록 예시 파일(`reference/회의록_예시.docx`)을 참고 자료로 쓸 수 있어서 **회의록 자동 정리 스킬**로 방향을 바꿔 진행했다.

### skill-creator 호출 프롬프트

```
/skill-creator 회의록 초안을 자동 정리하는 스킬을 만들어줘.

- 회의 중 나온 대화/메모를 입력하면 정형화된 회의록으로 정리해야 해
- 상단에 회의 정보(제목, 일시, 장소, 작성자, 참석자, 불참자, 안건) 포함
- 안건별로 발표자와 논의 내용을 불릿으로 정리
- 결정 사항 및 액션 아이템을 표(할 일 / 담당자 / 기한 / 상태)로 정리
- 마지막에 다음 회의 일정 포함
- 자체 검증 체크리스트 포함 (액션 아이템에 담당자·기한 누락 없는지 확인)
- "회의록 정리해줘", "회의록 작성해줘" 같은 요청에 자동 트리거

레퍼런스로 이 파일을 참고해서 만들어줘:
@claude-code-skills/reference/회의록_예시.docx

스킬 제작이후 eval test도 진행해줘.
```

이 요청 하나로 skill-creator가 아래를 한 번에 생성했다:

```
.claude/skills/meeting-minutes/
├── SKILL.md              ← 핵심 매뉴얼
├── scripts/
│   └── build_docx.py     ← 표/색상/서식 처리해서 .docx로 만드는 스크립트
└── evals/
    └── evals.json         ← eval 테스트 케이스 정의
```

## 4단계 — 생성된 SKILL.md 확인 (3계층 구조)

| 계층 | 내용 | 확인 결과 |
|---|---|---|
| 1계층 (frontmatter) | `name`, `description` | "회의록 정리해줘", "이 메모를 회의록으로 만들어줘" 등 실제 쓸 법한 트리거 표현이 다수 포함됨 |
| 2계층 (본문) | 입력 처리 규칙, 안건/결정사항 구분 기준, 작업 순서, 자체 검증 체크리스트 | 녹취록·슬랙 캡처·손메모처럼 지저분한 입력도 추론해서 채우는 규칙까지 포함 |
| 3계층 (부속자료) | `scripts/build_docx.py`, `evals/evals.json` | 필요할 때만 온디맨드로 로딩 |

## 5단계 — eval 테스트 결과 확인

skill-creator가 스킬 생성 직후 자체적으로 "스킬 적용 전 vs 후" 벤치마크를 돌렸고, 결과는 `meeting-minutes-workspace/iteration-1/benchmark.md`에 저장됐다.

> `meeting-minutes-workspace/`는 실제 스킬이 아니라, skill-creator가 만들고 테스트하는 동안 쓴 **작업용 임시 폴더**다 (벤치마크 결과, 케이스별 실행 로그 등).

| 지표 | 스킬 사용 | 스킬 미사용 | 차이 |
|---|---|---|---|
| Pass Rate | 100% ± 0% | 76% ± 8% | +24%p |
| 소요 시간 | 98.6s ± 25.5s | 37.1s ± 7.2s | +61.5s |
| 토큰 사용 | 33,843 ± 2,901 | 24,754 ± 1,296 | +9,089 |

**발견된 실패 패턴**:
1. 스킬 없이는 회의 정보 6필드 표가 자꾸 깨지고, 액션 아이템 누락을 체크리스트 없이 산문으로 뭉개는 경향이 있었다.
2. `messy-slack-transcript` 케이스에서, 담당자가 불분명한 항목("스크럼 시간 변경 건")에 스킬이 원문에 없는 "전체 팀원(지현 취합)"이라는 담당자를 **지어내고**, 체크리스트에는 담당자 항목을 ✅(통과)로 표시해버렸다. SKILL.md에 "담당자를 지어내지 말라"는 규칙이 이미 있었는데도 걸러지지 않은 케이스.

## 6단계 — 버그 수정을 SKILL.md에 반영

발견된 문제(②)를 다음 실행부터 재발하지 않도록 SKILL.md의 자체 검증 절차를 수정했다.

- **전**: "담당자가 지정되어 있는가?"만 체크 → 표에 아무 값이나 채워져 있으면 통과로 오인
- **후**: "담당자 지정"의 기준을 "원문에 실제로 등장하거나 문맥상 1인으로 명확히 좁혀지는 경우"로 명시하고, "전체 팀원", "해당 팀" 같은 그럴듯한 대표 표현으로 얼버무리는 것을 **명시적으로 금지**하는 문구를 추가. 애매하면 예외 없이 `owner: "미정"` + 체크리스트 ⚠️ 표시.

## 배운 점

- skill-creator가 만든 SKILL.md는 3계층(description → 본문 절차 → scripts/evals 부속자료) 구조를 그대로 따른다.
- `.claude/skills/`는 그 폴더가 있는 위치를 프로젝트 루트로 인식하므로, 저장소 전체에서 동작해야 하는 스킬은 하위 실험 폴더가 아니라 저장소 루트에 둬야 한다.
- eval 테스트는 실제로 유용한 버그를 잡아냈다: "값이 채워져 있는가"와 "그 값이 원문에 실제로 근거하는가"는 다른 기준이라, 검증 규칙에는 반드시 후자까지 명시해야 한다.
- 스킬 사용 시 정확도는 올라가지만(76%→100%) 속도/토큰 비용은 늘어난다(약 2.7배) — 결과물의 일관성이 중요한 작업일수록 이 트레이드오프가 합리적이다.
- Claude Code 실행 환경에 따라 사용 가능한 명령이 다르다: VSCode 확장에서는 `/plugin` 계열 명령이 지원되지 않아 표준 터미널 CLI가 필요했다.
