import logging
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from sklearn import (
    linear_model as lm,
    svm,
    tree,
    neighbors as nb,
    ensemble as ens,
    gaussian_process as gp,
    dummy,
)
from sklearn.compose import TransformedTargetRegressor
from sklearn.cross_decomposition import PLSRegression
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.isotonic import IsotonicRegression
from sklearn.kernel_ridge import KernelRidge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ----------------------------
# Helpers
# ----------------------------

def _scaled(reg):
    """Scale X; leave y as-is (used for GLMs that assume specific y distributions)."""
    return Pipeline([("scaler", StandardScaler()), ("reg", reg)])

def _scaled_ttr(reg):
    """Scale X and apply a log1p/expm1 transform to y (helps with large/heteroscedastic y)."""
    return TransformedTargetRegressor(
        regressor=Pipeline([("scaler", StandardScaler()), ("reg", reg)]),
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=False,
    )

def _safe_hgbr(**kwargs):
    """
    Create a HistGradientBoostingRegressor, using monotonic constraints if supported
    by the installed scikit-learn version.
    """
    try:
        return ens.HistGradientBoostingRegressor(**kwargs)
    except TypeError:
        # Older sklearn without monotonic_cst support: drop that arg and retry.
        kwargs.pop("monotonic_cst", None)
        return ens.HistGradientBoostingRegressor(**kwargs)


@dataclass
class ModelResult:
    name: str
    train_r2: float
    cv_r2_mean: float
    cv_r2_std: float
    cv_mae_mean: float


# ----------------------------
# Model zoo (tailored for your data)
# ----------------------------

def build_models(X: np.ndarray, y: np.ndarray) -> Dict[str, object]:
    """Return a dict of model_name -> estimator with safe, sensible defaults."""
    n = len(y)
    # y-constraints (you said y>0 and non-decreasing, but let's be defensive):
    y_ge_0 = np.all(y >= 0)
    y_gt_0 = np.all(y > 0)

    # Linear / penalized (scaled; bump max_iter where needed)
    linear_block = {
        "LinearRegression": _scaled(lm.LinearRegression()),
        "Ridge": _scaled(lm.Ridge()),
        "RidgeCV": _scaled(lm.RidgeCV(cv=min(5, n))),
        "Lasso": _scaled(lm.Lasso(max_iter=10000)),
        "LassoCV": _scaled(lm.LassoCV(cv=min(5, n), max_iter=10000)),
        "ElasticNet": _scaled(lm.ElasticNet(max_iter=10000)),
        "ElasticNetCV": _scaled(lm.ElasticNetCV(cv=min(5, n), max_iter=10000)),
        "Lars": _scaled(lm.Lars()),
        "LarsCV": _scaled(lm.LarsCV(cv=min(5, n))),
        "LassoLars": _scaled(lm.LassoLars()),
        "LassoLarsCV": _scaled(lm.LassoLarsCV(cv=min(5, n))),
        "LassoLarsIC": _scaled(lm.LassoLarsIC()),
        "OrthogonalMatchingPursuit": _scaled(lm.OrthogonalMatchingPursuit()),
        "BayesianRidge": _scaled(lm.BayesianRidge()),
        "ARDRegression": _scaled(lm.ARDRegression()),
        "HuberRegressor": _scaled(lm.HuberRegressor()),
        "TheilSenRegressor": _scaled(lm.TheilSenRegressor()),
        "RANSACRegressor": _scaled(lm.RANSACRegressor()),
        "SGDRegressor": _scaled(lm.SGDRegressor(max_iter=5000)),
        "PassiveAggressiveRegressor": _scaled(lm.PassiveAggressiveRegressor(max_iter=5000)),
    }

    # GLMs (scale X only; y left intact to respect distributional assumptions)
    glm_block = {}
    glm_block["QuantileRegressor"] = _scaled(lm.QuantileRegressor())  # median by default
    if y_ge_0:
        glm_block["PoissonRegressor"] = _scaled(lm.PoissonRegressor())
        # Tweedie with power>=1 needs y ≥ 0; default power=1.5
        glm_block["TweedieRegressor"] = _scaled(lm.TweedieRegressor())
    if y_gt_0:
        glm_block["GammaRegressor"] = _scaled(lm.GammaRegressor())

    # Kernel methods & SVMs (scale X and transform y)
    kernel_svm_block = {
        "KernelRidge_rbf": _scaled_ttr(KernelRidge(kernel="rbf")),
        "SVR_rbf": _scaled_ttr(svm.SVR(kernel="rbf", C=10.0, epsilon=0.1, gamma="scale")),
        "NuSVR_rbf": _scaled_ttr(svm.NuSVR(kernel="rbf", nu=0.5, C=10.0)),
        "LinearSVR": _scaled_ttr(svm.LinearSVR(C=1.0, epsilon=0.1)),
    }

    # Nearest neighbors (transforming y helps with large scale; KNN is stable)
    nn_block = {
        "KNeighborsRegressor": _scaled_ttr(nb.KNeighborsRegressor(n_neighbors=min(10, max(1, n // 10 or 1)))),
        # RadiusNeighborsRegressor is brittle without careful radius; omit by default.
    }

    # Trees / ensembles (no scaling needed; can enforce monotonicity on HGBR)
    tree_ens_block = {
        "DecisionTreeRegressor": tree.DecisionTreeRegressor(random_state=0),
        "ExtraTreeRegressor": tree.ExtraTreeRegressor(random_state=0),
        "RandomForestRegressor": ens.RandomForestRegressor(n_estimators=300, random_state=0, n_jobs=-1),
        "ExtraTreesRegressor": ens.ExtraTreesRegressor(n_estimators=300, random_state=0, n_jobs=-1),
        "AdaBoostRegressor": ens.AdaBoostRegressor(random_state=0),
        "GradientBoostingRegressor": ens.GradientBoostingRegressor(random_state=0),
        # Try Poisson loss if y≥0, else squared_error. Monotone increasing in X.
        "HistGradientBoostingRegressor_monotone": _safe_hgbr(
            loss="poisson" if y_ge_0 else "squared_error",
            monotonic_cst=[1],
            max_depth=None,
            max_iter=500,
            random_state=0,
        ),
        "BaggingRegressor": ens.BaggingRegressor(random_state=0, n_jobs=-1),
    }

    # Meta-ensembles
    voting = ens.VotingRegressor(
        estimators=[
            ("lr", lm.LinearRegression()),
            ("rf", ens.RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1)),
        ]
    )
    stacking = ens.StackingRegressor(
        estimators=[
            ("ridge", lm.Ridge()),
            ("rf", ens.RandomForestRegressor(n_estimators=200, random_state=0, n_jobs=-1)),
        ],
        final_estimator=lm.LinearRegression(),
        passthrough=False,
        cv=min(5, n),
        n_jobs=-1,
    )
    meta_block = {
        "VotingRegressor": voting,
        "StackingRegressor": stacking,
    }

    # Gaussian Process (scale X, transform y; add white noise; normalize)
    gp_block = {
        "GaussianProcessRegressor": _scaled_ttr(
            gp.GaussianProcessRegressor(
                kernel=RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0),
                normalize_y=True,
                random_state=0,
            )
        )
    }

    # Monotone 1D nonparametric
    mono_block = {
        "IsotonicRegression": IsotonicRegression(out_of_bounds="clip")
    }

    # Cross-decomposition (1 component for 1 feature)
    cross_block = {
        "PLSRegression": _scaled(PLSRegression(n_components=1))
    }

    # Neural net (scale + transform y; early stopping)
    nnets_block = {
        "MLPRegressor": _scaled_ttr(
            MLPRegressor(
                hidden_layer_sizes=(64, 64),
                max_iter=3000,
                early_stopping=True,
                random_state=0
            )
        )
    }

    # Baseline
    baseline_block = {
        "DummyRegressor": dummy.DummyRegressor(strategy="mean")
    }

    models = {}
    for block in (
        linear_block, glm_block, kernel_svm_block, nn_block, tree_ens_block,
        meta_block, gp_block, mono_block, cross_block, nnets_block, baseline_block
    ):
        models.update(block)

    return models


# ----------------------------
# Main API
# ----------------------------

def fit_and_report(dataset: np.ndarray, do_cv: bool = True, random_state: int = 0
                   ) -> Tuple[Dict[str, object], np.ndarray]:
    """
    Fit all models on a (n, 2) dataset with positive, non-decreasing target.
    Prints train R^2, CV R^2 (mean±std), and CV MAE for each successfully-fitted model.

    Returns:
        models: dict(name -> fitted estimator)
        results: structured numpy array with metrics for easy sorting/filtering
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    arr = np.array(dataset, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("dataset must be a 2D array of shape (n, 2)")

    # Sort by X just for readability (not strictly necessary)
    arr = arr[np.argsort(arr[:, 0])]
    X = arr[:, 0].reshape(-1, 1)
    y = arr[:, 1]
    n = len(y)

    print(f"X shape: {X.shape}, y shape: {y.shape}")

    models = build_models(X, y)

    # Cross-validation setup
    cv = KFold(n_splits=min(5, n), shuffle=True, random_state=random_state)

    results: list[ModelResult] = []

    for name, model in models.items():
        try:
            model.fit(X, y)
            train_r2 = float(getattr(model, "score")(X, y))

            if do_cv and n >= 3:
                cv_r2 = cross_val_score(model, X, y, scoring="r2", cv=cv, n_jobs=None)
                cv_mae = -cross_val_score(model, X, y, scoring="neg_mean_absolute_error", cv=cv, n_jobs=None)
                cv_r2_mean = float(np.mean(cv_r2))
                cv_r2_std = float(np.std(cv_r2))
                cv_mae_mean = float(np.mean(cv_mae))
            else:
                cv_r2_mean = np.nan
                cv_r2_std = np.nan
                cv_mae_mean = np.nan

            results.append(ModelResult(name, train_r2, cv_r2_mean, cv_r2_std, cv_mae_mean))

            print(f"{name:40s} | train R2: {train_r2: .4f}"
                  f" | cv R2: {cv_r2_mean: .4f} ± {cv_r2_std: .4f}"
                  f" | cv MAE: {cv_mae_mean: .4f}")

        except ValueError as e:
            logging.error(f"{name} not fitted: {e}")
        except Exception as e:
            logging.error(f"{name} unexpected error: {e}")

    # Pack results into a structured array for potential downstream sorting
    dtype = [
        ("name", "U50"),
        ("train_r2", "f8"),
        ("cv_r2_mean", "f8"),
        ("cv_r2_std", "f8"),
        ("cv_mae_mean", "f8"),
    ]
    results_array = np.array(
        [(r.name, r.train_r2, r.cv_r2_mean, r.cv_r2_std, r.cv_mae_mean) for r in results],
        dtype=dtype
    )

    # Nice summary: top models by CV R^2 (if available)
    if do_cv and len(results_array) > 0 and np.isfinite(results_array["cv_r2_mean"]).any():
        order = np.argsort(-np.nan_to_num(results_array["cv_r2_mean"], nan=-np.inf))
        print("\nTop by CV R^2:")
        for i in order[:10]:
            r = results_array[i]
            print(f"  {r['name']:40s}  CV R^2: {r['cv_r2_mean']:.4f} ± {r['cv_r2_std']:.4f}  "
                  f"(train R^2: {r['train_r2']:.4f})")

    return models, results_array


# ----------------------------
# Example usage
# ----------------------------
if __name__ == "__main__":
    # Example synthetic monotone dataset: y is increasing, positive, larger scale than x
    rng = np.random.RandomState(0)
    n = 200
    X_demo = np.linspace(0.1, 10.0, n)
    y_true = 3.0 * np.log1p(X_demo) ** 3 + 5.0  # positive, increasing, larger magnitude
    y_demo = y_true * (1.0 + 0.05 * rng.randn(n))   # small multiplicative noise, may create slight non-monotonicity
    y_demo = np.maximum(y_demo, 1e-6)               # keep strictly positive

    dataset_demo = np.column_stack([X_demo, y_demo])
    fit_and_report(dataset_demo, do_cv=True)
