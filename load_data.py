import sqlite3
from pathlib import Path

import pandas as pd

DATABASE_NAME = "cell-counts"
CSV_PATH = Path("cell-count.csv")


def database_path(database_name: str):
    return Path(f"{database_name}.db")


def initialize_database(database_path: Path, overwrite: bool = True):
    """
    Creates a SQLite database with a schema designed for the data in cell-count.csv.

    Args:
    - database_path (Path): The path of the database
    - overwrite (bool): If false, exits early if the file already exists
    """

    file_exists = database_path.exists()

    # Skip if the file exists, or delete the existing file
    if not overwrite and file_exists:
        return
    elif overwrite and file_exists:
        database_path.unlink(missing_ok=True)

    # Create and connect to the database
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")

    # Create subject table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subject (
        id INTEGER PRIMARY KEY,
        condition TEXT NOT NULL,
        age INTEGER NOT NULL,
        sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
        treatment TEXT NOT NULL,
        response INTEGER CHECK (response IN (0, 1) OR response IS NULL),
        project_id INTEGER NOT NULL
    );
    """)

    # Create sample table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sample (
        id INTEGER PRIMARY KEY,
        sample_type TEXT NOT NULL CHECK (sample_type IN ('PBMC','WB')),
        time_from_treatment_start INTEGER NOT NULL
            CHECK (time_from_treatment_start >= 0),
        b_cell INTEGER NOT NULL CHECK (b_cell >= 0),
        cd8_t_cell INTEGER NOT NULL CHECK (cd8_t_cell >= 0),
        cd4_t_cell INTEGER NOT NULL CHECK (cd4_t_cell >= 0),
        nk_cell INTEGER NOT NULL CHECK (nk_cell >= 0),
        monocyte INTEGER NOT NULL CHECK (monocyte >= 0),
        subject_id INTEGER NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subject(id)
    );
    """)

    conn.commit()
    conn.close()


def populate_database(database_path: Path):
    """
    Populates a SQLite database with values from cell-count.csv

    Args:
    - database_path (Path): The path of the database
    """

    df = pd.read_csv(CSV_PATH)

    # Convert string ids to integers (e.g. "sbj001" -> 1)
    for column in ["project", "subject", "sample"]:
        df[column] = df[column].str.extract(r"(\d+)$", expand=False).astype(int)

    # Convert response to 1/0 (SQLite bool), leaving missing values as NULL
    df["response"] = df["response"].map({"yes": 1, "no": 0}).astype("Int64")

    # Split the data into subject and sample tables
    subjects = (
        df[["subject", "condition", "age", "sex", "treatment", "response", "project"]]
        .drop_duplicates()
        .rename(columns={"subject": "id", "project": "project_id"})
    )
    samples = df[
        [
            "sample",
            "sample_type",
            "time_from_treatment_start",
            "b_cell",
            "cd8_t_cell",
            "cd4_t_cell",
            "nk_cell",
            "monocyte",
            "subject",
        ]
    ].rename(columns={"sample": "id", "subject": "subject_id"})

    # Connect to the database
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Insert subjects first so sample foreign keys resolve
    subjects.to_sql("subject", conn, if_exists="append", index=False)
    samples.to_sql("sample", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()


def main():
    path = database_path(DATABASE_NAME)

    # Initialize the database file
    initialize_database(path)

    # Populate the database
    populate_database(path)


if __name__ == "__main__":
    main()
