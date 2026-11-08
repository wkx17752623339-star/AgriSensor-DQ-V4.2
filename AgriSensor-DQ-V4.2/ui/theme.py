from pathlib import Path
from html import escape
import streamlit as st

ICONS={
'database':'<rect x="3" y="3" width="18" height="6" rx="3"/><path d="M3 6v6c0 1.7 4 3 9 3s9-1.3 9-3V6M3 12v6c0 1.7 4 3 9 3s9-1.3 9-3v-6"/>',
'activity':'<path d="M3 12h4l3-7 4 14 3-7h4"/>',
'flask':'<path d="M9 3h6M10 3v7l-6 9a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-6-9V3M7 16h10"/>',
'chart':'<path d="M4 19V5M4 19h17M7 15l4-5 4 3 5-7"/>',
'shield':'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
'leaf':'<path d="M20 4C9 4 4 9 4 16a4 4 0 0 0 4 4c7 0 12-5 12-16ZM4 20l12-12"/>',
'report':'<path d="M7 3h8l5 5v13H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3ZM15 3v6h5M9 14h7M9 18h7"/>',
}
def svg_icon(name):
    paths=ICONS.get(name,ICONS['leaf'])
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
def apply():
    css=(Path(__file__).resolve().parents[1]/'assets'/'style.css').read_text(encoding='utf-8')
    st.markdown(f'<style>{css}</style>',unsafe_allow_html=True)
def heading(title,subtitle):
    st.markdown(f'<div class="page-head"><div class="eyebrow">AGRISENSOR / RESEARCH WORKSPACE</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',unsafe_allow_html=True)
def feature_intro(icon,title,subtitle):
    st.markdown(f'<div class="feature-intro"><span class="feature-icon">{svg_icon(icon)}</span><div><div class="feature-title">{escape(title)}</div><div class="feature-desc">{escape(subtitle)}</div></div></div>',unsafe_allow_html=True)
