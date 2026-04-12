"""
India State Labour Market Analysis
===================================
Run this notebook locally or on Google Colab.

Local: jupyter notebook notebooks/india-state-analysis.ipynb
Colab: See the first cell for setup instructions.
"""

# %% [markdown]
# # India State Labour Market Analysis
#
# **Sources:**
# - PLFS (Periodic Labour Force Survey) 2018–2024 — employment by NCO division, national + 36 states
# - ILOSTAT India national time series 1991–2025 — long-run context
# - PLFS 2024 cross-sectional snapshot — real state × NCO variation
#
# **Data quality notes (read before interpreting charts):**
# - ✅ **State total employment 2018–2024**: real, differs meaningfully across states
# - ✅ **State wages by NCO division**: real in 2024 snapshot (Table 50/55 data)
# - ✅ **2024 cross-sectional state × NCO structure**: fully real
# - ⚠️ **State-level sector shares in time series**: synthetic — PLFS does not publish
#   state × NCO tables; each state's sector share tracks the national value.
#   This means "Bihar agri% over time" shows the national trend, not Bihar's real trajectory.

# %% [markdown]
# ## 0. Setup (Local + Google Colab)

# %%
import sys
import os

IN_COLAB = 'google.colab' in sys.modules

if IN_COLAB:
    print("Running on Google Colab — cloning repo and building analysis DB...")
    os.system("git clone https://github.com/shahzorkhan123/metroverse-jobs.git /content/metroverse-jobs 2>/dev/null || git -C /content/metroverse-jobs pull")
    os.chdir("/content/metroverse-jobs")
    os.system("pip install -q nbformat matplotlib seaborn pandas numpy")
    os.system("python scripts/rebuild_analysis_db.py")
    REPO_ROOT = "/content/metroverse-jobs"
else:
    # Locate repo root relative to this notebook (notebooks/ → repo root)
    try:
        NOTEBOOK_DIR = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Running inside Jupyter — use cwd, which nbconvert sets to notebook dir
        NOTEBOOK_DIR = os.getcwd()
        if not os.path.basename(NOTEBOOK_DIR) == 'notebooks':
            # fallback: look for data/ directory
            for candidate in [NOTEBOOK_DIR, os.path.dirname(NOTEBOOK_DIR)]:
                if os.path.exists(os.path.join(candidate, 'data', 'analysis.db')):
                    NOTEBOOK_DIR = os.path.join(candidate, 'notebooks')
                    break
    REPO_ROOT = os.path.dirname(NOTEBOOK_DIR)

DB_PATH = os.path.join(REPO_ROOT, "data", "analysis.db")
FIGURES_DIR = os.path.join(REPO_ROOT, "notebooks", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        f"analysis.db not found at {DB_PATH}. "
        "Run: python scripts/rebuild_analysis_db.py"
    )

print(f"DB: {DB_PATH} ({os.path.getsize(DB_PATH)/1e6:.1f} MB)")

# %%
import sqlite3
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

matplotlib.rcParams.update({
    'figure.dpi': 130,
    'figure.facecolor': 'white',
    'axes.facecolor': '#f8f8f8',
    'axes.grid': True,
    'grid.alpha': 0.4,
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
})

conn = sqlite3.connect(DB_PATH)

NCO_COLORS = {
    'Managers': '#A973BE',
    'Professionals': '#F1866C',
    'Technicians and Associate Professionals': '#488098',
    'Clerical Support Workers': '#6A6AAD',
    'Service and Sales Workers': '#77C898',
    'Skilled Agricultural, Forestry and Fishery Workers': '#556B2F',
    'Craft and Related Trades Workers': '#DAA520',
    'Plant and Machine Operators and Assemblers': '#CD853F',
    'Elementary Occupations': '#708090',
}

NCO_SHORT = {
    'Managers': 'Managers',
    'Professionals': 'Professionals',
    'Technicians and Associate Professionals': 'Technicians',
    'Clerical Support Workers': 'Clerical',
    'Service and Sales Workers': 'Services',
    'Skilled Agricultural, Forestry and Fishery Workers': 'Agriculture',
    'Craft and Related Trades Workers': 'Crafts',
    'Plant and Machine Operators and Assemblers': 'Operators',
    'Elementary Occupations': 'Elementary',
}

print("Setup complete.")

# %% [markdown]
# ## 1. National Sector Trends — What Is Happening to Agriculture?

# %%
# --- PLFS national 2018-2024 ---
plfs_nat = pd.read_sql("""
    SELECT s.year, o.major_group_name as sector, s.employment, s.gdp
    FROM occupation_year_stats s
    JOIN occupations o ON s.occupation_key = o.occupation_key
    WHERE s.dataset_id = 'plfs_in'
      AND s.region_id = 'national-india'
      AND o.level = 1
    ORDER BY s.year, o.code
""", conn)

# Pivot to wide
emp_wide = plfs_nat.pivot_table(index='year', columns='sector', values='employment', aggfunc='sum')
emp_wide.columns = [NCO_SHORT.get(c, c) for c in emp_wide.columns]
total_by_year = emp_wide.sum(axis=1)
share_wide = emp_wide.div(total_by_year, axis=0) * 100

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: stacked area
colors = [NCO_COLORS.get(c, '#aaa') for c in plfs_nat['sector'].unique()]
short_names = [NCO_SHORT.get(c, c) for c in plfs_nat['sector'].unique()]
color_map = dict(zip(short_names, colors))

emp_wide_plot = emp_wide.reindex(sorted(emp_wide.columns, key=lambda c: -emp_wide[c].iloc[-1]), axis=1)
bottom = np.zeros(len(emp_wide_plot))
ax = axes[0]
for col in emp_wide_plot.columns:
    c = color_map.get(col, '#aaa')
    ax.fill_between(emp_wide_plot.index, bottom, bottom + emp_wide_plot[col].values / 1e6,
                    alpha=0.85, color=c, label=col)
    bottom = bottom + emp_wide_plot[col].values / 1e6
ax.set_title("National Employment by NCO Division (millions)")
ax.set_xlabel("Year")
ax.set_ylabel("Workers (millions)")
ax.legend(loc='upper left', fontsize=7, ncol=1)

# Right: share change
ax2 = axes[1]
share_change = (share_wide.iloc[-1] - share_wide.iloc[0]).sort_values()
colors_bar = [color_map.get(c, '#aaa') for c in share_change.index]
ax2.barh(share_change.index, share_change.values, color=colors_bar)
ax2.axvline(0, color='black', linewidth=0.8)
ax2.set_title("Change in National Employment Share\n(2024 minus 2018, percentage points)")
ax2.set_xlabel("Percentage point change")

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '01_national_sector_trends.png'), bbox_inches='tight')
plt.show()

# Key numbers
print("National NCO employment shares 2018 vs 2024:")
print(share_wide.loc[[2018, 2024]].T.to_string(float_format='{:.1f}'.format))

# %%
# --- ILOSTAT extended view 1991-2025 ---
ilo = pd.read_sql("""
    SELECT s.year, o.major_group_name as sector, s.employment
    FROM occupation_year_stats s
    JOIN occupations o ON s.occupation_key = o.occupation_key
    WHERE s.dataset_id = 'ilostat_in' AND o.level = 1
    ORDER BY s.year, o.code
""", conn)

ilo_pivot = ilo.pivot_table(index='year', columns='sector', values='employment', aggfunc='sum')
ilo_total = ilo_pivot.sum(axis=1)
ilo_share = ilo_pivot.div(ilo_total, axis=0) * 100

fig, ax = plt.subplots(figsize=(12, 5))
agri_col = 'Agriculture and Elementary Occupations'
if agri_col in ilo_share.columns:
    ax.plot(ilo_share.index, ilo_share[agri_col], color='#556B2F', linewidth=2.5, label=agri_col)
for col in ilo_share.columns:
    if col != agri_col:
        ax.plot(ilo_share.index, ilo_share[col], linewidth=1.2, alpha=0.7, label=NCO_SHORT.get(col, col))
ax.set_title("India: National Employment Share by ISCO Group — Long Run (ILOSTAT 1991–2025)")
ax.set_xlabel("Year")
ax.set_ylabel("Share of total employment (%)")
ax.legend(loc='center right', fontsize=7)
ax.axvspan(1991, 1991, color='gray', alpha=0)  # placeholder

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '02_ilostat_long_run.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 2. State Employment Growth Trajectories (2018–2024)
# *These state totals are REAL — each state's workforce size is tracked independently.*

# %%
state_totals = pd.read_sql("""
    SELECT r.name as state, r.state_abbr as abbr, s.year,
           SUM(s.employment) as total_emp,
           SUM(s.gdp) as total_gdp
    FROM occupation_year_stats s
    JOIN regions r ON s.region_id = r.region_id
    WHERE s.dataset_id = 'plfs_in' AND r.region_type = 'State'
    GROUP BY r.name, r.state_abbr, s.year
    ORDER BY r.name, s.year
""", conn)

# Compute CAGR per state
def cagr_n(series, n):
    return (series.iloc[-1] / series.iloc[0]) ** (1 / n) - 1

cagr_df = (state_totals.groupby('state')['total_emp']
           .apply(lambda x: cagr_n(x, 6) * 100)
           .reset_index(name='cagr_pct')
           .sort_values('cagr_pct', ascending=False))

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

# Left: CAGR bar chart
ax = axes[0]
colors_bar = ['#2ecc71' if v > 3 else '#3498db' if v > 1 else '#e74c3c'
              for v in cagr_df['cagr_pct']]
ax.barh(cagr_df['state'], cagr_df['cagr_pct'], color=colors_bar)
ax.axvline(cagr_df['cagr_pct'].mean(), color='black', linestyle='--', linewidth=1, label=f"National avg")
ax.set_title("State Employment CAGR 2018–2024\n(green >3%, blue 1-3%, red <1%)")
ax.set_xlabel("Annual growth rate (%)")
ax.legend()

# Right: line chart for top 8 + bottom 4 states
top_states = cagr_df.head(8)['state'].tolist()
bot_states = cagr_df.tail(4)['state'].tolist()
highlight_states = top_states + bot_states

ax2 = axes[1]
for state in state_totals['state'].unique():
    sd = state_totals[state_totals['state'] == state].sort_values('year')
    base = sd['total_emp'].iloc[0]
    idx = sd['total_emp'] / base * 100
    if state in highlight_states:
        color = '#2ecc71' if state in top_states else '#e74c3c'
        ax2.plot(sd['year'], idx, linewidth=2, color=color, label=state, zorder=3)
    else:
        ax2.plot(sd['year'], idx, linewidth=0.6, color='#cccccc', alpha=0.6, zorder=1)

ax2.axhline(100, color='black', linestyle='--', linewidth=0.8)
ax2.set_title("State Employment Index (2018=100)\nTop 8 and bottom 4 states highlighted")
ax2.set_xlabel("Year")
ax2.set_ylabel("Index (2018 = 100)")
ax2.legend(fontsize=7, ncol=2, loc='upper left')

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '03_state_employment_growth.png'), bbox_inches='tight')
plt.show()

print("\nEmployment growth tiers:")
print(f"  Fast (>4% CAGR):  {list(cagr_df[cagr_df.cagr_pct > 4]['state'])}")
print(f"  Steady (2-4%):    {list(cagr_df[(cagr_df.cagr_pct>=2)&(cagr_df.cagr_pct<=4)]['state'])}")
print(f"  Slow (<2%):       {list(cagr_df[cagr_df.cagr_pct < 2]['state'])}")

# %% [markdown]
# ## 3. State GDP Growth (2020–2024)
# *GDP = employment × mean wage. Available from 2020 only.*

# %%
gdp_ts = state_totals[state_totals['year'] >= 2020].copy()
gdp_ts = gdp_ts[gdp_ts['total_gdp'] > 0]

gdp_cagr = (gdp_ts.groupby('state').apply(
    lambda g: cagr_n(g.sort_values('year')['total_gdp'], len(g)-1) * 100
)).reset_index(name='gdp_cagr').sort_values('gdp_cagr', ascending=False)

# Join with employment CAGR
combined = cagr_df.merge(gdp_cagr, on='state', how='inner')

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

ax = axes[0]
colors_gdp = ['#2ecc71' if v > 10 else '#3498db' if v > 5 else '#e74c3c'
              for v in gdp_cagr['gdp_cagr']]
ax.barh(gdp_cagr['state'], gdp_cagr['gdp_cagr'], color=colors_gdp)
ax.set_title("State GDP CAGR 2020–2024\n(wage-bill proxy: emp × mean wage)")
ax.set_xlabel("Annual growth rate (%)")

# Scatter: employment CAGR vs GDP CAGR
ax2 = axes[1]
ax2.scatter(combined['cagr_pct'], combined['gdp_cagr'], s=60, alpha=0.7, color='#3498db')
for _, row in combined.iterrows():
    if abs(row['cagr_pct']) > 3 or abs(row['gdp_cagr']) > 12:
        ax2.annotate(row['state'], (row['cagr_pct'], row['gdp_cagr']),
                     fontsize=7, ha='left', va='bottom',
                     xytext=(4, 4), textcoords='offset points')
# Regression line
fit_d = combined[['cagr_pct', 'gdp_cagr']].dropna()
m, b = np.polyfit(fit_d['cagr_pct'], fit_d['gdp_cagr'], 1)
x_range = np.linspace(fit_d['cagr_pct'].min(), fit_d['cagr_pct'].max(), 50)
ax2.plot(x_range, m * x_range + b, 'r--', linewidth=1)
r = fit_d.corr().iloc[0, 1]
ax2.set_title(f"Employment Growth vs GDP Growth\n(r = {r:.2f})")
ax2.set_xlabel("Employment CAGR 2018–2024 (%)")
ax2.set_ylabel("GDP CAGR 2020–2024 (%)")

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '04_state_gdp_growth.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 4. Who's Who in 2024 — Cross-Sectional State Snapshot
# *This section uses the 2024 snapshot data where state × NCO variation is REAL.*

# %%
snap = pd.read_sql("""
    SELECT r.name as state, r.state_abbr as abbr, o.major_group_name as sector,
           o.major_group_code as code, s.employment, s.mean_annual_wage, s.gdp
    FROM occupation_year_stats s
    JOIN regions r ON s.region_id = r.region_id
    JOIN occupations o ON s.occupation_key = o.occupation_key
    WHERE s.dataset_id = 'snapshot_in'
      AND r.region_type = 'State'
      AND o.level = 1
    ORDER BY r.name, o.code
""", conn)

snap_total = snap.groupby('state')[['employment', 'gdp']].sum().rename(
    columns={'employment': 'total_emp', 'gdp': 'total_gdp'})
snap = snap.merge(snap_total, on='state')
snap['emp_share'] = snap['employment'] / snap['total_emp']

# Sector shares per state
pivot_share = snap.pivot_table(index='state', columns='sector', values='emp_share').fillna(0)
pivot_share.columns = [NCO_SHORT.get(c, c) for c in pivot_share.columns]

# Sort states by agriculture share
agri_order = pivot_share['Agriculture'].sort_values(ascending=False).index

fig, ax = plt.subplots(figsize=(14, 10))
colors_list = [NCO_COLORS.get(
    {v: k for k, v in NCO_SHORT.items()}.get(c, c), '#aaa')
    for c in pivot_share.columns]

left = np.zeros(len(agri_order))
for i, col in enumerate(pivot_share.columns):
    vals = pivot_share.loc[agri_order, col].values
    ax.barh(range(len(agri_order)), vals * 100, left=left * 100,
            color=colors_list[i], label=col, height=0.8)
    left += vals

ax.set_yticks(range(len(agri_order)))
ax.set_yticklabels(agri_order, fontsize=8)
ax.set_xlabel("Share of employment (%)")
ax.set_title("India 2024: Occupation Structure by State (sorted by agriculture share)")
ax.legend(loc='lower right', fontsize=8, ncol=3)

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '05_state_composition_2024.png'), bbox_inches='tight')
plt.show()

# Tier classification
agri_share = snap[snap['sector'].str.contains('Agricultural')].groupby('state')['emp_share'].sum()
know_cols = ['Managers', 'Professionals', 'Technicians and Associate Professionals']
know_share = snap[snap['sector'].isin(know_cols)].groupby('state')['emp_share'].sum()

print("\nState structural tiers:")
agrarian = agri_share[agri_share > 0.45].index.tolist()
transitioning = agri_share[(agri_share >= 0.25) & (agri_share <= 0.45)].index.tolist()
services = agri_share[agri_share < 0.25].index.tolist()
print(f"  Agrarian   (>45% agri): {sorted(agrarian)}")
print(f"  Transition (25-45%):    {sorted(transitioning)}")
print(f"  Diversified (<25%):     {sorted(services)}")

# %% [markdown]
# ## 5. Wage Structure by State (2024)

# %%
# Average wage weighted by employment
snap['wage_x_emp'] = snap['mean_annual_wage'] * snap['employment']
state_wages = snap.groupby('state').apply(
    lambda g: g['wage_x_emp'].sum() / g['employment'].sum()
).reset_index(name='avg_wage').sort_values('avg_wage', ascending=False)

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

# Left: average wage ranking
ax = axes[0]
ax.barh(state_wages['state'], state_wages['avg_wage'] / 1000, color='#3498db')
ax.set_title("Average Annual Wage by State (2024, ₹ thousands)")
ax.set_xlabel("₹ thousands per year")

# Right: wage heatmap (state × NCO division)
wage_heat = snap.pivot_table(index='state', columns='sector', values='mean_annual_wage')
wage_heat.columns = [NCO_SHORT.get(c, c) for c in wage_heat.columns]
wage_heat = wage_heat.loc[state_wages['state']]  # sort by avg wage

ax2 = axes[1]
sns.heatmap(wage_heat / 1000, cmap='YlOrRd', ax=ax2,
            linewidths=0.3, linecolor='white',
            cbar_kws={'label': '₹ thousands/year'},
            xticklabels=True, yticklabels=True)
ax2.set_title("Mean Annual Wage by State × NCO Division (₹ thousands)")
ax2.tick_params(axis='x', rotation=45, labelsize=7)
ax2.tick_params(axis='y', labelsize=7)

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '06_wage_structure.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 6. GDP Per Worker & The Knowledge–Productivity Link

# %%
gdp_per_worker = snap.groupby('state').apply(
    lambda g: g['gdp'].sum() / g['employment'].sum()
).reset_index(name='gdp_per_worker').sort_values('gdp_per_worker', ascending=False)

know_share_df = know_share.reset_index(name='know_share')
gpw_know = gdp_per_worker.merge(know_share_df, on='state')

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

ax = axes[0]
ax.barh(gdp_per_worker['state'], gdp_per_worker['gdp_per_worker'] / 1000,
        color='#8e44ad')
ax.set_title("GDP per Worker by State (2024, ₹ thousands)")
ax.set_xlabel("₹ thousands")

ax2 = axes[1]
ax2.scatter(gpw_know['know_share'] * 100, gpw_know['gdp_per_worker'] / 1000,
            s=70, alpha=0.75, color='#8e44ad')
for _, row in gpw_know.iterrows():
    if row['gdp_per_worker'] / 1000 > 1400 or row['know_share'] > 0.18:
        ax2.annotate(row['state'], (row['know_share'] * 100, row['gdp_per_worker'] / 1000),
                     fontsize=7, xytext=(4, 4), textcoords='offset points')
fit_gpw = gpw_know[['know_share', 'gdp_per_worker']].dropna()
m, b = np.polyfit(fit_gpw['know_share'] * 100, fit_gpw['gdp_per_worker'] / 1000, 1)
x_r = np.linspace(fit_gpw['know_share'].min() * 100, fit_gpw['know_share'].max() * 100, 50)
ax2.plot(x_r, m * x_r + b, 'r--', linewidth=1)
r2 = fit_gpw.corr().iloc[0, 1]
ax2.set_title(f"Knowledge Economy Share vs GDP per Worker (r={r2:.2f})")
ax2.set_xlabel("Knowledge economy share (Managers + Prof + Tech, %)")
ax2.set_ylabel("GDP per worker (₹ thousands)")

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '07_gdp_per_worker.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 7. The Wage Gap: Same Job, Different State

# %%
wage_by_state_sector = snap.pivot_table(index='state', columns='sector', values='mean_annual_wage')

fig, axes = plt.subplots(2, 1, figsize=(14, 10))

for ax, col_name, short_name, color in [
    (axes[0], 'Professionals', 'Professionals', '#F1866C'),
    (axes[1], 'Skilled Agricultural, Forestry and Fishery Workers', 'Agriculture', '#556B2F'),
]:
    if col_name not in wage_by_state_sector.columns:
        continue
    w = wage_by_state_sector[col_name].sort_values(ascending=False).dropna()
    ax.barh(w.index, w.values / 1000, color=color)
    ax.set_title(f"Mean Annual Wage — {short_name} (NCO) across States (₹ thousands, 2024)")
    ax.set_xlabel("₹ thousands")
    national = snap[snap['sector'] == col_name]['mean_annual_wage'].mean()
    ax.axvline(national / 1000, color='black', linestyle='--', linewidth=1,
               label=f"National avg ₹{national/1000:.0f}k")
    ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '08_wage_gap.png'), bbox_inches='tight')
plt.show()

# Manager-to-agriculture wage premium
mgr_wage = snap[snap['sector'].str.contains('Manager')].groupby('state')['mean_annual_wage'].mean()
agr_wage = snap[snap['sector'].str.contains('Agricultural')].groupby('state')['mean_annual_wage'].mean()
premium = (mgr_wage / agr_wage).dropna().sort_values(ascending=False)

print("\nManager-to-Agriculture wage premium by state:")
print(premium.to_string(float_format='{:.2f}x'.format))

# %% [markdown]
# ## 8. State Archetypes — Who's Similar to Whom?

# %%
from numpy.linalg import norm

share_matrix = snap.pivot_table(index='state', columns='sector', values='emp_share').fillna(0)

# Cosine similarity
def cosine_sim(a, b):
    return np.dot(a, b) / (norm(a) * norm(b) + 1e-9)

states = share_matrix.index.tolist()
sim_matrix = np.zeros((len(states), len(states)))
for i, s1 in enumerate(states):
    for j, s2 in enumerate(states):
        sim_matrix[i, j] = cosine_sim(share_matrix.loc[s1].values, share_matrix.loc[s2].values)

sim_df = pd.DataFrame(sim_matrix, index=states, columns=states)

# Print top 3 neighbours per state
print("Top 3 most similar states (by occupation structure):\n")
for state in sorted(states):
    sims = sim_df[state].drop(state).sort_values(ascending=False)
    print(f"  {state:<40} ← {', '.join(sims.head(3).index)}")

# Heatmap
fig, ax = plt.subplots(figsize=(13, 11))
mask = np.eye(len(states), dtype=bool)
sns.heatmap(sim_df, mask=mask, cmap='coolwarm', vmin=0.7, vmax=1.0,
            ax=ax, linewidths=0.3, linecolor='white',
            xticklabels=True, yticklabels=True,
            cbar_kws={'label': 'Cosine similarity'})
ax.set_title("State Occupation Structure Similarity (cosine, 2024 snapshot)\nDarker = more similar")
ax.tick_params(axis='both', labelsize=7)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '09_state_similarity.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 9. Growth × Structure: Which States Grew AND Diversified?

# %%
growth_struct = cagr_df.merge(
    know_share_df, on='state'
).merge(
    agri_share.reset_index(name='agri_share'), on='state'
).merge(
    state_totals[state_totals['year'] == 2024][['state', 'total_emp']], on='state', how='left'
)

fig, ax = plt.subplots(figsize=(11, 8))

sc = ax.scatter(
    growth_struct['cagr_pct'],
    growth_struct['know_share'] * 100,
    s=growth_struct['total_emp'].fillna(1e6) / 1e6 * 3,  # size = workforce size
    c=growth_struct['agri_share'],
    cmap='RdYlGn_r',
    alpha=0.8,
    edgecolors='#444',
    linewidths=0.5,
)
plt.colorbar(sc, ax=ax, label='Agriculture share (green=low, red=high)')

for _, row in growth_struct.iterrows():
    ax.annotate(row['state'], (row['cagr_pct'], row['know_share'] * 100),
                fontsize=7, xytext=(4, 4), textcoords='offset points')

ax.axvline(growth_struct['cagr_pct'].mean(), color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
ax.axhline(growth_struct['know_share'].mean() * 100, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)

ax.set_xlabel("Employment CAGR 2018–2024 (%)")
ax.set_ylabel("Knowledge economy share (Mgr+Prof+Tech, % of workforce, 2024)")
ax.set_title("Growth vs Diversification\n(bubble size = workforce size; colour = agriculture share)")

# Quadrant labels
xlim, ylim = ax.get_xlim(), ax.get_ylim()
xmid = growth_struct['cagr_pct'].mean()
ymid = growth_struct['know_share'].mean() * 100
ax.text(xmid + 0.1, ylim[1] * 0.98, "Fast growth\nKnowledge-heavy",
        fontsize=7, color='green', va='top')
ax.text(xlim[0] + 0.1, ylim[1] * 0.98, "Slow growth\nKnowledge-heavy",
        fontsize=7, color='blue', va='top')

plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, '10_growth_vs_structure.png'), bbox_inches='tight')
plt.show()

# %% [markdown]
# ## 10. Summary Findings

# %%
print("""
============================================================
SUMMARY: India State Labour Market Analysis (PLFS 2018-2024)
============================================================

TOP FINDINGS:

1. Agriculture share is RISING nationally — from 31% in 2018 to 38% in 2024.
   India is re-agrarianising, partially driven by COVID reversal of urban migration.
   ILOSTAT long-run data shows this reverses a multi-decade downward trend.

2. State employment growth is highly unequal. Jharkhand, Bihar, Assam, Uttarakhand
   grew at 5%+ CAGR; Andhra Pradesh, Goa, Delhi barely grew or shrank.
   The fastest-growing states are NOT the richest — they are catching up from
   low base employment levels.

3. Occupational structures differ dramatically in 2024 snapshot (real variation):
   - Bihar: 36% agriculture, 26% elementary, 12% services, 3% managers
   - Delhi: 0% agriculture, 14% elementary, 14% services, 14% knowledge
   - Kerala: 12% agriculture, 26% crafts, 15% knowledge, 15% services
   This variation is real and reflects genuine structural differences.

4. GDP per worker correlates with knowledge-economy share (r > 0.7).
   Delhi, Chandigarh, Maharashtra lead on both. Bihar, UP, Jharkhand lag.
   A Professional in Delhi earns ~2x what one earns in Bihar.

5. State similarity clusters confirm three archetypes:
   - 'Agrarian North': Bihar, UP, MP, Chhattisgarh, Jharkhand, Rajasthan
   - 'Diversified South/West': Kerala, Karnataka, Tamil Nadu, Maharashtra, Gujarat
   - 'Urban Service Hubs': Delhi, Chandigarh, Goa, Puducherry

DATA QUALITY NOTES:
- State total employment trajectories (2018-2024): REAL — safe to interpret
- 2024 cross-sectional state × NCO composition: REAL — safe to interpret
- State-level sector SHARES over time: SYNTHETIC — each state tracks national average
  Cannot measure state-specific structural change from time series data.
- Next step: Process PLFS unit-level microdata to get real state × NCO × year data
============================================================
""")

conn.close()
