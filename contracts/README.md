# 계약 읽는 순서와 검증 규칙

1. `workflow.json`: 상태·쓰기·입력 버전의 규칙.
2. `database.sql`: SQLite 저장 구조. 별도 DB 서버가 필요하지 않다.
3. `domain.schema.json`: API가 주고받는 Project·Stage·Artifact·Job 등.
4. `artifacts.schema.json`: S1~S6의 모델 결과이자 저장 payload.
5. `upload.schema.json`: 외부 실험 결과 파일.
6. `api.openapi.json`: `/api` 아래의 정확한 HTTP 경로와 요청·응답.

JSON Schema 문법 검증 외에 아래 의미 검증을 백엔드 서비스에서 수행한다. 프런트의 검사만으로 대체하지 않는다.

## 공통

- 모든 엔티티 ID와 request_id는 앱에서 새 UUID 문자열로 생성한다. H1·E1·metric binding·reference ID는 문서의 의미 있는 식별자다.
- 모든 API 오류는 `{error:{code,message,fields:[{path,message}],retryable}}` 형식이다. FastAPI 기본 422 오류도 이 형식으로 바꾼다.
- 날짜는 앱에서 실제 작업 시각을 UTC ISO 문자열로 기록한다. `references.snapshot.json`의 확인일만 날짜 단위 기록이다.
- stage_no는 1~6. `payload.stage_no`와 경로의 stage_no는 일치해야 한다.
- 버전 번호는 해당 Stage의 기존 최대값+1이다. 생성·편집마다 새 행을 만들고 기존 행을 덮어쓰지 않는다.
- input_snapshot/evidence/생성 주체/모델/시각/버전은 서버가 만든다. 클라이언트는 payload와 코멘트만 수정한다.
- ArtifactView의 rendered_markdown은 서버가 payload와 해당 Artifact의 evidence로 계산한 미리보기다. DB에 별도 원본으로 저장하지 않는다. 저장 전 실시간 편집 미리보기는 필수가 아니며, 저장 후 이 값을 표시한다.
- Markdown은 HTML 실행 없이 렌더링한다. 빈 문자열·잘못된 payload는 저장하지 않는다.
- 실제 stage 상태·current/approved 포인터는 API에서 조회한다. 브라우저 localStorage를 연구 기록의 원본으로 쓰지 않는다.

## 승인 Brief 이력과 근거의 읽기 전용 열람

- 기존 `GET /projects/{id}/decisions`의 S1·approve 기록을 모아 승인 Brief 이력으로 표시한다. 각 artifact_id를 기존 Artifact 조회 API로 읽어 버전·내용·생성 주체와 승인 시각을 보여 준다. 버전 역순으로 정렬한다.
- 과거 승인본·stale 산출물을 열람해도 current/approved 포인터·Stage 상태·Decision 수는 바뀌지 않는다. 과거본은 읽기 전용이다. 전체 초안 버전 탐색·diff·복원 기능은 추가하지 않는다.
- `ref:ID`는 해당 Artifact evidence의 논문 source_url을 연다. `metric:ID`는 기존 Run 목록에서 binding의 run_id를 찾아 원본 JSON과 metric_index 행을 보여 준다. `artifact:ID`는 기존 Artifact 조회로 해당 버전을 연다.
- 열람할 근거는 현재 Artifact의 불변 evidence/input_snapshot과 연결된 ID로 한정한다. 현재 Stage의 새 근거로 옛 Artifact 근거를 대체하지 않는다. 기존 Project 소속 검사를 적용한다.
- `rationale.evidence_refs`가 비어 있으면 ‘근거 없음: 사용자 확인 필요’를 표시한다. 이유 텍스트와 대안은 보여 주되 대안 선택의 자동 적용은 구현하지 않는다. 필요하면 사용자가 직접 편집한다.
- 모든 문장의 근거 매핑과 자연어 의미 검증은 이번 범위에서 제외한다. 주요 결정·인용·지표의 원본을 사용자가 열어 확인하는 범위다.

## S1

- Brief 필수 텍스트와 가설 한 개 이상이 필요하다. 가설 ID는 중복 불가다.
- 확인 질문은 최대 3개다. proposal에 질문이 있어도 필수 필드를 사용자가 검토해 승인할 수 있다.
- `results_conclusion`은 null로 유지한다. 결과는 S5 Artifact에 보관한다.

## S2

- payload는 정리 본문을, 서버 evidence는 확인된 논문 메타데이터를 가진다.
- References는 1~3개. 모델이 authors·title·year를 새로 써서 evidence를 수정할 수 없다.
- `{{cite:ID}}`와 `rationale.evidence_refs`의 `ref:ID`는 evidence에 있어야 한다.
- 검증 대상 ID가 없거나 API가 실패하면 명확히 실패한다. 출력 문장을 다른 논문으로 임의 대체하지 않는다.
- 일부 후보를 미검증으로 제외하면 `evidence.warnings`에 대상 식별자/제목과 제외 사유를 기록해 검토 화면에 표시한다. 후보가 전부 제외되면 NO_VERIFIED_REFERENCES 오류의 message/fields로 사유를 제공한다. 없는 실패 후보를 만들지는 않는다. `verified=true`인 허용 목록에 미검증 후보를 섞지 않는다.

## S3

- experiments 1~5개. E ID 중복 불가.
- hypothesis_ids는 승인 Brief에 있는 H ID여야 한다.
- 한 실험 안의 hypothesis_ids는 중복 불가이며, 전체 experiments의 hypothesis_ids 합집합은 승인 Brief의 모든 H ID를 포함해야 한다. 누락된 가설은 INVALID_PAYLOAD와 필드 위치로 거부한다.
- metric_names는 실험 안에서 중복 불가이며 upload metric.name 문법과 같아야 한다.
- body_md에 가설–실험 대응, 데이터셋, 베이스라인, 평가 지표, 실행 절차, 예상 비용·시간을 설명한다.
- body_md에 `## Ablation 계획`과 비어 있지 않은 계획 또는 해당 없음 사유를 포함한다. 작은 통합 예제에서 수행하지 않은 ablation을 수행했다고 쓰지 않는다. 제목/비어 있음 검사와 계획의 과학적 타당성 평가는 구분한다.
- 실험 ID·가설·필수 지표 목록은 structured experiments가 기준이다. UI는 이를 별도 폼으로 보여 준다. 후속 단계에는 본문과 이 구조를 함께 전달한다.

## S4

- 파일 수 1~10, 각 content 최대 65,536자. 전체 UTF-8 크기 500 KiB 이하.
- 상대 POSIX 경로만 허용. 절대 경로, `..`, 역슬래시, 드라이브 경로, NUL, 중복 경로, `.env` 파일은 거부한다.
- zip 생성 때도 같은 검사를 수행한다. 사용자 코드는 exec·subprocess·eval·동적 import로 실행하지 않는다.
- Python 코드는 ast.parse 문법 검사까지만 허용한다. 이 검사를 통과해도 학습 성공으로 표시하지 않는다.
- 참조용 코드는 CPU·scikit-learn을 사용한다. PyTorch/GPU 의존성을 자동 설치하지 않는다.

## S5 업로드·분석

- `POST /projects/{id}/runs`는 multipart file과 client_upload_id를 받는다. JSON 파일 1 MiB 이하다.
- 업로드 형식은 `prototype_json_v1`이며 원문 SSRD A.II의 무변환 호환 형식이 아니다. 원래 규격·정상 예시는 `../sources/ssrd_context.json.external_upload_original`에 보존했다. 추가 필수 필드는 schema_version, data_origin, metrics[].unit이다. 자동 변환·단위 추측·CSV 입력은 구현하지 않는다. 빠진 필드는 422 위치를 보여 주고 동봉 정상 예시와 현재 형식을 안내한다.
- JSON parser에서 NaN·Infinity와 중복 object key를 거부한다. 숫자는 유한해야 한다. bool은 seed·value의 숫자로 취급하지 않는다.
- metric의 unit이 ratio면 0~1, percent면 0~100, seconds/count면 음수가 아니어야 한다. 그 밖은 유한값 여부를 검사한다.
- metrics의 `(name, split, step 또는 null)`이 중복이면 거부한다.
- experiment_id가 현재 승인된 S3에 존재해야 한다. 해당 실험의 필수 metric_names가 업로드에 모두 있어야 한다. 추가 지표는 허용한다.
- 업로드한 파일은 새 ExperimentRun이다. 서버가 실험했다는 표시를 하지 않는다. code_version은 사용자가 제공한 식별자이며 자동 코드 일치 검증을 구현하지 않는다.
- `data_origin=synthetic_demo`인 파일은 demo 프로젝트에만 허용한다. 동봉 정상 파일은 실제 실행값인 measured다. 이 필드는 업로더의 출처 진술이며 외부 실행의 진위를 자동 증명하는 인증은 아니다.
- S1~S4 승인 전 업로드는 409. 프로젝트 busy 중 업로드도 409.
- 분석 run_id는 해당 Project 소속이어야 한다. 같은 client_upload_id·같은 내용은 기존 Run 반환, 다른 내용 재사용은 409.
- evidence.metrics의 m0…는 원본 metrics 배열 순서. 과거 Artifact의 복사된 값은 수정하지 않는다.
- 가설 판정은 Brief의 H ID에 대해서만 만든다. 근거가 부족하면 inconclusive를 사용한다.
- hypothesis_verdicts는 Brief의 모든 H ID를 정확히 한 번씩 포함한다. 선택 Run의 experiment_id에 대응하지 않는 가설은 inconclusive와 ‘선택한 실행으로 검증하지 않음’ 사유만 허용한다. 한 Run의 결과를 다른 실험의 결과로 확대하지 않는다. 원문의 전체 실험 수집·다중 Run 통합은 이번 범위에 추가하지 않는다.

## S6

- 섹션 key는 abstract, introduction, related_work, methods, experiments, conclusion 순서로 정확히 한 번씩 있어야 한다.
- 영어 본문. UI와 편집 버튼은 한국어다.
- 논문 인용은 승인 S2의 확인된 reference ID만, 실험 수치는 승인 S5의 metric ID만 사용한다.
- 미등록 토큰·근거 ID가 있으면 거부한다. 토큰이 닫히지 않거나 지원하지 않는 `{{...}}`도 오류다.
- 자유 서술의 모든 숫자·인용 문장 의미를 증명하는 완전 검증기는 구현하지 않는다. 표·참조 토큰의 값 연결을 보장한다.

## 근거 복사와 수정

- S2 evidence.references는 외부 확인 결과 또는 demo snapshot이다.
- S3·S4는 승인된 상위 reference snapshot을 복사해 필요한 이유를 설명할 수 있다.
- S5는 선택 Run의 metric binding과 warnings를 만든다.
- S6는 승인 S2의 references와 승인 S5의 metrics·warnings를 복사한다.
- S2의 인용 제외 경고도 S6 evidence.warnings에 보존한다. 같은 경고는 중복 표시하지 않는다.
- 사용자가 새 payload를 저장해도 evidence와 입력 snapshot은 base Artifact에서 그대로 가져온다. 사용자가 evidence 숫자를 수정할 수 없다.
- rationale의 근거는 `ref:ID`, `metric:ID`, `artifact:ID` 중 현재 context/evidence에 존재하는 ID만 허용한다. 이유의 의미 적합성까지 자동 검증했다고 주장하지 않는다.

## 내보내기

- code.zip: S4가 approved일 때만 해당 승인 Artifact의 files를 사용한다.
- paper.md: S6가 approved일 때만 해당 승인 Artifact의 payload와 evidence로 렌더링한다.
- references.bib: S6가 approved면 그 evidence, 아니면 S2가 approved면 그 evidence에서 만든다. 현재 관련 Stage가 stale이면 내보내기를 차단한다.
- 문자열을 템플릿 코드로 실행하지 않는다. BibTeX의 중괄호 등 텍스트는 이스케이프한다.
- demo 내보내기에는 demo 생성 표시를 붙인다. S4 zip은 README 앞에 표시를 붙여 제공하고 원본 train.py 내용을 바꾸지 않는다. 따라서 동봉 참조 코드의 SHA-256도 유지된다.

## 응답·상태의 구체적 해석

- Job 생성은 202. 후속 polling은 같은 Job ID를 조회한다.
- Decision/편집 성공은 200. edit이면 새 Artifact, regenerate면 새 Job, back이면 navigate_to_stage를 채운다. 나머지 선택 필드는 null이다.
- 중복 요청 반환은 새 작업이 아니다. Job 상태·Stage 상태가 시간에 따라 바뀌는 것은 허용되지만 결과 객체 ID가 늘어나면 안 된다.
- stage 실패 후 current_artifact가 없으면 승인 불가. 기존 승인 결과가 남아 있어도 ‘새 실패 작업이 성공했다’고 표시하지 않는다.
- current_artifact_id와 approved_artifact_id가 같으면 재승인할 새 초안이 없으므로 승인 불가다. 실패 후 남아 있는 과거 승인본을 새 결과처럼 승인하지 않는다.
- Artifact 조회는 해당 Project 소속을 확인한다. 존재하는 다른 프로젝트의 ID도 현재 경로에서 접근하면 404다.

## 원문과 의도적으로 다른 점

원문 요구사항은 `requirements.selected.json`에 그대로 남겨 두었다. 이번 계약은 JSON만 업로드, Markdown 초안, S1만 Brief 갱신, 모든 하위 단계 stale, back은 이동만, CPU 외부 실행, SQLite라는 축소를 명시한다. 원문의 100% 품질·가용률·사용자 평가 기준을 달성했다고 보고하지 않는다.

이 중 SQLite·S1에서만 Brief 갱신·화면 이동만 수행하는 back·Markdown 출력은 SSAD와 별도로 둔 프로토타입 전용 임시 baseline이다. 계약은 이번 프로토타입의 동작을 고정하며 SSAD의 확정 사항이나 설계 변경을 뜻하지 않는다. SSRD·SSAD 원본은 수정하지 않는다. 상태와 적용 범위는 `../scope.json.prototype_baseline` 및 `../CLAUDE.md`를 확인한다.
