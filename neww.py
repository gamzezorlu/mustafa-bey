import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import gc
import time

def main():
    st.title("Doğalgaz Tüketim Sapma Analizi - Büyük Veri Optimizasyonlu")
    st.markdown("2023-2024 ortalamasından %30 fazla sapma gösteren tesisatları tespit edin")
    
    # Memory usage gösterimi
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Bellek Temizle"):
            gc.collect()
            st.success("Bellek temizlendi!")
    
    # Sidebar için dosya yükleme alanları
    st.sidebar.header("Excel Dosyalarını Yükleyin")
    
    # Chunk size ayarı
    chunk_size = st.sidebar.selectbox(
        "İşlem Parça Boyutu:",
        [10000, 25000, 50000, 100000],
        index=1,
        help="Büyük dosyalar için küçük değer seçin"
    )
    
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
    
    # Sadece belirli ay aralığını analiz etme seçeneği
    analyze_specific_months = st.sidebar.checkbox("Sadece belirli ayları analiz et", value=False)
    
    if analyze_specific_months:
        selected_months = st.sidebar.multiselect(
            "Analiz edilecek aylar:",
            range(1, 13),
            default=[1, 2, 3],
            format_func=lambda x: datetime(2023, x, 1).strftime("%B")
        )
    else:
        selected_months = list(range(1, 13))
    
    if file_2023 is not None and file_2024 is not None and file_2025 is not None:
        try:
            # Dosya boyutlarını göster
            st.info("📁 Dosya boyutları kontrol ediliyor...")
            
            # Dosya metadata'sını al
            file_info = get_file_info(file_2023, file_2024, file_2025)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("2023 Dosya Boyutu", f"{file_info['2023']:.1f} MB")
            with col2:
                st.metric("2024 Dosya Boyutu", f"{file_info['2024']:.1f} MB")
            with col3:
                st.metric("2025 Dosya Boyutu", f"{file_info['2025']:.1f} MB")
            
            # İlk satırları okuyarak sütun isimlerini al
            st.info("🔍 Sütun yapıları analiz ediliyor...")
            sample_2023 = pd.read_excel(file_2023, nrows=5)
            
            # Sütun eşleştirmesi
            st.header("🔧 Sütun Eşleştirmesi")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                tn_col = st.selectbox(
                    "TN Sütunu:",
                    options=sample_2023.columns.tolist()
                )
                
            with col2:
                tuketim_col = st.selectbox(
                    "Tüketim Sütunu:",
                    options=sample_2023.columns.tolist()
                )
                
            with col3:
                tarih_col = st.selectbox(
                    "Tarih Sütunu:",
                    options=sample_2023.columns.tolist()
                )
                
            with col4:
                sozlesme_col = st.selectbox(
                    "Sözleşme No Sütunu:",
                    options=sample_2023.columns.tolist()
                )
            
            # Örnek veri göster
            st.subheader("📋 Veri Önizleme (İlk 5 satır)")
            display_cols = [tn_col, tuketim_col, tarih_col, sozlesme_col]
            st.dataframe(sample_2023[display_cols], use_container_width=True)
            
            if st.button("🚀 Büyük Veri Analizi Başlat", type="primary"):
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    with st.spinner("Büyük veri seti işleniyor... Bu işlem birkaç dakika sürebilir."):
                        
                        # 1. Adım: 2023-2024 verilerini parçalı okuma ile işle
                        status_text.text("2023-2024 geçmiş veriler işleniyor...")
                        progress_bar.progress(10)
                        
                        historical_avg = process_large_historical_data(
                            file_2023, file_2024, tn_col, tuketim_col, 
                            tarih_col, sozlesme_col, chunk_size, selected_months
                        )
                        
                        if historical_avg is None or historical_avg.empty:
                            st.error("❌ Geçmiş veri işlenemedi!")
                            return
                        
                        progress_bar.progress(40)
                        
                        # 2. Adım: 2025 verilerini işle
                        status_text.text("2025 güncel veriler işleniyor...")
                        current_data = process_large_current_data(
                            file_2025, tn_col, tuketim_col, tarih_col, 
                            sozlesme_col, chunk_size, selected_months
                        )
                        
                        if current_data is None or current_data.empty:
                            st.error("❌ 2025 verisi işlenemedi!")
                            return
                            
                        progress_bar.progress(70)
                        
                        # 3. Adım: Sapma analizini yap
                        status_text.text("Sapma analizi yapılıyor...")
                        deviation_results = analyze_large_deviations(
                            historical_avg, current_data, threshold
                        )
                        
                        progress_bar.progress(90)
                        
                        # 4. Adım: Sonuçları göster
                        status_text.text("Sonuçlar hazırlanıyor...")
                        display_large_results(deviation_results, threshold)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Analiz tamamlandı!")
                        
                        # Belleği temizle
                        del historical_avg, current_data
                        gc.collect()
                        
                except Exception as e:
                    st.error(f"❌ Büyük veri işleme hatası: {str(e)}")
                    st.info("💡 Chunk boyutunu küçültmeyi deneyin veya belleği temizleyin")
                        
        except Exception as e:
            st.error(f"❌ Dosya okuma hatası: {str(e)}")
            st.info("💡 Dosyaların Excel formatında ve erişilebilir olduğundan emin olun")
    
    else:
        st.info("📂 Analiz yapmak için 2023, 2024 ve 2025 Excel dosyalarını yükleyin.")
        
        # Büyük veri için öneriler
        st.header("💡 Büyük Veri Seti İçin Öneriler")
        
        recommendations = """
        **Performans İpuçları:**
        - Chunk boyutunu 25,000-50,000 arasında tutun
        - Sadece gerekli ayları analiz edin 
        - İşlem sırasında diğer uygulamaları kapatın
        - En az 8GB RAM önerilir
        - Sonuçları CSV olarak indirip Excel'de açın
        """
        st.markdown(recommendations)
        
        # Örnek veri formatı
        st.header("📋 Beklenen Excel Formatı")
        example_data = pd.DataFrame({
            'TN': ['TN001', 'TN002', 'TN001', 'TN002'],
            'Tüketim Miktarı': [1250.50, 890.25, 1180.30, 920.15],
            'Tarih': ['2023-01-01', '2023-01-01', '2023-02-01', '2023-02-01'],
            'Sözleşme Numarası': ['SZ123', 'SZ124', 'SZ123', 'SZ124']
        })
        st.dataframe(example_data, use_container_width=True)

def get_file_info(file1, file2, file3):
    """Dosya boyutlarını MB cinsinden döndür"""
    try:
        sizes = {}
        for name, file in [('2023', file1), ('2024', file2), ('2025', file3)]:
            file.seek(0, 2)  # Dosya sonuna git
            size = file.tell()  # Boyutu al
            file.seek(0)  # Başa dön
            sizes[name] = size / (1024 * 1024)  # MB'ye çevir
        return sizes
    except:
        return {'2023': 0, '2024': 0, '2025': 0}

def process_large_historical_data(file_2023, file_2024, tn_col, tuketim_col, 
                                  tarih_col, sozlesme_col, chunk_size, selected_months):
    """Büyük geçmiş veriyi parçalı işle"""
    try:
        historical_data = []
        
        # 2023 dosyasını parçalı oku
        st.info("📊 2023 dosyası parçalı okunuyor...")
        for i, chunk in enumerate(pd.read_excel(file_2023, chunksize=chunk_size)):
            st.text(f"2023 - Parça {i+1} işleniyor ({len(chunk)} satır)")
            
            processed_chunk = process_chunk(
                chunk, tn_col, tuketim_col, tarih_col, sozlesme_col, 
                2023, selected_months
            )
            
            if processed_chunk is not None and not processed_chunk.empty:
                historical_data.append(processed_chunk)
        
        # 2024 dosyasını parçalı oku
        st.info("📊 2024 dosyası parçalı okunuyor...")
        for i, chunk in enumerate(pd.read_excel(file_2024, chunksize=chunk_size)):
            st.text(f"2024 - Parça {i+1} işleniyor ({len(chunk)} satır)")
            
            processed_chunk = process_chunk(
                chunk, tn_col, tuketim_col, tarih_col, sozlesme_col, 
                2024, selected_months
            )
            
            if processed_chunk is not None and not processed_chunk.empty:
                historical_data.append(processed_chunk)
        
        if not historical_data:
            st.error("❌ İşlenebilir geçmiş veri bulunamadı!")
            return None
        
        # Tüm parçaları birleştir
        st.info("🔗 Veriler birleştiriliyor...")
        combined_df = pd.concat(historical_data, ignore_index=True)
        
        # Bellek optimizasyonu
        del historical_data
        gc.collect()
        
        # Ortalama hesapla (optimized groupby)
        st.info("📈 TN bazında ortalamalar hesaplanıyor...")
        avg_data = combined_df.groupby(['TN', 'Sozlesme_No'], as_index=False).agg({
            'Tuketim': ['mean', 'count']
        })
        
        # Column flatten
        avg_data.columns = ['TN', 'Sozlesme_No', 'Ortalama_Tuketim', 'Kayit_Sayisi']
        
        # En az 2 kayıt olanları al (güvenilirlik için)
        avg_data = avg_data[avg_data['Kayit_Sayisi'] >= 2]
        
        st.success(f"✅ {len(avg_data)} tesisat için geçmiş ortalama hesaplandı")
        
        return avg_data[['TN', 'Sozlesme_No', 'Ortalama_Tuketim']]
        
    except Exception as e:
        st.error(f"Geçmiş veri işleme hatası: {str(e)}")
        return None

def process_large_current_data(file_2025, tn_col, tuketim_col, tarih_col, 
                               sozlesme_col, chunk_size, selected_months):
    """Büyük 2025 verisini parçalı işle"""
    try:
        current_data = []
        
        st.info("📊 2025 dosyası parçalı okunuyor...")
        for i, chunk in enumerate(pd.read_excel(file_2025, chunksize=chunk_size)):
            st.text(f"2025 - Parça {i+1} işleniyor ({len(chunk)} satır)")
            
            processed_chunk = process_chunk(
                chunk, tn_col, tuketim_col, tarih_col, sozlesme_col, 
                2025, selected_months
            )
            
            if processed_chunk is not None and not processed_chunk.empty:
                # Ay bilgisi ekle
                processed_chunk['Ay'] = processed_chunk['Tarih'].dt.month
                processed_chunk['Ay_Adi'] = processed_chunk['Tarih'].dt.strftime('%Y-%m')
                current_data.append(processed_chunk)
        
        if not current_data:
            st.error("❌ İşlenebilir 2025 verisi bulunamadı!")
            return None
        
        # Birleştir
        combined_current = pd.concat(current_data, ignore_index=True)
        
        # Bellek temizle
        del current_data
        gc.collect()
        
        st.success(f"✅ 2025 verisi hazırlandı: {len(combined_current)} kayıt")
        
        return combined_current
        
    except Exception as e:
        st.error(f"2025 veri işleme hatası: {str(e)}")
        return None

def process_chunk(chunk, tn_col, tuketim_col, tarih_col, sozlesme_col, 
                  expected_year, selected_months):
    """Veri parçasını işle"""
    try:
        # Sütunları seç
        df_chunk = chunk[[tn_col, tuketim_col, tarih_col, sozlesme_col]].copy()
        df_chunk.columns = ['TN', 'Tuketim', 'Tarih', 'Sozlesme_No']
        
        # Boş değerleri temizle
        df_chunk = df_chunk.dropna()
        
        if df_chunk.empty:
            return None
        
        # Tarihi çevir
        df_chunk['Tarih'] = pd.to_datetime(df_chunk['Tarih'], errors='coerce')
        df_chunk = df_chunk.dropna(subset=['Tarih'])
        
        # Yıl filtresi
        df_chunk = df_chunk[df_chunk['Tarih'].dt.year == expected_year]
        
        # Ay filtresi
        if selected_months:
            df_chunk = df_chunk[df_chunk['Tarih'].dt.month.isin(selected_months)]
        
        if df_chunk.empty:
            return None
        
        # Tüketimi sayısal yap
        df_chunk['Tuketim'] = pd.to_numeric(df_chunk['Tuketim'], errors='coerce')
        df_chunk = df_chunk.dropna(subset=['Tuketim'])
        
        # Negatif değerleri temizle
        df_chunk = df_chunk[df_chunk['Tuketim'] >= 0]
        
        # Geçmiş veriler için sıfır tüketim filtrele
        if expected_year in [2023, 2024]:
            df_chunk = df_chunk[df_chunk['Tuketim'] > 0]
        
        # String cleanup
        df_chunk['TN'] = df_chunk['TN'].astype(str).str.strip()
        df_chunk['Sozlesme_No'] = df_chunk['Sozlesme_No'].astype(str).str.strip()
        
        return df_chunk
        
    except Exception as e:
        st.warning(f"Parça işleme uyarısı: {str(e)}")
        return None

def analyze_large_deviations(historical_avg, current_data, threshold):
    """Büyük veri seti için sapma analizi"""
    try:
        st.info("🔍 Eşleşmeler bulunuyor...")
        
        # Memory efficient merge kullan
        merged_data = pd.merge(
            current_data, 
            historical_avg, 
            on=['TN', 'Sozlesme_No'], 
            how='inner'
        )
        
        if merged_data.empty:
            st.warning("⚠️ Eşleşen tesisat bulunamadı!")
            return pd.DataFrame()
        
        st.info(f"📊 {len(merged_data)} adet eşleşme bulundu")
        
        # Sapma hesaplamaları (vectorized)
        merged_data['Sapma_Miktarı'] = merged_data['Tuketim'] - merged_data['Ortalama_Tuketim']
        merged_data['Sapma_Yüzdesi'] = (merged_data['Sapma_Miktarı'] / merged_data['Ortalama_Tuketim']) * 100
        
        # Sonuç DataFrame'i oluştur
        result_data = merged_data[[
            'TN', 'Sozlesme_No', 'Ay_Adi', 'Tarih',
            'Ortalama_Tuketim', 'Tuketim', 'Sapma_Miktarı', 'Sapma_Yüzdesi'
        ]].copy()
        
        result_data.columns = [
            'TN', 'Sozlesme_No', 'Ay', 'Tarih',
            'Geçmiş_Ortalama', 'Güncel_Tuketim', 'Sapma_Miktarı', 'Sapma_Yüzdesi'
        ]
        
        # Bellek temizle
        del merged_data
        gc.collect()
        
        return result_data
        
    except Exception as e:
        st.error(f"Sapma analizi hatası: {str(e)}")
        return pd.DataFrame()

def display_large_results(deviation_results, threshold):
    """Büyük veri sonuçlarını göster"""
    try:
        if deviation_results is None or deviation_results.empty:
            st.error("❌ Sonuç verisi bulunamadı")
            return
        
        # Özet metrikler
        total_compared = len(deviation_results)
        high_deviation = len(deviation_results[deviation_results['Sapma_Yüzdesi'] >= threshold])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Toplam Karşılaştırma", f"{total_compared:,}")
        with col2:
            st.metric(f">{threshold}% Sapma", f"{high_deviation:,}")
        with col3:
            ratio = (high_deviation/total_compared*100) if total_compared > 0 else 0
            st.metric("Sapma Oranı", f"{ratio:.1f}%")
        with col4:
            avg_deviation = deviation_results['Sapma_Yüzdesi'].mean()
            st.metric("Ort. Sapma", f"{avg_deviation:.1f}%")
        
        # Yüksek sapma filter
        high_deviations = deviation_results[
            deviation_results['Sapma_Yüzdesi'] >= threshold
        ].copy()
        
        if not high_deviations.empty:
            st.header(f"⚠️ {threshold}% Üzeri Sapma Gösteren Tesisatlar")
            
            # Sırala
            high_deviations = high_deviations.sort_values('Sapma_Yüzdesi', ascending=False)
            
            # İlk 1000 kaydı göster (performance için)
            display_count = min(1000, len(high_deviations))
            st.info(f"📊 İlk {display_count} kayıt gösteriliyor (Toplam: {len(high_deviations)})")
            
            # Formatla ve göster
            display_df = format_display_table(high_deviations.head(display_count))
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # CSV indirme (Excel yerine daha hızlı)
            csv_data = high_deviations.to_csv(index=False)
            st.download_button(
                label=f"📥 Tüm Sapma Raporunu CSV Olarak İndir ({len(high_deviations)} kayıt)",
                data=csv_data,
                file_name=f"sapma_raporu_{threshold}pct_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                type="primary"
            )
            
            # İstatistikler
            st.subheader("📊 Sapma İstatistikleri")
            stats_col1, stats_col2, stats_col3 = st.columns(3)
            
            with stats_col1:
                st.metric("En Yüksek Sapma", f"{high_deviations['Sapma_Yüzdesi'].max():.1f}%")
            with stats_col2:
                st.metric("Ortalama Sapma", f"{high_deviations['Sapma_Yüzdesi'].mean():.1f}%")
            with stats_col3:
                median_dev = high_deviations['Sapma_Yüzdesi'].median()
                st.metric("Medyan Sapma", f"{median_dev:.1f}%")
        else:
            st.success(f"🎉 {threshold}% üzeri sapma gösteren tesisat bulunmamaktadır!")
            
    except Exception as e:
        st.error(f"Sonuç gösterimi hatası: {str(e)}")

def format_display_table(df):
    """Görüntüleme için tabloyu formatla"""
    display_df = df.copy()
    
    # Sayısal formatlar
    display_df['Geçmiş_Ortalama'] = display_df['Geçmiş_Ortalama'].apply(lambda x: f"{x:,.2f}")
    display_df['Güncel_Tuketim'] = display_df['Güncel_Tuketim'].apply(lambda x: f"{x:,.2f}")
    display_df['Sapma_Miktarı'] = display_df['Sapma_Miktarı'].apply(lambda x: f"{x:,.2f}")
    display_df['Sapma_Yüzdesi'] = display_df['Sapma_Yüzdesi'].apply(lambda x: f"{x:.1f}%")
    
    # Sütun başlıkları
    display_df.columns = [
        'TN', 'Sözleşme No', 'Ay', 'Tarih',
        'Geçmiş Ortalama', 'Güncel Tüketim', 
        'Sapma Miktarı', 'Sapma %'
    ]
    
    return display_df

if __name__ == "__main__":
    st.set_page_config(
        page_title="Doğalgaz Sapma Analizi - Büyük Veri",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sayfa başında bellek uyarısı
    st.sidebar.markdown("---")
    st.sidebar.markdown("💾 **Bellek Yönetimi**")
    st.sidebar.markdown("Büyük dosyalar için chunk boyutunu 25K-50K tutun")
    
    main()
