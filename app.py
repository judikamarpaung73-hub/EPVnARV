import streamlit as st
import yfinance as yf
import pandas as pd
import ta

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Mesin Analisis Institusional", layout="centered", page_icon="📈")

FILTERS = {
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
    'rsi_max': 70,
    'price_above_ma200': False
}

st.title("📊 Mesin Audit Institusional Terpusat")
st.write("Sistem ekstraksi fundamental, intervensi manual EPV/ARV, dan pemindaian 6 Pilar secara terintegrasi.")

ticker_input = st.text_input("Masukkan Ticker Saham (Contoh: META, BBCA.JK):", "").upper()

if ticker_input:
    with st.spinner(f"Menarik seluruh set data untuk {ticker_input}..."):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                st.error("⚠️ Emiten tidak ditemukan atau data ditarik dalam keadaan kosong.")
            else:
                # ==========================================
                # 1. EKSTRAKSI DATA KASAR UNTUK VALUASI
                # ==========================================
                current_price = float(info.get('currentPrice', info.get('previousClose', 0)) or 0)
                shares_raw = float(info.get('sharesOutstanding', 0) or 0)
                eps_raw = float(info.get('trailingEps', 0) or 0)
                market_cap = float(info.get('marketCap', 1) or 1)

                fcf_raw = 0.0
                cf = stock.cash_flow
                if cf is not None and not cf.empty:
                    if 'Free Cash Flow' in cf.index:
                        fcf_history = cf.loc['Free Cash Flow'].dropna().head(3)
                        if len(fcf_history) > 0:
                            fcf_raw = float(fcf_history.mean())
                
                if fcf_raw == 0.0:
                    fcf_raw = float(info.get('freeCashflow', 0) or 0)

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

                # ==========================================
                # 2. EKSTRAKSI DATA KASAR UNTUK SCREENER
                # ==========================================
                gross_margin = info.get('grossMargins', 0) * 100
                op_margin = info.get('operatingMargins', 0) * 100
                roic = info.get('returnOnEquity', info.get('returnOnAssets', 0)) * 100
                net_income = float(info.get('netIncomeToCommon', 1) or 1)
                
                ebitda = float(info.get('ebitda', 0) or 0)
                total_debt = float(info.get('totalDebt', 0) or 0)
                raw_debt_ebitda = info.get('debtToEbitda', None)
                
                if raw_debt_ebitda is not None:
                    debt_ebitda = float(raw_debt_ebitda)
                elif ebitda > 0:
                    debt_ebitda = total_debt / ebitda
                else:
                    debt_ebitda = 0.0
                    
                int_expense = float(info.get('interestExpense', 1) or 1)
                int_cover = abs(ebitda / int_expense) if int_expense != 0 else 999

                st.markdown("---")
                if fcf_raw <= 0:
                    st.warning("⚠️ **PERINGATAN KRITIS:** Mesin gagal menemukan FCF positif. Jika tidak diisi manual, mesin menggunakan EPS.")
                if rd_raw == 0 and sga_raw == 0:
                    st.info("ℹ️ **INFO:** Beban R&D dan SG&A terdeteksi 0.")

                # ==========================================
                # 3. FORMULIR INTERVENSI MANUAL
                # ==========================================
                st.markdown("### 📝 Ruang Koreksi Data Manual")
                
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
                    
                    submit_btn = st.form_submit_button("Jalankan Diagnosis Final")

                # ==========================================
                # 4. EKSEKUSI VALUASI & SCREENER (SETELAH SUBMIT)
                # ==========================================
                if submit_btn:
                    if shares_input <= 0:
                        st.error("❌ Eror Fatal: Jumlah saham beredar tidak boleh 0.")
                    else:
                        # LOGIKA VALUASI (HARGA WAJAR)
                        if fcf_input > 0:
                            eps_fcf = fcf_input / shares_input
                            basis_laba = "FCF per Share"
                        else:
                            eps_fcf = eps_input
                            basis_laba = "EPS Trailing"
                        
                        epv = eps_fcf * 15
                        arv_total = equity_input + rd_input + sga_input
                        arv_per_share = arv_total / shares_input
                        franchise_value = epv - arv_per_share
                        
                        if franchise_value > 0:
                            status_moat = "🔥 TERDETEKSI MOAT: Laba dilindungi nilai waralaba aset tak berwujud."
                            harga_wajar = epv
                        else:
                            status_moat = "⚠️ VALUE TRAP: Laba didorong padat modal, tidak memiliki kekuatan harga."
                            harga_wajar = min(epv, arv_per_share)
                        
                        zona_beli = harga_wajar * 0.80

                        st.markdown("---")
                        st.markdown("### 🎯 Kesimpulan Valuasi Institusional")
                        
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

                        # LOGIKA SCREENER (MENGGUNAKAN DATA KOREKSI)
                        st.markdown("---")
                        st.markdown("### 🛡️ Hasil Pemindaian Multi-Pilar")
                        
                        passed = []
                        failed = []

                        if gross_margin >= FILTERS['gross_margin_min'] and op_margin >= FILTERS['operating_margin_min']:
                            passed.append("P3 (Kualitas Margins)")
                        else:
                            failed.append(f"P3 (Kualitas): Gross {gross_margin:.1f}%, Op {op_margin:.1f}%")

                        if roic >= FILTERS['roic_min']:
                            passed.append(f"P4 (Pemajemuk/ROIC: {roic:.1f}%)")
                        else:
                            failed.append(f"P4 (Pemajemuk/ROIC): {roic:.1f}%")

                        # Cash Conversion sekarang menggunakan fcf_input dari form manual
                        cash_conv = (fcf_input / net_income) * 100 if net_income > 0 else 0
                        p5_reasons = []
                        if cash_conv < FILTERS['cash_conversion_min']: p5_reasons.append(f"Cash Conv {cash_conv:.1f}%")
                        if debt_ebitda > FILTERS['net_debt_ebitda_max']: p5_reasons.append(f"Debt/EBITDA {debt_ebitda:.2f}x")
                        if int_cover < FILTERS['interest_coverage_min']: p5_reasons.append(f"Int Cover {int_cover:.1f}x")
                        
                        if not p5_reasons:
                            passed.append(f"P5 (Neraca Sehat | Debt: {debt_ebitda:.2f}x)")
                        else:
                            failed.append(f"P5 (Neraca): {', '.join(p5_reasons)}")

                        # FCF Yield juga menggunakan fcf_input
                        fcf_yield = (fcf_input / market_cap) * 100 if market_cap > 0 else 0
                        if fcf_yield >= 5.0:
                            passed.append(f"P10 (Valuasi FCF Yield: {fcf_yield:.1f}%)")
                        else:
                            failed.append(f"P10 (Valuasi FCF Yield): {fcf_yield:.1f}%")

                        # Tarik data harga teknikal
                        period_str = f"{FILTERS['min_years_listed']}y"
                        df = yf.download(ticker_input, period=period_str, interval="1d", progress=False)
                        
                        if not df.empty and len(df) >= (250 * FILTERS['min_years_listed']):
                            passed.append(f"P1 (Lindy Effect: Lulus {FILTERS['min_years_listed']} Tahun)")
                        else:
                            failed.append("P1 (Lindy Effect): Gagal")

                        if not df.empty:
                            close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                            df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                            df['MA200'] = ta.trend.SMAIndicator(close_prices, window=200).sma_indicator()
                            
                            latest_rsi = float(df['RSI'].iloc[-1])
                            latest_close = float(close_prices.iloc[-1])
                            latest_ma200 = float(df['MA200'].iloc[-1])
                            
                            if (FILTERS['rsi_min'] <= latest_rsi <= FILTERS['rsi_max']):
                                passed.append(f"P8 (Teknikal: RSI {latest_rsi:.1f})")
                            else:
                                failed.append(f"P8 (Teknikal): RSI {latest_rsi:.1f} di luar batas aman")
                        else:
                            failed.append("P8 (Teknikal): Data harga gagal ditarik")

                        # Cetak Hasil Akhir Screener
                        skor = len(passed)
                        st.metric("Skor Kualitas Institusional", f"{skor} / 6")
                        
                        if skor == 6:
                            st.success("🚨 KANDIDAT MULTI-BAGGER SEMPURNA! Seluruh pilar berhasil ditembus.")
                        elif skor >= 4:
                            st.info("🏦 Emiten masuk kriteria pantauan, namun memiliki beberapa kelemahan.")
                        else:
                            st.error("☠️ HIGH RISK / VALUE TRAP. Mesin menolak emiten ini secara absolut.")

                        col_p, col_f = st.columns(2)
                        with col_p:
                            st.markdown("**✅ Pilar yang Lolos:**")
                            for p in passed:
                                st.markdown(f"- {p}")
                        with col_f:
                            st.markdown("**❌ Pilar yang Gagal:**")
                            for f in failed:
                                st.markdown(f"- {f}")

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan sistem. Detail: {e}")
