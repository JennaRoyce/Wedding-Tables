#!/usr/bin/env python3

"""Extract a normalized guest list from the Excel workbook without dependencies."""

from __future__ import annotations

import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict
from pathlib import Path

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")
NORMALIZED_HEADERS = [
    "guest_id",
    "name",
    "group",
    "source_column",
    "source_row",
    "is_plus_one",
]


def read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iterfind(".//a:t", NS))
        for item in root.findall("a:si", NS)
    ]


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value_node = cell.find("a:v", NS)
    if value_node is None:
        return ""

    value = value_node.text or ""
    if cell.get("t") == "s" and value:
        value = shared_strings[int(value)]

    return " ".join(value.split())


def resolve_sheet_path(workbook_zip: zipfile.ZipFile, sheet_ref: str | int) -> str:
    workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    workbook_rels_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))

    sheets = workbook_root.findall("a:sheets/a:sheet", NS)
    if isinstance(sheet_ref, int):
        if sheet_ref < 1 or sheet_ref > len(sheets):
            raise ValueError(f"Sheet index {sheet_ref} is out of range.")
        sheet = sheets[sheet_ref - 1]
    else:
        sheet = next((entry for entry in sheets if entry.get("name") == sheet_ref), None)
        if sheet is None:
            raise ValueError(f"Sheet named {sheet_ref!r} was not found.")

    relationship_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    for relation in workbook_rels_root.findall("r:Relationship", REL_NS):
        if relation.get("Id") == relationship_id:
            target = relation.get("Target")
            if not target:
                break
            normalized = target[1:] if target.startswith("/") else f"xl/{target}"
            return normalized

    raise ValueError(f"Could not resolve workbook path for sheet reference {sheet_ref!r}.")


def load_normalized_guests(sheet: ET.Element, shared_strings: list[str]) -> list[dict[str, object]]:
    rows = sheet.findall(".//a:sheetData/a:row", NS)
    if not rows:
        return []

    header_cells: dict[str, str] = {}
    for cell in rows[0].findall("a:c", NS):
        match = CELL_REF_RE.fullmatch(cell.get("r", ""))
        if not match:
            continue
        column, _ = match.groups()
        header_cells[column] = cell_value(cell, shared_strings)

    ordered_headers = [header_cells.get(column, "") for column in sorted(header_cells)]
    if ordered_headers[: len(NORMALIZED_HEADERS)] != NORMALIZED_HEADERS:
        return []

    guests: list[dict[str, object]] = []
    for row in rows[1:]:
        values: dict[str, str] = {}
        for cell in row.findall("a:c", NS):
            match = CELL_REF_RE.fullmatch(cell.get("r", ""))
            if not match:
                continue
            column, _ = match.groups()
            header = header_cells.get(column)
            if not header:
                continue
            values[header] = cell_value(cell, shared_strings)

        if not any(values.values()):
            continue

        guests.append(
            {
                "guest_id": int(values["guest_id"]),
                "name": values["name"],
                "group": values["group"],
                "source_column": values["source_column"],
                "source_row": int(values["source_row"]),
                "is_plus_one": values["is_plus_one"].strip().lower() in {"1", "true", "yes"},
            }
        )

    return guests


def load_grouped_guests(workbook_path: Path, sheet_ref: str | int = 1) -> list[dict[str, object]]:
    with zipfile.ZipFile(workbook_path) as workbook_zip:
        shared_strings = read_shared_strings(workbook_zip)
        sheet_path = resolve_sheet_path(workbook_zip, sheet_ref)
        sheet = ET.fromstring(workbook_zip.read(sheet_path))
        normalized_guests = load_normalized_guests(sheet, shared_strings)
        if normalized_guests:
            return normalized_guests
        grouped_cells: OrderedDict[str, dict[int, str]] = OrderedDict()

        for row in sheet.findall(".//a:sheetData/a:row", NS):
            for cell in row.findall("a:c", NS):
                match = CELL_REF_RE.fullmatch(cell.get("r", ""))
                if not match:
                    continue

                column, row_number = match.groups()
                value = cell_value(cell, shared_strings)
                if not value:
                    continue

                grouped_cells.setdefault(column, {})[int(row_number)] = value

    guests: list[dict[str, object]] = []
    guest_id = 1

    for column, rows in grouped_cells.items():
        group_name = rows[1]
        for row_number in sorted(row for row in rows if row > 1):
            name = rows[row_number]
            guests.append(
                {
                    "guest_id": guest_id,
                    "name": name,
                    "group": group_name,
                    "source_column": column,
                    "source_row": row_number,
                    "is_plus_one": "+1" in name,
                }
            )
            guest_id += 1

    return guests


def write_outputs(guests: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "guest-list.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "guest_id",
                "name",
                "group",
                "source_column",
                "source_row",
                "is_plus_one",
            ],
        )
        writer.writeheader()
        writer.writerows(guests)

    group_counts: OrderedDict[str, int] = OrderedDict()
    plus_one_count = 0
    for guest in guests:
        group = str(guest["group"])
        group_counts[group] = group_counts.get(group, 0) + 1
        plus_one_count += int(bool(guest["is_plus_one"]))

    summary = {
        "guest_count": len(guests),
        "plus_one_count": plus_one_count,
        "groups": [
            {"group": group_name, "count": count}
            for group_name, count in group_counts.items()
        ],
    }

    (output_dir / "guest-list.json").write_text(
        json.dumps(guests, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "guest-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    workbook_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("GuestListForSeatingChart.xlsx")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data")
    sheet_ref_arg = sys.argv[3] if len(sys.argv) > 3 else "1"
    sheet_ref: str | int = int(sheet_ref_arg) if sheet_ref_arg.isdigit() else sheet_ref_arg

    guests = load_grouped_guests(workbook_path, sheet_ref)
    write_outputs(guests, output_dir)
    print(f"Exported {len(guests)} guests from sheet {sheet_ref_arg} to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
