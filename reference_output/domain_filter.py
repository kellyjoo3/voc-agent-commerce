"""SPEC §3 정제 확장: 도메인 적합성 사전 필터.

500건 검증에서 실제 발견된 업종외 혼입 사례를 근거로 키워드 규칙을 구성한다.
삭제하지 않고 격리(제외_업종외 태그)한다. 애매한 나머지는 04 Topic 분류에서
LLM이 판단해 자연스럽게 `기타`로 걸러지도록 그대로 둔다.
"""
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 근거: output/voc_500_classified.csv 의 '기타' 판정 note 43건 실사례
DOMAIN_RULES = {
    "여행/숙박/항공": r"항공권|호텔예약|레저베이션|골프장|라운지 이용|탑승자|국내선|국제선|숙소 배정|여행을 취소|여행 상품",
    "게임": r"영웅|경험치|스테이지|각성|길드|팬텀|게임 유저|접속이 끊긴 카메라",
    "렌탈/구독/대여": r"렌탈 서비스|대여하려고|명의.{0,4}이전|해지하고 싶|의무사용기간|양도 받을만한",
    "통신/개통": r"개통.{0,4}확인서|통신사로|일련번호를 쓰라고|가족.{0,6}추가.{0,6}할인",
    "행정/공공": r"인감을|인감증명|코로나 백신|시설공사|하자 보증기간|주요 공종",
    "B2B/판매자 관점": r"입점 관련|하위거래처|판매 하고 있는 상품이 품절로 인하여|배송 관리로 들어가서 판매 취소",
    "오프라인 서비스 예약": r"전시장에서 견적|레스토랑|런치.{0,4}디너|매장.{0,4}방문.{0,10}예약|상담 예약을 하고 싶은데",
    "디지털콘텐츠/플랫폼": r"다운로드가 안되네요|이용권은 전체일정|팔로우하고 싶은데|카메라도 지난 이벤트",
}

COMPILED = {k: re.compile(v) for k, v in DOMAIN_RULES.items()}


def tag_domain(text: str) -> str | None:
    for label, pat in COMPILED.items():
        if pat.search(text):
            return label
    return None


def main():
    df = pd.read_csv(DATA_DIR / "voc_all.csv")
    df["domain_flag"] = df["text"].apply(tag_domain)

    n_total = len(df)
    n_flagged = df["domain_flag"].notna().sum()
    print(f"전량 {n_total}건 중 사전 필터로 격리: {n_flagged}건 ({n_flagged/n_total*100:.2f}%)")
    print(df["domain_flag"].value_counts())

    out_path = DATA_DIR / "voc_all.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path} (domain_flag 컬럼 추가, 삭제 없음)")


if __name__ == "__main__":
    main()
