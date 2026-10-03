import pandas as pd

from src.insights import detect_anomalies, filter_expenses, monthly_insights


def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "valor": [100.0, 50.0, 80.0, 30.0],
        "categoria": ["Mercado", "Lazer", "Mercado", "Lazer"],
        "data": pd.to_datetime([
            "2026-10-01",
            "2026-10-10",
            "2026-09-15",
            "2026-09-20",
        ]),
        "descricao": ["compras", "cinema", "compras", "jogo"],
        "estabelecimento": [None, "Cinema", None, None],
    })


def test_monthly_total_and_previous_comparison():
    result = monthly_insights(sample_df(), 2026, 10)
    assert result["total"] == 150.0
    assert result["previous_total"] == 110.0
    assert result["top_category"] == "Mercado"


def test_filter_expenses_by_month_and_category():
    result = filter_expenses(sample_df(), 2026, 10, "Mercado")
    assert len(result) == 1
    assert result.iloc[0]["valor"] == 100.0
    assert result.iloc[0]["categoria"] == "Mercado"


def test_monthly_insights_respects_category_filter():
    result = monthly_insights(sample_df(), 2026, 10, "Lazer")
    assert result["total"] == 50.0
    assert result["previous_total"] == 30.0
    assert result["top_category"] == "Lazer"


def test_detects_high_outlier():
    df = pd.DataFrame({
        "valor": [20, 21, 19, 20, 200],
        "categoria": ["Alimentação"] * 5,
        "data": pd.to_datetime(["2026-10-01"] * 5),
    })
    result = detect_anomalies(df)
    assert len(result) == 1
    assert result.iloc[0]["valor"] == 200


def test_filter_expenses_returns_empty_for_period_without_records():
    result = filter_expenses(sample_df(), 2025, 1)
    assert result.empty


def test_detects_gasoline_outlier_using_historical_transport_expenses():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "valor": [60.0, 80.0, 100.0, 90.0, 1000.0],
        "categoria": ["Transporte"] * 5,
        "data": pd.to_datetime([
            "2026-08-10",
            "2026-09-05",
            "2026-09-20",
            "2026-10-01",
            "2026-10-03",
        ]),
        "descricao": ["gasolina"] * 5,
        "estabelecimento": [None] * 5,
    })

    anomalies = detect_anomalies(df)
    october_anomalies = filter_expenses(anomalies, 2026, 10, "Transporte")

    assert len(october_anomalies) == 1
    assert october_anomalies.iloc[0]["valor"] == 1000.0
