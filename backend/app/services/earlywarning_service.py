"""多變量前兆預警模型。

從 precursor_windows（133 特徵 × 145 視窗，case/control）訓練 L2 邏輯迴歸，
以「按晶棒分組」交叉驗證取 out-of-fold 機率，避免同晶棒洩漏。

重要且誠實的結論（資料本身決定，非模型不夠力）：本資料 n≈145、特徵高度冗餘，
多變量組合的 OOF AUC 約 0.75–0.76，並未超越單一最佳特徵（~0.77）。此服務因此
同時回傳單特徵基線，讓使用者看清「加特徵無益、前兆集中在少數標記」這件事，
並提供可調閾值的風險分數作為實用產出。
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from app.repositories.base import DataRepository

# 由 analysis/matched_break_pipeline.py 離線產生（重跑該腳本即可更新）
_LEAD_CURVE_ASSET = Path(__file__).resolve().parents[1] / "assets" / "matched_break_leadcurve.json"

ID_COLUMNS = {"INGOT_NO", "SEGMENT_SEQ", "DATABASE_NAME", "GROUP", "N", "WIN_END_POS"}
DEFAULT_LAMBDA = 100.0
LAMBDA_GRID = [1, 2, 5, 10, 20, 50, 100, 200, 500]


def _auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney U / (n_pos·n_neg)，含 tie 處理。"""
    pos = labels == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    r = rankdata(scores)
    return float((r[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _fit_logit(X: np.ndarray, y: np.ndarray, lam: float, iters: int = 100) -> np.ndarray:
    """L2 正則化邏輯迴歸，Newton-IRLS。X 已標準化、含截距由此處補上。"""
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    beta = np.zeros(p + 1)
    reg = np.eye(p + 1) * lam
    reg[0, 0] = 0.0  # 截距不罰
    for _ in range(iters):
        mu = 1.0 / (1.0 + np.exp(-np.clip(Xb @ beta, -30, 30)))
        w = np.clip(mu * (1 - mu), 1e-6, None)
        grad = Xb.T @ (mu - y) + reg @ beta
        hess = Xb.T @ (Xb * w[:, None]) + reg
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            break
        beta -= step
        if np.max(np.abs(step)) < 1e-7:
            break
    return beta


class EarlyWarningService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    # ---------- 資料 ----------

    def _prepare(self):
        w = self.repo.load_precursor_windows()
        features = [c for c in w.columns if c not in ID_COLUMNS and "::" in c]
        X = w[features].to_numpy(float)
        y = (w["GROUP"] == "case").to_numpy(int)
        groups = w["INGOT_NO"].to_numpy()
        meta = w[["INGOT_NO", "SEGMENT_SEQ", "GROUP"]].reset_index(drop=True)
        return X, y, groups, features, meta

    @staticmethod
    def _standardize(train, test):
        med = np.nanmedian(train, axis=0)
        tr = np.where(np.isnan(train), med, train)
        te = np.where(np.isnan(test), med, test)
        mu, sd = tr.mean(0), tr.std(0) + 1e-9
        return (tr - mu) / sd, (te - mu) / sd

    def _grouped_oof(self, X, y, groups, lam, k=5, seeds=3):
        """按晶棒分組 K-fold，多個 seed 平均 out-of-fold 機率以穩定結果。"""
        uniq = np.array(sorted(set(groups)))
        acc = np.zeros(len(y))
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            order = uniq.copy()
            rng.shuffle(order)
            pred = np.full(len(y), np.nan)
            for fold in np.array_split(order, k):
                te = np.isin(groups, fold)
                tr = ~te
                Xtr, Xte = self._standardize(X[tr], X[te])
                beta = _fit_logit(Xtr, y[tr], lam)
                eta = np.hstack([np.ones((int(te.sum()), 1)), Xte]) @ beta
                pred[te] = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
            acc += pred
        return acc / seeds

    # ---------- 對外 ----------

    def lead_curve(self):
        """配對世代 vs naive 的前置時間衰減（離線預算，見 analysis/ 管線）。"""
        if not _LEAD_CURVE_ASSET.exists():
            return {"available": False}
        data = json.loads(_LEAD_CURVE_ASSET.read_text())
        data["available"] = True
        return data

    def overview(self):
        X, y, groups, features, _ = self._prepare()
        signals = sorted({f.split("::")[0] for f in features})
        return {
            "nWindows": int(len(y)),
            "nCase": int(y.sum()),
            "nControl": int((y == 0).sum()),
            "nFeatures": len(features),
            "nIngots": int(len(set(groups))),
            "nSignals": len(signals),
            "defaultLambda": DEFAULT_LAMBDA,
        }

    def baseline(self, X, y, features):
        """單一最佳特徵的 OOF-free（全體）AUC，作為多變量要超越的門檻。"""
        best_i, best_disc = 0, -1
        for i in range(X.shape[1]):
            col = X[:, i]
            valid = ~np.isnan(col)
            a = _auc(col[valid], y[valid])
            disc = abs(a - 0.5)
            if disc > best_disc:
                best_disc, best_i, best_auc = disc, i, a
        return {
            "feature": features[best_i],
            "auc": max(best_auc, 1 - best_auc),
        }

    def model(self, lam: float = DEFAULT_LAMBDA, threshold: float | None = None):
        X, y, groups, features, meta = self._prepare()
        oof = self._grouped_oof(X, y, groups, lam)
        auc = _auc(oof, y)
        base = self.baseline(X, y, features)

        # 全資料擬合取係數（部署用模型 + 特徵貢獻顯示）
        Xs, _ = self._standardize(X, X)
        beta = _fit_logit(Xs, y, lam)
        coefs = beta[1:]
        top = np.argsort(-np.abs(coefs))[:15]
        contributions = [
            {
                "feature": features[i],
                "signal": features[i].split("::")[0],
                "coef": float(coefs[i]),
            }
            for i in top
        ]

        if threshold is None:
            threshold = self._best_threshold(oof, y)

        return {
            "lambda": lam,
            "oofAuc": auc,
            "baseline": base,
            "beatsSingleFeature": bool(auc > base["auc"]),
            "verdict": (
                "多變量未超越單特徵——前兆訊號集中在少數標記，加特徵反而引入雜訊。"
                if auc <= base["auc"] + 0.005
                else "多變量略優於單特徵。"
            ),
            "roc": self._roc(oof, y),
            "pr": self._pr(oof, y),
            "calibration": self._calibration(oof, y),
            "threshold": float(threshold),
            "operating": self._operating(oof, y, threshold),
            "contributions": contributions,
            "riskScores": self._risk_rows(meta, oof),
            "distribution": {
                "case": [round(float(p), 4) for p in oof[y == 1]],
                "control": [round(float(p), 4) for p in oof[y == 0]],
            },
        }

    def reg_path(self):
        """過擬合曲線：訓練 AUC vs OOF AUC 隨 λ 變化，展示 bias-variance。"""
        X, y, groups, features, _ = self._prepare()
        rows = []
        for lam in LAMBDA_GRID:
            oof = self._grouped_oof(X, y, groups, lam, seeds=2)
            Xs, _ = self._standardize(X, X)
            beta = _fit_logit(Xs, y, lam)
            train_pred = 1.0 / (
                1.0 + np.exp(-np.clip(np.hstack([np.ones((len(y), 1)), Xs]) @ beta, -30, 30))
            )
            rows.append(
                {
                    "lambda": lam,
                    "trainAuc": _auc(train_pred, y),
                    "oofAuc": _auc(oof, y),
                }
            )
        base = self.baseline(X, y, features)
        return {"baseline": base, "path": rows}

    # ---------- 指標 ----------

    @staticmethod
    def _roc(scores, y, max_points=100):
        order = np.argsort(-scores)
        yy = y[order]
        tps = np.cumsum(yy)
        fps = np.cumsum(1 - yy)
        n_pos, n_neg = max(int(yy.sum()), 1), max(int((1 - yy).sum()), 1)
        tpr = np.concatenate([[0], tps / n_pos])
        fpr = np.concatenate([[0], fps / n_neg])
        idx = np.unique(np.linspace(0, len(tpr) - 1, max_points).astype(int))
        return [{"fpr": float(fpr[i]), "tpr": float(tpr[i])} for i in idx]

    @staticmethod
    def _pr(scores, y, max_points=100):
        order = np.argsort(-scores)
        yy = y[order]
        tps = np.cumsum(yy)
        fps = np.cumsum(1 - yy)
        n_pos = max(int(yy.sum()), 1)
        precision = tps / np.maximum(tps + fps, 1)
        recall = tps / n_pos
        thr = scores[order]
        idx = np.unique(np.linspace(0, len(recall) - 1, max_points).astype(int))
        return [
            {"recall": float(recall[i]), "precision": float(precision[i]), "threshold": float(thr[i])}
            for i in idx
        ]

    @staticmethod
    def _calibration(scores, y, bins=8):
        edges = np.linspace(0, 1, bins + 1)
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (scores >= lo) & (scores < hi if hi < 1 else scores <= hi)
            if m.sum() == 0:
                continue
            out.append(
                {
                    "predicted": float(scores[m].mean()),
                    "observed": float(y[m].mean()),
                    "n": int(m.sum()),
                }
            )
        return out

    @staticmethod
    def _best_threshold(scores, y):
        """Youden's J 最大化的閾值。"""
        best_t, best_j = 0.5, -1
        for t in np.unique(scores):
            pred = scores >= t
            tp = int((pred & (y == 1)).sum())
            fn = int((~pred & (y == 1)).sum())
            fp = int((pred & (y == 0)).sum())
            tn = int((~pred & (y == 0)).sum())
            tpr = tp / max(tp + fn, 1)
            fpr = fp / max(fp + tn, 1)
            if tpr - fpr > best_j:
                best_j, best_t = tpr - fpr, float(t)
        return best_t

    @staticmethod
    def _operating(scores, y, t):
        pred = scores >= t
        tp = int((pred & (y == 1)).sum())
        fn = int((~pred & (y == 1)).sum())
        fp = int((pred & (y == 0)).sum())
        tn = int((~pred & (y == 0)).sum())
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        return {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": prec,
            "recall": rec,
            "f1": (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0,
        }

    @staticmethod
    def _risk_rows(meta: pd.DataFrame, oof: np.ndarray):
        df = meta.copy()
        df["risk"] = oof
        df = df.sort_values("risk", ascending=False)
        return [
            {
                "ingotNo": r.INGOT_NO,
                "segmentSeq": int(r.SEGMENT_SEQ),
                "group": r.GROUP,
                "risk": round(float(r.risk), 4),
            }
            for r in df.itertuples()
        ]
