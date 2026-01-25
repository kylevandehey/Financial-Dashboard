# src/pages.py

from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class PageDef:
    key: str
    label: str
    icon: str

PAGES: list[PageDef] = [
    PageDef(key="dashboard", label="Dashboard", icon="📊"),
    PageDef(key="transactions", label="Transactions", icon="🧾"),
    PageDef(key="insights", label="Insights", icon="🧠"),
    PageDef(key="loan_tracker", label="Loan Tracker", icon="🏠"),
    PageDef(key="tools", label="Tools", icon="🛠️"),
    PageDef(key="assistance", label="Assistance", icon="💬"),
]
