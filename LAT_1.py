import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
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

# --- 3. ANTARAMUKA LOG MASUK & RESET ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Papar logo jika ada dalam folder yang sama
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
                    st.error("❌ Kata laluan tidak padan atau kosong.")
            
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

# --- 4. DASHBOARD UTAMA ---
st.title("📍 Plotter Poligon Cassini (EPSG:4390)")
st.success(f"👋 Selamat Datang, **Izzaan**! Sistem sedia digunakan.")

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Kawalan Visual")
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_lbl = st.sidebar.toggle("Papar Jarak (m)", value=True)
p_stn = st.sidebar.toggle("Papar No. Stesen", value=True)
s_font = st.sidebar.slider("Saiz Tulisan", 5, 15, 8)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PEMPROSESAN DATA & PLOT ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        # Standarisasi nama kolum (buang ruang kosong & tukar ke besar)
        df.columns = [c.upper().strip() for c in df.columns]

        if 'E' in df.columns and 'N' in df.columns:
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Koordinat untuk lukisan (tutup poligon)
            e_vals = df['E'].tolist()
            n_vals = df['N'].tolist()
            plot_e = e_vals + [e_vals[0]]
            plot_n = n_vals + [n_vals[0]]
            
            # Lukis garisan sempadan
            ax.plot(plot_e, plot_n, color='cyan', linewidth=2, zorder=5)
            # Plot titik stesen
            ax.scatter(df['E'], df['N'], color='yellow', s=40, edgecolors='black', zorder=6)

            # Label Stesen & Kira Jarak
            for i in range(len(df)):
                # Label No Stesen
                if p_stn:
                    ax.text(df.iloc[i]['E'], df.iloc[i]['N'], f" {int(df.iloc[i]['STN'])}", 
                            color='white', fontsize=s_font+2, fontweight='bold', zorder=7)

                # Label Jarak
                if p_lbl:
                    p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
                    next_idx = (i + 1) % len(df)
                    p2 = (df.iloc[next_idx]['E'], df.iloc[next_idx]['N'])
                    
                    dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    mid_e, mid_n = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                    
                    ax.text(mid_e, mid_n, f"{dist:.2f}m", color='red', fontsize=s_font,
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1),
                            ha='center', zorder=8)

            # --- INTEGRASI PETA SATELIT ---
            if p_sat:
                try:
                    # Menggunakan EPSG:4390 (Cassini West Malaysia)
