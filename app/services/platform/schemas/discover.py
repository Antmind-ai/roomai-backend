from pydantic import BaseModel, Field


class DiscoverCardResponse(BaseModel):
    id: str
    image_url: str


class DiscoverSectionResponse(BaseModel):
    id: str
    title: str
    cards: list[DiscoverCardResponse]


class DiscoverCategoryResponse(BaseModel):
    label: str
    sections: list[DiscoverSectionResponse]


class DiscoverCatalogCategoriesResponse(BaseModel):
    home: DiscoverCategoryResponse
    garden: DiscoverCategoryResponse
    exterior: DiscoverCategoryResponse


class DiscoverCatalogResponse(BaseModel):
    cache_max_age_seconds: int = Field(..., ge=1)
    expires_in_seconds: int = Field(..., ge=1)
    categories: DiscoverCatalogCategoriesResponse
