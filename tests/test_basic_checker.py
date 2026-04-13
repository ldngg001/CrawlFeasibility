import pytest
from unittest.mock import Mock

from src.crawler.basic_checker import BasicChecker
from src.models.result import BasicResult


@pytest.fixture
def mock_client():
    client = Mock()
    client.get_domain = Mock(return_value="http://example.com")
    return client


@pytest.mark.asyncio
async def test_check_robots_txt_exists(mock_client):
    # Mock the response for robots.txt
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "User-agent: *\nDisallow: /private\n"
    mock_client.get = Mock(return_value=mock_response)

    checker = BasicChecker(mock_client)
    result = await checker.check("http://example.com")

    assert result.robots_txt_exists == True
    assert result.robots_txt_content == "User-agent: *\nDisallow: /private\n"
    assert result.robots_txt_full_disallow == False  # Because it's not disallowing all


@pytest.mark.asyncio
async def test_check_robots_txt_not_exists(mock_client):
    # Mock the response for robots.txt as 404
    mock_response = Mock()
    mock_response.status_code = 404
    mock_client.get = Mock(return_value=mock_response)

    checker = BasicChecker(mock_client)
    result = await checker.check("http://example.com")

    assert result.robots_txt_exists == False
    assert result.robots_txt_content == ""
    assert result.robots_txt_full_disallow == False


@pytest.mark.asyncio
async def test_check_robots_txt_full_disallow(mock_client):
    # Mock the response for robots.txt with full disallow
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "User-agent: *\nDisallow: /\n"
    mock_client.get = Mock(return_value=mock_response)

    checker = BasicChecker(mock_client)
    result = await checker.check("http://example.com")

    assert result.robots_txt_exists == True
    assert result.robots_txt_content == "User-agent: *\nDisallow: /\n"
    assert result.robots_txt_full_disallow == True