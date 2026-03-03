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

# --- 2. SISTEM DATABASE KATA LALUAN (Simulasi) ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 3. ANTARAMUKA LOG MASUK & RESET PASSWORD ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=120)
        
        if st.session_state.page == "reset":
            st.subheader("🔑 Set Semula Kata Laluan")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.session_state.db_password = new_p
                    st.session_state.page = "login"
                    st.success("✅ Berjaya! Sila log masuk semula.")
                    st.rerun()
                else:
                    st.error("❌ Kata laluan tidak padan.")
            if st.button("Kembali"):
                st.session_state.page = "login"
                st.rerun()
        else:
            st.title("Sistem Plotter Geomatik PUO")
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id == "admin" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        st.markdown("---")
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- 4. FUNGSI GEOMATIK (Cassini EPSG:4390 -> WGS84) ---
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_brg_dst(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", dist

# --- 5. SIDEBAR (KAWALAN ON/OFF) ---
st.success(f"👋 Selamat Datang, **Izzaan**!")
st.sidebar.header("⚙️ Kawalan Visual")

# Toggle Buttons
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_lbl = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
p_stn = st.sidebar.toggle("Papar Label Stesen", value=True)

st.sidebar.markdown("---")
s_font = st.sidebar.slider("Saiz Tulisan Label", 8, 20, 11)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER INTERAKTIF ---
st.title("📍 Plotter Interaktif Izzaan")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Penukaran Koordinat
        coords = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'], df['lat'] = [c[0] for c in coords], [c[1] for c in coords]
        
        # Cipta Peta (Default zoom tinggi & max zoom ditingkatkan)
        m = folium.Map(
            location=[df['lat'].mean(), df['lon'].mean()], 
            zoom_start=19, 
            max_zoom=22, 
            control_scale=True
        )

        # Logik ON/OFF Satelit
        if p_sat:
            google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
            folium.TileLayer(
                tiles=google_url, 
                attr='Google', 
                name='Google Satellite', 
                max_zoom=22, 
                max_native_zoom=20
            ).add_to(m)

        # Plot Poligon (Garis Cyan sentiasa ada)
        poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        folium.Polygon(locations=poly_pts, color="cyan", weight=3, fill=False).add_to(m)

        # Plot Label mengikut Toggle Sidebar
        for i in range(len(df)):
            p1 = df.iloc[i]
            p2 = df.iloc[(i+1)%len(df)]
            
            # Logik ON/OFF Label Stesen
            if p_stn:
                folium.map.Marker(
                    [p1['lat'], p1['lon']],
                    icon=folium.DivIcon(html=f"""<div style="font-family: Arial; color: yellow; font-weight: bold; 
                    font-size: {s_font}pt; text-shadow: 2px 2px 3px black; width: 40px;">{int(p1['STN'])}</div>""")
                ).add_to(m)
                folium.CircleMarker([p1['lat'], p1['lon']], radius=4, color='red', fill=True, fill_color='red').add_to(m)

            # Logik ON/OFF Bearing & Jarak
            if p_lbl:
                brg_txt, dst_val = kira_brg_dst([p1['E'], p1['N']], [p2['E'], p2['N']])
                mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
                folium.map.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f"""<div style="background: white; border: 1px solid red; 
                    padding: 2px; border-radius: 3px; font-size: {s_font-2}pt; color: red; font-weight: bold; 
                    text-align: center; width: 85px; border: 1px solid gray;">{brg_txt}<br>{dst_val:.2f}m</div>""")
                ).add_to(m)

        # Zoom automatik ke kawasan poligon
        m.fit_bounds(poly_pts)

        # Paparkan Peta
        folium_static(m, width=1100, height=600)

        # --- 7. EKSPORT DATA ---
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📊 Jadual Koordinat")
            st.dataframe(df[['STN', 'E', 'N']], use_container_width=True)
        with c2:
            st.subheader("📥 Muat Turun")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="data_izzaan.csv", mime='text/csv')
            
            # GeoJSON Export
            geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[ [r['lon'], r['lat']] for _, r in df.iterrows() ] + [[df.iloc[0]['lon'], df.iloc[0]['lat']]] ]}}]}
            st.download_button("Download GeoJSON (GIS)", data=json.dumps(geojson), file_name="plot_izzaan.geojson")

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO | Versi Interaktif Full Zoom")
