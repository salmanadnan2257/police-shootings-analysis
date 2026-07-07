"""
Shared data-loading and cleaning logic for the fatalities dataset.

`analyse_deaths.py` (the original static-chart script) does its own inline
loading and cleaning and is left untouched. This module exists so `app.py`
(the interactive dashboard) does not duplicate that logic and always applies
the exact same cleaning steps the static script does to the same source
file, `Deaths_by_Police_US.csv`:

- read with `windows-1252` encoding (the file isn't UTF-8)
- fill missing values with 0
- coerce `age` to numeric with `errors='coerce'`
- parse `date` with `format='mixed', errors='coerce'` (the file mixes
  M/D/YYYY and DD/MM/YY rows) and derive a `year` column from it

The dashboard only uses `Deaths_by_Police_US.csv`. The four Census-derived
CSVs (income, high-school completion, poverty, race share by city) are used
only by the poverty/high-school-graduation/race comparison charts in
`analyse_deaths.py`, which stay static, three-library-comparison charts and
are out of scope for this dashboard (see README).
"""
import os

import pandas as pd

BASE_PATH = os.path.abspath(os.path.dirname(__file__))


def load_fatalities():
    """Load and clean Deaths_by_Police_US.csv, same steps as analyse_deaths.py."""
    df = pd.read_csv(os.path.join(BASE_PATH, 'Deaths_by_Police_US.csv'), encoding='windows-1252')
    df = df.fillna(0)
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
    df['year'] = df['date'].dt.year
    return df


def filter_options(df):
    """Dropdown option lists for the dashboard filters, derived from the real data."""
    states = sorted(s for s in df['state'].unique() if s and s != 0)
    years = sorted(int(y) for y in df['year'].dropna().unique())
    armed = (
        df['armed'].value_counts()
        .loc[lambda s: s.index != 0]
        .sort_values(ascending=False)
        .index.tolist()
    )
    return states, years, armed


def apply_filters(df, state=None, year=None, armed=None):
    """Apply the three optional filters, matching the dropdown semantics
    (empty string / None / 'all' means no filter on that dimension)."""
    out = df
    if state and state != 'all':
        out = out[out['state'] == state]
    if year and year != 'all':
        out = out[out['year'] == int(year)]
    if armed and armed != 'all':
        out = out[out['armed'] == armed]
    return out
