import streamlit as st
import yfinance as yf

# Konfigurasi halaman
st.set_page_config(page_title="Kalkulator Valuasi Institusional", layout="centered")

st.title("📊 Mesin Audit Manual (EPV vs ARV)")
st.write("Sistem ekstraksi data otomatis dengan opsi intervensi manual untuk akurasi absolut.")

# Kolom Input
ticker_input = st.text_input("Masukkan Ticker Saham (Contoh: META, BBCA.JK):", "").upper()

if ticker_input:
    with st.spinner(f"Menarik draf laporan keuangan untuk {ticker_input}..."):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                st.error("⚠️ Emiten tidak ditemukan atau data ditarik dalam keadaan kosong.")
            else:
                # 1. Ekstraksi Data Kasar (Raw Data) dengan proteksi tipe data
                current_price = float(info.get('currentPrice', info.get('previousClose', 0)) or 0)
                shares_raw = float(info.get('sharesOutstanding', 0) or 0)
                fcf_raw = float(info.get('freeCashflow', 0) or 0)
                eps_raw = float(info.get('trailingEps', 0) or 0)

                bs = stock.balance_sheet
                equity_raw = 0.0
                if bs is not None and not bs.empty:
                    for key in ['Stockholders Equity', 'Total Stockholder Equity', 'Common Stock Equity']:
                        if key in bs.index:
                            equity_raw = float(bs.loc[key].iloc[0])
                            break

                inc = stock.financials
                sga_raw = 0.0
                rd_raw = 0.0
                if inc is not None and not inc.empty:
                    if 'Selling General And Administration' in inc.index:
                        sga_raw = float(inc.loc['Selling General And Administration'].dropna().head(3).sum())
                    if 'Research And Development' in inc.index:
                        rd_raw = float(inc.loc['Research And Development'].dropna().head(5).sum())

                # 2. Sistem Peringatan Dini (Deteksi Eror/Kosong)
                st.markdown("---")
                if fcf_raw <= 0:
                    st.warning("⚠️ **PERINGATAN KRITIS:** Yahoo Finance gagal menemukan data Arus Kas Bebas (FCF) yang positif. Jika Anda tidak mengisinya secara manual di bawah, mesin akan terpaksa menggunakan EPS biasa sebagai cadangan.")
                if rd_raw == 0 and sga_raw == 0:
                    st.info("ℹ️ **INFO:** Beban R&D dan SG&A terdeteksi 0. Ini wajar untuk sektor komoditas/perbankan. Namun, jika ini adalah perusahaan konsumen/teknologi, silakan koreksi manual angkanya dari laporan laba rugi resmi.")

                # 3. Formulir Intervensi Manual (Pre-filled dengan data Yahoo Finance)
                st.markdown("### 📝 Ruang Koreksi Data Manual")
                st.write("Silakan timpa angka-angka di bawah ini menggunakan data dari Laporan Keuangan resmi jika menurut Anda hasil tarikan mesin kurang akurat.")
                
                with st.form("manual_override_form"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        fcf_input = st.number_input("Total Free Cash Flow (FCF)", value=fcf_raw, step=1000.0)
                        eps_input = st.number_input("EPS Trailing (Cadangan FCF)", value=eps_raw, step=10.0)
                        shares_input = st.number_input("Jumlah Saham Beredar", value=shares_raw, step=1000.0)
                    with col_b:
                        equity_input = st.number_input("Total Ekuitas (Nilai Buku)", value=equity_raw, step=1000.0)
                        rd_input = st.number_input("Total R&D (5 Tahun)", value=rd_raw, step=1000.0)
                        sga_input = st.number_input("Total SG&A (3 Tahun)", value=sga_raw, step=1000.0)
                    
                    # Tombol Eksekusi
                    submit_btn = st.form_submit_button("Jalankan Diagnosis Valuasi Final")

                # 4. Kalkulasi Final Berdasarkan Data Inputan Manual
                if submit_btn:
                    if shares_input <= 0:
                        st.error("❌ Eror Fatal: Jumlah saham beredar tidak boleh 0.")
                    else:
                        # Logika Penentuan Basis Laba
                        if fcf_input > 0:
                            eps_fcf = fcf_input / shares_input
                            basis_laba = "FCF per Share (Sangat Akurat)"
                        else:
                            eps_fcf = eps_input
                            basis_laba = "EPS Trailing (Rentang Eror Akuntansi)"
                        
                        # Rumus Triangulasi EPV & ARV
                        epv = eps_fcf * 15
                        arv_total = equity_input + rd_input + sga_input
                        arv_per_share = arv_total / shares_input
                        franchise_value = epv - arv_per_share
                        
                        # Keputusan Harga Wajar & Moat
                        if franchise_value > 0:
                            status_moat = "🔥 TERDETEKSI MOAT: Laba dilindungi nilai waralaba aset tak berwujud."
                            harga_wajar = epv
                        else:
                            status_moat = "⚠️ VALUE TRAP: Laba didorong padat modal, tidak memiliki kekuatan harga."
                            harga_wajar = min(epv, arv_per_share)
                        
                        zona_beli = harga_wajar * 0.80

                        # 5. Tampilan Kesimpulan di HP
                        st.markdown("---")
                        st.markdown("### 🎯 Kesimpulan Diagnosis")
                        
                        res1, res2 = st.columns(2)
                        res1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                        res2.metric("Harga Wajar (Fair Value)", f"{harga_wajar:,.2f}")
                        
                        st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli:,.2f}")
                        
                        if franchise_value > 0:
                            st.success(status_moat)
                        else:
                            st.error(status_moat)
                            
                        with st.expander("🔍 Lihat Detail Breakdown Kuantitatif"):
                            st.write(f"**Basis Laba yang Digunakan:** {basis_laba}")
                            st.write(f"**Nilai Laba Basis / Lembar:** {eps_fcf:,.2f}")
                            st.write(f"**Kapasitas Laba (EPV):** {epv:,.2f}")
                            st.write(f"**Biaya Reproduksi (ARV/Saham):** {arv_per_share:,.2f}")
                            st.write(f"**Nilai Monopoli (Franchise):** {franchise_value:,.2f}")

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan saat memproses data API. Silakan coba beberapa saat lagi. Detail: {e}")
