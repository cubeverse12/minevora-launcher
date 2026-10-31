# MINEVORA Launcher — aktualizacje Windows

Repozytorium dystrybucji nowych paczek MINEVORA Launcher.

Wersja **18.3.3** upraszcza PvP Mod Menu: usuwa trzy zbędne przyciski ręcznej instalacji .jar, przełączania pliku moda i otwierania folderu modów. Pozostaje automatyczny przycisk **POBIERZ I ZAINSTALUJ PVP HUD Z GITHUBA** oraz instalacja do zgodnej wersji Fabric.

Plik ZIP publikowany jest w sekcji **Releases**. Kod źródłowy aplikacji bazowej znajduje się również w paczce ZIP; w repozytorium jest skrypt przygotowujący aktualizację 18.3.3 z publicznej paczki 18.3.2.

Mod w grze można ukryć lub pokazać klawiszem **H**, bez zamykania Minecrafta. Instalacja pliku .jar wymaga zamknięcia gry.


## Modrinth — weryfikowany instalator planów profili (moduł rozwojowy)

Źródło: `tools/modrinth_plan_installer.py`.

- Przyjmuje wyeksportowany z podglądu MINEVORA plan JSON z identyfikatorami konkretnych wydań dodatków Modrinth.
- Sprawdza zgodność wersji Minecraft i loadera, wymagane zależności i sumę SHA-512 pobranych plików.
- Mody `.jar`, shadery/resource packi `.zip` i datapacki `.zip`; dla datapacków konieczne jest wskazanie konkretnego świata.
- Domyślnie działa jako **dry run**; dopiero `--apply` pobiera pliki do wskazanej istniejącej instancji.
- Nie nadpisuje istniejących zmienionych plików. Odmawia instalacji, jeżeli brakuje wymaganych zależności.
- Nie instaluje Minecrafta, loaderów ani pełnych modpacków `.mrpack`. Nie jest jeszcze połączony z przyciskiem GUI launchera Windows.

Przykładowe sprawdzenie bez instalacji:

```powershell
python tools/modrinth_plan_installer.py --plan minevora-plan.json --instance "C:\Minecraft\MojaInstancja"
```

Po zweryfikowaniu planu i wybranej instancji można świadomie dodać `--apply`.

Testy offline: `python -m unittest discover -s tests -p 'test_modrinth_plan_installer.py' -v`.

Potwierdzony udany workflow GitHub Actions: https://github.com/cubeverse12/minevora-launcher/actions/runs/41242441149.

To nadal komponent rozwojowy — testy integracji z GUI i uruchomienia Minecrafta na Windows są do wykonania.


## MINEVORA 18.3.8 SERVICES — eksperymentalna integracja Qt

Pierwsza paczka rozwojowa z **widoczną akcją menu „Konto Microsoft i dodatki…”**, skrótem **Ctrl+M** i osobnym oknem PySide6. Nie jest to jeszcze stabilna aktualizacja aplikacji ani nowy instalator EXE.

**Wynik GitHub Actions:** https://github.com/cubeverse12/minevora-launcher/actions/runs/41243357172

Archiwum znajduje się w sekcji **Artifacts** powyższego uruchomienia pod nazwą `MINEVORA-18.3.8-SERVICES-EXPERIMENTAL`. GitHub wymaga zalogowania do pobrania artefaktów; dostępność jest ograniczona retencją.

Źródła:
- `tools/minevora_services_window.py` — okno profili Modrinth i logowania Microsoft.
- `tools/microsoft_minecraft_device_auth.py` — logowanie **device code** (bez ręcznego `http://localhost/...`), wymiana tokenów Xbox/XSTS/Minecraft i weryfikacja praw do gry; sesja tylko w pamięci.
- `tools/modrinth_plan_installer.py` — weryfikowany instalator wybranych dodatków do istniejących instancji.
- `tools/build_services_18_3_8.py` — budowanie rozszerzonej paczki na podstawie zweryfikowanego wydania 18.3.7. Nie nadpisuje starszego wydania.

### Microsoft — co musi być skonfigurowane

**Wymagany jest własny identyfikator public-client aplikacji Microsoft (`MINEVORA_MS_CLIENT_ID`) obsługującej konta osobiste** i uprawnienia `XboxLive.signin` / usług Minecraft. Bez prawidłowej rejestracji i wymaganej zgody Microsoft/Minecraft logowanie do gry nie będzie działało. Nie ma tu żadnego hasła ani `client_secret` do wpisania w launcher.

Po uruchomieniu okna kliknięcie „Zaloguj przez Microsoft” wyświetla oficjalny adres Microsoft i jednorazowy kod. Po logowaniu program musi otrzymać potwierdzone uprawnienia Minecraft Java i profil gracza; bez nich nie przedstawia konta jako gotowego do gry. Kod urządzenia nie omija zabezpieczeń konta ani wymagań rodzinnych.

**Ograniczenia:** nie potwierdzono logowania na rzeczywistym koncie Microsoft, uprawnień app registration, uruchomienia gry w Windows ani pobierania modów z internetu w GUI. Wykonane testy to testy offline oraz kompilacja, analiza struktury i budowanie ZIP w CI.
