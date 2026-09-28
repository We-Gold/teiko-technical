# Loblaw Bio Analysis

## Running the project

Follow these steps in GitHub Codespaces.

```bash
make setup      
make pipeline 
make dashboard
```

`make pipeline` has to run before `make dashboard`. The dashboard reads results that the pipeline stored in the database.

## Dashboard

Once `make dashboard` is running, open **http://localhost:2718**.

In GitHub Codespaces, `.devcontainer/devcontainer.json` forwards port 2718 and opens the dashboard in the browser.

The dashboard has one tab per part of the problem.

To view the full analysis notebook with its code, run `make view-analysis` and open http://localhost:2717.

_Note: the analysis is in a marimo notebook, which is executed as a Python script in `make pipeline`. However, it is easier to read it as a notebook, hence the instruction above._

## Database schema

`load_data.py` normalizes each CSV row into three tables to avoid redundancy:

- **`subjects`**: one row per subject (`id`, `condition`, `age`, `sex`, `treatment`, `response`, `project`)
- **`samples`**: one row per sample (`id`, `sample_type`, `time_from_treatment_start`, `subject_id` → `subjects.id`)
- **`cell_counts`**: one row per sample and population (`sample_id` → `samples.id`, `population`, `count`)
