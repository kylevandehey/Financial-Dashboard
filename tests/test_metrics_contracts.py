import pandas as pd
from datetime import date

from src.metrics import build_yearly_balance_trends, summarize_accounts


def _sample_accounts_df() -> pd.DataFrame:
    # Minimal schema required by summarize_accounts + build_yearly_balance_trends
    # signed_balance: assets positive, liabilities negative
    return pd.DataFrame(
        [
            {
                "date": "2025-01-05",
                "account": "Checking",
                "signed_balance": 1000.00,
                "is_asset": True,
                "is_liability": False,
                "subtype": "checking",
            },
            {
                "date": "2025-01-05",
                "account": "Credit Card",
                "signed_balance": -250.00,
                "is_asset": False,
                "is_liability": True,
                "subtype": "credit",
            },
            # Add a later snapshot to ensure end_date selection works
            {
                "date": "2025-06-01",
                "account": "Checking",
                "signed_balance": 1200.00,
                "is_asset": True,
                "is_liability": False,
                "subtype": "checking",
            },
            {
                "date": "2025-06-01",
                "account": "Credit Card",
                "signed_balance": -300.00,
                "is_asset": False,
                "is_liability": True,
                "subtype": "credit",
            },
        ]
    )


def test_summarize_accounts_contract_keys() -> None:
    accounts = _sample_accounts_df()
    summary = summarize_accounts(accounts, end_date=date(2025, 6, 1))

    assert isinstance(summary, dict)
    assert "total_assets" in summary
    assert "total_liabilities" in summary
    assert "net_worth" in summary

    # Basic sanity checks on sign conventions
    assert summary["total_assets"] >= 0
    assert summary["total_liabilities"] <= 0
    assert summary["net_worth"] == summary["total_assets"] + summary["total_liabilities"]


def test_build_yearly_balance_trends_accepts_date_range_and_returns_shape() -> None:
    accounts = _sample_accounts_df()
    date_range = (date(2025, 1, 1), date(2025, 12, 31))

    result = build_yearly_balance_trends(accounts, date_range)

    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["year", "net_worth", "assets", "liabilities"]

    # Should include the year present in the sample dataset
    assert 2025 in result["year"].tolist()
