import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from config import BULLISH_THRESHOLD, BEARISH_THRESHOLD

# VADER lexicon is downloaded in the GitHub Actions workflow step.
# For local runs: python -c "import nltk; nltk.download('vader_lexicon')"
_sia = None


def _get_sia() -> SentimentIntensityAnalyzer:
    global _sia
    if _sia is None:
        _sia = SentimentIntensityAnalyzer()
    return _sia


def score_headlines(headlines: list[str]) -> float:
    """
    Returns the average VADER compound score for a list of headlines.
    Score range: -1.0 (most negative) to +1.0 (most positive).
    Returns 0.0 if no headlines provided.
    """
    if not headlines:
        return 0.0
    sia = _get_sia()
    scores = [sia.polarity_scores(h)["compound"] for h in headlines if h]
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Scores a list of article dicts (must have 'headline' key).
    Adds a 'score' key to each article and returns sorted by score descending.
    """
    sia = _get_sia()
    scored = []
    for a in articles:
        headline = a.get("headline", "")
        compound = sia.polarity_scores(headline)["compound"] if headline else 0.0
        scored.append({**a, "score": round(compound, 4)})
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def classify(score: float) -> str:
    """Maps a compound score to a human-readable signal label."""
    if score >= BULLISH_THRESHOLD:
        return "Bullish"
    if score <= BEARISH_THRESHOLD:
        return "Bearish"
    return "Neutral"
