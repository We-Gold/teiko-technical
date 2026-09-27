import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from pathlib import Path
    import sqlite3
    import pandas as pd
    import altair as alt
    from scipy.stats import mannwhitneyu

    return Path, alt, mannwhitneyu, mo, pd, sqlite3


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
    DATABASE_PATH = Path("cell-counts.db")
    return (DATABASE_PATH,)


@app.cell
def _(DATABASE_PATH, pd, sqlite3):
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
                response
            FROM subjects
            JOIN samples ON samples.subject_id = subjects.id
            WHERE treatment = 'miraclib' AND condition = 'melanoma'
                AND sample_type = 'PBMC' AND time_from_treatment_start = 0;
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
def _(alt, response_freq):
    response_boxplots = (
        alt.Chart(response_freq)
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
def _(mannwhitneyu, pd, response_freq):
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

        return pd.DataFrame(rows)

    mwu_results = mann_whitney_by_population(response_freq)

    mwu_results
    return


@app.cell(hide_code=True)
def _():
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
def _(DATABASE_PATH, pd, sqlite3):
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

    part4_target_samples
    return (part4_target_samples,)


@app.cell
def _(part4_target_samples):
    def part4_summary():
        samples_per_project = part4_target_samples.groupby(by='project').size()
        samples_per_response_group = part4_target_samples.groupby(by='response').size()
        samples_per_sex = part4_target_samples.groupby(by='sex').size()

        print(f"Distribution of samples across projects:")
        print(samples_per_project)
    
        print(f"\nDistribution of samples across response:")
        print(samples_per_response_group)
    
        print(f"\nDistribution of samples across sex:")
        print(samples_per_sex)

    part4_summary()
    return


@app.cell
def _(DATABASE_PATH, pd, sqlite3):
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

    find_melanoma_male_b_cells()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
