import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.preprocessing import PolynomialFeatures, MinMaxScaler, SplineTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import (
    LinearRegression,
    Ridge,
    LassoCV,
    ElasticNetCV,
    HuberRegressor,
    BayesianRidge,
    SGDRegressor,
)
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ---------------------------
# Helpers
# ---------------------------

def monotone_cummax(y):
    """Return cumulative max along the first axis (expects 2D (n,1) or 1D)."""
    y = np.asarray(y)
    if y.ndim == 1:
        return np.maximum.accumulate(y)
    return np.maximum.accumulate(y, axis=0)


def safe_col(v):
    """Ensure 2D column shape (n,1)."""
    return np.asarray(v).reshape(-1, 1)


def enforce_monotone_from_last(y_last, y_future, mode="shift_cummax", eps=0.0):
    """
    Post-process y_future so that it's >= y_last and non-decreasing.
    Modes:
      - "cummax": concat [y_last, y_future] then cumulative max.
      - "shift_cummax" (default): shift the whole y_future up if the first value < y_last,
         then cumulative max. This avoids long flatlines when the model undershoots.
    Returns a 2D (n,1) array.
    """
    y_last = float(np.asarray(y_last).ravel()[-1])
    yf = safe_col(y_future)

    if mode == "cummax":
        z = np.vstack([[[y_last]], yf])
        return monotone_cummax(z)[1:]

    # shift_cummax
    shift = max(0.0, y_last - float(yf[0, 0]) + eps)
    yf_shifted = yf + shift
    z = np.vstack([[[y_last]], yf_shifted])
    return monotone_cummax(z)[1:]


def step_and_future_grid(x, horizon):
    step = np.median(np.diff(x.flatten()))
    x_future = np.arange(x[-1] + step, x[-1] + (horizon + 1) * step, step).reshape(-1, 1)
    return step, x_future


def evaluate(y_true, y_pred):
    # Make lengths equal and compute MAE/RMSE (sklearn version safe)
    n = min(len(y_true), len(y_pred))
    y_true = np.asarray(y_true).reshape(-1, 1)[:n]
    y_pred = np.asarray(y_pred).reshape(-1, 1)[:n]
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return mae, rmse


def _resolve_n_test(n, test_size):
    """Return #test points from float (fraction) or int."""
    if isinstance(test_size, float):
        n_test = max(1, int(np.ceil(n * test_size)))
    else:
        n_test = int(test_size)
    return max(1, min(n_test, n - 1))


def train_gap_test_split(X, y, test_size=0.2, gap_steps=0):
    """
    Deterministic split: [TRAIN] [GAP skipped] [TEST]
    - test_size: float in (0,1] (fraction) or int (#points)
    - gap_steps: int number of points to skip between train and test
    """
    X = np.asarray(X).reshape(-1, 1)
    y = np.asarray(y).reshape(-1, 1)
    n = len(X)
    n_test = _resolve_n_test(n, test_size)
    gap_steps = int(gap_steps)
    train_end = n - n_test - gap_steps  # exclusive

    if train_end < 1:
        raise ValueError(
            f"gap_steps + test_size too large: leaves train_len={train_end}. "
            f"Reduce gap_steps ({gap_steps}) or test_size ({test_size})."
        )

    X_train, y_train = X[:train_end], y[:train_end]
    X_gap, y_gap = X[train_end:n - n_test], y[train_end:n - n_test]  # skipped; y for plotting if desired
    X_test, y_test = X[n - n_test:], y[n - n_test:]

    meta = {"n_test": int(n_test), "gap_steps": int(gap_steps), "train_len": int(train_end)}
    return X_train, y_train, X_gap, y_gap, X_test, y_test, meta


def _jsonify_results(results):
    for k, v in results.items():
        v["mae"] = float(v["mae"]) if isinstance(v.get("mae"), (np.floating, float)) else v["mae"]
        v["rmse"] = float(v["rmse"]) if isinstance(v.get("rmse"), (np.floating, float)) else v["rmse"]
        for key in ("x_future", "y_future", "y_val_pred", "x_test", "y_test_pred"):
            if key in v:
                v[key] = np.asarray(v[key]).ravel().tolist()
        if "best_params" in v and hasattr(v["best_params"], "items"):
            v["best_params"] = dict(v["best_params"])  # ensure plain dict
    return results


# ---------------------------
# Main benchmarks
# ---------------------------

def run_benchmark(
    al,
    horizon=48,
    test_size=0.2,
    gap_steps=0,
    random_state=42,
    enforce_monotone=True,
    monotone_mode="shift_cummax",
    jsonify=False,
    verbose=True,
):
    """
    Compare extrapolating regressors + SVR + Trees (reference) on cumulative target.
    Uses a TRAIN / GAP / TEST split and evaluates on TEST only.
    """
    al = np.asarray(al)
    X = al[:, 0].reshape(-1, 1)
    y = al[:, 1].reshape(-1, 1)

    # Split
    X_train, y_train, X_gap, _, X_test, y_test, split_meta = train_gap_test_split(
        X, y, test_size=test_size, gap_steps=gap_steps
    )

    # Future grid
    _, x_future = step_and_future_grid(X, horizon)

    results = {}

    # ---------- Models that extrapolate ----------
    models = {
        "LinearRegression": LinearRegression(),
        "Poly2": Pipeline([("poly", PolynomialFeatures(2)), ("lin", LinearRegression())]),
        "Poly3": Pipeline([("poly", PolynomialFeatures(3)), ("lin", LinearRegression())]),
        "SplineRidge": Pipeline([
            ("spline", SplineTransformer(degree=3, n_knots=10, extrapolation="linear")),
            ("ridge", Ridge(alpha=1.0, random_state=random_state)),
        ]),
    }

    for name, model in models.items():
        model.fit(X_train, y_train.ravel())

        # --- TEST predictions ---
        y_test_pred = safe_col(model.predict(X_test))
        if enforce_monotone:
            y_test_pred = enforce_monotone_from_last(y_train[-1], y_test_pred, mode=monotone_mode)

        mae, rmse = evaluate(y_test, y_test_pred)

        # --- FUTURE forecasts ---
        y_future = safe_col(model.predict(x_future))
        if enforce_monotone:
            y_future = enforce_monotone_from_last(y[-1], y_future, mode=monotone_mode)

        results[name] = dict(
            mae=mae,
            rmse=rmse,
            x_test=X_test.flatten(),
            y_test_pred=y_test_pred.flatten(),
            x_future=x_future.flatten(),
            y_future=y_future.flatten(),
        )

    # ---------- SVR with scaling + light tuning ----------
    y_scaler = MinMaxScaler().fit(y_train)

    svr_pipe = Pipeline([
        ("scale_x", MinMaxScaler()),
        ("svr", SVR(kernel="rbf"))
    ])

    param_grid = {
        "svr__C": [10, 100, 300],
        "svr__gamma": ["scale", 0.1, 0.03],
        "svr__epsilon": [0.01, 0.1, 0.5],
    }
    tscv = TimeSeriesSplit(n_splits=5)
    gsvr = GridSearchCV(svr_pipe, param_grid, scoring="neg_mean_squared_error", cv=tscv)

    # fit on scaled y
    gsvr.fit(X_train, y_scaler.transform(y_train).ravel())

    y_test_pred = safe_col(gsvr.predict(X_test))
    y_test_pred = y_scaler.inverse_transform(y_test_pred)

    if enforce_monotone:
        y_test_pred = enforce_monotone_from_last(y_train[-1], y_test_pred, mode=monotone_mode)

    mae, rmse = evaluate(y_test, y_test_pred)

    y_future = safe_col(gsvr.predict(x_future))
    y_future = y_scaler.inverse_transform(y_future)
    if enforce_monotone:
        y_future = enforce_monotone_from_last(y[-1], y_future, mode=monotone_mode)

    results["SVR(RBF)+GS"] = dict(
        mae=mae,
        rmse=rmse,
        x_test=X_test.flatten(),
        y_test_pred=y_test_pred.flatten(),
        x_future=x_future.flatten(),
        y_future=y_future.flatten(),
        best_params=gsvr.best_params_,
    )

    # ---------- Trees (reference only; no true extrapolation) ----------
    x_scaler = MinMaxScaler().fit(X_train)
    for name, model in {
        "RandomForest": RandomForestRegressor(n_estimators=300, random_state=random_state),
        "GradientBoosting": GradientBoostingRegressor(random_state=random_state),
    }.items():
        Xt = x_scaler.transform(X_train)
        model.fit(Xt, y_train.ravel())

        Xte = x_scaler.transform(X_test)
        y_test_pred = safe_col(model.predict(Xte))
        if enforce_monotone:
            y_test_pred = enforce_monotone_from_last(y_train[-1], y_test_pred, mode=monotone_mode)
        mae, rmse = evaluate(y_test, y_test_pred)

        Xf = x_scaler.transform(x_future)
        y_future = safe_col(model.predict(Xf))
        if enforce_monotone:
            y_future = enforce_monotone_from_last(y[-1], y_future, mode=monotone_mode)

        results[name] = dict(
            mae=mae,
            rmse=rmse,
            x_test=X_test.flatten(),
            y_test_pred=y_test_pred.flatten(),
            x_future=x_future.flatten(),
            y_future=y_future.flatten(),
        )

    # ---------- pick a winner ----------
    win_name, win_res = min(results.items(), key=lambda kv: kv[1]["rmse"])  # type: ignore
    if verbose:
        print(
            f"Winner: {win_name} | RMSE={win_res['rmse']:.2f} | MAE={win_res['mae']:.2f} "
            f"| split: train={split_meta['train_len']} gap={split_meta['gap_steps']} test={split_meta['n_test']}"
        )

    if jsonify:
        results = _jsonify_results(results)
    return results, (win_name, win_res), split_meta


def run_benchmark_with_diffs(
    al,
    horizon=48,
    test_size=0.2,
    gap_steps=0,
    random_state=42,
    enforce_monotone=True,
    monotone_mode="shift_cummax",
    clip_negative_diffs=True,
    jsonify=False,
    verbose=True,
):
    """
    Same as run_benchmark, plus models trained on first-differences. Increments can be
    easier to model and reconstruct to cumulative by cumsum.
    TRAIN on diffs up to train end; predict diffs across GAP+TEST; reconstruct to cumulative; evaluate on TEST.
    - clip_negative_diffs: set predicted diffs < 0 to 0 to preserve cumulative nature.
    """
    al = np.asarray(al)
    X = al[:, 0].reshape(-1, 1)
    y = al[:, 1].reshape(-1, 1)

    # Base split
    X_train, y_train, X_gap, _, X_test, y_test, split_meta = train_gap_test_split(
        X, y, test_size=test_size, gap_steps=gap_steps
    )
    _, x_future = step_and_future_grid(X, horizon)

    # Run base models silently
    base_results, (_, _), _ = run_benchmark(
        al,
        horizon=horizon,
        test_size=test_size,
        gap_steps=gap_steps,
        random_state=random_state,
        enforce_monotone=enforce_monotone,
        monotone_mode=monotone_mode,
        jsonify=False,
        verbose=False,
    )
    results = dict(base_results)

    # ----- build diffs -----
    diffs = np.diff(y.flatten())                 # length n-1, aligned to X[1:]
    X_diff = X[1:]                               # X indices for diffs
    n = len(X)
    n_test = split_meta["n_test"]
    train_len = split_meta["train_len"]         # number of training points

    # Training diffs end at X index train_len-1 -> diff index train_len-2
    idx_train_end_diff = max(0, train_len - 1)
    Xd_train = X_diff[:idx_train_end_diff]
    yd_train = diffs[:idx_train_end_diff]

    # We need predictions for GAP+TEST diffs starting at X index train_len
    k0 = max(0, train_len - 1)                   # diff index for first point after train
    Xd_gap_test = X_diff[k0:]
    # Predicted diffs length should be gap_steps + n_test
    target_steps = split_meta["gap_steps"] + n_test

    diff_models = {
        "Diff_Linear": LinearRegression(),
        "Diff_Ridge": Ridge(alpha=1.0, random_state=random_state),
        "Diff_LassoCV": LassoCV(cv=5, random_state=random_state, max_iter=10000),
        "Diff_ElasticNetCV": ElasticNetCV(l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9], cv=5, random_state=random_state,
                                          max_iter=10000),
        "Diff_BayesianRidge": BayesianRidge(),
        "Diff_Huber": HuberRegressor(),
        "Diff_SGDR_Huber": SGDRegressor(loss="huber", epsilon=0.1, max_iter=5000, random_state=random_state),
        "Diff_Poly2": Pipeline([("poly", PolynomialFeatures(2)), ("lin", LinearRegression())]),
        "Diff_SplineRidge": Pipeline([
            ("spline", SplineTransformer(degree=3, n_knots=8, extrapolation="linear")),
            ("ridge", Ridge(alpha=1.0, random_state=random_state)),
        ]),
        "Diff_SVR": Pipeline([("scale_x", MinMaxScaler()), ("svr", SVR(C=100, epsilon=0.1, kernel="rbf"))]),
        "Diff_KNN": Pipeline([
            ("scale_x", MinMaxScaler()),
            ("knn", KNeighborsRegressor(n_neighbors=5, weights="distance"))
        ]),
        "Diff_KernelRidge": Pipeline([
            ("scale_x", MinMaxScaler()),
            ("krr", KernelRidge(alpha=1.0, kernel="rbf", gamma=0.05))
        ]),
        "Diff_ExtraTrees": ExtraTreesRegressor(n_estimators=500, random_state=random_state),
        "Diff_GB": GradientBoostingRegressor(random_state=random_state),
        "Diff_RF": RandomForestRegressor(n_estimators=300, random_state=random_state),
    }

    for name, model in diff_models.items():
        # Guard: need at least one training diff
        if len(Xd_train) < 1:
            continue

        model.fit(Xd_train, yd_train)
        yd_gap_test = model.predict(Xd_gap_test)

        # Keep only the exact number of steps we need (GAP+TEST)
        yd_gap_test = np.asarray(yd_gap_test).ravel()[:target_steps]
        if clip_negative_diffs:
            yd_gap_test = np.maximum(yd_gap_test, 0.0)

        # accumulate to cumulative
        y_fore_path = y_train[-1] + np.cumsum(yd_gap_test)  # length GAP+TEST
        # slice TEST portion
        start_test_in_path = split_meta["gap_steps"]
        y_test_pred = safe_col(y_fore_path[start_test_in_path: start_test_in_path + n_test])

        if enforce_monotone:
            y_test_pred = monotone_cummax(y_test_pred)

        mae, rmse = evaluate(y_test, y_test_pred)

        # Future forecast (continue diffs beyond dataset end)
        yd_future = model.predict(x_future)
        if clip_negative_diffs:
            yd_future = np.maximum(yd_future, 0.0)
        y_future = safe_col(y[-1] + np.cumsum(yd_future))
        if enforce_monotone:
            y_future = monotone_cummax(y_future)

        results[name] = dict(
            mae=mae,
            rmse=rmse,
            x_test=X_test.flatten(),
            y_test_pred=y_test_pred.flatten(),
            x_future=x_future.flatten(),
            y_future=y_future.flatten(),
        )

    # ---------- pick a winner ----------
    win_name, win_res = min(results.items(), key=lambda kv: kv[1]["rmse"])  # type: ignore
    if verbose:
        print(
            f"Winner (with diffs): {win_name} | RMSE={win_res['rmse']:.2f} | MAE={win_res['mae']:.2f} "
            f"| split: train={split_meta['train_len']} gap={split_meta['gap_steps']} test={split_meta['n_test']}"
        )

    if jsonify:
        results = _jsonify_results(results)
    return results, (win_name, win_res), split_meta


# ---------------------------
# Plotting
# ---------------------------

def plot_all_models(al, results, title="Forecasts vs CT (actual)", show_test=True, show_future=True,
                    figsize=(12, 7), legend_cols=2):
    """
    Plot CT with each model's TEST predictions (using train/gap/test split) and optional future forecasts.
    Expects each model entry to have x_test/y_test_pred and optionally x_future/y_future.
    """
    al = np.asarray(al)
    X = safe_col(al[:, 0]).ravel()
    y = safe_col(al[:, 1]).ravel()

    if not results:
        raise ValueError("results is empty")

    # Infer TEST region from any model
    any_key = next(iter(results))
    x_test_any = np.asarray(results[any_key].get("x_test", []))
    if x_test_any.size == 0:
        raise ValueError("results does not contain x_test/y_test_pred — run the new benchmark functions.")

    test_start_x = float(x_test_any[0])
    train_mask = X < test_start_x
    if not np.any(train_mask):
        raise ValueError("Could not infer training region from x_test.")
    X_train, y_train = X[train_mask], y[train_mask]
    X_test = X[~train_mask]
    y_test = y[~train_mask]

    # Gap region (if any)
    train_last_x = X_train[-1]
    gap_exists = test_start_x - train_last_x > (np.median(np.diff(X)) * 0.5)

    fig, ax = plt.subplots(figsize=figsize)

    # CT (actual)
    ax.plot(X, y, label="CT (actual)", linewidth=2)

    # Shade GAP
    if gap_exists:
        ax.axvspan(train_last_x, test_start_x, alpha=0.08, label="GAP (skipped)")

    # TEST predictions
    if show_test:
        for name, res in results.items():
            xt = np.asarray(res.get("x_test", []))
            yt = np.asarray(res.get("y_test_pred", []))
            if xt.size and yt.size:
                ax.plot(xt.ravel(), yt.ravel(), linestyle="--", alpha=0.8, label=f"{name} (test)")

    # Future forecasts (optional)
    if show_future:
        for name, res in results.items():
            xf = np.asarray(res.get("x_future", []))
            yf = np.asarray(res.get("y_future", []))
            if xf.size and yf.size:
                ax.plot(xf.ravel(), yf.ravel(), label=f"{name} (future)")

    # Split marker for train/test boundary
    ax.axvline(train_last_x, linewidth=1, linestyle=":", alpha=0.7)

    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y (cumulative)")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=legend_cols, fontsize=9)
    plt.tight_layout()
    plt.show()


# ---------------------------
# Example usage (commented)
# ---------------------------
# al = np.column_stack([np.arange(200), np.cumsum(np.random.exponential(scale=1.0, size=200))])
# results, (winner_name, winner_res), split_meta = run_benchmark(
#     al, test_size=0.2, gap_steps=24, horizon=48, monotone_mode="shift_cummax"
# )
# plot_all_models(al, results, title="CT with GAP-aware Test Evaluation")
#
# results2, (winner_name2, winner_res2), split_meta2 = run_benchmark_with_diffs(
#     al, test_size=0.2, gap_steps=24, horizon=48
# )
# plot_all_models(al, results2, title="CT with GAP-aware Test Evaluation (Diff Models)")
