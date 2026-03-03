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
        
        # PAPAR LOGO TEMPATAN (logo l.png)
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=150)
        else:
            st.warning("Fail 'logo l.png' tidak dijumpai dalam folder.")
            
        st.title("Sistem Plotter Geomatik PUO")
        user_id = st.text_input("ID Pengguna")
        password_input = st.text_input("Kata Laluan", type="password")
        
        if st.button("🔓 Log Masuk", use_container_width=True):
            if user_id == "admin" and password_input == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("ID atau Kata Laluan Salah!")
            
        if st.button("❓ Lupa Password", use_container_width=True):
            st.info("Hubungi: admin.geomatik@puo.edu.my")
    st.stop()

# --- 3. FUNGSI GEOMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"" , jarak, bearing

# --- 4. SIDEBAR (KAWALAN & EKSPORT) ---
st.sidebar.header("⚙️ Kawalan Visual")
papar_satelit = st.sidebar.toggle("Boleh on off satelit imej", value=True)
papar_brg_dist = st.sidebar.toggle("Boleh on off bering dan jarak", value=True)
papar_stn = st.sidebar.toggle("Boleh on off label stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Pelarasan Teks")
saiz_font = st.sidebar.slider("Saiz Tulisan", 5, 20, 10)
jarak_teks = st.sidebar.slider("Jarak Teks (Offset)", 0.5, 10.0, 3.0)
stn_offset = st.sidebar.slider("Jarak No Stesen", 1.0, 15.0, 5.0)

st.sidebar.markdown("---")
st.sidebar.header("📤 Eksport GIS")
# Ruangan eksport diletakkan di sini supaya mudah dicapai

# --- 5. PLOTTER ---
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

        fig, ax = plt.subplots(figsize=(10, 10))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()
        
        # Plot Garisan & Teks Center
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='yellow' if papar_satelit else 'black', linewidth=2, zorder=5)
            
            if papar_brg_dist:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                mag = np.sqrt(dx**2 + dy**2)
                nx, ny = -dy/mag, dx/mag # Vektor Normal
                
                if np.dot([nx, ny], [mid_x - cx_m, mid_y - cy_m]) < 0: nx, ny = -nx, -ny

                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                
                # Bearing & Jarak (Center simetri)
                ax.text(mid_x + nx*jarak_teks, mid_y + ny*jarak_teks, brg_str, color='cyan' if papar_satelit else 'red', fontsize=saiz_font, fontweight='bold', ha='center', va='center', rotation=txt_rot)
                ax.text(mid_x - nx*jarak_teks, mid_y - ny*jarak_teks, f"{dst_val:.3f}m", color='white' if papar_satelit else 'blue', fontsize=saiz_font, fontweight='bold', ha='center', va='center', rotation=txt_rot)

        if papar_stn:
            for _, row in df.iterrows():
                dx, dy = row['E']-cx_m, row['N']-cy_m
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E']+(dx/mag)*stn_offset, row['N']+(dy/mag)*stn_offset, str(int(row['STN'])), color='yellow' if papar_satelit else 'black', fontweight='bold', ha='center', va='center', fontsize=saiz_font+2)

        # FIX SATELITE (Menambah headers & Zoom stabil)
        if papar_satelit:
            try:
                # Menggunakan URL Google yang paling stabil
                source_url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                cx.add_basemap(ax, crs="EPSG:4390", source=source_url, zoom=18, alpha=1.0)
            except Exception as e:
                st.sidebar.error(f"Satelit Error: {e}")

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # --- EKSPORT & JADUAL ---
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist() + [df[['E', 'N']].values[0].tolist()]]}}
        
        # Letak butang eksport di Sidebar
        st.sidebar.download_button("🚀 Export to GIS (JSON)", data=json.dumps(geojson, indent=4), file_name="geomatik_puo.json", use_container_width=True)

        st.divider()
        st.subheader("📊 Jadual Stesen & Poligon")
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.dataframe(df, use_container_width=True)
        with col_t2:
            st.success(f"**Luas:** {kira_luas(df['E'].values, df['N'].values):.3f} m²")
            st.info("Peta Satelit bergantung kepada kelajuan internet dan koordinat Cassini yang betul.")
