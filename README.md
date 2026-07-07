# Police Shootings Analysis

A data analysis of the Washington Post's dataset of fatal police shootings in the
United States, cross-referenced against four US Census datasets (poverty rate, high
school completion rate, median household income, and racial demographics by city) to
look for socioeconomic patterns. It ships two ways to look at the results: a static
analysis script that writes 24 chart files, and an interactive Flask dashboard that
lets you filter the fatality data by state, year, and armed status and watch a live
choropleth map and two other charts update in response.

## What it is

`analyse_deaths.py` loads five CSV files, cleans them, and produces 24 charts covering:

- Poverty rate and high school graduation rate by state (bar charts, three plotting
  libraries: matplotlib, seaborn, plotly)
- The relationship between poverty and high school graduation rate (line chart, joint
  KDE plot, linear regression plot)
- Racial makeup by state (stacked bar chart)
- Gender, age, and race breakdown of people killed
- Whether the person was armed
- Whether the person showed signs of mental illness
- The 10 cities with the most recorded killings, broken down by race
- A US state choropleth map of killings
- Killings per year

`app.py` is a small Flask dashboard built on top of the same fatality data (it does
not touch the four Census CSVs, see Architecture below for why). It renders a
clickable US-states choropleth, a killings-by-year bar chart, and a top-10-cities bar
chart, all filterable by state, year, and armed status, plus a stat row that
recomputes from whatever subset of rows is currently selected.

Neither is a live service in the sense of ingesting new data: both read the same fixed
CSV snapshot. `analyse_deaths.py` is a one-shot script that writes files and exits;
`app.py` is a locally-run server you interact with in a browser.

## Why it exists

It's a guided data-analysis exercise (originally a Udemy "100 Days of Code" project)
built to practice joining multiple real-world datasets, cleaning inconsistent data, and
producing the same chart in three different plotting libraries to compare their APIs.

## Features

- Loads and cleans 5 CSVs (about 2,500 rows of fatality data plus city-level Census
  data covering roughly 29,000 to 33,000 rows each)
- Converts string percentages and ages to numeric types with `errors='coerce'` so bad
  values become `NaN` instead of crashing the script
- Joins the poverty and high-school-completion datasets on `Geographic Area` + `City`
  for a combined regression plot
- Renders the same comparison chart in matplotlib, seaborn, and plotly.express, useful
  as a side-by-side reference for how each library's API differs
- Builds a US state choropleth map of total killings from raw state abbreviations
- Runs headless: writes every chart to `output/` as a file instead of requiring a
  display or a running Jupyter kernel
- Interactive dashboard (`app.py`) with:
  - Three dropdown filters (state, year, armed status) built from the actual values in
    the data, not a hardcoded list
  - A US-states choropleth of killings with real hover tooltips and pan/zoom; clicking
    a state on the map sets the state filter and refreshes the rest of the page, the
    same as picking it from the dropdown
  - A killings-per-year bar chart and a top-10-cities bar chart, both recomputed from
    whatever filter combination is active
  - A stat row (filtered record count, percent with signs of mental illness,
    most-affected state, most common armed status) that recomputes from the same
    filtered rows the charts show, so it can never drift from what's on screen
  - A `GET /api/charts` JSON endpoint that the page calls on every filter change; the
    three charts re-render with `Plotly.react` from the returned figure data, so hover,
    zoom, and click all keep working and no chart is a static image

## Architecture

Two entry points, sharing one cleaning path for the fatality data:

- **`data.py`** loads and cleans `Deaths_by_Police_US.csv` (windows-1252 encoding,
  fill NaN with 0, coerce `age` to numeric, parse `date` with `format='mixed'` and
  derive `year`) and exposes `apply_filters()` for the state/year/armed dropdowns. This
  is the only place that logic lives for the dashboard, so `app.py` can't drift from
  what the numbers actually are.
- **`analyse_deaths.py`** is the original static-chart script, run top to bottom, and is
  untouched by the dashboard work:
  1. Load the 5 CSVs with `windows-1252` encoding (the source files aren't UTF-8)
  2. Fill missing values with 0 and coerce numeric-looking string columns to actual
     numeric dtypes
  3. Build each chart in sequence, matplotlib/seaborn figures via `plt.savefig()` into
     `output/chart_NN.png`, and plotly figures via `fig.write_html()` into
     `output/chart_NN.html` (not committed here, see Setup below for why)
  4. No functions, no classes beyond one small helper (`convert_country_code`) and a
     `next_chart_path()` counter. It's a straight-line analysis script, not a package.
- **`app.py`** is the Flask dashboard. It loads and cleans the fatality data once at
  startup via `data.py`, and on every request to `/` or `/api/charts` filters that same
  in-memory dataframe and rebuilds three `plotly.graph_objects` figures (a choropleth,
  a year bar chart, a city bar chart) plus the stat row, converting each figure to
  plain JSON with `fig.to_json()`. `templates/index.html` renders the initial,
  unfiltered payload server-side on first load, then re-fetches `/api/charts` and calls
  `Plotly.react` on every dropdown change or map click, so filtering never triggers a
  full page reload.

The dashboard deliberately only covers `Deaths_by_Police_US.csv`, not the four
Census-derived CSVs: those feed the poverty-rate/high-school-completion/race-share
comparisons in `analyse_deaths.py`, whose point is comparing matplotlib, seaborn, and
plotly's APIs side by side on the same static chart, not interactive filtering. State,
year, and armed status are also the three fields that naturally support drill-down
filtering in the fatality data; the Census joins don't have an equivalent filterable
dimension.

The repo also ships a curated `output/` folder with 18 static PNGs from an actual run
of `analyse_deaths.py`, so you can look at those results without installing anything.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

No environment variables or external services are needed. There's no `.env.example`
because neither entry point reads any env vars; both only read the CSV files that ship
in this folder.

## Usage

Interactive dashboard (recommended):

```bash
python app.py
```

Open `http://127.0.0.1:5000/` in a browser. Pick a state, year, or armed status from
the dropdowns (or click a state directly on the map) to filter the choropleth, the
year chart, the city chart, and the stat row together. "Reset filters" clears back to
the full 2,535-record dataset.

Static analysis script (unchanged, still works exactly as before):

```bash
python analyse_deaths.py
```

This reads the 5 CSVs in the project root and writes 24 chart files into `output/`
(created automatically). Matplotlib and seaborn charts save as PNGs. Plotly charts
(the two poverty/graduation-rate comparisons, the box plot of age by manner of death,
and the two US choropleth maps) save as standalone HTML files. Those 6 HTML files
aren't committed to this repo because each one embeds a full copy of plotly.js and
inflates to roughly 5 MB apiece (30 MB total for 6 files); running the script
regenerates them locally in under a minute.

## Challenges

- **`plt.show()` / `fig.show()` don't work headlessly.** The original script (built for
  an interactive Jupyter session) called `plt.show()` after every matplotlib/seaborn
  chart and `fig.show()` after every plotly chart. In a plain script with no display,
  matplotlib's default backend has nothing to show to, and plotly's `fig.show()`
  actually raised `ValueError: Mime type rendering requires ipython`. Fixed by forcing
  `matplotlib.use('Agg')` and replacing every `.show()` call with `plt.savefig()` /
  `fig.write_html()` into a numbered `output/` folder, so the script produces durable
  files instead of a window that never appears.

- **`value_counts().reset_index()` column naming changed across pandas versions.** Code
  like `df['state'].value_counts().reset_index(name='count')` used to produce a column
  literally called `index`; on the pandas version available here (3.0.3) the resulting
  column keeps the original series name (`state`), so `state_kills['index']` raised a
  `KeyError`. Same problem in the racial-makeup-by-state section, where
  `merged_series.drop(columns='index')` failed outright because the column was never
  named `index` to begin with (it's `Geographic area`, inherited from the groupby key).
  Fixed both spots to reference the actual column names instead of a hardcoded
  `'index'`, and rewrote the racial-makeup merge to rename each grouped Series before
  concatenating rather than trying to rename a generic `0` column after the fact.

- **`pycountry.countries.get(alpha_2=code)` returns `None` for US state codes, and the
  script didn't check for that.** The choropleth section runs every state abbreviation
  (`WA`, `OR`, etc.) through a function meant to convert ISO-3166 alpha-2 *country*
  codes to alpha-3. US state postal codes aren't ISO country codes, so `pycountry`
  returns `None` for all of them, and `country.alpha_3` crashed with
  `AttributeError: 'NoneType' object has no attribute 'alpha_3'`. Added a `None` check
  that falls back to the original code unchanged. The first choropleth (which uses
  `locationmode='USA-states'`) doesn't actually need this conversion at all since
  plotly expects raw USPS codes there; the conversion only matters for the second map,
  which plots on a world scope and is mostly illustrative.

- **Mixed date formats broke `pd.to_datetime`.** Most rows in `date` are `M/D/YYYY`
  (e.g. `2/1/2015`), but some are `DD/MM/YY` (e.g. `13/01/15`), so a plain
  `pd.to_datetime(df['date'])` raised `ValueError: time data "13/01/15" doesn't match
  format`. Fixed with `format='mixed', errors='coerce'`, which infers the format
  per-value and turns anything unparseable into `NaT` instead of crashing.

- **`scipy` is a transitive dependency the script needs but never imports directly.**
  Both `df['age'].plot(kind='kde')` and `sns.jointplot(..., kind='kde')` fail at
  runtime with `ModuleNotFoundError: No module named 'scipy'` unless it's installed
  separately, because pandas/seaborn's KDE plotting delegates to
  `scipy.stats.gaussian_kde` lazily. Added `scipy` to `requirements.txt` explicitly so
  a fresh install doesn't hit this the first time a KDE chart runs.

- **A raw Plotly figure dict isn't safely `jsonify`-able.** `go.Figure` objects carry
  numpy `int64`/`float64` values inside their `data`/`layout` dicts (state counts from
  `value_counts()`, for example), and Flask's default JSON encoder doesn't know how to
  serialize those. Rather than hand `fig.to_dict()` straight to `jsonify()` and risk
  hitting that at request time, `app.py` routes every figure through Plotly's own
  `fig.to_json()` (which already handles numpy/pandas types) and `json.loads()` before
  it reaches `jsonify`, so the numpy-to-JSON conversion goes through Plotly's encoder
  instead of Flask's.

- **TikZ line breaks silently produced a tabular-style error, not a line break.** The
  Deep Dive PDF's `app.py` request-cycle diagram uses multi-line edge labels like
  `node[below]{4. rendered HTML +\\initial JSON payload}`. Without `align=center` set
  on that specific node, TikZ's `\\` doesn't act as a plain line break; it's
  interpreted the way `\\` behaves inside a tabular row, which produced three
  `! LaTeX Error: Something's wrong--perhaps a missing \item.` failures on every
  compile of `docs/explainers/deep-dive.pdf`, even though the picture still rendered
  something and the error was easy to miss in a long `pdflatex` log. Fixed by adding
  `align=center` to each multi-line edge-label node in that diagram.

## What I learned

- `reset_index()` after a `groupby()` or `value_counts()` names the new column after
  whatever the index already was, not always `'index'`. Code that hardcodes `'index'`
  as a column name is fragile across pandas versions and should instead capture or
  rename the index explicitly at the point of creation.
- Percent/age columns that look numeric in a CSV often aren't (leading/trailing
  whitespace, stray text, blanks), so `pd.to_numeric(col, errors='coerce')` is worth
  applying defensively even when a column looks clean in a preview.
- Real-world date columns are rarely one consistent format. `format='mixed'` in
  `pd.to_datetime` is the right tool when a dataset silently interleaves `M/D/Y` and
  `D/M/Y` rows, which is exactly what this dataset does.
- Library functions can return `None` instead of raising on a lookup miss (`pycountry`
  here), so "it worked in testing" doesn't mean every input path is actually guarded.
- Writing an analysis script to be headless-safe (backend + file output instead of
  interactive `.show()`) is what actually makes it reproducible and CI-friendly; the
  original notebook-style code only worked because it was always run inside a kernel
  that had somewhere to render to.

## What I'd do differently

- `analyse_deaths.py` itself is still one 380-line procedural script. Breaking each
  chart into a small function (`plot_poverty_by_state(df)`, etc.) would make it
  possible to test individual pieces and re-run just one chart without executing the
  whole file. `data.py`/`app.py` show what that split looks like for the fatality-only
  path, but the Census-joined charts in `analyse_deaths.py` weren't refactored.
- The dashboard filters (state, year, armed status) only apply to the fatality data.
  Extending them to also filter the poverty/high-school-completion charts would need a
  city-to-state join on the Census CSVs that `analyse_deaths.py` doesn't currently do
  cleanly (city names aren't unique across states in that data), so it was left out of
  scope rather than built on a shaky join.
- The `convert_country_code` helper is a leftover from a template meant for country-level
  choropleths; it's genuinely unnecessary for the first US-states map and only
  partially meaningful for the second. I'd drop the conversion for the state-level map
  and either fix or remove the world-scope map since USPS codes plotted on a
  world-country scale aren't a meaningful visualization.
- No schema or dtype validation on load. A malformed CSV (extra column, renamed
  header) would fail deep inside a chart-building block with a confusing traceback
  rather than a clear error at load time.
- The dataset is a fixed historical snapshot: 2,535 records spanning 2015 through part
  of 2017 (year counts from an actual run: 991 in 2015, 962 in 2016, and 582 in a
  partial 2017). It is not live or current data and the script has no way to pull an
  updated version of the Washington Post database; that's worth stating loudly rather
  than letting a chart title imply it's up to date.

## Data and framing notes

The fatality data (`Deaths_by_Police_US.csv`) is a fixed extract of The Washington
Post's ongoing database of fatal police shootings, covering 2015 through part of 2017
in this specific file (2,535 records). The four Census-derived CSVs (household income,
high school completion, poverty rate, and race share by city) are similarly static
snapshots, mostly dated around 2015. All charts here report descriptive counts and
correlations already present in the joined data; nothing here establishes causation,
and the small dataset for some cross-tabulations (for example, race by top-10-city)
means individual bars can represent a handful of records.

Verified facts from an actual run of the script (see Setup/Usage above), not
estimates: 2,535 total fatality records; 2,428 male and 107 female; 633 of 2,535 rows
(about 25 percent) recorded signs of mental illness; the five most common values of
`armed` are gun (1,398), knife (373), vehicle (177), unarmed (171), and undetermined
(117); the five states with the most recorded killings are California (424), Texas
(225), Florida (154), Arizona (118), and Ohio (79).
