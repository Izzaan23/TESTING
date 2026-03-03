import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from folium.plugins import Fullscreen  
from pyproj import Transformer
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM DATABASE KATA LALUAN ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 3. ANTARAMUKA LOG MASUK ---
if not st.session_state.logged_in:
    # Guna columns yang lebih lebar untuk memuatkan logo besar dan tajuk panjang
    _, col_mid, _ = st.columns([0.1, 4, 0.1]) 
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- BAHAGIAN LOGO & TITLE SEJAJAR (VERSI BESAR) ---
        # Kita kecilkan nisbah column kiri (logo) supaya teks ada lebih ruang
        head_l, head_r = st.columns([1, 2.5]) 
        
        with head_l:
            if os.path.exists("logo l.png"):
                # Kita besarkan width ke 250 supaya sama macam gambar rujukan
                st.image("logo l.png", width=250) 
        
        with head_r:
            # Guna HTML untuk pastikan teks besar, bold, dan sejajar tengah (vertical align)
            st.markdown("""
                <div style='display: flex; align-items: center; height: 150px;'>
                    <h1 style='margin: 0; font-size: 45px; font-weight: 800; line-height: 1.2;'>
                        SISTEM PENGURUSAN <br> MAKLUMAT TANAH
                    </h1>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        
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
            if st.button("Kembali"):
                st.session_state.page = "login"
                st.rerun()
        else:
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id == "11" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        
        st.markdown("---")
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- 4. FUNGSI GEOMATIK ---
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_brg_dst(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
    
    flipped = False
    angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
    if angle > 90: 
        angle -= 180
        flipped = True
    elif angle < -90: 
        angle += 180
        flipped = True
    
    return f"{d}°{m:02d}'{s:02.0f}\"", dist, angle, flipped

def kira_luas(df):
    x = df['E'].values
    y = df['N'].values
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- 5. SIDEBAR (DASHBOARD TETAPAN) ---
st.sidebar.title("🏠 Dashboard Tetapan")
st.sidebar.markdown("---")

st.sidebar.subheader("🗺️ Tetapan Peta")
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_stn = st.sidebar.toggle("Papar Label No. Stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🏷️ Tetapan Label")
p_lbl = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
s_font = st.sidebar.slider("Saiz Tulisan Label", 8, 20, 11)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Log Keluar", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER UTAMA ---
st.title("📍 Plotter Interaktif Izzaan")

uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        coords = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'], df['lat'] = [c[0] for c in coords], [c[1] for c in coords]
        
        m = folium.Map(
            location=[df['lat'].mean(), df['lon'].mean()], 
            zoom_start=19, max_zoom=22, control_scale=True
        )
        
        Fullscreen(position="topleft", title="Skrin Penuh", title_cancel="Keluar").add_to(m)

        if p_sat:
            google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
            folium.TileLayer(tiles=google_url, attr='Google', name='Google Satellite', max_zoom=22, max_native_zoom=20).add_to(m)

        luas = kira_luas(df)
        info_lot = f"""<div style='width:150px'><b>Info Lot:</b><br>Luas: {luas:.2f} m²<br>Luas: {(luas/4046.86):.3f} Ekar</div>"""
        
        poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        folium.Polygon(
            locations=poly_pts, color="cyan", weight=3, fill=True, fill_opacity=0.2,
            popup=folium.Popup(info_lot, max_width=200)
        ).add_to(m)

        for i in range(len(df)):
            p1 = df.iloc[i]
            p2 = df.iloc[(i+1)%len(df)]
            
            if p_stn:
                folium.map.Marker(
                    [p1['lat'], p1['lon']],
                    icon=folium.DivIcon(html=f"<div style='font-family: Arial; color: yellow; font-weight: bold; font-size: {s_font}pt; text-shadow: 2px 2px 3px black; width: 40px;'>{int(p1['STN'])}</div>")
                ).add_to(m)
                folium.CircleMarker([p1['lat'], p1['lon']], radius=5, color='red', fill=True, fill_color='red').add_to(m)

            if p_lbl:
                brg_txt, dst_val, angle, flipped = kira_brg_dst([p1['E'], p1['N']], [p2['E'], p2['N']])
                mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
                flex_direction = "column-reverse" if flipped else "column"
                
                folium.map.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f"""
                        <div style="transform: rotate({-angle}deg); display: flex; flex-direction: {flex_direction}; align-items: center; justify-content: center; width: 120px; margin-left: -60px; pointer-events: none;">
                            <div style="font-size: {s_font-2}pt; color: white; font-weight: bold; text-shadow: 1px 1px 2px black; padding-bottom: 2px;">{brg_txt}</div>
                            <div style="font-size: {s_font-3}pt; color: #00FF00; font-weight: bold; text-shadow: 1px 1px 2px black; padding-top: 2px;">{dst_val:.2f}m</div>
                        </div>""")
                ).add_to(m)

        m.fit_bounds(poly_pts)
        folium_static(m, width=1100, height=600)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📊 Jadual Koordinat")
            st.dataframe(df[['STN', 'E', 'N']], use_container_width=True)
        with c2:
            st.subheader("📥 Muat Turun")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="data_izzaan.csv", mime='text/csv')

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO | Sidebar Dashboard Mode")

