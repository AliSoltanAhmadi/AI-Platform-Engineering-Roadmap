#!/usr/bin/env python3
"""Small bilingual UI catalog for terminal guidance and recovery messages."""
from __future__ import annotations


SUPPORTED_LANGUAGES = ("en", "fa")


_FA = {
    "title": "ابزار یادگیری مهندسی پلتفرم هوش مصنوعی",
    "tagline": "یک مسیر عملی از DevOps/Platform/SRE به MLOps و LLMOps.",
    "phases": "مرحله‌ها: P0 ← P1 ← P2 ← P3 ← P4 ← P5",
    "next_start": "اقدام بعدی: گزینه ۱ را انتخاب کنید؛ پیشرفت شما خودکار ذخیره می‌شود.",
    "next_answer": "اقدام بعدی: پاسخ خود را وارد کنید؛ برای دیدن راه‌حل بنویسید: show answer",
    "next_quiz": "اقدام بعدی: به همه سؤال‌ها پاسخ دهید؛ پاسخ‌های درست ذخیره می‌شوند.",
    "next_assessment": "اقدام بعدی: برای هر سؤال فقط A یا B را انتخاب کنید.",
    "menu": "منوی اصلی:",
    "menu_1": "  1. ادامه مسیر",
    "menu_2": "  2. نمایش پیشرفت",
    "menu_3": "  3. انتخاب مسیر",
    "menu_4": "  4. مرور مرحله قبلی",
    "menu_5": "  5. خروج",
    "menu_6": "  6. پرسش درباره نقشه راه",
    "menu_7": "  7. پاک‌کردن همه پیشرفت",
    "menu_8": "  8. آزمون پیش/پس یادگیری",
    "menu_prompt": "یک گزینه از ۱ تا ۸ انتخاب کنید: ",
    "next_menu": "اقدام بعدی: شماره گزینه موردنظر را وارد کنید.",
    "select_level_prompt": "سطح را انتخاب کنید (1 مبتدی، 2 متوسط، 3 باتجربه): ",
    "selected_level": "سطح انتخاب‌شده: {level}",
    "goodbye": "خداحافظ. پیشرفت شما ذخیره شد. ✓",
    "active_model": "مدل محلی فعال: {backend}/{model}",
    "inference_ollama": "محدوده استنتاج: Ollama محلی با دانش‌نامه محلی.",
    "inference_vllm": "محدوده استنتاج: vLLM محلی با دانش‌نامه محلی.",
    "inference_fallback": "محدوده استنتاج: پاسخ‌گوی قطعی دانش‌نامه محلی؛ بدون اینترنت.",
    "correct": "درست است. پیشرفت ذخیره شد. ✓",
    "why_correct": "چرا درست است: {reason}",
    "empty_what": "پاسخی وارد نشد و پیشرفت کامل نشد.",
    "empty_why": "پاسخ خالی نمی‌تواند فرمان خواسته‌شده را نشان دهد.",
    "empty_next": "یک فرمان از درس وارد و دوباره ارسال کنید.",
    "incorrect_what": "پاسخ نادرست بود. {reason}",
    "incorrect_why": "پاسخ با فرمان یا مفهوم موردنیاز درس مطابقت نداشت.",
    "incorrect_next": "از راهنما استفاده کنید، پاسخ را اصلاح کنید و دوباره تلاش کنید.",
    "baseline_saved": "خط پایه ثبت شد و مانع ادامه مسیر نیست.",
    "assessment_instruction": "به هر ۱۰ سؤال پاسخ دهید؛ هر موضوع فقط یک‌بار آمده است.",
    "assessment_choice": "A یا B را انتخاب کنید: ",
    "progress_heading": "پیشرفت:",
    "next_stage": "  مرحله بعدی: {stage}",
    "what": "چه شد؟ {message}",
    "why": "چرا؟ {message}",
    "next": "حالا چه کار کنم؟ {message}",
    "invalid_menu_what": "گزینه منو معتبر نیست.",
    "invalid_menu_why": "منو فقط گزینه‌های ۱ تا ۸ را می‌پذیرد.",
    "invalid_menu_next": "یک عدد از ۱ تا ۸ وارد کنید.",
    "invalid_assessment_what": "پاسخ آزمون معتبر نیست.",
    "invalid_assessment_why": "این سؤال فقط پاسخ A یا B می‌پذیرد.",
    "invalid_assessment_next": "A یا B را وارد کنید.",
    "level_what": "سطح انتخاب نشد.",
    "level_why": "ورودی با سطح‌های موجود مطابقت ندارد.",
    "level_next": "۱، ۲، ۳ یا نام انگلیسی سطح را وارد کنید.",
    "missing_level_what": "اجرای غیرتعاملی سطح ندارد.",
    "missing_level_why": "گزینه --level الزامی است.",
    "missing_level_next": "دوباره با --level 1 اجرا کنید.",
    "missing_answer_what": "اجرای غیرتعاملی پاسخ ندارد.",
    "missing_answer_why": "گزینه --answer الزامی است.",
    "missing_answer_next": "دوباره با --answer و پاسخ تمرین اجرا کنید.",
    "eof_what": "ورودی پیش از پایان این مرحله قطع شد.",
    "eof_why": "ترمینال دیگر ورودی قابل خواندن دریافت نکرد.",
    "eof_next": "فرمان learn start را دوباره اجرا کنید؛ پیشرفت ذخیره‌شده ادامه پیدا می‌کند.",
    "content_what": "محتوای نقشه راه در دسترس نیست.",
    "content_why": "{reason}",
    "content_next": "فایل‌های content را بررسی کنید و سپس به منو برگردید.",
    "locked_what": "آزمون پایانی هنوز قفل است.",
    "locked_why": "همه درس‌ها و سؤال‌های quiz هنوز کامل نشده‌اند.",
    "locked_next": "گزینه ۱ را انتخاب کنید و مرحله بعدی مسیر را کامل کنید.",
    "no_path_what": "هنوز مسیری انتخاب نشده است.",
    "no_path_why": "آزمون به سطح انتخاب‌شده وابسته است.",
    "no_path_next": "ابتدا گزینه ۳ را انتخاب کنید.",
    "fatal_what": "پیشرفت بارگذاری یا ذخیره نشد.",
    "fatal_why": "{reason}",
    "fatal_next": "مجوز فایل و کامل‌بودن content را بررسی کنید و دوباره اجرا کنید.",
}


class Translator:
    def __init__(self, language="en"):
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        self.language = language

    def text(self, key, english, **values):
        template = _FA.get(key, english) if self.language == "fa" else english
        return template.format(**values)

    @property
    def is_farsi(self):
        return self.language == "fa"


def structured_error(output, translator, what, why, next_action):
    """Render every recoverable failure with what/why/next guidance."""
    output(translator.text("what", "What happened? {message}", message=what))
    output(translator.text("why", "Why? {message}", message=why))
    output(translator.text("next", "What should I do now? {message}", message=next_action))
