"""Create/verify the Menu tab in the Google Sheet.

Idempotent: only creates the tab or writes its header row when missing — never
touches existing data.

    python tools/seed_menu_sheet.py
    python tools/seed_menu_sheet.py --sample-data   # also append a few example rows

The sample rows below are a generic Nigerian restaurant menu (Lagos-style
prices in NGN) meant as a working starting point — replace them with the
real menu via the Menu tab directly once the business confirms it (see
workflows/seed_and_verify_business_data.md).
"""

from __future__ import annotations

import argparse

import gspread

from common import emit, log
from sheets_common import MENU_HEADERS, MENU_SHEET_NAME, open_spreadsheet

SAMPLE_MENU_ROWS = [
    ["Puff Puff", "Starters", 1500, "Sweet fried dough balls, a Lagos street food classic.", "vegetarian", "Chin Chin", "Y"],
    ["Chin Chin", "Starters", 1200, "Crunchy sweet fried pastry snack.", "vegetarian", "Puff Puff", "Y"],
    ["Peppered Snails", "Starters", 4500, "Spicy grilled snails in pepper sauce.", "spicy", "Chapman", "Y"],
    ["Egusi Soup & Pounded Yam", "Soups & Swallow", 5000, "Melon seed soup with assorted meat and fish, served with pounded yam.", "gluten-free", "", "Y"],
    ["Efo Riro & Semo", "Soups & Swallow", 4800, "Spinach stew with assorted meat, served with semovita.", "gluten-free, spicy", "", "Y"],
    ["Ogbono Soup & Eba", "Soups & Swallow", 4800, "Draw soup with assorted meat, served with eba.", "gluten-free", "", "Y"],
    ["Jollof Rice", "Rice & Grains", 3500, "Smoky party-style jollof rice.", "", "Peppered Chicken", "Y"],
    ["Fried Rice", "Rice & Grains", 3500, "Nigerian-style fried rice with mixed vegetables.", "", "Grilled Fish", "Y"],
    ["Ofada Rice & Ayamase", "Rice & Grains", 4500, "Local ofada rice with spicy green pepper sauce.", "spicy", "", "Y"],
    ["Coconut Rice", "Rice & Grains", 3800, "Fragrant rice cooked in coconut milk.", "vegetarian", "", "Y"],
    ["Suya (Beef)", "Grills & Proteins", 3000, "Spicy skewered grilled beef, Lagos street-food style.", "spicy, gluten-free", "Chapman", "Y"],
    ["Peppered Chicken", "Grills & Proteins", 4000, "Grilled chicken tossed in pepper sauce.", "spicy, gluten-free", "Jollof Rice", "Y"],
    ["Grilled Fish (Croaker)", "Grills & Proteins", 5500, "Whole grilled croaker fish with pepper sauce.", "gluten-free", "Fried Rice", "Y"],
    ["Asun (Spicy Goat Meat)", "Grills & Proteins", 5000, "Chopped, spiced, and grilled goat meat.", "spicy, gluten-free", "", "Y"],
    ["Fried Plantain (Dodo)", "Sides", 1500, "Sweet fried ripe plantain.", "vegetarian, gluten-free", "", "Y"],
    ["Moin Moin", "Sides", 1800, "Steamed bean pudding.", "vegetarian, gluten-free", "", "Y"],
    ["Chapman", "Drinks", 2000, "Nigeria's classic fruity mocktail.", "vegetarian, gluten-free", "", "Y"],
    ["Zobo", "Drinks", 1500, "Chilled hibiscus drink with ginger and pineapple.", "vegetarian, gluten-free", "", "Y"],
    ["Soft Drink", "Drinks", 800, "Coke, Fanta, or Sprite.", "vegetarian, gluten-free", "", "Y"],
    ["Bottled Water", "Drinks", 500, "75cl bottled water.", "vegetarian, gluten-free", "", "Y"],
    ["Fruit Salad", "Desserts", 2500, "Fresh seasonal fruit mix.", "vegetarian, gluten-free", "", "Y"],
]


def ensure_tab(spreadsheet: gspread.Spreadsheet, name: str, headers: list[str]) -> str:
    try:
        worksheet = spreadsheet.worksheet(name)
        log(f"tab {name!r} already exists")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=200, cols=len(headers))
        worksheet.append_row(headers)
        log(f"created tab {name!r} with headers")
        return "created"

    if not worksheet.row_values(1):
        worksheet.append_row(headers)
        log(f"wrote missing header row to {name!r}")
        return "headers_added"

    return "unchanged"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/verify the Menu tab.")
    parser.add_argument("--sample-data", action="store_true", help="Append a few example Menu rows.")
    args = parser.parse_args()

    spreadsheet = open_spreadsheet()

    menu_status = ensure_tab(spreadsheet, MENU_SHEET_NAME, MENU_HEADERS)

    sample_rows_added = 0
    if args.sample_data:
        worksheet = spreadsheet.worksheet(MENU_SHEET_NAME)
        for row in SAMPLE_MENU_ROWS:
            worksheet.append_row(row)
            sample_rows_added += 1
        log(f"appended {sample_rows_added} sample menu rows")

    emit(
        {
            "spreadsheet_title": spreadsheet.title,
            "menu_tab": menu_status,
            "sample_rows_added": sample_rows_added,
        }
    )


if __name__ == "__main__":
    main()
