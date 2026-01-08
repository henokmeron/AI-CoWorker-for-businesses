"""
Deterministic fee lookup engine for spreadsheet queries.
Bypasses LLM guessing by directly reading parquet tables and extracting exact cell values.
"""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

import pandas as pd


@dataclass
class FeeQuery:
    age: Optional[int]
    fee_kind: str  # standard | solo | enhanced | complex | core | unknown
    raw_text: str


_AGE_RE = re.compile(r"\b(\d{1,2})\s*[- ]?\s*year\b", re.IGNORECASE)


def parse_fee_query(user_text: str) -> FeeQuery:
    q = (user_text or "").strip()
    ql = q.lower()

    age = None
    m = _AGE_RE.search(ql)
    if m:
        try:
            age = int(m.group(1))
        except Exception:
            age = None

    # Fee-kind intent (explicit beats implicit)
    if "solo" in ql:
        fee_kind = "solo"
    elif "enhanced" in ql or "specialist" in ql or "mild" in ql:
        fee_kind = "enhanced"
    elif "complex" in ql or "severe" in ql:
        fee_kind = "complex"
    elif "core" in ql:
        fee_kind = "core"
    elif "standard" in ql:
        fee_kind = "standard"
    else:
        fee_kind = "unknown"

    # Standard vs Solo guardrail:
    # If user asked for standard/core and did NOT say solo, we must not match solo rows.
    if fee_kind in {"standard", "core"} and "solo" not in ql:
        fee_kind = "standard"

    return FeeQuery(age=age, fee_kind=fee_kind, raw_text=q)


def _age_to_band(age: int) -> Optional[str]:
    if age < 0:
        return None
    if 0 <= age <= 4:
        return "0-4"
    if 5 <= age <= 10:
        return "5-10"
    if 11 <= age <= 15:
        return "11-15"
    if 16 <= age <= 17:
        return "16-17"
    return None


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _format_numeric(v: Any) -> str:
    # Preserve decimals (no rounding)
    try:
        d = Decimal(str(v))
        # Use format to avoid scientific notation
        s = format(d, 'f')
        # Remove trailing zeros and decimal point if not needed
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s
    except (InvalidOperation, ValueError, TypeError):
        return str(v)


def _pick_label_column(df: pd.DataFrame) -> Optional[str]:
    # Pick the most "row-label-like" column (string-heavy)
    best = None
    best_score = -1
    for c in df.columns:
        series = df[c]
        try:
            nonnull = series.dropna()
        except Exception:
            continue
        if nonnull.empty:
            continue
        # score: how many strings and how long they are
        str_mask = nonnull.apply(lambda x: isinstance(x, str))
        str_count = int(str_mask.sum())
        score = str_count
        if score > best_score:
            best_score = score
            best = c
    return best


def _find_age_column(df: pd.DataFrame, age_band: str) -> Optional[str]:
    target = _norm(age_band)
    for c in df.columns:
        if _norm(str(c)) == target:
            return c
    # Sometimes columns are like "0-4", "5-10", etc. inside longer names
    for c in df.columns:
        if target and target in _norm(str(c)):
            return c
    return None


def _row_matches(label: str, fee_kind: str) -> bool:
    l = (label or "").lower()

    if fee_kind == "standard":
        if "solo" in l:
            return False
        return ("standard" in l) or ("core" in l)

    if fee_kind == "solo":
        return "solo" in l

    if fee_kind == "enhanced":
        return ("enhanced" in l) or ("mild" in l)

    if fee_kind == "complex":
        return ("complex" in l) or ("severe" in l)

    return False


def lookup_fee_in_table(df: pd.DataFrame, fq: FeeQuery, entity: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Deterministically locate a single fee cell for queries like:
      - "standard fee for 11 year old"
      - "enhanced fee for 7 year old"
      - "solo fee for 11 year old"
    
    Args:
        df: DataFrame containing the fee table
        fq: FeeQuery with age and fee_kind
        entity: Optional entity (LA name) to filter by - if provided, only return fee if entity exists in table
    
    Returns (fee_string, provenance_dict).
    """
    prov: Dict[str, Any] = {}

    if fq.age is None:
        return None, {"reason": "no_age"}
    age_band = _age_to_band(fq.age)
    if not age_band:
        return None, {"reason": "age_out_of_supported_bands", "age": fq.age}
    prov["age_band"] = age_band

    if fq.fee_kind not in {"standard", "solo", "enhanced", "complex", "core"}:
        return None, {"reason": "unsupported_fee_kind", "fee_kind": fq.fee_kind}

    # CRITICAL: If entity is provided, verify it exists in this table before proceeding
    if entity:
        entity_norm = _norm(entity)
        entity_found = False
        # Check all columns for the entity
        for col in df.columns:
            col_str = df[col].astype(str).str.lower()
            if col_str.str.contains(entity_norm, na=False, regex=False).any():
                entity_found = True
                prov["entity_column"] = str(col)
                break
        if not entity_found:
            return None, {"reason": "entity_not_in_table", "entity": entity}

    label_col = _pick_label_column(df)
    if not label_col:
        return None, {"reason": "no_label_column"}

    age_col = _find_age_column(df, age_band)
    if not age_col:
        return None, {"reason": "no_age_column", "age_band": age_band, "columns": [str(c) for c in df.columns]}

    # Find best matching row (ONLY the specific fee type requested)
    candidates = []
    for idx, row in df.iterrows():
        label = row.get(label_col, None)
        if not isinstance(label, str):
            continue
        if _row_matches(label, fq.fee_kind):
            candidates.append((idx, label))

    if not candidates:
        return None, {"reason": "no_matching_row", "fee_kind": fq.fee_kind, "label_col": str(label_col)}

    # Prefer explicit "standard" over "core" if fee_kind=standard
    chosen_idx, chosen_label = candidates[0]
    if fq.fee_kind == "standard":
        for idx, label in candidates:
            if "standard" in label.lower() and "solo" not in label.lower():
                chosen_idx, chosen_label = idx, label
                break

    prov["fee_type_row"] = chosen_label
    prov["label_col"] = str(label_col)
    prov["age_col"] = str(age_col)

    value = df.loc[chosen_idx, age_col]
    if pd.isna(value):
        return None, {"reason": "cell_empty", **prov}

    fee = _format_numeric(value)
    prov["raw_value"] = value
    prov["resolved_value"] = fee
    return fee, prov

