# Wedding-Tables

Interactive seating planner for Jenna and Tyler's reception.

## What this app does

This repo contains a browser-based seating planner for the wedding reception. It has two main views:

- `ballroom-mockup.html`: the interactive drag-and-drop seating app
- `table-roster.html`: a read-only roster view that lists every guest by table and seat

The app is designed so Jenna can own it locally, make changes directly in the HTML files, and commit updated seating data back to GitHub whenever needed.

## Current functionality

- Drag guests onto numbered table seats
- Move seated guests between tables
- Remove guests from tables by dragging them back to the unseated area
- Save seat assignments into a real project file instead of only browser storage
- Link multiple guests together so they move as a group
- View a roster-style table summary in a separate HTML page
- Keep guest names color-coded by guest category

## Run locally

From the project folder, run:

```bash
python3 server.py
```

Then open:

- `http://127.0.0.1:8000/ballroom-mockup.html`
- `http://127.0.0.1:8000/table-roster.html`

Use `server.py`, not `python3 -m http.server`, if you want the app to save seating changes into the repo files.

## Main files

- `ballroom-mockup.html`
  Interactive seating app. This is the main UI Jenna will use.
- `table-roster.html`
  Read-only roster/print view built from the saved layout data.
- `server.py`
  Lightweight local server that serves the files and exposes `/api/layout` for save/load.
- `data/seating-layout.json`
  The current saved seating state. This includes:
  - `assignments`
  - `link_groups`
  - `updated_at`
- `data/guest-list.json`
  The normalized guest source list used by the app.
- `data/guest-summary.json`
  Guest totals and category counts.
- `data/venue.json`
  Venue details and constraints.
- `docs/reception-planning.md`
  Layout planning notes and venue assumptions.
- `scripts/extract_guest_list.py`
  Utility for regenerating the normalized guest exports from the Excel workbook.

## Saving and persistence

When the app is running through `server.py`, seat assignments and linked groups are saved to:

- `data/seating-layout.json`

That file can be committed to GitHub, so Jenna can pull the repo on another machine and continue from the latest saved seating arrangement.

If the app is opened without the custom server, it falls back to browser storage only. That is useful as a backup, but the repo-backed workflow is the intended one.

## Linking guests

The app supports linking guests together so they move as a unit.

How it works:

1. Click the small `+` selector next to multiple guests in the right-hand guest column.
2. Click `Link Selected`.
3. Drag any guest in that linked set onto a table seat.
4. The group moves together as long as the destination table has enough open seats.

Additional controls:

- `Unlink Selected`
- `Clear Selected`

Linked groups are also saved into `data/seating-layout.json`.

## Roster view

`table-roster.html` reads the saved seating data and shows:

- every table from 1 to 29
- each seated guest in seat order
- category labels next to each guest
- an `Unseated Guests` section
- a print-friendly layout

This is useful for checking the current arrangement without using the drag-and-drop interface.

## Typical workflow

1. Pull the latest repo changes from GitHub
2. Run `python3 server.py`
3. Open `ballroom-mockup.html`
4. Adjust seating and linked groups
5. Refresh `table-roster.html` to review the results
6. Commit the updated `data/seating-layout.json` and any UI changes
7. Push back to GitHub

## Notes for Jenna

- The app is intentionally simple: plain HTML, CSS, JavaScript, and a tiny Python server.
- Most UI changes will happen in `ballroom-mockup.html` or `table-roster.html`.
- Data persistence behavior lives in `server.py` and `data/seating-layout.json`.
- Guest source data is already normalized, so Jenna does not need to parse the Excel file manually unless the guest list changes.

## If the guest list changes

Regenerate the normalized guest data with:

```bash
python3 scripts/extract_guest_list.py
```

That updates the files in `data/` based on `GuestListForSeatingChart.xlsx`.
