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
    
    # 2023 dosyası yükleme
    file_2023 = st.sidebar.file_uploader(
        "2023 Veriler", 
        type=['xlsx', 'xls'],
        key="file_2023",
        help="TN, Tüketim Miktarı, Tarih, Sözleşme Numarası sütunları olmalı"
    )
    
    # 2024 dosyası yükleme
    file_2024 = st.sidebar.file_uploader(
        "2024 Veriler", 
        type=['xlsx', 'xls'],
        key="file_2024",
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
    
    if file_2023 is not None and file_2024 is not None and file_2025 is not None:
        try:
            # Excel dosyalarını okuma
            df_2023 = pd.read_excel(file_2023)
            df_2024 = pd.read_excel(file_2024)
            df_2025 = pd.read_excel(file_2025)
            
            st.success("✅ Tüm dosyalar başarıyla yüklendi!")
            
            # Dosya önizlemeleri
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("2023 Verisi")
                st.dataframe(df_2023.head(), use_container_width=True)
                st.info(f"Toplam kayıt: {len(df_2023)}")
            
            with col2:
                st.subheader("2024 Verisi")
                st.dataframe(df_2024.head(), use_container_width=True)
                st.info(f"Toplam kayıt: {len(df_2024)}")
                
            with col3:
                st.subheader("2025 Verisi")
                st.dataframe(df_2025.head(), use_container_width=True)
                st.info(f"Toplam kayıt: {len(df_2025)}")
            
            # Sütun eşleştirmesi - 2023 dosyasına göre
            st.header("🔧 Sütun Eşleştirmesi")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                tn_col = st.selectbox(
                    "TN Sütunu:",
                    options=df_2023.columns.tolist()
                )
                
            with col2:
                tuketim_col = st.selectbox(
                    "Tüketim Sütunu:",
                    options=df_2023.columns.tolist()
                )
                
            with col3:
                tarih_col = st.selectbox(
                    "Tarih Sütunu:",
                    options=df_2023.columns.tolist()
                )
                
            with col4:
                sozlesme_col = st.selectbox(
                    "Sözleşme No Sütunu:",
                    options=df_2023.columns.tolist()
                )
            
            if st.button("🔍 Sapma Analizini Başlat", type="primary"):
                with st.spinner("Analiz yapılıyor..."):
                    # 2023-2024 ortalamalarını hesapla
                    historical_avg = calculate_historical_average_separate(
                        df_2023, df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col
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
                        
                        # Özet bilgi
                        total_compared = len(deviation_results)
                        high_deviation = len(deviation_results[deviation_results['Sapma_Yüzdesi'] >= threshold])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Karşılaştırılan Tesisat", f"{total_compared}")
                        with col2:
                            st.metric(f">{threshold}% Sapma Gösteren", f"{high_deviation}")
                        with col3:
                            st.metric("Oran", f"{high_deviation/total_compared*100:.1f}%" if total_compared > 0 else "0%")
                        
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
        st.info("📂 Analiz yapmak için 2023, 2024 ve 2025 Excel dosyalarını yükleyin.")
        
        # Örnek veri formatı
        st.header("📋 Beklenen Excel Formatı")
        example_data = pd.DataFrame({
            'TN': ['TN001', 'TN002', 'TN001', 'TN002'],
            'Tüketim Miktarı': [1250.50, 890.25, 1180.30, 920.15],
            'Tarih': ['2023-01-01', '2023-01-01', '2023-02-01', '2023-02-01'],
            'Sözleşme Numarası': ['SZ123', 'SZ124', 'SZ123', 'SZ124']
        })
        st.dataframe(example_data, use_container_width=True)
        st.warning("⚠️ Her üç dosya da aynı sütun yapısına sahip olmalıdır!")

def calculate_historical_average_separate(df_2023, df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col):
    """2023 ve 2024 verilerini ayrı ayrı işleyip ortalamasını hesapla"""
    try:
        # 2023 verilerini temizle
        df_2023_clean = clean_data(df_2023, tn_col, tuketim_col, tarih_col, sozlesme_col, 2023)
        # 2024 verilerini temizle  
        df_2024_clean = clean_data(df_2024, tn_col, tuketim_col, tarih_col, sozlesme_col, 2024)
        
        if df_2023_clean is None or df_2024_clean is None:
            return None
            
        # İki veriyi birleştir
        combined_df = pd.concat([df_2023_clean, df_2024_clean], ignore_index=True)
        
        st.info(f"📊 2023 verisi: {len(df_2023_clean)} kayıt, 2024 verisi: {len(df_2024_clean)} kayıt")
        
        # Sıfır tüketim değerlerini filtrele
        before_filter = len(combined_df)
        combined_df = combined_df[combined_df['Tuketim'] > 0]
        after_filter = len(combined_df)
        
        if before_filter > after_filter:
            st.warning(f"⚠️ {before_filter - after_filter} adet sıfır tüketim değeri ortalamadan çıkarıldı")
        
        if combined_df.empty:
            st.error("❌ Sıfırdan büyük tüketim değeri bulunamadı!")
            return None
        
        # TN bazında ortalama hesapla (sıfır olmayan değerlerden)
        monthly_avg = combined_df.groupby(['TN', 'Sozlesme_No'])['Tuketim'].mean().reset_index()
        monthly_avg.columns = ['TN', 'Sozlesme_No', 'Ortalama_Tuketim']
        
        st.success(f"✅ {len(monthly_avg)} tesisat için ortalama hesaplandı")
        
        return monthly_avg
        
    except Exception as e:
        st.error(f"Geçmiş veri analizi hatası: {str(e)}")
        return None

def clean_data(df, tn_col, tuketim_col, tarih_col, sozlesme_col, expected_year):
    """Veriyi temizle ve belirtilen yıla göre filtrele"""
    try:
        # Sütunları seç ve adlandır
        df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
        df_clean.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        
        # Boş değerleri temizle
        initial_count = len(df_clean)
        df_clean = df_clean.dropna()
        
        if len(df_clean) < initial_count:
            st.info(f"📝 {expected_year} verisinden {initial_count - len(df_clean)} boş kayıt temizlendi")
        
        # Tarihi datetime'a çevir
        df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tarih'])
        
        # Tüketimi sayısal yap
        df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tuketim'])
        
        # Belirtilen yılı filtrele
        df_clean = df_clean[df_clean['Tarih'].dt.year == expected_year]
        
        if df_clean.empty:
            st.warning(f"⚠️ {expected_year} yılına ait veri bulunamadı!")
            return None
            
        # TN ve Sözleşme No'yu string yap
        df_clean['TN'] = df_clean['TN'].astype(str).str.strip()
        df_clean['Sozlesme_No'] = df_clean['Sozlesme_No'].astype(str).str.strip()
        
        return df_clean
        
    except Exception as e:
        st.error(f"{expected_year} veri temizleme hatası: {str(e)}")
        return None

def prepare_current_data(df, tn_col, tuketim_col, tarih_col, sozlesme_col):
    """2025 verilerini hazırla"""
    try:
        df_clean = df[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
        df_clean.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        
        # Boş değerleri temizle
        df_clean = df_clean.dropna()
        
        # Tarihi datetime'a çevir
        df_clean['Tarih'] = pd.to_datetime(df_clean['Tarih'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tarih'])
        
        # Tüketimi sayısal yap
        df_clean['Tuketim'] = pd.to_numeric(df_clean['Tuketim'], errors='coerce')
        df_clean = df_clean.dropna(subset=['Tuketim'])
        
        # 2025 yılını filtrele
        df_clean = df_clean[df_clean['Tarih'].dt.year == 2025]
        
        if df_clean.empty:
            st.error("❌ 2025 yılına ait veri bulunamadı!")
            return None
        
        # Sıfır tüketim değerlerini dahil et (2025 için sıfır da önemli olabilir)
        # Ama negatif değerleri temizle
        df_clean = df_clean[df_clean['Tuketim'] >= 0]
        
        # TN ve Sözleşme No'yu string yap
        df_clean['TN'] = df_clean['TN'].astype(str).str.strip()
        df_clean['Sozlesme_No'] = df_clean['Sozlesme_No'].astype(str).str.strip()
        
        # Ay bilgisi ekle
        df_clean['Ay'] = df_clean['Tarih'].dt.month
        df_clean['Ay_Adi'] = df_clean['Tarih'].dt.strftime('%Y-%m')
        
        st.success(f"✅ 2025 verisi hazırlandı: {len(df_clean)} kayıt")
        
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
        matched_count = 0
        
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
                matched_count += 1
                avg_tuketim = historical_record.iloc[0]['Ortalama_Tuketim']
                
                # Sapma hesapla (ortalama > 0 olduğundan emin olduk)
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
        
        st.info(f"📊 {len(current_data)} adet 2025 kaydından {matched_count} tanesi geçmiş verilerle eşleşti")
        
        if results:
            return pd.DataFrame(results)
        else:
            st.warning("⚠️ Eşleşen tesisat bulunamadı!")
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
                'Toplam Fazla Tüketim (m³)',
                'Ortalama Geçmiş Tüketim (m³)',
                'Ortalama Güncel Tüketim (m³)'
            ],
            'Değer': [
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                f"{threshold}%",
                len(data),
                f"{data['Sapma_Yüzdesi'].mean():.1f}%",
                f"{data['Sapma_Yüzdesi'].max():.1f}%",
                f"{data['Sapma_Yüzdesi'].min():.1f}%",
                f"{data['Sapma_Miktarı'].sum():.2f}",
                f"{data['Geçmiş_Ortalama'].mean():.2f}",
                f"{data['Güncel_Tuketim'].mean():.2f}"
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
