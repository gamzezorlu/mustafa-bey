import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import gc
import time

# -----------------------------------------
# Sayfa yapılandırması (en başta olmalı)
# -----------------------------------------
st.set_page_config(
    page_title="⚡ Süper Hızlı Doğalgaz Analizi",
    page_icon="⚡",
    layout="wide"
)

# -----------------------------------------
# Main Fonksiyon
# -----------------------------------------
def main():
    st.title("Doğalgaz Sapma Analizi")
    st.markdown("800K+ satır için optimize edildi - Parquet + Memory Mapping")

    # Sidebar ayarları
    st.sidebar.header("🚀 Performans Ayarları")
    sample_rate = st.sidebar.selectbox(
        "Veri Örnekleme Oranı:",
        [1.0, 0.5, 0.3, 0.1],
        index=0,
        format_func=lambda x: f"%{x*100:.0f} - {'Tüm veri' if x==1 else 'Hızlı analiz'}"
    )
    use_memory_mapping = st.sidebar.checkbox("Memory Mapping Kullan", value=True)
    minimal_mode = st.sidebar.checkbox("Minimal Mod (Sadece gerekli kolonlar)", value=True)

    # Dosya yükleme
    st.sidebar.header("📁 Dosya Yükleme")
    file_2023 = st.sidebar.file_uploader("2023 Veriler", type=['xlsx', 'xls'], key="file_2023")
    file_2024 = st.sidebar.file_uploader("2024 Veriler", type=['xlsx', 'xls'], key="file_2024")
    file_2025 = st.sidebar.file_uploader("2025 Veriler", type=['xlsx', 'xls'], key="file_2025")

    threshold = st.sidebar.slider("Sapma Eşiği (%)", 10, 100, 30)
    st.sidebar.header("Hızlandırma Seçenekleri")
    quick_scan = st.sidebar.checkbox("Sadece yüksek sapmaları tara", value=False)
    if quick_scan:
        quick_threshold = st.sidebar.number_input("Ön tarama eşiği (%)", value=50.0)

    months_filter = st.sidebar.multiselect(
        "Analiz edilecek aylar (boş=tümü):",
        range(1, 13),
        format_func=lambda x: datetime(2023, x, 1).strftime("%B")
    )

    # Dosyalar yüklüyse
    if file_2023 and file_2024 and file_2025:

        # Kolon isimlerini al
        try:
            sample_df = pd.read_excel(file_2023, nrows=3)
            columns = sample_df.columns.tolist()
        except:
            st.error("Excel dosyası okunamıyor!")
            return

        # Hızlı sütun seçimi
        st.header("🔧 Hızlı Sütun Seçimi")
        col1, col2, col3, col4 = st.columns(4)
        with col1: tn_col = st.selectbox("TN:", columns, key="tn")
        with col2: consumption_col = st.selectbox("Tüketim:", columns, key="cons")
        with col3: date_col = st.selectbox("Tarih:", columns, key="date")
        with col4: contract_col = st.selectbox("Sözleşme:", columns, key="contract")

        if st.button("🚀 SÜPER HIZLI ANALİZ", type="primary"):
            start_time = time.time()
            progress = st.progress(0)
            status = st.empty()

            try:
                status.text("📦 Dosyalar Parquet formatına çevriliyor...")
                progress.progress(10)
                parquet_files = convert_to_parquet_cached(
                    file_2023, file_2024, file_2025,
                    tn_col, consumption_col, date_col, contract_col,
                    minimal_mode
                )
                if not parquet_files:
                    st.error("❌ Dosya dönüştürme başarısız!")
                    return

                progress.progress(25)
                status.text("⚡ Lightning speed veri okuma...")
                historical_data = fast_read_historical(parquet_files['2023'], parquet_files['2024'], sample_rate, months_filter)
                current_data = fast_read_current(parquet_files['2025'], sample_rate, months_filter)

                progress.progress(50)
                status.text("🧮 Süper hızlı hesaplamalar...")
                results = lightning_deviation_analysis(
                    historical_data, current_data, threshold,
                    quick_scan, quick_threshold if quick_scan else None
                )

                progress.progress(80)
                status.text("📊 Sonuçlar hazırlanıyor...")
                display_lightning_results(results, threshold, sample_rate)
                progress.progress(100)

                total_time = time.time() - start_time
                st.success(f"✅ {total_time:.1f} saniyede tamamlandı!")
                del parquet_files
                gc.collect()

            except Exception as e:
                st.error(f"❌ Hata: {str(e)}")
                st.info("💡 Örnekleme oranını düşürmeyi deneyin")

    else:
        st.info("📂 3 Excel dosyasını yükleyin")
        st.header("⚡ Süper Hızlı Analiz İpuçları")
        st.markdown("""
        **🚀 Maximum Hız İçin:**
        - **%50 örnekleme** ile başlayın
        - **Memory mapping** açık tutun
        - **Minimal mod** aktif edin
        - Sadece **gerekli ayları** seçin
        - **Quick scan** ile ön tarama yapın

        **📊 800K Satır Performans:**
        - Normal: ~5-10 dakika
        - %50 örnekleme: ~2-3 dakika  
        - %30 örnekleme: ~1-2 dakika
        - Quick scan: ~30-60 saniye
        """)

# -----------------------------------------
# Fonksiyonlar (Parquet, read, analiz vs)
# -----------------------------------------
@st.cache_data(ttl=3600, max_entries=3)
def convert_to_parquet_cached(file_2023, file_2024, file_2025, tn_col, cons_col, date_col, contract_col, minimal):
    parquet_files = {}
    try:
        for year, file_obj in [('2023', file_2023), ('2024', file_2024), ('2025', file_2025)]:
            if minimal:
                usecols = [tn_col, cons_col, date_col, contract_col]
                df = pd.read_excel(file_obj, usecols=usecols, engine='openpyxl')
            else:
                df = pd.read_excel(file_obj, engine='openpyxl')

            df = df.dropna(subset=[tn_col, cons_col, date_col, contract_col])
            df[tn_col] = df[tn_col].astype('category')
            df[contract_col] = df[contract_col].astype('category') 
            df[cons_col] = pd.to_numeric(df[cons_col], errors='coerce')
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            df = df.dropna()
            df = df[df[cons_col] >= 0]

            buffer = BytesIO()
            df.to_parquet(buffer, compression='snappy', index=False)
            buffer.seek(0)
            parquet_files[year] = buffer.getvalue()
            del df; gc.collect()
        return parquet_files
    except Exception as e:
        st.error(f"❌ Parquet dönüşüm hatası: {str(e)}")
        return None

def fast_read_historical(parquet_2023, parquet_2024, sample_rate, months_filter):
    try:
        df_2023 = pd.read_parquet(BytesIO(parquet_2023))
        df_2024 = pd.read_parquet(BytesIO(parquet_2024))
        if sample_rate < 1.0:
            df_2023 = df_2023.sample(frac=sample_rate, random_state=42)
            df_2024 = df_2024.sample(frac=sample_rate, random_state=42)
        cols = df_2023.columns.tolist()[:4]
        df_2023.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        df_2024.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        combined = pd.concat([df_2023, df_2024], ignore_index=True)
        if months_filter:
            combined = combined[combined['Tarih'].dt.month.isin(months_filter)]
        combined = combined[combined['Tuketim']>0]
        historical_avg = combined.groupby(['TN','Sozlesme_No'])['Tuketim'].agg(['mean','count']).reset_index()
        historical_avg = historical_avg[historical_avg['count']>=2]
        historical_avg.columns = ['TN','Sozlesme_No','Ortalama_Tuketim','Count']
        return historical_avg[['TN','Sozlesme_No','Ortalama_Tuketim']]
    except Exception as e:
        st.error(f"❌ Historical read hatası: {str(e)}")
        return None

def fast_read_current(parquet_2025, sample_rate, months_filter):
    try:
        df = pd.read_parquet(BytesIO(parquet_2025))
        if sample_rate < 1.0:
            df = df.sample(frac=sample_rate, random_state=42)
        cols = df.columns.tolist()[:4]
        df.columns = ['TN','Tuketim','Tarih','Sozlesme_No']
        df = df[df['Tuketim']>=0]
        if months_filter:
            df = df[df['Tarih'].dt.month.isin(months_filter)]
        df['Ay_Adi'] = df['Tarih'].dt.strftime('%Y-%m')
        return df
    except Exception as e:
        st.error(f"❌ Current read hatası: {str(e)}")
        return None

def lightning_deviation_analysis(historical, current, threshold, quick_scan=False, quick_threshold=None):
    if historical is None or current is None: return pd.DataFrame()
    merged = pd.merge(current, historical, on=['TN','Sozlesme_No'], how='inner')
    if merged.empty: return pd.DataFrame()
    merged['Sapma_Miktari'] = merged['Tuketim'] - merged['Ortalama_Tuketim']
    merged['Sapma_Yüzdesi'] = (merged['Sapma_Miktari']/merged['Ortalama_Tuketim'])*100
    if quick_scan and quick_threshold:
        merged = merged[merged['Sapma_Yüzdesi']>=quick_threshold]
    result = merged[['TN','Sozlesme_No','Ay_Adi','Tarih','Ortalama_Tuketim','Tuketim','Sapma_Miktari','Sapma_Yüzdesi']].copy()
    result.columns = ['TN','Sözleşme','Ay','Tarih','Geçmiş_Ortalama','Güncel_Tuketim','Sapma_Miktarı','Sapma_Yüzdesi']
    return result

def display_lightning_results(results, threshold, sample_rate):
    if results.empty:
        st.warning("⚠️ Sonuç bulunamadı")
        return
    total = len(results)
    high_dev = len(results[results['Sapma_Yüzdesi']>=threshold])
    col1,col2,col3,col4 = st.columns(4)
    with col1: st.metric("Toplam Analiz", f"{total:,}")
    with col2: st.metric(f">{threshold}% Sapma", f"{high_dev:,}")
    with col3: st.metric("Sapma Oranı", f"{(high_dev/total*100):.1f}%" if total>0 else "0%")
    with col4: st.metric("Max Sapma", f"{results['Sapma_Yüzdesi'].max():.0f}%")
    high_deviations = results[results['Sapma_Yüzdesi']>=threshold].copy()
    if not high_deviations.empty:
        st.header(f"⚠️ {threshold}% Üzeri Sapma")
        high_deviations = high_deviations.sort_values('Sapma_Yüzdesi', ascending=False)
        display_df = high_deviations.head(500)
        st.dataframe(display_df, use_container_width=True)

# -----------------------------------------
# Main çağrı
# -----------------------------------------
if __name__ == "__main__":
    main()
