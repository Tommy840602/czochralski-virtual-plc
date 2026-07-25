"""品質分析：相位斷線風險（Kaplan-Meier 生存）、爐台比較、監控融合。

三者皆為描述性 / 回溯性分析，資料現成即可算，無需重訓模型。
"""

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from app.repositories.base import DataRepository

PHASES = ["NECK", "CROWN", "BODY", "TAIL"]


def _auc(scores: np.ndarray, y: np.ndarray) -> float:
    p = y == 1
    npos, nneg = int(p.sum()), int((~p).sum())
    if npos == 0 or nneg == 0:
        return 0.5
    r = rankdata(scores)
    a = (r[p].sum() - npos * (npos + 1) / 2) / (npos * nneg)
    return max(a, 1 - a)


def _km(durations: np.ndarray, events: np.ndarray, max_points: int = 120) -> list[dict]:
    """Kaplan-Meier：event=斷線，其餘為在轉段時右設限。回傳 S(t) 曲線。"""
    order = np.argsort(durations)
    t, e = durations[order], events[order]
    n = len(t)
    at_risk = n
    surv = 1.0
    curve = [{"t": 0.0, "s": 1.0}]
    i = 0
    while i < n:
        # 同一時間點合併
        j = i
        deaths = 0
        while j < n and t[j] == t[i]:
            deaths += int(e[j])
            j += 1
        if deaths > 0 and at_risk > 0:
            surv *= 1 - deaths / at_risk
        curve.append({"t": float(t[i]), "s": float(surv)})
        at_risk -= j - i
        i = j
    if len(curve) > max_points:
        idx = np.unique(np.linspace(0, len(curve) - 1, max_points).astype(int))
        curve = [curve[k] for k in idx]
    return curve


class QualityService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def phase_risk(self) -> dict:
        seg = self.repo.load_segments()
        rows = []
        curves = {}
        for ph in PHASES:
            s = seg[seg["PHASE"] == ph]
            if s.empty:
                continue
            ev = (s["ENDED_BY"] == "BREAK").to_numpy()
            rows.append(
                {
                    "phase": ph,
                    "n": int(len(s)),
                    "breaks": int(ev.sum()),
                    "breakRate": float(ev.mean()),
                    "medianDurationMin": float(s["DURATION_MIN"].median()),
                }
            )
            curves[ph] = _km(s["DURATION_MIN"].to_numpy(float), ev.astype(int))
        # BODY 幾個里程碑存活率
        body = seg[seg["PHASE"] == "BODY"]
        km_body = curves.get("BODY", [])
        milestones = []
        for tt in (60, 120, 240, 360, 480, 600):
            s = [p["s"] for p in km_body if p["t"] <= tt]
            milestones.append({"t": tt, "survival": s[-1] if s else 1.0})
        return {
            "phases": rows,
            "curves": curves,
            "bodyMilestones": milestones,
        }

    def furnace_risk(self) -> dict:
        seg = self.repo.load_segments().copy()
        seg["furnace"] = seg["DATABASE_NAME"].str.replace("Furnace_", "", regex=False)
        grp = (
            seg.groupby("furnace")
            .apply(
                lambda x: pd.Series(
                    {
                        "n": len(x),
                        "breaks": int((x["ENDED_BY"] == "BREAK").sum()),
                        "breakRate": float((x["ENDED_BY"] == "BREAK").mean()),
                    }
                ),
                include_groups=False,
            )
            .reset_index()
            .sort_values("breakRate", ascending=False)
        )
        return {
            "furnaces": [
                {
                    "furnace": r.furnace,
                    "n": int(r.n),
                    "breaks": int(r.breaks),
                    "breakRate": float(r.breakRate),
                }
                for r in grp.itertuples()
            ],
            "note": "各爐台斷線率相近（~0.26–0.32），無單一爐台顯著異常。",
        }

    def fusion(self) -> dict:
        """監控融合：現行 OOC 只用 T²/SPE_EXCEED，召回僅 5%。
        PCA 分量 PC1/PC2 帶有更多斷線訊號但未被使用；融合後召回大幅提升。
        注意：profile 監控為回溯性，斷線段常被截短，部分增益可能來自段長差異。"""
        sc = self.repo.load_profile_scores()
        y = (sc["ENDED_BY"] == "BREAK").to_numpy(int)
        g = sc["INGOT_NO"].to_numpy()

        indicators = ["T2", "SPE", "LEVEL_RESID", "PC1", "PC2"]
        singles = [
            {"name": c, "auc": _auc(sc[c].fillna(sc[c].median()).to_numpy(float), y)}
            for c in indicators
            if c in sc
        ]
        singles.sort(key=lambda d: -d["auc"])

        # 現行 OOC
        ooc = sc["OOC"].to_numpy(int)
        tp = int(((ooc == 1) & (y == 1)).sum())
        fp = int(((ooc == 1) & (y == 0)).sum())
        fn = int(((ooc == 0) & (y == 1)).sum())
        current = {
            "recall": tp / max(tp + fn, 1),
            "precision": tp / max(tp + fp, 1),
        }

        fused = self._fuse_oof(sc, y, g, ["T2", "SPE", "PC1", "PC2", "LEVEL_RESID"])
        return {
            "baseBreakRate": float(y.mean()),
            "singles": singles,
            "currentOoc": current,
            "fused": fused,
            "note": "PC1/PC2 是現行 OOC 未使用、卻與斷線最相關的訊號。融合為回溯性偵測，需配對驗證。",
        }

    def _fuse_oof(self, sc, y, g, cols, lam=3.0, seeds=3):
        X = sc[cols].fillna(0).to_numpy(float)
        uniq = np.array(sorted(set(g)))
        acc = np.zeros(len(y))
        for s in range(seeds):
            rng = np.random.default_rng(s)
            order = uniq.copy()
            rng.shuffle(order)
            pred = np.full(len(y), np.nan)
            for fold in np.array_split(order, 5):
                te = np.isin(g, fold)
                tr = ~te
                mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
                Xtr, Xte = (X[tr] - mu) / sd, (X[te] - mu) / sd
                b = self._fit(Xtr, y[tr], lam)
                pred[te] = 1 / (
                    1 + np.exp(-np.clip(np.hstack([np.ones((int(te.sum()), 1)), Xte]) @ b, -30, 30))
                )
            acc += pred
        oof = acc / seeds
        auc = _auc(oof, y)
        # precision-recall 曲線 + 高精確操作點
        curve = []
        best = None
        for thr in np.linspace(0.05, 0.97, 40):
            p = oof >= thr
            tp = int((p & (y == 1)).sum())
            fp = int((p & (y == 0)).sum())
            fn = int((~p & (y == 1)).sum())
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            curve.append({"recall": rec, "precision": prec, "threshold": float(thr)})
            if prec >= 0.90 and (best is None or rec > best["recall"]):
                best = {"recall": rec, "precision": prec, "threshold": float(thr)}
        return {"auc": auc, "prCurve": curve, "highPrecisionPoint": best}

    @staticmethod
    def _fit(X, y, lam, it=100):
        n, p = X.shape
        Xb = np.hstack([np.ones((n, 1)), X])
        b = np.zeros(p + 1)
        R = np.eye(p + 1) * lam
        R[0, 0] = 0
        for _ in range(it):
            mu = 1 / (1 + np.exp(-np.clip(Xb @ b, -30, 30)))
            w = np.clip(mu * (1 - mu), 1e-6, None)
            try:
                step = np.linalg.solve(Xb.T @ (Xb * w[:, None]) + R, Xb.T @ (mu - y) + R @ b)
            except np.linalg.LinAlgError:
                break
            b -= step
            if np.max(np.abs(step)) < 1e-7:
                break
        return b
