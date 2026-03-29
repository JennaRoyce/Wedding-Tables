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
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")


def read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iterfind(".//a:t", NS))
        for item in root.findall("a:si", NS)
    ]


def load_grouped_guests(workbook_path: Path) -> list[dict[str, object]]:
    with zipfile.ZipFile(workbook_path) as workbook_zip:
        shared_strings = read_shared_strings(workbook_zip)
        sheet = ET.fromstring(workbook_zip.read("xl/worksheets/sheet1.xml"))
        grouped_cells: OrderedDict[str, dict[int, str]] = OrderedDict()

        for row in sheet.findall(".//a:sheetData/a:row", NS):
            for cell in row.findall("a:c", NS):
                match = CELL_REF_RE.fullmatch(cell.get("r", ""))
                if not match:
                    continue

                column, row_number = match.groups()
                value_node = cell.find("a:v", NS)
                if value_node is None:
                    continue

                value = value_node.text or ""
                if cell.get("t") == "s" and value:
                    value = shared_strings[int(value)]

                value = " ".join(value.split())
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

    guests = load_grouped_guests(workbook_path)
    write_outputs(guests, output_dir)
    print(f"Exported {len(guests)} guests to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
