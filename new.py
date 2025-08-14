import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

def main():
    st.title("Doğalgaz Tüketim Sapma Analizi")
    st.markdown("2023-2024 ortalamasından %30 fazla sapma gösteren tesisatları tespit edin")
    
    # Sidebar için dosya yükleme alanları
    st.sidebar.header("Excel Dosyalarını Yükleyin")
    
    # 2023-2024 dosyası yükleme
    file_historical = st.sidebar.file_uploader(
        "2023-2024 Geçmiş Veriler", 
        type=['xlsx', 'xls'],
        key="file_historical",
        help="TN, Tüketim Miktarı, Tarih, Sözleşme Numarası sütunları olmalı"
    )
    
    # 2025 dosyası yükleme
    file_2025 = st.sidebar.file_uploader(
        "2025 Güncel Veriler", 
        type=['xlsx', 'xls'],
        key="file_2025",
        help="TN, Tüketim Miktarı, Tarih, Sözleşme Numarası sütunları olmalı"
    )
    
    # Eşik değeri ayarı
    threshold = st.sidebar.slider(
        "Sapma Eşiği (%)", 
        min_value=10, 
        max_value=100, 
        value=30,
        help="Bu yüzdeden fazla artış gösteren tesisatlar raporlanacak"
    )
    
    if file_historical is not None and file_2025 is not None:
        try:
            # Excel dosyalarını okuma
            df_historical = pd.read_excel(file_historical)
            df_2025 = pd.read_excel(file_2025)
            
            st.success("✅ Dosyalar başarıyla yüklendi!")
            
            # Dosya önizlemeleri
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("2023-2024 Verisi")
                st.dataframe(df_historical.head(), use_container_width=True)
                st.info(f"Toplam kayıt: {len(df_historical)}")
            
            with col2:
                st.subheader("2025 Verisi")
                st.dataframe(df_2025.head(), use_container_width=True)
                st.info(f"Toplam kayıt: {len(df_2025)}")
            
            # Sütun eşleştirmesi
            st.header("🔧 Sütun Eşleştirmesi")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                tn_col = st.selectbox(
                    "TN Sütunu:",
                    options=df_historical.columns.tolist()
                )
                
            with col2:
                tuketim_col = st.selectbox(
                    "Tüketim Sütunu:",
                    options=df_historical.columns.tolist()
                )
                
            with col3:
                tarih_col = st.selectbox(
                    "Tarih Sütunu:",
                    options=df_historical.columns.tolist()
                )
                
            with col4:
                sozlesme_col = st.selectbox(
                    "Sözleşme No Sütunu:",
                    options=df_historical.columns.tolist()
                )
            
            if st.button("🔍 Sapma Analizini Başlat", type="primary"):
                with st.spinner("Analiz yapılıyor..."):
                    # 2023-2024 ortalamalarını hesapla
                    historical_avg = calculate_historical_average(
                        df_historical, tn_col, tuketim_col, tarih_col, sozlesme_col
                    )
                    
                    # 2025 verilerini hazırla
                    current_data = prepare_current_data(
                        df_2025, tn_col, tuketim_col, tarih_col, sozlesme_col
                    )
                    
                    # Sapma analizini yap
                    deviation_results = analyze_deviations(
                        historical_avg, current_data, threshold
                    )
                    
                    if deviation_results is not None and not deviation_results.empty:
                        st.success(f"✅ Analiz tamamlandı!")
                        
                       
                        # Yüksek sapma gösteren tesisatları filtrele
                        high_deviations = deviation_results[
                            deviation_results['Sapma_Yüzdesi'] >= threshold
                        ].copy()
                        
                        if not high_deviations.empty:
                            st.header(f"⚠️ {threshold}% Üzeri Sapma Gösteren Tesisatlar")
                            
                            # Sıralama
                            high_deviations = high_deviations.sort_values('Sapma_Yüzdesi', ascending=False)
                            
                            # Tablo gösterimi
                            display_df = format_display_table(high_deviations)
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                            
                            # Excel indirme
                            excel_data = create_deviation_report(high_deviations, threshold)
                            
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
            st.info("💡 Dosyalarınızın doğru formatta olduğundan emin olun.")
    
    else:
        st.info("📂 Analiz yapmak için her iki Excel dosyasını da yükleyin.")
        
        # Örnek veri formatı
        st.header("📋 Beklenen Excel Formatı")
        example_data = pd.DataFrame({
            'TN': ['TN001', 'TN002', 'TN001', 'TN002'],
            'Tüketim Miktarı': [1250.50, 890.25, 1180.30, 920.15],
            'Tarih': ['2023-01-01', '2023-01-01', '2023-02-01', '2023-02-01'],
            'Sözleşme Numarası': ['SZ123', 'SZ124', 'SZ123', 'SZ124']
        })
        st.dataframe(example_data, use_container_width=True)

def calculate_historical_average(df, tn_col, tuketim_col, tarih_col, sozlesme_col):
    """2023-2024 verilerinin aylık ortalamalarını hesapla"""
    try:
        # Veriyi temizle
        df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
        df_clean.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        
        # Tarihi datetime'a çevir
        df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tarih'])
        
        # Tüketimi sayısal yap
        df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tuketim'])
        
        # 2023-2024 yıllarını filtrele
        df_clean = df_clean[
            (df_clean['Tarih'].dt.year == 2023) | 
            (df_clean['Tarih'].dt.year == 2024)
        ]
        
        # Ay-yıl sütunu ekle
        df_clean['Ay_Yil'] = df_clean['Tarih'].dt.to_period('M')
        
        # TN bazında aylık ortalama hesapla
        monthly_avg = df_clean.groupby(['TN', 'Sozlesme_No'])['Tuketim'].mean().reset_index()
        monthly_avg.columns = ['TN', 'Sozlesme_No', 'Ortalama_Tuketim']
        
        return monthly_avg
        
    except Exception as e:
        st.error(f"Geçmiş veri analizi hatası: {str(e)}")
        return None

def prepare_current_data(df, tn_col, tuketim_col, tarih_col, sozlesme_col):
    """2025 verilerini hazırla"""
    try:
        df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
        df_clean.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        
        # Tarihi datetime'a çevir
        df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tarih'])
        
        # Tüketimi sayısal yap
        df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tuketim'])
        
        # 2025 yılını filtrele
        df_clean = df_clean[df_clean['Tarih'].dt.year == 2025]
        
        # Ay bilgisi ekle
        df_clean['Ay'] = df_clean['Tarih'].dt.month
        df_clean['Ay_Adi'] = df_clean['Tarih'].dt.strftime('%Y-%m')
        
        return df_clean
        
    except Exception as e:
        st.error(f"2025 veri hazırlama hatası: {str(e)}")
        return None

def analyze_deviations(historical_avg, current_data, threshold):
    """Sapma analizini yap"""
    try:
        if historical_avg is None or current_data is None:
            return None
            
        results = []
        
        # Her 2025 kaydı için kontrol et
        for _, row in current_data.iterrows():
            tn = row['TN']
            sozlesme_no = row['Sozlesme_No']
            current_tuketim = row['Tuketim']
            ay_adi = row['Ay_Adi']
            tarih = row['Tarih']
            
            # Bu TN'nin geçmiş ortalamasını bul
            historical_record = historical_avg[
                (historical_avg['TN'] == tn) & 
                (historical_avg['Sozlesme_No'] == sozlesme_no)
            ]
            
            if not historical_record.empty:
                avg_tuketim = historical_record.iloc[0]['Ortalama_Tuketim']
                
                # Sapma hesapla
                if avg_tuketim > 0:
                    sapma_miktar = current_tuketim - avg_tuketim
                    sapma_yuzde = (sapma_miktar / avg_tuketim) * 100
                    
                    results.append({
                        'TN': tn,
                        'Sozlesme_No': sozlesme_no,
                        'Ay': ay_adi,
                        'Tarih': tarih,
                        'Geçmiş_Ortalama': avg_tuketim,
                        'Güncel_Tuketim': current_tuketim,
                        'Sapma_Miktarı': sapma_miktar,
                        'Sapma_Yüzdesi': sapma_yuzde
                    })
        
        if results:
            return pd.DataFrame(results)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Sapma analizi hatası: {str(e)}")
        return None

def format_display_table(df):
    """Görüntüleme için tabloyu formatla"""
    display_df = df.copy()
    
    # Sayısal sütunları formatla
    display_df['Geçmiş_Ortalama'] = display_df['Geçmiş_Ortalama'].apply(lambda x: f"{x:,.2f}")
    display_df['Güncel_Tuketim'] = display_df['Güncel_Tuketim'].apply(lambda x: f"{x:,.2f}")
    display_df['Sapma_Miktarı'] = display_df['Sapma_Miktarı'].apply(lambda x: f"{x:,.2f}")
    display_df['Sapma_Yüzdesi'] = display_df['Sapma_Yüzdesi'].apply(lambda x: f"{x:.1f}%")
    
    # Sütun isimlerini güncelle
    display_df.columns = [
        'TN', 'Sözleşme No', 'Ay', 'Tarih',
        'Geçmiş Ortalama', 'Güncel Tüketim', 
        'Sapma Miktarı', 'Sapma %'
    ]
    
    return display_df

def create_deviation_report(data, threshold):
    """Excel sapma raporu oluştur"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Ana rapor
        report_data = data.copy()
        report_data.columns = [
            'TN', 'Sözleşme Numarası', 'Ay', 'Tarih',
            'Geçmiş Ortalama (m³)', 'Güncel Tüketim (m³)', 
            'Sapma Miktarı (m³)', 'Sapma Yüzdesi (%)'
        ]
        
        report_data.to_excel(writer, sheet_name=f'Sapma Raporu {threshold}%', index=False)
        
        # Özet sayfa
        summary_data = pd.DataFrame({
            'Kriter': [
                'Analiz Tarihi',
                'Sapma Eşiği (%)',
                'Toplam Sapma Gösteren Tesisat',
                'Ortalama Sapma (%)',
                'Maksimum Sapma (%)',
                'Minimum Sapma (%)',
                'Toplam Fazla Tüketim (m³)'
            ],
            'Değer': [
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                f"{threshold}%",
                len(data),
                f"{data['Sapma_Yüzdesi'].mean():.1f}%",
                f"{data['Sapma_Yüzdesi'].max():.1f}%",
                f"{data['Sapma_Yüzdesi'].min():.1f}%",
                f"{data['Sapma_Miktarı'].sum():.2f}"
            ]
        })
        
        summary_data.to_excel(writer, sheet_name='Özet', index=False)
        
        # Format ayarları
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Başlıkları formatla
        for worksheet_name in writer.sheets:
            worksheet = writer.sheets[worksheet_name]
            for col_num in range(len(report_data.columns)):
                worksheet.set_column(col_num, col_num, 15)
            
            # İlk satırı formatla
            for col_num in range(len(report_data.columns)):
                worksheet.write(0, col_num, report_data.columns[col_num], header_format)
    
    output.seek(0)
    return output.getvalue()

if __name__ == "__main__":
    st.set_page_config(
        page_title="Doğalgaz Sapma Analizi",
        page_icon="",
        layout="wide"
    )
    
    main()
