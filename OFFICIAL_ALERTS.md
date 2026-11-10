# Official weather alert coverage

The feed checks four official marine products (small-craft and high-surf advisory/
warning) and six verified official tropical/flood statement URLs. It recognizes
local tropical-storm/hurricane watches and warnings, flood products, and separate
Antigua/Barbuda alert levels. An old public page is not proof of an active alert.
Issue time, validity, explicit locality, operative wording and cancellation are
checked. Negated, conditional and future cancellations do not clear current
warnings; cancelling one island does not cancel another.

Marine timing is evaluated independently for Antigua and Barbuda. A failed or
ambiguous check is unknown, rather than verified inactive. Named cached alerts
are retained only within their original validity bounds. Verified cancellations
and changed source scopes clear old alerts. Refreshes are singleflight and cached
for five minutes, with alert validity boundaries honored before the normal TTL.

`/alerts` returns `alerts`, canonical `links`, `alert_sources`, `status`,
`checked_at`, per-source `checked` results and `coverage`. Status is `ready`,
`partial` or `unavailable`. Empty incomplete reports return HTTP503 so older
clients do not mistake failed checks for an all-clear. The updated client reads
structured200/503 reports and shows incomplete coverage as unverified. Each
source includes current names, original check times and applicable validity.

Official source pages can retain archived or stale documents. These remain
unverified when their current status cannot be established; this feed does not
claim exhaustive coverage of every possible future product. The Weather card
shows current verified or explicitly cached/unverified notices above the daily
forecasts, not predicted warnings for future forecast dates.

No fixture alert or weather data is returned by production. Unit tests use
injected clocks/readers; live-source checks verify old/foreign products cannot
become current local warnings. No extra dependency or API key is required.

Run `python -m unittest discover -s tests -p 'test_*.py'` with existing dependencies.
