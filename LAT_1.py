import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik - Izzaan", layout="wide")

# --- 2. SISTEM DATABASE KATA LALUAN ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 3. ANTARAMUKA LOG MASUK & RESET ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Sila pastikan fail logo l.png ada dalam folder yang sama
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
            st.button("Kembali", on_click=lambda: st.session_state.__setitem__('page', 'login'))

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

# --- 4. FUNGSI GEOMATIK (EPSG:4390 -> WGS84) ---
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Kawalan Paparan")
p_sat_label = st.sidebar.toggle("Papar Nama Jalan/Bangunan", value=True)
p_brg_dist = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
p_stn_label = st.sidebar.toggle("Papar No Stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz Tulisan")
s_stn = st.sidebar.slider("Saiz No Stesen", 8, 24, 14)
s_data = st.sidebar.slider("Saiz Bearing/Jarak", 8, 20, 10)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER UTAMA ---
st.title("📍 Plotter Poligon Cassini (EPSG:4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Penukaran Koordinat untuk Folium
        coords_wgs = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'] = [c[0] for c in coords_wgs]
        df['lat'] = [c[1] for c in coords_wgs]
        
        # Inisialisasi Peta Folium
        m = folium.Map(control_scale=True)

        # GOOGLE SATELLITE LAYER (Hybrid atau Satelit Sahaja)
        tile_lyr = 'y' if p_sat_label else 's'
        google_url = f'https://mt1.google.com/vt/lyrs={tile_lyr}&x={{x}}&y={{y}}&z={{z}}'
        folium.TileLayer(tiles=google_url, attr='Google', name='Google Satellite').add_to(m)

        # Plot Poligon (Garis Cyan)
        poly_points = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(locations=poly_points, color="cyan", weight=3, fill=False).add_to(m)

        # 1. Plot Bearing & Jarak (Center)
        if p_brg_dist:
            for i in range(len(df)):
                p1, p2 = df.iloc[i], df.iloc[(i+1)%len(df)]
                brg, dst = kira_bearing_jarak([p1['E'], p1['N']], [p2['E'], p2['N']])
                mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
                
                folium.map.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f"""<div style="font-family: Arial; color: black; background: white; 
                    padding: 3px; border-radius: 4px; font-size: {s_data}pt; font-weight: bold; border: 1px solid red;
                    text-align: center; width: 90px; pointer-events: none;">{brg}<br>{dst:.2f}m</div>""")
                ).add_to(m)

        # 2. Plot Bucu (Clickable) & No Stesen (Luar)
        centroid_lat, centroid_lon = df['lat'].mean(), df['lon'].mean()
        for _, row in df.iterrows():
            # Info bucu bila diklik
            pop_txt = f"<b>Stesen:</b> {int(row['STN'])}<br><b>E:</b> {row['E']:.3f}<br><b>N:</b> {row['N']:.3f}"
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6, color="red", fill=True, fill_color="red",
                popup=folium.Popup(pop_txt, max_width=200)
            ).add_to(m)

            # Label No Stesen (Offset automatik ke luar poligon)
            if p_stn_label:
                off_lat, off_lon = (row['lat'] - centroid_lat) * 0.2, (row['lon'] - centroid_lon) * 0.2
                folium.map.Marker(
                    [row['lat'] + off_lat, row['lon'] + off_lon],
                    icon=folium.DivIcon(html=f"""<div style="font-size: {s_stn}pt; color: yellow; font-weight: bold; 
                    text-shadow: 2px 2px 4px black; pointer-events: none; width: 30px;">{int(row['STN'])}</div>""")
                ).add_to(m)

        # AUTO ZOOM KE POLIGON
        m.fit_bounds(poly_points)

        # Paparkan Peta Interaktif
        folium_static(m, width=1000, height=600)

        # --- INFO PANEL ---
        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📊 Jadual Koordinat")
            st.dataframe(df[['STN', 'E', 'N']], use_container_width=True)
        with c2:
            st.subheader("👨‍🏫 Maklumat")
            st.write(f"Surveyor: **Izzaan**")
            # Kira Luas secara kasar
            x, y = df['E'].values, df['N'].values
            luas = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
            st.metric("Luas Keseluruhan", f"{luas:.2f} m²")
            
            geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['lon', 'lat']].values.tolist()]}}
            st.download_button("🚀 Eksport JSON", data=json.dumps(geojson), file_name="izzaan_geomatik.json")
