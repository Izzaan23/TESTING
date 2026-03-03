import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
import contextily as cx
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 1. SISTEM PASSWORD ---
st.sidebar.header("🔒 Akses Sistem")
password_input = st.sidebar.text_input("Masukkan Password", type="password")

if password_input != "admin":
    if password_input == "":
        st.warning("⚠️ Halaman dikunci. Sila masukkan password di sidebar.")
    else:
        st.error("❌ Password Salah!")
    st.stop() 

st.sidebar.success("Akses Dibenarkan ✅")

# --- FUNGSI-FUNGSI MATEMATIK ---
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de = p2[0] - p1[0]
    dn = p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- FUNGSI EKSPORT KE QGIS (DENGAN CRS) ---
def convert_to_geojson(df, luas, epsg):
    features = []
    coords = []
    for _, row in df.iterrows():
        coords.append([round(float(row['E']), 3), round(float(row['N']), 3)])
    coords.append([round(float(df.iloc[0]['E']), 3), round(float(df.iloc[0]['N']), 3)]) 
    
    poly_feature = {
        "type": "Feature",
        "properties": {"Layer": "Lot_Poligon", "Luas_m2": round(luas, 3)},
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    }
    features.append(poly_feature)

    for i, row in df.iterrows():
        p1 = [row['E'], row['N']]; p2 = [df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N']]
        brg, dist, _ = kira_bearing_jarak(p1, p2)
        point_feature = {
            "type": "Feature",
            "properties": {"STN": int(row['STN']), "Bearing": brg, "Jarak_m": round(dist, 3)},
            "geometry": {"type": "Point", "coordinates": [round(float(row['E']), 3), round(float(row['N']), 3)]}
        }
        features.append(point_feature)

    # Tambah maklumat CRS supaya QGIS tak pening
    geojson_data = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{epsg}"}
        },
        "features": features
    }
    return json.dumps(geojson_data, indent=4)

# --- SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Peta")

# Pilihan jenis peta
pilihan_peta = st.sidebar.selectbox(
    "🗺️ Jenis Paparan Peta:",
    ["Tiada Peta", "OpenStreetMap (Jalan)", "Google Satellite", "Google Hybrid (Satelit + Jalan)"]
)

epsg_code = st.sidebar.text_input("Kod EPSG (Cth Cassini Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin Meter)", 0, 100, 5)

# --- HEADER UTAMA ---
col_logo, col_text = st.columns([1, 4])
with col_logo:
    st.markdown('<div style="padding-top: 35px;"></div>', unsafe_allow_html=True)
    current_dir = os.path.dirname(__file__)
    logo_path = os.path.join(current_dir, "logo l.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)

with col_text:
    st.title("POLITEKNIK UNGKU OMAR")
    st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Poligon")

st.divider()

# --- MUAT NAIK FAIL ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Pastikan ada kolum STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Pastikan kolum sentiasa Huruf Besar untuk elak error
    df.columns = [c.upper() for c in df.columns]

    # --- LOGIK PELARASAN KOORDINAT MUTLAK ---
    # Target: U (N) = 6757.654, B (E) = 115594.785
    target_n = 6757.654
    target_e = 115594.785

    if 'STN' in df.columns and 1 in df['STN'].values:
        idx_1 = df[df['STN'] == 1].index[0]
        shift_e = target_e - df.at[idx_1, 'E']
        shift_n = target_n - df.at[idx_1, 'N']
        
        df['E'] = df['E'] + shift_e
        df['N'] = df['N'] + shift_n
        st.success(f"📍 Stesen 1 dilaraskan ke: U={target_n}, B={target_e}")
    else:
        st.error("❌ Ralat: Kolum 'STN' atau stesen nombor 1 tidak dijumpai dalam CSV.")

    st.dataframe(df.set_index('STN'), use_container_width=True)

    if 'E' in df.columns and 'N' in df.columns:
        if 'tampilkan_luas' not in st.session_state:
            st.session_state.tampilkan_luas = False

        luas_semasa = kira_luas(df['E'].values, df['N'].values)
        
        # --- SIDEBAR EKSPORT ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("🚀 Eksport ke QGIS")
        geojson_output = convert_to_geojson(df, luas_semasa, epsg_code)
        st.sidebar.download_button(label="🌍 MUAT TURUN FAIL QGIS", data=geojson_output, file_name="plot_puo.geojson", mime="application/json", type="primary")

        # --- PLOTTING MATPLOTLIB ---
        fig, ax = plt.subplots(figsize=(10, 10))
        # --- LOGIK BASEMAP (PETA LATAR) ---
        source_peta = None
        if pilihan_peta == "OpenStreetMap (Jalan)":
            source_peta = cx.providers.OpenStreetMap.Mapnik
        elif pilihan_peta == "Google Satellite":
            source_peta = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
        elif pilihan_peta == "Google Hybrid (Satelit + Jalan)":
            source_peta = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"

        # Tukar warna garisan ikut jenis peta supaya nampak jelas
        warna_garisan = 'yellow' if "Google" in pilihan_peta else 'black'
        warna_teks_brg = 'cyan' if "Google" in pilihan_peta else 'red'
        warna_teks_dist = 'white' if "Google" in pilihan_peta else 'blue'
        ax.grid(True, linestyle='--', alpha=0.6, color='gray', zorder=1)
        
        points = df[['E', 'N']].values
        n_points = len(points)
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])

        for i in range(n_points):
            p1, p2 = points[i], points[(i + 1) % n_points]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='yellow' if on_off_satelit else 'black', marker='o', linewidth=2, zorder=4)
            
            brg_str, dist, brg_val = kira_bearing_jarak(p1, p2)
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            if papar_brg_dist:
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                mag = np.sqrt(dx**2 + dy**2)
                nx, ny = -dy/mag, dx/mag 
                if ((mid_x + nx) - cx_mean)**2 + ((mid_y + ny) - cy_mean)**2 < (mid_x - cx_mean)**2 + (mid_y - cy_mean)**2:
                    nx, ny = -nx, -ny
                
                rot = 90 - brg_val
                if rot < -90: rot += 180
                if rot > 90: rot -= 180

                ax.text(mid_x + nx*0.7, mid_y + ny*0.7, brg_str, color='cyan' if on_off_satelit else 'red', fontsize=9, rotation=rot, ha='center', fontweight='bold')
                ax.text(mid_x + nx*1.4, mid_y + ny*1.4, f"{dist:.3f}m", color='white' if on_off_satelit else 'blue', fontsize=8, rotation=rot, ha='center', fontweight='bold')

        if papar_stn:
            for _, row in df.iterrows():
                dx_s = row['E'] - cx_mean
                dy_s = row['N'] - cy_mean
                dist_s = np.sqrt(dx_s**2 + dy_s**2)
                label_e = row['E'] + (dx_s / dist_s) * 1.5
                label_n = row['N'] + (dy_s / dist_s) * 1.5
                ax.text(label_e, label_n, f"{int(row['STN'])}", color='black', fontweight='bold', bbox=dict(facecolor='yellow', alpha=0.9, boxstyle='round'))

        if st.session_state.tampilkan_luas or papar_luas_label:
            ax.fill(df['E'], df['N'], alpha=0.2, color='green', zorder=2)
            ax.text(cx_mean, cy_mean, f"LUAS\n{luas_semasa:.3f} m²", fontsize=14, color='darkgreen', fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.7))

        if on_off_satelit:
            try:
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=cx.providers.Esri.WorldImagery, zorder=0)
            except:
                st.error("Gagal muat satelit. Sila pastikan Kod EPSG (cth: 4390) betul.")

        ax.set_aspect('equal')
        ax.set_xlim(df['E'].min() - margin_meter - 2, df['E'].max() + margin_meter + 2)
        ax.set_ylim(df['N'].min() - margin_meter - 2, df['N'].max() + margin_meter + 2)
        st.pyplot(fig)

        if st.button('📐 Kira & Papar Luas'):
            st.session_state.tampilkan_luas = True
            st.rerun()

