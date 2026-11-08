# OpenWeather current conditions

`GET /weather-current?lat=17.12&lon=-61.8` adds current temperature,
feels-like temperature, humidity, and an optional weather description using
OpenWeather One Call 4.0. Existing alerts, tides, and radar endpoints are unchanged.
The response includes the provider's data timestamp (`dt`), cache timestamp
(`fetched_at`), and source. Missing optional values are omitted.

## Render configuration

- Keep the existing Python start command and dependencies.
- Set `OPENWEATHER_API_KEY` in Render's Environment settings. Do not commit it.
  An existing value can be reused if authorized for One Call 4.0.
- Keep the OpenWeather account's daily limit at 1,000 calls.
- Optional: set `OPENWEATHER_CACHE_DB` to a writable path on an existing persistent
  disk. By default the SQLite file is beside the Python module. No additional
  disk purchase is required; on ephemeral storage the budget/cache reset when
  the filesystem is replaced. Separate instances with independent files also
  have separate budgets, so the provider's account-wide cap remains essential.

The endpoint shares a 15-minute cache for each location across clients. It
reserves at most 900 upstream attempts per UTC day per database, including failed
attempts. Cached responses remain available after reaching that budget.
Upstream failures trigger a shared cooldown (one hour for 401/403/429; five
minutes for other errors). Error responses never include the upstream URL/key.

Invalid or missing coordinates return HTTP 400. An unconfigured key, exhausted
budget, upstream failure, or invalid/old upstream data returns HTTP 503. Clients
should keep their existing Open-Meteo fallback; this endpoint does not replace
forecasts, marine data, or official local warnings.

## Validation

Run from the repository root:

```sh
python -m unittest discover -s tests -v
```

Tests use fixtures and temporary SQLite files; no key or paid calls are needed.
After deploying, verify `/health` and `/weather-current?lat=17.12&lon=-61.8`.
A successful response must contain `source: "OpenWeather"` and current data.
The Flutter client must be updated separately before the phone app uses this
endpoint. This repository contains only the backend.
