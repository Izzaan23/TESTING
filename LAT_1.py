import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import json

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Interactive", layout="wide")

# --- 2. SISTEM AKSES ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.sidebar.header("🔒 Akses Sistem")
if not st.session_state.logged_in:
    user_id = st.sidebar.text_input("ID Pengguna")
    password_input = st.sidebar.text_input("Kata Laluan", type="password")
    if st.sidebar.button("Log Masuk"):
        if user_id == "admin" and password_input == "admin123":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("❌ Salah!")
    st.stop()

# --- 3. FUNGSI GEOMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    return f"{d}°{m:02d}'{s:02.0f}\""

# --- 4. SIDEBAR TETAPAN ---
st.sidebar.header("⚙️ Kawalan Paparan")
papar_satelit = st.sidebar.checkbox("Boleh on off satelit imej", value=True)
papar_brg = st.sidebar.checkbox("Boleh on off bering dan jarak", value=True)
papar_stn = st.sidebar.checkbox("Boleh on off label stesen", value=True)

st.sidebar.markdown("---")
# Butang Eksport GIS (GeoJSON)
st.sidebar.header("📤 Eksport Data")

# --- 5. PEMPROSESAN DATA ---
st.title("POLITEKNIK UNGKU OMAR")
st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Interaktif")

uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    # Pelarasan Cassini Perak (WGS84 Approximation untuk Folium)
    # Nota: Folium guna Lat/Lon. Di sini kita guna simulasi koordinat untuk demo.
    # Untuk hasil tepat, anda perlu library 'pyproj' untuk convert Cassini ke WGS84.
    
    if 'E' in df.columns and 'N' in df.columns:
        luas = kira_luas(df['E'].values, df['N'].values)
        
        # Simpan GeoJSON untuk butang eksport
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [df[['E', 'N']].values.tolist() + [df[['E', 'N']].values[0].tolist()]]
                    },
                    "properties": {"Luas_m2": luas, "Nama": "Lot Poligon"}
                }
            ]
        }
        
        st.sidebar.download_button(
            label="🚀 Eksport ke GIS (GeoJSON)",
            data=json.dumps(geojson_data),
            file_name="poligon_geomatik.geojson",
            mime="application/json"
        )

        # --- PETA INTERAKTIF (FOLIUM) ---
        # Kita guna titik tengah untuk center peta
        m = folium.Map(location=[4.6, 101.1], zoom_start=18) # Lokasi Ipoh/Perak

        # Tambah Google Satellite secara paksa (Direct Tile)
        if papar_satelit:
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Satellite',
                overlay=False,
                control=True
            ).add_to(m)

        # Tambah Poligon (Boleh klik untuk info)
        points = df[['N', 'E']].values.tolist() # Folium guna [Lat, Lon]
        # Nota: Koordinat Cassini anda perlu diconvert ke Lat/Lon untuk tepat di atas peta.
        # Jika anda cuma mahu lihat bentuk, kita guna koordinat asal:
        
        poly = folium.Polygon(
            locations=points,
            color="yellow",
            weight=3,
            fill=True,
            fill_opacity=0.2,
            popup=f"<b>INFO POLIGON</b><br>Luas: {luas:.3f} m²<br>Perimeter: Muncul di jadual bawah"
        ).add_to(m)

        # Tambah Penanda Stesen (Boleh klik untuk info stesen)
        if papar_stn:
            for _, row in df.iterrows():
                folium.CircleMarker(
                    location=[row['N'], row['E']],
                    radius=5,
                    color="red",
                    fill=True,
                    popup=f"<b>STESEN {int(row['STN'])}</b><br>E: {row['E']}<br>N: {row['N']}"
                ).add_to(m)

        # Paparkan Peta
        st_data = st_folium(m, width=1100, height=600)

        # --- INFO TABLE ---
        st.markdown("### 📊 Jadual Maklumat & Koordinat")
        st.table(df[['STN', 'E', 'N']])
        st.info(f"💡 **Tips:** Klik pada garisan kuning atau titik merah di atas peta untuk melihat info stesen dan poligon.")
