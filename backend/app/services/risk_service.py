"""操作型風險匯總：把站得住的訊號合成每段/每晶棒的風險回顧。

刻意保持兩個組件**分開且標示其性質**，不混成單一不透明分數：
  A. 監控偵測風險 —— profile PC1/PC2/SPE 融合的 OOF 機率（回溯性，段結束後才有）。
  B. 時間風險先驗 —— Kaplan-Meier hazard，由生長時數給出的基礎斷線率（先驗，非偵測）。

用途定位：**回溯性風險回顧 / 研究審視**，非即時預測。時間先驗可即時用（只需生長時數）；
監控偵測回溯性。頁面明確標示，避免把先驗/回溯當成預測力。
"""

import numpy as np
from scipy.stats import rankdata

from app.repositories.base import DataRepository

FUSION_COLS = ["T2", "SPE", "PC1", "PC2", "LEVEL_RESID"]
MILESTONES = (60, 120, 240, 360, 480, 600)


def _auc(scores, y):
    p = y == 1
    npos, nneg = int(p.sum()), int((~p).sum())
    if npos == 0 or nneg == 0:
        return 0.5
    r = rankdata(scores)
    a = (r[p].sum() - npos * (npos + 1) / 2) / (npos * nneg)
    return max(a, 1 - a)


class RiskService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    # ---------- 時間風險先驗（KM） ----------

    def _km_body(self):
        seg = self.repo.load_segments()
        body = seg[seg["PHASE"] == "BODY"]
        t = body["DURATION_MIN"].to_numpy(float)
        e = (body["ENDED_BY"] == "BREAK").to_numpy(int)
        order = np.argsort(t)
        t, e = t[order], e[order]
        n = len(t)
        at_risk, surv = n, 1.0
        ts, ss = [0.0], [1.0]
        i = 0
        while i < n:
            j, deaths = i, 0
            while j < n and t[j] == t[i]:
                deaths += int(e[j])
                j += 1
            if deaths and at_risk:
                surv *= 1 - deaths / at_risk
            ts.append(float(t[i]))
            ss.append(float(surv))
            at_risk -= j - i
            i = j
        return np.array(ts), np.array(ss)

    def _hazard_at(self, ts, ss, duration):
        """1 - S(t)：生長到此時數的累積斷線先驗。"""
        s = np.interp(duration, ts, ss)
        return float(1 - s)

    def hazard_curve(self):
        ts, ss = self._km_body()
        idx = np.unique(np.linspace(0, len(ts) - 1, 120).astype(int))
        curve = [{"t": float(ts[k]), "hazard": float(1 - ss[k])} for k in idx]
        milestones = [{"t": m, "hazard": self._hazard_at(ts, ss, m)} for m in MILESTONES]
        return {"curve": curve, "milestones": milestones}

    # ---------- 監控偵測風險（融合 OOF） ----------

    def _fusion_scores(self, lam=3.0, seeds=3):
        sc = self.repo.load_profile_scores()
        y = (sc["ENDED_BY"] == "BREAK").to_numpy(int)
        g = sc["INGOT_NO"].to_numpy()
        X = sc[FUSION_COLS].fillna(0).to_numpy(float)
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
        return sc, y, acc / seeds

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

    @staticmethod
    def _threshold_for_precision(scores, y, target=0.90):
        best = None
        for thr in np.linspace(0.05, 0.97, 60):
            p = scores >= thr
            tp = int((p & (y == 1)).sum())
            fp = int((p & (y == 0)).sum())
            fn = int((~p & (y == 1)).sum())
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            if prec >= target and (best is None or rec > best[1]):
                best = (float(thr), rec, prec)
        return best[0] if best else 0.5

    # ---------- 匯總 ----------

    def board(self):
        ts, ss = self._km_body()
        sc, y, fusion = self._fusion_scores()
        thr = self._threshold_for_precision(fusion, y)

        seg = self.repo.load_segments()
        body = seg[seg["PHASE"] == "BODY"].set_index(["INGOT_NO", "SEGMENT_SEQ"])

        rows = []
        for i, r in sc.reset_index(drop=True).iterrows():
            key = (r["INGOT_NO"], int(r["SEGMENT_SEQ"]))
            duration = float(body.loc[key, "DURATION_MIN"]) if key in body.index else None
            time_haz = self._hazard_at(ts, ss, duration) if duration is not None else None
            mon = float(fusion[i])
            broke = r["ENDED_BY"] == "BREAK"
            # 透明分級：監控高於高精確閾值 → 監控高風險；時間先驗按里程碑
            tier = "high" if mon >= thr else ("mid" if mon >= 0.5 else "low")
            rows.append(
                {
                    "ingotNo": r["INGOT_NO"],
                    "segmentSeq": int(r["SEGMENT_SEQ"]),
                    "durationMin": duration,
                    "timeHazard": time_haz,
                    "monitorRisk": mon,
                    "pc2": float(r["PC2"]) if "PC2" in r else None,
                    "ooc": int(r["OOC"]),
                    "endedBy": r["ENDED_BY"],
                    "broke": bool(broke),
                    "tier": tier,
                }
            )
        rows.sort(key=lambda d: d["monitorRisk"], reverse=True)

        # 誠實驗證：監控高風險層 vs 實際斷線
        high = [r for r in rows if r["tier"] == "high"]
        broke_total = sum(r["broke"] for r in rows)
        tp = sum(r["broke"] for r in high)
        return {
            "monitorThreshold": thr,
            "monitorAuc": _auc(fusion, y),
            "validation": {
                "highTierCount": len(high),
                "highTierPrecision": tp / max(len(high), 1),
                "recallOfBreaks": tp / max(broke_total, 1),
                "totalBreaks": int(broke_total),
                "totalSegments": len(rows),
            },
            "items": rows,
            "note": (
                "監控偵測為回溯性（段結束後才有 profile）；時間風險為生長時數先驗（可即時）。"
                "本頁為回溯性風險回顧，非即時預測。"
            ),
        }

    def ingot(self, ingot_no: str):
        b = self.board()
        items = [r for r in b["items"] if r["ingotNo"] == ingot_no]
        if not items:
            raise KeyError(ingot_no)
        items.sort(key=lambda d: d["segmentSeq"])
        return {"ingotNo": ingot_no, "segments": items, "hazardCurve": self.hazard_curve()}
