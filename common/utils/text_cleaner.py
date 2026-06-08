import re

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)

    # 🔴 Remove contact block fully
    text = re.sub(
        r"How does the user want to be contacted.*?(MS Teams|phone number).*?\d+",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # 🔴 Remove MS Teams lines
    text = re.sub(r"MS Teams.*", "", text, flags=re.IGNORECASE)

    # 🔴 Remove phone numbers
    text = re.sub(r"\+?\d{10,15}", "", text)

    # 🔴 Clean spacing
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def format_description(text):
    return clean_text(text)
