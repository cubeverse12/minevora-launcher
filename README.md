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
