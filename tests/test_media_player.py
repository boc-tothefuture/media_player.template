"""Unit tests for media_player_template custom component."""
import datetime
import logging
from unittest.mock import patch

import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util

from custom_components.media_player_template.media_player import MediaPlayerTemplate


async def test_position_survives_playing_buffering_playing(hass: HomeAssistant) -> None:
    """Test that media position survives playing -> buffering -> playing transition without resetting."""
    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "42")
    hass.states.async_set("sensor.player_dur", "120")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_duration_template": "{{ states('sensor.player_dur') }}",
                }
            },
        }
    }

    assert await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "playing"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 42
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 120
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is not None

    # Transition to buffering while position remains 42
    hass.states.async_set("sensor.player_state", "buffering")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "buffering"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 42
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 120
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is not None

    # Transition back to playing while position is still 42
    hass.states.async_set("sensor.player_state", "playing")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "playing"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 42
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 120
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is not None


async def test_position_and_duration_in_buffering_and_idle(hass: HomeAssistant) -> None:
    """Test that position and duration are set and retained while state is buffering and idle."""
    hass.states.async_set("sensor.player_state", "idle")
    hass.states.async_set("sensor.player_pos", "10")
    hass.states.async_set("sensor.player_dur", "100")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_duration_template": "{{ states('sensor.player_dur') }}",
                }
            },
        }
    }

    assert await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "idle"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 10
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 100
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is not None

    # Transition to buffering
    hass.states.async_set("sensor.player_state", "buffering")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "buffering"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 10
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 100


async def test_media_position_updated_at_iso_z_and_offset(hass: HomeAssistant) -> None:
    """Test media_position_updated_at with ISO-8601 strings ending in Z and +00:00."""
    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "30")
    hass.states.async_set("sensor.player_updated_at", "2026-11-01T03:43:52Z")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_position_updated_at_template": "{{ states('sensor.player_updated_at') }}",
                }
            },
        }
    }

    assert await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    expected_dt_z = datetime.datetime(2026, 11, 1, 3, 43, 52, tzinfo=datetime.timezone.utc)
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 30
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == expected_dt_z

    # Now update with +00:00 offset format
    hass.states.async_set(
        "sensor.player_updated_at", "2026-11-01T03:43:52.702492+00:00"
    )
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    expected_dt_offset = datetime.datetime(
        2026, 11, 1, 3, 43, 52, 702492, tzinfo=datetime.timezone.utc
    )
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 30
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == expected_dt_offset


async def test_resume_updates_only_timestamp_same_position(hass: HomeAssistant) -> None:
    """Test that media_position_updated_at updates when only timestamp changes (same position, e.g. resume)."""
    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "55")
    hass.states.async_set("sensor.player_updated_at", "2026-11-01T03:43:52Z")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_position_updated_at_template": "{{ states('sensor.player_updated_at') }}",
                }
            },
        }
    }

    assert await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 55
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == datetime.datetime(
        2026, 11, 1, 3, 43, 52, tzinfo=datetime.timezone.utc
    )

    # Resume at the exact same position (55) with new timestamp
    hass.states.async_set("sensor.player_updated_at", "2026-11-01T03:44:10Z")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 55
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == datetime.datetime(
        2026, 11, 1, 3, 44, 10, tzinfo=datetime.timezone.utc
    )


async def test_without_new_option_legacy_behavior(hass: HomeAssistant) -> None:
    """Test that without media_position_updated_at_template, behavior is identical to legacy apart from B/C."""
    frozen_time_1 = datetime.datetime(2026, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    frozen_time_2 = datetime.datetime(2026, 11, 1, 10, 5, 0, tzinfo=datetime.timezone.utc)

    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "10")
    hass.states.async_set("sensor.player_dur", "120")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_duration_template": "{{ states('sensor.player_dur') }}",
                }
            },
        }
    }

    with patch("homeassistant.util.dt.utcnow", return_value=frozen_time_1):
        assert await async_setup_component(hass, "media_player", config)
        await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 10
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == frozen_time_1
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 120

    # Updating position stamps new utcnow
    with patch("homeassistant.util.dt.utcnow", return_value=frozen_time_2):
        hass.states.async_set("sensor.player_pos", "20")
        await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 20
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == frozen_time_2

    # Setting position to invalid clears both position and updated_at
    hass.states.async_set("sensor.player_pos", "invalid_number")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) is None
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is None

    # Duration invalid clears duration
    hass.states.async_set("sensor.player_dur", "invalid_duration")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_DURATION) is None


async def test_invalid_timestamp_logs_error_and_falls_back(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that invalid timestamp logs an error once per bad value, falls back to utcnow, and does not raise."""
    fallback_time = datetime.datetime(2026, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "50")
    hass.states.async_set("sensor.player_updated_at", "not-a-valid-timestamp")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_position_updated_at_template": "{{ states('sensor.player_updated_at') }}",
                }
            },
        }
    }

    with patch("homeassistant.util.dt.utcnow", return_value=fallback_time):
        with caplog.at_level(logging.ERROR):
            assert await async_setup_component(hass, "media_player", config)
            await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 50
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == fallback_time
    assert any(
        "invalid media position updated at timestamp" in record.message
        for record in caplog.records
    )

    # Re-trigger with same invalid value: should not log error again (once per bad value)
    error_count_before = sum(
        1 for r in caplog.records if "invalid media position updated at timestamp" in r.message
    )
    with patch("homeassistant.util.dt.utcnow", return_value=fallback_time):
        hass.states.async_set("sensor.player_pos", "51")
        await hass.async_block_till_done()

    error_count_after = sum(
        1 for r in caplog.records if "invalid media position updated at timestamp" in r.message
    )
    assert error_count_after == error_count_before


async def test_timestamp_empty_none_unknown_unavailable(hass: HomeAssistant) -> None:
    """Test that None, TemplateError, empty, unknown, unavailable sets None when no position, or falls back to utcnow when position is set."""
    fallback_time = datetime.datetime(2026, 11, 1, 12, 30, 0, tzinfo=datetime.timezone.utc)

    hass.states.async_set("sensor.player_state", "playing")
    hass.states.async_set("sensor.player_pos", "10")
    hass.states.async_set("sensor.player_updated_at", "unknown")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_position_updated_at_template": "{{ states('sensor.player_updated_at') }}",
                }
            },
        }
    }

    with patch("homeassistant.util.dt.utcnow", return_value=fallback_time):
        assert await async_setup_component(hass, "media_player", config)
        await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 10
    # Position is set, so updated_at falls back to utcnow
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == fallback_time

    # When position is None/cleared, updated_at becomes None
    hass.states.async_set("sensor.player_pos", "")
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.attributes.get(ATTR_MEDIA_POSITION) is None
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) is None

    # Check empty string "" and "unavailable"
    for empty_val in ("", "unavailable"):
        with patch("homeassistant.util.dt.utcnow", return_value=fallback_time):
            hass.states.async_set("sensor.player_pos", "25")
            hass.states.async_set("sensor.player_updated_at", empty_val)
            await hass.async_block_till_done()

        state = hass.states.get("media_player.test")
        assert state.attributes.get(ATTR_MEDIA_POSITION) == 25
        assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == fallback_time


async def test_rendering_order_independence(hass: HomeAssistant) -> None:
    """Test that position, timestamp, duration, and state are correct regardless of callback ordering."""
    player = MediaPlayerTemplate(
        hass,
        {
            "name": "Order Test",
            "state": "{{ 'playing' }}",
            "current_position_template": "{{ 42 }}",
            "media_position_updated_at_template": "{{ '2026-11-01T03:43:52Z' }}",
            "media_duration_template": "{{ 300 }}",
        },
        "order_test_unique_id",
    )
    player.entity_id = "media_player.order_test"

    valid_ts = "2026-11-01T03:43:52Z"
    expected_ts = datetime.datetime(2026, 11, 1, 3, 43, 52, tzinfo=datetime.timezone.utc)

    # Order 1: updated_at callback runs BEFORE position callback
    player._attr_state = None
    player._attr_media_position = None
    player._attr_media_position_updated_at = None
    player._attr_media_duration = None

    player._update_media_position_updated_at(valid_ts)
    player._update_media_position("42")
    player._update_media_duration("300")
    player._update_state("playing")

    assert player.state == MediaPlayerState.PLAYING
    assert player.media_position == 42
    assert player.media_position_updated_at == expected_ts
    assert player.media_duration == 300

    # Order 2: position callback runs BEFORE updated_at callback
    player._attr_state = None
    player._attr_media_position = None
    player._attr_media_position_updated_at = None
    player._attr_media_duration = None

    player._update_media_position("42")
    player._update_media_position_updated_at(valid_ts)
    player._update_media_duration("300")
    player._update_state("playing")

    assert player.state == MediaPlayerState.PLAYING
    assert player.media_position == 42
    assert player.media_position_updated_at == expected_ts
    assert player.media_duration == 300

    # Order 3: state callback runs LAST
    player._attr_state = None
    player._attr_media_position = None
    player._attr_media_position_updated_at = None
    player._attr_media_duration = None

    player._update_media_duration("300")
    player._update_media_position("42")
    player._update_media_position_updated_at(valid_ts)
    player._update_state("buffering")

    assert player.state == MediaPlayerState.BUFFERING
    assert player.media_position == 42
    assert player.media_position_updated_at == expected_ts
    assert player.media_duration == 300


async def test_datetime_object_naive_and_aware(hass: HomeAssistant) -> None:
    """Test datetime object result directly in _update_media_position_updated_at (both naive and aware)."""
    player = MediaPlayerTemplate(
        hass,
        {
            "name": "Datetime Test",
            "state": "{{ 'playing' }}",
            "current_position_template": "{{ 10 }}",
            "media_position_updated_at_template": "{{ now() }}",
        },
        "dt_test_unique_id",
    )
    player.entity_id = "media_player.dt_test"

    # Naive datetime assumes UTC
    naive_dt = datetime.datetime(2026, 11, 1, 3, 43, 52)
    player._update_media_position_updated_at(naive_dt)
    assert player.media_position_updated_at == datetime.datetime(
        2026, 11, 1, 3, 43, 52, tzinfo=datetime.timezone.utc
    )

    # Aware datetime in non-UTC timezone converts to UTC
    tz_offset = datetime.timezone(datetime.timedelta(hours=-5))
    aware_dt = datetime.datetime(2026, 11, 1, 3, 43, 52, tzinfo=tz_offset)
    player._update_media_position_updated_at(aware_dt)
    expected_utc = datetime.datetime(2026, 11, 1, 8, 43, 52, tzinfo=datetime.timezone.utc)
    assert player.media_position_updated_at == expected_utc


async def test_template_errors_and_whitespace_state(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling of TemplateErrors and whitespace in state."""
    fallback_time = datetime.datetime(2026, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)

    hass.states.async_set("sensor.player_state", "  playing\n")
    hass.states.async_set("sensor.player_pos", "15")
    hass.states.async_set("sensor.player_updated_at", "2026-11-01T03:43:52Z")
    hass.states.async_set("sensor.player_dur", "180")
    await hass.async_block_till_done()

    config = {
        "media_player": {
            "platform": "media_player_template",
            "media_players": {
                "test": {
                    "friendly_name": "Test Player",
                    "value_template": "{{ states('sensor.player_state') }}",
                    "current_position_template": "{{ states('sensor.player_pos') }}",
                    "media_position_updated_at_template": "{{ states('sensor.player_updated_at') }}",
                    "media_duration_template": "{{ states('sensor.player_dur') }}",
                }
            },
        }
    }

    assert await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    assert state.state == "playing"
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 15
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 180

    # Test error in duration template
    player: MediaPlayerTemplate = hass.data["media_player"].get_entity("media_player.test")
    player._update_media_duration(TemplateError("duration error"))
    assert player.media_duration is None

    # Test error in position template
    player._update_media_position(TemplateError("position error"))
    assert player.media_position is None

    # Test error in updated_at template with position set
    player._attr_media_position = 20
    with patch("homeassistant.util.dt.utcnow", return_value=fallback_time):
        player._update_media_position_updated_at(TemplateError("updated_at error"))
    assert player.media_position_updated_at == fallback_time

    # Test error in updated_at template with no position set
    player._attr_media_position = None
    player._update_media_position_updated_at(TemplateError("updated_at error"))
    assert player.media_position_updated_at is None
