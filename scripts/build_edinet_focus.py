"""Extract a focused, machine-readable view of selected EDINET taxonomy elements.

Reads ``data/sources/edinet-taxonomy-<YEAR>/1e_ElementList.xlsx`` and emits
``data/derived/edinet_taxonomy_focus.json`` containing only the elements used by
J-FIBO and the benchmark cases, with bilingual labels and taxonomy metadata.

Run:
    uv run python scripts/build_edinet_focus.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

REPO = Path(__file__).resolve().parents[1]

DEFAULT_FOCUS = {
    "ShareholdingsTextBlock",
    "DetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompanyTable",
    "NameOfSecuritiesDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "NumberOfSharesHeldDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "BookValueDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "PurposesOfHoldingDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "OverviewOfBusinessAllianceDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "QuantitativeEffectsOfShareholdingDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "ReasonForIncreaseInNumberOfSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "MajorShareholdersTextBlock",
    "AnnexedDetailedScheduleOfBorrowingsFinancialStatementsTextBlock",
    "AnnexedConsolidatedDetailedScheduleOfBorrowingsTextBlock",
    "SecurityCodeDEI",
    "EDINETCodeDEI",
    "FilerNameInJapaneseDEI",
    "DocumentTypeDEI",
    "CurrentFiscalYearStartDateDEI",
    "CurrentFiscalYearEndDateDEI",
    # jppfs core borrowings elements
    "LongTermLoansPayable",
    "ShortTermLoansPayable",
    "CurrentPortionOfLongTermLoansPayable",
}

EDINET_NAMESPACES = {
    "jpdei_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpdei/2013-08-31/jpdei_cor",
    "jpcrp_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jpcrp/2025-11-01/jpcrp_cor",
    "jppfs_cor": "http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/2025-11-01/jppfs_cor",
}


def collect_from_workbook(path: Path, focus: set[str]) -> list[dict[str, object]]:
    wb = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for ws in wb.worksheets:
        for r, row in enumerate(ws.iter_rows(values_only=True), 1):
            vals = list(row)
            if len(vals) <= 8:
                continue
            element = vals[8]
            prefix = vals[7]
            if not element or element not in focus:
                continue
            key = (str(prefix), str(element))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "sheet": ws.title,
                "row": r,
                "standard_label_ja": vals[0],
                "terse_label_ja": vals[2],
                "standard_label_en": vals[3],
                "terse_label_en": vals[4],
                "prefix": str(prefix),
                "namespace": EDINET_NAMESPACES.get(str(prefix)),
                "element": str(element),
                "type": vals[9],
                "substitution_group": vals[10],
                "period_type": vals[11],
                "abstract": vals[13],
            })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--workbook",
        type=Path,
        default=REPO / "data" / "sources" / "edinet-taxonomy-2026" / "1e_ElementList.xlsx",
    )
    ap.add_argument("--out", type=Path, default=REPO / "data" / "derived" / "edinet_taxonomy_focus.json")
    args = ap.parse_args()
    if not args.workbook.exists():
        print(
            f"workbook not found: {args.workbook}; run scripts/download_edinet_taxonomy.py",
            file=sys.stderr,
        )
        return 2
    rows = collect_from_workbook(args.workbook, DEFAULT_FOCUS)
    account_workbook = args.workbook.parent / "1f_AccountList.xlsx"
    if account_workbook.exists():
        rows += collect_from_workbook(account_workbook, DEFAULT_FOCUS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "source": str(args.workbook.relative_to(REPO)),
        "namespaces": EDINET_NAMESPACES,
        "elements": rows,
    }, ensure_ascii=False, indent=2))
    print(f"wrote {args.out.relative_to(REPO)} ({len(rows)} elements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
