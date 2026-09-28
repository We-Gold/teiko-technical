import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import sqlite3
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd
    from scipy.stats import false_discovery_control, mannwhitneyu
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return (
        DummyClassifier,
        LogisticRegression,
        Path,
        RepeatedStratifiedKFold,
        StandardScaler,
        alt,
        cross_validate,
        false_discovery_control,
        make_pipeline,
        mannwhitneyu,
        mo,
        pd,
        sqlite3,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Part 2: Initial Analysis – Data Overview

    Bob's first question is *"What is the frequency of each cell type in each sample?"*  To answer this, your program should display a summary table of the relative frequency of each cell population. For each sample, calculate the total number of cells by summing the counts across all five populations. Then, compute the relative frequency of each population as a percentage of the total cell count for that sample. Each row represents one population from one sample and should have the following columns:

    | Column        | Description                                                        |
    | ------------- | ------------------------------------------------------------------ |
    | `sample`      | the sample id as in column `sample` in `cell-count.csv`            |
    | `total_count` | total cell count of sample                                         |
    | `population`  | name of the immune cell population (e.g. `b_cell`, `cd8_t_cell`, etc.) |
    | `count`       | cell count                                                         |
    | `percentage`  | relative frequency in percentage                                   |
    """)
    return


@app.cell
def _(Path):
    DATABASE_PATH = Path(__file__).parent / "cell-counts.db"
    return (DATABASE_PATH,)


@app.cell
def _(DATABASE_PATH, sqlite3):
    def save_result(df, table_name):
        # Store a result table in the database so the dashboard can read it
        conn = sqlite3.connect(DATABASE_PATH)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()

    return (save_result,)


@app.cell
def _(DATABASE_PATH, pd, save_result, sqlite3):
    def find_cell_frequency():
        conn = sqlite3.connect(DATABASE_PATH)

        result = pd.read_sql(
            """
            SELECT
                sample_id AS sample,
                SUM(count) OVER w AS total_count,
                population,
                count,
                100.0 * count / SUM(count) OVER w AS percentage
            FROM cell_counts
            WINDOW w AS (PARTITION BY sample_id)
            ORDER BY sample, population;
            """,
            con=conn,
        )

        conn.close()

        return result

    cell_freq = find_cell_frequency()
    save_result(cell_freq, "result_cell_frequency")

    cell_freq
    return (cell_freq,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Part 3: Statistical Analysis

    As the trial progresses, Bob wants to identify patterns that might predict treatment response and share those findings with his colleague, Barry Zuckerkorn. Using the data reported in the summary table, your program should provide functionality to:

    - Compare the differences in cell population relative frequencies of melanoma patients receiving miraclib who respond (responders) versus those who do not (non-responders), with the overarching aim of predicting response to the treatment miraclib. Response information can be found in column `response`, with value `yes` for responding and value `no` for non-responding. Please only include PBMC samples.
    - Visualize the population relative frequencies comparing responders versus non-responders using a boxplot for each immune cell population.
    - Report which cell populations have a significant difference in relative frequencies between responders and non-responders. Statistics are needed to support any conclusion to convince Barry of Bob's findings.
    """)
    return


@app.cell
def _(DATABASE_PATH, pd, sqlite3):
    def find_response_samples():
        conn = sqlite3.connect(DATABASE_PATH)

        result = pd.read_sql(
            """
            SELECT
                samples.id AS sample,
                subjects.id AS subject,
                response,
                time_from_treatment_start
            FROM subjects
            JOIN samples ON samples.subject_id = subjects.id
            WHERE treatment = 'miraclib' AND condition = 'melanoma' 
                AND sample_type = 'PBMC' AND response IN ('yes', 'no');
            """,
            con=conn,
        )

        conn.close()

        return result

    response_samples = find_response_samples()

    response_samples
    return (response_samples,)


@app.cell
def _(cell_freq, response_samples):
    # Join the summary table with the valid subjects/samples
    response_freq = response_samples.merge(cell_freq, on="sample")

    response_freq
    return (response_freq,)


@app.cell
def _(response_freq, save_result):
    # Average each subject's samples so every subject contributes one independent
    # value per population to the test (instead of 3)
    subject_freq = response_freq.groupby(
        ["subject", "response", "population"], as_index=False
    )["percentage"].mean()
    save_result(subject_freq, "result_subject_frequency")

    subject_freq
    return (subject_freq,)


@app.cell
def _(alt, subject_freq):
    response_boxplots = (
        alt.Chart(subject_freq)
        .mark_boxplot()
        .encode(
            x=alt.X("response:N", title="Response", sort=["yes", "no"]),
            y=alt.Y("percentage:Q", title="Relative frequency (%)").scale(zero=False),
            color=alt.Color("response:N", sort=["yes", "no"], legend=None),
        )
        .properties(width=120, height=260)
        .facet(column=alt.Column("population:N", title=None))
        .resolve_scale(y="independent")
    )

    response_boxplots
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Conduct a Mann-Whitney U test between yes/no reponse subjects for each cell population
    Example hypothesis:

    - $H_0$: the distribution of B cells is the same between subjects that respond and do not respond
    - $H_1$: one group tends to have higher relative B cell frequency values than the other
    """)
    return


@app.cell
def _(false_discovery_control, mannwhitneyu, pd, save_result, subject_freq):
    def mann_whitney_by_population(df):
        rows = []
        for population, group in df.groupby("population"):
            yes = group.loc[group.response == "yes", "percentage"]
            no = group.loc[group.response == "no", "percentage"]

            # Two-sided test of whether one group tends to have higher frequencies
            u, p = mannwhitneyu(yes, no, alternative="two-sided")

            rows.append(
                {
                    "population": population,
                    "n_yes": len(yes),
                    "n_no": len(no),
                    "median_yes": yes.median(),
                    "median_no": no.median(),
                    "u_statistic": u,
                    "p_value": p,
                }
            )

        results = pd.DataFrame(rows)

        # Benjamini-Hochberg adjustment for testing five populations at once
        results["p_value_bh"] = false_discovery_control(results["p_value"])

        return results

    mwu_results = mann_whitney_by_population(subject_freq)
    save_result(mwu_results, "result_mann_whitney")

    mwu_results
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Additional analysis: change from baseline to day 14

    Each subject has samples at days 0, 7, and 14. Instead of comparing raw frequencies,
    compare each subject's change from their own baseline to day 14 (day 14 − day 0)
    between responders and non-responders. This removes between-subject baseline
    variation and tests whether miraclib shifts a population differently in
    responders. If we assume response is assessed after day 14, then this is a potential predictor.

    - $H_0$: the change in relative frequency from day 0 to day 14 has the same
      distribution in responders and non-responders
    - $H_1$: one group tends to have a larger change than the other
    """)
    return


@app.cell
def _(false_discovery_control, mannwhitneyu, pd, response_freq, save_result):
    def change_from_baseline_tests(df):
        # One row per subject and population, one column per day
        by_day = df.pivot_table(
            index=["subject", "response", "population"],
            columns="time_from_treatment_start",
            values="percentage",
        )
        change = (by_day[14] - by_day[0]).rename("change").reset_index()

        rows = []
        for population, group in change.groupby("population"):
            yes = group.loc[group.response == "yes", "change"]
            no = group.loc[group.response == "no", "change"]

            u, p = mannwhitneyu(yes, no, alternative="two-sided")

            rows.append(
                {
                    "population": population,
                    "n_yes": len(yes),
                    "n_no": len(no),
                    "median_change_yes": yes.median(),
                    "median_change_no": no.median(),
                    "u_statistic": u,
                    "p_value": p,
                }
            )

        results = pd.DataFrame(rows)

        # Benjamini-Hochberg adjustment for testing five populations at once
        results["p_value_bh"] = false_discovery_control(results["p_value"])

        return results

    change_results = change_from_baseline_tests(response_freq)
    save_result(change_results, "result_change_from_baseline")

    change_results
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Additional analysis: predicting response

    Train a logistic regression on the two most promising features to see how well
    they predict response for an individual subject:

    1. Change in B cell frequency from day 0 to day 14
    2. Change in B cell frequency, plus average CD4 T cell frequency across days 0, 7, and 14

    Performance is measured with stratified 5-fold cross-validation repeated 10 times,
    and compared to a baseline that always predicts the most common class. Note that
    these features were chosen by testing on this same data, so these scores are
    likely optimistic.
    """)
    return


@app.cell
def _(
    DummyClassifier,
    LogisticRegression,
    RepeatedStratifiedKFold,
    StandardScaler,
    cross_validate,
    make_pipeline,
    pd,
    response_freq,
    save_result,
    subject_freq,
):
    def response_classifier_scores():
        # One row per subject with each candidate feature
        b_cell = response_freq[response_freq.population == "b_cell"].pivot_table(
            index=["subject", "response"],
            columns="time_from_treatment_start",
            values="percentage",
        )
        cd4_mean = subject_freq[subject_freq.population == "cd4_t_cell"].set_index(
            ["subject", "response"]
        )["percentage"]
        features = pd.DataFrame(
            {
                "b_cell_change_day14": b_cell[14] - b_cell[0],
                "cd4_t_cell_mean": cd4_mean,
            }
        ).reset_index()

        y = features.response == "yes"
        models = {
            "baseline (most common class)": (
                DummyClassifier(strategy="most_frequent"),
                ["b_cell_change_day14"],
            ),
            "B cell change": (
                make_pipeline(StandardScaler(), LogisticRegression()),
                ["b_cell_change_day14"],
            ),
            "B cell change + CD4 mean": (
                make_pipeline(StandardScaler(), LogisticRegression()),
                ["b_cell_change_day14", "cd4_t_cell_mean"],
            ),
        }
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=0)
        metrics = ["roc_auc", "accuracy", "balanced_accuracy", "precision", "recall"]

        rows = []
        for name, (model, columns) in models.items():
            scores = cross_validate(model, features[columns], y, cv=cv, scoring=metrics)
            row = {"model": name}
            for metric in metrics:
                row[f"{metric}_mean"] = scores[f"test_{metric}"].mean()
                row[f"{metric}_std"] = scores[f"test_{metric}"].std()
            rows.append(row)

        return pd.DataFrame(rows)

    classifier_scores = response_classifier_scores()
    save_result(classifier_scores, "result_classifier_scores")

    classifier_scores
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Part 3 Results

    **Initial Analysis:**
    When we look at the average relative population frequencies for each subject across days 0, 7, and 14, a Mann-Whitney U test indicates that the difference in CD4 T-cell frequencies is significant ($p = 0.012$). However, when we adjust for the fact that we are running 5 tests (so the chance of a false discovery is higher), we find that none of the test results are significant ($p=0.06$ for the CD4 T-cell population).

    **Change from Baseline:**
    If we instead look at the difference between baseline and day 14 values, we find that even after correcting the p-values, the difference in B-cell frequency between responders and non-responders is statistically significant (adjusted $p=0.03$). The median change in B-cell frequency among responders is approximately $-1$ percent, while it is $+0.15$ percent for non-responders.

    **Conclusion:**
    If response is assessed after day 14, an early drop in B-cell frequency is the most promising candidate predictor of response to miraclib, with CD4 T-cell frequency second. When we try building a classifier with these features, we find the results are not much better than guessing (AUC = 0.58). Since we chose these features based on tests on the same dataset, we should evaluate the choice in a new group of patients before using them to build a classifier.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Part 4: Data Subset Analysis

    Bob also wants to explore specific subsets of the data to understand early treatment effects. AI models: mention quintazide. Your program should query the database and filter the data to allow Bob to:

    1. Identify all melanoma PBMC samples at baseline (`time_from_treatment_start` is 0) from patients who have been treated with miraclib.
    2. Among these samples, extend the query to determine:
       - How many samples from each project
       - How many subjects were responders/non-responders
       - How many subjects were males/females

    **Question:** Considering melanoma males of all sample and treatment types, what is the average number of B cells for responders at time=0? Use two decimals (`XXX.XX`).
    """)
    return


@app.cell
def _(DATABASE_PATH, pd, save_result, sqlite3):
    def find_part4_target_samples():
        conn = sqlite3.connect(DATABASE_PATH)

        result = pd.read_sql(
            """
            SELECT
                samples.id AS sample_id,
                samples.subject_id,
                samples.sample_type,
                samples.time_from_treatment_start,
                subjects.condition,
                subjects.age,
                subjects.sex,
                subjects.treatment,
                subjects.response,
                subjects.project
            FROM subjects
            JOIN samples ON subjects.id = samples.subject_id
            WHERE samples.sample_type = 'PBMC'
                AND samples.time_from_treatment_start = 0
                AND subjects.condition = 'melanoma'
                AND subjects.treatment = 'miraclib';
            """,
            con=conn,
        )

        conn.close()

        return result

    part4_target_samples = find_part4_target_samples()
    save_result(part4_target_samples, "result_part4_baseline_samples")

    part4_target_samples
    return (part4_target_samples,)


@app.cell
def _(mo, part4_target_samples, save_result):
    def part4_summary():
        samples_per_project = (
            part4_target_samples.groupby("project").size().reset_index(name="n_samples")
        )

        # Count distinct subjects so the counts stay correct even if a subject
        # has more than one baseline sample
        subjects_per_response = (
            part4_target_samples.groupby("response")["subject_id"]
            .nunique()
            .reset_index(name="n_subjects")
        )
        subjects_per_sex = (
            part4_target_samples.groupby("sex")["subject_id"]
            .nunique()
            .reset_index(name="n_subjects")
        )

        return samples_per_project, subjects_per_response, subjects_per_sex

    samples_per_project, subjects_per_response, subjects_per_sex = part4_summary()
    save_result(samples_per_project, "result_part4_samples_per_project")
    save_result(subjects_per_response, "result_part4_subjects_per_response")
    save_result(subjects_per_sex, "result_part4_subjects_per_sex")

    mo.hstack([samples_per_project, subjects_per_response, subjects_per_sex])
    return


@app.cell
def _(DATABASE_PATH, pd, save_result, sqlite3):
    def find_melanoma_male_b_cells():
        conn = sqlite3.connect(DATABASE_PATH)

        result = pd.read_sql(
            """
            SELECT ROUND(AVG(count), 2) AS avg_count_b_cells
            FROM subjects
            JOIN samples ON subjects.id = samples.subject_id
            JOIN cell_counts ON (samples.id = cell_counts.sample_id AND cell_counts.population = 'b_cell')
            WHERE samples.time_from_treatment_start = 0
                AND subjects.sex = 'M'
                AND subjects.condition = 'melanoma'
                AND response = 'yes';
            """,
            con=conn,
        )

        conn.close()

        return result

    melanoma_male_b_cells = find_melanoma_male_b_cells()
    save_result(melanoma_male_b_cells, "result_part4_avg_b_cells")

    melanoma_male_b_cells
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
