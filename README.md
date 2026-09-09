# voc-agent-commerce

이커머스 고객센터(CS) VOC를 분석하는 **범용 지시문(Playbook) 기반** 도구.

Python 설치, API 키, 별도 과금 없이 동작한다.
당신이 이미 쓰는 LLM 구독(Claude Code, Codex CLI, Cursor 등)으로 실행한다.

---

## 동작 원리

이 리포에는 실행 파일이 없다. 대신 [`PLAYBOOK.md`](PLAYBOOK.md)라는 상세 지시문이 있다.

```
당신의 CSV  +  이 리포 URL  →  당신이 쓰는 AI에게 전달
                                   ↓
                          AI가 PLAYBOOK.md를 읽고
                          VOC 분석 파이프라인을 직접 수행
                                   ↓
                         output/ 에 분석 결과 저장
```

**의미 판단**(Topic·Sentiment 분류, 원인 가설)은 AI가 직접 수행한다.
**계산**(F/S/T·Priority)은 `scripts/priority_calc.py`를 실행해서 처리한다.
**사람 검토 지점**에서는 AI가 실제로 멈추고 사용자 확인을 받는다.

---

## 빠른 시작

1. **이 리포를 클론 또는 URL 공유**

   ```bash
   git clone https://github.com/<your-username>/voc-agent-commerce.git
   ```

   또는 GitHub URL(`https://github.com/<your-username>/voc-agent-commerce`)을 그대로 AI에게 전달한다.

2. **당신의 LLM 환경에서 아래 메시지를 입력한다**

   ```
   이 리포의 PLAYBOOK.md를 읽고, 내 CSV 파일을 분석해줘.
   CSV 경로: [당신의 CSV 파일 경로]
   ```

3. **AI가 00단계부터 시작한다**
   - 컬럼 매핑을 제안하고 확인을 요청
   - 분류 → 계산 → 원인 가설 → 실행안 순으로 진행
   - 사람 검토가 필요한 지점에서 멈추고 질문

---

## 입력 CSV 요건

| 요건 | 내용 |
|---|---|
| 필수 컬럼 | **VOC 본문 텍스트** 컬럼 1개 (컬럼명은 무엇이든 가능) |
| 권장 컬럼 | 고객 ID 또는 순번, 날짜(Trend 계산에 사용) |
| 인코딩 | UTF-8 또는 CP949(EUC-KR) |
| 언어 | 한국어 (이 택소노미는 한국 이커머스 CS 기반) |
| 건수 | 제한 없음. 5,000건 초과 시 PLAYBOOK이 층화 추출을 안내 |

컬럼명이 달라도 된다. 00단계에서 AI가 자동 매핑을 제안한다.

---

## 산출물 (output/ 폴더)

| 파일 | 내용 |
|---|---|
| `report.html` | **공유용 결과 리포트** — 브라우저로 열람, 토픽별 PDF 개별 출력 가능 |
| `01_cleaned.csv` | 정제 + 도메인 필터 결과 |
| `06_classified.csv` | Topic 분류 (대분류 A~J + 중분류) |
| `07_sentiment.csv` | Sentiment 분류 추가 |
| `09_priority.csv` | F/S/T/Priority 계산 결과 |
| `review_log.jsonl` | Human 검토 기록 |
| `11_recommendation.md` | 실행안 초안 |
| `12_dashboard.md` | 1페이지 요약 대시보드 |

> ⚠️ **`output/report.html`에는 고객 발화 원문이 포함됩니다.**
> 외부 공유·Git 커밋 전 반드시 내용을 검토하세요.
> `output/` 폴더 전체가 `.gitignore`에 등록되어 있어 실수로 커밋되지 않습니다.

---

## 분석 택소노미 (A~J)

원본 이커머스 CS 데이터 15,163건의 임베딩·군집화를 거쳐 사람이 확정한 10개 대분류:

| 대분류 | 이름 |
|---|---|
| A | 배송 지연·미도착 |
| B | 주문 취소 (배송 전) |
| C | 반품·교환·환불 (배송 후) |
| D | 상품 주문 접수 |
| E | 절차·정책 문의 |
| F | 결제 방법·오류 |
| G | 혜택·적립 |
| H | 계정·회원 관리 |
| I | 제품 A/S (고장·수리) |
| J | 제품 사용법·문의 |

상세 정의·포함·제외(행선지) Guideline은 [`configs/commerce_cs.json`](configs/commerce_cs.json) 참조.
원본 문서는 [`context/topic_taxonomy.md`](context/topic_taxonomy.md).

---

## 택소노미 확장

"기타" 비율이 15%를 초과하면 PLAYBOOK이 **확장 마법사**를 자동 실행한다.
새 카테고리는 [`EXTENDING.md`](EXTENDING.md)의 체크리스트 6개 필드를 모두 채운 후
[`configs/local_extensions.json`](configs/local_extensions.json)에 저장된다.

`configs/commerce_cs.json`(원본)은 수정되지 않는다.
확장 마법사는 필드를 한 번에 하나씩, 매 필드 사용자 확인 후 진행한다.

---

## 파일 구조

```
voc-agent-commerce/
├── PLAYBOOK.md              ← 실행 지시문 (이 도구의 핵심)
├── EXTENDING.md             ← 택소노미 확장 가이드
├── candidate_extensions.md  ← 미검증 관찰 기록
├── configs/
│   ├── commerce_cs.json     ← 원본 config (수정 금지)
│   └── local_extensions.json← 사용자 확장 (여기에만 저장)
├── context/
│   ├── topic_taxonomy.md    ← 택소노미 원본 문서
│   ├── cause_taxonomy.md    ← 귀책 원인 원본 문서
│   ├── action_playbook.md   ← Action 카탈로그 원본
│   ├── metric_dictionary.md ← 지표 원본
│   └── process_map.md       ← 프로세스 맵
├── reference_output/
│   ├── action_plan_full.md  ← 검증된 실행안 상세 (참조용)
│   ├── rootcause_recommendation.md
│   ├── deliverable_exemplars.md
│   └── domain_filter.py     ← 도메인 필터 원본 스크립트
├── scripts/
│   └── priority_calc.py     ← F/S/T/Priority 계산 전용
├── data/
│   └── ecommerce_voc_sample.csv ← 테스트용 샘플 50건
└── output/                  ← 분석 결과 저장 (AI가 생성)
```

---

## Priority 공식

```
Priority = 0.4 × F_score + 0.4 × S_score + 0.2 × T_score
```

| 지표 | 정의 | 범위 |
|---|---|---|
| F_score | Frequency (빈도). 상한 20% 적용 | 0~100 |
| S_score | Severity (심각도). Sentiment 평균 기반 | 0~100 |
| T_score | Trend (추세). 직전·최근 기간 비중 변화율 | 0~100 |

**Priority는 실행 순서가 아니다.** 심각도(S)가 높지만 빈도(F)가 낮은 이슈는 Priority는 낮아도 별도 원인 분석이 필요할 수 있다.

---

## 한계 사항

- 이 택소노미는 한국 이커머스 콜센터 데이터 기반이다. 패션·식품 특화 유형(사이즈 문의, 신선도 등)은 기본 포함되지 않으며, 확장 마법사로 추가할 수 있다.
- Trend 계산은 `created_at`이 있을 때만 동작한다. 합성 타임스탬프를 사용한 경우 Trend 수치는 실측이 아니다.
- Priority 수식에 Business Impact(매출·이탈 영향)는 포함되지 않는다. VOC 분석의 책임 범위를 정확히 그었기 때문이다 (SPEC §1-A). 사업 데이터 확보 시 `0.3F+0.3S+0.2T+0.2B`로 확장 가능하다.
- 원인 규명은 주문 DB·택배 API 데이터와의 결합이 있어야 정확하다. 텍스트만으로는 가설 수준이다.

---

## 설계 배경

이 도구의 방법론 설계 배경은 원본 프로젝트에서 확인할 수 있습니다: https://github.com/kellyjoo3/voc-insight-project

---

## 라이선스 / 출처

- 택소노미 원본: AI Hub「용도별 목적대화 데이터」(dataSetSn=544) shopping 도메인 분석 결과
- 이 리포는 이커머스 CS 일반 참조 모델(Reference Model)로, 특정 기업의 실제 운영 정책이 아니다
