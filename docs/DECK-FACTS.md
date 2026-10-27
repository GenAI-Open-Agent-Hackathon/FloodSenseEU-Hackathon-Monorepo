# Deck facts: event figures and where they come from

Every figure below is quoted from a document stored in this repository (`corpus/pdf/`, listed in `corpus/manifest.yaml`). Nothing is rounded or added. All quotes are from English Wikipedia snapshots at a pinned revision (CC BY-SA 4.0; authors are listed in each file and in [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)). Quotes are single sentences, copied exactly.

How to read a locator. `section` and `paragraph` count the way the ingest does (`scripts/rag_ingest.py`, `sections_from_html`): the `h1` title and each `h2` start a new section; each `p` is a paragraph, counted from 1 inside its section. In section 1, paragraph 1 is the "Source:" line of the file, so the article text starts at paragraph 2. These are the same numbers the demo memories use in `api/app/demo_seed.py`.

**Before you put a death toll on a slide, read "Where the sources disagree" at the end. Pick one figure, say which source it is, and say "at least" where the source does.**

## Ahr valley and Germany, July 2021

Document: `wiki-2021-european-floods`, "2021 European floods", revision 1375935659 (21 Sep 2026).
Revision URL: <https://en.wikipedia.org/w/index.php?title=2021_European_floods&oldid=1375935659>

| Figure | Quote | Section, paragraph |
| --- | --- | --- |
| Deaths, all countries: 243, of which 196 in Germany | "At least 243 people died in the floods, including 196 in Germany, 39 in Belgium, two in Romania, one in Italy and one in Austria." | section 1 "2021 European floods", paragraph 2 |
| Deaths in Germany: 184 | "With at least 184 deaths, the floods are the deadliest natural disaster in Germany since the North Sea flood of 1962." | section 3 "Impact", paragraph 11 |
| Rhineland-Palatinate 135 (all in Ahrweiler), North Rhine-Westphalia 47, Bavaria 2 | "During the floods, 135 people died in Rhineland-Palatinate (all of whom were in the district of Ahrweiler), 47 in North Rhine-Westphalia (twenty-seven of whom in Euskirchen), and two in Bavaria." | section 3 "Impact", paragraph 12 |
| Ahr (district of Ahrweiler): 110 | "Some of the worst damage from the flood was in the district of Ahrweiler, Rhineland-Palatinate, where the river Ahr rose, destroying many buildings and causing at least 110 deaths." | section 3 "Impact", paragraph 13 |
| Ahr, earlier worst flood: 1910, up to 200 killed | "The flooding here was the worst since 1910 when up to 200 people were killed in flash flooding." | section 3 "Impact", paragraph 13 |
| Insured and total cost | "The floods are estimated to have cost at least €2 billion (US$2.35 billion) in insured losses, with the total damage costs being much higher, amounted to be €46 billion (US$54 billion)." | section 1 "2021 European floods", paragraph 3 |
| Germany direct and indirect damage | "Direct damage caused by the flooding in Germany was estimated at €33.4 billion (US$39.3 billion) with further €7.1 billion (US$8.36 billion) in indirect damage." | section 3 "Impact", paragraph 19 |
| Rain at Reifferscheid and Cologne | "In Reifferscheid, 207 mm (8.1 in) fell within a nine-hour period while Cologne observed 154 mm (6.1 in) in 24 hours." | section 2 "Weather events", paragraph 1 |

The Ahr replay in the product uses ERA5 rain and GloFAS discharge from Open-Meteo, not the figures above. Those series are far below the published peak (for example about 1000 m3/s reconstructed at Altenahr), so the deck must not call them observed ([SUBMISSION.md](SUBMISSION.md), "Honest limits").

## Valencia, 29 October 2024

Document: `wiki-2024-spanish-floods`, "2024 Spanish floods", revision 1379732613 (11 Oct 2026).
Revision URL: <https://en.wikipedia.org/w/index.php?title=2024_Spanish_floods&oldid=1379732613>

| Figure | Quote | Section, paragraph |
| --- | --- | --- |
| Deaths: about 241 | "The resulting floodwaters caused the deaths of about 241 people and substantial property damage." | section 1 "2024 Spanish floods", paragraph 2 |
| Deaths: at least 232 (224 in the province of Valencia) | "The floodwaters killed at least 232 people, including 224 in the province of Valencia, seven more in Castile–La Mancha and one in Andalusia." | section 5 "Casualties and damage", paragraph 1 |
| Paiporta: 62 | "In the ground zero town of Paiporta alone, 62 people died." | section 4 "Flooding", paragraph 5 |
| Insurance claims and value | "The Insurance Compensation Consortium recorded at least 116,000 insurance claims for flood damage with a total value of at least 3.5 billion euros ($3.8 billion), with 60% of the claims for cars and 31% for homes." | section 5 "Casualties and damage", paragraph 4 |
| Total and insured damage (Munich Re) | "Munich Re estimates the total damage to have been 10.7 billion euros ($11 billion) of which 4.1 billion euros ($4.2 billion) were insured." | section 5 "Casualties and damage", paragraph 4 |
| Share of Europe's flood deaths in 2024 | "Valencia alone accounted for 70% of flood-related deaths in Europe in 2024." | section 5 "Casualties and damage", paragraph 5 |
| Spanish one-hour rain record | "At 18:00, the town of Turís recorded 42 mm of precipitation in 10 minutes, and set the new Spanish record with 184.6 mm (7.27 in) in one hour." | section 4 "Flooding", paragraph 3 |

## Storm Boris, September 2024 (Central Europe)

Document: `wiki-2024-central-european-floods`, "2024 Central European floods", revision 1377676053.
Revision URL: <https://en.wikipedia.org/w/index.php?title=2024_Central_European_floods&oldid=1377676053>

| Figure | Quote | Section, paragraph |
| --- | --- | --- |
| Deaths 28; damage and insured loss (Munich Re) | "The floods caused 28 fatalities, and Munich Re estimates the total damage to have been approximately 4.2 billion euros ($4.3 billion), of which approximately 1.9 billion euros ($2.1 billion) were insured." | section 1 "2024 Central European floods", paragraph 2 |
| Poland, reported dead: ten | "Ten people were reported dead as a result of the floods" | section 2 "By country", paragraph 8 |
| Poland, confirmed victims: nine | "The number of flood victims was officially confirmed as 9." | section 2 "By country", paragraph 14 |
| Romania: seven | "Seven people were reported dead as the result of floods in Romania." | section 2 "By country", paragraph 16 |
| Lower Austria: five | "Five people, including one firefighter on duty, died in Lower Austria." | section 2 "By country", paragraph 1 |

## Other figures in the demo memories

These are the other death and people counts that appear in the 59 labelled demo-seed memories (`api/app/demo_seed.py`, `HISTORY`). The quote is the sentence in the stored document; the revision URL is the file's `HISTORY_URLS` entry.

| Memory text (short) | Stored sentence | doc_id, section, paragraph | Revision URL |
| --- | --- | --- | --- |
| Oder 1997: 114 died | "The flood caused the deaths of 114 people (56 in Poland, 50 in the Czech Republic) and material damages estimated at $4.5 billion (3.8 billion euros in the Czech Republic and Poland and 330 million euros in Germany)." | `wiki-1997-central-european-flood`, section 5 "Fatalities and damages", paragraph 1 | <https://en.wikipedia.org/w/index.php?title=1997_Central_European_flood&oldid=1368946079> |
| Poland 2010: at least 25 | "In Poland, the floods caused the deaths of at least 25 people, the evacuation of approximately 23,000 people, and an estimated economic cost of 2.5 billion euros." | `wiki-2010-central-european-floods`, section 2 "Poland", paragraph 1 | <https://en.wikipedia.org/w/index.php?title=2010_Central_European_floods&oldid=1359816549> |
| Germany and Neckar 2016: at least 21 | "At least 21 people died in the floods." | `wiki-2016-european-floods`, section 1 "2016 European floods", paragraph 2 | <https://en.wikipedia.org/w/index.php?title=2016_European_floods&oldid=1360455033> |
| Baden-Württemberg 2016: four | "While no one was killed in Braunsbach, four people died in Baden-Württemberg alone, three of them in the floods, and a fourth victim, a 13-year-old girl, was killed while seeking shelter from the rain under a railway bridge in Schorndorf, near Stuttgart." | `wiki-2016-european-floods`, section 2 "Flooded countries", paragraph 1 | same as above |
| Seine 2016, France: four | "Four people died in the floods." | `wiki-2016-european-floods`, section 2 "Flooded countries", paragraph 7 | same as above |
| Danube, St. Mary Magdalene's flood: 6000 | "The overall number of casualties is not known, but it is believed that in the Danube area alone 6000 people were killed." | `wiki-list-of-floods`, section 2 "List of floods", paragraph 3 | <https://en.wikipedia.org/w/index.php?title=List_of_floods&oldid=1380945599> |

## Where the sources disagree

Our stored documents do not give one number for these events, so a slide should name its source.

- **Valencia 2024:** about 241 (section 1, paragraph 2) against at least 232, of which 224 in the province of Valencia (section 5, paragraph 1). Both are in the same article. The demo memory uses 241. A conservative slide can say "at least 232" or "about 241" with the source named.
- **Germany 2021:** 196 in Germany (section 1, paragraph 2), at least 184 (section 3, paragraph 11), and 135 + 47 + 2 = 184 by state (section 3, paragraph 12), all in one article. Use one and name it.
- **Ahr 2021:** at least 110 deaths in the district of Ahrweiler (section 3, paragraph 13) against 135 in Rhineland-Palatinate, "all of whom were in the district of Ahrweiler" (section 3, paragraph 12). Two sentences in the same article give different counts for the same district. Do not put an Ahr-only death toll on a slide without saying which sentence it is.
- **Storm Boris, Poland:** ten reported dead (section 2, paragraph 8) against nine officially confirmed (section 2, paragraph 14), in one article.
- **Storm Boris, total:** the article says 28 fatalities (section 1, paragraph 2). The country lines stored here (Poland ten or nine, Romania seven, Lower Austria five, Moravian-Silesian Region four in section 2, paragraph 5) are partial and do not cover every affected country. We do not reconcile them. Quote the 28 and name the source.
- **Wikipedia is not an authority.** These are the snapshots our RAG cites. If a number goes on a slide as fact, confirm it against an official source (for example Copernicus EMS, the national statistics offices) first. This repository stores no such official death-toll document.

## Figures from the product, not from documents

- 45 watched sources (26 PEGELONLINE gauges, 11 GloFAS points, 8 Valencia demo points), 25 documents, 1,859 passages and 59 demo-seed memories: from [HANDOVER.md](HANDOVER.md) and the repository.
- Evaluation numbers: [SUBMISSION.md](SUBMISSION.md) and the reports in [evals/](evals/).
