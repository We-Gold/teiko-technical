import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium", app_title="Loblaw Bio Analysis")


@app.cell(hide_code=True)
def _():
    import sqlite3
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    return Path, alt, mo, pd, sqlite3


@app.cell(hide_code=True)
def _(Path, mo, pd, sqlite3):
    DATABASE_PATH = Path(__file__).parent / "cell-counts.db"

    RESULT_TABLES = [
        "result_cell_frequency",
        "result_subject_frequency",
        "result_mann_whitney",
        "result_change_from_baseline",
        "result_classifier_scores",
        "result_part4_baseline_samples",
        "result_part4_samples_per_project",
        "result_part4_subjects_per_response",
        "result_part4_subjects_per_sex",
        "result_part4_avg_b_cells",
    ]

    def load_results():
        # Read every result table the pipeline wrote, or None if any are missing
        if not DATABASE_PATH.exists():
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        existing = set(
            pd.read_sql("SELECT name FROM sqlite_master WHERE type = 'table'", conn)[
                "name"
            ]
        )
        if not set(RESULT_TABLES) <= existing:
            conn.close()
            return None

        tables = {
            name.removeprefix("result_"): pd.read_sql(f"SELECT * FROM {name}", conn)
            for name in RESULT_TABLES
        }
        conn.close()

        return tables

    results = load_results()

    mo.stop(
        results is None,
        mo.callout(
            mo.md("No results found in `cell-counts.db`. Run `make pipeline` first."),
            kind="danger",
        ),
    )
    return (results,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Loblaw Bio Analysis

    Created by Weaver Goldman
    """)
    return


@app.cell(hide_code=True)
def _(mo, results):
    cell_frequency = results["cell_frequency"]

    part2 = mo.vstack(
        [
            mo.md(
                "Relative frequency of each immune cell population in each sample, "
                "as a percentage of the sample's total count across all five "
                "populations. Use the table's search and filters to look up a sample."
            ),
            mo.ui.table(cell_frequency.round({"percentage": 2}), page_size=15),
        ]
    )
    return (part2,)


@app.cell(hide_code=True)
def _(alt, mo, results):
    subject_frequency = results["subject_frequency"]
    mann_whitney = results["mann_whitney"]
    change_from_baseline = results["change_from_baseline"]
    classifier_scores = results["classifier_scores"]

    boxplots = (
        alt.Chart(subject_frequency)
        .mark_boxplot()
        .encode(
            x=alt.X("response:N", title="Response", sort=["yes", "no"]),
            y=alt.Y("percentage:Q", title="Relative frequency (%)").scale(zero=False),
            color=alt.Color("response:N", sort=["yes", "no"], legend=None),
        )
        .properties(width=110, height=260)
        .facet(column=alt.Column("population:N", title=None))
        .resolve_scale(y="independent")
    )

    # Pull conclusion numbers from the results tables
    cd4 = mann_whitney.set_index("population").loc["cd4_t_cell"]
    b_cell = change_from_baseline.set_index("population").loc["b_cell"]
    models = classifier_scores.set_index("model")
    best_auc = models.drop("baseline (most common class)")["roc_auc_mean"].max()

    conclusions = mo.md(rf"""
    **Initial Analysis:**
    When we look at the average relative population frequencies for each subject across days 0, 7, and 14, a Mann-Whitney U test indicates that the difference in CD4 T-cell frequencies is significant ($p = {cd4.p_value:.3f}$). However, when we adjust for the fact that we are running {len(mann_whitney)} tests (so the chance of a false discovery is higher), we find that none of the test results are significant ($p={cd4.p_value_bh:.2f}$ for the CD4 T-cell population).

    **Change from Baseline:**
    If we instead look at the difference between baseline and day 14 values, we find that even after correcting the p-values, the difference in B-cell frequency between responders and non-responders is statistically significant (adjusted $p={b_cell.p_value_bh:.2f}$). The median change in B-cell frequency among responders is approximately ${b_cell.median_change_yes:.0f}$ percent, while it is ${b_cell.median_change_no:+.2f}$ percent for non-responders.

    **Conclusion:**
    If response is assessed after day 14, an early drop in B-cell frequency is the most promising candidate predictor of response to miraclib, with CD4 T-cell frequency second. When we try building a classifier with these features, we find the results are not much better than guessing (AUC = {best_auc:.2f}). Since we chose these features based on tests on the same dataset, we should evaluate the choice in a new group of patients before using them to build a classifier.
    """)

    part3 = mo.vstack(
        [
            mo.md(
                "Melanoma patients treated with miraclib. "
                "Each point is one subject's average frequency across days 0, 7, "
                "and 14."
            ),
            boxplots,
            mo.md("### Part 3 Results"),
            conclusions,
            mo.md(
                "### Mann-Whitney U test: average frequencies\n"
                "P-values adjusted with Benjamini-Hochberg (p_value_bh column)."
            ),
            mo.ui.table(mann_whitney.round(4), selection=None),
            mo.md(
                "### Mann-Whitney U test: change from day 0 to day 14\n"
                "Each subject's day 14 frequency minus their day 0 frequency."
            ),
            mo.ui.table(change_from_baseline.round(4), selection=None),
            mo.md(
                "### Classifier performance\n"
                "A logistic regression model evaluated with stratified 5-fold cross-validation with 10 repetitions."
            ),
            mo.ui.table(classifier_scores.round(3), selection=None),
        ]
    )
    return (part3,)


@app.cell(hide_code=True)
def _(mo, results):
    baseline_samples = results["part4_baseline_samples"]
    samples_per_project = results["part4_samples_per_project"]
    subjects_per_response = results["part4_subjects_per_response"]
    subjects_per_sex = results["part4_subjects_per_sex"]
    avg_b_cells = results["part4_avg_b_cells"]["avg_count_b_cells"].iloc[0]

    def count_stats(df, key, count_column, caption):
        return mo.hstack(
            [
                mo.stat(int(row[count_column]), label=str(row[key]), caption=caption)
                for _, row in df.iterrows()
            ],
            justify="start",
        )

    def count_group(title, df, key, count_column, caption):
        return mo.vstack(
            [mo.md(f"### {title}"), count_stats(df, key, count_column, caption)]
        )

    part4 = mo.vstack(
        [
            mo.md(
                f"**{len(baseline_samples)} melanoma PBMC samples** at baseline "
                "(day 0) from patients treated with miraclib."
            ),
            mo.hstack(
                [
                    count_group(
                        "Samples per project",
                        samples_per_project,
                        "project",
                        "n_samples",
                        "samples",
                    ),
                    count_group(
                        "Subjects by response",
                        subjects_per_response,
                        "response",
                        "n_subjects",
                        "subjects",
                    ),
                    count_group(
                        "Subjects by sex",
                        subjects_per_sex,
                        "sex",
                        "n_subjects",
                        "subjects",
                    ),
                ],
                justify="space-between",
                wrap=True,
            ),
            mo.accordion(
                {"Baseline samples": mo.ui.table(baseline_samples, selection=None)}
            ),
            mo.md("### Average B cells in male melanoma responders at day 0"),
            mo.stat(
                f"{avg_b_cells:.2f}",
                label="Average B cell count",
                caption="all sample types and treatments",
            ),
        ]
    )
    return (part4,)


@app.cell(hide_code=True)
def _(mo, part2, part3, part4):
    mo.ui.tabs(
        {
            "Part 2: Cell frequencies": part2,
            "Part 3: Responders vs. non-responders": part3,
            "Part 4: Baseline subset": part4,
        }
    )
    return


if __name__ == "__main__":
    app.run()
