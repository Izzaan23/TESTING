import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import contextily as cx
from xyzservices import TileProvider

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 2. SISTEM AKSES ---
st.sidebar.header("🔒 Akses Sistem")
user_id = st.sidebar.text_input("ID Pengguna", placeholder="Masukkan ID anda")
password_input = st.sidebar.text_input("Kata Laluan", type="password", placeholder="Masukkan Password")

if user_id == "admin" and password_input == "admin123":
    st.sidebar.success(f"Log Masuk Berjaya: {user_id.upper()} ✅")
else:
    st.stop() 

# --- 3. FUNGSI MATEMATIK ---
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- 4. SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Paparan")
papar_satelit = st.sidebar.checkbox("Boleh on off satelit imej", value=True)
papar_brg_dist = st.sidebar.checkbox("Boleh on off bering dan jarak", value=True)
papar_stn_label = st.sidebar.checkbox("Boleh on off label stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz & Jarak Tulisan")
saiz_stn = st.sidebar.slider("Saiz No. Stesen", 5, 25, 12)
saiz_text = st.sidebar.slider("Saiz Bearing/Jarak", 5, 15, 9)
offset_teks = st.sidebar.slider("Jarak Teks dari Garisan (m)", 0.5, 10.0, 2.5)
offset_stn = st.sidebar.slider("Jarak No. Stesen (m)", 0.5, 15.0, 5.0)

epsg_code = st.sidebar.text_input("Kod EPSG (Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin)", 10, 1000, 200)

# --- 5. PEMPROSESAN DATA ---
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
        
        is_dark = papar_satelit
        warna_garisan = 'yellow' if is_dark else 'black'
        warna_brg = 'cyan' if is_dark else 'darkred'
        warna_dist = 'white' if is_dark else 'blue'
        warna_stn = 'yellow' if is_dark else 'black'

        points = df[['E', 'N']].values
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])
        total_peri = 0

        # Plot Garisan & Teks
        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', markersize=4, linewidth=2, zorder=5)
            
            brg_str, d_val, brg_deg = kira_bearing_jarak(p1, p2)
            total_peri += d_val
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            if papar_brg_dist:
                # Kira arah serenjang (perpendicular) untuk offset teks
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                L = np.sqrt(dx**2 + dy**2)
                nx, ny = -dy/L, dx/L # Vektor normal
                
                # Tentukan arah offset (keluar dari poligon)
                if np.dot([nx, ny], [mid_x - cx_mean, mid_y - cy_mean]) < 0:
                    nx, ny = -nx, -ny

                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                
                # Bearing (Luar) & Jarak (Dalam sedikit atau sebaliknya ikut offset)
                ax.text(mid_x + nx*offset_teks, mid_y + ny*offset_teks, brg_str, 
                        color=warna_brg, fontsize=saiz_text, rotation=txt_rot, ha='center', va='center', fontweight='bold')
                ax.text(mid_x - nx*offset_teks, mid_y - ny*offset_teks, f"{d_val:.3f}m", 
                        color=warna_dist, fontsize=saiz_text, rotation=txt_rot, ha='center', va='center', fontweight='bold')

        # No Stesen
        if papar_stn_label:
            for _, row in df.iterrows():
                dx, dy = row['E'] - cx_mean, row['N'] - cy_mean
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E'] + (dx/mag)*offset_stn, row['N'] + (dy/mag)*offset_stn, 
                        str(int(row['STN'])), color=warna_stn, fontsize=saiz_stn, fontweight='bold', ha='center')

        # --- FIX GOOGLE SATELITE ---
        if papar_satelit:
            try:
                # Guna TileProvider manual untuk bypass isu headers
                google_sat = TileProvider(
                    name="GoogleSatellite",
                    url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                    attribution="Google",
                )
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=google_sat, zoom=18, zorder=0)
            except:
                st.sidebar.warning("Satelit gagal. Cuba besarkan Margin.")

        ax.set_aspect('equal')
        ax.set_xlim(df['E'].min() - margin_meter, df['E'].max() + margin_meter)
        ax.set_ylim(df['N'].min() - margin_meter, df['N'].max() + margin_meter)
        ax.axis('off')
        st.pyplot(fig)

        # --- JADUAL & INFO (DI BAWAH) ---
        st.markdown("### 📊 Jadual Data & Maklumat Poligon")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("**Koordinat Stesen (Terlaras):**")
            st.table(df[['STN', 'E', 'N']]) # Guna st.table supaya nampak semua data terus
            
        with col2:
            st.write("**Ringkasan Poligon:**")
            info_box = f"""
            - **Luas:** {luas_semasa:.3f} m²
            - **Perimeter:** {total_peri:.3f} m
            - **Negeri:** Perak (EPSG:{epsg_code})
            - **Status:** Stesen 1 dilaraskan ✅
            """
            st.info(info_box)
