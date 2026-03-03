import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik - Izzaan", layout="wide")

# --- 2. SISTEM DATABASE RINGKAS (Simulasi) ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_reset" not in st.session_state:
    st.session_state.show_reset = False

# --- 3. LOG MASUK & LUPA PASSWORD ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=120)
        
        # LOGIK TUKAR PASSWORD (FORGET PASSWORD)
        if st.session_state.show_reset:
            st.subheader("🔄 Set Semula Kata Laluan")
            new_pass = st.text_input("Masukkan Kata Laluan Baru", type="password")
            confirm_pass = st.text_input("Sahkan Kata Laluan Baru", type="password")
            if st.button("Simpan Password Baru"):
                if new_pass == confirm_pass and new_pass != "":
                    st.session_state.db_password = new_pass
                    st.session_state.show_reset = False
                    st.success("Password berjaya diubah! Sila log masuk.")
                    st.rerun()
                else:
                    st.error("Password tidak padan!")
            if st.button("Batal"):
                st.session_state.show_reset = False
                st.rerun()
        
        # LOGIK LOG MASUK BIASA
        else:
            st.title("Sistem Plotter Geomatik PUO")
            st.markdown("---")
            user_id = st.text_input("ID Pengguna")
            password_input = st.text_input("Kata Laluan", type="password")
            
            if st.button("🔓 Log Masuk", use_container_width=True):
                if user_id == "admin" and password_input == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Password salah!")
            
            if st.button("❓ Lupa Password? Klik di sini untuk ubah", use_container_width=True):
                st.session_state.show_reset = True
                st.rerun()
        
        st.markdown("<br><p style='text-align: center; color: gray;'>Website ini dibangunkan oleh: <b>Izzaan</b></p>", unsafe_allow_html=True)
    st.stop()

# --- 4. HALAMAN UTAMA (SURVEYOR INFO) ---
st.title("📍 Plotter Poligon Cassini Perak (4390)")
st.markdown(f"**Surveyor:** Izzaan | **System Provider:** Izzaan Geomatics Solutions")
st.divider()

# --- 5. FUNGSI GEOMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 6. SIDEBAR ---
st.sidebar.header("⚙️ Tetapan Visual")
papar_satelit = st.sidebar.checkbox("Papar Imej Satelit", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_stn = st.sidebar.checkbox("Papar Label Stesen", value=True)

saiz_font = st.sidebar.slider("Saiz Tulisan", 3, 15, 7)
stn_offset = st.sidebar.slider("Jarak No Stesen", 1.0, 10.0, 4.0)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 7. PLOTTER ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Pelarasan Cassini Perak
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        fig, ax = plt.subplots(figsize=(10, 8))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()
        
        # Plot Poligon
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2.5, zorder=3)
            
            if papar_brg_dist:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                ax.text(mid_x, mid_y, f"{brg_str}\n{dst_val:.2f}m", color='red', fontsize=saiz_font, 
                        fontweight='bold', ha='center', va='center', rotation=txt_rot, zorder=5,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

        # Titik Merah (Bucu)
        ax.scatter(df['E'], df['N'], color='red', s=50, edgecolors='white', zorder=10)

        # Label Stesen
        if papar_stn:
            for _, row in df.iterrows():
                dx, dy = row['E']-cx_m, row['N']-cy_m
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E']+(dx/mag)*stn_offset, row['N']+(dy/mag)*stn_offset, 
                        f"{int(row['STN'])}", color='yellow', fontweight='bold', 
                        ha='center', fontsize=saiz_font+2,
                        bbox=dict(facecolor='black', alpha=0.6, edgecolor='none', pad=0.5))

        # --- FUNGSI SATELIT (Kaedah XYZ Manual) ---
        if papar_satelit:
            try:
                # Menggunakan Tile Provider Esri (Paling Stabil untuk Python)
                cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=18)
            except:
                st.error("Imej satelit gagal dimuatkan. Sila semak sambungan internet.")

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # --- INFO STESEN (KLIK INFO) ---
        st.divider()
        stn_info = st.selectbox("Pilih Stesen untuk Info Koordinat:", df['STN'].unique())
        sel_row = df[df['STN'] == stn_info].iloc[0]
        st.success(f"📍 **Stesen {int(sel_row['STN'])}** | E: {sel_row['E']:.3f} | N: {sel_row['N']:.3f}")

        # Ringkasan Luas
        luas_m2 = kira_luas(df['E'].values, df['N'].values)
        st.markdown(f"""
            <div style="background-color:white; padding:15px; border-radius:10px; border: 2px solid green; text-align:center;">
                <h2 style="color:black; margin:0;">LUAS: {luas_m2:.2f} m²</h2>
                <p style="color:gray; margin:0;">Surveyor: Izzaan</p>
            </div>
        """, unsafe_allow_html=True)
