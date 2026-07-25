import numpy as np
import pandas as pd
from scipy import stats

from app.repositories.base import DataRepository
from app.services.catalog_service import records

# precursor_windows 中非特徵的識別欄
ID_COLUMNS = {"INGOT_NO", "SEGMENT_SEQ", "DATABASE_NAME", "GROUP", "N", "WIN_END_POS"}

FEATURE_LABELS = {
    "mean": "均值",
    "absmean": "絕對均值",
    "sd": "標準差",
    "slope": "斜率",
    "rollsd": "滾動標準差",
    "range": "全距",
    "delta": "首尾差",
}


def _auc_and_p(case: np.ndarray, control: np.ndarray) -> tuple[float, float]:
    """以 Mann-Whitney U 同時取得 AUC 與 p 值。

    AUC = U / (n_case × n_control)，即 P(case 的值 > control 的值)。
    AUC < 0.5 代表該特徵在 case 組偏低，一樣具鑑別力，方向相反而已。
    """
    if len(case) < 3 or len(control) < 3:
        return float("nan"), float("nan")
    result = stats.mannwhitneyu(case, control, alternative="two-sided")
    return float(result.statistic / (len(case) * len(control))), float(result.pvalue)


def _bh_fdr(pvalues: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg 校正。一次掃上百個特徵，不校正必然出現假陽性。"""
    p = np.asarray(pvalues, dtype=float)
    ok = ~np.isnan(p)
    q = np.full_like(p, np.nan)
    if not ok.any():
        return q

    valid = p[ok]
    n = len(valid)
    order = np.argsort(valid)
    ranked = valid[order]
    adjusted = ranked * n / np.arange(1, n + 1)
    # 由大到小取累積最小值，確保 q 值單調
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1].clip(max=1.0)

    out = np.empty(n)
    out[order] = adjusted
    q[ok] = out
    return q


class PrecursorService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def _windows(self) -> pd.DataFrame:
        return self.repo.load_precursor_windows()

    def feature_columns(self) -> list[str]:
        return [c for c in self._windows().columns if c not in ID_COLUMNS]

    def overview(self) -> dict:
        w = self._windows()
        counts = w["GROUP"].value_counts()
        signals = sorted({c.split("::")[0] for c in self.feature_columns()})
        features = sorted({c.split("::")[1] for c in self.feature_columns()})
        return {
            "nCase": int(counts.get("case", 0)),
            "nControl": int(counts.get("control", 0)),
            "nFeatures": len(self.feature_columns()),
            "signals": signals,
            "features": [
                {"value": f, "label": FEATURE_LABELS.get(f, f)} for f in features
            ],
            "windowLength": int(w["N"].median()) if "N" in w else None,
        }

    def ranking(
        self,
        signals: list[str] | None = None,
        features: list[str] | None = None,
        min_discriminance: float = 0.0,
    ) -> list[dict]:
        """線上重算 AUC 排行，可依訊號 / 特徵子集篩選。"""
        w = self._windows()
        case_mask = w["GROUP"] == "case"

        columns = self.feature_columns()
        if signals:
            columns = [c for c in columns if c.split("::")[0] in signals]
        if features:
            columns = [c for c in columns if c.split("::")[1] in features]

        rows = []
        for col in columns:
            values = pd.to_numeric(w[col], errors="coerce")
            case = values[case_mask].dropna().to_numpy()
            control = values[~case_mask].dropna().to_numpy()
            auc, p = _auc_and_p(case, control)
            if np.isnan(auc):
                continue
            signal, feature = col.split("::")
            rows.append(
                {
                    "key": col,
                    "signal": signal,
                    "feature": feature,
                    "featureLabel": FEATURE_LABELS.get(feature, feature),
                    "auc": auc,
                    "discriminance": abs(auc - 0.5) * 2,
                    "direction": "case 偏高" if auc > 0.5 else "case 偏低",
                    "p": p,
                    "nCase": int(len(case)),
                    "nControl": int(len(control)),
                }
            )

        if not rows:
            return []

        qs = _bh_fdr(np.array([r["p"] for r in rows]))
        for row, q in zip(rows, qs):
            row["q"] = None if np.isnan(q) else float(q)

        rows = [r for r in rows if r["discriminance"] >= min_discriminance]
        return sorted(rows, key=lambda r: r["discriminance"], reverse=True)

    def detail(self, key: str, roc_points: int = 120) -> dict:
        """單一特徵的 ROC 曲線與 case/control 分布。"""
        w = self._windows()
        if key not in w.columns:
            raise KeyError(key)

        values = pd.to_numeric(w[key], errors="coerce")
        valid = values.notna()
        scores = values[valid].to_numpy(float)
        labels = (w.loc[valid, "GROUP"] == "case").to_numpy()

        auc, p = _auc_and_p(scores[labels], scores[~labels])
        # AUC < 0.5 時反轉分數方向，ROC 才畫得出有意義的曲線
        oriented = scores if auc >= 0.5 else -scores

        roc = self._roc(oriented, labels, roc_points)
        signal, feature = key.split("::")

        return {
            "key": key,
            "signal": signal,
            "feature": feature,
            "featureLabel": FEATURE_LABELS.get(feature, feature),
            "auc": auc,
            "orientedAuc": max(auc, 1 - auc),
            "p": p,
            "flipped": auc < 0.5,
            "roc": roc,
            "distribution": {
                "case": self._describe(scores[labels]),
                "control": self._describe(scores[~labels]),
            },
            "samples": {
                "case": scores[labels].round(6).tolist(),
                "control": scores[~labels].round(6).tolist(),
            },
        }

    @staticmethod
    def _roc(scores: np.ndarray, labels: np.ndarray, max_points: int) -> list[dict]:
        order = np.argsort(-scores)
        y = labels[order]
        tps = np.cumsum(y)
        fps = np.cumsum(~y)
        n_pos, n_neg = max(int(y.sum()), 1), max(int((~y).sum()), 1)

        tpr = np.concatenate([[0.0], tps / n_pos])
        fpr = np.concatenate([[0.0], fps / n_neg])
        thresholds = np.concatenate([[np.inf], scores[order]])

        if len(tpr) > max_points:
            idx = np.unique(np.linspace(0, len(tpr) - 1, max_points).astype(int))
        else:
            idx = np.arange(len(tpr))

        return [
            {
                "fpr": float(fpr[i]),
                "tpr": float(tpr[i]),
                "threshold": None if np.isinf(thresholds[i]) else float(thresholds[i]),
            }
            for i in idx
        ]

    @staticmethod
    def _describe(values: np.ndarray) -> dict:
        if values.size == 0:
            return {}
        q1, med, q3 = np.percentile(values, [25, 50, 75])
        return {
            "n": int(values.size),
            "min": float(values.min()),
            "q1": float(q1),
            "median": float(med),
            "q3": float(q3),
            "max": float(values.max()),
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        }

    def sweep(self, signal: str | None = None, feature: str | None = None) -> list[dict]:
        """離線算好的「提前多久仍偵測得到」掃描結果。"""
        df = self.repo.load_precursor_sweep().rename(
            columns={"訊號": "signal", "特徵": "feature"}
        )
        if signal:
            df = df[df["signal"] == signal]
        if feature:
            df = df[df["feature"] == feature]
        df = df.rename(
            columns={"OFFSET": "offset", "n_case": "nCase", "AUC": "auc"}
        )
        return records(df.sort_values(["signal", "feature", "offset"]))

    def offline_auc(self) -> list[dict]:
        df = self.repo.load_precursor_auc().rename(
            columns={
                "訊號": "signal",
                "特徵": "feature",
                "AUC": "auc",
                "鑑別力": "discriminance",
            }
        )
        return records(df.sort_values("discriminance", ascending=False))
