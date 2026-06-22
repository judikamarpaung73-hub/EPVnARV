import streamlit as st
import yfinance as yf
import pandas as pd

# Konfigurasi halaman awal peramban
st.set_page_config(page_title="Kalkulator Valuasi Institusional", layout="centered")

st.title("📊 Mesin Audit Manual (EPV vs ARV)")
st.write("Aplikasi analitik kuantitatif berbasis Arus Kas Riil dan Aset Tak Berwujud.")

# Kolom Input Ticker di HP
ticker_input = st.text_input("Masukkan Ticker Saham (Contoh: META, BBCA.JK):", "").upper()

if ticker_input:
    with st.spinner(f"Menarik laporan keuangan untuk {ticker_input}..."):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            if not info:
                st.error("⚠️ Emiten tidak ditemukan atau data kosong.")
            else:
                # 1. Ekstraksi Data Dasar Laba
                shares = info.get('sharesOutstanding', 0)
                fcf = info.get('freeCashflow', 0)
                
                if fcf > 0 and shares > 0:
                    eps_fcf = fcf / shares
                    basis_laba = "FCF per Share"
                else:
                    eps_fcf = info.get('trailingEps', 0)
                    basis_laba = "EPS (Trailing)"

                current_price = info.get('currentPrice', info.get('previousClose', 0))

                # 2. Ekstraksi Neraca (Ekuitas)
                bs = stock.balance_sheet
                equity = 0
                if 'Stockholders Equity' in bs.index:
                    equity = bs.loc['Stockholders Equity'].iloc[0]
                elif 'Total Stockholder Equity' in bs.index:
                    equity = bs.loc['Total Stockholder Equity'].iloc[0]
                elif 'Common Stock Equity' in bs.index:
                    equity = bs.loc['Common Stock Equity'].iloc[0]

                # 3. Ekstraksi Laba Rugi (SG&A 3 Thn, R&D 5 Thn)
                inc = stock.financials
                sga_total = 0
                if 'Selling General And Administration' in inc.index:
                    sga_total = inc.loc['Selling General And Administration'].dropna().head(3).sum()

                rd_total = 0
                if 'Research And Development' in inc.index:
                    rd_total = inc.loc['Research And Development'].dropna().head(5).sum()

                if shares == 0 or eps_fcf <= 0:
                    st.warning("⚠️ Perusahaan membukukan kerugian bersih atau data lembar saham tidak valid.")
                else:
                    # 4. Kalkulasi Formula Valuasi
                    epv = eps_fcf * 15
                    arv_total = equity + rd_total + sga_total
                    arv_per_share = arv_total / shares
                    franchise_value = epv - arv_per_share

                    if franchise_value > 0:
                        status_moat = "🔥 TERDETEKSI MOAT: Laba dilindungi nilai waralaba aset tak berwujud."
                        harga_wajar = epv
                    else:
                        status_moat = "⚠️ VALUE TRAP: Laba didorong padat modal, tidak memiliki kekuatan harga."
                        harga_wajar = min(epv, arv_per_share)

                    zona_beli = harga_wajar * 0.80

                    # 5. Tampilan Dasbor di Layar HP
                    st.markdown("---")
                    
                    # Menampilkan metrik utama dalam kolom berdampingan
                    col1, col2 = st.columns(2)
                    col1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                    col2.metric("Harga Wajar (Fair Value)", f"{harga_wajar:,.2f}")
                    
                    st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli:,.2f}")
                    
                    if franchise_value > 0:
                        st.success(status_moat)
                    else:
                        st.error(status_moat)

                    # Detail metrik yang bisa dibuka-tutup di layar HP
                    with st.expander("🔍 Lihat Detail Breakdown Kuantitatif"):
                        st.write(f"**Basis Kapasitas Laba:** {basis_laba}")
                        st.write(f"**Laba per Saham:** {eps_fcf:,.2f}")
                        st.write(f"**Kapasitas Laba (EPV):** {epv:,.2f}")
                        st.write(f"**Biaya Reproduksi (ARV/Saham):** {arv_per_share:,.2f}")
                        st.write(f"**Nilai Monopoli (Franchise):** {franchise_value:,.2f}")
                        st.write(f"**Total Ekuitas:** {equity:,.0f}")
                        st.write(f"**Total R&D (5 Tahun):** {rd_total:,.0f}")
                        st.write(f"**Total SG&A (3 Tahun):** {sga_total:,.0f}")
                        
        except Exception as e:
            st.error(f"❌ Gagal memproses emiten. Peladen Yahoo Finance mengembalikan eror: {e}")
