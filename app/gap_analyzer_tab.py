"""Compatibility wrapper for the gap-analysis Streamlit tab.

The page implementation now lives in ``app.pages.gap_analysis_page``.
Keep this module during migration so existing imports from ``app/ui.py`` and
older entrypoints continue to work.
"""

from app.pages.gap_analysis_page import (
    render_gap_analysis_page,
    render_gap_analyzer_tab,
    render_gap_analyzer_tab_v2,
)


__all__ = [
    "render_gap_analysis_page",
    "render_gap_analyzer_tab",
    "render_gap_analyzer_tab_v2",
]
