# Changelog

## v1.0.1 - 2026-11-20
Uygulamanın açılır açılmaz kapanması ve Windows ile birlikte başlamaması düzeltildi.

### Fixed
- Tepsi simgesi oluşturulurken 64-bit Windows'ta oluşan çökme giderildi. Uygulama artık açılıyor ve açık kalıyor, Windows açılışında da başlıyor.

### Added
- Beklenmedik bir çökmede nedeni `crash.log` dosyasına yazılıyor.

## v1.0.0 - 2026-11-20
Desktop Snow'un ilk sürümü: Windows masaüstü için birikebilen kar, karakterler ve hayvanlar.

### Added
- Altı efekt: kar, yaprak, sakura, yağmur, ateş böceği, yıldız kayması. Tıklamalar alttaki pencerelere geçer.
- Kar pencerelerin üstünde ve görev çubuğunda birikiyor. Pencere sallanınca dökülüyor, fareyle itilebiliyor.
- Yılbaşı ağaçları ve kardan adamlar. Küçük çıkıp büyüyebiliyorlar.
- Üç ziyaretçi: yeti, kar küreyici ve elfli hediye treni. Hepsi pürüzsüz çizgi film tarzında.
- 9 köpek ve 8 kedi türü. Dolaşıyor, oturuyor, uyuyor, ekrana bakıyor, üşüyor, oynuyor ve karı dağıtıyorlar.
- Animasyonlu, modern kontrol paneli. Her ayar panelden değiştirilebiliyor ve kaydediliyor. Kaos modu var.
- Ekran başına ayar: efekt gösterilsin mi, kar uygulamaların önüne mi düşsün yoksa arkasında mı kalsın.
- Tepsi simgesi, kısayol tuşları, Windows ile birlikte açılma seçeneği ve tek kopya koruması.
- Ekranın yenileme hızında (örneğin 180 Hz) akıcı çizim.
- `Desktop Snow.bat` başlatıcı (gerekli paketleri kendisi kurar) ve taşınabilir zip yapan `paketle.bat`.

### Why
- Güvenilmeyen bir üçüncü parti uygulama yerine, kodu tamamen bilinen kendi sürümünü yapmak için.
- Kurulum gerektirmeyen `.bat` + zip dağıtımı seçildi; ayrı bir exe/kurulum dosyası yok.
