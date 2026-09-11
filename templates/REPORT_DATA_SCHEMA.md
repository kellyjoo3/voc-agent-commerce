# report_data.json 스키마

12단계에서 `templates/report_template.html`에 주입할 데이터 형식.

## 생성 절차

```
1. output/report_data.json 을 아래 스키마대로 작성
2. templates/report_template.html 을 읽는다
3. 문자열 "/*__REPORT_DATA__*/ null" 을 report_data.json 의 내용으로 치환
4. output/report.html 로 저장
```

**주의:** 데이터는 반드시 HTML에 **인라인으로 박아야** 한다. `fetch()`로 별도
JSON을 읽게 만들면 사용자가 `file://`로 열 때 CORS 차단으로 빈 페이지가 된다.

---

## 스키마

```jsonc
{
  "meta": {
    "title": "VOC 분석 리포트",          // 페이지 제목
    "analyzed_at": "2026-09-09",
    "input_file": "my_voc.csv",
    "record_count": 1200,
    "period": "2026-07-01 ~ 08-31",      // 없으면 생략 가능
    "generator": "voc-agent-commerce",
    "caveat": "..."                       // 상단 경고 박스. 없으면 생략
  },

  "summary": {
    "tiles": [                            // 4~5개 권장
      { "label": "분석 건수", "value": "1,200", "unit": "건" },
      { "label": "최고 Priority", "value": "78.9", "sub": "C 반품·교환·환불 (P1)" }
      // label/value 필수, unit/sub 선택
    ]
  },

  "distribution": [                       // 건수 내림차순
    { "code": "C", "name": "반품·교환·환불", "count": 18, "pct": 36.0,
      "is_extension": false }
  ],

  "priority": [                           // priority 내림차순, rank 1부터
    { "rank": 1, "code": "C", "name": "반품·교환·환불",
      "priority": 78.9, "grade": "P1",
      "f_score": 100, "s_score": 68.9, "t_score": 56.9,
      "voc_count": 18,
      "trend_insufficient": false,        // true면 T열에 n/a 표기 + 경고 배너
      "is_extension": false,
      "status": "confirmed"               // "draft"면 "잠정" 배지
      // f_contrib/s_contrib/t_contrib 생략 시 score×가중치로 자동 계산
    }
  ],

  "extensions": [                         // 확장 마법사로 추가된 것만. 없으면 [] 
    { "code": "K", "name": "재고·물류 가용성",
      "status": "confirmed",              // "confirmed" | "draft"
      "real_evidence_count": 4 }
  ],

  "topics": [                             // 상세를 보여줄 토픽 (보통 P1·P2)
    { "code": "C", "name": "반품·교환·환불", "grade": "P1", "priority": 78.9,
      "hypotheses": [
        { "id": "C-c1", "text": "배송 중 파손 (포장 기준 미달)",
          "cause_tags": ["[택배사]", "[판매자]"],
          "evidence": [
            { "voc_id": "7K2M9", "text": "박스가 찌그러진 채로 와서..." }
          ]}
      ],
      "deliverables": [
        { "id": "C-a1",
          "title": "반품·교환 프로세스 SLA 설정 및 자동 알림",
          "route": "Jira",                // 전달처. 선택
          "owner": "CS팀",                 // 담당. 선택
          "body_md": "## 배경\n...\n\n| 조건 | 기대 동작 |\n|---|---|\n| ... | ... |"
        }
      ]}
  ],

  "validation": [                         // 게이트 통과 기록
    { "label": "컬럼 매핑 확인 (00단계)", "status": "pass", "note": "사용자 확인 후 진행" },
    { "label": "추세(T) 산출", "status": "warn", "note": "8개 중 7개 산출 불가" }
    // status: "pass" | "warn"
  ]
}
```

---

## 문체 규칙 — 개조식 (필수)

이 리포트는 **사내 공유용 보고서**다. 데이터에 넣는 모든 텍스트
(`meta.caveat`, `summary.tiles[].sub`, `validation[].note`, `body_md` 등)는
**개조식(명사형 종결)**으로 작성한다. 템플릿이 자동 생성하는 문구는
이미 개조식으로 고정되어 있으므로, 데이터 쪽만 맞추면 된다.

| 구분 | ✗ 사용 금지 | ✓ 사용 |
|---|---|---|
| 종결 | ~했습니다 / ~하세요 / ~합니다 | ~함 / ~임 / ~필요 / ~요망 / 명사 종결 |
| 예시 | "실제 의사결정 근거로 쓸 수 없습니다." | "실제 의사결정 근거로 사용 불가." |
| 예시 | "표본이 부족해 산출하지 못했습니다." | "표본 부족으로 산출 불가." |
| 예시 | "내부 확인 후 확정하세요." | "내부 확인 후 확정 요망." |

질문형·구어체 제목(예: "무엇이 얼마나 들어왔는가")은 사용하지 않는다.

---

## body_md 작성 규칙

`deliverables[].body_md`는 마크다운으로 쓴다. 템플릿의 내장 렌더러가 지원하는 문법:

| 문법 | 지원 |
|---|---|
| `## 제목` | ✅ (h1~h6 모두 같은 크기로 렌더) |
| `- 목록` / `* 목록` | ✅ |
| `\| 표 \|` (구분선 `\|---\|` 필수) | ✅ |
| `**굵게**` | ✅ |
| `` `코드` `` | ✅ |
| 일반 문단 | ✅ |
| 줄 첫머리의 `**굵게**` (예: `**[AI 추론 · 협의 후 확정]** ...`) | ✅ (표기 규칙 3단이 이 형태다) |
| 중첩 목록·이미지·링크·인용문 | ❌ 사용하지 말 것 |

**표기 규칙 3단**을 body_md 안에 그대로 유지한다:
- `**[Human 확정]**` — 사람이 확정한 값
- `**[AI 생성 불가 · 내부 확인 필수]**` — 값을 비워두고 확인 요청
- `**[AI 추론 · 협의 후 확정]**` — 추정값 제시, 협의 필요 명시

---

## 검증 체크

리포트 생성 후 반드시 확인:

- [ ] `output/report.html`에 `const DATA = {` 가 있는가 (치환 성공)
- [ ] `"/*__REPORT_DATA__*/ null"` 문자열이 남아있지 않은가
- [ ] 파일 크기가 템플릿(약 34KB)보다 큰가
- [ ] 사용자에게 **파일 경로를 안내**했는가

## 프라이버시 경고 (사용자에게 반드시 전달)

`output/report.html`에는 **고객 발화 원문이 인라인으로 포함**된다.
외부 공유·커밋 전에 반드시 내용을 검토하도록 안내한다.
