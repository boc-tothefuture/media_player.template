# media_player.template

media_player template for Home Assistant.

> **Fork note:** This repository is a fork of [Sennevds/media_player.template](https://github.com/Sennevds/media_player.template). All credit to the original author @Sennevds.

[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License][license-shield]](LICENSE)

Current implemented features:

- `on_action`
- `off_action`
- `play_action`
- `play_pause_action`
- `stop_action`
- `pause_action`
- `next_action`
- `previous_action`
- `volume_up_action`
- `volume_down_action`
- `mute_action`
- `source list`
- `current source`
- `title`
- `artist`
- `album`
- `current volume`
- `set_volume action`
- `play_media action` (not tested)
- `app_id_template`
- `app_name_template`
- `media_content_type_template`
- `media_image_url_template`
- `media_image_url_remotely_accessible`
- `media_episode_template`
- `media_season_template`
- `media_series_title_template`
- `media_album_artist_template`
- `current_position_template`
- `media_position_updated_at_template`
- `media_duration_template`
- `current_is_muted_template`
- `device_class`

`media_content_type_template` can be one of the following values:

- tv_show
- music
- movie
- video

Based on this value other parameters are shown (e.g. artist is only shown when type is music).

## Media Position & Position Updated At

The integration supports position tracking for media scrub bars in the frontend.

```yaml
current_position_template: "{{ state_attr('sensor.x','position_s') | int(0) }}"
media_position_updated_at_template: "{{ state_attr('sensor.x','position_updated_at') }}"
```

- `current_position_template` (*Optional*, template): Returns the media position in seconds. Position and duration are maintained regardless of playback state (surviving `playing` -> `buffering` -> `playing` transitions as well as `idle`).
- `media_position_updated_at_template` (*Optional*, template): Returns the timestamp when `current_position_template` was valid as an ISO-8601 string (e.g., `"2026-11-01T03:43:52Z"` or `"2026-11-01T03:43:52.702492+00:00"`), a `datetime` object, or empty/None.
  - If omitted, legacy behavior is preserved (stamping `dt_util.utcnow()` whenever the position value changes).
  - When configured, resuming playback at the same position with an updated timestamp correctly advances the frontend scrub bar without stale jumps.
  - If empty, unknown, unavailable, or on template error: falls back to `dt_util.utcnow()` if a position is set, or `None` if position is cleared.

## Variables used:

set_volume:

- `{volume}`

mute:

- `{is_muted}`

play_media:

- `{media_type}`
- `{media_id}`

## Preview config:

```yaml
media_player:
  - platform: media_player_template
    media_players:
      receiver:
        friendly_name: Receiver
        device_class: receiver
        current_source_template: "{{ states('input_text.selected_source') }}"
        value_template: >
          {% if is_state("input_boolean.receiver_on", "on") -%}
            on
          {%- else -%}
            off
          {%- endif %}
        turn_on:
          service: switch.turn_on
          data_template:
            entity_id: switch.receiver_on
        turn_off:
          service: switch.turn_on
          data_template:
            entity_id: switch.receiver_off
        volume_up:
          service: switch.turn_on
          data_template:
            entity_id: switch.volume_up
        volume_down:
          service: switch.turn_on
          data_template:
            entity_id: switch.vol
        inputs:
          source 1:
            service: input_boolean.turn_on
            data_template:
              entity_id: input_boolean.source_1
          source 2:
            service: input_boolean.turn_on
            data_template:
              entity_id: input_boolean.source_2
        set_volume:
          service: input_text.set_value
          data:
            entity_id: input_text.selected_volume
            value: "{{volume}}"
        mute:
          service: input_number.set_value
          data:
            entity_id: input_number.selected_is_muted
            value: "{{is_muted}}"
        current_is_muted_template: >
          {{ states('input_boolean.is_muted') }}
        app_id_template: "{{ states('input_text.app_id') }}"
        app_name_template: "{{ states('input_text.app_name') }}"
        album_art_template: "{{ states('input_text.album_art') }}"
        title_template: "{{ states('input_text.title') }}"
        album_template: "{{ states('input_text.album') }}"
        artist_template: "{{ states('input_text.artist') }}"
        current_position_template: "{{ state_attr('sensor.x', 'position_s') | int(0) }}"
        media_position_updated_at_template: "{{ state_attr('sensor.x', 'position_updated_at') }}"
        media_duration_template: "{{ state_attr('sensor.x', 'duration_s') | int(0) }}"
```

## Note on Entity State After Home Assistant Restart

In Home Assistant core, template entities evaluate and track state changes through `async_track_template_result`.

During Home Assistant startup or restart:
1. When the template media player is registered, its state begins as `unknown` until its templates render.
2. If referenced entities in `value_template` are not yet available or restored as `unknown`/`unavailable` during early startup, the template evaluates to `unknown`.
3. If the underlying source entities do not subsequently emit a `state_changed` event (for example, if they remain in their restored state or are unpolled), the template listener will not re-evaluate automatically.
4. Calling the `homeassistant.update_entity` service forces `TemplateEntity.async_update` (`_template_result_info.async_refresh()`), immediately re-rendering the template against current state machine values.

## Changelog

### 1.1.0
- Added optional `media_position_updated_at_template` configuration key (`cv.template`) to supply the exact source timestamp (supporting ISO-8601 strings and datetimes) for media position updates.
- Removed `PLAYING` / `PAUSED` state gating from `_update_media_position` and `_update_media_duration`, allowing position and duration to survive buffering and idle states.
- Fixed position timestamp handling so resuming at the same position with an updated timestamp refreshes `media_position_updated_at`.
- Ensured template callback evaluation order invariance (position, duration, and timestamp remain correct regardless of callback execution order).
- Handled whitespace in `value_template` to prevent invalid state failures.
- Updated `manifest.json` version to 1.1.0 and added fork maintenance metadata.
- Added comprehensive pytest test suite using `pytest-homeassistant-custom-component`.

[license-shield]: https://img.shields.io/github/license/boc-tothefuture/media_player.template.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/boc-tothefuture/media_player.template?style=for-the-badge
[releases]: https://github.com/boc-tothefuture/media_player.template/releases
