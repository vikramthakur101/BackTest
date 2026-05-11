import pandas as pd
import numpy as np

# --- 1. CONFIGURATION ---
START_DATE = '2022-05-10'  # Format: YYYY-MM-DD
END_DATE = '2026-05-6'

SESSIONS = {
    'asia': {'start': '18:00', 'end': '02:00'},
    'london': {'start': '02:00', 'end': '11:00'},
    'newyork': {'start': '07:30', 'end': '16:00'}
}

# --- 2. DATA LOADING & FILTERING ---
df = pd.read_csv('C:/VIKRAM/HISTORICAL DATA/NAS 1min 5yrs.csv')
df['DateTime'] = pd.to_datetime(df['DateTime'], dayfirst=True)

# Convert to NY Time for consistent session tracking
df = df.set_index('DateTime').tz_localize('Asia/Kolkata').tz_convert('America/New_York')

# APPLY CUSTOM DATE RANGE
df = df.loc[START_DATE: END_DATE]
df['Date'] = df.index.date


# --- 3. LEVEL GENERATION ---
def get_ranges(df, session_dict):
    for sess, times in session_dict.items():
        sess_data = df.between_time(times['start'], times['end'])
        ranges = sess_data.groupby('Date').agg(
            h=('High', 'max'), l=('Low', 'min')
        ).rename(columns={'h': f'{sess}_h', 'l': f'{sess}_l'})
        df = df.merge(ranges, left_on='Date', right_index=True, how='left')
    return df


df = get_ranges(df, SESSIONS)

# Shift levels so we use the CORRECT prior session
df['prior_asia_h'] = df['asia_h'].shift(1)
df['prior_asia_l'] = df['asia_l'].shift(1)
df['prior_london_h'] = df['london_h']  # London is same-day for NY
df['prior_london_l'] = df['london_l']


# --- 4. PURGE & REVERT STATS LOGIC ---
def analyze_occurrences(df):
    # Total unique trading days in the range
    total_days = df['Date'].nunique()

    # 1. London Purging Asia
    df['lon_purge_asia'] = np.where(
        (df.index.time >= pd.to_datetime('03:00').time()) & (df.index.time <= pd.to_datetime('11:00').time()) &
        ((df['High'] > df['prior_asia_h']) | (df['Low'] < df['prior_asia_l'])), 1, 0
    )

    # 2. NY Purging London
    df['ny_purge_lon'] = np.where(
        (df.index.time >= pd.to_datetime('08:30').time()) & (df.index.time <= pd.to_datetime('16:00').time()) &
        ((df['High'] > df['prior_london_h']) | (df['Low'] < df['prior_london_l'])), 1, 0
    )

    # Count days where at least one purge event happened
    lon_days = df.groupby('Date')['lon_purge_asia'].max().sum()
    ny_days = df.groupby('Date')['ny_purge_lon'].max().sum()

    # --- 5. DISPLAY RESULTS ---
    print(f"--- Statistics from {START_DATE} to {END_DATE} ---")
    print(f"Total Trading Days Analyzed: {total_days}")
    print("-" * 40)

    stats = pd.DataFrame({
        'Session Setup': ['London Purges Asia', 'NY Purges London'],
        'Occurrences (Days)': [lon_days, ny_days],
        'Frequency (%)': [round((lon_days / total_days) * 100, 2), round((ny_days / total_days) * 100, 2)]
    })

    return stats


# Execute Analysis
stats_table = analyze_occurrences(df)
print(stats_table)

# Save the detailed data
df.to_csv('session_analysis_full_report.csv')