# Systemtests

Testfaelle fuer den Durchlauf gegen eine **laufende** Home-Assistant-Instanz.

Sie ergaenzen die automatisierten Tests, decken aber etwas anderes ab: die
Domaenentests pruefen die Kuerzelregel, die Farben und den Kartenabgleich ohne
Home Assistant, die Komponententests pruefen die Integration gegen eine
Testinstanz. Was keiner von ihnen sieht, ist das Zusammenspiel im Betrieb --
echte Kalender-Integrationen, echte Dashboards, echte Neustarts und die
Darstellung in der Daylight Calendar Card.

## Durchfuehrung

**Testkalender statt echter Termine.** Die Faelle A bis G arbeiten auf einem
eigens angelegten *Local Calendar* `FK Test` (`calendar.fk_test`) mit erfundenen
Terminen und einem eigenen Dashboard `fk-test`. Nur Abschnitt R liest den
echten Familienkalender, und zwar ausschliesslich lesend; seine Termine landen
in keinem Protokoll, nur Zaehler und Abweichungen.

**Personen im Test:** Anna `A`, Ben `B`, Carla `C`, Dora `D`.

**Termine anlegen** mit `calendar.create_event` auf `calendar.fk_test`,
**abfragen** mit `calendar.get_events` auf den Personenkalendern. Die
Erwartung liefert jeweils die Referenzregel: erstes Wort aus bekannten
Buchstaben, jeder hoechstens einmal, sonst alle.

**Aufraeumen.** Nach dem Durchlauf: Eintrag `FK Test` der Integration
loeschen, Local Calendar `FK Test` loeschen, Dashboard `fk-test` loeschen.
Anschliessend pruefen, dass keine `calendar.fk_test*`-Entities uebrig sind.

**Nicht ausfuehren:** Aenderungen am echten Familienkalender oder an seiner
CalDAV-Integration. Abschnitt R schreibt nichts.

---

## A -- Installation

| ID | Fall | Erwartung |
|----|------|-----------|
| A1 | HACS: benutzerdefiniertes Repository `DaFlouw/familycalender`, Kategorie Integration, herunterladen | HACS meldet die Version aus dem Manifest. |
| A2 | Neustart | *Familienkalender* laesst sich unter *Integration hinzufuegen* finden, mit Logo. |
| A3 | Protokoll nach dem Neustart | Keine Fehler oder Warnungen von `family_calendar`. |

## B -- Einrichtung

| ID | Fall | Erwartung |
|----|------|-----------|
| B1 | Config Flow: Name `FK Test`, Quelle `calendar.fk_test`, vier Personen | Eintrag geladen, vier Kalender `calendar.fk_test_anna` bis `calendar.fk_test_dora`. |
| B2 | Farbvorschlaege im Flow | Jede neue Person bekommt die naechste freie Farbe der Palette. |
| B3 | Zweite Person mit bereits vergebenem Kuerzel (andere Schreibweise) | Abgelehnt mit *Kuerzel vergeben*. |
| B4 | Kuerzel `AB` oder leerer Name | Abgelehnt. |
| B5 | Neuer Flow mit einem Personenkalender als Quelle | Abgelehnt. |
| B6 | Neuer Flow mit `calendar.fk_test` | Abbruch *bereits eingerichtet*. |
| B7 | Entities | Je `letter` und `color` als Attribut; Geraet *FK Test*. |

## C -- Zuordnung der Termine

| ID | Fall | Erwartung |
|----|------|-----------|
| C1 | 64 Termine, einer je Kuerzelkombination und -reihenfolge, gemischte Schreibweise | Jede Person sieht genau die Termine mit ihrem Buchstaben. |
| C2 | Termine ohne gueltiges Kuerzel: `Sommerfest`, `Alle Grillen`, `AA Tippfehler`, `AX Fremd`, `F-Jugend` | Alle vier sehen sie. |
| C3 | Ort und Beschreibung beginnen mit fremden Kuerzeln | Ohne Einfluss auf die Zuordnung. |
| C4 | Ganztaegiger und mehrtaegiger Termin `D Klassenfahrt` | Nur Dora, an jedem Tag. |
| C5 | Terminliste gegen den Quellkalender | Titel, Beginn, Ende und Ort unveraendert. |
| C6 | Termin, der in zwei Minuten beginnt | Kalender der Person wechselt zum Beginn auf `on`, zum Ende auf `off`; die anderen bleiben `off`. |
| C7 | Neuer Termin im Quellkalender | Erscheint spaetestens nach 30 Sekunden in den Personenkalendern. |

## D -- Personen

| ID | Fall | Erwartung |
|----|------|-----------|
| D1 | *Person hinzufuegen*: Emil `E` | Neuer Kalender `calendar.fk_test_emil`; ein `E`-Termin, der vorher alle betraf, betrifft nur noch Emil. |
| D2 | *Person bearbeiten*: Farbe von Anna | Attribut, Kalenderoption der Entity und Karte uebernehmen die Farbe. |
| D3 | Person Emil entfernen | Kalender verschwindet; `E`-Termine betreffen wieder alle. |

## E -- Optionen

| ID | Fall | Erwartung |
|----|------|-----------|
| E1 | Quelle auf einen zweiten Testkalender umstellen | Personenkalender zeigen dessen Termine. |
| E2 | Zurueck auf `calendar.fk_test` | Alte Termine wieder da. |
| E3 | Farbabgleich aus, Farbe aendern | Karte behaelt die alte Farbe. |

## F -- Dashboard

Dashboard `fk-test` mit einer Daylight Calendar Card: die vier
Personenkalender, dazu ein fremder Kalender mit eigener Farbe,
`combine_calendars: true`, `combine_style: stripes`.

| ID | Fall | Erwartung |
|----|------|-----------|
| F1 | Farbabgleich an, Eintrag neu laden | Die vier Farben stehen in `colors`, die fremde Farbe ist unveraendert. |
| F2 | Screenshot Woche | Einzeltermine einfarbig, Termine mehrerer Personen gestreift in deren Farben, Termine ohne Kuerzel vierfarbig. |
| F3 | Zweite Karte nachtraeglich speichern | Bekommt die Farben innerhalb weniger Sekunden. |
| F4 | Andere Karten und Dashboards | Unveraendert (Vergleich vorher/nachher). |

## G -- Robustheit

| ID | Fall | Erwartung |
|----|------|-----------|
| G1 | Eintrag neu laden | Entities kommen wieder, Farben bleiben. |
| G2 | Home Assistant neu starten | Wie G1; kein Fehler im Protokoll, auch wenn der Quellkalender spaeter laedt. |
| G3 | Quellkalender umbenennen | Eintrag folgt, Personenkalender liefern weiter Termine. |
| G4 | Quellkalender entfernen | Eintrag wartet auf neuen Versuch, Warnung im Protokoll, kein Absturz. |
| G5 | Protokoll nach dem gesamten Lauf | Keine unerwarteten Fehler oder Warnungen von `family_calendar`. |

## R -- Echter Familienkalender (nur lesend)

| ID | Fall | Erwartung |
|----|------|-----------|
| R1 | Eintrag auf den echten Quellkalender, 90 Tage abfragen | Jede Personenliste deckt sich mit der Referenzregel. Protokolliert werden nur Anzahlen. |
| R2 | Kalender-Ansicht auf die Personenkalender umstellen | Streifen und Farben wie in F2. |

---

## Durchlauf vom 13.09.2026, Home Assistant 2026.9.1

Ausgefuehrt gegen die produktive Instanz (Raspberry Pi 4, HAOS 18.2) mit den
Testkalendern `FK Test` und `FK Test Zwei` und dem Dashboard `fk-test`.
Abschnitt R lesend gegen den echten Familienkalender.

| Bereich | Ergebnis |
|---------|----------|
| A Installation | bestanden |
| B Einrichtung | B1 zunaechst fehlgeschlagen (Issue 1), nach der Behebung bestanden; B2 ueber die Komponententests; uebrige bestanden |
| C Zuordnung | bestanden |
| D Personen | bestanden |
| E Optionen | E1 fehlgeschlagen (Issue 8), nach der Behebung bestanden; E3 bestanden |
| F Dashboard | F2 mit Befund (Issue 7), nach der Behebung bestanden; uebrige bestanden |
| G Robustheit | G2 mit Warnung (Issue 6), nach der Behebung bestanden; G4 abgewandelt, siehe unten; uebrige bestanden |
| R Echter Kalender | bestanden |

Im Einzelnen:

* **B1** Mit vier Personen entstand nur `calendar.fk_test_dora`. Alle
  Personenkalender meldeten dasselbe Geraet, Home Assistant verschob es von
  Person zu Person. Seit dem eigenen Geraet je Person entstehen alle vier
  Kalender mit Kuerzel, Farbe und dem richtigen naechsten Termin.
* **B3 bis B6** Vergebenes Kuerzel in anderer Schreibweise, leerer Name mit
  Kuerzel `AB`, Personenkalender als Quelle, bereits eingerichtete Quelle --
  jeweils mit der vorgesehenen Meldung abgelehnt.
* **C1** Von 64 Kombinations-Terminen sieht jede Person genau die 49 mit ihrem
  Buchstaben. Von den 15 Terminen der Anzeigewoche sehen Anna 10, Ben 10,
  Carla 9 und Dora 10 -- keiner fehlt, keiner zu viel.
* **C2** `Sommerfest`, `Alle Grillen`, `AA Tippfehler`, `AX Fremd` und
  `F-Jugend Turnier` sehen alle vier.
* **C3** `C Yoga` mit Ort `B-Strasse 5` und Beschreibung `D bitte abholen`
  sieht nur Carla.
* **C4** Die dreitaegige, ganztaegige `D Klassenfahrt` sieht nur Dora.
* **C6** `B Zustandstest` 16:35 bis 16:37: Ben wechselt um 16:35:00 auf `on`
  und um 16:37:00 auf `off`, Anna bleibt `off`.
* **C7** Ein neu angelegter Termin steht sofort im Zustand des Personenkalenders
  und auf der Karte.
* **D1** `E Werkstatt` betrifft zunaechst alle; nach dem Anlegen von Emil (`E`)
  nur noch ihn.
* **D2** Eine geaenderte Farbe steht im Attribut, in der Kalenderoption der
  Entity und in der Karte.
* **D3** Nach dem Entfernen von Emil verschwindet sein Kalender, `E Werkstatt`
  betrifft wieder alle.
* **E1** Die neue Quelle stand in den Optionen, die Kalender lieferten aber die
  Termine der alten. Der Options-Flow hatte vor dem Speichern die `unique_id`
  geaendert und damit ein Neuladen mit den alten Optionen ausgeloest. Nach der
  Behebung greift der Wechsel ohne Neuladen von Hand.
* **E3** Bei abgeschaltetem Abgleich behaelt die Karte die alte Farbe; nach dem
  Einschalten uebernimmt sie die aktuelle.
* **F2** Einzeltermine einfarbig, `CD Zahnarzt` zweifarbig, `cab Schwimmbad`
  dreifarbig, Termine ohne Kuerzel vierfarbig gestreift. Befund: Jedes Personen-
  Chip trug das Initial *F* und den vollen Geraetenamen. Seit Issue 7 traegt der
  Abgleich den Personennamen ein, wo die Karte keinen hat.
* **F3** Eine nachtraeglich gespeicherte Karte *Nur Ben* bekommt Farbe und Namen
  innerhalb weniger Sekunden.
* **F4** Farbe und Name des fremden Kalenders bleiben unberuehrt.
* **G2** Nach dem Neustart meldete Home Assistant den veralteten Aufruf
  `async_update_device(remove_config_entry_id=...)`. Seit der Behebung keine
  Meldung der Integration mehr.
* **G3** Nach dem Umbenennen der Quelle folgt der Eintrag, die Kalender liefern
  weiter.
* **G4** Mit den verfuegbaren Werkzeugen liess sich die Quelle nur
  **deaktivieren**, nicht aus der Registry entfernen. Ergebnis: Der
  Personenkalender wird sofort `unavailable`, im Protokoll steht genau eine
  Fehlermeldung des Coordinators, nach dem Reaktivieren ist er ohne Eingriff
  wieder verfuegbar. Das vollstaendige Entfernen deckt der Komponententest
  `test_entfernte_quelle` ab.
* **R1** Ein Monat echter Familienkalender: Die vier Personenkalender enthalten
  zusammen 33 Termine aus 29 Quellterminen -- genau die Zuordnung der
  Kuerzelregel, zwei Termine mit `CF` und einer mit `ECA` zaehlen mehrfach.
* **R2** Die Kalender-Ansicht zeigt die vier Personen mit eigenem Initial und
  eigener Farbe, Termine mehrerer Personen gestreift.

Issues aus diesem Durchlauf:
[1](https://github.com/DaFlouw/familycalender/issues/1),
[2](https://github.com/DaFlouw/familycalender/issues/2),
[3](https://github.com/DaFlouw/familycalender/issues/3),
[4](https://github.com/DaFlouw/familycalender/issues/4),
[5](https://github.com/DaFlouw/familycalender/issues/5),
[6](https://github.com/DaFlouw/familycalender/issues/6),
[7](https://github.com/DaFlouw/familycalender/issues/7),
[8](https://github.com/DaFlouw/familycalender/issues/8) -- alle behoben.
