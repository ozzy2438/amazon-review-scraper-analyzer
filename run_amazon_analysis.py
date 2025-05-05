#!/usr/bin/env python3
"""
Amazon Ürün Tarama ve Analiz Sistemi
-----------------------------------
Bu script, Amazon ürün tarayıcısını çalıştırır ve
sonrasında otomatik olarak analiz aracını başlatır.
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def main():
    """Ana fonksiyon"""
    print("="*60)
    print("Amazon Ürün Tarama ve Analiz Sistemi")
    print(f"Başlama zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Çıktı klasörlerini kontrol et
    output_folders = ["amazon_products", "analysis_results"]
    for folder in output_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"'{folder}' klasörü oluşturuldu.")
    
    try:
        # 1. Scraper'ı çalıştır
        print("\n1) Amazon Scraper başlatılıyor...")
        print("Not: Kullanıcı girdisi gerekebilir, lütfen terminalde ürün adı ve çekilecek ürün sayısını girin")
        scraper_start = time.time()
        
        # Gerçek zamanlı çıktı almak için subprocess.run yerine Popen kullanıyoruz
        scraper_process = subprocess.Popen(
            ["python", "amazon_review_scraper.py"],
            stdin=None,  # Kullanıcı girdisi için standart girdiyi kullan
            stdout=None,  # Çıktıyı doğrudan terminale yaz
            stderr=None,  # Hataları doğrudan terminale yaz
            text=True
        )
        
        # Scraper işleminin tamamlanmasını bekle
        scraper_return_code = scraper_process.wait()
        scraper_end = time.time()
        scraper_duration = scraper_end - scraper_start
        
        if scraper_return_code == 0:
            print(f"Scraper başarıyla tamamlandı! ({scraper_duration:.1f} saniye)")
        else:
            print("Scraper çalıştırılırken hata oluştu!")
            return 1
        
        # 2. En son oluşturulan CSV dosyasını bul
        amazon_products_folder = "amazon_products"
        csv_files = [f for f in os.listdir(amazon_products_folder) if f.endswith('.csv')]
        
        if not csv_files:
            print("Hata: CSV dosyası bulunamadı!")
            return 1
        
        # Dosyaları oluşturulma zamanına göre sırala (en yenisi ilk)
        csv_files.sort(key=lambda x: os.path.getctime(os.path.join(amazon_products_folder, x)), reverse=True)
        latest_csv = os.path.join(amazon_products_folder, csv_files[0])
        
        print(f"\nEn son oluşturulan dosya: {latest_csv}")
        
        # 3. Analyzer'ı çalıştır
        print("\n2) Amazon Analyzer başlatılıyor...")
        analyzer_start = time.time()
        
        analyzer_process = subprocess.Popen(
            ["python", "amazon_review_analyzer.py", latest_csv],
            stdin=None,
            stdout=None,
            stderr=None,
            text=True
        )
        
        # Analyzer işleminin tamamlanmasını bekle
        analyzer_return_code = analyzer_process.wait()
        analyzer_end = time.time()
        analyzer_duration = analyzer_end - analyzer_start
        
        if analyzer_return_code == 0:
            print(f"Analyzer başarıyla tamamlandı! ({analyzer_duration:.1f} saniye)")
            
            # 4. HTML rapor dosyasını bul
            analysis_folder = "analysis_results"
            html_files = [f for f in os.listdir(analysis_folder) if f.endswith('.html')]
            
            if html_files:
                # En son oluşturulan HTML dosyasını bul
                html_files.sort(key=lambda x: os.path.getctime(os.path.join(analysis_folder, x)), reverse=True)
                latest_html = os.path.join(analysis_folder, html_files[0])
                
                print(f"\nAnaliz raporu: {latest_html}")
                print(f"HTML raporunu tarayıcınızda açmak için:\nopen {latest_html}")
        else:
            print("Analyzer çalıştırılırken hata oluştu!")
            return 1
        
        total_duration = analyzer_end - scraper_start
        print("\n" + "="*60)
        print(f"Tüm işlem başarıyla tamamlandı! Toplam süre: {total_duration:.1f} saniye")
        print(f"Bitiş zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 