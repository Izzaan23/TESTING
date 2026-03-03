# --- 2. SISTEM PASSWORD & ID ---
st.sidebar.header("🔒 Akses Sistem")

# Input untuk ID dan Password
user_id = st.sidebar.text_input("ID Pengguna", placeholder="Masukkan ID anda")
password_input = st.sidebar.text_input("Kata Laluan", type="password", placeholder="Masukkan Password")

# Logik Login
if user_id == "admin" and password_input == "admin123":
    st.sidebar.success(f"Selamat Datang, {user_id.upper()} ✅")
else:
    if user_id == "" and password_input == "":
        st.warning("⚠️ Sila log masuk di sidebar untuk mula.")
    else:
        st.error("❌ ID atau Password salah!")
    
    # --- Butang Lupa Password ---
    st.sidebar.markdown("---")
    if st.sidebar.button("❓ Lupa Kata Laluan?"):
        st.sidebar.info("""
        **Bantuan Pemulihan:**
        Sila hubungi Admin Jabatan Geomatik PUO atau pensyarah bertugas untuk set semula akses anda.
        
        📧 *admin.geomatik@puo.edu.my*
        """)
    
    st.stop() # Hentikan aplikasi jika belum login
