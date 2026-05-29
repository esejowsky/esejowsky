# Vault reorg — 2026-05-29

Rekord porządkowania i optymalizacji vaulta Obsidian pod agentów AI. Substancja zmian jest w
samym vaulcie (`/vault`, edytowanym na żywo przez filesystem MCP — nie jest częścią tego repo);
ten plik to czytelny ślad wykonanych prac.

## Cel
Vault stał się „burgerem" — rozjazd między udokumentowaną strukturą (PARA + Zettelkasten) a stanem
faktycznym oraz duplikacja instrukcji. Bałagan regenerował się (cron pisał daily-notes do złej
ścieżki bez frontmatter). Cel: porządek, maksymalna efektywność dla agentów AI, zapis z tematami
(nie samą datą), jedno źródło prawdy, anty-regeneracja.

## Wykonane

### Struktura / śmieci
- Usunięto z roota (→ `.trash/cleanup-2026-05-29/`): pusty `2026-05-26.md` + 4 puste `Bez nazwy*.canvas`.
- `Architektura-Serwera-2026.md` → `03-ZASOBY/31-technologia/` (+ frontmatter).
- `TODO-MCP.md` (DONE) → `40-ARCHIWUM/tasks-done/`.

### Dzienniki
- Zlikwidowano regenerujący się stray `50-dziennik/` (cały → kosz).
- Unikalny `2026-05-17` odtworzony w `05-DZIENNIK/` z `tematy`; `2026-W21-trakt-weekly` zachowany
  (inny tydzień niż W20). Dni 18–23 to były chude duplikaty — odrzucone.

### Archiwum — pełny porządek
- `40-ARCHIWUM/projekty/`: z 71 plików na płask → **11 realnych projektów**.
- ~37 osób → `40-ARCHIWUM/osoby/`; ~23 firm/marek/usług/grup → nowy `40-ARCHIWUM/firmy/`.
- Naprawiono przykładowe patologiczne aliasy + zdublowany frontmatter.

### Jedno źródło prawdy dla AI
- `_meta/VAULT-CONVENTIONS.md` — struktura, nazewnictwo, tagi, YAML.
- `_meta/iris-vault-protocol.md` — protokół I/O: **GDZIE SZUKAĆ** (mapa czytania) + **GDZIE ZAPISAĆ**.
- `00-CORE/AGENTS.md` — reguły agenta + blok „JAK czytać i zapisywać" + integralność linków.
- `00-CORE/BOOTSTRAP.md` — jedyna sekwencja startowa.
- Usunięto zdublowane reguły (tabela struktury ×3, „kiedy sprawdzać vault" ×3, sekwencja ×4);
  reszta plików linkuje. `IRIS-startup-prompt` odchudzony.

### Zapis z tematami
- Pole `tematy:` + nagłówek `# data — tematy` w konwencji, szablonie dziennika i auto-save-protocol.
- `05-DZIENNIK/README.md` z auto-indeksem Dataview „data → tematy" + kuratorowane highlights.

### Szablony
- Każdy szablon zawiera gotowy blok `yaml` (koniec plików bez frontmatter).
- Nowe szablony: rozmowa, firma, decyzja, log-iris, tygodniowka.

### Rozszerzenia
- Auto-indeksy Dataview w README (dziennik, ludzie, projekty, iris, decisions).
- Linter `_meta/scripts/vault-lint.py` + dashboard `_meta/vault-health.md`.
- `_meta/SECURITY-REVIEW-2026-05-29.md` — ekspozycja przez publiczny MCP (do decyzji).
- MOC huby: ludzie / projekty / zasoby.

### Anty-regeneracja
- `50-dziennik/`, `30-zasoby/` jawnie ZAKAZANE w AGENTS/BOOTSTRAP/VAULT-CONVENTIONS.
- Linter wyłapuje: pliki w roocie, brak frontmatter, zakazane foldery, aliasy ze ścieżką backupu,
  dziennik bez `tematy`.

## Follow-up (egzekwowane przez linter)
- Backfill `tematy:` do starszych wpisów `05-DZIENNIK/` (07–26).
- Normalizacja frontmatter/aliasów reszty plików z importu 2026-05-08 w `40-ARCHIWUM/`.
- Normalizacja nazw Unicode w `04-LUDZIE/rozmowy/`.
- Decyzje z SECURITY-REVIEW.
