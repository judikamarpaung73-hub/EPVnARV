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
                    
                    # PERBAIKAN BUG DELTAGENERATOR
                    c1.markdown("**✅ Lolos**")
                    for p in passed:
                        c1.markdown(f"- {p}")
                        
                    c2.markdown("**❌ Gagal**")
                    for f in failed:
                        c2.markdown(f"- {f}")
                        
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
                    
                    # PERBAIKAN BUG DELTAGENERATOR
                    c1.markdown("**✅ Lolos**")
                    for p in passed:
                        c1.markdown(f"- {p}")
                        
                    c2.markdown("**❌ Gagal**")
                    for f in failed:
                        c2.markdown(f"- {f}")
                        
            except Exception as e: st.error(f"Eror: {e}")

# ============================================================
# MODUL 3: STRATEGI TAKTIS 1-3 TAHUN
# ============================================================
elif sektor_pilihan == "🎯 Strategi Taktis (1-3 Tahun)":
    st.sidebar.info(
        "**Arsitektur 1-3 Tahun:**\n\n"
        "Mesin mendeteksi Deep Value, Katalis Fiskal, Siklus Komoditas, dan Bantalan Kas berdasarkan sub-sektor."
    )
    st.title("🎯 Mesin Audit 10 Pilar Taktis (1-3 Tahun)")
    
    taktis_tipe = st.radio("Pilih Kategori Emiten:", ["Sektor Riil", "Sektor Keuangan (Perbankan/Asuransi)"])
    ticker_input = st.text_input("🔍 Masukkan Ticker Saham (Contoh: BMRI.JK, JPFA.JK):", "").upper()

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
                    div_yield_raw = safe_float(info.get('dividendYield', 0)) * 100
                    eps_growth_raw = safe_float(info.get('earningsGrowth', 0)) * 100
                    rev_growth_raw = safe_float(info.get('revenueGrowth', 0)) * 100
                    
                    df = yf.download(ticker_input, period="1y", interval="1d", progress=False)
                    latest_close, latest_ma200, latest_rsi = current_price, 0.0, 50.0
                    
                    if not df.empty and len(df) > 50:
                        close_prices = df['Close'].squeeze() if isinstance(df.columns, pd.MultiIndex) else df['Close']
                        latest_close = float(close_prices.iloc[-1])
                        df['MA200'] = ta.trend.SMAIndicator(close_prices, window=200).sma_indicator()
                        latest_ma200 = float(df['MA200'].iloc[-1]) if not pd.isna(df['MA200'].iloc[-1]) else latest_close
                        df['RSI'] = ta.momentum.RSIIndicator(close_prices, window=14).rsi()
                        latest_rsi = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0

                    if taktis_tipe == "Sektor Riil":
                        ev_ebitda_raw = safe_float(info.get('enterpriseToEbitda', 0))
                        op_margin_raw = safe_float(info.get('operatingMargins', 0)) * 100
                        raw_de = safe_float(info.get('debtToEquity', 0))
                        de_ratio_raw = raw_de / 100 if raw_de > 0 else 0.0
                        
                        earn_g_decimal = safe_float(info.get('earningsGrowth', 0))
                        rev_g_decimal = safe_float(info.get('revenueGrowth', 0))
                        dol_raw = (earn_g_decimal / rev_g_decimal) if rev_g_decimal > 0 else 0.0

                        with st.form("tactical_riil_form"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                pbv_input = st.number_input("PBV (Price to Book)", value=float(pbv_raw), step=0.1)
                                roe_input = st.number_input("ROE (%)", value=float(roe_raw), step=1.0)
                                ev_ebitda_input = st.number_input("EV / EBITDA", value=float(ev_ebitda_raw), step=0.5)
                            with col2:
                                eps_g_input = st.number_input("Pertumbuhan EPS (%)", value=float(eps_growth_raw), step=1.0)
                                rev_g_input = st.number_input("Pertumbuhan Pendapatan (%)", value=float(rev_growth_raw), step=1.0)
                                dol_input = st.number_input("DOL (Degree of Op Leverage)", value=float(dol_raw), step=0.1)
                            with col3:
                                div_yield_input = st.number_input("Dividend Yield (%)", value=float(div_yield_raw), step=0.5)
                                op_margin_input = st.number_input("Operating Margin (%)", value=float(op_margin_raw), step=1.0)
                                de_ratio_input = st.number_input("DER", value=float(de_ratio_raw), step=0.1)
                            submit_btn = st.form_submit_button("🚀 JALANKAN AUDIT 10 PILAR RIIL")

                        if submit_btn:
                            passed, failed = [], []
                            
                            metrics = [
                                ("P1 [Valuasi] PBV", pbv_input, TACTICAL_FILTERS['p1_pbv_max'], "x", True),
                                ("P2 [Kualitas] ROE", roe_input, TACTICAL_FILTERS['p2_roe_min'], "%", False),
                                ("P3 [Tuas Ops] DOL", dol_input, TACTICAL_FILTERS['p3_dol_min'], "x", False),
                                ("P4 [Siklus EV] EV/EBITDA", ev_ebitda_input, TACTICAL_FILTERS['p4_ev_ebitda_max'], "x", True),
                                ("P5 [Bantalan Kas] Yield", div_yield_input, TACTICAL_FILTERS['p5_div_yield_min'], "%", False),
                                ("P6 [Laba] EPS Growth", eps_g_input, TACTICAL_FILTERS['p6_eps_growth_min'], "%", False),
                                ("P7 [Margin Ops]", op_margin_input, TACTICAL_FILTERS['p7_op_margin_min'], "%", False),
                                ("P8 [Neraca] DER", de_ratio_input, TACTICAL_FILTERS['p8_de_ratio_max'], "x", True)
                            ]

                            for name, val, limit, unit, is_max in metrics:
                                if is_max:
                                    if 0 < val <= limit: passed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                                    else: failed.append(f"**{name}** {val:.2f}{unit} (Maks {limit}{unit})")
                                else:
                                    if val >= limit: passed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")
                                    else: failed.append(f"**{name}** {val:.2f}{unit} (Min {limit}{unit})")

                            if latest_close > latest_ma200: passed.append(f"**P9 [Tren]** Harga > MA200")
                            else: failed.append(f"**P9 [Tren]** Harga < MA200")
                            if TACTICAL_FILTERS['p10_rsi_min'] <= latest_rsi <= TACTICAL_FILTERS['p10_rsi_max']: passed.append(f"**P10 [RSI]** {latest_rsi:.2f}")
                            else: failed.append(f"**P10 [RSI]** {latest_rsi:.2f} (Ekstrem)")

                            skor = len(passed)
                            st.metric("SKOR TAKTIS RIIL", f"{skor} / 10")
                            res_pass, res_fail = st.columns(2)
                            with res_pass:
                                for p in passed: st.success(p)
                            with res_fail:
                                for f in failed: st.error(f)

                    elif taktis_tipe == "Sektor Keuangan (Perbankan/Asuransi)":
                        roa_raw = safe_float(info.get('returnOnAssets', 0)) * 100
                        per_raw = safe_float(info.get('trailingPE', 0))
                        net_margin_raw = safe_float(info.get('profitMargins', 0)) * 100

                        with st.form("tactical_bank_form"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                pbv_input = st.number_input("PBV (Price to Book)", value=float(pbv_raw), step=0.1)
                                per_input = st.number_input("PER (Price to Earnings)", value=float(per_raw), step=0.5)
                                roe_input = st.number_input("ROE (%)", value=float(roe_raw), step=1.0)
                            with col2:
                                roa_input = st.number_input("ROA (%)", value=float(roa_raw), step=0.1)
                                eps_g_input = st.number_input("Pertumbuhan EPS (%)", value=float(eps_growth_raw), step=1.0)
                                rev_g_input = st.number_input("Pertumbuhan Pendapatan (%)", value=float(rev_growth_raw), step=1.0)
                            with col3:
                                div_yield_input = st.number_input("Dividend Yield (%)", value=float(div_yield_raw), step=0.5)
                                net_margin_input = st.number_input("Net Profit Margin (%)", value=float(net_margin_raw), step=1.0)
                            submit_btn = st.form_submit_button("🚀 JALANKAN AUDIT 10 PILAR FINANSIAL")

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

                            if latest_close > latest_ma200: passed.append(f"**P9 [Tren]** Harga > MA200")
                            else: failed.append(f"**P9 [Tren]** Harga < MA200")
                            if TACTICAL_FILTERS_BANK['p10_rsi_min'] <= latest_rsi <= TACTICAL_FILTERS_BANK['p10_rsi_max']: passed.append(f"**P10 [RSI]** {latest_rsi:.2f}")
                            else: failed.append(f"**P10 [RSI]** {latest_rsi:.2f} (Ekstrem)")

                            skor = len(passed)
                            st.metric("SKOR TAKTIS FINANSIAL", f"{skor} / 10")
                            res_pass, res_fail = st.columns(2)
                            with res_pass:
                                for p in passed: st.success(p)
                            with res_fail:
                                for f in failed: st.error(f)
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan pada sistem: {e}")
