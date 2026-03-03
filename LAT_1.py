import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM LOGIN (Simulasi) ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 3. ANTARAMUKA LOGIN ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.title("Sistem Plotter Geomatik PUO")
        u_id = st.text_input("ID Pengguna")
        u_pass = st.text_input("Kata Laluan", type="password")
        if st.button("🔓 Log Masuk", use_container_width=True):
            if u_id == "admin" and u_pass == st.session_state.db_password:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Salah!")
    st.stop()

# --- 4. FUNGSI GEOMATIK ---
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_data(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    return f"{int(brg)}°{int((brg-int(brg))*60)}'", dist

# --- 5. SIDEBAR & SETTING ---
st.sidebar.header("⚙️ Kawalan Visual")
s_font = st.sidebar.slider("Saiz Tulisan", 8, 20, 11)
if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER UTAMA ---
st.title("📍 Plotter Interaktif Google Satellite")
uploaded_file = st.file_uploader("📂 Muat naik CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Tukar koordinat
        coords = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'], df['lat'] = [c[0] for c in coords], [c[1] for c in coords]
        
        # --- FIX ZOOM: Set max_zoom=22 supaya boleh nampak sampai bawah ---
        m = folium.Map(
            location=[df['lat'].mean(), df['lon'].mean()], 
            zoom_start=19, 
            max_zoom=22, 
            control_scale=True
        )
        
        # Google Satellite Hybrid (lyrs=y) dengan max_zoom ditingkatkan
        google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
        folium.TileLayer(
            tiles=google_url, 
            attr='Google', 
            name='Google Satellite', 
            max_zoom=22, 
            max_native_zoom=20 # Google biasanya native sampai 20, tapi boleh "stretch" ke 22
        ).add_to(m)

        # Draw Traverse
        poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        folium.Polygon(locations=poly_pts, color="cyan", weight=3).add_to(m)

        # Labels
        for i in range(len(df)):
            p1, p2 = df.iloc[i], df.iloc[(i+1)%len(df)]
            brg, dst = kira_data([p1['E'], p1['N']], [p2['E'], p2['N']])
            
            # Marker No Stesen
            folium.map.Marker(
                [p1['lat'], p1['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{s_font}pt; color:yellow; font-weight:bold;">{int(p1["STN"])}</div>')
            ).add_to(m)
            
            # Label Bearing/Jarak
            folium.map.Marker(
                [(p1['lat']+p2['lat'])/2, (p1['lon']+p2['lon'])/2],
                icon=folium.DivIcon(html=f'<div style="background:white; border:1px solid red; padding:2px; font-size:{s_font-2}pt; color:red; font-weight:bold; width:80px; text-align:center;">{brg}<br>{dst:.2f}m</div>')
            ).add_to(m)

        m.fit_bounds(poly_pts)
        folium_static(m, width=1100, height=600)

        # --- 7. BUTTON EXPORT (Dah masukkan balik!) ---
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Data Koordinat")
            st.dataframe(df[['STN', 'E', 'N']])
        
        with col2:
            st.subheader("🚀 Eksport Hasil")
            # Export ke CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV Terkini", data=csv, file_name="export_geomatik_izzaan.csv", mime='text/csv')
            
            # Export ke GeoJSON (Untuk buka dalam QGIS/AutoCAD)
            geojson = {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[ [r['lon'], r['lat']] for _, r in df.iterrows() ] + [[df.iloc[0]['lon'], df.iloc[0]['lat']]] ]}}]
            }
            st.download_button("🌍 Download GeoJSON", data=json.dumps(geojson), file_name="plot_izzaan.geojson", mime='application/json')

st.caption("Izzaan Geomatik PUO - Fixed Zoom & Export")
