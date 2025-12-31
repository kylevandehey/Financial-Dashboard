import pandas as pd
import pytest

from src.categories import (
    aggregate_expense_categories,
    aggregate_income_categories,
    format_accounting_currency,
    get_all_categories,
    get_top_categories,
)


def sample_transactions():
    return pd.DataFrame(
        {
            "Category": [
                "Rent",
                "Salary",
                "Groceries",
                "Investments",
                "Freelance",
                "Rent",
                "Groceries",
                "Investments",
            ],
            "Amount": [-1500, 5000, -250, 400, 600, -1500, -300, 400],
        }
    )


def test_expense_vs_income_separation():
    transactions = sample_transactions()

    expenses = aggregate_expense_categories(transactions)
    incomes = aggregate_income_categories(transactions)

    assert set(expenses["category"]) == {"Rent", "Groceries"}
    assert set(incomes["category"]) == {"Salary", "Investments", "Freelance"}

    rent_row = expenses[expenses["category"] == "Rent"].iloc[0]
    assert rent_row["total_amount"] == -3000
    assert rent_row["transaction_count"] == 2

    salary_row = incomes[incomes["category"] == "Salary"].iloc[0]
    assert salary_row["total_amount"] == 5000
    assert salary_row["transaction_count"] == 1


def test_top_n_ordering_by_absolute_value():
    expenses = aggregate_expense_categories(sample_transactions())
    top_two = get_top_categories(expenses, n=2)

    assert list(top_two["category"]) == ["Rent", "Groceries"]
    assert top_two.iloc[0]["total_amount"] == -3000
    assert top_two.iloc[1]["total_amount"] == -550


def test_accounting_formatting_rules():
    assert format_accounting_currency(-2450) == "($2,450.00)"
    assert format_accounting_currency(1234.5) == "$1,234.50"
    assert format_accounting_currency(0) == "$0.00"
    assert format_accounting_currency(float("nan")) == "$0.00"


def test_empty_category_handling():
    empty_df = pd.DataFrame(columns=["Category", "Amount"])
    expenses = aggregate_expense_categories(empty_df)
    top = get_top_categories(expenses)

    assert expenses.empty
    assert top.empty
    assert list(expenses.columns) == ["category", "total_amount", "transaction_count"]


def test_mixed_sign_categories_only_count_requested_sign():
    transactions = pd.DataFrame(
        {
            "Category": ["Mixed", "Mixed", "IncomeOnly"],
            "Amount": [-100, 75, 200],
        }
    )

    expenses = aggregate_expense_categories(transactions)
    incomes = aggregate_income_categories(transactions)

    assert expenses.iloc[0]["category"] == "Mixed"
    assert expenses.iloc[0]["total_amount"] == -100
    assert expenses.iloc[0]["transaction_count"] == 1

    ordered_income = get_all_categories(incomes)
    assert list(ordered_income["category"]) == ["IncomeOnly", "Mixed"]
