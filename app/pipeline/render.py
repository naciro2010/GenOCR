"""Rendering utilities for turning table results into HTML and JSON."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import List

from .native import TableExtraction

TABLE_STYLE = """
<style>
.table-card { margin-top: 1.5rem; }
.table-card h3 { font-weight: 600; margin-bottom: 0.5rem; }
.table-card table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.table-card th, .table-card td { border: 1px solid #e5e7eb; padding: 0.5rem; font-size: 0.875rem; }
.table-card tbody tr:nth-child(odd) { background-color: #f9fafb; }
.table-card caption { text-align: left; font-weight: 600; margin-bottom: 0.5rem; }
</style>
"""


def render_tables(tables: List[TableExtraction]) -> tuple[str, dict]:
    if not tables:
        html = "<p class=\"text-sm text-gray-600\">No tables detected.</p>"
        return html, {"tables": []}

    fragments = [TABLE_STYLE]
    metadata = {"tables": []}
    for table in tables:
        fragments.append(
            """
            <div class="table-card">
              <h3>Page {page} – Table {order} <span class="text-xs text-slate-500">({flavor})</span></h3>
              {html}
            </div>
            """.format(page=table.page, order=table.order, flavor=table.flavor, html=table.html)
        )
        metadata["tables"].append(asdict(table))
    return "\n".join(fragments), metadata


def serialize_metadata(metadata: dict) -> str:
    return json.dumps(metadata, indent=2, ensure_ascii=False)

