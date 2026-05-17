from __future__ import annotations

LEGACY_DISCOVER_ASSET_IDS = (
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

DISCOVER_LIVING_ROOM_ASSET_IDS = (
    "discover-living-room",
    "discover-living-room-01",
    "discover-living-room-02",
    "discover-living-room-03",
    "discover-living-room-04",
    "discover-living-room-05",
    "discover-living-room-06",
    "discover-living-room-07",
    "discover-living-room-08",
    "discover-living-room-09",
    "discover-living-room-10",
    "discover-living-room-11",
    "discover-living-room-12",
    "discover-living-room-13",
    "discover-living-room-14",
    "discover-living-room-15",
    "discover-living-room-16",
    "discover-living-room-17",
    "discover-living-room-18",
    "discover-living-room-19",
    "discover-living-room-20",
)

DISCOVER_KITCHEN_ASSET_IDS = (
    "discover-kitchen",
    "discover-kitchen-01",
    "discover-kitchen-02",
    "discover-kitchen-03",
    "discover-kitchen-04",
    "discover-kitchen-05",
    "discover-kitchen-06",
    "discover-kitchen-07",
    "discover-kitchen-08",
    "discover-kitchen-09",
    "discover-kitchen-10",
)

DISCOVER_HOUSE_ASSET_IDS = (
    "discover-house-exterior",
    "discover-house-exterior-01",
    "discover-house-exterior-02",
    "discover-house-exterior-03",
    "discover-house-exterior-04",
    "discover-house-exterior-05",
    "discover-house-exterior-06",
    "discover-house-exterior-07",
    "discover-house-exterior-08",
    "discover-house-exterior-09",
    "discover-house-exterior-10",
)

DISCOVER_VILLA_ASSET_IDS = (
    "discover-villa-exterior",
    "discover-villa-exterior-01",
    "discover-villa-exterior-02",
    "discover-villa-exterior-03",
    "discover-villa-exterior-04",
    "discover-villa-exterior-05",
    "discover-villa-exterior-06",
    "discover-villa-exterior-07",
    "discover-villa-exterior-08",
    "discover-villa-exterior-09",
    "discover-villa-exterior-10",
)

DISCOVER_GARDEN_ASSET_IDS = (
    "discover-garden",
    "discover-garden-courtyard-01",
    "discover-garden-courtyard-02",
    "discover-garden-courtyard-03",
    "discover-garden-courtyard-04",
    "discover-garden-courtyard-05",
    "discover-garden-backyard-01",
    "discover-garden-backyard-02",
    "discover-garden-backyard-03",
    "discover-garden-backyard-04",
    "discover-garden-backyard-05",
)

NEW_DISCOVER_ASSET_IDS = (
    *DISCOVER_LIVING_ROOM_ASSET_IDS[1:],
    *DISCOVER_KITCHEN_ASSET_IDS[1:],
    *DISCOVER_HOUSE_ASSET_IDS[1:],
    *DISCOVER_VILLA_ASSET_IDS[1:],
    *DISCOVER_GARDEN_ASSET_IDS[1:],
)

DISCOVER_ASSET_ID_TO_R2_KEY: dict[str, str] = {
    asset_id: f"assets/3-4/{asset_id}.webp"
    for asset_id in (*LEGACY_DISCOVER_ASSET_IDS, *NEW_DISCOVER_ASSET_IDS)
}


def _cards(section_id: str, asset_ids: tuple[str, ...]) -> list[dict[str, str]]:
    return [
        {
            "id": f"{section_id}-{index}",
            "image_asset_id": asset_id,
        }
        for index, asset_id in enumerate(asset_ids, start=1)
    ]


def _section(
    section_id: str,
    title: str,
    asset_ids: str | tuple[str, ...],
) -> dict[str, object]:
    normalized_asset_ids = (asset_ids,) if isinstance(asset_ids, str) else asset_ids
    return {
        "id": section_id,
        "title": title,
        "cards": _cards(section_id, normalized_asset_ids),
    }


DISCOVER_CATEGORIES_TEMPLATE: dict[str, object] = {
    "home": {
        "label": "Home",
        "sections": [
            _section("kitchen", "Kitchen", DISCOVER_KITCHEN_ASSET_IDS),
            _section("living-room", "Living Room", DISCOVER_LIVING_ROOM_ASSET_IDS),
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
            _section("garden-main", "Garden", DISCOVER_GARDEN_ASSET_IDS),
        ],
    },
    "exterior": {
        "label": "Exterior Design",
        "sections": [
            _section("apartment", "Apartment", "discover-apartment-exterior"),
            _section("house", "House", DISCOVER_HOUSE_ASSET_IDS),
            _section("villa", "Villa", DISCOVER_VILLA_ASSET_IDS),
        ],
    },
}
