"""Native PDF table extraction using Camelot."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import camelot
import pandas as pd


@dataclass
class TableExtraction:
    page: int
    order: int
    flavor: str
    html: str
    data: List[List[str]]


def _table_to_payload(table: camelot.core.Table, flavor: str) -> TableExtraction:
    html = table.to_html()
    df = table.df.replace({pd.NA: "", None: ""})
    data = df.values.tolist()
    return TableExtraction(
        page=int(table.page),
        order=int(table.order),
        flavor=flavor,
        html=html,
        data=data,
    )


def extract_tables(pdf_path: Path, flavors: Iterable[str] | None = None) -> List[TableExtraction]:
    flavors = tuple(flavors or ("lattice", "stream"))
    results: List[TableExtraction] = []
    for flavor in flavors:
        try:
            tables = camelot.read_pdf(
                pdf_path.as_posix(),
                pages="all",
                flavor=flavor,
                edge_tol=500,
                strip_text="\n",
                process_background=True,
            )
        except Exception:
            continue
        for table in tables:
            payload = _table_to_payload(table, flavor)
            results.append(payload)
        if results:
            break
    return results

