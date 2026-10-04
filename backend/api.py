"""HTTP API for translating tour reviews into Kiswahili."""

from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from echo_api import router, initialize, owner
from pydantic import BaseModel, Field, field_validator

from review import Review, TranslatedReview
from review_storage import load_translated_reviews, save_translated_reviews
from translate_opus import translate_review
from analytics import build_insights
from insight_model import InsightModel

app = FastAPI(
    title="Echo Offline API",
    description="Local visitor feedback, translation, topics and approved suggestions.",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)
insight_model = None
initialize()
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])
app.include_router(router)


class ReviewPayload(BaseModel):
    """JSON representation accepted by the translation endpoints."""

    rating: Annotated[float, Field(ge=1, le=5)]
    language: str = "en"
    date: date
    favorite: str = ""
    improvement: str = ""

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value != "en":
            raise ValueError("language must be 'en'.")
        return value

    @field_validator("favorite", "improvement")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return value

    def to_review(self) -> Review:
        return Review(
            rating=self.rating,
            language=self.language,
            date=self.date,
            favorite=self.favorite,
            improvement=self.improvement,
        )


class TranslatedReviewPayload(BaseModel):
    """JSON representation returned after translation."""

    rating: float
    language: str
    date: date
    favorite: str
    improvement: str

    @classmethod
    def from_review(cls, review: TranslatedReview) -> "TranslatedReviewPayload":
        return cls(
            rating=review.rating,
            language=review.language,
            date=review.date,
            favorite=review.favorite,
            improvement=review.improvement,
        )


class BatchReviewPayload(BaseModel):
    """A bounded batch of reviews to translate."""

    reviews: Annotated[list[ReviewPayload], Field(min_length=1, max_length=50)]


class BatchTranslatedReviewPayload(BaseModel):
    """Translated reviews returned for a batch request."""

    reviews: list[TranslatedReviewPayload]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/reviews/translate",
    response_model=TranslatedReviewPayload,
)
def translate_single_review(payload: ReviewPayload, s=Depends(owner)) -> TranslatedReviewPayload:
    try:
        translated = translate_review(payload.to_review())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        save_translated_reviews([translated])
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Could not save translated review.") from error
    return TranslatedReviewPayload.from_review(translated)


@app.post(
    "/reviews/translate/batch",
    response_model=BatchTranslatedReviewPayload,
)
def translate_review_batch(
    payload: BatchReviewPayload,
    s=Depends(owner),
) -> BatchTranslatedReviewPayload:
    translated_models: list[TranslatedReview] = []
    for review_payload in payload.reviews:
        try:
            translated = translate_review(review_payload.to_review())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        translated_models.append(translated)

    try:
        save_translated_reviews(translated_models)
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Could not save translated reviews.") from error

    return BatchTranslatedReviewPayload(
        reviews=[TranslatedReviewPayload.from_review(review) for review in translated_models]
    )


@app.get(
    "/reviews/translated",
    response_model=list[TranslatedReviewPayload],
)
def get_translated_reviews(s=Depends(owner)) -> list[TranslatedReviewPayload]:
    try:
        stored_reviews = load_translated_reviews()
        return [TranslatedReviewPayload.model_validate(review) for review in stored_reviews]
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Could not read translated review storage.",
        ) from error


@app.get("/reviews/insights")
def get_review_insights(s=Depends(owner)) -> dict:
    from echo_analytics import patterns
    import store
    return {"themes": patterns(store.records("reviews", s["user_id"]))}

# Serve the unchanged frontend directory from the local API for simple offline startup.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "frontend", html=True), name="frontend")
