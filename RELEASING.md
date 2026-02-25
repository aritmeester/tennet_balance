# Releasing

Deze repository gebruikt een vaste releaseprocedure voor consistente versies en betrouwbare publicaties.

## Versieformaat

`yymm.dd.release`

- `yy` = jaar (2 cijfers)
- `mm` = maand (2 cijfers)
- `dd` = dag (2 cijfers)
- `release` = oplopend releasenummer op die dag

Voorbeeld: `2602.25.1` = 2026-02-25, release 1.

## Prerelease-versie

Gebruik voor prereleases een beta-suffix op dezelfde basisversie:

- `2602.25.1b1`
- `2602.25.1b2`

Daarna volgt de definitieve release zonder suffix:

- `2602.25.1`

## Standaard releaseflow

### 1) Versie in manifest aanpassen

Bestand: `custom_components/tennet_balance/manifest.json`

- prerelease: zet `version` op bijvoorbeeld `2602.25.1b1`
- final: zet `version` op bijvoorbeeld `2602.25.1`

### 2) Commit + push

Maak een commit met duidelijke releaseboodschap en push naar `main`.

### 3) Validatie afwachten

Wacht totdat de GitHub Actions workflow **Home Assistant Validate** geslaagd is.

### 4) GitHub release maken

- Tag: `v<versie>` (bijv. `v2602.25.1b1`)
- Prerelease: **aan** voor beta (`b1`, `b2`, ...)
- Prerelease: **uit** voor definitieve release
- Release notes: neem de relevante tekst uit `CHANGELOG.md` (`Unreleased`)

### 5) Controle achteraf

Controleer:

- juiste versie in `manifest.json`
- juiste tag op GitHub
- prerelease-flag correct ingesteld
- release-notes gevuld vanuit changelog

## Praktisch voorbeeld

- Prerelease:
  - manifest: `2602.25.1b1`
  - release: `v2602.25.1b1` (prerelease)
- Final:
  - manifest: `2602.25.1`
  - release: `v2602.25.1` (normale release)
