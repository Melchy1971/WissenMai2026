# Prompt 431 – Auth-Full-Suite Selektoren fixen

Fixe die Auth-Gruppe der Frontend Full-Suite.

Problem:
Minimal Slice ist grün, aber Full-Suite Auth-Gruppe scheitert an UI-Selektoren.

Fehler:
- getByTestId("login-page") nicht gefunden
- heading "Anmeldung" nicht gefunden
- heading "Dokumente" nicht stabil gefunden
- ".shell" nicht stabil gefunden

Aufgabe:
1. Ergänze stabile data-testid:
   - login-page
   - login-email
   - login-password
   - login-submit
   - app-shell
   - documents-page
   - document-list
   - auth-error
   - workspace-ready

2. Passe Full-Suite Tests auf data-testid an.
3. Entferne fragile Text-/CSS-Abhängigkeiten.
4. Auth-Gruppe erneut ausführen.

Ziel:
- Auth-Gruppe >= 25/27 grün
- keine Selector-Failures

Output:
- UI-TestID-Fix
- aktualisierte Tests
- neuer frontend_full_suite_staged_report.json
