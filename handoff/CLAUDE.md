# Research-to-Paper 프로토타입: 프로젝트 개요와 작업 안내

이 파일은 프로젝트의 목적과 계획 자료를 읽는 법을 안내한다. 상세 구현 범위와 데이터·동작 규칙은 `scope.json` 및 `contracts/`를 확인한다. 아래 경로는 이 파일과 `scope.json`이 함께 있는 계획팩 폴더를 기준으로 한다.

**작업 시작 안내는 이 파일 하나로 통일한다.** 이 지침을 읽고 `implementation_plan.md`의 미완료 항목부터 실제 구현·실행·검사를 진행한다. 계획 자료의 검사 결과와 웹 앱의 구현 상태는 `IMPLEMENTATION_STATUS.md`에서 구분해 확인한다.

## 기존 작업 폴더에 넣을 때

기존 `CLAUDE.md` 또는 `claude.md`의 지침을 보존하고 이 내용을 병합한다. 계획팩 전체를 프로젝트 루트에 놓으면 아래 상대 경로를 그대로 사용한다. 팩을 `prototype_handoff/` 같은 하위 폴더에 두고 안내만 루트 지침에 합치면, 안내의 파일 경로에도 해당 접두어를 붙인다.

기존 앱 코드·설정·진행 기록부터 확인하고 이어서 작업한다. 초기 TODO 표시를 근거로 이미 작성한 구현을 덮어쓰지 않는다. 새 작업 요청을 전달할 때는 다음 한 문장이면 된다.

```text
CLAUDE.md의 프로젝트 지침과 구현 계획을 읽고, 현재 코드와 진행 기록을 확인한 뒤 미완료 작업부터 구현·실행·검사해 줘.
```

## 프로젝트 요약

연구자가 아이디어를 입력하면 관련 연구 정리, 실험 설계, 코드 작성, 결과 분석, 영어 논문 초안 작성을 순서대로 지원하는 수업 과제용 웹 프로토타입이다. 각 단계의 AI 생성 결과를 사용자가 검토·수정·승인하며, 승인된 결과만 다음 단계의 입력으로 사용한다. 이번 구현은 로컬 단일 사용자 환경에서 승인·버전 연결·변경 영향·실험 결과 업로드가 실제로 작동하는지 확인하는 데 우선순위를 둔다.

- 제출일: **2026-11-08, Asia/Seoul**. 제출 시각은 지정되지 않았다.
- 원래 시스템의 요구사항은 SSRD, 원래 구조 설계는 SSAD에 있다. 계획팩은 그중 일부를 구현할 범위와 구체적인 작업을 정리한다.
- 계획팩 자체에는 완성된 웹 앱이 포함되어 있지 않다. 기존 작업 디렉터리에서 개발이 시작됐을 수 있으므로 현재 코드와 `IMPLEMENTATION_STATUS.md`를 먼저 확인하고 이어서 작업한다.
- UI는 한국어, S6 논문 초안은 영어다. UI/UX 팀의 기획안은 아직 전달되지 않은 상태이며 계획팩의 화면 배치는 임시 구현안이다.
- 지원 대상은 공개 데이터셋의 소규모 ML 비교 연구다. 이번은 외부 CPU/scikit-learn 실행을 연결한다. 원문의 예제 규모·제외 대상과 이번 축소의 차이는 `SOURCE_COVERAGE.md`에서 읽는다. 고객 가정 A-1~A-7은 검증 완료 사실로 다루지 않는다.

## 원문 정보 보완판을 기존 프로젝트에 적용

이번 팩은 `source-completion` 개정이다. 먼저 `SOURCE_COVERAGE.md`의 N-01~N-09 처리와 UI 대응·업로드 차이를 확인한다. 기존 코드가 있다면 아래 변경만 대조하고 이어서 작업한다. SSRD·SSAD 원본은 `sources/original/`에 있으며 바이트가 동일한 사본이다.

- S3에 ablation 계획 또는 해당 없음 사유와 모든 가설의 실험 대응을 확인한다.
- 기존 Decision/Artifact API로 승인 Brief 이력과 근거 원본을 읽기 전용으로 연다.
- 빈 근거 표시, 미검증 후보 제외 경고, 업로드 형식 차이를 화면에 안내한다.
- `LLM_DATA_POLICY.md`의 확인 상태를 사실대로 기록한다. 현재는 NOT_CHECKED다.

DB 테이블과 API 경로·요청·응답 형식은 이전 팩과 같다. SQLite·S1 Brief 갱신·back 이동·Markdown baseline도 유지한다. 모든 원문 기능을 새로 구현하지 않는다.

## 사용자가 거치는 여섯 단계

| 단계 | 사용자가 받는 결과 | 이번 구현의 범위 |
| --- | --- | --- |
| S1 | Research Brief와 확인 질문 | 연구 문제·가설·평가 계획·제약을 검토하고 승인한다. |
| S2 | 관련 연구 목록과 정리 | live에서는 arXiv에서 확인한 논문 1~3편을 초록 기반으로 정리한다. |
| S3 | 실험 계획 | 가설과 실험 ID, 필수 지표 이름을 연결한다. |
| S4 | 실행할 코드·설명서 zip | CPU Python 코드를 내보낸다. 사용자가 서비스 밖에서 실행한다. |
| S5 | 업로드한 결과의 분석 | 실험 결과 JSON을 검증·저장하고 지표를 분석한다. |
| S6 | 영어 논문 초안과 참고문헌 | 승인된 상위 결과로 여섯 섹션의 Markdown 초안과 BibTeX를 내보낸다. |

모든 단계에서 생성 결과 저장, 직접 수정, 코멘트를 포함한 재생성, 사용자 승인을 지원한다. 상위 결과의 새 버전을 승인하면 기존 하위 결과를 오래됨(stale)으로 표시한다. 오래된 결과와 입력 버전은 기록으로 보존한다.

## 처음 작업할 때 읽을 순서

1. `scope.json`: 이번에 구현할 것과 제외할 것을 확인한다. 원문 55개 요구사항 중 36개를 부분 구현 대상으로 선택했고 19개는 보류했다.
   `SOURCE_COVERAGE.md`에서 원문 배경·화면 ID·형식 차이와 N-01~N-09의 반영 범위를 함께 확인한다.
2. `requirements.selected.json`: 선택한 원문 요구사항과 이번 부분 구현의 연결을 확인한다. 원문 전체를 구현할 할 일 목록으로 해석하지 않는다.
3. `architecture.md`: 브라우저·API·내부 서비스·DB의 역할과 요청 처리 흐름을 읽는다.
4. `contracts/README.md`와 `contracts/workflow.json`: 승인·버전·업로드 검증·오래됨·중복 요청·재시작 규칙을 읽는다. 구현할 기능에 해당하는 schema/API 파일도 함께 확인한다.
5. `implementation_plan.md`: T01~T08의 구현 항목을 확인한다. 기존 코드와 진행 기록을 대조해 미완료 작업부터 이어서 수행한다.
6. `acceptance.md`와 `acceptance.cases.json`: 완료 조건과 시연 순서를 확인한다. live 단계 구현 시에는 `prompts/stage_prompts.md`도 읽는다.

처음부터 모든 원문을 LLM 프롬프트에 넣지 않는다. 필요한 작업의 계약과 단계별 프롬프트를 선택해 읽는다. 파일의 용도는 아래 표에, 배포 파일 전체 목록과 해시는 `manifest.json`에 있다.

## 무엇이 궁금할 때 어느 파일을 볼 것인가

| 확인할 내용 | 파일 |
| --- | --- |
| 이번에 구현할 기능과 제외 기능 | `scope.json` |
| 원문 누락 보완 내용·화면 ID 대응·업로드 차이 | `SOURCE_COVERAGE.md` |
| 원래 시스템 범위·고객 계층·A.II·A.III·용어 | `sources/ssrd_context.json` |
| LLM 입력 데이터 사용 조건을 확인했는가 | `LLM_DATA_POLICY.md` |
| SSRD의 어떤 요구사항에서 왔으며 어디까지 구현하는가 | `requirements.selected.json`의 원문 `fields`와 `prototype` 설명 |
| 실제 개발 TODO와 수정할 파일, 작업별 완료 기준 | `implementation_plan.md` |
| 내부 프로그램의 역할, 호출 흐름, 저장·화면 구성 | `architecture.md` |
| 승인·편집·재생성·back·오래됨·재시작 처리 | `contracts/workflow.json` 및 `contracts/README.md` |
| 저장할 테이블·관계·제약 | `contracts/database.sql` |
| 공통 Project·Stage·Artifact·Job 데이터 | `contracts/domain.schema.json` |
| S1~S6가 생성할 결과의 필드와 형식 | `contracts/artifacts.schema.json` |
| 실험 결과 업로드 파일의 필드와 형식 | `contracts/upload.schema.json` |
| API URL·메서드·요청·응답 | `contracts/api.openapi.json` |
| 실제 모델에 전달할 지시 | `prompts/stage_prompts.md` |
| API 키 없는 demo의 입력·사전 작성 결과 | `fixtures/` |
| 여섯 단계 demo의 개별 출력 | `fixtures/stages/s1.json`부터 `fixtures/stages/s6.json` |
| 정상 업로드와 오류 거부를 확인할 파일 | `fixtures/experiment_result.valid.json`, `fixtures/experiment_result.invalid.json` |
| 참조 측정값의 검사 기준 | `fixtures/expected_reference_metrics.json` |
| 외부에서 실제 실행할 작은 CPU 실험과 설치 패키지 | `reference_experiment/README.md`, `reference_experiment/train.py`, `reference_experiment/requirements.txt` |
| 구현 완료 판정과 시연 | `acceptance.md`, `acceptance.cases.json` |
| 실제 구현·검사 진행 상황 | `IMPLEMENTATION_STATUS.md`와 현재 코드 |
| 계획 자료에 대해 이미 수행한 검사와 재검사 | `IMPLEMENTATION_STATUS.md`, `scripts/check_handoff.py` |
| 원문 보존 규칙·전체 요구사항·SSAD 추출·기술 근거 | `SOURCE_COVERAGE.md`, `sources/requirements.all.json`, `sources/ssad_evidence.json`, `sources/external_references.json` |
| 환경 변수와 실행 설정 예시 | `.env.example` |

SQL은 저장 구조, JSON Schema는 데이터 형식, workflow는 처리 규칙, OpenAPI는 요청·응답 방법을 정한다. `contracts/README.md`에는 형식 검사만으로 확인할 수 없는 추가 규칙도 있다. 같은 기능을 여러 파일이 다른 관점에서 설명하는 것이므로 각각을 별개의 신규 기능으로 세지 않는다.

SSAD 원문을 확인할 때도 2.3은 행동, 2.4는 상태, 3.2는 담당 구성요소와 입출력, 3.3은 저장 데이터, 3.4는 실행 순서, 4장은 기술·인터페이스, 6장은 요구사항 연결, 7.1은 미결 사항으로 읽는다. `sources/ssad_evidence.json`은 텍스트 추출본이며 그림은 `sources/original/SSAD_v0.1.pdf`에서 확인한다. SSRD 전체는 `sources/original/SSRD_v0.1.docx`에 있다.

## SSAD와 별도로 둔 임시 baseline

| 설정 | 이번 프로토타입에서 적용할 내용 |
| --- | --- |
| SQLite | 별도 DB 서버 없이 로컬 파일에 저장한다. |
| Brief 갱신 | S1 결과를 승인할 때만 승인된 Brief를 교체한다. S2~S6 결과는 각 단계 산출물에 저장한다. |
| back | Decision을 기록하고 이전 화면으로 이동한다. back 자체는 승인 상태·산출물·stale 상태를 바꾸지 않는다. |
| Markdown 출력 | S6 초안을 Markdown으로 내보낸다. LaTeX/PDF는 이번 범위에서 제외한다. |

이 네 가지는 **프로토타입 전용 임시 선택**이다. SSAD의 확정 사항이나 설계 변경, 원문 준수를 입증한 결과로 설명하지 않는다. 상태는 `scope.json.prototype_baseline`에 있다. SSRD·SSAD 원본과 추출 원문은 보존한다. 정식 시스템 설계에 채택할지는 이 계획팩에서 결정하지 않는다.

이번 프로토타입 구현에서는 **scope → contracts → implementation_plan** 순서로 범위와 동작을 판단한다. 이는 SSRD·SSAD 원문의 의미를 바꾸지 않는다. 자료끼리 모순이 있으면 모순과 해결 내용을 기록하며, 사용자의 현재 명시적 지시를 우선한다.

## 환경과 실행 방식

- Node 22 이상, Python 3.11을 사용한다. 프런트는 Next.js 16.4.5·TypeScript, 백엔드는 FastAPI·Pydantic 2·SQLAlchemy 2다. 세부 설정은 `scope.json`과 T01을 따르고 설치에 성공한 의존성을 lockfile로 고정한다.
- 브라우저는 로컬 프런트 3000번, API는 8000번의 `/api`를 사용한다. 실제 앱의 설치·실행 명령은 구현 후 루트 README에 작성한다.
- 서버는 단일 프로세스와 내부 작업 스레드 하나로 실행한다. 상태 복구 규칙 때문에 기본 실행 명령에는 자동 reload·다중 worker를 넣지 않는다. 진행 상태는 1초 간격 조회다.
- 저장소 루트 `.env`를 백엔드가 읽는다. live에는 서버의 `ANTHROPIC_API_KEY`와 `LLM_MODEL`이 필요하며 `ANTHROPIC_WORKSPACE_ID`는 선택 설정이다. 비밀키를 소스·브라우저·보고서에 넣지 않는다.
- API 키와 네트워크 없이 demo 구현·검사를 마칠 수 있어야 한다. 생성 코드는 서비스 밖에서 사용자가 실행하며 웹 서버에 scikit-learn·PyTorch를 설치하거나 생성 코드를 실행하지 않는다.

## 구현하면서 유지할 구분

- **demo/live:** APP_MODE의 기본값은 demo다. 사전 작성 결과도 매번 실제 앱 코드로 새 버전을 저장하고 편집·승인·오래됨·업로드·내보내기를 처리한다. live는 실제 모델과 arXiv를 사용하며 실패를 demo 결과로 바꾸지 않는다. 프로젝트 mode는 생성 때 고정하고 환경 변경을 기존 프로젝트에 소급하지 않는다. UI와 내보내기에 ‘데모 모드: 사전 작성 산출물 사용’을 표시한다.
- **예시 출력/실측 데이터:** `fixtures/stages/`는 사전 작성 생성 결과다. `fixtures/experiment_result.valid.json`의 지표는 동봉 CPU 실험에서 실제 측정했다. 단일 실행으로 일반적인 성능 우위를 주장하지 않는다.
- **내부 모듈/외부 서비스:** CitationVerifier는 백엔드 내부 모듈이며 arXiv가 외부 서비스다. WorkflowService는 상태와 승인을, ContextBuilder는 입력 버전 조립을 담당한다. 구체적인 역할은 `architecture.md`를 따른다.
- **서버 검사/화면 표시:** 승인 조건, 입력 버전, 중복 요청, 업로드 검증은 서버가 강제한다. 버튼 비활성화만으로 완료 처리하지 않는다.
- **UI 변경/동작 변경:** UI/UX 기획안 도착 후 배치·스타일은 조정할 수 있다. API·필수 입력·승인 순서 등 동작에 영향을 주면 관련 계약과 구현 계획의 영향도 확인하고 기록한다.
- **계획 검사/앱 검사:** `python scripts/check_handoff.py`는 계획 자료의 일관성 검사다. 웹 앱의 구현 완료나 live 동작을 입증하지 않는다.

## 작업 기록과 완료 보고

기존 코드·설정·진행 기록을 먼저 확인하고 보존한다. 계획팩의 초기 TODO 표시만 보고 이미 작성된 구현을 지우거나 처음부터 다시 만들지 않는다. 새 프로젝트에서는 `implementation_plan.md`의 구조로 시작하고, 기존 프로젝트에서는 관련 위치를 확인해 이어서 구현한다.

작업을 마칠 때 `IMPLEMENTATION_STATUS.md`에 완료한 T 항목, 실제 실행 명령과 결과, 미실행 검사, 남은 제한을 기록한다. API 키가 없어도 demo와 오프라인 검사는 진행한다. 실제 실행하지 않은 검사나 구현되지 않은 기능을 완료로 보고하지 않는다. 세부 완료 판정은 `acceptance.md`와 `acceptance.cases.json`을 따른다.

작업 결과에는 실제 앱 코드, 설치·실행 명령과 lockfile, 처음부터 재현 가능한 demo 사용법, PASS/FAIL/NOT RUN으로 구분한 검사 결과를 포함한다. 마감이 가까워지면 새 기능보다 필수 승인·버전·업로드·다운로드 동작의 오류 수정을 우선한다. 범위 안의 일반적인 구현 선택은 스스로 해결하고 기록한다.
