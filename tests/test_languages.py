import pytest
from app.languages import get_text, TRANSLATIONS

def test_get_text_happy_path_en():
    """Test retrieving an existing key for English."""
    result = get_text("en", "page_title_setup")
    assert result == TRANSLATIONS["en"]["page_title_setup"]

def test_get_text_happy_path_tr():
    """Test retrieving an existing key for Turkish."""
    result = get_text("tr", "page_title_setup")
    assert result == TRANSLATIONS["tr"]["page_title_setup"]

def test_get_text_happy_path_de():
    """Test retrieving an existing key for German."""
    result = get_text("de", "page_title_setup")
    assert result == TRANSLATIONS["de"]["page_title_setup"]

def test_get_text_fallback_unsupported_language():
    """Test requesting a valid key for an unsupported language falls back to English."""
    # Assuming 'fr' is not supported
    result = get_text("fr", "page_title_setup")
    assert result == TRANSLATIONS["en"]["page_title_setup"]

def test_get_text_missing_key():
    """Test requesting a non-existent key returns [key]."""
    result = get_text("en", "non_existent_key_12345")
    assert result == "[non_existent_key_12345]"

def test_get_text_missing_key_unsupported_language():
    """Test requesting a non-existent key for an unsupported language returns [key]."""
    result = get_text("fr", "non_existent_key_12345")
    assert result == "[non_existent_key_12345]"

def test_get_text_empty_language():
    """Test requesting an empty language code falls back to English."""
    result = get_text("", "page_title_setup")
    assert result == TRANSLATIONS["en"]["page_title_setup"]

def test_get_text_none_language():
    """Test requesting None as language code falls back to English."""
    result = get_text(None, "page_title_setup")
    assert result == TRANSLATIONS["en"]["page_title_setup"]

def test_get_text_empty_key():
    """Test requesting an empty key returns []"""
    result = get_text("en", "")
    assert result == "[]"
