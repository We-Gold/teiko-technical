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

    # Create subjects table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id TEXT PRIMARY KEY,
        condition TEXT NOT NULL,
        age INTEGER NOT NULL,
        sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
        treatment TEXT NOT NULL,
        response TEXT CHECK (response IN ('yes', 'no') OR response IS NULL),
        project TEXT NOT NULL
    );
    """)

    # Create samples table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        id TEXT PRIMARY KEY,
        sample_type TEXT NOT NULL CHECK (sample_type IN ('PBMC','WB')),
        time_from_treatment_start INTEGER NOT NULL
            CHECK (time_from_treatment_start >= 0),
        subject_id TEXT NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    );
    """)

    # Create cell counts table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cell_counts (
        sample_id TEXT NOT NULL,
        population TEXT NOT NULL,
        count INTEGER NOT NULL CHECK (count >= 0),
        PRIMARY KEY (sample_id, population),
        FOREIGN KEY (sample_id) REFERENCES samples(id)
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

    # Split the data into subject and sample tables
    subjects = (
        df[["subject", "condition", "age", "sex", "treatment", "response", "project"]]
        .drop_duplicates()
        .rename(columns={"subject": "id"})
    )
    samples = df[
        ["sample", "sample_type", "time_from_treatment_start", "subject"]
    ].rename(columns={"sample": "id", "subject": "subject_id"})

    # Unpivot the counts into one row per sample and population
    cell_counts = df.melt(
        id_vars="sample",
        value_vars=["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"],
        var_name="population",
        value_name="count",
    ).rename(columns={"sample": "sample_id"})

    # Connect to the database
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Insert parents first so foreign keys resolve
    subjects.to_sql("subjects", conn, if_exists="append", index=False)
    samples.to_sql("samples", conn, if_exists="append", index=False)
    cell_counts.to_sql("cell_counts", conn, if_exists="append", index=False)

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
