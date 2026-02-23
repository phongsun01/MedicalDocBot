from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
from app.classifier import MedicalClassifier

@pytest.mark.asyncio
async def test_classify_file_success():
    """Test AI classification with mocked API response."""
    classifier = MedicalClassifier()
    
    # Mock httpx AsyncClient
    with patch("app.classifier.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"doc_type": "ky_thuat", "vendor": "GE", "model": "Optima", "category_slug": "x_quang", "summary": "test", "confidence": 0.95}'
                }
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        
        # Test classification
        with patch("app.classifier.extract_file") as mock_extract:
            mock_extract_result = MagicMock()
            mock_extract_result.content = "Dummy text"
            mock_extract.return_value = mock_extract_result
            
            result = await classifier.classify_file("test.pdf", max_retries=1)
            
            assert result["doc_type"] == "ky_thuat"
            assert result["vendor"] == "GE"
            assert result["confidence"] == 0.95
