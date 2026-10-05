from src.navigation import selected_category_from_chart_state


def test_reads_streamlit_vega_point_selection():
    state = {
        "selection": {
            "category_select": [
                {"categoria": "Transporte"},
            ]
        }
    }
    assert selected_category_from_chart_state(state) == "Transporte"


def test_reads_latest_point_when_multiple_are_present():
    state = {
        "selection": {
            "category_select": [
                {"categoria": "Mercado"},
                {"categoria": "Lazer"},
            ]
        }
    }
    assert selected_category_from_chart_state(state) == "Lazer"


def test_empty_chart_selection_returns_none():
    assert selected_category_from_chart_state(
        {"selection": {"category_select": []}}
    ) is None
