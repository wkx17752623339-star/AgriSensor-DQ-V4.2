"""Observable, explainable data-quality metrics. No ground-truth faults inferred."""
import numpy as np
import pandas as pd
from engine import normalize


def extra_quality(df, stuck_min_samples=6, gap_multiplier=3.0):
    if stuck_min_samples < 2 or gap_multiplier <= 1:
        raise ValueError('恒值最短记录数必须>=2，间隔倍数必须>1')
    d = normalize(df)
    rows = []
    for node, g in d.groupby('node_id', sort=True):
        g = g.sort_values('timestamp', kind='stable').reset_index(drop=True)
        n = len(g)
        x, h, ts = g['temperature'], g['humidity'], g['timestamp']
        delta = ts.diff().dt.total_seconds()
        positive = delta[delta > 0]
        typical = float(positive.median()) if len(positive) else np.nan
        gaps = (delta > typical * gap_multiplier) if np.isfinite(typical) else pd.Series(False, index=g.index)
        gap_count = int(gaps.sum())
        dup_count = int(ts.duplicated().sum())
        missing_count = int((x.isna() | h.isna()).sum())
        # A run is consecutive identical, non-null temperature readings.
        valid = x.notna()
        same = valid & valid.shift(fill_value=False) & x.eq(x.shift())
        run_id = (~same).cumsum()
        lengths = x[valid].groupby(run_id[valid]).size()
        long_runs = lengths[lengths >= stuck_min_samples]
        stuck_runs = int(len(long_runs))
        stuck_samples = int(long_runs.sum())
        missing_rate = missing_count / n if n else 0
        duplicate_rate = dup_count / n if n else 0
        gap_rate = gap_count / max(n - 1, 1)
        stuck_rate = stuck_samples / n if n else 0
        deductions = {
            '缺失扣分': 50 * missing_rate,
            '重复扣分': 10 * duplicate_rate,
            '间隔扣分': 20 * gap_rate,
            '恒值扣分': 20 * stuck_rate,
        }
        score = max(0, 100 - sum(deductions.values()))
        rssi = g['rssi']
        snr = pd.to_numeric(g['snr'], errors='coerce') if 'snr' in g else pd.Series(dtype=float)
        rows.append({
            'node_id': node, '完整率': round(100 * (1 - missing_rate), 2),
            '温度标准差': round(float(x.std()), 2) if x.notna().sum() > 1 else np.nan,
            '疑似卡死片段': stuck_runs, '疑似卡死记录数': stuck_samples,
            '时间间隔异常数': gap_count,
            '典型采样间隔(秒)': round(typical, 1) if np.isfinite(typical) else np.nan,
            '最大采样间隔(秒)': round(float(positive.max()), 1) if len(positive) else np.nan,
            '重复时间戳数': dup_count,
            '平均RSSI': round(float(rssi.mean()), 1) if rssi.notna().any() else np.nan,
            '平均SNR': round(float(snr.mean()), 2) if snr.notna().any() else np.nan,
            **{k: round(v, 4) for k, v in deductions.items()},
            '扩展数据质量分': round(score, 2),
        })
    return pd.DataFrame(rows)
