from unittest.mock import MagicMock, call, patch

import pytest
import requests

import ingest


def make_resp(status, body=None, json_ok=True):
    """Fake API response: status code + JSON body"""

    r = MagicMock()
    r.status_code = status
    if json_ok:
        r.json.return_value = body or {}
    else:
        r.json.side_effect = ValueError("not JSON")
    if status >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(response=r)
    return r


OK = make_resp(200, {"hourly": {}})


def call_api():
    return ingest.fetch_weather(52.5, 13.4, "2026-01-01", "2026-01-02")


# 1. daily quota used up -> stop at once
@patch("ingest.time.sleep")  # mock_sleep
@patch("ingest.requests.get")  # mock_get
def test_quota_exhausted_stops_at_once(mock_get, mock_sleep):
    mock_get.side_effect = [
        make_resp(429, {"reason": "Daily API request limit exceeded"})
    ]
    with pytest.raises(ingest.QuotaExhausted):
        call_api()
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


# 2. 429 with a body whic is not JSON -> retry


@patch("ingest.time.sleep")  # mock_sleep
@patch("ingest.requests.get")  # mock_get
def test_429_without_reason_is_retried(mock_get, mock_sleep):
    mock_get.side_effect = [make_resp(429, json_ok=False), OK]
    assert call_api() == {"hourly": {}}
    assert mock_get.call_count == 2
    assert mock_sleep.call_args_list == [call(10)]


# 3. retryable server error every time → 4 attempts, growing waits, then give up
@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_server_error_retries_then_gives_up(mock_get, mock_sleep):
    mock_get.side_effect = [make_resp(503)] * 4
    with pytest.raises(requests.HTTPError):
        call_api()
    assert mock_get.call_count == 4
    assert mock_sleep.call_args_list == [call(10), call(30), call(60)]


# 4. non-retryable error → stop at once
@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_bad_request_is_not_retried(mock_get, mock_sleep):
    mock_get.side_effect = [make_resp(400)]
    with pytest.raises(requests.HTTPError):
        call_api()
    assert mock_get.call_count == 1


# 5. connection lost once → retry → success
@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_connection_error_is_retried(mock_get, mock_sleep):
    mock_get.side_effect = [requests.ConnectionError(), OK]
    assert call_api() == {"hourly": {}}
    assert mock_get.call_count == 2


# 6. connection lost every time → give up after 4 attempts
@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_connection_error_every_time_gives_up(mock_get, mock_sleep):
    mock_get.side_effect = [requests.ConnectionError()] * 4
    with pytest.raises(requests.ConnectionError):
        call_api()
    assert mock_get.call_count == 4
