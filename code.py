import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import xlsxwriter

def main():
    st.title("🔥 Doğalgaz Tüketim Karşılaştırma Uygulaması")
    st.markdown("2024 ve 2025 yaz ayları doğalgaz tüketimlerini karşılaştırın")
    
    # Sidebar için dosya yükleme alanları
    st.sidebar.header("📁 Excel Dosyalarını Yükleyin")
    
    # 2024 dosyası yükleme
    file_2024 = st.sidebar.file_uploader(
        "2024 Yaz Ayları Tüketimi", 
        type=['xlsx', 'xls'],
        key="file_2024"
    )
    
    # 2025 dosyası yükleme
    file_2025 = st.sidebar.file_uploader(
        "2025 Yaz Ayları Tüketimi", 
        type=['xlsx', 'xls'],
        key="file_2025"
    )
    
    if file_2024 is not None and file_2025 is not None:
        try:
            # Excel dosyalarını okuma
            df_2024 = pd.read_excel(file_2024)
            df_2025 = pd.read_excel(file_2025)
            
            st.success("✅ Dosyalar başarıyla yüklendi!")
            
            # Dosya önizlemeleri
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("2024 Verisi Önizleme")
                st.dataframe(df_2024.head(), use_container_width=True)
                st.info(f"Toplam satır sayısı: {len(df_2024)}")
            
            with col2:
                st.subheader("2025 Verisi Önizleme")
                st.dataframe(df_2025.head(), use_container_width=True)
                st.info(f"Toplam satır sayısı: {len(df_2025)}")
            
            # Sütun seçimi
            st.header("🔧 Sütun Eşleştirmesi")
            col1, col2 = st.columns(2)
            
            with col1:
                tesisat_col = st.selectbox(
                    "Tesisat/ID Sütunu Seçin:",
                    options=df_2024.columns.tolist(),
                    help="Tesisatları tanımlayan benzersiz sütunu seçin"
                )
                
            with col2:
                tuketim_col = st.selectbox(
                    "Tüketim Sütunu Seçin:",
                    options=df_2024.columns.tolist(),
                    help="Doğalgaz tüketim miktarını içeren sütunu seçin"
                )
            
            if st.button("📊 Karşılaştırmayı Başlat", type="primary"):
                # Veri temizleme ve hazırlama
                df_2024_clean = prepare_data(df_2024, tesisat_col, tuketim_col, "2024")
                df_2025_clean = prepare_data(df_2025, tesisat_col, tuketim_col, "2025")
                
                # Karşılaştırma yapma
                comparison_result = compare_consumption(df_2024_clean, df_2025_clean)
                
                if comparison_result is not None and not comparison_result.empty:
                    # Artış gösteren tesisatları filtrele
                    increased_consumption = comparison_result[comparison_result['Artış_Yüzdesi'] > 0]
                    
                    if not increased_consumption.empty:
                        st.header("📈 Tüketimi Artan Tesisatlar")
                        
                        # Özet bilgiler
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Toplam Tesisat",
                                f"{len(comparison_result)}",
                                help="Karşılaştırılan toplam tesisat sayısı"
                            )
                        with col2:
                            st.metric(
                                "Artış Gösteren",
                                f"{len(increased_consumption)}",
                                f"{len(increased_consumption)/len(comparison_result)*100:.1f}%"
                            )
                        with col3:
                            avg_increase = increased_consumption['Artış_Yüzdesi'].mean()
                            st.metric(
                                "Ortalama Artış",
                                f"{avg_increase:.1f}%",
                                help="Artış gösteren tesisatlardaki ortalama artış yüzdesi"
                            )
                        
                        # Detaylı tablo
                        st.subheader("📋 Detaylı Liste")
                        
                        # Sıralama seçeneği
                        sort_option = st.selectbox(
                            "Sıralama:",
                            ["Artış Yüzdesine Göre (Büyükten Küçüğe)", 
                             "Artış Miktarına Göre (Büyükten Küçüğe)",
                             "Tesisat Adına Göre"]
                        )
                        
                        if sort_option == "Artış Yüzdesine Göre (Büyükten Küçüğe)":
                            increased_consumption = increased_consumption.sort_values('Artış_Yüzdesi', ascending=False)
                        elif sort_option == "Artış Miktarına Göre (Büyükten Küçüğe)":
                            increased_consumption = increased_consumption.sort_values('Artış_Miktarı', ascending=False)
                        else:
                            increased_consumption = increased_consumption.sort_values('Tesisat')
                        
                        # Formatlanmış tablo gösterimi
                        display_df = increased_consumption.copy()
                        display_df['Tüketim_2024'] = display_df['Tüketim_2024'].apply(lambda x: f"{x:,.2f}")
                        display_df['Tüketim_2025'] = display_df['Tüketim_2025'].apply(lambda x: f"{x:,.2f}")
                        display_df['Artış_Miktarı'] = display_df['Artış_Miktarı'].apply(lambda x: f"{x:,.2f}")
                        display_df['Artış_Yüzdesi'] = display_df['Artış_Yüzdesi'].apply(lambda x: f"{x:.2f}%")
                        
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Excel indirme
                        excel_data = create_excel_report(increased_consumption)
                        
                        st.download_button(
                            label="📥 Excel Olarak İndir",
                            data=excel_data,
                            file_name=f"tuketim_artisi_raporu_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                        
                        # Görselleştirme
                        st.subheader("📊 En Çok Artış Gösteren 10 Tesisat")
                        top_10 = increased_consumption.head(10)
                        
                        chart_data = pd.DataFrame({
                            'Tesisat': top_10['Tesisat'],
                            '2024': top_10['Tüketim_2024'],
                            '2025': top_10['Tüketim_2025']
                        })
                        
                        st.bar_chart(chart_data.set_index('Tesisat'))
                        
                    else:
                        st.info("🎉 Hiçbir tesisatta tüketim artışı bulunmamaktadır!")
                        st.balloons()
                        
                else:
                    st.error("❌ Karşılaştırma yapılırken bir hata oluştu. Lütfen dosyalarınızı kontrol edin.")
                    
        except Exception as e:
            st.error(f"❌ Dosya okuma hatası: {str(e)}")
            st.info("💡 Lütfen Excel dosyalarınızın doğru formatta olduğundan emin olun.")
    
    else:
        st.info("📂 Başlamak için lütfen her iki Excel dosyasını da yükleyin.")
        
        # Örnek veri formatı gösterimi
        st.header("📋 Beklenen Veri Formatı")
        example_data = pd.DataFrame({
            'Tesisat_ID': ['TES001', 'TES002', 'TES003', 'TES004'],
            'Tesisat_Adi': ['Merkez Bina', 'Depo', 'Ofis Binası', 'Üretim Tesisi'],
            'Tuketim_m3': [1250.50, 890.25, 650.75, 2100.00],
            'Tarih': ['2024-06', '2024-06', '2024-06', '2024-06']
        })
        st.dataframe(example_data, use_container_width=True)
        st.caption("⚠️ Tablolarınızda tesisat tanımlayıcısı ve tüketim miktarı sütunları bulunmalıdır.")

def prepare_data(df, tesisat_col, tuketim_col, year):
    """Veriyi temizle ve hazırla"""
    try:
        # Gerekli sütunları seç
        cleaned_df = df[[tesisat_col, tuketim_col]].copy()
        cleaned_df.columns = ['Tesisat', f'Tuketim_{year}']
        
        # Null değerleri temizle
        cleaned_df = cleaned_df.dropna()
        
        # Tüketim değerlerini sayısal hale getir
        cleaned_df[f'Tuketim_{year}'] = pd.to_numeric(
            cleaned_df[f'Tuketim_{year}'], errors='coerce'
        )
        
        # NaN olan satırları kaldır
        cleaned_df = cleaned_df.dropna()
        
        # Tesisat adlarındaki boşlukları temizle
        cleaned_df['Tesisat'] = cleaned_df['Tesisat'].astype(str).str.strip()
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Veri hazırlama hatası: {str(e)}")
        return None

def compare_consumption(df_2024, df_2025):
    """2024 ve 2025 tüketimlerini karşılaştır"""
    try:
        # Verileri birleştir
        merged_df = pd.merge(df_2024, df_2025, on='Tesisat', how='inner')
        
        if merged_df.empty:
            st.warning("⚠️ Eşleşen tesisat bulunamadı. Tesisat adlarının her iki dosyada aynı olduğundan emin olun.")
            return None
        
        # Artış miktarı ve yüzdesini hesapla
        merged_df['Artış_Miktarı'] = merged_df['Tuketim_2025'] - merged_df['Tuketim_2024']
        merged_df['Artış_Yüzdesi'] = (
            (merged_df['Tuketim_2025'] - merged_df['Tuketim_2024']) / 
            merged_df['Tuketim_2024'] * 100
        )
        
        # Sonsuz veya NaN değerleri temizle
        merged_df = merged_df.replace([np.inf, -np.inf], np.nan).dropna()
        
        return merged_df
        
    except Exception as e:
        st.error(f"Karşılaştırma hatası: {str(e)}")
        return None

def create_excel_report(data):
    """Excel raporu oluştur"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Ana rapor sayfası
        data_copy = data.copy()
        
        # Sütun başlıklarını Türkçeye çevir
        data_copy.columns = [
            'Tesisat', '2024 Tüketimi (m³)', '2025 Tüketimi (m³)', 
            'Artış Miktarı (m³)', 'Artış Yüzdesi (%)'
        ]
        
        data_copy.to_excel(writer, sheet_name='Tüketim Artışı Raporu', index=False)
        
        # Özet istatistikler sayfası
        summary_data = pd.DataFrame({
            'İstatistik': [
                'Toplam Tesisat Sayısı',
                'Artış Gösteren Tesisat',
                'Ortalama 2024 Tüketimi (m³)',
                'Ortalama 2025 Tüketimi (m³)',
                'Ortalama Artış Miktarı (m³)',
                'Ortalama Artış Yüzdesi (%)',
                'Maksimum Artış Miktarı (m³)',
                'Maksimum Artış Yüzdesi (%)'
            ],
            'Değer': [
                len(data),
                len(data[data['Artış_Yüzdesi'] > 0]),
                f"{data['Tüketim_2024'].mean():.2f}",
                f"{data['Tüketim_2025'].mean():.2f}",
                f"{data['Artış_Miktarı'].mean():.2f}",
                f"{data['Artış_Yüzdesi'].mean():.2f}",
                f"{data['Artış_Miktarı'].max():.2f}",
                f"{data['Artış_Yüzdesi'].max():.2f}"
            ]
        })
        
        summary_data.to_excel(writer, sheet_name='Özet İstatistikler', index=False)
        
        # Worksheet formatlaması
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        for worksheet_name in writer.sheets:
            worksheet = writer.sheets[worksheet_name]
            
            # Başlıkları formatla
            for col_num, value in enumerate(data_copy.columns):
                worksheet.write(0, col_num, value, header_format)
            
            # Sütun genişliklerini ayarla
            worksheet.set_column('A:A', 20)  # Tesisat
            worksheet.set_column('B:E', 15)  # Diğer sütunlar
    
    output.seek(0)
    return output.getvalue()

if __name__ == "__main__":
    # Sayfa konfigürasyonu
    st.set_page_config(
        page_title="Doğalgaz Tüketim Karşılaştırması",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    main()
