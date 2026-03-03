import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
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

# --- 4. MESEJ SAMBUTAN ---
st.success(f"👋 Selamat Datang, **Izzaan**!")

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Kawalan Visual")
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_lbl = st.sidebar.toggle("Papar Bearing/Jarak", value=True)
p_stn = st.sidebar.toggle("Papar Label Stesen", value=True)
s_font = st.sidebar.slider("Saiz Tulisan", 4, 12, 7)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER ---
st.title("📍 Plotter Poligon Cassini (EPSG:4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot Poligon
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if p_lbl:
                dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                mid = [(p1[0]+p2[0])/2, (p1[1]+p2[1])/2]
                ax.text(mid[0], mid[1], f"{dist:.2f}m", color='red', fontsize=s_font, 
                        fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        ax.scatter(df['E'], df['N'], color='yellow', s=30, zorder=5)

        # --- BAHAGIAN YANG DIBETULKAN (INDENTATION) ---
        if p_sat:
            try:
                # Baris di bawah ini sekarang sudah masuk ke dalam (4 spaces)
                cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except Exception as e:
                st.warning(f"Peta satelit tidak dapat dipaparkan: {e}")

        ax.set_aspect('equal')
        st.pyplot(fig)
        
        with st.expander("📊 Jadual Data"):
            st.dataframe(df)

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO")
