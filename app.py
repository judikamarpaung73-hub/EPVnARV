import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import numpy as np

# ============================================================
# KONFIGURASI HALAMAN (Hanya dipanggil sekali)
# ============================================================
st.set_page_config(page_title="Mesin Audit Institusional", layout="wide", page_icon="📈")

# ============================================================
# PARAMETER FILTER (GLOBAL)
# ============================================================
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

TACTICAL_FILTERS = {
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

def safe_float(val, default=0.0):
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except:
        return default

# ============================================================
# NAVIGASI SIDEBAR
# ============================================================
st.sidebar.title("🛡️ Panel Kendali Algoritma")
sektor_pilihan = st.sidebar.radio(
    "Pilih Modul Audit:",
    ["🏭 Sektor Riil (EPV & ARV)", 
     "🏦 Sektor Keuangan (Justified PBV)", 
     "🎯 Strategi Taktis (1-3 Tahun)"]
)
st.sidebar.markdown("---")

# ============================================================
# MODUL 1: SEKTOR RIIL
# ============================================================
if sektor_pilihan == "🏭 Sektor Riil (EPV & ARV)":
    st.sidebar.info("Modul Valuasi Jangka Panjang: Menggunakan kapasitas Arus Kas Bebas (FCF) tanpa pertumbuhan dan biaya reproduksi aset.")
    st.title("🏭 Sektor Riil: Auditing EPV & ARV")
    ticker_input = st.text_input("Masukkan Ticker (Contoh: META, UNVR.JK):", "").upper()

    if ticker_input:
        with st.spinner("Mengekstraksi data..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                shares_raw = safe_float(info.get('sharesOutstanding', 0))
                eps_raw = safe_float(info.get('trailingEps', 0))
                market_cap = safe_float(info.get('marketCap', 1))

                fcf_raw = 0.0
                cf = stock.cash_flow
                if cf is not None and not cf.empty and 'Free Cash Flow' in cf.index:
                    fcf_raw = float(cf.loc['Free Cash Flow'].dropna().head(3).mean())
                if fcf_raw == 0.0: fcf_raw = safe_float(info.get('freeCashflow', 0))

                bs = stock.balance_sheet
                equity_raw = float(bs.loc['Stockholders Equity'].iloc[0]) if bs is not None and not bs.empty and 'Stockholders Equity' in bs.index else 0.0
                inc = stock.financials
                sga_raw = float(inc.loc['Selling General And Administration'].dropna().head(3).sum()) if inc is not None and not inc.empty and 'Selling General And Administration' in inc.index else 0.0
                rd_raw = float(inc.loc['Research And Development'].dropna().head(5).sum()) if inc is not None and not inc.empty and 'Research And Development' in inc.index else 0.0

                with st.form("riil_form"):
                    col_a, col_b = st.columns(2)
                    fcf_input = col_a.number_input("FCF", value=fcf_raw)
                    eps_input = col_a.number_input("EPS", value=eps_raw)
                    shares_input = col_a.number_input("Saham Beredar", value=shares_raw)
                    equity_input = col_b.number_input("Ekuitas", value=equity_raw)
                    rd_input = col_b.number_input("R&D", value=rd_raw)
                    sga_input = col_b.number_input("SG&A", value=sga_raw)
                    submit_btn = st.form_submit_button("Analisis Sektor Riil")

                if submit_btn and shares_input > 0:
                    eps_fcf = fcf_input / shares_input if fcf_input > 0 else eps_input
                    harga_wajar = (eps_fcf * 15) if (eps_fcf * 15) - ((equity_input + rd_input + sga_input) / shares_input) > 0 else min((eps_fcf * 15), ((equity_input + rd_input + sga_input) / shares_input))
                    
                    st.metric("Harga Pasar", f"{current_price:,.2f}")
                    st.metric("Harga Wajar (Fair Value)", f"{harga_wajar:,.2f}")
                    
                    passed, failed = [], []
                    net_income = safe_float(info.get('netIncomeToCommon', 1))
                    cash_conv = (fcf_input / net_income) * 100 if net_income > 0 else 0
                    debt_ebitda = safe_float(info.get('debtToEbitda', 0))
                    
                    ebitda = safe_float(info.get('ebitda', 0))
                    int_exp = safe_float(info.get('interestExpense', 1))
                    int_cover = abs(ebitda / int_exp) if int_exp != 0 else 999
                    fcf_yield = (fcf_input / market_cap) * 100 if market_cap > 0 else 0
                    
                    gross_m = safe_float(info.get('grossMargins', 0)) * 100
                    op_m = safe_float(info.get('operatingMargins', 0)) * 100
                    roe_val = safe_float(info.get('returnOnEquity', 0)) * 100
                    
                    metrics = [
                        ("P3 (Margin)", (gross_m + op_m)/2, 27.5, "%"),
                        ("P4 (ROIC)", roe_val, FILTERS_RIIL['roic_min'], "%"),
                        ("P5 (Cash Conv)", cash_conv, FILTERS_RIIL['cash_conversion_min'], "%"),
                        ("P5 (Debt/EBITDA)", debt_ebitda, FILTERS_RIIL['net_debt_ebitda_max'], "x"),
                        ("P10 (FCF Yield)", fcf_yield, 5.0, "%")
                    ]
                    
                    for l, v, m, u in metrics:
                        if (l == "P5 (Debt/EBITDA)" and v <= m) or (l != "P5 (Debt/EBITDA)" and v >= m):
                            passed.append(f"{l}: {v:.1f}{u} (Min: {m}{u})")
                        else: failed.append(f"{l}: {v:.1f}{u} (Min: {m}{u})")
                    
                    st.markdown("### 🛡️ Pilar Riil")
                    c1, c2 = st.columns(2)
                    c1.markdown("**✅ Lolos**"); [c1.markdown(f"- {p}") for p in passed]
                    c2.markdown("**❌ Gagal**"); [c2.markdown(f"- {f}") for f in failed]
            except Exception as e: st.error(f"Eror: {e}")

# ============================================================
# MODUL 2: SEKTOR KEUANGAN
# ============================================================
elif sektor_pilihan == "🏦 Sektor Keuangan (Justified PBV)":
    st.sidebar.info("Modul Khusus Bank & Asuransi: Menggunakan korelasi antara Return on Equity (ROE), Suku Bunga Diskonto, dan Nilai Buku Per Lembar Saham.")
    st.title("🏦 Sektor Keuangan: Auditing")
    ticker_input = st.text_input("Masukkan Ticker (Contoh: BBCA.JK):", "").upper()

    if ticker_input:
        with st.spinner("Mengekstraksi data..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                current_price = safe_float(info.get('currentPrice', info.get('previousClose', 0)))
                bvps = safe_float(info.get('bookValue', 0))
                roe = safe_float(info.get('returnOnEquity', 0)) * 100
                roa = safe_float(info.get('returnOnAssets', 0)) * 100
                
                with st.form("bank_form"):
                    col_c, col_d = st.columns(2)
                    bvps_i = col_c.number_input("BVPS", value=bvps)
                    roe_i = col_c.number_input("ROE (%)", value=roe)
                    ke_i = col_d.number_input("Cost of Equity (%)", value=11.0)
                    g_i = col_d.number_input("Growth (%)", value=6.0)
                    submit_bank = st.form_submit_button("Analisis Bank")

                if submit_bank and ke_i > g_i:
                    pbv = (roe_i/100 - g_i/100) / (ke_i/100 - g_i/100)
                    st.metric("Harga Pasar", f"{current_price:,.2f}")
                    st.metric("Harga Wajar (Justified PBV)", f"{pbv * bvps_i:,.2f}")
                    
                    passed, failed = [], []
                    market_pbv = current_price / bvps_i if bvps_i > 0 else 0
                    
                    bank_metrics = [
                        ("P3 (ROE)", roe_i, FILTERS_KEUANGAN['roe_min'], "%"),
                        ("P4 (ROA)", roa, FILTERS_KEUANGAN['roa_min'], "%"),
                        ("P5 (PBV vs Fair)", market_pbv, pbv, "x")
                    ]
                    
                    for l, v, m, u in bank_metrics:
                        if ("PBV" in l and v <= m) or (not "PBV" in l and v >= m):
                            passed.append(f"{l}: {v:.2f}{u} (Min: {m:.2f}{u})")
                        else: failed.append(f"{l}: {v:.2f}{u} (Min: {m:.2f}{u})")
                        
                    st.markdown("### 🛡️ Pilar Finansial")
                    c1, c2 = st.columns(2)
                    c1.markdown("**✅ Lolos**"); [c1.markdown(f"- {p}") for p in passed]
                    c2.markdown("**❌ Gagal**"); [c2.markdown(f"- {f}") for f in failed]
            except Exception as e: st.error(f"Eror: {e}")

# ============================================================
# MODUL 3: STRATEGI TAKTIS 1-3 TAHUN
# ============================================================
elif sektor_pilihan == "🎯 Strategi Taktis (1-3 Tahun)":
    st.sidebar.info(
        "**Arsitektur 1-3 Tahun:**\n\n"
        "Mesin ini menggunakan 10 Pilar Taktis untuk mendeteksi:\n"
        "1. **Deep Value** (Perbankan/Properti)\n"
        "2. **Katalis Fiskal / MBG** (Tuas Operasional)\n"
        "3. **Siklus AI & HPM** (Valuasi Logam)\n"
        "4. **Bantalan Kas** (Obligasi Sintetis)\n\n"
        "Berlaku untuk semua sektor."
    )
    st.title("🎯 Mesin Audit 10 Pilar Taktis (1-3 Tahun)")
    st.write("Sistem ekstraksi data fundamental & teknikal dengan fitur koreksi data manual (Override).")

    ticker_input = st.text_input("🔍 Masukkan Ticker Saham (Contoh: BMRI.JK, JPFA.JK, AMMN.JK, AAPL):", "").upper()

    if ticker_input:
        with st.spinner(f"Mengekstraksi data fundamental dan teknikal untuk {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
                    st.error("⚠️ Emiten tidak ditemukan atau data YFinance kosong.")
                else:
                    # --- EKSTRAKSI DATA FUNDAMENTAL MENTAH ---
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

                    # --- EKSTRAKSI DATA TEKNIKAL ---
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
                    
                    st.info("💡 **Tinjau dan Koreksi Data:** Data di bawah ditarik dari sistem. Anda dapat mengedit angkanya secara manual jika Laporan Keuangan terbaru belum di-*update* oleh Yahoo Finance.")
                    
                    with st.form("tactical_override_form"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**1. Valuasi & Laba**")
                            pbv_input = st.number_input("PBV (Price to Book)", value=float(pbv_raw), step=0.1)
                            roe_input = st.number_input("ROE (%)", value=float(roe_raw), step=1.0)
                            ev_ebitda_input = st.number_input("EV / EBITDA", value=float(ev_ebitda_raw), step=0.5)
                            
                        with col2:
                            st.markdown("**2. Tuas Ops & Efisiensi**")
                            eps_g_input = st.number_input("Pertumbuhan EPS (%)", value=float(eps_growth_raw), step=1.0)
                            rev_g_input = st.number_input("Pertumbuhan Pendapatan (%)", value=float(rev_growth_raw), step=1.0)
                            dol_input = st.number_input("DOL (Degree of Op Leverage)", value=float(dol_raw), step=0.1, help="Berapa kali lipat EPS tumbuh dibanding Pendapatan.")
                            
                        with col3:
                            st.markdown("**3. Keamanan & Neraca**")
                            div_yield_input = st.number_input("Dividend Yield (%)", value=float(div_yield_raw), step=0.5)
                            op_margin_input = st.number_input("Operating Margin (%)", value=float(op_margin_raw), step=1.0)
                            de_ratio_input = st.number_input("Rasio Hutang / Ekuitas (DER)", value=float(de_ratio_raw), step=0.1)

                        st.markdown("**Data Teknikal (Statik)**")
                        col_t1, col_t2, col_t3 = st.columns(3)
                        col_t1.metric("Harga Terakhir", f"{latest_close:,.2f}")
                        col_t2.metric("MA-200", f"{latest_ma200:,.2f}")
                        col_t3.metric("RSI (14)", f"{latest_rsi:,.2f}")

                        submit_btn = st.form_submit_button("🚀 JALANKAN AUDIT 10 PILAR")

                    if submit_btn:
                        st.markdown("---")
                        st.markdown(f"### 🛡️ Laporan Audit Taktis: {ticker_input}")
                        
                        passed = []
                        failed = []

                        # PILAR 1: Deep Value
                        if pbv_input <= TACTICAL_FILTERS['p1_pbv_max'] and pbv_input > 0:
                            passed.append(f"**P1 [UTAMA: Valuasi]** PBV {pbv_input:.2f}x (Syarat: Maks {TACTICAL_FILTERS['p1_pbv_max']}x)")
                        else:
                            failed.append(f"**P1 [UTAMA: Valuasi]** PBV {pbv_input:.2f}x (Gagal: Terlalu Mahal / Negatif)")

                        # PILAR 2: Kualitas Fundamental
                        if roe_input >= TACTICAL_FILTERS['p2_roe_min']:
                            passed.append(f"**P2 [UTAMA: Kualitas]** ROE {roe_input:.2f}% (Syarat: Min {TACTICAL_FILTERS['p2_roe_min']}%)")
                        else:
                            failed.append(f"**P2 [UTAMA: Kualitas]** ROE {roe_input:.2f}% (Gagal: Di bawah standar)")

                        # PILAR 3: Tuas Operasional (Katalis Fiskal / MBG)
                        if dol_input >= TACTICAL_FILTERS['p3_dol_min'] and eps_g_input > 0:
                            passed.append(f"**P3 [UTAMA: Tuas Ops]** DOL {dol_input:.2f}x (Syarat: Min {TACTICAL_FILTERS['p3_dol_min']}x)")
                        else:
                            failed.append(f"**P3 [UTAMA: Tuas Ops]** DOL {dol_input:.2f}x (Gagal: Tuas lemah / Laba Minus)")

                        # PILAR 4: Valuasi EV / Logam AI
                        if 0 < ev_ebitda_input <= TACTICAL_FILTERS['p4_ev_ebitda_max']:
                            passed.append(f"**P4 [UTAMA: Siklus EV]** EV/EBITDA {ev_ebitda_input:.2f}x (Syarat: Maks {TACTICAL_FILTERS['p4_ev_ebitda_max']}x)")
                        else:
                            failed.append(f"**P4 [UTAMA: Siklus EV]** EV/EBITDA {ev_ebitda_input:.2f}x (Gagal: Valuasi mahal / Negatif)")

                        # PILAR 5: Bantalan Kas (Obligasi Sintetis)
                        if div_yield_input >= TACTICAL_FILTERS['p5_div_yield_min']:
                            passed.append(f"**P5 [Bantalan Kas]** Yield {div_yield_input:.2f}% (Syarat: Min {TACTICAL_FILTERS['p5_div_yield_min']}%)")
                        else:
                            failed.append(f"**P5 [Bantalan Kas]** Yield {div_yield_input:.2f}% (Gagal: Yield rendah)")

                        # PILAR 6: Pertumbuhan Laba
                        if eps_g_input >= TACTICAL_FILTERS['p6_eps_growth_min']:
                            passed.append(f"**P6 [Pertumbuhan Laba]** EPS Tumbuh {eps_g_input:.2f}% (Syarat: Min {TACTICAL_FILTERS['p6_eps_growth_min']}%)")
                        else:
                            failed.append(f"**P6 [Pertumbuhan Laba]** EPS Tumbuh {eps_g_input:.2f}% (Gagal: Laba lambat/turun)")

                        # PILAR 7: Margin Operasional
                        if op_margin_input >= TACTICAL_FILTERS['p7_op_margin_min']:
                            passed.append(f"**P7 [Margin Ops]** Margin {op_margin_input:.2f}% (Syarat: Min {TACTICAL_FILTERS['p7_op_margin_min']}%)")
                        else:
                            failed.append(f"**P7 [Margin Ops]** Margin {op_margin_input:.2f}% (Gagal: Margin tipis)")

                        # PILAR 8: Kesehatan Neraca
                        if de_ratio_input <= TACTICAL_FILTERS['p8_de_ratio_max']:
                            passed.append(f"**P8 [Kesehatan Neraca]** DER {de_ratio_input:.2f}x (Syarat: Maks {TACTICAL_FILTERS['p8_de_ratio_max']}x)")
                        else:
                            failed.append(f"**P8 [Kesehatan Neraca]** DER {de_ratio_input:.2f}x (Gagal: Banyak Utang)")

                        # PILAR 9: Konfirmasi Tren Teknikal
                        if latest_close > latest_ma200:
                            passed.append(f"**P9 [Konfirmasi Tren]** Harga ({latest_close:.2f}) di atas MA200 ({latest_ma200:.2f})")
                        else:
                            failed.append(f"**P9 [Konfirmasi Tren]** Harga ({latest_close:.2f}) di bawah MA200 (AWAS: Pisau Jatuh)")

                        # PILAR 10: Momentum RSI
                        if TACTICAL_FILTERS['p10_rsi_min'] <= latest_rsi <= TACTICAL_FILTERS['p10_rsi_max']:
                            passed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f} (Status: Netral/Aman)")
                        else:
                            failed.append(f"**P10 [Momentum]** RSI {latest_rsi:.2f} (Gagal: Oversold / Overbought Ekstrem)")

                        # --- HASIL SKORING ---
                        skor = len(passed)
                        
                        score_col, info_col = st.columns([1, 2])
                        with score_col:
                            st.metric(label="SKOR KUALITAS TAKTIS", value=f"{skor} / 10")
                        with info_col:
                            if skor >= 7:
                                st.success("✅ **STATUS KANDIDAT:** SANGAT DIREKOMENDASIKAN. Memiliki dislokasi makro yang tervalidasi fundamental.")
                            elif skor >= 4:
                                st.warning("⚠️ **STATUS KANDIDAT:** HOLD / PENGAMATAN. Harus masuk ke salah satu dari 4 Pilar Utama agar layak beli.")
                            else:
                                st.error("☠️ **STATUS KANDIDAT:** HINDARI (VALUE TRAP).")

                        st.markdown("<br>", unsafe_allow_html=True)
                        res_pass, res_fail = st.columns(2)
                        
                        with res_pass:
                            st.markdown("### ✅ PILAR YANG TERPENUHI")
                            for p in passed:
                                st.success(p)
                                
                        with res_fail:
                            st.markdown("### ❌ PILAR YANG GAGAL")
                            for f in failed:
                                st.error(f)

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan pada sistem: {e}")
