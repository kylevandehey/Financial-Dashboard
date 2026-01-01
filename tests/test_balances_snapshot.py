from datetime import date

import pandas as pd

from src.metrics import get_balances_snapshot, summarize_accounts


def test_get_balances_snapshot_uses_latest_per_account():
    balances = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-01-15", "2024-03-01"]),
            "account": ["Checking", "Checking", "Travel Card", "Travel Card"],
            "balance": [1000, 1500, -2000, -1000],
            "signed_balance": [1000, 1500, -2000, -1000],
            "is_asset": [True, True, False, False],
            "is_liability": [False, False, True, True],
            "subtype": ["checking", "checking", "credit", "credit"],
        }
    )

    snapshot = get_balances_snapshot(balances, date(2024, 2, 15))

    assert len(snapshot) == 2
    checking_row = snapshot.loc[snapshot["account"] == "Checking"].iloc[0]
    card_row = snapshot.loc[snapshot["account"] == "Travel Card"].iloc[0]
    assert checking_row["balance"] == 1500
    assert card_row["balance"] == -2000  # latest before cutoff, not summed


def test_summarize_accounts_uses_snapshot_for_totals():
    balances = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-02-10"]),
            "account": ["Investments", "Investments"],
            "balance": [5000, 7500],
            "signed_balance": [5000, 7500],
            "is_asset": [True, True],
            "is_liability": [False, False],
            "subtype": ["brokerage", "brokerage"],
        }
    )

    summary = summarize_accounts(balances, end_date=date(2024, 1, 15))

    assert summary["total_assets"] == 5000
    assert summary["total_liabilities"] == 0
    assert summary["net_worth"] == 5000
