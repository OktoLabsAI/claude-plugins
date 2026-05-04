---
description: Diagnose okto-pulse plugin state and offer reversible auto-fixes for any red checks.
when_to_use: Run this anytime the plugin feels off, before reporting issues, or after a failed /okto-pulse:setup.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash, Read, Write
---

# okto-pulse:doctor

Read-only diagnosis followed by an opt-in remediation loop.

## Steps

1. **Run the diagnostic** via `Bash`:

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/bin/doctor.sh"
   ```

   Each line of stdout is one NDJSON record - either a check or the
   final `summary`. Parse them.

2. **All green?** Print the summary and stop.

3. **Any red?** Group by check name and propose fixes from the
   reversible-fix matrix below. Print **one** y/n prompt that lists
   every fix you intend to apply. On `y`, run them in order and re-run
   `doctor.sh`. On `n`, print the manual remediation commands and stop.

## Reversible-fix matrix

| Red check                 | Auto-fix                                                  |
|---------------------------|-----------------------------------------------------------|
| `readyz_200` (local-pip)  | re-spawn `okto-pulse serve --accept-terms` (record pid)   |
| `container_running`       | `docker compose -f ${CLAUDE_PLUGIN_ROOT}/deploy/docker-compose.yml start okto-pulse` |
| missing userConfig key    | prompt for value and write via plugin runtime             |
| `active_board_file_exists` | run interactive board picker (`okto_pulse_list_my_boards`) |
| `okto_pulse_pip_installed` | `python3.12 -m pip install -U okto-pulse==<plugin-version>` (with confirm) |
| `image_tag_matches_plugin` | `docker pull ghcr.io/oktolabsai/okto-pulse:<plugin-version>` |
| `pulse_api_token_set`     | clear keychain entry and re-prompt                        |

## Never auto-fix

- drop tables / reset KG
- force-recreate containers
- overwrite credentials silently
- alter okto-pulse server config
- delete `active-board.json` or graph data

Per BR `br_98c485f6`: any fix outside this matrix requires the user to
run the underlying command themselves.
