from __future__ import annotations

import json

DISCOVER_ASSET_ID_TO_R2_KEY: dict[str, str] = {
  "heroApartment": "assets/9-16/hero-apartment.webp",
  "apartmentTerrace": "assets/9-16/apartment-terrace.webp",
  "gardenLandscape": "assets/9-16/garden-landscape.webp",
  "houseModern": "assets/9-16/house-modern.webp",
  "houseContemporary": "assets/9-16/house-contemporary.webp",
  "livingRoomBright": "assets/9-16/living-room-bright.webp",
  "livingRoomLuxury": "assets/9-16/living-room-luxury.webp",
  "gardenBackyard": "assets/9-16/garden-backyard.webp",
  "interiorStyled": "assets/9-16/interior-styled.webp"
}

DISCOVER_CATEGORIES_TEMPLATE: dict[str, object] = json.loads(
    r'''{
  "home": {
    "label": "Home",
    "sections": [
      {
        "id": "kitchen",
        "title": "Kitchen",
        "cards": [
          {
            "id": "kitchen-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "kitchen-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "kitchen-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "living-room",
        "title": "Living Room",
        "cards": [
          {
            "id": "living-1",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "living-2",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "living-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "dining-room",
        "title": "Dining Room",
        "cards": [
          {
            "id": "dining-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "dining-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "dining-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "bedroom",
        "title": "Bedroom",
        "cards": [
          {
            "id": "bedroom-1",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "bedroom-2",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "bedroom-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "master-bedroom",
        "title": "Master Bedroom",
        "cards": [
          {
            "id": "master-bedroom-1",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "master-bedroom-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "master-bedroom-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "guest-bedroom",
        "title": "Guest Bedroom",
        "cards": [
          {
            "id": "guest-bedroom-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "guest-bedroom-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "guest-bedroom-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "kids-room",
        "title": "Kids Room",
        "cards": [
          {
            "id": "kids-room-1",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "kids-room-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "kids-room-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "nursery",
        "title": "Nursery",
        "cards": [
          {
            "id": "nursery-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "nursery-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "nursery-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "bathroom",
        "title": "Bathroom",
        "cards": [
          {
            "id": "bathroom-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "bathroom-2",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "bathroom-3",
            "image_asset_id": "livingRoomBright"
          }
        ]
      },
      {
        "id": "powder-room",
        "title": "Powder Room",
        "cards": [
          {
            "id": "powder-room-1",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "powder-room-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "powder-room-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "home-office",
        "title": "Home Office",
        "cards": [
          {
            "id": "office-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "office-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "office-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "study-room",
        "title": "Study Room",
        "cards": [
          {
            "id": "study-1",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "study-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "study-3",
            "image_asset_id": "livingRoomBright"
          }
        ]
      },
      {
        "id": "entryway",
        "title": "Entryway",
        "cards": [
          {
            "id": "entryway-1",
            "image_asset_id": "heroApartment"
          },
          {
            "id": "entryway-2",
            "image_asset_id": "houseModern"
          },
          {
            "id": "entryway-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "hallway",
        "title": "Hallway",
        "cards": [
          {
            "id": "hallway-1",
            "image_asset_id": "heroApartment"
          },
          {
            "id": "hallway-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "hallway-3",
            "image_asset_id": "houseContemporary"
          }
        ]
      },
      {
        "id": "staircase",
        "title": "Staircase",
        "cards": [
          {
            "id": "staircase-1",
            "image_asset_id": "houseModern"
          },
          {
            "id": "staircase-2",
            "image_asset_id": "houseContemporary"
          },
          {
            "id": "staircase-3",
            "image_asset_id": "heroApartment"
          }
        ]
      },
      {
        "id": "laundry-room",
        "title": "Laundry Room",
        "cards": [
          {
            "id": "laundry-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "laundry-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "laundry-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "pantry",
        "title": "Pantry",
        "cards": [
          {
            "id": "pantry-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "pantry-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "pantry-3",
            "image_asset_id": "livingRoomLuxury"
          }
        ]
      },
      {
        "id": "walk-in-closet",
        "title": "Walk-in Closet",
        "cards": [
          {
            "id": "closet-1",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "closet-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "closet-3",
            "image_asset_id": "livingRoomBright"
          }
        ]
      },
      {
        "id": "home-gym",
        "title": "Home Gym",
        "cards": [
          {
            "id": "gym-1",
            "image_asset_id": "houseModern"
          },
          {
            "id": "gym-2",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "gym-3",
            "image_asset_id": "houseContemporary"
          }
        ]
      },
      {
        "id": "media-room",
        "title": "Media Room",
        "cards": [
          {
            "id": "media-1",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "media-2",
            "image_asset_id": "livingRoomBright"
          },
          {
            "id": "media-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "sunroom",
        "title": "Sunroom",
        "cards": [
          {
            "id": "sunroom-1",
            "image_asset_id": "apartmentTerrace"
          },
          {
            "id": "sunroom-2",
            "image_asset_id": "heroApartment"
          },
          {
            "id": "sunroom-3",
            "image_asset_id": "interiorStyled"
          }
        ]
      },
      {
        "id": "balcony",
        "title": "Balcony",
        "cards": [
          {
            "id": "balcony-1",
            "image_asset_id": "apartmentTerrace"
          },
          {
            "id": "balcony-2",
            "image_asset_id": "heroApartment"
          },
          {
            "id": "balcony-3",
            "image_asset_id": "gardenBackyard"
          }
        ]
      },
      {
        "id": "terrace",
        "title": "Terrace",
        "cards": [
          {
            "id": "terrace-1",
            "image_asset_id": "apartmentTerrace"
          },
          {
            "id": "terrace-2",
            "image_asset_id": "houseModern"
          },
          {
            "id": "terrace-3",
            "image_asset_id": "gardenLandscape"
          }
        ]
      },
      {
        "id": "patio",
        "title": "Patio",
        "cards": [
          {
            "id": "patio-1",
            "image_asset_id": "gardenBackyard"
          },
          {
            "id": "patio-2",
            "image_asset_id": "houseContemporary"
          },
          {
            "id": "patio-3",
            "image_asset_id": "apartmentTerrace"
          }
        ]
      },
      {
        "id": "garage",
        "title": "Garage",
        "cards": [
          {
            "id": "garage-1",
            "image_asset_id": "houseModern"
          },
          {
            "id": "garage-2",
            "image_asset_id": "houseContemporary"
          },
          {
            "id": "garage-3",
            "image_asset_id": "heroApartment"
          }
        ]
      },
      {
        "id": "basement",
        "title": "Basement",
        "cards": [
          {
            "id": "basement-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "basement-2",
            "image_asset_id": "livingRoomLuxury"
          },
          {
            "id": "basement-3",
            "image_asset_id": "houseContemporary"
          }
        ]
      },
      {
        "id": "attic",
        "title": "Attic",
        "cards": [
          {
            "id": "attic-1",
            "image_asset_id": "interiorStyled"
          },
          {
            "id": "attic-2",
            "image_asset_id": "houseModern"
          },
          {
            "id": "attic-3",
            "image_asset_id": "livingRoomBright"
          }
        ]
      }
    ]
  },
  "garden": {
    "label": "Garden",
    "sections": [
      {
        "id": "garden-main",
        "title": "Garden",
        "cards": [
          {
            "id": "garden-1",
            "image_asset_id": "gardenLandscape"
          },
          {
            "id": "garden-2",
            "image_asset_id": "gardenBackyard"
          },
          {
            "id": "garden-3",
            "image_asset_id": "gardenLandscape"
          }
        ]
      }
    ]
  },
  "exterior": {
    "label": "Exterior Design",
    "sections": [
      {
        "id": "apartment",
        "title": "Apartment",
        "cards": [
          {
            "id": "apt-1",
            "image_asset_id": "heroApartment"
          },
          {
            "id": "apt-2",
            "image_asset_id": "apartmentTerrace"
          },
          {
            "id": "apt-3",
            "image_asset_id": "heroApartment"
          }
        ]
      },
      {
        "id": "house",
        "title": "House",
        "cards": [
          {
            "id": "house-1",
            "image_asset_id": "houseModern"
          },
          {
            "id": "house-2",
            "image_asset_id": "houseContemporary"
          },
          {
            "id": "house-3",
            "image_asset_id": "houseModern"
          }
        ]
      },
      {
        "id": "villa",
        "title": "Villa",
        "cards": [
          {
            "id": "villa-1",
            "image_asset_id": "houseContemporary"
          },
          {
            "id": "villa-2",
            "image_asset_id": "houseModern"
          },
          {
            "id": "villa-3",
            "image_asset_id": "apartmentTerrace"
          }
        ]
      }
    ]
  }
}'''
)
