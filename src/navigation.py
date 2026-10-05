def selected_category_from_chart_state(chart_state) -> str | None:
    """Extract a category from Streamlit's Vega-Lite selection state.

    Streamlit normalizes point selections to a list of selected records,
    e.g. [{"categoria": "Transporte"}].
    """
    if not chart_state:
        return None

    selection = chart_state.get("selection", {}).get("category_select", [])

    if isinstance(selection, list):
        for point in reversed(selection):
            if isinstance(point, dict):
                category = point.get("categoria")
                if isinstance(category, str) and category:
                    return category
        return None

    # Defensive fallback for older/unexpected selection shapes.
    if isinstance(selection, dict):
        category = selection.get("categoria")
        if isinstance(category, str) and category:
            return category
        if isinstance(category, list) and category:
            last = category[-1]
            return last if isinstance(last, str) and last else None

    return None
