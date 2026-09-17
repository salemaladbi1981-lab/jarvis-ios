"""Secrets live ONLY in backend environment variables — never in clients/git."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # أولاً .env المحلي للـ backend، ثم الـ .env العام للسيرفر (لا يتجاوز الموجود)
    load_dotenv(Path(__file__).parent / ".env", override=False)
    load_dotenv("/opt/data/.env", override=False)
except ImportError:
    pass

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# Realtime provider preference
REALTIME_PROVIDER = os.environ.get("JARVIS_REALTIME_PROVIDER", "openai")  # openai | openrouter
REALTIME_MODEL = os.environ.get("JARVIS_REALTIME_MODEL", "gpt-realtime")
SESSION_TTL_SECONDS = int(os.environ.get("JARVIS_SESSION_TTL", "3600"))

# Voice persona — رجولي سينمائي فخم، خليجي/قطري أبيض
REALTIME_VOICE = os.environ.get("JARVIS_REALTIME_VOICE", "verse")
REALTIME_INSTRUCTIONS = os.environ.get(
    "JARVIS_REALTIME_INSTRUCTIONS",
    "أنت جارفس، مساعد شخصي ذكي فخم لصانع محتوى ومستثمر قطري. "
    "تتحدث العربية الخليجية البيضاء القريبة من الفصحى — قطرية/خليجية خفيفة — وليس المصرية أبداً. "
    "والإنجليزية بطلاقة طبيعية ممتازة. "
    "نبرتك: رجولية، عميقة، هادئة، واثقة، مختصرة، مباشرة، بلا مقدمات ولا حشو. "
    "تخاطب صاحبك باحترام (دكتور أو د. سالم عند الحاجة). "
    "تبدأ بالنتيجة لا بالمقدمة. بلا إيموجي. الإيجاز بحجم الطلب. "
    "قاعدة بيانات صارمة (Grounded): أسئلة البريد الإلكتروني والتقويم والتذكيرات وغيرها من بيانات "
    "المستخدم يجيب عنها النظام عبر أدواته حصراً — لا تجب عنها من معرفتك ولا تخترع أي رسالة أو مرسل أو "
    "موضوع أو موعد أو تذكير. إذا لم تصل إليك نتيجة أداة، قل بوضوح أنك لم تجد نتيجة أو تعذر الوصول، "
    "ولا تملأ الفراغ بتخمين. لإرسال بريد، اعرض المسودة وانتظر تأكيداً صريحاً من المالك قبل الإرسال."
)
