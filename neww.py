import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

def main():
    st.title("Doğalgaz Tüketim Sapma Analizi")
    st.markdown("2023-2024 ortalamasından %30 fazla sapma gösteren tesisatları tespit edin")

    st.sidebar.header("Excel Dosyalarını Yükleyin")
    file_2023 = st.sidebar.file_uploader("2023 Veriler", type=['xlsx', 'xls'], key="file_2023")
    file_2024 = st.sidebar.file_uploader("2024 Veriler", type=['xlsx', 'xls'], key="file_2024")
    file_2025 = st.sidebar.file_uploader("2025 Güncel Veriler", type=['xlsx', 'xls'], key="file_2025")

    threshold = st.sidebar.slider("Sapma Eşiği (%)", min_value=10, max_value=100, value=30)

    if file_2023 and file_2024 and file_2025:
        try:
            df_2023 = pd.read_excel(file_2023)
            df_2024 = pd.read_excel(file_2024)
            df_2025 = pd.read_excel(file_2025)
            st.success("✅ Tüm dosyalar yüklendi!")

            # Sütun eşleştirmesi
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                tn_col = st.selectbox("TN Sütunu:", df_2023.columns.tolist())
            with col2:
                tuketim_col = st.selectbox("Tüketim Sütunu:", df_2023.columns.tolist())
            with col3:
                tarih_col = st.selectbox("Tarih Sütunu:", df_2023.columns.tolist())
            with col4:
                sozlesme_col = st.selectbox("Sözleşme No Sütunu:", df_2023.columns.tolist())

            if st.button("🔍 Sapma Analizini Başlat", type="primary"):
                with st.spinner("Analiz yapılıyor..."):
                    historical_avg = calculate_historical_average_separate(df_2023, df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col)
                    current_data = prepare_current_data(df_2025, tn_col, tuketim_col, tarih_col, sozlesme_col)
                    deviation_results = analyze_deviations(historical_avg, current_data, threshold)

                    if deviation_results is not None and not deviation_results.empty:
                        st.success("✅ Analiz tamamlandı!")

                        total_compared = len(deviation_results)
                        high_deviation = len(deviation_results[deviation_results['Sapma_Yüzdesi'] >= threshold])

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Karşılaştırılan Tesisat", f"{total_compared}")
                        col2.metric(f">{threshold}% Sapma Gösteren", f"{high_deviation}")
                        col3.metric("Oran", f"{high_deviation/total_compared*100:.1f}%" if total_compared > 0 else "0%")

                        high_devs = deviation_results[deviation_results['Sapma_Yüzdesi'] >= threshold].copy()
                        if not high_devs.empty:
                            st.header(f"⚠️ {threshold}% Üzeri Sapma Gösteren Tesisatlar")
                            display_df = format_display_table(high_devs.sort_values('Sapma_Yüzdesi', ascending=False))
                            st.dataframe(display_df, use_container_width=True, hide_index=True)

                            excel_data = create_deviation_report(high_devs, threshold)
                            st.download_button(
                                label="📥 Sapma Raporunu Excel Olarak İndir",
                                data=excel_data,
                                file_name=f"sapma_raporu_{threshold}pct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                type="primary"
                            )
                        else:
                            st.success(f"🎉 {threshold}% üzeri sapma gösteren tesisat bulunmamaktadır!")
                    else:
                        st.error("❌ Veri analizi sırasında hata oluştu.")

        except Exception as e:
            st.error(f"❌ Hata: {str(e)}")
    else:
        st.info("📂 2023, 2024 ve 2025 Excel dosyalarını yükleyin.")

def clean_data(df, tn_col, tuketim_col, tarih_col, sozlesme_col, expected_year):
    df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
    df_clean.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
    df_clean = df_clean.dropna()
    df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Tarih'])
    df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Tuketim'])
    df_clean = df_clean[df_clean['Tarih'].dt.year == expected_year]
    df_clean = df_clean[df_clean['Tuketim'] > 0]
    df_clean['TN'] = df_clean['TN'].astype(str).str.strip()
    df_clean['Sozlesme_No'] = df_clean['Sozlesme_No'].astype(str).str.strip()
    return df_clean if not df_clean.empty else None

def calculate_historical_average_separate(df_2023, df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col):
    df_2023_clean = clean_data(df_2023, tn_col, tuketim_col, tarih_col, sozlesme_col, 2023)
    df_2024_clean = clean_data(df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col, 2024)
    if df_2023_clean is None or df_2024_clean is None:
        return None
    combined = pd.concat([df_2023_clean, df_2024_clean], ignore_index=True)
    monthly_avg = combined.groupby(['TN','Sozlesme_No'])['Tuketim'].mean().reset_index()
    monthly_avg.columns = ['TN','Sozlesme_No','Ortalama_Tuketim']
    return monthly_avg

def prepare_current_data(df, tn_col, tuketim_col, tarih_col, sozlesme_col):
    df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
    df_clean.columns = ['TN','Tuketim','Tarih','Sozlesme_No']
    df_clean = df_clean.dropna()
    df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Tarih'])
    df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Tuketim'])
    df_clean = df_clean[df_clean['Tarih'].dt.year == 2025]
    df_clean = df_clean[df_clean['Tuketim'] >= 0]
    df_clean['TN'] = df_clean['TN'].astype(str).str.strip()
    df_clean['Sozlesme_No'] = df_clean['Sozlesme_No'].astype(str).str.strip()
    df_clean['Ay'] = df_clean['Tarih'].dt.month
    df_clean['Ay_Adi'] = df_clean['Tarih'].dt.strftime('%Y-%m')
    return df_clean

def analyze_deviations(historical_avg, current_data, threshold):
    merged = current_data.merge(historical_avg, on=['TN','Sozlesme_No'], how='inner')
    merged['Sapma_Miktarı'] = merged['Tuketim'] - merged['Ortalama_Tuketim']
    merged['Sapma_Yüzdesi'] = (merged['Sapma_Miktarı']/merged['Ortalama_Tuketim'])*100
    return merged

def format_display_table(df):
    display_df = df.copy()
    display_df['Geçmiş_Ortalama'] = display_df['Ortalama_Tuketim'].apply(lambda x:f"{x:,.2f}")
    display_df['Güncel_Tuketim'] = display_df['Tuketim'].apply(lambda x:f"{x:,.2f}")
    display_df['Sapma_Miktarı'] = display_df['Sapma_Miktarı'].apply(lambda x:f"{x:,.2f}")
    display_df['Sapma_Yüzdesi'] = display_df['Sapma_Yüzdesi'].apply(lambda x:f"{x:.1f}%")
    display_df = display_df.rename(columns={
        'TN':'TN',
        'Sozlesme_No':'Sözleşme No',
        'Ay_Adi':'Ay',
        'Tarih':'Tarih',
        'Geçmiş_Ortalama':'Geçmiş Ortalama',
        'Güncel_Tuketim':'Güncel Tüketim',
        'Sapma_Miktarı':'Sapma Miktarı',
        'Sapma_Yüzdesi':'Sapma %'
    })
    return display_df

def create_deviation_report(data, threshold):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        report_data = data.copy()
        report_data.to_excel(writer, sheet_name=f'Sapma Raporu {threshold}%', index=False)
        workbook = writer.book
        header_format = workbook.add_format({'bold':True,'text_wrap':True,'valign':'top','fg_color':'#D7E4BC','border':1})
        for ws_name in writer.sheets:
            ws = writer.sheets[ws_name]
            for col_num in range(len(report_data.columns)):
                ws.set_column(col_num,col_num,20)
                ws.write(0,col_num,report_data.columns[col_num],header_format)
    output.seek(0)
    return output.getvalue()

if __name__ == "__main__":
    st.set_page_config(page_title="Doğalgaz Sapma Analizi", layout="wide")
    main()
