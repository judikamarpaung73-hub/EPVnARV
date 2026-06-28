import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import numpy as np

st.set_page_config(page_title="Mesin Audit Multi-Sektor", layout="wide", page_icon="📈")

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

TACTICAL_FILTERS_RIIL = {
    'p1_pbv_max': 1.6,          
    'p2_roe_min': 15.0,         
    'p3_dol_min': 1.2,          
    'p4_ev_ebitda_max': 9.0,    
    'p5_div_yield_min': 7.0,    
    'p6_eps_growth_min': 10.0,  
    'p7_op_margin_min': 15.0,   
    'p8_de_ratio_max': 1.5,     
    'p10_rsi_min': 30.0,        
    'p10_rsi_max': 70.0         
}

TACTICAL_FILTERS_BANK = {
    'p1_pbv_max': 1.6,
    'p2_roe_min': 15.0,
    'p3_roa_min': 1.5,
    'p4_per_max': 10.0,
    'p5_div_yield_min': 7.0,
    'p6_eps_growth_min': 10.0,
    'p7_net_margin_min': 20.0,
    'p8_rev_growth_min': 5.0,
    'p10_rsi_min': 30.0,
    'p10_rsi_max': 70.0
}

def safe_float(val, default=0.0):
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except:
        return default

st.sidebar.title("🛡️ Panel Kendali Multi-Sektor")
sektor_pilihan = st.sidebar.radio(
    "Pilih Modul Audit:",
    [
        "🏭 Sektor Riil (EPV & ARV)", 
        "🏦 Sektor Keuangan (Justified PBV)", 
        "🎯 Taktis 1-3 Thn (Sektor Riil)",
        "🎯 Taktis 1-3 Thn (Sektor Keuangan)"
    ]
)
st.sidebar.markdown("---")
st.sidebar.info("Sistem akan menyesuaikan formula dan pilar berdasarkan sektor yang dipilih.")

if sektor_pilihan == "🏭 Sektor Riil (EPV & ARV)":
    st.title("🏭 Sektor Riil: Auditing EPV & ARV")
    ticker_input = st.text_input("Masukkan Ticker Saham Sektor Riil (Contoh: META, UNVR.JK):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi data industri untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data kosong.")
                else:
                    current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                    shares_raw = safe_float(info.get('sharesOutstanding', 0))
                    eps_raw = safe_float(info.get('trailingEps', 0))
                    market_cap = safe_float(info.get('marketCap', 1))

                    fcf_raw = 0.0
                    cf = stock.cash_flow
                    if cf is not None and not cf.empty and 'Free Cash Flow' in cf.index:
                        fcf_history = cf.loc['Free Cash Flow'].dropna().head(3)
                        if len(fcf_history) > 0: fcf_raw = float(fcf_history.mean())
                    if fcf_raw == 0.0: fcf_raw = safe_float(info.get('freeCashflow', 0))

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

                    gross_margin = safe_float(info.get('grossMargins', 0)) * 100
                    op_margin = safe_float(info.get('operatingMargins', 0)) * 100
                    roic = safe_float(info.get('returnOnEquity', info.get('returnOnAssets', 0))) * 100
                    net_income = safe_float(info.get('netIncomeToCommon', 1))
                    if net_income == 0: net_income = 1
                    ebitda = safe_float(info.get('ebitda', 0))
                    total_debt = safe_float(info.get('totalDebt', 0))
                    
                    raw_debt_ebitda = info.get('debtToEbitda', None)
                    debt_ebitda = float(raw_debt_ebitda) if raw_debt_ebitda is not None else (total_debt / ebitda if ebitda > 0 else 0.0)
                    int_expense = safe_float(info.get('interestExpense', 1))
                    if int_expense == 0: int_expense = 1
                    int_cover = abs(ebitda / int_expense)

                    st.markdown("---")
                    
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
                        eps_fcf = fcf_input / shares_input if fcf_input > 0 else eps_input
                        basis_laba = "FCF per Share" if fcf_input > 0 else "EPS Trailing"
                        epv = eps_fcf * 15
                        arv_per_share = (equity_input + rd_input + sga_input) / shares_input
                        franchise_value = epv - arv_per_share
                        harga_wajar = epv if franchise_value > 0 else min(epv, arv_per_share)
                        zona_beli = harga_wajar * 0.80
                        
                        cash_conv = (fcf_input / net_income) * 100 if net_income > 0 else 0
                        fcf_yield = (fcf_input / market_cap) * 100 if market_cap > 0 else 0
                        
                        df = yf.download(ticker_input, period=f"{FILTERS_RIIL['min_years_listed']}y", interval="1d", progress=False)
                        latest_rsi = "N/A"
                        if not df.empty:
                            close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                            df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                            latest_rsi = float(df['RSI'].iloc[-1])

                        st.markdown("### 🎯 Kesimpulan Valuasi Sektor Riil")
                        res1, res2 = st.columns(2)
                        res1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                        res2.metric("Harga Wajar (Fair Value)", f"{harga_wajar:,.2f}")
                        st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli:,.2f}")
                        
                        if franchise_value > 0: st.success("🔥 TERDETEKSI MOAT: Memiliki nilai waralaba.")
                        else: st.error("⚠️ VALUE TRAP: Bersifat padat modal.")

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

                        st.markdown("---")
                        st.markdown("### 🛡️ Hasil Pemindaian Multi-Pilar (Sektor Riil)")
                        passed, failed = [], []

                        metrics = [
                            ("P3 (Margin)", (gross_margin + op_margin) / 2, (FILTERS_RIIL['gross_margin_min'] + FILTERS_RIIL['operating_margin_min']) / 2, ", Kombinasi Margin > 27.5%"),
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
                            for p in passed:
                                st.markdown(f"- {p}")
                        with col_f:
                            st.markdown("**❌ Gagal:**")
                            for f in failed:
                                st.markdown(f"- {f}")

            except Exception as e: st.error(f"❌ Sistem Eror Sektor Riil: {e}")

elif sektor_pilihan == "🏦 Sektor Keuangan (Justified PBV)":
    st.title("🏦 Sektor Keuangan: Auditing Justified PBV Model")
    ticker_input = st.text_input("Masukkan Ticker Saham Finansial (Contoh: BBCA.JK, BBRI.JK):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi neraca perbankan untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data kosong.")
                else:
                    current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                    bvps_raw = safe_float(info.get('bookValue', 0))
                    roe_raw = safe_float(info.get('returnOnEquity', 0)) * 100
                    roa_raw = safe_float(info.get('returnOnAssets', 0)) * 100

                    st.markdown("---")
                    
                    with st.form("bank_override_form"):
                        st.markdown("### 📝 Koreksi Laporan Keuangan Bank (Input Manual)")
                        col_c, col_d = st.columns(2)
                        with col_c:
                            bvps_input = st.number_input("Book Value Per Share (BVPS)", value=bvps_raw, step=100.0)
                            roe_input = st.number_input("Return on Equity (ROE %)", value=roe_raw, step=1.0)
                            roa_input = st.number_input("Return on Assets (ROA %)", value=roa_raw, step=0.1)
                        with col_d:
                            ke_input = st.number_input("Cost of Equity / Batas Diskonto (Ke %)", value=11.0, step=0.5)
                            g_input = st.number_input("Long-term Growth Rate (g %)", value=6.0, step=0.5)
                        
                        submit_bank_btn = st.form_submit_button("Jalankan Audit Keuangan")

                    if submit_bank_btn:
                        if ke_input <= g_input:
                            st.error("❌ Eror Matematika: Nilai Cost of Equity (Ke) harus lebih besar dari pertumbuhan (g).")
                        else:
                            roe_decimal = roe_input / 100
                            g_decimal = g_input / 100
                            ke_decimal = ke_input / 100
                            justified_pbv = (roe_decimal - g_decimal) / (ke_decimal - g_decimal)
                            harga_wajar_bank = justified_pbv * bvps_input
                            zona_beli_bank = harga_wajar_bank * 0.80
                            market_pbv = current_price / bvps_input if bvps_input > 0 else 0
                            
                            period_str = f"{FILTERS_KEUANGAN['min_years_listed']}y"
                            df = yf.download(ticker_input, period=period_str, interval="1d", progress=False)
                            latest_rsi = "N/A"
                            if not df.empty:
                                close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                                df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                                latest_rsi = float(df['RSI'].iloc[-1])

                            st.markdown("### 🎯 Kesimpulan Valuasi Perbankan")
                            res_b1, res_b2 = st.columns(2)
                            res_b1.metric("Harga Pasar Saat Ini", f"{current_price:,.2f}")
                            res_b2.metric("Harga Wajar (Fair Justified PBV)", f"{harga_wajar_bank:,.2f}")
                            st.metric("Zona Beli (MoS 20%)", f"Maks. {zona_beli_bank:,.2f}")

                            if roe_input > ke_input:
                                st.success(f"🔥 ECONOMIC MOAT POSITIF: ROE ({roe_input:.1f}%) di atas biaya modal ({ke_input:.1f}%).")
                            else:
                                st.error(f"☠️ VALUE DESTRUKTIF: ROE ({roe_input:.1f}%) < Cost of Equity ({ke_input:.1f}%).")

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

                            st.markdown("---")
                            st.markdown("### 🛡️ Hasil Pemindaian Multi-Pilar (Sektor Finansial)")
                            passed_bank, failed_bank = [], []
                            
                            bank_metrics = [
                                ("P3 (ROE)", roe_input, FILTERS_KEUANGAN['roe_min'], "%"),
                                ("P4 (ROA)", roa_input, FILTERS_KEUANGAN['roa_min'], "%"),
                                ("P5 (PBV vs Fair)", market_pbv, justified_pbv, "x (PBV Pasar <= Fair)")
                            ]

                            for label, val, limit, unit in bank_metrics:
                                if "PBV" in label:
                                    if val <= limit: passed_bank.append(f"{label}: {val:.2f}{unit}")
                                    else: failed_bank.append(f"{label}: {val:.2f}{unit}")
                                else:
                                    if val >= limit: passed_bank.append(f"{label}: {val:.1f}{unit} (Min: {limit}{unit})")
                                    else: failed_bank.append(f"{label}: {val:.1f}{unit} (Min: {limit}{unit})")

                            if not df.empty and len(df) >= (200 * FILTERS_KEUANGAN['min_years_listed']):
                                passed_bank.append(f"P1 (Lindy): Lulus > {FILTERS_KEUANGAN['min_years_listed']} Tahun")
                            else: failed_bank.append("P1 (Lindy): Gagal")

                            if isinstance(latest_rsi, float):
                                if FILTERS_KEUANGAN['rsi_min'] <= latest_rsi <= FILTERS_KEUANGAN['rsi_max']:
                                    passed_bank.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_KEUANGAN['rsi_min']}-{FILTERS_KEUANGAN['rsi_max']})")
                                else: failed_bank.append(f"P8 (RSI): {latest_rsi:.1f} (Range: {FILTERS_KEUANGAN['rsi_min']}-{FILTERS_KEUANGAN['rsi_max']})")

                            skor_bank = len(passed_bank)
                            st.metric("Skor Kualitas Institusional Perbankan", f"{skor_bank} / 5")
                            
                            col_bp, col_bf = st.columns(2)
                            with col_bp:
                                st.markdown("**✅ Lolos:**")
                                for p in passed_bank:
                                    st.markdown(f"- {p}")
                            with col_bf:
                                st.markdown("**❌ Gagal:**")
                                for f in failed_bank:
                                    st.markdown(f"- {f}")

            except Exception as e: st.error(f"❌ Terjadi kesalahan pengolahan data perbankan: {e}")

elif sektor_pilihan == "🎯 Taktis 1-3 Thn (Sektor Riil)":
    st.title("🎯 Taktis 1-3 Tahun: Sektor Riil")
    ticker_input = st.text_input("🔍 Masukkan Ticker Saham (Contoh: JPFA.JK, AAPL):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi data taktis untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data YFinance kosong.")
                else:
                    current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                    pbv_raw = safe_float(info.get('priceToBook', 0))
                    roe_raw = safe_float(info.get('returnOnEquity', 0)) * 100
                    ev_ebitda_raw = safe_float(info.get('enterpriseToEbitda', 0))
                    div_yield_raw = safe_float(info.get('dividendYield', 0)) * 100
                    eps_growth_raw = safe_float(info.get('earningsGrowth', 0)) * 100
                    rev_growth_raw = safe_float(info.get('revenueGrowth', 0)) * 100
                    op_margin_raw = safe_float(info.get('operatingMargins', 0)) * 100
                    
                    raw_de = safe_float(info.get('debtToEquity', 0))
                    de_ratio_raw = raw_de / 100 if raw_de > 0 else 0.0
                    
                    earn_g_decimal = safe_float(info.get('earningsGrowth', 0))
                    rev_g_decimal = safe_float(info.get('revenueGrowth', 0))
                    dol_raw = (earn_g_decimal / rev_g_decimal) if rev_g_decimal > 0 else 0.0

                    df = yf.download(ticker_input, period="1y", interval="1d", progress=False)
                    latest_close, latest_ma200, latest_rsi = current_price, 0.0, 50.0
                    
                    if not df.empty and len(df) > 50:
                        close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                        latest_close = float(close_prices.iloc[-1])
                        df['MA200'] = ta.trend.SMAIndicator(close_prices, window=200).sma_indicator()
                        latest_ma200 = float(df['MA200'].iloc[-1]) if not pd.isna(df['MA200'].iloc[-1]) else latest_close
                        df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                        latest_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0

                    st.markdown("---")
                    
                    with st.form("tactical_riil_form"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            pbv_input = st.number_input("PBV", value=float(pbv_raw), step=0.1)
                            roe_input = st.number_input("ROE (%)", value=float(roe_raw), step=1.0)
                            ev_ebitda_input = st.number_input("EV / EBITDA", value=float(ev_ebitda_raw), step=0.5)
                        with col2:
                            eps_g_input = st.number_input("EPS Growth (%)", value=float(eps_growth_raw), step=1.0)
                            rev_g_input = st.number_input("Rev Growth (%)", value=float(rev_growth_raw), step=1.0)
                            dol_input = st.number_input("DOL", value=float(dol_raw), step=0.1)
                        with col3:
                            div_yield_input = st.number_input("Dividend Yield (%)", value=float(div_yield_raw), step=0.5)
                            op_margin_input = st.number_input("Op Margin (%)", value=float(op_margin_raw), step=1.0)
                            de_ratio_input = st.number_input("DER", value=float(de_ratio_raw), step=0.1)

                        col_t1, col_t2, col_t3 = st.columns(3)
                        col_t1.metric("Harga Terakhir", f"{latest_close:,.2f}")
                        col_t2.metric("MA-200", f"{latest_ma200:,.2f}")
                        col_t3.metric("RSI (14)", f"{latest_rsi:,.2f}")

                        submit_btn = st.form_submit_button("🚀 JALANKAN AUDIT 10 PILAR RIIL")

                    if submit_btn:
                        passed, failed = [], []
                        metrics = [
                            ("P1 [Valuasi] PBV", pbv_input, TACTICAL_FILTERS_RIIL['p1_pbv_max'], "x", True),
                            ("P2 [Kualitas] ROE", roe_input, TACTICAL_FILTERS_RIIL['p2_roe_min'], "%", False),
                            ("P3 [Tuas Ops] DOL", dol_input, TACTICAL_FILTERS_RIIL['p3_dol_min'], "x", False),
                            ("P4 [Siklus EV] EV/EBITDA", ev_ebitda_input, TACTICAL_FILTERS_RIIL['p4_ev_ebitda_max'], "x", True),
                            ("P5 [Bantalan Kas] Yield", div_yield_input, TACTICAL_FILTERS_RIIL['p5_div_yield_min'], "%", False),
                            ("P6 [Laba] EPS Growth", eps_g_input, TACTICAL_FILTERS_RIIL['p6_eps_growth_min'], "%", False),
                            ("P7 [Margin Ops]", op_margin_input, TACTICAL_FILTERS_RIIL['p7_op_margin_min'], "%", False),
                            ("P8 [Neraca] DER", de_ratio_input, TACTICAL_FILTERS_RIIL['p8_de_ratio_max'], "x", True)
                        ]

                        for name, val, limit, unit, is_max in metrics:
                            if is_max:
                                if 0 < val <= limit: passed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                                else: failed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                            else:
                                if val >= limit: passed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")
                                else: failed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")

                        if latest_close > latest_ma200: passed.append(f"**P9 [Tren]** Harga ({latest_close:.2f}) > MA200")
                        else: failed.append(f"**P9 [Tren]** Harga ({latest_close:.2f}) < MA200")
                        
                        if TACTICAL_FILTERS_RIIL['p10_rsi_min'] <= latest_rsi <= TACTICAL_FILTERS_RIIL['p10_rsi_max']: passed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f}")
                        else: failed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f} (Ekstrem)")

                        skor = len(passed)
                        score_col, info_col = st.columns([1, 2])
                        with score_col:
                            st.metric(label="SKOR KUALITAS TAKTIS", value=f"{skor} / 10")
                        with info_col:
                            if skor >= 7: st.success("✅ **STATUS KANDIDAT:** SANGAT DIREKOMENDASIKAN.")
                            elif skor >= 4: st.warning("⚠️ **STATUS KANDIDAT:** HOLD / PENGAMATAN.")
                            else: st.error("☠️ **STATUS KANDIDAT:** HINDARI (VALUE TRAP).")

                        res_pass, res_fail = st.columns(2)
                        with res_pass:
                            st.markdown("### ✅ PILAR YANG TERPENUHI")
                            for p in passed: st.success(p)
                        with res_fail:
                            st.markdown("### ❌ PILAR YANG GAGAL")
                            for f in failed: st.error(f)

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan pada sistem: {e}")

elif sektor_pilihan == "🎯 Taktis 1-3 Thn (Sektor Keuangan)":
    st.title("🎯 Taktis 1-3 Tahun: Sektor Keuangan")
    ticker_input = st.text_input("🔍 Masukkan Ticker Saham Bank/Asuransi (Contoh: BMRI.JK, BBCA.JK):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi data taktis untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data YFinance kosong.")
                else:
                    current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                    pbv_raw = safe_float(info.get('priceToBook', 0))
                    roe_raw = safe_float(info.get('returnOnEquity', 0)) * 100
                    roa_raw = safe_float(info.get('returnOnAssets', 0)) * 100
                    per_raw = safe_float(info.get('trailingPE', 0))
                    div_yield_raw = safe_float(info.get('dividendYield', 0)) * 100
                    eps_growth_raw = safe_float(info.get('earningsGrowth', 0)) * 100
                    rev_growth_raw = safe_float(info.get('revenueGrowth', 0)) * 100
                    net_margin_raw = safe_float(info.get('profitMargins', 0)) * 100

                    df = yf.download(ticker_input, period="1y", interval="1d", progress=False)
                    latest_close, latest_ma200, latest_rsi = current_price, 0.0, 50.0
                    
                    if not df.empty and len(df) > 50:
                        close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                        latest_close = float(close_prices.iloc[-1])
                        df['MA200'] = ta.trend.SMAIndicator(close_prices, window=200).sma_indicator()
                        latest_ma200 = float(df['MA200'].iloc[-1]) if not pd.isna(df['MA200'].iloc[-1]) else latest_close
                        df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                        latest_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0

                    st.markdown("---")
                    
                    with st.form("tactical_bank_form"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            pbv_input = st.number_input("PBV", value=float(pbv_raw), step=0.1)
                            per_input = st.number_input("PER", value=float(per_raw), step=0.5)
                            roe_input = st.number_input("ROE (%)", value=float(roe_raw), step=1.0)
                        with col2:
                            roa_input = st.number_input("ROA (%)", value=float(roa_raw), step=0.1)
                            eps_g_input = st.number_input("Pertumbuhan EPS (%)", value=float(eps_growth_raw), step=1.0)
                            rev_g_input = st.number_input("Pertumbuhan Pendapatan (%)", value=float(rev_growth_raw), step=1.0)
                        with col3:
                            div_yield_input = st.number_input("Dividend Yield (%)", value=float(div_yield_raw), step=0.5)
                            net_margin_input = st.number_input("Net Margin (%)", value=float(net_margin_raw), step=1.0)

                        col_t1, col_t2, col_t3 = st.columns(3)
                        col_t1.metric("Harga Terakhir", f"{latest_close:,.2f}")
                        col_t2.metric("MA-200", f"{latest_ma200:,.2f}")
                        col_t3.metric("RSI (14)", f"{latest_rsi:,.2f}")

                        submit_btn = st.form_submit_button("🚀 JALANKAN AUDIT TAKTIS BANK")

                    if submit_btn:
                        passed, failed = [], []
                        metrics = [
                            ("P1 [Valuasi] PBV", pbv_input, TACTICAL_FILTERS_BANK['p1_pbv_max'], "x", True),
                            ("P2 [Kualitas] ROE", roe_input, TACTICAL_FILTERS_BANK['p2_roe_min'], "%", False),
                            ("P3 [Efisiensi] ROA", roa_input, TACTICAL_FILTERS_BANK['p3_roa_min'], "%", False),
                            ("P4 [Deep Value] PER", per_input, TACTICAL_FILTERS_BANK['p4_per_max'], "x", True),
                            ("P5 [Bantalan Kas] Yield", div_yield_input, TACTICAL_FILTERS_BANK['p5_div_yield_min'], "%", False),
                            ("P6 [Laba] EPS Growth", eps_g_input, TACTICAL_FILTERS_BANK['p6_eps_growth_min'], "%", False),
                            ("P7 [Profitabilitas] Net Margin", net_margin_input, TACTICAL_FILTERS_BANK['p7_net_margin_min'], "%", False),
                            ("P8 [Top-Line] Rev Growth", rev_g_input, TACTICAL_FILTERS_BANK['p8_rev_growth_min'], "%", False)
                        ]

                        for name, val, limit, unit, is_max in metrics:
                            if is_max:
                                if 0 < val <= limit: passed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                                else: failed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                            else:
                                if val >= limit: passed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")
                                else: failed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")

                        if latest_close > latest_ma200: passed.append(f"**P9 [Tren]** Harga ({latest_close:.2f}) > MA200")
                        else: failed.append(f"**P9 [Tren]** Harga ({latest_close:.2f}) < MA200")
                        
                        if TACTICAL_FILTERS_BANK['p10_rsi_min'] <= latest_rsi <= TACTICAL_FILTERS_BANK['p10_rsi_max']: passed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f}")
                        else: failed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f} (Ekstrem)")

                        skor = len(passed)
                        score_col, info_col = st.columns([1, 2])
                        with score_col:
                            st.metric(label="SKOR KUALITAS TAKTIS", value=f"{skor} / 10")
                        with info_col:
                            if skor >= 7: st.success("✅ **STATUS KANDIDAT:** SANGAT DIREKOMENDASIKAN.")
                            elif skor >= 4: st.warning("⚠️ **STATUS KANDIDAT:** HOLD / PENGAMATAN.")
                            else: st.error("☠️ **STATUS KANDIDAT:** HINDARI (VALUE TRAP).")

                        res_pass, res_fail = st.columns(2)
                        with res_pass:
                            st.markdown("### ✅ PILAR YANG TERPENUHI")
                            for p in passed: st.success(p)
                        with res_fail:
                            st.markdown("### ❌ PILAR YANG GAGAL")
                            for f in failed: st.error(f)

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan pada sistem: {e}")
