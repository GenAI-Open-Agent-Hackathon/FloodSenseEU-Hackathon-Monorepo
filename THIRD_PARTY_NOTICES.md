# Third-party notices

FloodSense EU stores some third-party content in this repository. This file lists it, with the licence and the attribution recorded in the repository's own records ([corpus/manifest.yaml](corpus/manifest.yaml), [docs/legal/sources.md](docs/legal/sources.md), [engines/NOTICE](engines/NOTICE)). It adds nothing that is not in those files. It is not legal advice.

Data that the product reads at run time from public APIs (PEGELONLINE, Open-Meteo, DWD ICON, GloFAS, ERA5) is not stored as documents here. Its licences and attributions are in [docs/legal/sources.md](docs/legal/sources.md). Python and npm dependencies are installed from their registries and are not vendored.

## 1. Document corpus (`corpus/pdf/`)

25 documents for the retrieval layer (RAG layer c): 12 authority, paper and insurer documents, and 13 English Wikipedia snapshots. The checksums, tiers, event ids and the rest of the metadata are in [corpus/manifest.yaml](corpus/manifest.yaml).

### 1.1 Authority, paper and insurer documents (12)

| doc_id | Title | Publisher | Licence | File | URL |
| --- | --- | --- | --- | --- | --- |
| `emsr773-aoi03-del` | [EMSR773] Horta Sud (AOI03): Delineation Map | Copernicus Emergency Management Service | CEMS On-Demand Mapping terms | `corpus/pdf/emsr773-aoi03-delineation-map.pdf` | <https://mapping.emergency.copernicus.eu/activations/EMSR773> |
| `emsr517-aoi15-gra` | [EMSR517] Bad Neuenahr-Ahrweiler (AOI15): Grading Map | Copernicus Emergency Management Service | CEMS On-Demand Mapping terms | `corpus/pdf/emsr517-aoi15-grading-map.pdf` | <https://mapping.emergency.copernicus.eu/activations/EMSR517> |
| `hess-29-6715-2025` | Torrential rainfall in Valencia, Spain, recorded by personal weather stations preceding and during the 29 October 2024 floods | Copernicus Publications | CC-BY-4.0 | `corpus/pdf/hess-29-6715-2025.pdf` | <https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf> |
| `nhess-23-1287-2023` | A multi-disciplinary analysis of the exceptional flood event of July 2021 in central Europe – Part 2: Historical context and relation to climate change | Copernicus Publications | CC-BY-4.0 | `corpus/pdf/nhess-23-1287-2023.pdf` | <https://nhess.copernicus.org/articles/23/1287/2023/nhess-23-1287-2023.pdf> |
| `easyxlab-s19` | What the maps did not show: dwellings inside the observed extent of the October 2024 DANA in Valencia, and the official flood maps | EasyxLab | CC-BY-4.0 | `corpus/pdf/easyxlab-s19.html` | <https://easybyte.es/lab/studies/s19/paper/> |
| `nhess-23-525-2023` | A multi-disciplinary analysis of the exceptional flood event of July 2021 in central Europe - Part 1: Event description and analysis | Copernicus Publications | CC-BY-4.0 | `corpus/pdf/nhess-23-525-2023.pdf` | <https://nhess.copernicus.org/articles/23/525/2023/nhess-23-525-2023.pdf> |
| `nhess-23-973-2023` | Performance of the flood warning system in Germany in July 2021 - insights from affected residents | Copernicus Publications | CC-BY-4.0 | `corpus/pdf/nhess-23-973-2023.pdf` | <https://nhess.copernicus.org/articles/23/973/2023/nhess-23-973-2023.pdf> |
| `boe-a-2004-18910` | Real Decreto Legislativo 7/2004, de 29 de octubre, por el que se aprueba el texto refundido del Estatuto Legal del Consorcio de Compensación de Seguros (original 2004 text, not consolidated) | Agencia Estatal Boletín Oficial del Estado | BOE reuse conditions (aviso legal), commercial and non-commercial reuse | `corpus/pdf/boe-a-2004-18910-original.pdf` | <https://www.boe.es/boe/dias/2004/11/05/pdfs/A36653-36661.pdf> |
| `eea-briefing-economic-losses-2025` | Economic losses and fatalities from weather- and climate-related extremes (EEA briefing, published 2 Jul 2025) | European Environment Agency | CC-BY-4.0 (EEA re-use policy) | `corpus/pdf/eea-briefing-economic-losses-2025.html` | <https://www.eea.europa.eu/en/analysis/publications/economic-losses-from-climate-extremes> |
| `eea-briefing-economic-losses-2022` | Economic losses and fatalities from weather- and climate-related events in Europe (EEA briefing, published 3 Feb 2022) | European Environment Agency | CC-BY-4.0 (EEA re-use policy) | `corpus/pdf/eea-briefing-economic-losses-2022.html` | <https://www.eea.europa.eu/en/analysis/publications/economic-losses-and-fatalities-from-weather-and-climate-related-events-in-europe> |
| `eiopa-19-485` | EIOPA Staff Discussion Paper: Protection gap for natural catastrophes (EIOPA-19/485, September 2019) | European Insurance and Occupational Pensions Authority | EIOPA legal notice: reproduction authorised without prior permission, source acknowledged | `corpus/pdf/eiopa-19-485-protection-gap.pdf` | <https://register.eiopa.europa.eu/Publications/EIOPA-19-485_EIOPA%20Staff_Discussion_Paper_Protection_Gap.pdf> |
| `eu-floods-directive-2007-60-ec` | Directive 2007/60/EC of the European Parliament and of the Council of 23 October 2007 on the assessment and management of flood risks (OJ L 288, 6.11.2007) | Publications Office of the European Union (EUR-Lex) | Commission reuse policy (Decision 2011/833/EU), reuse with source acknowledged | `corpus/pdf/eu-floods-directive-2007-60-ec.pdf` | <https://eur-lex.europa.eu/eli/dir/2007/60/oj> |

Attribution strings, as recorded in the manifest:

- `emsr773-aoi03-del`: Copernicus Emergency Management Service (© 2024 European Union), EMSR773
- `emsr517-aoi15-gra`: Copernicus Emergency Management Service (© 2021 European Union), EMSR517
- `hess-29-6715-2025`: Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0, https://doi.org/10.5194/hess-29-6715-2025
- `nhess-23-1287-2023`: Ludwig, Mohr, and co-authors (2023), CC BY 4.0, https://doi.org/10.5194/nhess-23-1287-2023
- `easyxlab-s19`: EasyxLab (2026), Study S19, CC BY 4.0, https://easybyte.es/lab/studies/s19/paper/
- `nhess-23-525-2023`: Mohr, Ehret, Kunz, Ludwig, and co-authors (2023), CC BY 4.0, https://doi.org/10.5194/nhess-23-525-2023
- `nhess-23-973-2023`: Thieken, Bubeck, Heidenreich, von Keyserlingk, Dillenardt, and Otto (2023), CC BY 4.0, https://doi.org/10.5194/nhess-23-973-2023
- `boe-a-2004-18910`: Fuente de los datos: Agencia Estatal Boletín Oficial del Estado, BOE núm. 267, 5 Nov 2004, BOE-A-2004-18910, https://www.boe.es. Original text as published; not the official consolidated version
- `eea-briefing-economic-losses-2025`: European Environment Agency (2025), Economic losses and fatalities from weather- and climate-related extremes, CC BY 4.0, https://www.eea.europa.eu/en/analysis/publications/economic-losses-from-climate-extremes
- `eea-briefing-economic-losses-2022`: European Environment Agency (2022), Economic losses and fatalities from weather- and climate-related events in Europe, CC BY 4.0, https://www.eea.europa.eu/en/analysis/publications/economic-losses-and-fatalities-from-weather-and-climate-related-events-in-europe
- `eiopa-19-485`: Source: EIOPA - European Insurance and Occupational Pensions Authority, https://eiopa.europa.eu/, EIOPA-19/485 (2019)
- `eu-floods-directive-2007-60-ec`: © European Union, https://eur-lex.europa.eu, Directive 2007/60/EC, OJ L 288, 6.11.2007, p. 27-34. Only the Official Journal text is authentic

### 1.2 Wikipedia snapshots (13, CC BY-SA 4.0)

Each file is the plain text of the article paragraphs and list items of one English Wikipedia page at a pinned revision, with reference markers, tables, infoboxes, images and captions removed. The authors are listed on each page's history (the link is in the first paragraph of each file). The licence is Creative Commons Attribution-ShareAlike 4.0 International, <https://creativecommons.org/licenses/by-sa/4.0/>.

**Share-alike applies to these 13 files only.** They are shared under the same licence, and each file says so. The FloodSense code, the other corpus documents and the rest of the repository are not adapted from them and are not licensed under CC BY-SA 4.0 by this notice. Short passages are quoted in answers and in [docs/DECK-FACTS.md](docs/DECK-FACTS.md) with the attribution below.

| doc_id | Title | Publisher | Licence | File | URL |
| --- | --- | --- | --- | --- | --- |
| `wiki-1997-central-european-flood` | 1997 Central European flood (Wikipedia, revision 1368946079) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-1997-central-european-flood.html` | <https://en.wikipedia.org/w/index.php?title=1997_Central_European_flood&oldid=1368946079> |
| `wiki-2002-european-floods` | 2002 European floods (Wikipedia, revision 1374296101) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2002-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2002_European_floods&oldid=1374296101> |
| `wiki-2010-central-european-floods` | 2010 Central European floods (Wikipedia, revision 1359816549) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2010-central-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2010_Central_European_floods&oldid=1359816549> |
| `wiki-2013-european-floods` | 2013 European floods (Wikipedia, revision 1372735297) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2013-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2013_European_floods&oldid=1372735297> |
| `wiki-2016-european-floods` | 2016 European floods (Wikipedia, revision 1360455033) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2016-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2016_European_floods&oldid=1360455033> |
| `wiki-2021-european-floods` | 2021 European floods (Wikipedia, revision 1375935659) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2021-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2021_European_floods&oldid=1375935659> |
| `wiki-2024-central-european-floods` | 2024 Central European floods (Wikipedia, revision 1377676053) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2024-central-european-floods.html` | <https://en.wikipedia.org/w/index.php?title=2024_Central_European_floods&oldid=1377676053> |
| `wiki-2024-spanish-floods` | 2024 Spanish floods (Wikipedia, revision 1379732613) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-2024-spanish-floods.html` | <https://en.wikipedia.org/w/index.php?title=2024_Spanish_floods&oldid=1379732613> |
| `wiki-seine` | Seine (Wikipedia, revision 1381786474) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-seine.html` | <https://en.wikipedia.org/w/index.php?title=Seine&oldid=1381786474> |
| `wiki-moselle` | Moselle (Wikipedia, revision 1374522670) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-moselle.html` | <https://en.wikipedia.org/w/index.php?title=Moselle&oldid=1374522670> |
| `wiki-neckar` | Neckar (Wikipedia, revision 1381972636) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-neckar.html` | <https://en.wikipedia.org/w/index.php?title=Neckar&oldid=1381972636> |
| `wiki-flood-control-netherlands` | Flood control in the Netherlands (Wikipedia, revision 1369449074) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-flood-control-netherlands.html` | <https://en.wikipedia.org/w/index.php?title=Flood_control_in_the_Netherlands&oldid=1369449074> |
| `wiki-list-of-floods` | List of floods (Wikipedia, revision 1380945599) | Wikipedia (Wikimedia Foundation) | CC-BY-SA-4.0 | `corpus/pdf/wiki-list-of-floods.html` | <https://en.wikipedia.org/w/index.php?title=List_of_floods&oldid=1380945599> |

Attribution strings, as recorded in the manifest:

- `wiki-1997-central-european-flood`: Wikipedia contributors, "1997 Central European flood", English Wikipedia, revision 1368946079 (2026-08-12), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=1997_Central_European_flood&oldid=1368946079. Paragraph text only, accessed 27 Oct 2026
- `wiki-2002-european-floods`: Wikipedia contributors, "2002 European floods", English Wikipedia, revision 1374296101 (2026-09-11), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2002_European_floods&oldid=1374296101. Paragraph text only, accessed 27 Oct 2026
- `wiki-2010-central-european-floods`: Wikipedia contributors, "2010 Central European floods", English Wikipedia, revision 1359816549 (2026-06-17), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2010_Central_European_floods&oldid=1359816549. Paragraph text only, accessed 27 Oct 2026
- `wiki-2013-european-floods`: Wikipedia contributors, "2013 European floods", English Wikipedia, revision 1372735297 (2026-09-02), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2013_European_floods&oldid=1372735297. Paragraph text only, accessed 27 Oct 2026
- `wiki-2016-european-floods`: Wikipedia contributors, "2016 European floods", English Wikipedia, revision 1360455033 (2026-06-21), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2016_European_floods&oldid=1360455033. Paragraph text only, accessed 27 Oct 2026
- `wiki-2021-european-floods`: Wikipedia contributors, "2021 European floods", English Wikipedia, revision 1375935659 (2026-09-21), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2021_European_floods&oldid=1375935659. Paragraph text only, accessed 27 Oct 2026
- `wiki-2024-central-european-floods`: Wikipedia contributors, "2024 Central European floods", English Wikipedia, revision 1377676053 (2026-09-30), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2024_Central_European_floods&oldid=1377676053. Paragraph text only, accessed 27 Oct 2026
- `wiki-2024-spanish-floods`: Wikipedia contributors, "2024 Spanish floods", English Wikipedia, revision 1379732613 (2026-10-11), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=2024_Spanish_floods&oldid=1379732613. Paragraph text only, accessed 27 Oct 2026
- `wiki-seine`: Wikipedia contributors, "Seine", English Wikipedia, revision 1381786474 (2026-10-24), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=Seine&oldid=1381786474. Paragraph text only, accessed 27 Oct 2026
- `wiki-moselle`: Wikipedia contributors, "Moselle", English Wikipedia, revision 1374522670 (2026-09-12), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=Moselle&oldid=1374522670. Paragraph text only, accessed 27 Oct 2026
- `wiki-neckar`: Wikipedia contributors, "Neckar", English Wikipedia, revision 1381972636 (2026-10-25), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=Neckar&oldid=1381972636. Paragraph text only, accessed 27 Oct 2026
- `wiki-flood-control-netherlands`: Wikipedia contributors, "Flood control in the Netherlands", English Wikipedia, revision 1369449074 (2026-08-15), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=Flood_control_in_the_Netherlands&oldid=1369449074. Paragraph text only, accessed 27 Oct 2026
- `wiki-list-of-floods`: Wikipedia contributors, "List of floods", English Wikipedia, revision 1380945599 (2026-10-18), CC BY-SA 4.0, https://en.wikipedia.org/w/index.php?title=List_of_floods&oldid=1380945599. Paragraph text only, accessed 27 Oct 2026

## 2. Vendored code: Meterless engines (`engines/vendor/`)

`engines/vendor/` contains software from Meterless (<https://github.com/Meterless/meterless>), licensed under the Apache License, Version 2.0. Per [engines/NOTICE](engines/NOTICE) it was copied unchanged from commit `1742dec` (19 Oct 2026):

- `engines/vendor/hmem/reference/src/`, `engines/vendor/hmem/conformance/` and `engines/vendor/hmem/reference/tsconfig.json` (H-MEM),
- `engines/vendor/world-model/reference/src/`, `engines/vendor/world-model/conformance/` and `engines/vendor/world-model/reference/tsconfig.json` (World Model).

The full licence text for each engine is in [engines/vendor/hmem/LICENSE](engines/vendor/hmem/LICENSE) and [engines/vendor/world-model/LICENSE](engines/vendor/world-model/LICENSE) (Apache License 2.0). The upstream vitest smoke tests were not copied; the conformance suites are the acceptance check here. Everything in `engines/` outside `vendor/` (`src/`, `test/`, `scripts/`) is FloodSense code.

## 3. FloodSense code

There is no `LICENSE` file for the FloodSense code in this repository yet. The licence is a team decision. Until a `LICENSE` file is added, the code is unlicensed, and this notice grants no rights to it.
