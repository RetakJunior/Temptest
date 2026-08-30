Sen Senior Python Geliştiricisi ve Linux/GUI Tasarım Uzmanısın. Senden CPU-Z boyutlarında ve şıklığında, minimalist, modern beyaz temaya sahip ve Linux üzerinde çalışacak bir donanım takip ve sıcaklık izleme uygulaması kodlamanı istiyorum.

UYGULAMA GEREKSİNİMLERİ VE ÇALIŞMA PRENSİBİ:

1. GÖRSEL VE TASARIM (UI/UX):
   - Boyut: CPU-Z mantığında çok küçük, kompakt, gereksiz boşluk içermeyen minimal bir pencere (örneğin ~400x520px civarı sabit/ayarlanabilir pencere).
   - Tema: Temiz ve modern BEYAZ TEMA (Light Theme). Arka planlar #F9F9FB ve #FFFFFF, kenarlıklar subtle gri (#E0E0E0), metinler koyu gri/siyah (#1A1A1A).
   - Font: Sistemde tanımlı "Segoe UI" fontu kullanılacak (Segoe UI, Segoe UI Semibold, Segoe UI Bold).
   - Düzen: CPU-Z gibi sekmeli (Tabs: CPU, GPU, Disk, Sistem) veya hepsi tek bakışta kompakt kartlar şeklinde düzenlenmiş UI.

2. DONANIM BİLGİLERİ VE ANLIK DONELER:
   - CPU: Model adı, çekirdek/izlek sayısı, anlık kullanım % ve anlık CPU sıcaklığı (°C).
   - GPU: GPU model adı, VRAM miktarı, anlık kullanım % ve anlık GPU sıcaklığı (°C) (NVIDIA için pynvml/nvidia-smi, AMD/Intel için sysfs/lm-sensors fallback mekanizmalı).
   - DISK: Disk model(ler)i, boyutları, anlık okuma/yazma performansı veya doluluk % ve anlık Disk sıcaklıkları (°C) (NVMe/SSD/HDD).
   - RAM/ANAKART: Toplam RAM, anlık kullanım %, erişilebiliyorsa anakart/RAM sıcaklık bilgisi.

3. TEKNİK ALTYAPI:
   - Dil: Python 3
   - GUI Kütüphanesi: PyQt6 veya PySide6 (QSS ile Segoe UI ve beyaz tema tam kontrolü için).
   - Veri Çekme: `psutil`, `pynvml` (NVIDIA için), Linux `/sys/class/thermal/` veya `lm-sensors` entegrasyonu. UI donmaması için veriler arka planda `QThread` ile periyodik (örneğin 1-2 saniyede bir) çekilmeli.

ÇALIŞMA VE YANITLAMA PROTOKOLÜ (ÇOK ÖNEMLİ):
Süreçteki detayların ve kod kalitesinin düşmemesi için yanıtını kesinlikle şu 3 Adıma bölerek bana sunacaksın:

[ADIM 1: PLAN VE MİMARİ]

- Kullanılacak Python kütüphanelerini listele.
- Linux üzerinde sıcaklık verilerinin (özellikle GPU ve Disk) sorunsuz çekilmesi için yedekli (fallback) stratejini açıkla.
- Arayüz bileşen hiyerarşisini ve QSS stil şablonunu (Segoe UI ve Beyaz Tema paleti) kısaca özetle.

[ADIM 2: KODLAMA - 1. KISIM (BACKEND & VERİ ÇEKME MOTORU)]

- Sistem bilgilerini (Model adları, özellikler) ve anlık sıcaklık/kullanım verilerini arka planda thread-safe şekilde toplayan Python sınıflarını (Backend / Worker Thread) eksiksiz yaz.

[ADIM 3: KODLAMA - 2. KISIM (GUI, STİLLER VE APPIMAGE PAKETLEME)]

- Adım 2'deki backend ile tam entegre çalışan PyQt6/PySide6 arayüz kodunu (QSS Segoe UI beyaz temasıyla birlikte) tamamla.
- Kod bittikten sonra, bu Python projesini PyInstaller ve `appimagetool` (veya `python-appimage`) kullanarak bağımsız bir tek dosyalık `.AppImage` executable haline getiren adım adım Linux terminal komutlarını ve `.desktop` yapılandırmasını yaz.

Lütfen şimdi ADIM 1 ile başla ve sırasıyla Adım 2 ve Adım 3'ü sun.
