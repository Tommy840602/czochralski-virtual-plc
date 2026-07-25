"""配對世代 BODY 斷線前置時間分析（可重現管線）。

問題：提前多久能預測 BODY 斷線？naive 擴樣本會被混淆膨脹（見
docs/body_break_confound_audit.md）。本管線以「同群體 + Residual Weight（熔料剩餘，
生長階段代理）配對」建立公平世代，量測 AUC 隨提前時間的**衰減**——真前兆會衰減，
混淆則否。

輸出：backend/app/assets/matched_break_leadcurve.json（前端「前置時間分析」面板讀取）。

用法：
    python analysis/matched_break_pipeline.py --data-root /path/to/output

依賴：pandas, numpy, scipy, pyarrow（與後端相同）。
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

WIN = 180  # ~30 分鐘視窗（10s 取樣）
LEADS = [0, 20, 40, 60]
SIGNALS = [
    "D_mean", "Heater Power SV", "Seed lift", "Heater temp", "PIDSL_temp1",
    "PIDSL_dDmean", "Crucible lift ratio", "Thro Valve Open", "Argon gas flow rate",
    "Lower chamber press", "MAGNET PV", "temp2", "temp4", "temp5", "temp9", "temp29",
]
ERR = {
    "D_ERR": ("Diameter", "Diameter target"),
    "HT_ERR": ("Heater temp", "Heater temp target"),
    "SL_ERR": ("Seed lift", "Seed lift target"),
}


def _auc(scores, y):
    p = y == 1
    npos, nneg = int(p.sum()), int((~p).sum())
    if npos == 0 or nneg == 0:
        return 0.5
    r = rankdata(scores)
    return (r[p].sum() - npos * (npos + 1) / 2) / (npos * nneg)


def _fit(X, y, lam, it=80):
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


def _oof(X, y, g, lam=30, k=5, seeds=3):
    uniq = np.array(sorted(set(g)))
    acc = np.zeros(len(y))
    for s in range(seeds):
        rng = np.random.default_rng(s)
        order = uniq.copy()
        rng.shuffle(order)
        pred = np.full(len(y), np.nan)
        for fold in np.array_split(order, k):
            te = np.isin(g, fold)
            tr = ~te
            med = np.nanmedian(X[tr], 0)
            Xtr = np.where(np.isnan(X[tr]), med, X[tr])
            Xte = np.where(np.isnan(X[te]), med, X[te])
            mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
            Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
            b = _fit(Xtr, y[tr], lam)
            pred[te] = 1 / (1 + np.exp(-np.clip(np.hstack([np.ones((int(te.sum()), 1)), Xte]) @ b, -30, 30)))
        acc += pred
    return acc / seeds


class Pipeline:
    def __init__(self, data_root: str):
        self.root = data_root
        self.seg = pd.read_parquet(f"{data_root}/segment_summary.parquet")
        self.body = self.seg[self.seg.PHASE == "BODY"]
        self._cache: dict[str, pd.DataFrame | None] = {}

    def _load(self, ingot):
        if ingot not in self._cache:
            paths = glob.glob(f"{self.root}/rawdata/*/{ingot}_*.parquet")
            self._cache[ingot] = pd.read_parquet(paths[0]) if paths else None
        return self._cache[ingot]

    @staticmethod
    def _feats(w):
        f, cols = {}, {}
        for c in SIGNALS:
            if c in w:
                cols[c] = pd.to_numeric(w[c], errors="coerce").to_numpy(float)
        for nm, (a, b) in ERR.items():
            if a in w and b in w:
                cols[nm] = (
                    pd.to_numeric(w[a], errors="coerce").to_numpy(float)
                    - pd.to_numeric(w[b], errors="coerce").to_numpy(float)
                )
        for nm, x in cols.items():
            x = x[~np.isnan(x)]
            if len(x) < 8:
                continue
            n, t, h, third = len(x), np.arange(len(x)), len(x) // 2, max(len(x) // 3, 3)
            f[f"{nm}::mean"] = x.mean()
            f[f"{nm}::sd"] = x.std()
            f[f"{nm}::absmean"] = np.abs(x).mean()
            f[f"{nm}::range"] = x.max() - x.min()
            f[f"{nm}::slope"] = np.polyfit(t, x, 1)[0]
            f[f"{nm}::delta"] = x[-1] - x[0]
            f[f"{nm}::accel"] = (
                np.polyfit(np.arange(n - h), x[h:], 1)[0] - np.polyfit(np.arange(h), x[:h], 1)[0]
            )
            f[f"{nm}::endshift"] = x[-third:].mean() - x[:third].mean()
            f[f"{nm}::rollsd"] = pd.Series(x).rolling(min(20, n)).std().mean()
        return f

    @staticmethod
    def _resid(w):
        return (
            pd.to_numeric(w["Residual Weight"], errors="coerce").median()
            if "Residual Weight" in w
            else np.nan
        )

    def _pools(self, lead_min):
        lead = pd.Timedelta(minutes=lead_min)
        cases, ctrls = [], []
        for _, r in self.body[self.body.ENDED_BY == "BREAK"].iterrows():
            d = self._load(r.INGOT_NO)
            if d is None:
                continue
            w = d[(d.LogTime >= r.START_TIME) & (d.LogTime <= r.END_TIME - lead)].tail(WIN)
            if len(w) < 60:
                continue
            f = self._feats(w)
            if f:
                cases.append({**f, "_rw": self._resid(w), "_g": r.DATASET_TYPE, "_ing": r.INGOT_NO})
        for _, r in self.body[self.body.ENDED_BY.isin(["ADVANCE", "COMPLETE"])].iterrows():
            d = self._load(r.INGOT_NO)
            if d is None:
                continue
            ww = d[(d.LogTime >= r.START_TIME) & (d.LogTime <= r.END_TIME)]
            if len(ww) < 120:
                continue
            for frac in (0.35, 0.55, 0.75, 0.95):
                end = int(len(ww) * frac)
                w = ww.iloc[max(0, end - WIN):end]
                if len(w) < 60:
                    continue
                f = self._feats(w)
                if f:
                    ctrls.append({**f, "_rw": self._resid(w), "_g": r.DATASET_TYPE, "_ing": r.INGOT_NO})
        return pd.DataFrame(cases), pd.DataFrame(ctrls)

    @staticmethod
    def _match(cases, ctrls, caliper=1.0, ratio=2):
        """同群體 + |Residual Weight| 相近，1:ratio 最近配對，排除同晶棒、不重複用 control。"""
        used, rows, lab, grp = set(), [], [], []
        cp = ctrls.dropna(subset=["_rw"]).reset_index(drop=True)
        for _, c in cases.dropna(subset=["_rw"]).iterrows():
            cand = cp[(cp._g == c._g) & (cp._ing != c._ing) & (~cp.index.isin(used))].copy()
            if len(cand) == 0:
                continue
            cand["d"] = (cand._rw - c._rw).abs()
            cand = cand[cand.d <= caliper].nsmallest(ratio, "d")
            if len(cand) == 0:
                continue
            rows.append(c)
            lab.append(1)
            grp.append(c._ing)
            for idx, cc in cand.iterrows():
                used.add(idx)
                rows.append(cc)
                lab.append(0)
                grp.append(cc._ing)
        return pd.DataFrame(rows), np.array(lab), np.array(grp)

    @staticmethod
    def _feature_cols(M):
        return [c for c in M.columns if "::" in c]

    def _eval(self, M, y, g, lam=30, boot=300):
        X = M[self._feature_cols(M)].to_numpy(float)
        oof = _oof(X, y, g, lam=lam)
        auc = _auc(oof, y)
        uniq = np.array(sorted(set(g)))
        rng = np.random.default_rng(0)
        bs = []
        for _ in range(boot):
            samp = rng.choice(uniq, len(uniq))
            idx = np.concatenate([np.where(g == u)[0] for u in samp])
            bs.append(_auc(oof[idx], y[idx]))
        return {
            "auc": float(auc),
            "lo": float(np.percentile(bs, 2.5)),
            "hi": float(np.percentile(bs, 97.5)),
            "nCase": int(y.sum()),
            "nControl": int((y == 0).sum()),
        }

    def run(self):
        matched, naive = [], []
        for lead in LEADS:
            cases, ctrls = self._pools(lead)
            # 配對世代
            M, y, g = self._match(cases, ctrls)
            m = self._eval(M, y, g)
            m["lead"] = lead
            matched.append(m)
            # naive（未配對，全體 control）作對照
            allrows = pd.concat([cases.assign(_y=1), ctrls.assign(_y=0)], ignore_index=True)
            yn = allrows["_y"].to_numpy()
            gn = allrows["_ing"].to_numpy()
            n = self._eval(allrows, yn, gn, boot=100)
            n["lead"] = lead
            naive.append(n)
            print(f"lead {lead:>3}m  matched AUC {m['auc']:.3f} [{m['lo']:.3f},{m['hi']:.3f}]"
                  f"  naive {n['auc']:.3f}")
        return {
            "description": "BODY 斷線前置時間分析：配對世代 vs naive。配對衰減=真前兆；naive 持平=混淆。",
            "window_min": 30,
            "matched": matched,
            "naive": naive,
        }


def main():
    ap = argparse.ArgumentParser()
    default_root = str(Path(__file__).resolve().parents[2])
    ap.add_argument("--data-root", default=default_root)
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "backend/app/assets/matched_break_leadcurve.json"),
    )
    args = ap.parse_args()

    result = Pipeline(args.data_root).run()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"→ 寫入 {out}")


if __name__ == "__main__":
    main()
