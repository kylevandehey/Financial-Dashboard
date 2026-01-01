import io

import pytest

from src.ingest import normalize_accounts


def test_infers_type_from_account_type_column():
    csv_content = """account_name,account_type,subtype,balance
Everyday Checking,checking account,checking,1500
Travel Card,credit card,credit card,2500
Home Loan,mortgage,secured loan,-350000
"""
    df = normalize_accounts(io.StringIO(csv_content))

    assert list(df["type"].unique()) == ["Asset", "Credit", "Liability"]
    assert bool(df.loc[df["account"] == "Travel Card", "is_liability"].iloc[0]) is True
    assert bool(df.loc[df["account"] == "Everyday Checking", "is_asset"].iloc[0]) is True
    # Mortgage should be treated as liability with negative signed balance
    mortgage_balance = df.loc[df["account"] == "Home Loan", "signed_balance"].iloc[0]
    assert mortgage_balance < 0


def test_raises_when_no_classification_columns():
    csv_content = """account,balance
Primary,1000
"""
    with pytest.raises(ValueError) as excinfo:
        normalize_accounts(io.StringIO(csv_content))

    message = str(excinfo.value)
    assert "could not be normalized" in message
    assert "account_type, subtype, or category" in message
