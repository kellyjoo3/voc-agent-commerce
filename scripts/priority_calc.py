#!/usr/bin/env python3
"""
priority_calc.py — F/S/T/Priority 계산 스크립트 (PROJECT_SPEC.md §6 확정 사양 구현)

이 스크립트는 호스트 AI(Claude Code 등)가 "직접 암산하지 말고 반드시 실행"해야 하는
계산 전용 스크립트다. Topic 분류·Sentiment 분류 등 "의미 판단"은 호스트 AI가 하고,
이 스크립트는 그 결과(CSV)를 받아 F_score / S_score / T_score / Priority만 계산한다.

표준 라이브러리(csv, json, argparse, statistics)만 사용한다. 별도 설치 불필요.

사용법:
    python scripts/priority_calc.py \
        --input output/03_classified.csv \
        --config configs/commerce_cs.json \
        --output output/04_priority.csv

입력 CSV 필수 컬럼:
    voc_id, topic, sentiment
선택 컬럼 (Trend 계산에 사용, 없으면 T_score는 전부 50 중립 처리):
    created_at (YYYY-MM-DD 등 파싱 가능한 날짜 문자열)

출력 CSV 컬럼 (PROJECT_SPEC.md §6.5):
    topic, voc_count, frequency_pct, f_score, s_score, t_score,
    severity_raw, trend_raw_pct, trend_insufficient, priority, priority_grade
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from statistics import mean


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_rows(input_path):
    with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise ValueError(f"입력 파일에 데이터가 없습니다: {input_path}")
    for col in ("voc_id", "topic", "sentiment"):
        if col not in rows[0]:
            raise ValueError(
                f"입력 CSV에 필수 컬럼 '{col}'이 없습니다. "
                f"현재 컬럼: {list(rows[0].keys())}"
            )
    return rows


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value[: len(fmt) + 2], fmt)
        except ValueError:
            continue
    return None


def sentiment_score_map(config):
    return {item["label"]: item["score"] for item in config["sentiment_scale"]}


def t_score_from_anchors(trend_raw_pct, anchors):
    """anchors: [{trend_raw_pct, t_score}, ...] 오름차순. 구간 선형보간, 양끝은 클램프."""
    anchors = sorted(anchors, key=lambda a: a["trend_raw_pct"])
    if trend_raw_pct <= anchors[0]["trend_raw_pct"]:
        return float(anchors[0]["t_score"])
    if trend_raw_pct >= anchors[-1]["trend_raw_pct"]:
        return float(anchors[-1]["t_score"])
    for a, b in zip(anchors, anchors[1:]):
        if a["trend_raw_pct"] <= trend_raw_pct <= b["trend_raw_pct"]:
            span = b["trend_raw_pct"] - a["trend_raw_pct"]
            frac = (trend_raw_pct - a["trend_raw_pct"]) / span
            return a["t_score"] + frac * (b["t_score"] - a["t_score"])
    return 50.0  # 도달 불가하지만 안전망


def compute_trend(rows, topics, min_sample_per_period):
    """created_at이 있으면 전체 기간을 중앙값 기준 직전/최근 2구간으로 나눠 Trend_raw(%)를 계산한다.
    created_at이 없거나 파싱 불가하면 모든 topic에 대해 (None, insufficient=True)를 반환한다."""
    dated = [(r, parse_date(r.get("created_at"))) for r in rows]
    dated = [(r, d) for r, d in dated if d is not None]

    if len(dated) < 2:
        return {t: (None, True) for t in topics}

    dates_sorted = sorted(d for _, d in dated)
    mid = dates_sorted[len(dates_sorted) // 2]

    prev_period = [r for r, d in dated if d < mid]
    recent_period = [r for r, d in dated if d >= mid]

    prev_total = len(prev_period)
    recent_total = len(recent_period)

    result = {}
    for t in topics:
        prev_count = sum(1 for r in prev_period if r["topic"] == t)
        recent_count = sum(1 for r in recent_period if r["topic"] == t)

        if prev_count < min_sample_per_period or recent_count < min_sample_per_period:
            result[t] = (None, True)
            continue

        prev_share = (prev_count / prev_total * 100) if prev_total else 0
        recent_share = (recent_count / recent_total * 100) if recent_total else 0

        if prev_share == 0:
            result[t] = (None, True)
            continue

        trend_raw_pct = (recent_share - prev_share) / prev_share * 100
        result[t] = (trend_raw_pct, False)

    return result


def main():
    parser = argparse.ArgumentParser(description="VOC F/S/T/Priority 계산 (PROJECT_SPEC.md §6)")
    parser.add_argument("--input", required=True, help="분류된 VOC CSV (voc_id, topic, sentiment[, created_at])")
    parser.add_argument("--config", default="configs/commerce_cs.json", help="commerce_cs.json 경로")
    parser.add_argument("--output", required=True, help="출력 CSV 경로")
    args = parser.parse_args()

    config = load_config(args.config)
    rows = load_rows(args.input)

    pf = config["priority_formula"]
    weights = pf["weights"]
    f_cap_pct = pf["F_cap_pct"]
    anchors = pf["trend_score_anchors"]
    min_sample = pf["trend_min_sample_per_period"]
    insufficient_t = pf["trend_insufficient_score"]
    top_n = pf["grade_rule"]["top_n"]
    threshold = pf["grade_rule"]["threshold"]

    sent_map = sentiment_score_map(config)
    unknown_sentiments = {r["sentiment"] for r in rows} - set(sent_map.keys())
    if unknown_sentiments:
        print(
            f"[경고] config에 없는 sentiment 라벨 발견: {unknown_sentiments} "
            f"— 이 행들은 Severity 계산에서 제외됩니다.",
            file=sys.stderr,
        )

    total = len(rows)
    topics = sorted(set(r["topic"] for r in rows))

    trend_by_topic = compute_trend(rows, topics, min_sample)

    results = []
    for topic in topics:
        topic_rows = [r for r in rows if r["topic"] == topic]
        voc_count = len(topic_rows)
        frequency_pct = voc_count / total * 100

        f_score = min(frequency_pct / f_cap_pct, 1) * 100

        scores = [sent_map[r["sentiment"]] for r in topic_rows if r["sentiment"] in sent_map]
        severity_raw = mean(scores) if scores else 0.0
        s_score = severity_raw / 5 * 100

        trend_raw_pct, insufficient = trend_by_topic.get(topic, (None, True))
        if insufficient:
            t_score = insufficient_t
        else:
            t_score = t_score_from_anchors(trend_raw_pct, anchors)

        priority = weights["F"] * f_score + weights["S"] * s_score + weights["T"] * t_score

        results.append({
            "topic": topic,
            "voc_count": voc_count,
            "frequency_pct": round(frequency_pct, 2),
            "f_score": round(f_score, 1),
            "s_score": round(s_score, 1),
            "t_score": round(t_score, 1),
            "severity_raw": round(severity_raw, 2),
            "trend_raw_pct": round(trend_raw_pct, 1) if trend_raw_pct is not None else "",
            "trend_insufficient": insufficient,
            "priority": round(priority, 1),
        })

    results.sort(key=lambda r: r["priority"], reverse=True)
    for idx, r in enumerate(results):
        if idx < top_n and r["priority"] >= threshold:
            r["priority_grade"] = "P1"
        elif r["priority"] >= threshold:
            r["priority_grade"] = "P2"
        else:
            r["priority_grade"] = "P3"

    fieldnames = [
        "topic", "voc_count", "frequency_pct", "f_score", "s_score", "t_score",
        "severity_raw", "trend_raw_pct", "trend_insufficient", "priority", "priority_grade",
    ]
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"[완료] {len(results)}개 Topic 계산 완료 → {args.output}")
    print(f"[안내] Priority는 실행 순서가 아니다 (PROJECT_SPEC.md §6.4). "
          f"S_score 최고 Topic이 P1/P2에 없으면 원인가설 대상에 별도 추가할 것 (§9).")

    max_s_topic = max(results, key=lambda r: r["s_score"])["topic"]
    top_n_topics = {r["topic"] for r in results[:top_n]}
    if max_s_topic not in top_n_topics:
        print(f"[안내] S_score 최고 Topic '{max_s_topic}'이 상위 {top_n}위 밖입니다. "
              f"원인가설 분석 대상에 추가하십시오 (PROJECT_SPEC.md §9 대상 선정 규칙).")


if __name__ == "__main__":
    main()
