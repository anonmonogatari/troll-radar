# 📡 TrollRadar // Ekşi Sözlük Manipülasyon & Koordinasyon Analiz Platformu

Ekşi Sözlük üzerindeki hedef yazar hesaplarının entrylerini düzenli tarayarak; organize algı operasyonlarını, eşzamanlı koro halinde girilen başlıkları ve manipülasyon temalarını tespit eden tam kapsamlı web istihbarat platformu.

---

## 🚀 Özellikler

- **Cloudflare Bypass Scraper (`curl_cffi`)**: 27 hedef yazarın entrylerini otomatik ve kesintisiz çekme.
- **Koordinasyon & Eşzamanlılık Tespiti (Synchronicity Engine)**: Dakikalar arayla aynı konuya entry giren troll operasyonlarını otomatik yakalama.
- **Haftalık İstihbarat Bülteni**: Toplumsal kutuplaştırma, ekonomi aklama, belediye karalama ve suni gündem temalarını delil entryleriyle dosyalama.
- **Görsel Analiz & Grafikler**:
  - Günlük koordinasyon patlama grafiği (Chart.js)
  - Kategori dağılım pasta grafiği
  - **7x24 Troll Mesai Isı Haritası (Heatmap)**
  - En çok tekrarlanan anahtar kelimeler
- **İnteraktif İş Birliği Ağı (Network Graph)**: Canvas üzerinde sürüklenebilir hesaplar arası ortak başlık bağlantı ağı.
- **Entry Havuzu & Gelişmiş Filtreleme**: Kategori, yazar, tarih ve koordinasyon durumu filtreleri.
- **Dışa Aktarma**: JSON ve CSV formatlarında veri dökümü.

---

## 📦 Kurulum ve Yerel Çalıştırma

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADINIZ/troll-radar.git
cd troll-radar
```

### 2. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Uygulamayı Başlatın
```bash
python run.py
```
Tarayıcınızdan **`http://localhost:8000`** adresine gidin.

---

## 🌐 İnternette Yayımlama (Canlı Dağıtım Seçenekleri)

Bu projeyi canlıda herkesin erişebileceği bir web sitesi olarak ücretsiz veya düşük maliyetle yayımlayabilirsiniz:

### 1. Render.com (En Kolay & Ücretsiz)
1. Kodunuzu GitHub'a yükleyin (`git push`).
2. [Render.com](https://render.com) adresine gidin ve **New > Web Service** seçin.
3. GitHub deponuzu bağlayın.
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python run.py`
6. Birkaç dakika içinde `https://trollradar.onrender.com` gibi ücretsiz bir canlı bağlantı alırsınız.

### 2. Railway.app / Fly.io (Docker ile)
Depo içerisindeki `Dockerfile` sayesinde Railway veya Fly.io üzerine tek tıkla deploy edebilirsiniz:
```bash
fly launch
fly deploy
```

### 3. Hugging Face Spaces (Ücretsiz Python / Docker Alanı)
1. [Hugging Face Spaces](https://huggingface.co/spaces) üzerinde yeni bir **Docker Space** açın.
2. Depodaki dosyaları oraya aktarın. Kalıcı olarak ücretsiz çalışacaktır.

### 4. VPS / Ubuntu Sunucu (DigitalOcean, Hetzner vb.)
```bash
git clone <repo-url>
cd troll-radar
pip install -r requirements.txt
python run.py
```
`systemd` veya `pm2` ile 7/24 arka planda çalıştırabilir, `cron` ile her gece otomatik tarama yaptırabilirsiniz.
