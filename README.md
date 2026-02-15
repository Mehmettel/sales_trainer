# Sigorta Sales Trainer – Yapay Zeka Müşterisi Sohbet Robotu

[![GitHub](https://img.shields.io/badge/GitHub-Mehmettel%2Fsales__trainer-blue?logo=github)](https://github.com/Mehmettel/sales_trainer)

Sigorta satış görüşmesinde potansiyel bir müşteri gibi davranan sohbet robotu. İnsan kullanıcı sigorta acentesi rolünde poliçe satmaya çalışır; AI müşteri doğal yanıtlar verir, sorular sorar, itirazlarını dile getirir ve sonunda karar verir.

**Repo:** https://github.com/Mehmettel/sales_trainer

## Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **LLM**: OpenAI GPT-4o-mini (JSON mode ile yapılandırılmış yanıtlar)
- **Language**: Python 3.x
- **Key Libraries**:
  - `streamlit>=1.28.0` – Web arayüzü
  - `openai>=1.0.0` – LLM entegrasyonu

## Prompt Design / İstek Tasarımı

### System Prompt
- AI potansiyel sigorta müşterisi rolünde; satış temsilcisi değil
- 7 zorunlu itiraz kategorisi: fiyat, kapsam, geçiş zorluğu, muafiyetler, güven, hasar süreci, müşteri hizmetleri
- Ruh haline göre davranış: 4 mood (Tarafsız, Şüpheci, Aceleci, Dost canlısı)
- Konuşma geçmişi ve mevcut skorlar prompt’a eklenir
- LLM yalnızca `Message` döndürür; skorlar Python’da hesaplanır

### Ruh Hali Davranışları
| Mood | Davranış |
|------|----------|
| Tarafsız | Sakin, kibar, dengeli |
| Şüpheci/Kızgın | Sabırsız, itiraz etmeye hazır |
| Aceleci | Kısa cevaplar, hızlı ikna ister |
| Dost canlısı ama temkinli | Kibar ama çok soru sorar |

## Bellek Mekanizması

### Session State
- **messages**: Konuşma geçmişi (son 10 mesaj LLM’e gönderilir)
- **annoyance_level** / **convince_level**: 0–10 arası skorlar
- **objections**: 7 kategori itiraz takibi (ele alındı mı?)
- **mood**: Konuşma boyunca sabit ruh hali
- **conversation_ended** / **decision_type**: Karar durumu

### Skor Güncelleme (Python, rule-based)
- **ConvinceLevel**: Spesifik bilgi, yapılandırılmış cevap, yardımcı dil → artış
- **AnnoyanceLevel**: Belirsiz ifadeler, baskı dili, savunmacı dil → artış
- Skorlar LLM tarafından değil, Python heuristics ile güncellenir

### Konuşma Sonlandırma
- **Kabul**: `convince_level >= 10` VE tüm itirazlar ele alınmışsa
- **Red**: `annoyance_level >= 10` ise
- Karar sonrası input kilitlenir; AI tekrar müzakere etmez

## Sınırlamalar ve İyileştirmeler

1. **Skorlama**: Keyword/pattern tabanlı; bağlam analizi sınırlı
2. **Itiraz tespiti**: Keyword matching; LLM fallback mevcut
3. **Bellek**: Son 10 mesaj; uzun konuşmalarda eski bağlam kaybolabilir
4. **Session**: Sayfa yenilendiğinde veriler kaybolur
5. **API Key**: `OPENAI_API_KEY` gerekli (secrets veya env)

## Kurulum ve Çalıştırma

### Projeyi klonlama

```bash
git clone https://github.com/Mehmettel/sales_trainer.git
cd sales_trainer
```

### Bağımlılıklar

```bash
pip install -r requirements.txt
```

### API anahtarı

OpenAI API anahtarını aşağıdaki yollardan biriyle tanımlayın:

- **Seçenek 1:** `.streamlit/secrets.toml` dosyası oluşturup `OPENAI_API_KEY = "sk-..."` ekleyin (bu dosya `.gitignore` ile takip dışıdır).
- **Seçenek 2:** Ortam değişkeni: `OPENAI_API_KEY`

### Uygulamayı çalıştırma

```bash
# Yöntem 1: Python ile
python app.py

# Yöntem 2: Streamlit CLI
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır.
