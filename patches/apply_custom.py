#!/usr/bin/env python3
"""Apply exactly one change to upstream Couch TV: display clock +1 hour."""
from pathlib import Path
import sys
root = Path(sys.argv[1])
app = root / "tv-home/web/app.js"
source = app.read_text(encoding="utf-8")
original = "function clock() {\n    var d = new Date(),"
patched = "function clock() {\n    var d = new Date(Date.now() + 3600000),"
if source.count(original) != 1:
    raise RuntimeError("Clock function not found exactly once; refusing other modifications")
app.write_text(source.replace(original, patched, 1), encoding="utf-8")
print("Applied only +1 hour to the Couch TV clock display")
