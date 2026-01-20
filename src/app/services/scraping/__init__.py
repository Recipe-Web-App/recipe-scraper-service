"""Recipe scraping service module."""

from app.services.scraping.models import ScrapedRecipe
from app.services.scraping.service import RecipeScraperService


__all__ = ["RecipeScraperService", "ScrapedRecipe"]
