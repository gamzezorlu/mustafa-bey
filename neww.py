import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(
    page_title="Doğalgaz Sapma Analizi",
    layout="wide"
)

st.title("Doğalgaz Tüketim Sapma Analizi (CSV)")

# CSV yükleme
file_2023 = st.sidebar.file_uploader("2023 Verisi (CSV)", type=['csv'])
file_2024 = st.sidebar.file_uploader("2024 Verisi (CSV)", type=['csv'])
file_2025 = st.sidebar.file_uploader("2025 Verisi (CSV)", type=['csv'])

threshold = st.sidebar.slider("Sapma Eşiği (%)", min_value=10, max_value=100, value=30)

# Tüm dosyalar yüklendiyse
if file_2023 and file_2024 and file_2025:
    # Sütun adlarını ilk dosyadan al
    sample_df = pd.read_csv(file_2023, nrows=1)
    sample_df.columns = sample_df.columns.str.strip()
    col_names = sample_df.columns.tolist()

    st.subheader("Sütun Eşleştirme")
    col1, col2, col3, col4 = st.columns(4)
    with col1: tn_col = st.selectbox("TN Sütunu", col_names, index=col_names.index("Tesisat") if "Tesisat" in col_names else 0)
    with col2: tuketim_col = st.selectbox("Tüketim Sütunu", col_names, index=col_names.index("Tuketim M3") if "Tuketim M3" in col_names else 0)
    with col3: tarih_col = st.selectbox("Tarih Sütunu", col_names, index=col_names.index("Belge tarihi") if "Belge tarihi" in col_names else 0)
    with col4: sozlesme_col = st.selectbox("Sözleşme No Sütunu", col_names, index=col_names.index("Sozlesme hes.") if "Sozlesme hes." in col_names else 0)

    if st.button("Analizi Başlat"):
        with st.spinner("İşleniyor..."):

            def read_and_validate(file):
                """CSV dosyasını okuyup gerekli sütunları seçer"""
                chunks_list = []
                for chunk in pd.read_csv(file, chunksize=50000):
                    chunk.columns = chunk.columns.str.strip()
                    df = chunk[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
                    chunks_list.append(df)
                return pd.concat(chunks_list, ignore_index=True)

            # 2023-2024 ortalama tüketim hesaplama
            historical_avg = []
            for file in [file_2023, file_2024]:
                df = read_and_validate(file)
                df.columns = ['Tesisat', 'Tuketim M3', 'Belge tarihi', 'Sozlesme hes.']
                df['Belge tarihi'] = pd.to_datetime(df['Belge tarihi'], errors='coerce')
                df['Tuketim M3'] = pd.to_numeric(df['Tuketim M3'], errors='coerce')
                df = df.dropna(subset=['Belge tarihi', 'Tuketim M3'])
                df = df[df['Tuketim M3'] > 0]
                historical_avg.append(df)

            historical_df = pd.concat(historical_avg, ignore_index=True)
            ortalama_df = historical_df.groupby(['Tesisat', 'Sozlesme hes.'])['Tuketim M3'].mean().reset_index()
            ortalama_df.columns = ['Tesisat', 'Sozlesme hes.', 'Ortalama_Tuketim']

            # 2025 verisi
            current_df = read_and_validate(file_2025)
            current_df.columns = ['Tesisat', 'Tuketim M3', 'Belge tarihi', 'Sozlesme hes.']
            current_df['Belge tarihi'] = pd.to_datetime(current_df['Belge tarihi'], errors='coerce')
            current_df['Tuketim M3'] = pd.to_numeric(current_df['Tuketim M3'], errors='coerce')
            current_df = current_df.dropna(subset=['Belge tarihi', 'Tuketim M3'])

            # Sapma analizi
            merged = current_df.merge(ortalama_df, on=['Tesisat', 'Sozlesme hes.'], how='inner')
            merged['Sapma_Miktarı'] = merged['Tuketim M3'] - merged['Ortalama_Tuketim']
            merged['Sapma_Yüzdesi'] = (merged['Sapma_Miktarı'] / merged['Ortalama_Tuketim']) * 100
            sonuc = merged[merged['Sapma_Yüzdesi'] > threshold]

            # CSV olarak indir
            output = BytesIO()
            sonuc.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)

            st.success("Analiz tamamlandı!")
            st.download_button(
                label="Sonucu CSV olarak indir",
                data=output,
                file_name="sapma_sonuclari.csv",
                mime="text/csv"
            )
else:
    st.info("Lütfen 2023, 2024 ve 2025 CSV dosyalarını yükleyin.")
