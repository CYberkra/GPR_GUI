# GPR GUI (Minimal Prototype)

This is a minimal Tkinter-based GUI to load CSV, display B-scan, and apply basic processing methods from `PythonModule_core`.

## Features
- Import CSV
- Display B-scan (matplotlib)
- Fixed method list (order required)
- Apply selected method (calls `PythonModule_core` functions)
- Info/notes text box

## Requirements
- Python 3.8+
- numpy
- pandas
- matplotlib
- tkinter (usually included with Python)

Install deps:
```bash
pip install numpy pandas matplotlib
```

## Run
From repo root:
```bash
python app.py
```


## Sample data
- Example B-scan CSV: `sample_data/sample_bscan.csv`

How to verify:
1) Run `python app.py`
2) Click **Import CSV** and select `sample_data/sample_bscan.csv`
3) The B-scan should render in the right panel

## Notes
- Output CSV/PNG are saved under `output/` in this repo.
- Default parameters are minimal placeholders; adjust inside `app.py` as needed.
- `read_file_data.py` is included locally so `PythonModule_core` imports succeed.

## Repo layout
- `app.py` — main GUI
- `read_file_data.py` — minimal CSV IO helpers
- `output/` — generated results
