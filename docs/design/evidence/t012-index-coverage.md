# T-012 browser indexed coverage

- Tested source SHA: `16a79efff36afc0b690197bc4a55bd568d2e9676`
- Command: `just test-e2e-local`
- Fixture: pinned M1 + disposable PostgreSQL + isolated NATS/JetStream + real FastAPI/React/Chromium
- Viewports: 1330x900, 390x844, and Chromium page scale 200%

| Case | Projects | Runtime titles | Result |
| --- | --- | --- | --- |
| `E2E-M12-FILES` | desktop, mobile | UI-M10-PNG UI-M10-PARITY E2E-M12-FILES actual CSV parsing, PNG decoding, and bounded private actions<br>UI-M11-PDF E2E-M12-FILES real download is bounded, safe, and text-readable | PASS |
| `E2E-M12-INDEX` | desktop, mobile | E2E-M12-PATH E2E-M12-INDEX private queue journey preserves authorization, cache clearing, and a clean browser console | PASS |
| `E2E-M12-MAP` | desktop, mobile | UI-M8-MAP E2E-M12-MAP deterministic WebGL failure keeps API list fallback usable<br>UI-M8-MAP E2E-M12-MAP deterministic style failure keeps API list fallback usable<br>UI-M8-MAP E2E-M12-MAP exact API marker/list identity, attribution, and live style response | PASS |
| `E2E-M12-PATH` | desktop, mobile | E2E-M12-PATH E2E-M12-INDEX private queue journey preserves authorization, cache clearing, and a clean browser console<br>IDB-M7-PREF UI-M7-PARITY E2E-M12-PATH public list, detail, back, deep-link and reload<br>SEC-M9-CACHE IDB-M9-ISOLATE E2E-M12-PATH sign out clears all private IndexedDB rows and restores public<br>UI-M12-ALL E2E-M12-PATH API outage has a useful retry and recovers without stale data<br>UT-M9-SESSIONS E2E-M12-PATH principal B is denied principal A Plant by the actual API (404)<br>UT-M9-SESSIONS UI-M12-ALL E2E-M12-PATH expired session triggers 401 and returns to public with Session expired<br>UT-M9-SESSIONS UI-M9-PARITY E2E-M12-PATH invited principal sees only assigned Plants via the real API | PASS |
| `IDB-M7-PREF` | desktop, mobile | IDB-M7-PREF UI-M7-PARITY E2E-M12-PATH public list, detail, back, deep-link and reload | PASS |
| `IDB-M9-ISOLATE` | desktop, mobile | SEC-M9-CACHE IDB-M9-ISOLATE E2E-M12-PATH sign out clears all private IndexedDB rows and restores public | PASS |
| `SEC-M10-EXPORT` | desktop, mobile | SEC-M10-EXPORT logout removes private export actions and cannot reuse stale chart | PASS |
| `SEC-M9-CACHE` | desktop, mobile | SEC-M9-CACHE IDB-M9-ISOLATE E2E-M12-PATH sign out clears all private IndexedDB rows and restores public | PASS |
| `UI-M10-PARITY` | desktop, mobile | UI-M10-PNG UI-M10-PARITY E2E-M12-FILES actual CSV parsing, PNG decoding, and bounded private actions | PASS |
| `UI-M10-PNG` | desktop, mobile | UI-M10-PNG UI-M10-PARITY E2E-M12-FILES actual CSV parsing, PNG decoding, and bounded private actions | PASS |
| `UI-M11-PDF` | desktop, mobile | UI-M11-PDF E2E-M12-FILES real download is bounded, safe, and text-readable | PASS |
| `UI-M12-ALL` | desktop, mobile | UI-M12-ALL E2E-M12-PATH API outage has a useful retry and recovers without stale data<br>UI-M8-PARITY UI-M12-ALL desktop and mobile expose four chart channels, units, 24-72-168 controls, keyboard focus, and 200% scale<br>UT-M9-SESSIONS UI-M12-ALL E2E-M12-PATH expired session triggers 401 and returns to public with Session expired | PASS |
| `UI-M7-PARITY` | desktop, mobile | IDB-M7-PREF UI-M7-PARITY E2E-M12-PATH public list, detail, back, deep-link and reload | PASS |
| `UI-M8-MAP` | desktop, mobile | UI-M8-MAP E2E-M12-MAP deterministic WebGL failure keeps API list fallback usable<br>UI-M8-MAP E2E-M12-MAP deterministic style failure keeps API list fallback usable<br>UI-M8-MAP E2E-M12-MAP exact API marker/list identity, attribution, and live style response<br>UI-M8-MAP keyboard marker activation opens its API Plant | PASS |
| `UI-M8-PARITY` | desktop, mobile | UI-M8-PARITY UI-M12-ALL desktop and mobile expose four chart channels, units, 24-72-168 controls, keyboard focus, and 200% scale | PASS |
| `UI-M9-PARITY` | desktop, mobile | UI-M9-PARITY signed-out anonymous mode shows Sign in and no open-signup CTA<br>UT-M9-FORECAST UI-M9-PARITY real API shows 12 forecast targets and an observed→predicted boundary<br>UT-M9-SESSIONS UI-M9-PARITY E2E-M12-PATH invited principal sees only assigned Plants via the real API | PASS |
| `UT-M9-FORECAST` | desktop, mobile | UT-M9-FORECAST UI-M9-PARITY real API shows 12 forecast targets and an observed→predicted boundary | PASS |
| `UT-M9-SESSIONS` | desktop, mobile | UT-M9-SESSIONS E2E-M12-PATH principal B is denied principal A Plant by the actual API (404)<br>UT-M9-SESSIONS UI-M12-ALL E2E-M12-PATH expired session triggers 401 and returns to public with Session expired<br>UT-M9-SESSIONS UI-M9-PARITY E2E-M12-PATH invited principal sees only assigned Plants via the real API<br>UT-M9-SESSIONS zero-Plant principal sees No plants assigned | PASS |
