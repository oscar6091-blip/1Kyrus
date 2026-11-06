# 외부 CPU 참조 실험

이 코드는 **프로토타입 웹 서비스 밖에서 실행할 작은 참조 실험**이다. 구현 계획 작성자가 실제 실행해 `../fixtures/experiment_result.valid.json`을 만들었다. S4 fixture의 코드 파일도 이 코드와 같다.

```bash
python -m pip install -r requirements.txt
python train.py --output experiment_result.json
```

- 내장 Iris 데이터, 계층화 train/test 분할, 학습 데이터에만 표준화 fit.
- 같은 분할·seed·작은 MLP에서 SGD·Adam을 비교.
- 출력의 `code_version`은 이 `train.py`의 SHA-256이다. Git 커밋 해시라고 주장하지 않는다.
- 데이터·모델 환경 버전과 측정 시각·시간·수렴 경고를 JSON에 남긴다.
- 출력은 웹 앱 S5에서 업로드할 형식이다.

동봉 실행에서는 두 방법의 accuracy가 같았고, 두 학습 모두 최대 iteration 도달 경고를 냈다. 단일 seed·단일 split이므로 알고리즘의 일반적인 우위를 판단할 자료가 아니다. 결과를 좋게 보이게 숫자나 경고를 수정하지 않는다.

다른 환경에서 재실행한 결과는 새로운 실험 기록이다. 동봉된 JSON을 덮어써 같은 실행인 것처럼 취급하지 않는다. 이 비교에 대한 confidence interval·통계 검정·반복 seed 실험은 수행하지 않았다.
