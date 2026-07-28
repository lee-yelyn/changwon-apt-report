"""디딤돌 대출 추정 (가정치 — 실제 한도·금리는 조건별 상이)."""
from __future__ import annotations

# 디딤돌 한도(만원)·LTV 가정치. 신혼·다자녀·신생아 특례 등은 추가 상향. 본인 조건별 상이.
DDIMDOL_CAP = 25000          # 일반 한도 2.5억
LTV = 0.70                   # 일반 LTV 70%
DDIMDOL_CAP_FIRST = 30000    # 생애최초 한도 3억
LTV_FIRST = 0.80             # 생애최초 LTV 80%


def estimate(price_manwon, trade_type):
    """매매 매물 → 일반·생애최초 디딤돌 추정. 전세/실패 시 None."""
    if trade_type != "매매" or not price_manwon:
        return None
    loan = min(int(price_manwon * LTV), DDIMDOL_CAP)
    first_loan = min(int(price_manwon * LTV_FIRST), DDIMDOL_CAP_FIRST)
    return {
        "loan": loan, "cash": price_manwon - loan, "ltv_pct": int(LTV * 100),
        "first_loan": first_loan, "first_cash": price_manwon - first_loan,
        "first_ltv_pct": int(LTV_FIRST * 100),
    }
