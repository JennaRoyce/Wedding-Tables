# Wedding-Tables

Interactive seating planner for Jenna and Tyler's reception.

## Run locally

```bash
python3 server.py
```

Then open `http://127.0.0.1:8000/ballroom-mockup.html`.

## What is here

- `ballroom-mockup.html`: the drag-and-drop seating app
- `server.py`: local server with save/load API
- `data/seating-layout.json`: saved seating assignments that can be committed and shared
- `data/guest-list.json`: embedded guest source data

## Saving

When you run the app through `server.py`, table assignments save into `data/seating-layout.json` so the latest layout can be committed to GitHub and picked up on another machine.
