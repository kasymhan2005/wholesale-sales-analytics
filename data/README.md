# Data source

The local delivery includes the user's supplied educational data from karpov.courses:
`data(2).zip` (382 CSV files) and `usd_rate.txt` from `final_project_python (1).zip`.
Original rows are preserved under `raw/data/orders`, `raw/data/products` and
`raw/usd_rate.txt`. The supplied course notebook is not redistributed.

To reproduce without bundled data, place the extracted `data` folder inside
`data/raw/` and put `usd_rate.txt` alongside it, then run `python run_analysis.py`.

These are educational records, not verified commercial operations. The course
provider owns its source materials. Redistribution rights have not been established.
Raw data and detailed order-level exports are excluded by `.gitignore`; review
permission before adding them to a public repository. The downloadable delivery
contains them for the user's local reproduction.
