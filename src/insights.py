import pandas as pd


def expenses_to_dataframe(expenses) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": e.id,
            "valor": float(e.amount),
            "categoria": e.category,
            "data": pd.Timestamp(e.expense_date),
            "descricao": e.description,
            "estabelecimento": e.establishment,
        }
        for e in expenses
    ])


def filter_expenses(
    df: pd.DataFrame,
    year: int,
    month: int,
    category: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    filtered = df[
        (df["data"].dt.year == year)
        & (df["data"].dt.month == month)
    ].copy()

    if category:
        filtered = filtered[filtered["categoria"] == category].copy()

    return filtered.sort_values(["data", "id"], ascending=[False, False])


def monthly_insights(
    df: pd.DataFrame,
    year: int,
    month: int,
    category: str | None = None,
) -> dict:
    empty_result = {
        "total": 0.0,
        "previous_total": 0.0,
        "variation_pct": None,
        "top_category": None,
        "by_category": pd.Series(dtype=float),
    }
    if df.empty:
        return empty_result

    current = filter_expenses(df, year, month, category)

    first = pd.Timestamp(year=year, month=month, day=1)
    prev_day = first - pd.Timedelta(days=1)
    previous = filter_expenses(df, prev_day.year, prev_day.month, category)

    total = float(current["valor"].sum())
    previous_total = float(previous["valor"].sum())
    variation = (
        (total - previous_total) / previous_total * 100
        if previous_total > 0
        else None
    )
    by_category = (
        current.groupby("categoria")["valor"]
        .sum()
        .sort_values(ascending=False)
    )

    return {
        "total": total,
        "previous_total": previous_total,
        "variation_pct": variation,
        "top_category": by_category.index[0] if not by_category.empty else None,
        "by_category": by_category,
    }


def detect_anomalies(df: pd.DataFrame, min_history: int = 4) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    alerts = []
    for _, group in df.groupby("categoria"):
        if len(group) < min_history:
            continue

        q1 = group["valor"].quantile(0.25)
        q3 = group["valor"].quantile(0.75)
        upper = q3 + 1.5 * (q3 - q1)

        anomalous = group[group["valor"] > upper].copy()
        if not anomalous.empty:
            anomalous["limite_anomalia"] = upper
            alerts.append(anomalous)

    return pd.concat(alerts, ignore_index=True) if alerts else pd.DataFrame()
