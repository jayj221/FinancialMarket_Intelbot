import time
import datetime
import torch
from transformers import pipeline
from config import FINBERT_MODEL, SENTIMENT_RECENT_WEIGHT

_finbert = None


def _get_pipeline():
    global _finbert
    if _finbert is None:
        _finbert = pipeline(
            "sentiment-analysis",
            model=FINBERT_MODEL,
            tokenizer=FINBERT_MODEL,
            device=-1,
            truncation=True,
            max_length=512,
        )
    return _finbert


def _label_to_score(label: str, confidence: float) -> float:
    if label == "positive":
        return confidence
    if label == "negative":
        return -confidence
    return 0.0


def score_articles(articles: list[dict], cutoff_hours: int = 24) -> list[dict]:
    if not articles:
        return []

    pipe = _get_pipeline()
    headlines = [a.get("headline", "")[:512] for a in articles]

    with torch.no_grad():
        results = pipe(headlines, batch_size=8)

    now = datetime.datetime.utcnow().timestamp()
    scored = []
    for article, result in zip(articles, results):
        raw_score = _label_to_score(result["label"], result["score"])
        age_hours = (now - article.get("datetime", now)) / 3600
        weight = SENTIMENT_RECENT_WEIGHT if age_hours <= cutoff_hours else 1.0
        scored.append({
            **article,
            "finbert_label": result["label"],
            "finbert_confidence": round(result["score"], 4),
            "score": round(raw_score, 4),
            "weight": weight,
        })

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def aggregate_score(scored_articles: list[dict]) -> float:
    if not scored_articles:
        return 0.0
    total_weight = sum(a["weight"] for a in scored_articles)
    weighted_sum = sum(a["score"] * a["weight"] for a in scored_articles)
    return round(weighted_sum / total_weight, 4)


def classify(score: float) -> str:
    if score >= 0.15:
        return "Bullish"
    if score <= -0.15:
        return "Bearish"
    return "Neutral"
