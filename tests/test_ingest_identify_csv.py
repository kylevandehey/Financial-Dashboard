import io

from src.ingest import identify_csv_roles


def test_identify_csv_roles_success():
    transactions = io.BytesIO(
        b"Date,Amount,Merchant,Category,Account\n2024-01-01,10.50,Store,Groceries,Checking\n"
    )
    balances = io.BytesIO(b"Date,Balance,Account\n2024-01-01,5000,Checking\n")

    tx_file, bal_file, diagnostics, error_message = identify_csv_roles([transactions, balances])

    assert error_message is None
    assert tx_file is not None
    assert bal_file is not None
    assert len(diagnostics) == 2


def test_identify_csv_roles_reports_missing_columns():
    only_transactions = io.BytesIO(b"Date,Amount,Merchant\n2024-01-01,10.50,Store\n")
    incomplete_balances = io.BytesIO(b"Date,Account\n2024-01-01,Checking\n")

    tx_file, bal_file, diagnostics, error_message = identify_csv_roles([only_transactions, incomplete_balances])

    assert tx_file is not None
    assert bal_file is None
    assert "Could not identify both required CSVs." in error_message
    # Ensure diagnostics includes missing balance requirement
    assert any("balance" in missing for detection in diagnostics for missing in detection.balances_missing)
