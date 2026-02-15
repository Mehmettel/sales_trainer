import streamlit as st
import json
import time
import os
from openai import OpenAI

# Sayfa yapılandırması
st.set_page_config(
    page_title="Sigorta Satış Simülasyonu",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern tasarım - Özel CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f8fafc 100%);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Başlık stili */
    h1 {
        font-weight: 700 !important;
        color: #0f172a !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem !important;
    }
    
    /* Kart stili - Metrikler için */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.05);
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }
    
    /* Progress bar container */
    .progress-container {
        margin-top: 0.5rem;
        background: #f1f5f9;
        border-radius: 8px;
        height: 8px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.5s ease;
    }
    .progress-annoyance { background: linear-gradient(90deg, #fef3c7, #f59e0b); }
    .progress-convince { background: linear-gradient(90deg, #a7f3d0, #10b981); }
    
    /* Selectbox ve input */
    .stSelectbox > div, .stChatInput > div {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 3px rgb(0 0 0 / 0.05) !important;
    }
    
    /* Chat mesajları */
    [data-testid="stChatMessage"] {
        background: white !important;
        border-radius: 16px !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 1px 3px rgb(0 0 0 / 0.06) !important;
        border: 1px solid #f1f5f9 !important;
    }
    
    /* Skor badge'leri */
    [data-testid="stChatMessage"] [data-testid="stCaptionContainer"] {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid #f1f5f9;
    }
    
    /* Divider */
    hr {
        margin: 1.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent) !important;
    }
    
    /* Buton */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.25rem !important;
        background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
        border: none !important;
        color: white !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.4);
    }
    
    /* Info/Warning kutuları */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 2px 8px rgb(0 0 0 / 0.06) !important;
    }
    
    /* Genel padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 900px !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state'i başlat
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history" not in st.session_state:
    st.session_state.history = []

if "annoyance_level" not in st.session_state:
    st.session_state.annoyance_level = 0

if "convince_level" not in st.session_state:
    st.session_state.convince_level = 0

if "conversation_ended" not in st.session_state:
    st.session_state.conversation_ended = False

if "decision_type" not in st.session_state:
    st.session_state.decision_type = None  # "accept" veya "reject"

if "objections" not in st.session_state:
    st.session_state.objections = {
        "price": False,
        "coverage": False,
        "migration": False,
        "deductibles": False,
        "trust": False,
        "claims": False,
        "support": False
    }

# 4 ruh hali (ödev gereksinimi) - konuşma başlamadan önce seçilir
MOODS = {
    "neutral": "Tarafsız – sakin ve kibar",
    "skeptical": "Şüpheci/Kızgın – sabırsız, itiraz etmeye hazır",
    "hurried": "Aceleci – kısa cevaplar, hızlı ikna istiyor",
    "friendly": "Dost canlısı ama temkinli – kibar ama çok soru soruyor"
}
if "mood" not in st.session_state:
    st.session_state.mood = "skeptical"  # Varsayılan

def detect_objection_categories(user_message):
    """
    Kullanıcı mesajını analiz ederek hangi itiraz kategorilerini ele aldığını tespit eder.
    Bir mesajda birden fazla kategori ele alınmış olabilir.
    Returns: list of category keys (e.g. ["price", "coverage"])
    """
    message_lower = user_message.lower()
    
    categories = {
        "price": ["price", "cost", "expensive", "cheap", "afford", "payment", "premium", "fee", "fiyat", "ücret", "maliyet", "pahalı", "ucuz"],
        "coverage": ["coverage", "cover", "protect", "include", "exclude", "policy", "plan", "kapsam", "koruma", "poliçe"],
        "migration": ["migration", "switch", "transfer", "change", "move", "transition", "geçiş", "değiştir", "taşı"],
        "deductibles": ["deductible", "deduction", "out-of-pocket", "kesinti", "ödediğim"],
        "trust": ["trust", "reputation", "reliable", "company", "experience", "years", "güven", "itibar", "güvenilir", "şirket"],
        "claims": ["claim", "file", "process", "reimbursement", "talepte", "tazminat", "talep"],
        "support": ["support", "help", "service", "assistance", "contact", "customer service", "destek", "yardım", "hizmet"]
    }
    
    detected = []
    for category, keywords in categories.items():
        if any(kw in message_lower for kw in keywords):
            detected.append(category)
    
    if detected:
        return detected
    
    # Hiçbir kategori bulunamazsa LLM ile tek kategori dene
    single = detect_objection_with_llm(user_message)
    return [single] if single else []

def detect_objection_with_llm(user_message):
    """
    LLM kullanarak itiraz kategorisini tespit eder (keyword-based yöntem başarısız olduğunda).
    """
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, 'secrets') else None
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return None  # API key yoksa None döndür
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""Analyze this customer message about insurance and determine which objection category it addresses.
Categories: price, coverage, migration, deductibles, trust, claims, support

Message: "{user_message}"

Respond with ONLY the category name (one word: price, coverage, migration, deductibles, trust, claims, or support).
If the message doesn't clearly fit any category, respond with "none"."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=10
        )
        
        detected = response.choices[0].message.content.strip().lower()
        
        # Geçerli kategorilerden biri mi kontrol et
        valid_categories = ["price", "coverage", "migration", "deductibles", "trust", "claims", "support"]
        if detected in valid_categories:
            return detected
        
        return None
    except Exception:
        return None  # Hata durumunda None döndür

def update_scores(user_message, assistant_message, current_convince_level, current_annoyance_level):
    """
    Python tabanlı rule-based skorlama sistemi.
    
    İyi satış davranışı ödüllendirilir:
    - Açık ve spesifik cevaplar (sayılar, örnekler, detaylar)
    - Yapılandırılmış ve profesyonel dil
    - Sorulara doğrudan yanıt verme
    
    Kötü satış davranışı cezalandırılır:
    - Belirsiz veya kaçamak cevaplar
    - Baskı dili veya agresif yaklaşım
    - Tekrar eden veya alakasız içerik
    
    Returns: (new_convince_level, new_annoyance_level)
    """
    user_lower = user_message.lower()
    assistant_lower = assistant_message.lower()
    
    convince_delta = 0
    annoyance_delta = 0
    
    # ===== CONVINCE LEVEL ARTIRICI FAKTÖRLER =====
    
    # 1. Spesifik bilgiler (sayılar, para birimleri, yüzdeler)
    has_numbers = any(char.isdigit() for char in user_message)
    has_currency = any(term in user_lower for term in ["$", "€", "₺", "tl", "usd", "eur"])
    has_percentage = "%" in user_message or "percent" in user_lower or "yüzde" in user_lower
    
    if has_numbers or has_currency or has_percentage:
        convince_delta += 2  # Spesifik bilgi = güven
    
    # 2. Yapılandırılmış cevaplar (liste, örnekler, kategoriler)
    has_structure = any(marker in user_lower for marker in [
        "first", "second", "third", "finally",
        "for example", "such as", "including",
        "birinci", "ikinci", "örneğin", "içerir"
    ])
    if has_structure:
        convince_delta += 1
    
    # 3. Uzun ve detaylı cevaplar (yeterli bilgi verme)
    word_count = len(user_message.split())
    if word_count > 30:
        convince_delta += 1  # Detaylı açıklama
    elif word_count > 20:
        convince_delta += 1  # Orta-uzun detay
    elif word_count > 10:
        convince_delta += 0.5  # Orta detay
    
    # 4. Pozitif ve yardımcı dil + güven verici ifadeler
    helpful_phrases = [
        "i can help", "let me explain", "here's how",
        "i understand", "that's a good question",
        "yardımcı olabilirim", "açıklayayım", "anlıyorum",
        "güvenebilir", "eminiz", "garantili", "kesinlikle",
        "memnun", "kaliteli", "profesyonel", "deneyim",
        "uzman", "titiz", "hızlı", "kolay"
    ]
    if any(phrase in user_lower for phrase in helpful_phrases):
        convince_delta += 1
    
    # 5. Soruya doğrudan yanıt (AI'nın sorusuna cevap verme)
    question_words = ["what", "how", "why", "when", "where", "which", "ne", "nasıl", "neden", "mi", "mu", "mı", "mü", "hangi", "nerede"]
    if any(qw in assistant_lower for qw in question_words):
        # AI soru sormuş, kullanıcı cevap vermiş mi kontrol et
        if word_count > 5:  # Yeterli uzunlukta cevap (daha esnek)
            convince_delta += 1
    
    # ===== ANNOYANCE LEVEL ARTIRICI FAKTÖRLER =====
    
    # 1. Belirsiz veya kaçamak cevaplar
    vague_phrases = [
        "i don't know", "not sure", "maybe", "perhaps", "possibly",
        "i think", "probably", "might", "could be", "unclear",
        "bilmiyorum", "emin değilim", "belki", "sanırım"
    ]
    vague_count = sum(1 for phrase in vague_phrases if phrase in user_lower)
    if vague_count >= 2:
        annoyance_delta += 2  # Çok belirsiz
    elif vague_count == 1:
        annoyance_delta += 1
    
    # 2. Çok kısa cevaplar (yetersiz bilgi)
    if word_count < 5:
        annoyance_delta += 1
    
    # 3. Baskı dili veya agresif yaklaşım
    pressure_phrases = [
        "you must", "you have to", "you should", "you need to",
        "hurry", "limited time", "last chance", "now or never",
        "yapmalısın", "yapmak zorundasın", "acele et", "son şans"
    ]
    if any(phrase in user_lower for phrase in pressure_phrases):
        annoyance_delta += 2  # Baskı = sinirlilik
    
    # 4. Savunmacı veya sorumluluktan kaçınma
    defensive_phrases = [
        "that's not my problem", "not my responsibility", "i can't help",
        "that's your issue", "not my fault",
        "benim sorunum değil", "sorumluluğum değil", "senin sorunun"
    ]
    if any(phrase in user_lower for phrase in defensive_phrases):
        annoyance_delta += 2
    
    # 5. Tekrar eden içerik (aynı şeyi söyleme)
    # Basit heuristics: çok kısa mesajlar veya aynı kelimelerin tekrarı
    if word_count < 10 and len(set(user_lower.split())) < 5:
        annoyance_delta += 1  # Çok tekrarlı
    
    # ===== CONVINCE LEVEL AZALTICI FAKTÖRLER (kötü satış davranışı) =====
    convince_penalty = 0
    
    # Olumsuz itiraf veya red
    negative_admissions = [
        "avantajımız yok", "avantajimiz yok", "we have no", "we don't have",
        "don't have", "don't know", "can't help", "cannot help",
        "bilmiyorum", "bilgim yok", "fikrim yok"
    ]
    if any(phrase in user_lower for phrase in negative_admissions):
        convince_penalty += 2  # Ciddi düşüş
    
    # Çok kısa cevaplar (yetersiz bilgi)
    if word_count < 5:
        convince_penalty += 1
    
    # Belirsiz cevap verilmişse convince artmamalı
    if vague_count >= 1:
        convince_penalty += 1
    
    # ===== SKOR HESAPLAMA (0-10 ölçeği) =====
    
    # DEBUG: Skorlama detaylarını göster (geliştirme aşamasında)
    # st.write(f"DEBUG - word_count: {word_count}, convince_delta: {convince_delta}, convince_penalty: {convince_penalty}, annoyance_delta: {annoyance_delta}")
    
    # Convince: İyi davranışta artar, kötü davranışta azalır, nötrde SABİT KALIR
    # Minimum +1 KALDIRILDI - otomatik artış yok
    net_convince = convince_delta - convince_penalty
    if net_convince > 0:
        new_convince = current_convince_level + min(2, int(net_convince))
    elif net_convince < 0:
        new_convince = current_convince_level - min(2, int(abs(net_convince)))
    else:
        new_convince = current_convince_level  # Değişmez
    new_convince = min(10, max(0, new_convince))
    
    # Annoyance level: 0-10, sadece negatif davranış varsa artır
    annoyance_increase = min(2, int(annoyance_delta))
    new_annoyance = current_annoyance_level + annoyance_increase
    new_annoyance = min(10, max(0, new_annoyance))
    
    return new_convince, new_annoyance

def get_ai_response(current_annoyance, current_convince, user_message, conversation_history, mood_key="skeptical"):
    """
    Gerçek LLM kullanarak AI yanıtı alır.
    JSON formatında yanıt döndürür ve retry mantığı içerir.
    """
    # OpenAI client'ı oluştur
    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, 'secrets') else None
    if not api_key:
        # Eğer secrets yoksa environment variable'dan dene
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        st.error("OpenAI API key bulunamadı. Lütfen OPENAI_API_KEY'i ayarlayın.")
        return {
            "Message": "API key bulunamadı."
        }
    
    client = OpenAI(api_key=api_key)
    
    # Konuşma geçmişini hazırla
    messages = []
    recent_history = conversation_history[-10:]  # Son 10 mesajı al
    
    # Conversation history'yi formatla
    chat_history_text = ""
    if recent_history:
        chat_history_text = "\nConversation history (most recent last):\n"
        for msg in recent_history:
            role_label = "User" if msg["role"] == "user" else "You (Client)"
            chat_history_text += f"- {role_label}: {msg['content']}\n"
    else:
        chat_history_text = "\nConversation history (most recent last):\n(No previous messages)\n"
    
    # Konuşma geçmişi (user_message zaten conversation_history'de, tekrar ekleme)
    for msg in recent_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Ruh haline göre davranış kuralları (ödev: 4 mood)
    MOOD_BEHAVIOR = {
        "neutral": "Calm and polite. Give balanced, thoughtful responses.",
        "skeptical": "Impatient, ready to object. Be direct and questioning.",
        "hurried": "Give SHORT answers. Want quick persuasion. Be brief.",
        "friendly": "Polite but cautious. Ask MANY questions. Warm but careful."
    }
    mood_behavior = MOOD_BEHAVIOR.get(mood_key, MOOD_BEHAVIOR["skeptical"])
    mood_display = MOODS.get(mood_key, "Şüpheci")
    
    system_prompt = f"""You are an AI acting as a potential insurance CLIENT (not a sales agent) in a sales conversation.

CRITICAL: You are the CUSTOMER who is being sold insurance. The USER is the SALES AGENT trying to convince YOU.
You MUST act as a skeptical client who asks questions and raises objections.
DO NOT try to sell insurance. DO NOT initiate sales conversation. RESPOND to what the sales agent tells you.

Your MOOD is: {mood_display}. {mood_behavior}
{chat_history_text}

User message (from the SALES AGENT):
"{user_message}"

ROLE & BEHAVIOR
- You are the CUSTOMER, NOT a sales agent.
- The USER is the sales agent trying to sell you insurance.
- You are skeptical and need to be convinced.
- WAIT for the sales agent to explain, then ASK QUESTIONS or RAISE OBJECTIONS.
- Your mood is fixed for the entire conversation and must influence tone and verbosity.
- You must behave like a real human client, not like a checklist.

Current conversation state:
- Mood: {mood_display}
- AnnoyanceLevel: {current_annoyance}
- ConvinceLevel: {current_convince}

Behavior rules reminder:
- Do not ask more than two questions.
- Prefer follow-up questions over new topics.
- Adjust tone based on the current levels above.

CONVERSATION FLOW
- The USER (sales agent) will speak first with offers/pitches. YOU respond as the customer.
- Focus on one or two concerns at a time.
- NEVER raise more than TWO objection topics in a single response.
- Prioritize follow-up questions based on the user's most recent response.
- Do NOT introduce new objection categories unless the previous concern has been sufficiently addressed.
- Avoid listing all concerns at once.
- WAIT for the sales agent to make a pitch, THEN ask questions or express concerns.

MANDATORY OBJECTION CATEGORIES
You are a CUSTOMER, not a sales agent. WAIT for the sales agent to answer your questions.
You must eventually ask about all of the following before accepting:
1. Price - "How much does it cost?"
2. Coverage - "What does it cover?"
3. Migration difficulty - "How hard is it to switch?"
4. Deductibles - "What are the deductibles?"
5. Trust in the provider - "Why should I trust your company?"
6. Claim settlement process - "How do claims work?"
7. Customer service and reviews - "What about customer service?"

ASK these questions; DO NOT answer them. The USER will answer.

TONE CONTROL
- As ConvinceLevel increases, become slightly more open and collaborative.
- As AnnoyanceLevel increases, become shorter, more direct, and less patient.
- Do NOT use hard rejection language unless AnnoyanceLevel is 7 or higher.
- Remain within your initial mood at all times.

MEMORY USAGE
- Remember earlier statements made by the user.
- Refer back to them when relevant.
- Evaluate the user's consistency and clarity over time.

DECISION RULES
- Do NOT finalize a decision on your own.
- Acceptance or rejection will be handled by system logic.
- Once a decision is made, you must not re-engage or negotiate further.

OUTPUT FORMAT (STRICT)
You MUST respond ONLY in the following JSON format:

{{
  "Message": "..."
}}

No text is allowed outside this JSON structure.

Respond as the insurance client.
Follow all rules above strictly.
Return ONLY valid JSON with the Message field."""
    
    messages.insert(0, {
        "role": "system",
        "content": system_prompt
    })
    
    # Retry mantığı ile LLM çağrısı
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # veya "gpt-3.5-turbo" daha ucuz için
                messages=messages,
                response_format={"type": "json_object"},  # JSON formatını zorla
                temperature=0.7
            )
            
            # JSON'u parse et
            response_text = response.choices[0].message.content
            parsed_response = json.loads(response_text)
            
            # Gerekli anahtarları kontrol et (Message veya message)
            msg_content = parsed_response.get("Message") or parsed_response.get("message")
            if not msg_content:
                raise ValueError("Eksik anahtar: Message gerekli")
            
            # Sadece Message döndür, skorlar Python tarafında hesaplanacak
            return {
                "Message": msg_content if isinstance(msg_content, str) else str(msg_content)
            }
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                st.error(f"JSON parse hatası (deneme {attempt + 1}/{max_retries}): {str(e)}")
                # Fallback yanıt
                return {
                    "Message": "Üzgünüm, yanıt işlenirken bir hata oluştu. Lütfen tekrar deneyin."
                }
        
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                st.error(f"LLM çağrısı hatası (deneme {attempt + 1}/{max_retries}): {str(e)}")
                # Fallback yanıt
                return {
                    "Message": "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin."
                }
    
    # Tüm denemeler başarısız olduysa fallback
    return {
        "Message": "Üzgünüm, yanıt alınamadı. Lütfen tekrar deneyin."
    }

def check_conversation_end():
    """
    Konuşmanın bitip bitmediğini kontrol eder ve karar verir.
    Returns: (ended: bool, decision_type: str or None)
    """
    # Eğer zaten bitmişse, mevcut kararı döndür
    if st.session_state.conversation_ended:
        return True, st.session_state.decision_type
    
    # Annoyance seviyesi kontrolü
    if st.session_state.annoyance_level >= 10:
        st.session_state.conversation_ended = True
        st.session_state.decision_type = "reject"
        return True, "reject"
    
    # Convince seviyesi ve tüm itirazlar kontrolü
    all_objections_addressed = all(st.session_state.objections.values())
    if st.session_state.convince_level >= 10 and all_objections_addressed:
        st.session_state.conversation_ended = True
        st.session_state.decision_type = "accept"
        return True, "accept"
    
    return False, None

# Başlık
st.markdown("""
<div style="margin-bottom: 2rem;">
    <h1 style="font-size: 1.75rem; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-size: 2rem;">💬</span> Sigorta Satış Simülasyonu
    </h1>
    <p style="color: #64748b; font-size: 0.9rem; margin-top: 0.25rem;">Müşteriyi ikna etmeye çalışın — AI şüpheci bir sigorta müşterisi gibi davranacak</p>
</div>
""", unsafe_allow_html=True)

# Ruh hali seçimi (sadece konuşma başlamadan önce)
if len(st.session_state.messages) == 0 and not st.session_state.conversation_ended:
    st.session_state.mood = st.selectbox(
        "Müşteri ruh halini seçin (konuşma boyunca sabit kalacak)",
        options=list(MOODS.keys()),
        format_func=lambda x: MOODS[x],
        index=list(MOODS.keys()).index(st.session_state.mood)
    )

# Üstte ruh hali ve skorlar - Modern kartlar
if not st.session_state.conversation_ended:
    mood_display = MOODS.get(st.session_state.get("mood", "skeptical"), "Şüpheci")
    ann = st.session_state.annoyance_level / 10
    conv = st.session_state.convince_level / 10
    
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
        <div class="metric-card">
            <div class="metric-label">Ruh Hali</div>
            <div class="metric-value" style="font-size: 1rem; font-weight: 600;">{mood_display}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Rahatsızlık Seviyesi</div>
            <div class="metric-value">{st.session_state.annoyance_level}/10</div>
            <div class="progress-container">
                <div class="progress-fill progress-annoyance" style="width: {ann*100}%;"></div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">İkna Seviyesi</div>
            <div class="metric-value">{st.session_state.convince_level}/10</div>
            <div class="progress-container">
                <div class="progress-fill progress-convince" style="width: {conv*100}%;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Konuşma alanı
if st.session_state.messages:
    st.markdown('<p style="color: #64748b; font-size: 0.8rem; font-weight: 600; margin: 1.5rem 0 1rem 0;">KONUŞMA GEÇMİŞİ</p>', unsafe_allow_html=True)
elif not st.session_state.conversation_ended:
    st.markdown("""
    <div style="background: white; border-radius: 16px; padding: 2rem; text-align: center; border: 1px dashed #e2e8f0; margin: 1.5rem 0;">
        <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">👋 Aşağıdaki kutuya ilk mesajınızı yazarak konuşmayı başlatın</p>
        <p style="color: #cbd5e1; font-size: 0.8rem; margin-top: 0.5rem;">Müşteri fiyat, kapsam, geçiş süreci ve daha fazlası hakkında sorular soracak</p>
    </div>
    """, unsafe_allow_html=True)

# Konuşma geçmişini göster
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # AI mesajları için skorları göster
        if message["role"] == "assistant":
            # Mesajda skor bilgisi varsa onu kullan, yoksa mevcut skorları göster
            annoyance = message.get("annoyance_level", st.session_state.annoyance_level)
            convince = message.get("convince_level", st.session_state.convince_level)
            
            # Skorları göster
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"**Ruh Hali:** {MOODS.get(st.session_state.get('mood', 'skeptical'), 'Şüpheci')}")
            with col2:
                st.caption(f"**Rahatsızlık:** {annoyance}/10")
            with col3:
                st.caption(f"**İkna:** {convince}/10")

# Konuşma bitmişse bilgi göster
if st.session_state.conversation_ended:
    if st.session_state.decision_type == "accept":
        st.success("✅ **Tebrikler!** Sigorta kabul edildi. Müşteriyi başarıyla ikna ettiniz.")
    elif st.session_state.decision_type == "reject":
        st.error("❌ **Konuşma sona erdi.** Sigorta reddedildi. Müşteri ikna olmadı.")
    st.markdown("---")
    if st.button("🔄 Yeni Konuşma Başlat"):
        # Sadece uygulama anahtarlarını temizle (Streamlit dahili anahtarlarına dokunma)
        app_keys = ["messages", "history", "annoyance_level", "convince_level", 
                    "conversation_ended", "decision_type", "objections", "mood"]
        for key in app_keys:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Kullanıcı girişi (sadece konuşma bitmemişse göster)
if not st.session_state.conversation_ended:
    if prompt := st.chat_input("Satış temsilcisi olarak yanıtınızı yazın..."):
        # Kullanıcı mesajını ekle
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Kullanıcı mesajını göster
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Itiraz kategorilerini tespit et ve işaretle (bir mesajda birden fazla olabilir)
        for cat in detect_objection_categories(prompt):
            if cat in st.session_state.objections:
                st.session_state.objections[cat] = True
        
        # Konuşma devam ediyor, AI yanıtını al
        ai_response = get_ai_response(
            st.session_state.annoyance_level,
            st.session_state.convince_level,
            prompt,
            st.session_state.messages,
            st.session_state.mood
        )
        response = ai_response["Message"]
        
        # Python tabanlı skorlama sistemi ile skorları güncelle
        old_convince = st.session_state.convince_level
        old_annoyance = st.session_state.annoyance_level
        
        new_convince, new_annoyance = update_scores(
            prompt,  # user_message
            response,  # assistant_message (AI'nın yanıtı)
            st.session_state.convince_level,
            st.session_state.annoyance_level
        )
        
        # DEBUG: Skor değişimini göster
        if new_convince != old_convince or new_annoyance != old_annoyance:
            st.toast(f"📊 Skorlar güncellendi! İkna: {old_convince} → {new_convince}, Rahatsızlık: {old_annoyance} → {new_annoyance}", icon="✅")
        else:
            st.toast(f"📊 Skorlar değişmedi (İkna: {old_convince}, Rahatsızlık: {old_annoyance})", icon="ℹ️")
        
        # Skorları session state'e kaydet
        st.session_state.convince_level = new_convince
        st.session_state.annoyance_level = new_annoyance
        
        # Konuşmanın bitip bitmediğini kontrol et
        ended, decision_type = check_conversation_end()
        
        if ended:
            # Konuşma bitti, karar mesajını göster
            if decision_type == "accept":
                decision_message = "✅ **Kabul Edildi!** Tüm sorularınız yanıtlandı ve sigortayı kabul etmeye karar verdiniz."
            elif decision_type == "reject":
                decision_message = "❌ **Reddedildi!** Yeterli bilgi alamadığınız için sigortayı reddetmeye karar verdiniz."
            else:
                decision_message = "Konuşma sona erdi."
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": decision_message,
                "annoyance_level": st.session_state.annoyance_level,
                "convince_level": st.session_state.convince_level
            })
            with st.chat_message("assistant"):
                st.markdown(decision_message)
                # Skorları göster
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"**Ruh Hali:** {MOODS.get(st.session_state.get('mood', 'skeptical'), 'Şüpheci')}")
                with col2:
                    st.caption(f"**Rahatsızlık:** {st.session_state.annoyance_level}/10")
                with col3:
                    st.caption(f"**İkna:** {st.session_state.convince_level}/10")
            st.rerun()  # Sayfayı yenile ki input kilitlensin
        else:
            # Asistan mesajını ekle (skorları da kaydet)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response,
                "annoyance_level": st.session_state.annoyance_level,
                "convince_level": st.session_state.convince_level
            })
    
            # Asistan mesajını göster
            with st.chat_message("assistant"):
                st.markdown(response)
                # Skorları göster
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"**Ruh Hali:** {MOODS.get(st.session_state.get('mood', 'skeptical'), 'Şüpheci')}")
                with col2:
                    st.caption(f"**Rahatsızlık:** {st.session_state.annoyance_level}/10")
                with col3:
                    st.caption(f"**İkna:** {st.session_state.convince_level}/10")
            
            # Üstteki metrikleri güncellemek için rerun (skorlar değişti)
            st.rerun()


if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    sys.argv = ["streamlit", "run", __file__]
    stcli.main()
