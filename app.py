"""
Interactive dashboard for the fatal-police-shootings dataset.

Loads Deaths_by_Police_US.csv once at startup (via `data.py`, the same
cleaning steps `analyse_deaths.py` uses) and serves it behind a small Flask
app with three Plotly views that respond to three filters: state, year, and
armed status.

  1. A US-states choropleth of killings, click a state on the map (or use the
     dropdown) to filter everything else to it.
  2. A bar chart of killings per year.
  3. A bar chart of the top 10 cities by killings, filtered by the same
     state/year/armed selections.

A stat row (filtered count, percent with signs of mental illness, most
common armed status, most-affected state) recomputes from the same filtered
rows shown in the charts, so nothing on the page is a static number pasted
in separately from the data.

Every filter change calls `GET /api/charts` (JSON in the query string, JSON
figures back) and the page re-renders the three Plotly figures with
`Plotly.react`, so hover/zoom/click all stay live and no chart is a static
image.

Run with `python app.py` and open http://127.0.0.1:5000/.

`python analyse_deaths.py` is unaffected: it still reads the same 5 CSVs
independently and writes the original 24 static chart files to `output/`.
"""
import json

import plotly.graph_objects as go
from flask import Flask, jsonify, render_template, request

from data import apply_filters, filter_options, load_fatalities

app = Flask(__name__)

# Load and clean once at startup; reused (read-only) by every request.
DF = load_fatalities()
STATES, YEARS, ARMED_TYPES = filter_options(DF)


def fig_to_json(fig):
    """Convert a Plotly figure to a plain JSON-safe dict (handles numpy/
    pandas dtypes that `jsonify` alone would choke on)."""
    return json.loads(fig.to_json())


def build_choropleth(filtered_df, selected_state):
    state_counts = filtered_df['state'].value_counts().reset_index()
    state_counts.columns = ['state', 'count']

    fig = go.Figure(data=go.Choropleth(
        locations=state_counts['state'],
        z=state_counts['count'],
        locationmode='USA-states',
        colorscale='Viridis',
        colorbar_title='Deaths',
        hovertemplate='%{location}: %{z} deaths<extra></extra>',
        marker_line_color=(
            [('#f97316' if s == selected_state else 'white') for s in state_counts['state']]
        ),
        marker_line_width=(
            [3 if s == selected_state else 0.5 for s in state_counts['state']]
        ),
    ))
    fig.update_layout(
        title='Killings by State (click a state to filter)',
        geo=dict(scope='usa'),
        template='plotly_white',
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def build_year_chart(filtered_df):
    year_counts = filtered_df['year'].dropna().value_counts().sort_index()
    fig = go.Figure(data=go.Bar(
        x=[int(y) for y in year_counts.index],
        y=year_counts.values,
        marker_color='#3b82f6',
        hovertemplate='%{x}: %{y} deaths<extra></extra>',
    ))
    fig.update_layout(
        title='Killings by Year',
        xaxis_title='Year',
        yaxis_title='Number of deaths',
        xaxis=dict(type='category'),
        template='plotly_white',
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def build_city_chart(filtered_df):
    city_counts = filtered_df['city'].value_counts().head(10).sort_values()
    fig = go.Figure(data=go.Bar(
        x=city_counts.values,
        y=city_counts.index,
        orientation='h',
        marker_color='#8b5cf6',
        hovertemplate='%{y}: %{x} deaths<extra></extra>',
    ))
    fig.update_layout(
        title='Top 10 Cities by Killings (current filter)',
        xaxis_title='Number of deaths',
        template='plotly_white',
        margin=dict(l=120, r=20, t=50, b=50),
    )
    return fig


def build_stats(filtered_df):
    total = int(len(filtered_df))
    if total == 0:
        return {
            'total': 0, 'pct_mental_illness': None,
            'top_state': None, 'top_armed': None,
        }
    mental_illness = int((filtered_df['signs_of_mental_illness'] == True).sum())  # noqa: E712
    pct_mental_illness = round(100 * mental_illness / total, 1)
    top_state_series = filtered_df['state'].value_counts()
    top_state = f"{top_state_series.index[0]} ({int(top_state_series.iloc[0])})" if len(top_state_series) else None
    armed_series = filtered_df[filtered_df['armed'] != 0]['armed'].value_counts()
    top_armed = f"{armed_series.index[0]} ({int(armed_series.iloc[0])})" if len(armed_series) else None
    return {
        'total': total,
        'pct_mental_illness': pct_mental_illness,
        'top_state': top_state,
        'top_armed': top_armed,
    }


def build_payload(state, year, armed):
    filtered = apply_filters(DF, state=state, year=year, armed=armed)
    return {
        'choropleth': fig_to_json(build_choropleth(filtered, state)),
        'year_chart': fig_to_json(build_year_chart(filtered)),
        'city_chart': fig_to_json(build_city_chart(filtered)),
        'stats': build_stats(filtered),
    }


@app.route('/')
def index():
    payload = build_payload(state=None, year=None, armed=None)
    return render_template(
        'index.html',
        states=STATES,
        years=YEARS,
        armed_types=ARMED_TYPES,
        initial_payload_json=json.dumps(payload),
        total_records=len(DF),
    )


@app.route('/api/charts')
def api_charts():
    state = request.args.get('state') or 'all'
    year = request.args.get('year') or 'all'
    armed = request.args.get('armed') or 'all'
    return jsonify(build_payload(state=state, year=year, armed=armed))


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)
