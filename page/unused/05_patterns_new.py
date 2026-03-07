import warnings
import numpy as np
import pandas as pd
from tqdm import tqdm
from scipy.stats import zscore

# -------------------------------------------------------------
# 1️⃣ Parameters
# -------------------------------------------------------------
CSV_PATH          = "./data/tefas_transformed.csv"   # <-- adjust
WINDOW_LEN        = 30          # days
HORIZON          = 5           # days ahead
K_NEIGHBORS      = 5           # neighbours to keep
MIN_TRADING_DAYS = 3 * 252     # ≈ 756 days

# -------------------------------------------------------------
# 2️⃣ Helper – sliding windows
# -------------------------------------------------------------
def sliding_windows(series: pd.Series, win_len: int):
    """Return (windows_array, start_dates)"""
    vals   = series.values
    dates  = series.index
    n      = len(series)
    win    = []
    starts = []
    for i in range(0, n - win_len + 1):
        win.append(vals[i:i+win_len])
        starts.append(dates[i])
    return np.array(win), starts

# -------------------------------------------------------------
# 3️⃣ Load data & compute returns
# -------------------------------------------------------------
print("Loading data…")
df_raw = pd.read_csv(CSV_PATH, parse_dates=['date'])
df_raw = df_raw[['symbol', 'date', 'close']].dropna()
df_raw = df_raw.sort_values(['symbol', 'date'])

df_raw['ret'] = np.log(df_raw['close']) - np.log(df_raw['close'].shift(1))
df_ret = df_raw.dropna(subset=['ret'])

# Keep symbols with ≥ 3 years of data
symbols = df_ret['symbol'].unique()
symbols = [s for s in symbols if df_ret[df_ret['symbol'] == s].shape[0] >= MIN_TRADING_DAYS]
print(f"Using {len(symbols)} symbols with ≥ 3 years of data.")

# -------------------------------------------------------------
# 4️⃣ Build concatenated window table
# -------------------------------------------------------------
print("Building all windows…")
all_windows   = []          # list of arrays (n_win, WINDOW_LEN)
all_starts    = []          # list of pd.Timestamp
all_symbols   = []          # list of str
ret_series_dict = {}        # {symbol: pd.Series}

for sym in tqdm(symbols, desc="windows"):
    df_sym   = df_ret[df_ret['symbol'] == sym].sort_values('date')
    ret_series = df_sym.set_index('date')['ret']
    ret_series_dict[sym] = ret_series

    wins, starts = sliding_windows(ret_series, WINDOW_LEN)
    if wins.shape[0] == 0:   # symbol too short
        warnings.warn(f"Symbol {sym!r} has fewer than {WINDOW_LEN} days; skipped.")
        continue

    all_windows.append(wins)
    all_starts.extend(starts)
    all_symbols.extend([sym] * len(starts))

if not all_windows:
    raise RuntimeError("No windows were built – check the data.")

# Concatenate
windows_np = np.concatenate([np.vstack(w) for w in all_windows], axis=0)   # shape (N, WINDOW_LEN)
sym_arr    = np.array(all_symbols, dtype=object)                           # length N
# -------------------------------------------------------------
# 5️⃣ Z‑score & drop NaNs
# -------------------------------------------------------------
print("Z‑scoring windows…")
windows_std = zscore(windows_np, axis=1, ddof=0)

# Drop rows that still contain NaNs
valid = ~np.isnan(windows_std).any(axis=1)
windows_std = windows_std[valid]
sym_arr     = sym_arr[valid]
all_starts  = [s for s in all_starts if s in all_starts]  # keep only those that survived
all_starts  = [all_starts[i] for i, v in enumerate(valid) if v]  # align with valid rows

print(f"Total windows: {windows_std.shape[0]}")
print(f"Symbols kept after cleaning: {len(set(sym_arr))}")

# -------------------------------------------------------------
# 6️⃣ Helper – nearest neighbours from a *different* symbol
# -------------------------------------------------------------
def find_best_matches(curr_std: np.ndarray, curr_sym: str, k: int = K_NEIGHBORS):
    """Return indices of the k nearest windows that belong to a different symbol."""
    # Euclidean distances against *all* windows
    dists = np.linalg.norm(curr_std - windows_std, axis=1)

    # Mask windows that belong to *different* symbol
    diff_mask = sym_arr != curr_sym
    if not diff_mask.any():
        return np.array([], dtype=int)

    dists_diff = dists[diff_mask]
    diff_idx   = np.where(diff_mask)[0]          # indices in the concatenated table

    if dists_diff.size < k:
        k = dists_diff.size

    nearest = np.argsort(dists_diff)[:k]
    return diff_idx[nearest]   # indices in concatenated table

# -------------------------------------------------------------
# 7️⃣ Loop over symbols – compute best matches
# -------------------------------------------------------------
print("Matching symbols…")
output_rows = []

for sym in tqdm(symbols, desc="matching"):
    # indices of all windows for this symbol
    sym_mask    = sym_arr == sym
    sym_idx_all = np.where(sym_mask)[0]
    if sym_idx_all.size == 0:
        continue

    # last window (most recent) of this symbol
    last_idx   = sym_idx_all[-1]
    curr_std   = windows_std[last_idx]            # already z‑scored
    curr_start = all_starts[last_idx]             # start date of that window

    # find best neighbours from other symbols
    best_idx = find_best_matches(curr_std, sym, k=K_NEIGHBORS)

    # build list of match‑dicts
    matches = []
    for idx in best_idx:
        match_sym   = sym_arr[idx]
        match_start = all_starts[idx]
        dist        = np.linalg.norm(curr_std - windows_std[idx])

        # next HORIZON returns after the matching window
        match_ret_series = ret_series_dict[match_sym]
        # the window covers [match_start, match_start + WINDOW_LEN-1]
        horizon_start = match_start
        horizon_returns = match_ret_series.loc[
            horizon_start : horizon_start + pd.Timedelta(days=HORIZON-1)
        ].values

        if horizon_returns.size < HORIZON:
            horizon_returns = np.full(HORIZON, np.nan)

        matches.append({
            'match_symbol'    : match_sym,
            'match_date'      : match_start,
            'distance'        : dist,
            'horizon_returns': horizon_returns
        })

    # ---- keep the *best* neighbour (first in the list)
    best = matches[0] if matches else None
    output_rows.append({
        'symbol'          : sym,
        'current_window'  : curr_start,
        'match_symbol'    : best['match_symbol'] if best else np.nan,
        'match_date'      : best['match_date'] if best else pd.NaT,
        'distance'        : best['distance'] if best else np.nan,
        'horizon_returns' : best['horizon_returns'] if best else np.full(HORIZON, np.nan)
    })

# -------------------------------------------------------------
# 8️⃣ Build final DataFrame
# -------------------------------------------------------------
df_final = pd.DataFrame(output_rows)
print("\nResult table (first 10 rows):")
print(df_final.head(10))

# -------------------------------------------------------------
# 9️⃣ Optional: save
# -------------------------------------------------------------
OUT_CSV = "patterns_best_matches.csv"
df_final.to_csv(OUT_CSV, index=False)
print(f"\nSaved to {OUT_CSV}.")