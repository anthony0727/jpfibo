"""Extract a focused set of facts from an EDINET XBRL instance.

We do not try to be a general XBRL processor. We pull specific concepts that
J-FIBO maps onto Japanese disclosure semantics: DEI metadata, the shareholding
text block, the major-shareholders text block, the borrowings schedule text
block, and the specified-investment-equity holding table (purposes, share
counts, carrying amounts).

The output is a compact JSON per filing under data/edinet/extracted/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "data" / "edinet" / "raw"
OUT_DIR = REPO / "data" / "edinet" / "extracted"

XBRLI_NS = "http://www.xbrl.org/2003/instance"
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
XLINK_NS = "http://www.w3.org/1999/xlink"

# Concepts we want, identified by namespace prefix family + local name.
WANT_DEI: dict[str, str] = {
    "EDINETCodeDEI": "edinet_code",
    "SecurityCodeDEI": "security_code",
    "FilerNameInJapaneseDEI": "filer_name_ja",
    "FilerNameInEnglishDEI": "filer_name_en",
    "DocumentTypeDEI": "document_type",
    "AccountingStandardsDEI": "accounting_standards",
    "CurrentFiscalYearStartDateDEI": "fy_start",
    "CurrentFiscalYearEndDateDEI": "fy_end",
}

WANT_TEXT_BLOCKS: dict[str, str] = {
    "ShareholdingsTextBlock": "shareholdings_text",
    "MajorShareholdersTextBlock": "major_shareholders_text",
    "AnnexedDetailedScheduleOfBorrowingsFinancialStatementsTextBlock": "borrowings_schedule_fs_text",
    "AnnexedConsolidatedDetailedScheduleOfBorrowingsTextBlock": "borrowings_schedule_consolidated_text",
}

WANT_TYPED: set[str] = {
    # Reporting company (提出会社) variants
    "NameOfSecuritiesDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "NumberOfSharesHeldDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "BookValueDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "PurposesOfHoldingDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "PurposeOfShareholdingOverviewOfBusinessAllianceQuantitativeEffectsOfShareholdingAndReasonForIncreaseInNumberOfSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "NumberOfSharesHeldDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "BookValueDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "NameOfSecuritiesDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "PurposeOfShareholdingOverviewOfBusinessAllianceQuantitativeEffectsOfShareholdingAndReasonForIncreaseInNumberOfSharesDetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "NumberOfSharesNotDisclosedAsBelowThresholdDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    "CarryingAmountNotDisclosedAsBelowThresholdDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentReportingCompany",
    # Largest-holding-company (最大保有会社) variants -- used when the reporting
    # entity is a holding company that discloses via its largest subsidiary
    "NameOfSecuritiesDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "NumberOfSharesHeldDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "BookValueDetailsOfSpecifiedInvestmentEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "PurposeOfShareholdingOverviewOfBusinessAllianceQuantitativeEffectsOfShareholdingAndReasonForIncreaseInNumberOfSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "NameOfSecuritiesDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "NumberOfSharesHeldDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "BookValueDetailsOfDeemedHoldingsOfEquitySecuritiesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "PurposeOfShareholdingOverviewOfBusinessAllianceQuantitativeEffectsOfShareholdingAndReasonForIncreaseInNumberOfSharesDetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "WhetherIssuerOfAforementionedSharesHoldsReportingCompanysSharesDetailsOfDeemedHoldingsOfSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "NumberOfSharesNotDisclosedAsBelowThresholdDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
    "CarryingAmountNotDisclosedAsBelowThresholdDetailsOfSpecifiedInvestmentSharesHeldForPurposesOtherThanPureInvestmentLargestHoldingCompany",
}


def parse_period(ctx: etree._Element) -> dict[str, str]:
    period = ctx.find(f"{{{XBRLI_NS}}}period")
    if period is None:
        return {}
    instant = period.find(f"{{{XBRLI_NS}}}instant")
    start = period.find(f"{{{XBRLI_NS}}}startDate")
    end = period.find(f"{{{XBRLI_NS}}}endDate")
    if instant is not None:
        return {"instant": instant.text}
    if start is not None and end is not None:
        return {"start": start.text, "end": end.text}
    return {}


def parse_dimensions(ctx: etree._Element) -> dict[str, str]:
    out: dict[str, str] = {}
    scenario = ctx.find(f"{{{XBRLI_NS}}}scenario")
    segment = ctx.find(f"{{{XBRLI_NS}}}segment")
    for parent in (scenario, segment):
        if parent is None:
            continue
        for dim in parent.findall(f"{{{XBRLDI_NS}}}explicitMember"):
            out[dim.get("dimension")] = dim.text
    return out


def squash_text(s: str | None) -> str | None:
    if s is None:
        return None
    # Text blocks contain inline HTML; remove tags, collapse whitespace.
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def collect_inner_text(el: etree._Element) -> str:
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for child in el:
        parts.append(etree.tostring(child, encoding="unicode", with_tail=True))
    return "".join(parts)


def extract(xbrl_bytes: bytes) -> dict:
    root = etree.fromstring(xbrl_bytes)
    contexts: dict[str, etree._Element] = {}
    facts: list[etree._Element] = []
    for el in root:
        local = etree.QName(el).localname
        if local == "context":
            contexts[el.get("id")] = el
        else:
            facts.append(el)

    dei: dict[str, dict] = {}
    text_blocks: dict[str, list[dict]] = {k: [] for k in WANT_TEXT_BLOCKS.values()}
    typed_rows: list[dict] = []

    for fact in facts:
        local = etree.QName(fact).localname
        ns = etree.QName(fact).namespace or ""
        ctx_id = fact.get("contextRef")
        ctx = contexts.get(ctx_id) if ctx_id else None
        period = parse_period(ctx) if ctx is not None else {}
        dims = parse_dimensions(ctx) if ctx is not None else {}

        # DEI metadata
        if "/jpdei/" in ns and local in WANT_DEI:
            dei[WANT_DEI[local]] = {
                "value": (fact.text or "").strip(),
                "period": period,
            }
            continue

        # Disclosure text blocks
        if "/jpcrp/" in ns and local in WANT_TEXT_BLOCKS:
            key = WANT_TEXT_BLOCKS[local]
            inner = collect_inner_text(fact)
            text_blocks[key].append({
                "context": ctx_id,
                "period": period,
                "dimensions": dims,
                "text": squash_text(inner),
            })
            continue

        # Specified investment equity row facts
        if "/jpcrp/" in ns and local in WANT_TYPED:
            inner = collect_inner_text(fact)
            typed_rows.append({
                "concept": local,
                "context": ctx_id,
                "period": period,
                "dimensions": dims,
                "value": squash_text(inner),
                "unitRef": fact.get("unitRef"),
                "decimals": fact.get("decimals"),
            })
            continue

    return {"dei": dei, "text_blocks": text_blocks, "typed_rows": typed_rows}


def find_instance(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.endswith(".xbrl") and "PublicDoc" in n:
                return n
        raise FileNotFoundError(f"no PublicDoc .xbrl in {zip_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id", nargs="?", help="EDINET docID (S100...); when omitted, process all in data/edinet/raw")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    doc_ids: list[str]
    if args.doc_id:
        doc_ids = [args.doc_id]
    else:
        doc_ids = sorted({p.stem.split(".")[0] for p in RAW_DIR.glob("*.xbrl.zip")})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for doc_id in doc_ids:
        zip_path = RAW_DIR / f"{doc_id}.xbrl.zip"
        if not zip_path.exists():
            print(f"missing {zip_path}", file=sys.stderr)
            continue
        instance = find_instance(zip_path)
        with zipfile.ZipFile(zip_path) as z:
            data = z.read(instance)
        try:
            payload = extract(data)
        except etree.XMLSyntaxError as e:
            print(f"{doc_id}: {e}", file=sys.stderr)
            continue
        payload["doc_id"] = doc_id
        payload["instance"] = instance
        payload["extracted_at"] = dt.datetime.now(dt.UTC).isoformat()
        out = args.out_dir / f"{doc_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(
            f"{doc_id}: DEI={list(payload['dei'])} "
            f"text_blocks={ {k: len(v) for k,v in payload['text_blocks'].items() if v} } "
            f"typed_rows={len(payload['typed_rows'])} -> {out.relative_to(REPO)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
