from __future__ import annotations

DISCOVER_ASSET_ID_TO_R2_KEY: dict[str, str] = {
    asset_id: f"assets/3-4/{asset_id}.webp"
    for asset_id in (
        "discover-living-room",
        "discover-kitchen",
        "discover-dining-room",
        "discover-bedroom",
        "discover-master-bedroom",
        "discover-guest-bedroom",
        "discover-kids-room",
        "discover-nursery",
        "discover-bathroom",
        "discover-powder-room",
        "discover-home-office",
        "discover-study-room",
        "discover-entryway",
        "discover-hallway",
        "discover-staircase",
        "discover-laundry-room",
        "discover-pantry",
        "discover-walk-in-closet",
        "discover-home-gym",
        "discover-media-room",
        "discover-sunroom",
        "discover-balcony",
        "discover-terrace",
        "discover-patio",
        "discover-garage",
        "discover-basement",
        "discover-attic",
        "discover-garden",
        "discover-apartment-exterior",
        "discover-house-exterior",
        "discover-villa-exterior",
    )
}


def _cards(section_id: str, asset_id: str) -> list[dict[str, str]]:
    return [
        {
            "id": f"{section_id}-1",
            "image_asset_id": asset_id,
        }
    ]


def _section(section_id: str, title: str, asset_id: str) -> dict[str, object]:
    return {
        "id": section_id,
        "title": title,
        "cards": _cards(section_id, asset_id),
    }


DISCOVER_CATEGORIES_TEMPLATE: dict[str, object] = {
    "home": {
        "label": "Home",
        "sections": [
            _section("kitchen", "Kitchen", "discover-kitchen"),
            _section("living-room", "Living Room", "discover-living-room"),
            _section("dining-room", "Dining Room", "discover-dining-room"),
            _section("bedroom", "Bedroom", "discover-bedroom"),
            _section("master-bedroom", "Master Bedroom", "discover-master-bedroom"),
            _section("guest-bedroom", "Guest Bedroom", "discover-guest-bedroom"),
            _section("kids-room", "Kids Room", "discover-kids-room"),
            _section("nursery", "Nursery", "discover-nursery"),
            _section("bathroom", "Bathroom", "discover-bathroom"),
            _section("powder-room", "Powder Room", "discover-powder-room"),
            _section("home-office", "Home Office", "discover-home-office"),
            _section("study-room", "Study Room", "discover-study-room"),
            _section("entryway", "Entryway", "discover-entryway"),
            _section("hallway", "Hallway", "discover-hallway"),
            _section("staircase", "Staircase", "discover-staircase"),
            _section("laundry-room", "Laundry Room", "discover-laundry-room"),
            _section("pantry", "Pantry", "discover-pantry"),
            _section("walk-in-closet", "Walk-in Closet", "discover-walk-in-closet"),
            _section("home-gym", "Home Gym", "discover-home-gym"),
            _section("media-room", "Media Room", "discover-media-room"),
            _section("sunroom", "Sunroom", "discover-sunroom"),
            _section("balcony", "Balcony", "discover-balcony"),
            _section("terrace", "Terrace", "discover-terrace"),
            _section("patio", "Patio", "discover-patio"),
            _section("garage", "Garage", "discover-garage"),
            _section("basement", "Basement", "discover-basement"),
            _section("attic", "Attic", "discover-attic"),
        ],
    },
    "garden": {
        "label": "Garden",
        "sections": [
            _section("garden-main", "Garden", "discover-garden"),
        ],
    },
    "exterior": {
        "label": "Exterior Design",
        "sections": [
            _section("apartment", "Apartment", "discover-apartment-exterior"),
            _section("house", "House", "discover-house-exterior"),
            _section("villa", "Villa", "discover-villa-exterior"),
        ],
    },
}
