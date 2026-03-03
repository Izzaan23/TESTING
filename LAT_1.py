import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import contextily as cx

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 2. SISTEM AKSES (ID & PASSWORD) ---
st.sidebar.header("🔒 Akses Sistem")
user_id = st.sidebar.text_input("ID Pengguna", placeholder="Masukkan ID anda")
password_input = st.sidebar.text_input("Kata Laluan", type="password", placeholder="Masukkan Password")

if user_id == "admin" and password_input == "admin123":
    st.sidebar.success(f"Log Masuk Berjaya: {user_id.upper()} ✅")
else:
    if user_id == "" and password_input == "":
        st.warning("⚠️ Sila masukkan ID dan Password.")
    else:
        st.error("❌ ID atau Password Salah!")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("❓ Lupa Kata Laluan?"):
        st.sidebar.info("Sila hubungi Admin Jabatan Geomatik PUO.\n📧 admin.geomatik@puo.edu.my")
    st.stop() 

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

# --- SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Paparan")

# Pilihan Peta (Kemas kini logik Google)
pilihan_peta = st.sidebar.selectbox(
    "🗺️ Peta Latar:", 
    ["Tiada Peta", "OpenStreetMap", "Esri World Imagery", "Google Satellite", "Google Hybrid"]
)
on_off_satelit = pilihan_peta != "Tiada Peta"

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz Tulisan")
saiz_stn = st.sidebar.slider("Saiz No. Stesen", 5, 25, 11)
saiz_bearing = st.sidebar.slider("Saiz Teks Bearing", 5, 15, 9)
saiz_jarak = st.sidebar.slider("Saiz Teks Jarak", 5, 15, 8)
jarak_offset_stn = st.sidebar.slider("Jarak No. Stesen dari Titik (m)", 0.5, 10.0, 3.0)

st.sidebar.markdown("---")
epsg_code = st.sidebar.text_input("Kod EPSG (Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin)", 0, 500, 50)

# --- HEADER UTAMA ---
st.title("POLITEKNIK UNGKU OMAR")
st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Poligon")
st.divider()

uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    target_n, target_e = 6757.654, 115594.785
    if 'STN' in df.columns and 1 in df['STN'].values:
        idx_1 = df[df['STN'] == 1].index[0]
        df['E'] += (target_e - df.at[idx_1, 'E'])
        df['N'] += (target_n - df.at[idx_1, 'N'])

    if 'E' in df.columns and 'N' in df.columns:
        luas_semasa = kira_luas(df['E'].values, df['N'].values)
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Warna ikut mod peta
        is_dark = "Satellite" in pilihan_peta or "Imagery" in pilihan_peta or "Hybrid" in pilihan_peta
        warna_garisan = 'yellow' if is_dark else 'black'
        warna_brg = 'cyan' if is_dark else 'darkred'
        warna_dist = 'white' if is_dark else 'blue'
        warna_stn = 'yellow' if is_dark else 'black'

        points = df[['E', 'N']].values
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])

        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', markersize=3, linewidth=1.5, zorder=5)
            brg_str, dist_val, brg_deg = kira_bearing_jarak(p1, p2)
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            txt_rot = 90 - brg_deg
            if txt_rot < -90: txt_rot += 180
            if txt_rot > 90: txt_rot -= 180
            
            ax.text(mid_x, mid_y, brg_str, color=warna_brg, fontsize=saiz_bearing, 
                    rotation=txt_rot, ha='center', va='bottom', fontweight='bold', rotation_mode='anchor')
            ax.text(mid_x, mid_y, f"{dist_val:.3f}m", color=warna_dist, fontsize=saiz_jarak, 
                    rotation=txt_rot, ha='center', va='top', fontweight='bold', rotation_mode='anchor')

        for _, row in df.iterrows():
            dx, dy = row['E'] - cx_mean, row['N'] - cy_mean
            mag = np.sqrt(dx**2 + dy**2)
            ax.text(row['E'] + (dx/mag)*jarak_offset_stn, row['N'] + (dy/mag)*jarak_offset_stn, 
                    str(int(row['STN'])), color=warna_stn, fontsize=saiz_stn, fontweight='bold', ha='center', va='center')

        # --- LOGIK PANGGIL GOOGLE SATELLITE ---
        if on_off_satelit:
            try:
                if pilihan_peta == "Google Satellite":
                    # Panggil URL Google Satellite secara manual
                    url_google = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                    cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=url_google, zoom='auto', zorder=0)
                elif pilihan_peta == "Google Hybrid":
                    url_hybrid = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                    cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=url_hybrid, zoom='auto', zorder=0)
                elif pilihan_peta == "Esri World Imagery":
                    cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=cx.providers.Esri.WorldImagery, zoom='auto', zorder=0)
                else:
                    cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=cx.providers.OpenStreetMap.Mapnik, zoom='auto', zorder=0)
            except Exception as e:
                st.sidebar.error(f"Gagal muat peta: {e}")

        ax.set_aspect('equal')
        ax.set_xlim(df['E'].min() - margin_meter, df['E'].max() + margin_meter)
        ax.set_ylim(df['N'].min() - margin_meter, df['N'].max() + margin_meter)
        ax.axis('off') 
        
        st.pyplot(fig)
        st.write(f"📐 **Luas Poligon:** {luas_semasa:.3f} meter persegi")
