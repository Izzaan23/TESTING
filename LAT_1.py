import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. LOG MASUK TENGAH ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Pastikan fail logo l.png ada dalam folder yang sama
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=150)
        st.title("Sistem Plotter Geomatik PUO")
        user_id = st.text_input("ID Pengguna")
        password_input = st.text_input("Kata Laluan", type="password")
        if st.button("🔓 Log Masuk", use_container_width=True):
            if user_id == "admin" and password_input == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Salah!")
        if st.button("❓ Lupa Password", use_container_width=True):
            st.info("Hubungi: admin.geomatik@puo.edu.my")
    st.stop()

# --- 3. FUNGSI MATEMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 4. SIDEBAR ---
st.sidebar.header("⚙️ Tetapan Label")
papar_satelit = st.sidebar.checkbox("Papar Label Satelit", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_stn = st.sidebar.checkbox("Papar Label Stesen (STN)", value=True)

st.sidebar.markdown("---")
saiz_font = st.sidebar.slider("Saiz Tulisan Bearing/Jarak", 3, 15, 6)
stn_offset = st.sidebar.slider("Jarak No Stesen", 1.0, 10.0, 3.0)

# --- 5. PLOTTER UTAMA ---
st.title("📍 Plotter Poligon Interaktif")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Penyelarasan Stesen 1 (Cassini Perak)
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        # Cipta Plot
        fig, ax = plt.subplots(figsize=(10, 8))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()
        
        # Plot Garisan (Cyan seperti gambar anda)
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if papar_brg_dist:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                
                # Kotak Teks Putih (Bbox)
                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                
                ax.text(mid_x, mid_y, f"{brg_str}\n{dst_val:.2f}m", 
                        color='red', fontsize=saiz_font, fontweight='bold', 
                        ha='center', va='center', rotation=txt_rot, zorder=5,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

        # Plot Titik Merah pada Bucu (Untuk Info Klik)
        scatter = ax.scatter(df['E'], df['N'], color='red', s=40, edgecolors='white', zorder=10)

        # Label Nombor Stesen (Kuning)
        if papar_stn:
            for _, row in df.iterrows():
                dx, dy = row['E']-cx_m, row['N']-cy_m
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E']+(dx/mag)*stn_offset, row['N']+(dy/mag)*stn_offset, 
                        f"{row['STN']:.1f}", color='yellow', fontweight='bold', 
                        ha='center', fontsize=saiz_font+2,
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=0.5))

        # Tambah Peta Satelit (Guna Esri kerana lebih stabil daripada Google 404)
        if papar_satelit:
            try:
                # Esri World Imagery selalunya tidak menyekat akses
                cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except:
                st.sidebar.error("Gagal memuat peta satelit. Sila semak internet.")

        ax.set_aspect('equal')
        st.pyplot(fig)

        # --- 6. FUNGSI KLIK INFO (INTERAKTIF) ---
        st.markdown("### 🔍 Klik Info Bucu & Poligon")
        st.info("Pilih stesen di bawah untuk melihat koordinat terperinci:")
        
        # Menggunakan selectbox untuk simulasi 'klik' pada titik
        stesen_pilihan = st.selectbox("Pilih Stesen untuk Info Koordinat:", df['STN'].unique())
        data_stn = df[df['STN'] == stesen_pilihan].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Stesen", int(data_stn['STN']))
        c2.metric("East (E)", f"{data_stn['E']:.3f}")
        c3.metric("North (N)", f"{data_stn['N']:.3f}")

        # Label Luas di tengah poligon (seperti gambar 3)
        st.markdown(f"""
        <div style="text-align: center; border: 2px solid green; padding: 10px; border-radius: 10px; background-color: #f0fff0;">
            <h3 style="color: green; margin: 0;">LUAS</h3>
            <h2 style="color: black; margin: 0;">{kira_luas(df['E'].values, df['N'].values):.2f} m²</h2>
        </div>
        """, unsafe_allow_html=True)

        # Butang Eksport di Sidebar
        st.sidebar.markdown("---")
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
        st.sidebar.download_button("🚀 Export to GIS (JSON)", data=json.dumps(geojson), file_name="geomatik.json")
