"""Local CSS: no external fonts, scripts, images, or network services."""
import streamlit as st

CSS = """
<style>
:root {--navy:#0B1220;--panel:#131F33;--edge:#263951;--mint:#7CDEC2;--muted:#A8B9CF;}
html, body, [class*="css"] {font-family:'Segoe UI',Inter,system-ui,sans-serif;}
.stApp {background:radial-gradient(ellipse at 85% 0%,#172742 0%,#0B1220 56%);color:#F4F8FF;}
[data-testid="stSidebar"] {background:#101A2B;border-right:1px solid #24344B;}
[data-testid="stSidebar"] .block-container {padding-top:1.8rem;}
.block-container {max-width:1440px;padding-top:2.2rem;padding-bottom:3rem;}
h1 {font-weight:720!important;letter-spacing:-1.4px!important;}
h2,h3 {letter-spacing:-.5px;}
.brand {font-size:21px;font-weight:750;letter-spacing:-.5px;margin:0 0 5px;}
.brand-mark {display:inline-block;background:linear-gradient(135deg,#48B8EA,#7CDEC2);color:#0B1220;
 padding:7px 11px;border-radius:10px;margin-right:9px;font-weight:900;}
.eyebrow {font-size:11px;letter-spacing:2px;color:#7CDEC2;text-transform:uppercase;font-weight:650;}
.muted {color:#A8B9CF;font-size:14px;line-height:1.65;}
.hero {border:1px solid #2B4262;border-radius:18px;padding:28px 32px;margin:4px 0 22px;
 background:linear-gradient(110deg,#152A43 0%,#15203A 65%,#202A4C 100%);position:relative;overflow:hidden;}
.hero h2 {font-size:34px;margin:8px 0 10px;line-height:1.18;}
.hero p {max-width:760px;margin:0;color:#B9C8DE;line-height:1.6;}
.pill {display:inline-block;padding:5px 11px;border:1px solid #395369;border-radius:20px;
 color:#7CDEC2;background:#132D33;font-size:12px;margin-right:8px;}
.pill-muted {color:#B9A7FF;background:#24223D;border-color:#44405F;}
[data-testid="stMetric"] {background:linear-gradient(140deg,#17253A,#131F33);border:1px solid #2A3D56;
 border-radius:14px;padding:19px 20px;box-shadow:0 8px 25px #00000015;}
[data-testid="stMetricValue"] {font-size:29px;font-weight:700;color:#F4F8FF;}
[data-testid="stMetricLabel"] {color:#A8B9CF;font-size:13px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px;}
.stButton>button {border-radius:9px;transition:background .15s ease,border-color .15s ease;font-weight:600;}
.stButton>button[kind="primary"] {background:#48B8EA;color:#081424;border-color:#48B8EA;}
.stButton>button[kind="primary"]:hover {background:#7CDEC2;border-color:#7CDEC2;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:5px;}
[data-testid="stSidebar"] [role="radiogroup"] label {border-radius:9px;padding:7px 10px;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#20324E;color:#7CDEC2;}
.flow {display:flex;gap:12px;flex-wrap:wrap;margin:20px 0;align-items:stretch;}
.flow-card {flex:1;min-width:140px;background:#15243A;border:1px solid #304762;border-radius:13px;padding:20px 16px;}
.flow-card strong {display:block;margin:10px 0;color:#F4F8FF;}
.flow-card small {color:#A8B9CF;line-height:1.5;}
.flow-number {font-family:Consolas,monospace;color:#7CDEC2;font-size:12px;}
.worker {border:1px solid #36547A;background:#172C47;border-radius:10px;padding:15px;margin:7px 0;}
.footer {font-size:11px;color:#8095AF;letter-spacing:.4px;margin-top:30px;}
@media(max-width:750px){.block-container{padding:1rem;} .hero{padding:22px;} .hero h2{font-size:27px;}}
</style>
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)
