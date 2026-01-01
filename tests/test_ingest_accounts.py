import io

import pytest

from src.ingest import normalize_accounts


def test_infers_type_from_account_type_column():
    csv_content = """date,account_name,account_type,subtype,balance
2024-01-01,Everyday Checking,checking account,checking,1500
2024-01-01,Travel Card,credit card,credit card,2500
2024-01-01,Home Loan,mortgage,secured loan,-350000
"""
    df = normalize_accounts(io.StringIO(csv_content))

    assert list(df["type"].unique()) == ["Asset", "Credit", "Liability"]
    assert bool(df.loc[df["account"] == "Travel Card", "is_liability"].iloc[0]) is True
    assert bool(df.loc[df["account"] == "Everyday Checking", "is_asset"].iloc[0]) is True
    # Mortgage should be treated as liability with negative signed balance
    mortgage_balance = df.loc[df["account"] == "Home Loan", "signed_balance"].iloc[0]
    assert mortgage_balance < 0


def test_classifies_using_balance_when_no_metadata():
    csv_content = """date,account,balance
2024-02-01,Primary Checking,2500
2024-02-01,Travel Card,-750
2024-02-01,Zero Account,0
"""
    df = normalize_accounts(io.StringIO(csv_content))

    assert df.loc[df["account"] == "Primary Checking", "type"].iloc[0] == "Asset"
    assert bool(df.loc[df["account"] == "Primary Checking", "is_asset"].iloc[0]) is True
    assert df.loc[df["account"] == "Travel Card", "type"].iloc[0] == "Liability"
    assert bool(df.loc[df["account"] == "Travel Card", "is_liability"].iloc[0]) is True
    assert df.loc[df["account"] == "Zero Account", "type"].iloc[0] == "Asset"


def test_requires_balance_column_when_no_classification_present():
    csv_content = """date,account,category
2024-01-01,Primary Checking,deposit
"""
    with pytest.raises(ValueError) as excinfo:
        normalize_accounts(io.StringIO(csv_content))

    assert "Include Date, Account, and Balance columns" in str(excinfo.value)
