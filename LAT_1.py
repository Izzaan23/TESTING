import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
import contextily as cx
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 2. SISTEM AKSES (ID & PASSWORD) ---
st.sidebar.header("🔒 Akses Sistem")

# Input untuk ID dan Password
user_id = st.sidebar.text_input("ID Pengguna", placeholder="Masukkan ID anda")
password_input = st.sidebar.text_input("Kata Laluan", type="password", placeholder="Masukkan Password")

# Logik Pengesahan
# Anda boleh tambah lebih banyak ID di sini jika mahu
if user_id == "admin" and password_input == "admin123":
    st.sidebar.success(f"Log Masuk Berjaya: {user_id.upper()} ✅")
else:
    if user_id == "" and password_input == "":
        st.warning("⚠️ Sila masukkan ID dan Password untuk mula.")
    else:
        st.error("❌ ID atau Password Salah!")
    
    # --- Butang Lupa Password ---
    st.sidebar.markdown("---")
    if st.sidebar.button("❓ Lupa Kata Laluan?"):
        st.sidebar.info("""
        **Bantuan Pemulihan:**
        Sila hubungi Admin Jabatan Geomatik PUO atau pensyarah anda untuk mendapatkan semula akses.
        
        📧 *admin.geomatik@puo.edu.my*
        """)
    st.stop() # Hentikan aplikasi jika belum login berjaya

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

# --- SIDEBAR TETAPAN PETA ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Peta")

pilihan_peta = st.sidebar.selectbox(
    "🗺️ Jenis Paparan Peta:",
    ["Tiada Peta", "OpenStreetMap (Jalan)", "Google Satellite", "Google Hybrid"]
)

# Definisi variable kawalan supaya tidak error (NameError)
on_off_satelit = pilihan_peta != "Tiada Peta"
papar_stn = st.sidebar.checkbox("Papar No. Stesen", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_luas_label = st.sidebar.checkbox("Papar Label Luas", value=False)

epsg_code = st.sidebar.text_input("Kod EPSG (Cth Cassini Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin Meter)", 0, 100, 5)

# --- HEADER UTAMA ---
col_logo, col_text = st.columns([1, 4])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=120)

with col_text:
    st.title("POLITEKNIK UNGKU OMAR")
    st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Poligon")

st.divider()

# --- MUAT NAIK FAIL ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Pastikan ada kolum STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    # Target Koordinat Stesen 1
    target_n, target_e = 6757.654, 115594.785

    if 'STN' in df.columns and 1 in df['STN'].values:
        idx_1 = df[df['STN'] == 1].index[0]
        shift_e = target_e - df.at[idx_1, 'E']
        shift_n = target_n - df.at[idx_1, 'N']
        df['E'] += shift_e
        df['N'] += shift_n
        st.success(f"📍 Stesen 1 dilaraskan ke: U={target_n}, B={target_e}")

    st.dataframe(df.set_index('STN'), use_container_width=True)

    if 'E' in df.columns and 'N' in df.columns:
        if 'tampilkan_luas' not in st.session_state:
            st.session_state.tampilkan_luas = False

        luas_semasa = kira_luas(df['E'].values, df['N'].values)
        
        # --- PLOTTING MATPLOTLIB ---
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Warna ikut mod peta
        warna_garisan = 'yellow' if on_off_satelit else 'black'
        warna_teks = 'cyan' if on_off_satelit else 'red'

        points = df[['E', 'N']].values
        n_points = len(points)
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])

        for i in range(n_points):
            p1, p2 = points[i], points[(i + 1) % n_points]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', linewidth=2, zorder=4)
            
            brg_str, dist, brg_val = kira_bearing_jarak(p1, p2)
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            if papar_brg_dist:
                rot = 90 - brg_val
                if rot < -90: rot += 180
                if rot > 90: rot -= 180
                ax.text(mid_x, mid_y, f"{brg_str}\n{dist:.3f}m", color=warna_teks, fontsize=8, rotation=rot, ha='center', fontweight='bold')

        if papar_stn:
            for _, row in df.iterrows():
                ax.text(row['E'], row['N'], f" {int(row['STN'])}", color='black', fontweight='bold', bbox=dict(facecolor='yellow', alpha=0.7))

        if st.session_state.tampilkan_luas or papar_luas_label:
            ax.fill(df['E'], df['N'], alpha=0.3, color='green', zorder=2)
            ax.text(cx_mean, cy_mean, f"LUAS\n{luas_semasa:.3f} m²", fontsize=12, color='darkgreen', fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.8))

        if on_off_satelit:
            try:
                # Pilih source berdasarkan pilihan_peta
                if "Satellite" in pilihan_peta:
                    source_img = cx.providers.Esri.WorldImagery
                else:
                    source_img = cx.providers.OpenStreetMap.Mapnik
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=source_img, zorder=0)
            except:
                st.error("Gagal muat peta latar. Sila semak Kod EPSG.")

        ax.set_aspect('equal')
        st.pyplot(fig)

        if st.button('📐 Kira & Papar Luas'):
            st.session_state.tampilkan_luas = True
            st.rerun()
