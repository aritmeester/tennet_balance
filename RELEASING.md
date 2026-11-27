# Releasing

Deze repository gebruikt een vaste releaseprocedure voor consistente
versies, betrouwbare publicaties en gecontroleerde uitrol van wijzigingen.

## Versieformaat

`yymm.dd.release`

- `yy` = jaar (2 cijfers)
- `mm` = maand (2 cijfers)
- `dd` = dag (2 cijfers)
- `release` = oplopend releasenummer op die dag

Voorbeeld: `2611.27.1` = 2026-11-27, release 1.

## Prerelease-versie

Gebruik voor prereleases een beta-suffix op dezelfde basisversie:

- `2611.27.2b1`
- `2611.27.2b2`
- `2611.27.2b3`

Daarna volgt de definitieve release zonder suffix:

- `2611.27.2`

Bij promotie van een prerelease naar een definitieve release blijft
de basisversie gelijk, ook wanneer de definitieve release op een
latere datum wordt gepubliceerd.

De Release-workflow bepaalt automatisch of een release een
prerelease is op basis van het beta-suffix in de versie.

| Versie | Git-tag | Release type |
|--------|---------|--------------|
| `2611.27.2b1` | `v2611.27.2b1` | Prerelease |
| `2611.27.2b2` | `v2611.27.2b2` | Prerelease |
| `2611.27.2` | `v2611.27.2` | Definitieve release |

## Releasestrategie

Gebruik bij voorkeur een prerelease voor wijzigingen die invloed
hebben op het runtimegedrag van de integratie.

Voorbeelden:

- Wijzigingen aan de DataUpdateCoordinator
- Wijzigingen aan API-communicatie en polling
- Wijzigingen aan sensorberekeningen
- Wijzigingen aan beschikbaarheid en foutafhandeling
- Wijzigingen aan caching en dataverwerking
- Wijzigingen aan Recorder-gedrag
- Wijzigingen aan entity metadata of unieke identifiers

Kleine documentatiewijzigingen en wijzigingen aan de
ontwikkelomgeving vereisen niet noodzakelijk een nieuwe release.

## Standaard releaseflow

### 1. Versie in manifest aanpassen

Bestand: `custom_components/tennet_balance/manifest.json`

Voor een prerelease:

```json
"version": "2611.27.2b1"
```

Voor een definitieve release:

```json
"version": "2611.27.2"
```

### 2. Changelog bijwerken

Bestand: `CHANGELOG.md`

Voeg een sectie toe waarvan de versie exact overeenkomt met
de versie in `manifest.json`.

Bijvoorbeeld:

```markdown
## Unreleased

## 2611.27.2b1

Changes since 2611.27.1:

### Added

- Description of new functionality.

### Changed

- Description of changed functionality.

### Fixed

- Description of resolved issues.
```

Gebruik waar relevant de volgende categorieën:

- Added
- Changed
- Deprecated
- Removed
- Fixed
- Security

Beschrijf wijzigingen vanuit het perspectief van de gebruiker.

De Release-workflow gebruikt de betreffende versiesectie
automatisch als GitHub release notes.

Na een release hoort `Unreleased` leeg te zijn of alleen
placeholders te bevatten.

### 3. Lokale validatie uitvoeren

Installeer de ontwikkelafhankelijkheden:

```bash
python -m pip install -r requirements-dev.txt
```

Controleer de Python-syntax:

```bash
python -m compileall -q custom_components/tennet_balance tests
```

Voer alle unit tests uit:

```bash
python -m unittest discover -s tests -v
```

Controleer de Git-wijzigingen:

```bash
git diff --check
git status --porcelain
git diff
```

Controleer dat:

- Alle unit tests succesvol zijn.
- Er geen Python-syntaxfouten zijn.
- Alleen bedoelde bestanden gewijzigd zijn.
- De manifestversie overeenkomt met de changelog.
- Er geen tijdelijke bestanden, Python-cachebestanden of
  gevoelige gegevens worden gecommit.

### 4. Commit en push

Maak een commit met een duidelijke releaseboodschap.

Voor een prerelease:

```bash
git commit -m "Release 2611.27.2b1 - Optimize coordinator processing"
git push origin main
```

Voor een definitieve release:

```bash
git commit -m "Release 2611.27.2"
git push origin main
```

Controleer vooraf welke bestanden zijn toegevoegd aan de commit:

```bash
git diff --cached --stat
git diff --cached --check
```

### 5. GitHub Actions-validatie

Wacht totdat de workflow
[Home Assistant Validate](https://github.com/aritmeester/tennet_balance/actions/workflows/validate.yml)
volledig geslaagd is.

De workflow bestaat uit de volgende validatiejobs:

| Validatie | Platform | Python |
|-----------|----------|--------|
| HACS | Ubuntu | - |
| Hassfest | Ubuntu | - |
| Unit tests | Ubuntu | 3.12 |
| Unit tests | Ubuntu | 3.14 |
| Unit tests | Windows | 3.12 |
| Unit tests | Windows | 3.14 |

Alle zes validatiejobs moeten succesvol zijn.

Publiceer geen release wanneer een validatiejob is mislukt.

De Release-workflow controleert momenteel niet automatisch
of de validatieworkflow succesvol is afgerond. Dit moet daarom
voor publicatie handmatig worden gecontroleerd.

### 6. GitHub release publiceren

Open de GitHub Actions-workflow
[Release](https://github.com/aritmeester/tennet_balance/actions/workflows/release.yml).

Selecteer:

- Run workflow
- Branch: `main`
- Version: de exacte versie uit `manifest.json`

Voorbeeld prerelease:

```text
2611.27.2b1
```

Voorbeeld definitieve release:

```text
2611.27.2
```

De workflow voert automatisch de volgende stappen uit:

1. Checkout van de geselecteerde branch.
2. Controle van de manifestversie.
3. Extractie van release notes uit `CHANGELOG.md`.
4. Aanmaken van de Git-tag.
5. Pushen van de Git-tag.
6. Aanmaken van de GitHub release.
7. Instellen van de prerelease-flag op basis van het beta-suffix.

Maak normaal gesproken niet handmatig een Git-tag of GitHub
release aan wanneer de Release-workflow gebruikt wordt.

### 7. Controle na publicatie

Controleer op de GitHub Releases-pagina:

- De juiste releaseversie.
- De juiste Git-tag.
- De juiste commit waarop de tag gebaseerd is.
- De correcte prerelease-flag.
- De release notes uit `CHANGELOG.md`.
- De juiste versie in `manifest.json` binnen de gepubliceerde tag.

Controleer vervolgens of de release beschikbaar is in HACS.

## Prerelease testen

Installeer de prerelease via HACS door, indien nodig,
betaversies beschikbaar te maken en de gewenste versie
handmatig te selecteren.

Herstart Home Assistant na installatie.

Controleer minimaal de volgende onderdelen:

- [ ] Home Assistant start zonder integratiefouten.
- [ ] De integratie wordt correct geladen.
- [ ] Bestaande entiteiten blijven beschikbaar.
- [ ] Entity IDs en unique IDs blijven behouden.
- [ ] Sensorwaarden en attributen worden correct bijgewerkt.
- [ ] De normale pollingfrequentie blijft behouden.
- [ ] Overgangen tussen kwartieren werken correct.
- [ ] Diagnostische sensoren blijven correct functioneren.
- [ ] Bestaande automatiseringen blijven functioneren.
- [ ] Recorder-gedrag komt overeen met de verwachtingen.
- [ ] Long-term statistics blijven functioneren waar van toepassing.
- [ ] Er zijn geen nieuwe relevante fouten in de Home Assistant-logs.

Voer daarnaast eventuele release-specifieke acceptatietests uit.

### Observatieperiode

Gebruik voor wijzigingen aan het runtimegedrag bij voorkeur
een observatieperiode van minimaal 24 uur.

Verleng deze periode wanneer specifieke omstandigheden
nodig zijn om de wijziging voldoende te kunnen testen,
bijvoorbeeld API-storingen of bijzondere marktcondities.

De duur van de observatieperiode is geen vervanging voor
gerichte functionele validatie.

### Problemen tijdens de prerelease

Wanneer tijdens de observatieperiode problemen worden gevonden:

1. Analyseer en reproduceer het probleem.
2. Voeg waar mogelijk een regressietest toe.
3. Corrigeer de implementatie.
4. Verhoog het beta-releasenummer.
5. Werk `manifest.json` en `CHANGELOG.md` bij.
6. Doorloop opnieuw de volledige releaseprocedure.

Bijvoorbeeld:

```text
2611.27.2b1 -> 2611.27.2b2 -> 2611.27.2b3
```

Wijzig of verplaats geen bestaande gepubliceerde Git-tags.

Elke prerelease moet reproduceerbaar blijven.

## Promotie naar een definitieve release

Wanneer de laatste prerelease succesvol is gevalideerd:

1. Verwijder het beta-suffix uit de manifestversie.
2. Voeg een definitieve versiesectie toe aan `CHANGELOG.md`.
3. Neem alle relevante wijzigingen sinds de vorige definitieve
   release op in deze sectie.
4. Behoud de eerdere prerelease-secties voor traceerbaarheid.
5. Voer de lokale validatie opnieuw uit.
6. Commit en push de wijzigingen naar `main`.
7. Controleer of alle GitHub Actions-validatiejobs slagen.
8. Start de Release-workflow met de definitieve versie.
9. Controleer of de release zonder prerelease-flag gepubliceerd is.
10. Controleer of de definitieve release beschikbaar is in HACS.

Voorbeeld:

```text
2611.27.2b1 -> 2611.27.2
```

De definitieve release krijgt een eigen Git-tag:

```text
v2611.27.2
```

De bestaande prerelease-tag blijft behouden:

```text
v2611.27.2b1
```

Promotie naar een definitieve release bevat bij voorkeur
geen functionele wijzigingen ten opzichte van de laatst
succesvol geteste prerelease.

Wanneer aanvullende functionele wijzigingen nodig zijn,
publiceer dan eerst een nieuwe prerelease.

## Rollback

Wanneer een release problemen veroorzaakt:

1. Selecteer de laatst bekende werkende versie via HACS.
2. Installeer deze versie.
3. Herstart Home Assistant.
4. Controleer of de integratie weer correct functioneert.
5. Analyseer het probleem en voeg een regressietest toe.
6. Publiceer een gecorrigeerde versie.

Verwijder of overschrijf bestaande gepubliceerde Git-tags
niet om een release te corrigeren.

Gebruik een nieuwe versie voor een gecorrigeerde release.

## Releasechecklist

### Voor publicatie

- [ ] Manifestversie bijgewerkt.
- [ ] Changelog bijgewerkt.
- [ ] Lokale unit tests geslaagd.
- [ ] Python-syntaxcontrole geslaagd.
- [ ] Git-wijzigingen gecontroleerd.
- [ ] Commit gepusht naar `main`.
- [ ] HACS-validatie geslaagd.
- [ ] Hassfest-validatie geslaagd.
- [ ] Alle cross-platform unit tests geslaagd.

### Na publicatie

- [ ] Git-tag correct.
- [ ] Releaseversie correct.
- [ ] Prerelease-flag correct.
- [ ] Release notes correct.
- [ ] Release beschikbaar in HACS.
- [ ] Installatie en runtimevalidatie uitgevoerd.

## Praktisch voorbeeld

### Eerste prerelease

- Manifest: `2611.27.2b1`
- Changelog: `## 2611.27.2b1`
- Workflow input: `2611.27.2b1`
- Git-tag: `v2611.27.2b1`
- GitHub release: prerelease

### Tweede prerelease

Indien aanvullende correcties noodzakelijk zijn:

- Manifest: `2611.27.2b2`
- Changelog: `## 2611.27.2b2`
- Workflow input: `2611.27.2b2`
- Git-tag: `v2611.27.2b2`
- GitHub release: prerelease

### Definitieve release

Na succesvolle validatie:

- Manifest: `2611.27.2`
- Changelog: `## 2611.27.2`
- Workflow input: `2611.27.2`
- Git-tag: `v2611.27.2`
- GitHub release: definitieve release

## Gerelateerde documentatie

- [README.md](README.md)
- [CHANGELOG.md](CHANGELOG.md)
- [Development dependencies](requirements-dev.txt)
- [Validation workflow](.github/workflows/validate.yml)
- [Release workflow](.github/workflows/release.yml)
- [GitHub Releases](https://github.com/aritmeester/tennet_balance/releases)