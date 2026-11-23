from __future__ import annotations

import argparse
import re
from pathlib import Path

from argostranslate import package, translate

MODEL_VERSION = "1.5"
SOCIAL_LINKS = (
    "https://t.me/drghanizade",
    "https://www.instagram.com/dr.ghanizade",
    "https://x.com/DrGhanizadeh",
    "https://www.linkedin.com/in/drghanizade",
    "https://www.tradingview.com/u/DrGhanizadeh",
    "https://farcaster.xyz/drghanizade",
    "https://github.com/ghanizade-web",
)
SOCIAL_LABELS = {
    "Telegram": "تلگرام",
    "Instagram": "اینستاگرام",
    "LinkedIn": "لینکدین",
    "TradingView": "تریدینگ‌ویو",
    "Farcaster": "فارکستر",
    "GitHub": "گیت‌هاب",
}
PERSIAN_RUN = re.compile(r"[\u0600-\u06FF\u200c]+")
PRESERVED = re.compile(
    r"ZXQSOCIAL\d{2}XZQ"
    r"|\*\*"
    r"|\d+(?:[.,:/-]\d+)*%?"
    r"|(?<![A-Za-z])[A-Z][A-Z0-9.-]{1,12}(?:/[A-Z0-9.-]{1,12})?"
    r"|[\u0600-\u06FF\u200c]+"
)
ENGLISH_WORD = re.compile(r"(?<![A-Za-z])[A-Za-z]{3,}(?![A-Za-z])")
URL = re.compile(r"https?://\S+")


def ensure_model() -> None:
    installed = package.get_installed_packages()
    if any(
        item.from_code == "en"
        and item.to_code == "fa"
        and item.package_version == MODEL_VERSION
        for item in installed
    ):
        return
    available = package.get_available_packages()
    model = next(
        (
            item
            for item in available
            if item.from_code == "en"
            and item.to_code == "fa"
            and item.package_version == MODEL_VERSION
        ),
        None,
    )
    if model is None:
        raise RuntimeError("ARGOS_EN_FA_MODEL_NOT_FOUND")
    package.install_from_path(model.download())


def prepare_report(text: str) -> str:
    # The appended source appendix repeats stories already present in the report body.
    appendix = "\n## خبرهای اثرگذار و مسیر اثر بر دارایی‌ها"
    if appendix in text:
        text = text.split(appendix, 1)[0]

    # Keep only official profile links in Telegram. Story links remain in the
    # source JSON and workflow artifact for verification.
    for index, link in enumerate(SOCIAL_LINKS):
        text = text.replace(link, f"ZXQSOCIAL{index:02d}XZQ")

    cleaned: list[str] = []
    for line in text.splitlines():
        if "لینک راستی‌آزمایی" in line:
            continue
        cleaned.append(URL.sub("", line))
    return "\n".join(cleaned)


def translate_segmented(text: str) -> str:
    output: list[str] = []
    start = 0
    for match in PRESERVED.finditer(text):
        segment = text[start:match.start()]
        output.append(
            translate.translate(segment, "en", "fa")
            if re.search(r"[A-Za-z]", segment)
            else segment
        )
        output.append(match.group(0))
        start = match.end()
    tail = text[start:]
    output.append(
        translate.translate(tail, "en", "fa")
        if re.search(r"[A-Za-z]", tail)
        else tail
    )
    return "".join(output)


def translate_report(text: str) -> tuple[str, int]:
    prepared = prepare_report(text)
    translated_lines: list[str] = []
    dropped = 0

    for line in prepared.splitlines():
        translated = translate_segmented(line) if re.search(r"[A-Za-z]", line) else line
        for source, target in SOCIAL_LABELS.items():
            translated = translated.replace(source, target)

        # Fail closed on English sentence fragments so untranslated RSS headlines
        # are not sent to Telegram. Keep common market acronyms and asset symbols.
        residual = [
            word
            for word in ENGLISH_WORD.findall(translated)
            if word.upper()
            not in {
                "GRIOS", "CFTC", "FRED", "EIA", "SEC", "ETF", "ETFS", "USD",
                "EUR", "JPY", "BTC", "ETH", "AI", "GDP", "CPI", "PPI",
                "OPEC", "FED",
            }
        ]
        if len(residual) >= 4:
            translated = "خبر انگلیسی به‌دلیل اطمینان پایین از ترجمهٔ ماشینی از نسخهٔ تلگرام حذف شد."
            dropped += 1
        translated_lines.append(translated)

    result = "\n".join(translated_lines).strip()
    if dropped:
        result += (
            "\n\n⚠️ بخشی از گزیده‌های انگلیسی به‌دلیل اطمینان پایین از ترجمه حذف شد؛ "
            "جزئیات منبع در پیوست اجرای GitHub نگهداری می‌شود."
        )
    result += (
        "\n\n⚙️ ترجمه با مدل آفلاین و رایگان انجام شده است؛ "
        "برای تصمیم‌گیری مالی، اعداد و روایت خبر را با منابع اصلی تطبیق دهید."
    )
    return result, dropped


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate the GRIOS report to Persian offline")
    parser.add_argument("--input", default="reports/latest.txt")
    parser.add_argument("--output", default="reports/latest.txt")
    args = parser.parse_args()

    source = Path(args.input)
    destination = Path(args.output)
    if not source.is_file():
        raise SystemExit("REPORT_NOT_FOUND")

    ensure_model()
    translated, dropped = translate_report(source.read_text(encoding="utf-8"))
    if not translated or not PERSIAN_RUN.search(translated):
        raise SystemExit("PERSIAN_TRANSLATION_EMPTY")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(translated + "\n", encoding="utf-8")
    print("PERSIAN_REPORT_READY=true")
    print(f"UNTRANSLATED_LINES_DROPPED={dropped}")
    print(f"REPORT_CHARACTERS={len(translated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
