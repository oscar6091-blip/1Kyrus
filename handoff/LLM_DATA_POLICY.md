# LLM 입력 데이터 사용 조건 확인 기록

현재 상태: **DOCUMENTS_REVIEWED** (공식 문서만 검토. 실제 사용할 계정·계약의 조건은 확인하지 않음)

이 파일은 SSRD PR-7·SIR-3 및 SSAD의 Gateway 설계에 있는 조건 확인을 구현 작업으로 전달하기 위한 기록이다. 현재 제공자의 정책 충족 여부를 판정한 문서는 아니다. API 키를 서버에 보관하거나 Gateway를 경유하는 것만으로 입력 데이터 사용 조건을 확인했다고 보고하지 않는다.

| 항목 | 현재 기록 |
| --- | --- |
| 계획한 제공자·제품 | Anthropic API (상용 API 제품, 서버 측 API 키 사용). 소비자용 Claude 앱이 아님. 실제 계정·계약 유형은 미확인 |
| 확인 상태 | DOCUMENTS_REVIEWED |
| 확인일·확인자 | 2026-11-07, 구현 작업 중 Claude Code가 공식 문서 페이지를 직접 조회해 기록 (사용자 계정 정보 없음) |
| 공식 근거 문서 URL·적용일 | ① https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training (페이지 표시일 2026-08-18; privacy.anthropic.com에서 리다이렉트) ② https://www.anthropic.com/legal/commercial-terms (Effective 2025-06-17, 대상 Business) ③ https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data (페이지 표시일 2026-07-01) |
| 입력 데이터의 모델 학습 사용 조건 | ①: "By default, we will not use your inputs or outputs from our commercial products (e.g. Claude for Work, Anthropic API, Claude Gov, etc.) to train our models." ②: "Anthropic may not train models on Customer Content from Services." 예외(①): 사용자가 피드백·버그를 명시적으로 보고하거나 데이터 사용을 허용한 경우 |
| 실제 사용할 계정·설정에 조건이 적용되는 근거 | **미확인.** 사용할 API 계정이 상용 약관(Commercial Terms) 적용 대상인지, 별도 계약·ZDR·피드백 제출 여부를 확인하지 않았다. 이 프로토타입은 피드백 기능을 호출하지 않는다 |
| 조건·예외·추가 확인 사항 | 보존(③): "For Anthropic API users, we automatically delete inputs and outputs on our backend within 30 days of receipt or generation", 예외로 Usage Policy 위반 판정 시 입력·출력 최대 2년, 피드백 제출 데이터 5년. 상용 약관은 데이터 처리를 DPA로 위임하며 DPA 원문은 조회하지 않았다. 소비자용 개인정보처리방침(https://www.anthropic.com/legal/privacy)은 개인 사용자 대상이라 이 판단의 근거로 쓰지 않았다 |

### 남은 확인 (ACCOUNT_CONDITIONS_CONFIRMED로 올리려면)

- 실제로 쓸 Anthropic 계정·조직이 상용 약관(Commercial Terms) 적용 대상인지 계정 소유자가 확인한다. 별도 계약이 있으면 그 계약도 확인한다.
- 그 결과와 확인일·확인자를 이 표에 적는다. 확인 전에는 이 상태를 PASS나 공식 인증으로 보고하지 않는다.

## T05에서 할 일

1. 실제 사용할 API 제품과 계정 조건을 확인한다. 소비자용 채팅 제품과 API 제품의 조건을 혼동하지 않는다.
2. 공식 문서·계약 근거의 URL, 적용 조건, 확인일을 기록한다. 실제로 확인하지 않은 계정 설정을 확인했다고 적지 않는다.
3. 문서만 검토했으면 DOCUMENTS_REVIEWED, 실제 적용 조건까지 확인했으면 ACCOUNT_CONDITIONS_CONFIRMED로 상태를 구분한다. 확인하지 못하면 NOT_CHECKED와 사유를 유지한다.
4. `IMPLEMENTATION_STATUS.md`에 live 기능 검사 결과와 이 확인 상태를 별도로 기록한다. 확인 불가를 PASS나 공식 인증으로 바꾸지 않는다.

demo 구현·시험은 이 확인 때문에 중단하지 않는다. 이 기록을 만든 사실과 실제 조건 확인이 끝났다는 사실은 구분한다. 정식 인증 기능·제공자 자동 교체·SSRD/SSAD 원본 수정은 이번 작업에 포함되지 않는다.
