import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from folium.plugins import Fullscreen  
from pyproj import Transformer
import json
import os
import base64

# Fungsi untuk imej logo
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_base64_image("logo.png")
logo_html = f"data:image/png;base64,{img_base64}" if img_base64 else ""

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Visualisasi Poligon", layout="wide")

st.markdown("""
    <style>
    .stApp header { z-index: 100; }
    .sticky-header {
        position: sticky; top: 0; background-color: #0e1117; z-index: 99;
        padding: 10px 0; border-bottom: 1px solid #31333f; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. SISTEM KATA LALUAN (MENGGUNAKAN URL PARAMS) ---
if "pwd" in st.query_params:
    current_db_pass = st.query_params["pwd"]
else:
    current_db_pass = "admin123"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

# --- 3. ANTARAMUKA LOG MASUK ---
if not st.session_state.logged_in:
    st.markdown(f"""
        <div class="sticky-header">
            <div style="display: flex; align-items: center; gap: 20px; padding-left: 20px;">
                <img src="{logo_html}" width="150">
                <h1 style="color: white; margin: 0; font-size: 32px;">🏛️ SISTEM PENGURUSAN MAKLUMAT TANAH</h1>
            </div>
        </div>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([0.1, 4, 0.1]) 
    with col_mid:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.page == "reset":
            st.subheader("🔑 Set Semula Kata Laluan")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.query_params["pwd"] = new_p
                    st.session_state.page = "login"
                    st.success(f"✅ Berjaya! Kata laluan baru anda disimpan dalam URL. Sila log masuk.")
                    st.rerun()
            if st.button("Kembali"):
                st.session_state.page = "login"
                st.rerun()
        else:
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id in ["11", "12", "13"] and u_pass == current_db_pass:
                    st.session_state.logged_in = True
                    st.session_state.user_id = u_id 
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        st.markdown("---")
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- HEADER LOCKED ---
st.markdown(f"""
    <div class="sticky-header">
        <div style="display: flex; align-items: center; gap: 20px; padding-left: 20px;">
            <img src="{logo_html}" width="150">
            <h1 style="color: white; margin: 0; font-size: 32px;">📐 Visualisasi Poligon</h1>
        </div>
    </div>
""", unsafe_allow_html=True)

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
    if angle > 90: angle -= 180; flipped = True
    elif angle < -90: angle += 180; flipped = True
    return f"{d}°{m:02d}'{s:02.0f}\"", dist, angle, flipped

def kira_luas(df):
    x, y = df['E'].values, df['N'].values
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- 5. SIDEBAR (STRUKTUR AWAL) ---
names = {"11": "izzaan", "12": "adam muqhris", "13": "alif"}
user_display = names.get(st.session_state.user_id, "Pengguna")
st.sidebar.markdown(f"### hi, {user_display}! 👋") 

st.sidebar.title("🏠 Dashboard Tetapan")
p_point = st.sidebar.checkbox("Papar Point Stesen", value=True)
s_point = st.sidebar.slider("Saiz Point Stesen", 1, 15, 5)
p_stn = st.sidebar.checkbox("Papar Label No. Stesen (STN)", value=True)
s_stn = st.sidebar.slider("Saiz Tulisan Stesen", 5, 25, 12)
p_lbl = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
s_brg = st.sidebar.slider("Saiz Teks Brg/Jarak", 5, 20, 10)
p_luas = st.sidebar.checkbox("Papar Label Luas", value=True)
s_luas = st.sidebar.slider("Saiz Label Luas", 5, 30, 17)
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)

# --- 6. PLOTTER UTAMA ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        coords = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'], df['lat'] = [c[0] for c in coords], [c[1] for c in coords]
        
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, max_zoom=22)
        Fullscreen(position="topleft").add_to(m)

        if p_sat:
            google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
            folium.TileLayer(tiles=google_url, attr='Google', name='Google Satellite', max_zoom=22).add_to(m)

        luas_m2 = kira_luas(df)
        luas_ekar = luas_m2 / 4046.856
        perimeter = 0
        features_gis = []
        
        # 1. TAMBAH POLIGON KE GIS
        poly_coords = [[r['lon'], r['lat']] for _, r in df.iterrows()]
        poly_coords.append(poly_coords[0])
        features_gis.append({
            "type": "Feature",
            "properties": {
                "Nama": "Lot Tanah", 
                "Luas_m2": round(luas_m2, 3),
                "Luas_Ekar": round(luas_ekar, 4)
            },
            "geometry": {"type": "Polygon", "coordinates": [poly_coords]}
        })

        bil_garis = len(df)
        for i in range(bil_garis):
            p1_row, p2_row = df.iloc[i], df.iloc[(i+1)%bil_garis]
            brg_txt, dst_val, angle, flipped = kira_brg_dst([p1_row['E'], p1_row['N']], [p2_row['E'], p2_row['N']])
            perimeter += dst_val
            
            features_gis.append({
                "type": "Feature",
                "properties": {"Stesen": int(p1_row['STN']), "Easting": p1_row['E'], "Northing": p1_row['N']},
                "geometry": {"type": "Point", "coordinates": [p1_row['lon'], p1_row['lat']]}
            })

            features_gis.append({
                "type": "Feature",
                "properties": {"Dari_Stn": int(p1_row['STN']), "Ke_Stn": int(p2_row['STN']), "Bearing": brg_txt, "Jarak": round(dst_val, 3)},
                "geometry": {"type": "LineString", "coordinates": [[p1_row['lon'], p1_row['lat']], [p2_row['lon'], p2_row['lat']]]}
            })

        # --- PERUBAHAN DI SINI: Pindahkan butang eksport ke sidebar ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("💾 Eksport Data")
        geojson_final = {"type": "FeatureCollection", "features": features_gis}
        st.sidebar.download_button(
            label="🌍 Muat Turun GIS (.geojson)", 
            data=json.dumps(geojson_final), 
            file_name=f"{uploaded_file.name.split('.')[0]}.geojson", 
            mime="application/json", 
            use_container_width=True
        )

        poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        info_lot = f"<b>MAKLUMAT LOT:</b><br>Luas: {luas_m2:.2f} m²<br>Luas: {luas_ekar:.4f} Ekar<br>Perimeter: {perimeter:.2f} m"
        folium.Polygon(locations=poly_pts, color="cyan", weight=3, fill=True, fill_opacity=0.2, popup=folium.Popup(info_lot, max_width=250)).add_to(m)
        
        sw, ne = [df['lat'].min(), df['lon'].min()], [df['lat'].max(), df['lon'].max()]
        m.fit_bounds([sw, ne])

        if p_luas:
            folium.map.Marker([df['lat'].mean(), df['lon'].mean()], icon=folium.DivIcon(html=f'<div style="text-align: center; width: 200px; margin-left: -100px; pointer-events: none;"><b style="font-size: {s_luas}pt; color: white; text-shadow: 2px 2px 4px black;">LUAS: {luas_m2:.2f} m²</b></div>')).add_to(m)

        for i in range(len(df)):
            p1_row = df.iloc[i]
            info_stn = f"<b>STN: {int(p1_row['STN'])}</b><br>E: {p1_row['E']:.3f}<br>N: {p1_row['N']:.3f}"
            if p_point:
                folium.CircleMarker([p1_row['lat'], p1_row['lon']], radius=s_point, color='red', fill=True, popup=info_stn).add_to(m)
            if p_stn:
                folium.map.Marker([p1_row['lat'], p1_row['lon']], icon=folium.DivIcon(html=f"<div style='color: white; font-weight: bold; font-size: {s_stn}pt; text-shadow: 2px 2px 3px black; width: 40px;'>{int(p1_row['STN'])}</div>"), popup=info_stn).add_to(m)
            if p_lbl:
                p2_row = df.iloc[(i+1)%len(df)]
                brg_txt, dst_val, angle, flipped = kira_brg_dst([p1_row['E'], p1_row['N']], [p2_row['E'], p2_row['N']])
                mid_lat, mid_lon = (p1_row['lat'] + p2_row['lat'])/2, (p1_row['lon'] + p2_row['lon'])/2
                flex_dir = "column-reverse" if flipped else "column"
                folium.map.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=f'<div style="transform: rotate({-angle}deg); display: flex; flex-direction: {flex_dir}; align-items: center; width: 150px; margin-left: -75px; pointer-events: none;"><div style="font-size: {s_brg}pt; color: #FF0000; font-weight: bold; text-shadow: 0.5px 0.5px 1px black;">{brg_txt}</div><div style="font-size: {s_brg-1}pt; color: #0000FF; font-weight: bold; text-shadow: 0.5px 0.5px 1px black;">{dst_val:.2f}m</div></div>')).add_to(m)

        folium_static(m, width=1100, height=600)
        
        st.subheader("📊 Ringkasan Maklumat Lot")
        st.table(pd.DataFrame({"Perkara": ["Nama Fail", "Luas (m²)", "Luas (Ekar)", "Perimeter (m)"], "Maklumat": [uploaded_file.name, f"{luas_m2:.2f}", f"{luas_ekar:.4f}", f"{perimeter:.2f}"]}))
        
        st.subheader("📋 Jadual Koordinat Traverse")
        st.dataframe(df[['STN', 'E', 'N']], use_container_width=True, hide_index=True)

# Tambah butang log keluar di bawah sekali di sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Log Keluar", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO")
