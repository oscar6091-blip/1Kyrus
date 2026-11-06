# 구현 상태

현재 상태: **계획 팩만 작성됨. 아래 웹 앱 작업은 아직 시작하지 않음.**

이 문구는 배포한 계획팩의 초기 상태다. 기존 작업 폴더에 구현이 있다면 현재 코드·검사 결과를 확인해 갱신하고 이어서 작업한다. source-completion 개정으로 원문 자료와 N-01~N-09 구현 지시를 보완했으며, 이것이 앱 구현 완료라는 뜻은 아니다. LLM 입력 데이터 조건의 확인 상태는 LLM_DATA_POLICY.md의 NOT_CHECKED에서 시작한다.

범위 설명: SQLite·S1에서만 Brief 갱신·화면 이동만 수행하는 back·Markdown 출력은 SSAD와 별도로 둔 프로토타입 전용 임시 baseline이다. 구현 상태 보고에서도 이를 SSAD의 확정 사항이나 설계 변경으로 표현하지 않는다. SSRD·SSAD 원본 수정은 이번 작업에 포함되지 않는다.

| 작업 | 상태 | 실제 실행 명령과 결과 |
| --- | --- | --- |
| T01 환경·골격 | TODO | |
| T02 DB·워크플로 | TODO | |
| T03 demo 실행·업로드·내보내기 | TODO | |
| T04 공통 UI | TODO | |
| T05 live Gateway·arXiv | TODO | |
| T06 단계별 live 생성 | TODO | |
| T07 필수 동작 검증 | TODO | |
| T08 제출 정리 | TODO | |

## 계획 자료 검사

검사일: 2026-11-07. 이 절은 계획 자료와 동봉 참조 실행의 기록이며 웹 앱의 완료 판정과 구분한다.

계획팩 폴더에서 다음 명령을 실행한다. 결과는 PASS다.

```bash
python scripts/check_handoff.py
```

- 첨부 SSRD·SSAD와 동봉 사본의 SHA-256 일치.
- SSRD DOCX XML과 요구사항 55개·필드 478개 직접 대조 일치. 공란 26개 보존.
- 부분 구현 36개·보류 19개가 요구사항 ID 전체를 중복 없이 나누며 선택 항목이 AC에 연결됨.
- 요구사항 표 밖 본문·일반 표 110개 블록, UI 정의 10개, 미검증 고객 가정 7개, A.II 규격 8개 필드·예시 보존.
- N-01~N-09 보완 항목과 실제 파일·기존 AC의 연결 확인.
- 여섯 단계 fixture의 스키마, 가설 대응·Ablation 계획, 지표·인용·이유의 근거 ID 연결 확인.
- 정상 업로드 수락·잘못된 업로드 거부와 원문 A.II 예시의 추가 필수 필드 세 곳 거부 확인. 원문 무변환 호환은 지원하지 않음.
- OpenAPI operation 16개와 로컬 schema 참조, S6 여섯 섹션 순서 확인.
- SQLite 여섯 테이블 생성과 프로젝트당 active Job 한 개 제약 확인.
- 참조 train.py의 SHA-256과 실측 JSON의 code_version 일치. S4 코드 fixture가 참조 코드와 동일하고 문법 검사 통과.

동봉 checker는 이 팩에서 사용하는 JSON Schema 키워드를 검사하는 표준 라이브러리 도구다. 범용 Draft 2020-12 인증 도구나 실제 앱 테스트는 아니다. 앱에서는 Pydantic과 서버 의미 검증을 함께 구현한다.

## 동봉한 실측 자료

작성자가 `reference_experiment/train.py`를 CPU에서 실행해 `fixtures/experiment_result.valid.json`을 만들었다. 정확한 실행 시각·환경·시간은 해당 JSON에 있다.

- Iris의 계층화 split·학습 데이터에만 fit한 전처리·고정 seed·작은 MLP를 사용했다.
- SGD·Adam의 accuracy와 macro F1, 총 네 측정값을 기록했다. 두 accuracy는 같았다.
- 두 학습의 최대 iteration 도달 수렴 경고를 config.fit_warnings에 보존했다.
- 단일 실행으로 통계적 우위나 재현성 목표 달성을 주장하지 않는다. 이 측정이 웹 앱의 구현·시험을 뜻하지도 않는다.

## 아직 수행하지 않은 확인

- 웹 프런트·백엔드 구현·통합·브라우저 시연.
- 사용자의 API 키를 이용한 실제 앱 LLM 호출과 arXiv 네트워크 어댑터 동작.
- LLM 입력 데이터 사용 조건의 실제 계정 적용 여부. 현재 확인 기록은 LLM_DATA_POLICY.md에서 본다.
- SUS·고객 평가·가용률·기관용 보안·모든 자유 서술 수치의 정확성 평가.

## live 검사

아직 미실행. 구현 후 실제 사용한 키·모델로 수행한 경우에만 결과를 기록한다. 키 값은 적지 않는다. API 기능 시험 결과와 데이터 사용 조건 확인 상태를 분리한다.
