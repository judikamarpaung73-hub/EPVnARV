import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="Mesin Audit Multi-Sektor", layout="centered", page_icon="📈")

FILTERS_RIIL = {
    'min_market_cap_usd': 500000000,
    'min_avg_volume': 100000,
    'gross_margin_min': 40.0,
    'operating_margin_min': 15.0,
    'roic_min': 12.0,
    'cash_conversion_min': 80.0,
    'net_debt_ebitda_max': 3.0,
    'interest_coverage_min': 5.0,
    'min_years_listed': 5,
    'rsi_min': 30,
    'rsi_max': 70
}

FILTERS_KEUANGAN = {
    'min_market_cap_usd': 500000000,
    'min_avg_volume': 100000,
    'roe_min': 15.0,
    'roa_min': 1.5,
    'min_years_listed': 5,
    'rsi_min': 30,
    'rsi_max': 70
}

st.sidebar.title("🛡️ Panel Kendali Multi-Sektor")
sektor_pilihan = st.sidebar.radio(
    "Pilih Sektor Emiten:",
    ["Sektor Riil (Teknologi, Konsumsi, Ritel)", "Sektor Keuangan (Bank & Asuransi)"]
)
st.sidebar.markdown("---")
st.sidebar.info("Sistem akan menyesuaikan seluruh formula matematika dan pilar evaluasi berdasarkan sektor yang dipilih.")

if sektor_pilihan == "Sektor Riil (Teknologi, Konsumsi, Ritel)":
    st.title("🏭 Sektor Riil: Auditing EPV & ARV")
    st.write("Menggunakan kapasitas Arus Kas Bebas (FCF) tanpa pertumbuhan dan biaya reproduksi aset.")

    ticker_input = st.text_input("Masukkan Ticker Saham Sektor Riil (Contoh: META, UNVR.JK):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi data industri untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data kosong.")
                else:
                    current_price = float(info.get('currentPrice', info.get('previousClose', 0)) or 0)
                    shares_raw = float(info.get('sharesOutstanding', 0) or 0)
                    eps_raw = float(info.get('trailingEps', 0) or 0)
                    market_cap = float(info.get('marketCap', 1) or 1)

                    fcf_raw = 0.0
                    cf = stock.cash_flow
                    if cf is not None and not cf.empty:
                        if 'Free Cash Flow' in cf.index:
                            fcf_history = cf.loc['Free Cash Flow'].dropna().head(3)
                            if len(fcf_history) > 0: fcf_raw = float(fcf_history.mean())
                    if fcf_raw == 0.0: fcf_raw = float(info.get('freeCashflow', 0) or 0)

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

                    gross_margin = info.get('grossMargins', 0) * 100
                    op_margin = info.get('operatingMargins', 0) * 100
                    roic = info.get('returnOnEquity', info.get('returnOnAssets', 0)) * 100
                    net_income = float(info.get('netIncomeToCommon', 1) or 1)
                    ebitda = float(info.get('ebitda', 0) or 0)
                    total_debt = float(info.get('totalDebt', 0) or 0)
                    
                    raw_debt_ebitda = info.get('debtToEbitda', None)
                    debt_ebitda = float(raw_debt_ebitda) if raw_debt_ebitda is not None else (total_debt / ebitda if ebitda > 0 else 0.0)
                    int_expense = float(info.get('interestExpense', 1) or 1)
                    int_cover = abs(ebitda / int_expense) if int_expense != 0 else 999

                    st.markdown("---")
                    if fcf_raw <= 0: st.warning("⚠️ **PERINGATAN KRITIS:** FCF negatif/0. Mesin beralih ke EPS.")
                    
                    with st.form("riil_override_form"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            fcf_input = st.number_input("Total Free Cash Flow (FCF)", value=fcf_raw, step=1000.0)
                            eps_input = st.number_input("EPS Trailing", value=eps_raw, step=10.0)
                            shares_input = st.number_input("Jumlah Saham Beredar", value=shares_raw, step=1000.0)
                        with col_b:
                            equity_input = st.number_input("Total Ekuitas (Nilai Buku)", value=equity_raw, step=1000.0)
                            rd_input = st.number_input("Total R&D (5 Tahun)", value=rd_raw, step=1000.0)
                            sga_input = st.number_input("Total SG&A (3 Tahun)", value=sga_raw, step=1000.0)
                        submit_btn = st.form_submit_button("Jalankan Audit Sektor Riil")

                    if submit_btn and shares_input > 0:
                        # 1. Kalkulasi Valuasi
                        eps_fcf = fcf_input / shares_input if fcf_input > 0 else eps_input
                        basis_laba = "FCF per Share" if fcf_input > 0 else "EPS Trailing"
                        epv = eps_fcf * 15
                        arv_per_share = (equity_input + rd_input + sga_input) / shares_input
                        franchise_value = epv - arv_per_share
                        harga_wajar = epv if franchise_value > 0 else min(epv, arv_per_share)
                        zona_beli = harga_wajar * 0.80
                        
                        # 2. Kalkulasi Pilar & Tarikan Data Teknikal
                        cash_conv = (fcf_input / net_income) * 100 if net_income > 0 else 0
                        fcf_yield = (fcf_input / market_cap) * 100 if market_cap > 0 else 0
                        
                        df = yf.download(ticker_input, period=f"{FILTERS_RIIL['min_years_listed']}y", interval="1d", progress=False)
                        latest_rsi = "N/A"
                        if not df.empty:
                            close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                            df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                            latest_rsi = float(df['RSI'].iloc[-1])

                        # 3. Tampilan UI Kesimpulan Valuasi
                        st.markdown("### 🎯 Kesimpulan Valuasi Sektor Riil")
                        res1, res2 = st.columns(2)
                        res1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                        res2.metric("Harga Wajar (Fair Value)", f"{harga_wajar:,.2f}")
                        st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli:,.2f}")
                        
                        if franchise_value > 0: st.success("🔥 TERDETEKSI MOAT: Memiliki nilai waralaba.")
                        else: st.error("⚠️ VALUE TRAP: Bersifat padat modal.")

                        # 4. Tampilan UI Breakdown Kuantitatif Riil
                        with st.expander("🔍 Detail Breakdown Kuantitatif (Valuasi & 6 Pilar)"):
                            st.markdown("**METRIK VALUASI:**")
                            st.write(f"- **Basis Laba:** {basis_laba}")
                            st.write(f"- **Laba Basis / Lembar:** {eps_fcf:,.2f}")
                            st.write(f"- **Kapasitas Laba (EPV):** {epv:,.2f}")
                            st.write(f"- **Biaya Reproduksi (ARV/Saham):** {arv_per_share:,.2f}")
                            st.write(f"- **Nilai Monopoli (Franchise):** {franchise_value:,.2f}")
                            
                            st.markdown("**METRIK SCREENER 6 PILAR:**")
                            st.write(f"- **Gross Margin:** {gross_margin:.1f}%")
                            st.write(f"- **Operating Margin:** {op_margin:.1f}%")
                            st.write(f"- **ROIC:** {roic:.1f}%")
                            st.write(f"- **Cash Conversion:** {cash_conv:.1f}%")
                            st.write(f"- **Debt / EBITDA:** {debt_ebitda:.2f}x")
                            st.write(f"- **Interest Coverage:** {int_cover:.1f}x")
                            st.write(f"- **FCF Yield:** {fcf_yield:.1f}%")
                            if isinstance(latest_rsi, float):
                                st.write(f"- **RSI (14 Hari):** {latest_rsi:.1f}")
                            else:
                                st.write("- **RSI (14 Hari):** Data Kosong")

                        # 5. Tampilan UI Lolos/Gagal Pilar
                        st.markdown("---")
                        st.markdown("### 🛡️ Hasil Pemindaian Multi-Pilar (Sektor Riil)")
                        passed, failed = [], []

                        # Logika Evaluasi dengan Detail Metrik
                        metrics = [
                            ("P3 (Margin)", (gross_margin + op_margin) / 2, (FILTERS_RIIL['gross_margin_min'] + FILTERS_RIIL['operating_margin_min']) / 2, "Kombinasi Margin > 27.5%"),
                            ("P4 (ROIC)", roic, FILTERS_RIIL['roic_min'], "%"),
                            ("P5 (Cash Conv)", cash_conv, FILTERS_RIIL['cash_conversion_min'], "%"),
                            ("P5 (Debt/EBITDA)", debt_ebitda, FILTERS_RIIL['net_debt_ebitda_max'], "x (Maks)"),
                            ("P10 (FCF Yield)", fcf_yield, 5.0, "%")
                        ]

                        for label, val, min_val, unit in metrics:
                            if (label == "P5 (Debt/EBITDA)" and val <= min_val) or (label != "P5 (Debt/EBITDA)" and val >= min_val):
                                passed.append(f"{label}: {val:.1f}{unit} (Min: {min_val}{unit})")
                            else:
                                failed.append(f"{label}: {val:.1f}{unit} (Min: {min_val}{unit})")

                        # Lindy & RSI
                        if not df.empty and len(df) >= (200 * FILTERS_RIIL['min_years_listed']):
                            passed.append(f"P1 (Lindy): Lulus {FILTERS_RIIL['min_years_listed']} Tahun")
                        else: failed.append("P1 (Lindy): Gagal")
                        
                        if isinstance(latest_rsi, float):
                            if FILTERS_RIIL['rsi_min'] <= latest_rsi <= FILTERS_RIIL['rsi_max']:
                                passed.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_RIIL['rsi_min']}-{FILTERS_RIIL['rsi_max']})")
                            else: failed.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_RIIL['rsi_min']}-{FILTERS_RIIL['rsi_max']})")

                        skor = len(passed)
                        st.metric("Skor Kualitas Institusional", f"{skor} / 6")
                        
                        col_p, col_f = st.columns(2)
                        with col_p:
                            st.markdown("**✅ Lolos:**")
                            for p in passed: st.markdown(f"- {p}")
                        with col_f:
                            st.markdown("**❌ Gagal:**")
                            for f in failed: st.markdown(f"- {f}")

            except Exception as e: st.error(f"❌ Sistem Eror Sektor Riil: {e}")

elif sektor_pilihan == "Sektor Keuangan (Bank & Asuransi)":
    st.title("🏦 Sektor Keuangan: Auditing Justified PBV Model")
    st.write("Menggunakan korelasi antara Return on Equity (ROE), Suku Bunga Diskonto, dan Nilai Buku Per Lembar Saham (BVPS).")

    ticker_input = st.text_input("Masukkan Ticker Saham Finansial (Contoh: BBCA.JK, BBRI.JK, JPM):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi neraca perbankan untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data kosong.")
                else:
                    current_price = float(info.get('currentPrice', info.get('previousClose', 0)) or 0)
                    bvps_raw = float(info.get('bookValue', 0) or 0)
                    roe_raw = float(info.get('returnOnEquity', 0) * 100 or 0)
                    roa_raw = float(info.get('returnOnAssets', 0) * 100 or 0)
                    shares_raw = float(info.get('sharesOutstanding', 0) or 0)

                    st.markdown("---")
                    st.info(f"ℹ️ **Data Terdeteksi:** ROE: {roe_raw:.2f}% | BVPS (Nilai Buku/Lembar): {bvps_raw:,.2f}")

                    with st.form("bank_override_form"):
                        st.markdown("### 📝 Koreksi Laporan Keuangan Bank (Input Manual)")
                        col_c, col_d = st.columns(2)
                        with col_c:
                            bvps_input = st.number_input("Book Value Per Share (BVPS)", value=bvps_raw, step=100.0)
                            roe_input = st.number_input("Return on Equity (ROE %)", value=roe_raw, step=1.0)
                            roa_input = st.number_input("Return on Assets (ROA %)", value=roa_raw, step=0.1)
                        with col_d:
                            ke_input = st.number_input("Cost of Equity / Batas Diskonto (Ke %)", value=11.0, step=0.5, help="Tingkat pengembalian minimum wajib bagi investor.")
                            g_input = st.number_input("Long-term Growth Rate (g %)", value=6.0, step=0.5, help="Ekspektasi pertumbuhan kredit jangka panjang emiten.")
                        
                        submit_bank_btn = st.form_submit_button("Jalankan Audit Keuangan")

                    if submit_bank_btn:
                        if ke_input <= g_input:
                            st.error("❌ Eror Matematika: Nilai Cost of Equity (Ke) harus lebih besar daripada tingkat pertumbuhan (g).")
                        else:
                            # 1. Kalkulasi Matematika Bank
                            roe_decimal = roe_input / 100
                            g_decimal = g_input / 100
                            ke_decimal = ke_input / 100
                            justified_pbv = (roe_decimal - g_decimal) / (ke_decimal - g_decimal)
                            harga_wajar_bank = justified_pbv * bvps_input
                            zona_beli_bank = harga_wajar_bank * 0.80
                            market_pbv = current_price / bvps_input if bvps_input > 0 else 0
                            
                            # 2. Tarik Data Teknikal
                            period_str = f"{FILTERS_KEUANGAN['min_years_listed']}y"
                            df = yf.download(ticker_input, period=period_str, interval="1d", progress=False)
                            latest_rsi = "N/A"
                            if not df.empty:
                                close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                                df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                                latest_rsi = float(df['RSI'].iloc[-1])

                            # 3. Tampilan UI Kesimpulan
                            st.markdown("### 🎯 Kesimpulan Valuasi Perbankan")
                            res_b1, res_b2 = st.columns(2)
                            res_b1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                            res_b2.metric("Harga Wajar (Fair Justified PBV)", f"{harga_wajar_bank:,.2f}")
                            
                            st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli_bank:,.2f}")

                            if roe_input > ke_input:
                                st.success(f"🔥 ECONOMIC MOAT POSITIF: Bank sukses menghasilkan return ({roe_input:.1f}%) di atas biaya modalnya ({ke_input:.1f}%). PBV Wajar secara teoritis layak dihargai {justified_pbv:.2f}x.")
                            else:
                                st.error(f"☠️ VALUE DESTRUKTIF: Operasional bank membakar modal pemegang saham karena ROE ({roe_input:.1f}%) < Cost of Equity ({ke_input:.1f}%).")

                            # 4. Tampilan UI Breakdown Kuantitatif Finansial
                            with st.expander("🔍 Detail Breakdown Kuantitatif (Valuasi & 5 Pilar)"):
                                st.markdown("**METRIK VALUASI (GORDON GROWTH):**")
                                st.write(f"- **Market PBV Saat Ini:** {market_pbv:.2f}x")
                                st.write(f"- **Justified PBV Teoritis:** {justified_pbv:.2f}x")
                                st.write(f"- **Spread (ROE - Cost of Equity):** {(roe_input - ke_input):.2f}%")
                                st.write(f"- **Book Value Per Share (BVPS):** {bvps_input:,.2f}")
                                
                                st.markdown("**METRIK SCREENER 5 PILAR:**")
                                st.write(f"- **Return on Equity (ROE):** {roe_input:.1f}%")
                                st.write(f"- **Return on Assets (ROA):** {roa_input:.2f}%")
                                if isinstance(latest_rsi, float):
                                    st.write(f"- **RSI (14 Hari):** {latest_rsi:.1f}")
                                else:
                                    st.write("- **RSI (14 Hari):** Data Kosong")

                            # 5. Tampilan UI Lolos/Gagal Pilar Finansial
                        st.markdown("---")
                        st.markdown("### 🛡️ Hasil Pemindaian Multi-Pilar (Sektor Riil)")
                        passed, failed = [], []

                        # Logika Evaluasi dengan Detail Metrik
                        metrics = [
                            ("P3 (Margin)", (gross_margin + op_margin) / 2, (FILTERS_RIIL['gross_margin_min'] + FILTERS_RIIL['operating_margin_min']) / 2, "Kombinasi Margin > 27.5%"),
                            ("P4 (ROIC)", roic, FILTERS_RIIL['roic_min'], "%"),
                            ("P5 (Cash Conv)", cash_conv, FILTERS_RIIL['cash_conversion_min'], "%"),
                            ("P5 (Debt/EBITDA)", debt_ebitda, FILTERS_RIIL['net_debt_ebitda_max'], "x (Maks)"),
                            ("P10 (FCF Yield)", fcf_yield, 5.0, "%")
                        ]

                        for label, val, min_val, unit in metrics:
                            if (label == "P5 (Debt/EBITDA)" and val <= min_val) or (label != "P5 (Debt/EBITDA)" and val >= min_val):
                                passed.append(f"{label}: {val:.1f}{unit} (Min: {min_val}{unit})")
                            else:
                                failed.append(f"{label}: {val:.1f}{unit} (Min: {min_val}{unit})")

                        # Lindy & RSI
                        if not df.empty and len(df) >= (200 * FILTERS_RIIL['min_years_listed']):
                            passed.append(f"P1 (Lindy): Lulus {FILTERS_RIIL['min_years_listed']} Tahun")
                        else: failed.append("P1 (Lindy): Gagal")
                        
                        if isinstance(latest_rsi, float):
                            if FILTERS_RIIL['rsi_min'] <= latest_rsi <= FILTERS_RIIL['rsi_max']:
                                passed.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_RIIL['rsi_min']}-{FILTERS_RIIL['rsi_max']})")
                            else: failed.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_RIIL['rsi_min']}-{FILTERS_RIIL['rsi_max']})")

                        skor = len(passed)
                        st.metric("Skor Kualitas Institusional", f"{skor} / 6")
                        
                        col_p, col_f = st.columns(2)
                        with col_p:
                            st.markdown("**✅ Lolos:**")
                            for p in passed: st.markdown(f"- {p}")
                        with col_f:
                            st.markdown("**❌ Gagal:**")
                            for f in failed: st.markdown(f"- {f}")
            except Exception as e: st.error(f"❌ Terjadi kesalahan pengolahan data perbankan: {e}")
