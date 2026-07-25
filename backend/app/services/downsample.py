import numpy as np


def lttb(x: np.ndarray, y: np.ndarray, threshold: int) -> np.ndarray:
    """Largest-Triangle-Three-Buckets 降採樣，回傳保留的索引。

    相較於等間隔抽樣，LTTB 會保住尖峰與轉折，這對看 PLC 波形是關鍵：
    直徑震盪與加熱器功率的突跳不能被抽掉。
    """
    n = len(x)
    if threshold >= n or threshold < 3:
        return np.arange(n)

    # 首尾固定保留，中間切成 threshold-2 個桶，每桶挑一點
    bucket_size = (n - 2) / (threshold - 2)
    sampled = np.empty(threshold, dtype=np.int64)
    sampled[0] = 0
    sampled[-1] = n - 1

    a = 0
    for i in range(threshold - 2):
        # 下一個桶的平均點，作為三角形的第三頂點
        next_lo = int(np.floor((i + 1) * bucket_size)) + 1
        next_hi = min(int(np.floor((i + 2) * bucket_size)) + 1, n)
        if next_lo >= next_hi:
            next_lo, next_hi = next_hi - 1, next_hi
        avg_x = x[next_lo:next_hi].mean()
        avg_y = y[next_lo:next_hi].mean()

        lo = int(np.floor(i * bucket_size)) + 1
        hi = min(int(np.floor((i + 1) * bucket_size)) + 1, n - 1)
        if lo >= hi:
            sampled[i + 1] = a = lo
            continue

        # 挑出與 (a, avg) 構成面積最大的點
        area = np.abs(
            (x[a] - avg_x) * (y[lo:hi] - y[a]) - (x[a] - x[lo:hi]) * (avg_y - y[a])
        )
        sampled[i + 1] = a = lo + int(np.argmax(area))

    return sampled


def downsample_frame(
    timestamps: np.ndarray, values: np.ndarray, threshold: int
) -> np.ndarray:
    """對含 NaN 的訊號做 LTTB：NaN 不參與選點，但保留原始索引位置。"""
    valid = np.flatnonzero(~np.isnan(values))
    if len(valid) <= threshold:
        return valid
    keep = lttb(timestamps[valid].astype(np.float64), values[valid], threshold)
    return valid[keep]
