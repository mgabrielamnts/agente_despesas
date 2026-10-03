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




def filter_expenses_by_months(
    df: pd.DataFrame,
    year: int,
    months: list[int],
    category: str | None = None,
) -> pd.DataFrame:
    if df.empty or not months:
        return df.iloc[0:0].copy()
    filtered = df[
        (df["data"].dt.year == year)
        & (df["data"].dt.month.isin(months))
    ].copy()
    if category:
        filtered = filtered[filtered["categoria"] == category].copy()
    return filtered.sort_values(["data", "id"], ascending=[False, False])


def period_insights(
    df: pd.DataFrame,
    year: int,
    months: list[int],
    category: str | None = None,
) -> dict:
    current = filter_expenses_by_months(df, year, months, category)
    total = float(current["valor"].sum()) if not current.empty else 0.0
    by_category = (
        current.groupby("categoria")["valor"].sum().sort_values(ascending=False)
        if not current.empty else pd.Series(dtype=float)
    )
    return {
        "total": total,
        "top_category": by_category.index[0] if not by_category.empty else None,
        "by_category": by_category,
    }


def filter_expenses_by_year(
    df: pd.DataFrame,
    year: int,
    category: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filtered = df[df["data"].dt.year == year].copy()
    if category:
        filtered = filtered[filtered["categoria"] == category].copy()
    return filtered.sort_values(["data", "id"], ascending=[False, False])


def annual_insights(
    df: pd.DataFrame,
    year: int,
    category: str | None = None,
) -> dict:
    current = filter_expenses_by_year(df, year, category)
    previous = filter_expenses_by_year(df, year - 1, category)
    total = float(current["valor"].sum()) if not current.empty else 0.0
    previous_total = float(previous["valor"].sum()) if not previous.empty else 0.0
    by_category = (
        current.groupby("categoria")["valor"].sum().sort_values(ascending=False)
        if not current.empty else pd.Series(dtype=float)
    )
    by_month = (
        current.assign(mes=current["data"].dt.month)
        .groupby("mes")["valor"].sum()
        .reindex(range(1, 13), fill_value=0.0)
        if not current.empty else pd.Series(0.0, index=range(1, 13), dtype=float)
    )
    variation = (
        (total - previous_total) / previous_total * 100
        if previous_total > 0 else None
    )
    return {
        "total": total,
        "previous_total": previous_total,
        "variation_pct": variation,
        "top_category": by_category.index[0] if not by_category.empty else None,
        "by_category": by_category,
        "by_month": by_month,
    }


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
    """Detect high expenses against prior history from the same category.

    Each expense is compared only with earlier records, so the candidate
    expense does not inflate its own IQR threshold.
    """
    if df.empty:
        return pd.DataFrame()

    alerts = []
    for _, group in df.groupby("categoria"):
        sort_columns = ["data"] + (["id"] if "id" in group.columns else [])
        ordered = group.sort_values(sort_columns, kind="stable").reset_index(drop=True)

        for position in range(min_history, len(ordered)):
            history = ordered.iloc[:position]
            candidate = ordered.iloc[position]

            q1 = history["valor"].quantile(0.25)
            q3 = history["valor"].quantile(0.75)
            upper = q3 + 1.5 * (q3 - q1)

            if candidate["valor"] > upper:
                anomalous = candidate.to_frame().T.copy()
                anomalous["limite_anomalia"] = upper
                alerts.append(anomalous)

    if not alerts:
        return pd.DataFrame()

    result = pd.concat(alerts, ignore_index=True)
    result["valor"] = pd.to_numeric(result["valor"])
    result["limite_anomalia"] = pd.to_numeric(result["limite_anomalia"])
    result["data"] = pd.to_datetime(result["data"])
    return result
