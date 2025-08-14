import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime


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

if file_2023 and file_2024 and file_2025:
    # Sütun isimlerini kullanıcıdan al
    col1, col2, col3, col4 = st.columns(4)
    with col1: tn_col = st.text_input("TN Sütunu Adı", "TN")
    with col2: tuketim_col = st.text_input("Tüketim Sütunu Adı", "Tuketim")
    with col3: tarih_col = st.text_input("Tarih Sütunu Adı", "Tarih")
    with col4: sozlesme_col = st.text_input("Sözleşme No Sütunu Adı", "Sozlesme_No")

    if st.button("Analizi Başlat"):
        with st.spinner("İşleniyor..."):
            # 2023-2024 verilerini oku ve ortalamayı hesapla
            historical_avg = []
            for file in [file_2023, file_2024]:
                for chunk in pd.read_csv(file, chunksize=50000):
                    df = chunk[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
                    df.columns = ['Tesisat','Tuketim M3','Belge tarihi','Sozlesme hes.']
                    df['Tarih'] = pd.to_datetime(df['Belge tarihi'], errors='coerce')
                    df['Tuketim'] = pd.to_numeric(df['Tuketim M3'], errors='coerce')
                    df = df.dropna(subset=['Belge tarihi','Tuketim M3'])
                    df = df[df['Tuketim M3'] > 0]
                    historical_avg.append(df)

            historical_df = pd.concat(historical_avg, ignore_index=True)
            ortalama_df = historical_df.groupby(['TN','Sozlesme_No'])['Tuketim'].mean().reset_index()
            ortalama_df.columns = ['TN','Sozlesme_No','Ortalama_Tuketim']

            # 2025 verisini oku
            current_data_chunks = []
            for chunk in pd.read_csv(file_2025, chunksize=50000):
                df = chunk[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
                df.columns = ['TN','Tuketim','Tarih','Sozlesme_No']
                df['Tarih'] = pd.to_datetime(df['Tarih'], errors='coerce')
                df['Tuketim'] = pd.to_numeric(df['Tuketim'], errors='coerce')
                df = df.dropna(subset=['Tarih','Tuketim'])
                current_data_chunks.append(df)

            current_df = pd.concat(current_data_chunks, ignore_index=True)

            # Sapma analizi
            merged = current_df.merge(ortalama_df, on=['TN','Sozlesme_No'], how='inner')
            merged['Sapma_Miktarı'] = merged['Tuketim'] - merged['Ortalama_Tuketim']
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
