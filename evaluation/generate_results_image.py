"""Generate a visual summary of evaluation/results.csv."""
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "evaluation" / "results.csv"
OUTPUT_PATH = ROOT / "evaluation" / "results_visualization.png"
CATEGORIES = [
    "Account Enquiry",
    "Loan Enquiry",
    "Credit-card Enquiry",
    "Transaction Enquiry",
    "Investment Enquiry",
]
CATEGORY_LABELS = {
    "Account Enquiry": "Account\nEnquiry",
    "Loan Enquiry": "Loan\nEnquiry",
    "Credit-card Enquiry": "Credit-card\nEnquiry",
    "Transaction Enquiry": "Transaction\nEnquiry",
    "Investment Enquiry": "Investment\nEnquiry",
}
QUERY_TYPES = ["Normal", "Curated", "Edge case", "Informal"]
COLORS = {
    "background": "#F3F6F4",
    "ink": "#17272E",
    "muted": "#64727A",
    "panel": "#FFFFFF",
    "border": "#D9E2DE",
    "teal": "#117768",
    "teal_dark": "#0D564D",
    "red": "#A93D35",
    "red_light": "#F6E3E0",
    "track": "#E8EEEB",
    "header": "#10252C",
    "accent": "#91D5BD",
}
WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")


def load_font(size, bold=False):
    font_name = "seguisb.ttf" if bold else "segoeui.ttf"
    font_path = WINDOWS_FONT_DIR / font_name
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def draw_centered(draw, bounds, text, font, fill, spacing=3):
    left, top, right, bottom = bounds
    text_bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    text_width = text_bounds[2] - text_bounds[0]
    text_height = text_bounds[3] - text_bounds[1]
    x = left + (right - left - text_width) / 2 - text_bounds[0]
    y = top + (bottom - top - text_height) / 2 - text_bounds[1]
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing, align="center")


def main():
    with RESULTS_PATH.open(encoding="utf-8", newline="") as results_file:
        rows = list(csv.DictReader(results_file))
    if not rows:
        raise ValueError(f"No evaluation rows found in {RESULTS_PATH}")

    matrix = defaultdict(lambda: defaultdict(int))
    support = defaultdict(int)
    correct_by_category = defaultdict(int)
    type_support = defaultdict(int)
    correct_by_type = defaultdict(int)
    for row in rows:
        expected = row["expected_category"]
        predicted = row["predicted_category"]
        query_type = row["query_type"]
        matrix[expected][predicted] += 1
        support[expected] += 1
        type_support[query_type] += 1
        if row["correct"].strip().lower() == "true":
            correct_by_category[expected] += 1
            correct_by_type[query_type] += 1

    correct_count = sum(row["correct"].strip().lower() == "true" for row in rows)
    incorrect_rows = [row for row in rows if row["correct"].strip().lower() != "true"]
    fallback_rows = [
        row for row in rows
        if row["reason"].startswith("The query contains terms and intent that most strongly match")
    ]
    width, height = 1800, 1390
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)

    font_title = load_font(42, bold=True)
    font_heading = load_font(22, bold=True)
    font_label = load_font(15, bold=True)
    font_body = load_font(17)
    font_small = load_font(14)
    font_value = load_font(39, bold=True)
    font_cell = load_font(28, bold=True)

    draw.rectangle((0, 0, width, 170), fill=COLORS["header"])
    draw.rectangle((0, 164, width, 170), fill=COLORS["accent"])
    draw.text((72, 42), "FSIS  /  EVALUATION RESULTS", font=font_title, fill=COLORS["panel"])
    draw.text(
        (76, 108),
        f"Financial query intent classification  |  {len(rows)} evaluated queries",
        font=font_body,
        fill="#C9D8D4",
    )

    accuracy = correct_count / len(rows) * 100
    summary_cards = [
        ("OVERALL ACCURACY", f"{accuracy:.2f}%", f"{correct_count} correct of {len(rows)}"),
        ("QUERIES", str(len(rows)), "rows in results.csv"),
        ("INCORRECT", str(len(incorrect_rows)), "see error IDs below"),
        ("RECOVERY FALLBACK", str(len(fallback_rows)), "rule-based recovery result(s)"),
    ]
    card_left = 72
    card_gap = 20
    card_width = (width - 2 * card_left - 3 * card_gap) // 4
    for index, (label, value, note) in enumerate(summary_cards):
        left = card_left + index * (card_width + card_gap)
        draw.rounded_rectangle(
            (left, 205, left + card_width, 338),
            radius=10,
            fill=COLORS["panel"],
            outline=COLORS["border"],
            width=2,
        )
        draw.text((left + 22, 222), label, font=font_label, fill=COLORS["muted"])
        draw.text((left + 22, 248), value, font=font_value, fill=COLORS["teal_dark"])
        draw.text((left + 24, 304), note, font=font_small, fill=COLORS["muted"])

    draw.text((72, 382), "CONFUSION MATRIX", font=font_heading, fill=COLORS["ink"])
    draw.text(
        (72, 414),
        "Rows are expected categories; columns are predicted categories.",
        font=font_small,
        fill=COLORS["muted"],
    )

    grid_x = 348
    grid_y = 518
    cell_width = 138
    cell_height = 76
    cell_gap = 7
    draw.text((76, 488), "EXPECTED", font=font_label, fill=COLORS["muted"])
    draw_centered(
        draw,
        (grid_x, 442, grid_x + cell_width * len(CATEGORIES) + cell_gap * (len(CATEGORIES) - 1), 467),
        "PREDICTED CATEGORY",
        font_label,
        COLORS["muted"],
    )

    for column_index, category in enumerate(CATEGORIES):
        left = grid_x + column_index * (cell_width + cell_gap)
        draw_centered(
            draw,
            (left, 470, left + cell_width, 514),
            CATEGORY_LABELS[category],
            font_small,
            COLORS["ink"],
        )

    for row_index, actual in enumerate(CATEGORIES):
        top = grid_y + row_index * (cell_height + cell_gap)
        draw.multiline_text(
            (76, top + 17),
            CATEGORY_LABELS[actual],
            font=font_body,
            fill=COLORS["ink"],
            spacing=2,
        )
        for column_index, predicted in enumerate(CATEGORIES):
            left = grid_x + column_index * (cell_width + cell_gap)
            value = matrix[actual][predicted]
            if actual == predicted:
                fill = COLORS["teal"]
                text_fill = COLORS["panel"]
            elif value:
                fill = COLORS["red_light"]
                text_fill = COLORS["red"]
            else:
                fill = COLORS["panel"]
                text_fill = COLORS["muted"]
            draw.rounded_rectangle(
                (left, top, left + cell_width, top + cell_height),
                radius=8,
                fill=fill,
                outline=COLORS["border"],
                width=1,
            )
            draw_centered(
                draw,
                (left, top, left + cell_width, top + cell_height),
                str(value),
                font_cell,
                text_fill,
            )

    panel_left = 1115
    panel_top = 445
    panel_right = 1728
    panel_bottom = 918
    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=10,
        fill=COLORS["panel"],
        outline=COLORS["border"],
        width=2,
    )
    draw.text((panel_left + 26, panel_top + 24), "PER-CLASS ACCURACY", font=font_heading, fill=COLORS["ink"])
    bar_left = panel_left + 28
    bar_right = panel_right - 112
    bar_width = bar_right - bar_left
    for index, category in enumerate(CATEGORIES):
        y = panel_top + 88 + index * 68
        score = correct_by_category[category] / support[category] if support[category] else 0
        label = category.replace(" Enquiry", "")
        draw.text((bar_left, y), label, font=font_small, fill=COLORS["ink"])
        draw.text((panel_right - 96, y), f"{score * 100:.2f}%", font=font_small, fill=COLORS["teal_dark"])
        draw.rounded_rectangle((bar_left, y + 27, bar_right, y + 40), radius=6, fill=COLORS["track"])
        fill_right = bar_left + int(bar_width * score)
        draw.rounded_rectangle((bar_left, y + 27, fill_right, y + 40), radius=6, fill=COLORS["teal"])

    draw.text((72, 972), "SCORES BY QUERY TYPE", font=font_heading, fill=COLORS["ink"])
    type_gap = 18
    type_width = (width - 144 - type_gap * 3) // 4
    for index, query_type in enumerate(QUERY_TYPES):
        left = 72 + index * (type_width + type_gap)
        total = type_support[query_type]
        type_accuracy = correct_by_type[query_type] / total * 100 if total else 0
        draw.rounded_rectangle(
            (left, 1010, left + type_width, 1110),
            radius=8,
            fill=COLORS["panel"],
            outline=COLORS["border"],
            width=1,
        )
        draw.text((left + 18, 1025), query_type.upper(), font=font_label, fill=COLORS["muted"])
        draw.text(
            (left + 18, 1054),
            f"{type_accuracy:.2f}%  ({correct_by_type[query_type]}/{total})",
            font=load_font(23, bold=True),
            fill=COLORS["teal_dark"],
        )

    error_ids = ", ".join(row["id"] for row in incorrect_rows) or "None"
    draw.rounded_rectangle(
        (72, 1140, width - 72, 1305),
        radius=8,
        fill="#F8EBE8",
        outline="#EBD0CB",
        width=1,
    )
    draw.text((96, 1162), "MISCLASSIFIED QUERY IDS", font=font_label, fill=COLORS["red"])
    draw.text((96, 1192), error_ids, font=load_font(25, bold=True), fill=COLORS["ink"])
    if fallback_rows:
        fallback_ids = ", ".join(row["id"] for row in fallback_rows)
        fallback_note = f"Rule-based recovery was used for query ID {fallback_ids}; inspect results.csv for its reason."
    else:
        fallback_note = "No rule-based recovery results were detected."
    draw.text((96, 1248), fallback_note, font=font_small, fill=COLORS["muted"])
    draw.text(
        (72, 1340),
        "Generated from evaluation/results.csv  |  Per-class scores use expected-label support.",
        font=font_small,
        fill=COLORS["muted"],
    )

    image.save(OUTPUT_PATH)
    print(f"Saved visualization: {OUTPUT_PATH}")
    print(f"Rows: {len(rows)}; correct: {correct_count}; accuracy: {accuracy:.2f}%")


if __name__ == "__main__":
    main()