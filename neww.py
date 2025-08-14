import streamlit as st
import pandas as pd
import io
import numpy as np
from io import BytesIO
from datetime import datetime

# Excel'i CSV'ye çevirip DataFrame döndüren fonksiyon
@st.cache_data
def excel_to_csv_df(file):
    df = pd.read_excel(file)  # Excel oku
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)  # CSV'ye çevir (bellekte)
    buffer.seek(0)
    return pd.read_csv(buffer)  # CSV'den oku

st.title("📊 Sapma Hesaplama Aracı")

# Dosya yükleme alanları
file_2023 = st.file_uploader("2023-2024 Dosyası", type=["xlsx"])
file_2025 = st.file_uploader("2025 Dosyası", type=["xlsx"])
file_export = st.file_uploader("Export CSV veya Excel", type=["xlsx", "csv"])

# Tüm dosyalar yüklendiğinde işle
if file_2023 and file_2025 and file_export:
    with st.spinner("📂 Dosyalar işleniyor, lütfen bekleyin..."):
        df1 = excel_to_csv_df(file_2023)
        df2 = excel_to_csv_df(file_2025)

        if file_export.name.endswith(".xlsx"):
            df3 = excel_to_csv_df(file_export)
        else:
            df3 = pd.read_csv(file_export)

        # Sütun isimlerini uyumlu hale getirme
        df1.columns = df1.columns.str.strip()
        df2.columns = df2.columns.str.strip()
        df3.columns = df3.columns.str.strip()

        # Birleştirme
        merged_df = pd.concat([df1, df2, df3], ignore_index=True)

    st.success("✅ Dosyalar başarıyla yüklendi ve birleştirildi!")

    # Buradan itibaren merged_df ile devam edebilirsin
    st.dataframe(merged_df)
else:
    st.warning("Lütfen tüm dosyaları yükleyin.")
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
