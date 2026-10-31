#!/usr/bin/env python3
"""MINEVORA desktop services: real Modrinth profile plans + Microsoft device login.

Standalone Qt window and embeddable QDialog. Not a replacement for the main
Minecraft launcher. Backend work runs in QThreads to keep the GUI responsive.
Requires Python 3.12+, PySide6; MSAL only for Microsoft sign-in.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, QWidget
)

from modrinth_plan_installer import PlanError, read_plan, validate_entries, install
from microsoft_minecraft_device_auth import AuthError, authenticate_device_code, public_client_id


class OperationWorker(QThread):
    device_code = Signal(str, str, str)
    account_ready = Signal(object)
    plan_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, operation: str, *, plan="", instance="", world="", apply=False, client_id="", parent=None):
        super().__init__(parent)
        self.operation = operation
        self.plan = plan
        self.instance = instance
        self.world = world
        self.apply = apply
        self.client_id = client_id

    def run(self):
        try:
            if self.operation == "login":
                account = authenticate_device_code(
                    self.client_id,
                    lambda uri, code, message: self.device_code.emit(uri, code, message)
                )
                self.account_ready.emit(account)
            elif self.operation == "addons":
                plan = read_plan(self.plan)
                resolved = validate_entries(plan)
                result = install(plan, resolved, self.instance, self.world or None, self.apply)
                safe_result = {
                    "profil": plan["name"],
                    "wersja": plan["minecraftVersion"],
                    "loader": plan["loader"],
                    "operacje": result,
                    "pliki_zapisane": self.apply
                }
                self.plan_ready.emit(json.dumps(safe_result, ensure_ascii=False, indent=2))
            else:
                self.failed.emit("Nieobsługiwana operacja.")
        except (PlanError, AuthError) as exc:
            self.failed.emit(str(exc))
        except Exception:
            # Never print exception arguments from auth libraries, which may contain tokens.
            self.failed.emit("Operacja nie powiodła się. Sprawdź ustawienia i połączenie sieciowe.")


class MinevoraServicesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MINEVORA — Konto i dodatki")
        self.setMinimumSize(680, 510)
        self._worker = None
        self._account = None  # in-memory only, never persisted or logged
        self._verification_url = None
        self._user_code = None

        self.setStyleSheet("""
        QDialog { background:#131124;color:#f1e8ff;font:13px 'Segoe UI'; }
        QGroupBox { border:1px solid #735299;border-radius:12px;
                    margin-top:14px;padding:16px 12px 12px;font-weight:600; }
        QGroupBox::title { subcontrol-origin:margin;left:12px;padding:0 7px; }
        QLabel { color:#dccde9; }
        QLineEdit,QTextEdit { background:#211b32;color:#fff;
             border:1px solid #675080;border-radius:8px;padding:8px; }
        QPushButton { background:#563783;border:1px solid #9e78cb;color:#fff;
             border-radius:8px;padding:9px 13px;font-weight:600; }
        QPushButton:hover:!disabled { background:#6a48a1; }
        QPushButton:disabled { color:#aaa; }
        """)

        layout = QVBoxLayout(self)
        title = QLabel("MINEVORA · konto Microsoft i dodatki Modrinth")
        title.setStyleSheet("font-size:19px;font-weight:700;color:#fff")
        layout.addWidget(title)
        layout.addWidget(QLabel("To osobne narzędzie integracyjne. Nie uruchamia ani nie instaluje samego Minecrafta."))

        account_group = QGroupBox("Konto Microsoft / Minecraft Java")
        acct = QVBoxLayout(account_group)
        self.auth_status = QLabel("Niepołączono. Wymagany jest identyfikator zarejestrowanej aplikacji MINEVORA_MS_CLIENT_ID.")
        self.auth_status.setWordWrap(True)
        acct.addWidget(self.auth_status)
        buttons = QHBoxLayout()
        self.login_btn = QPushButton("Zaloguj przez Microsoft")
        self.open_link_btn = QPushButton("Otwórz oficjalną stronę logowania")
        self.open_link_btn.setEnabled(False)
        self.copy_code_btn = QPushButton("Kopiuj kod")
        self.copy_code_btn.setEnabled(False)
        buttons.addWidget(self.login_btn)
        buttons.addWidget(self.open_link_btn)
        buttons.addWidget(self.copy_code_btn)
        acct.addLayout(buttons)
        self.code_label = QLabel("")
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code_label.setStyleSheet("font-size:18px;font-weight:700;color:#d4b4ff")
        acct.addWidget(self.code_label)
        layout.addWidget(account_group)

        group = QGroupBox("Dodatki Modrinth — plan JSON")
        form = QFormLayout(group)
        self.plan_edit = QLineEdit()
        self.instance_edit = QLineEdit()
        self.world_edit = QLineEdit()
        self.plan_edit.setPlaceholderText("Plik planu wyeksportowanego w podglądzie MINEVORA")
        self.instance_edit.setPlaceholderText("Katalog istniejącej instalacji/profilu Minecraft")
        self.world_edit.setPlaceholderText("Opcjonalne: folder konkretnego świata (dla datapacków)")
        form.addRow("Plan JSON:", self._file_row(self.plan_edit, self.choose_plan))
        form.addRow("Instancja:", self._file_row(self.instance_edit, self.choose_instance))
        form.addRow("Świat:", self._file_row(self.world_edit, self.choose_world))
        self.acknowledge = QCheckBox("Rozumiem, że instalacja pobierze pliki do wskazanej instancji.")
        form.addRow(self.acknowledge)
        buttons = QHBoxLayout()
        self.check_btn = QPushButton("Sprawdź plan (bez zmian)")
        self.apply_btn = QPushButton("Instaluj zweryfikowane dodatki")
        buttons.addWidget(self.check_btn)
        buttons.addWidget(self.apply_btn)
        form.addRow(buttons)
        layout.addWidget(group)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(95)
        self.output.setPlaceholderText("Wyniki weryfikacji zostaną wyświetlone tutaj. Tokeny Microsoft nie są zapisywane.")
        layout.addWidget(self.output)

        self.login_btn.clicked.connect(self.start_login)
        self.open_link_btn.clicked.connect(self.open_login_page)
        self.copy_code_btn.clicked.connect(self.copy_code)
        self.check_btn.clicked.connect(lambda: self.start_install(False))
        self.apply_btn.clicked.connect(lambda: self.start_install(True))

    @staticmethod
    def _file_row(field, callback):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        choose = QPushButton("Wybierz…")
        choose.clicked.connect(callback)
        lay.addWidget(field)
        lay.addWidget(choose)
        return row

    def choose_plan(self):
        value, _ = QFileDialog.getOpenFileName(self, "Plan MINEVORA", "", "JSON (*.json)")
        if value:
            self.plan_edit.setText(value)

    def choose_instance(self):
        value = QFileDialog.getExistingDirectory(self, "Wybierz istniejącą instancję Minecraft")
        if value:
            self.instance_edit.setText(value)

    def choose_world(self):
        value = QFileDialog.getExistingDirectory(self, "Wybierz katalog świata Minecraft")
        if value:
            self.world_edit.setText(value)

    def _start(self, worker):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "MINEVORA", "Operacja już trwa.")
            return False
        self._worker = worker
        self.login_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_finished)
        worker.start()
        return True

    def _on_failed(self, text):
        self.output.append("Błąd: " + text)
        self.auth_status.setText("Nie udało się zakończyć logowania lub operacji.") if self._worker.operation == "login" else None

    def _on_finished(self):
        self.login_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)

    def start_login(self):
        try:
            client_id = public_client_id()
        except AuthError as exc:
            QMessageBox.warning(self, "Konfiguracja Microsoft", str(exc))
            return
        worker = OperationWorker("login", client_id=client_id, parent=self)
        worker.device_code.connect(self._on_device_code)
        worker.account_ready.connect(self._on_account)
        if self._start(worker):
            self.auth_status.setText("Trwa bezpieczne logowanie Microsoft — bez ręcznego adresu localhost.")

    def _on_device_code(self, uri, code, message):
        self._verification_url = uri
        self._user_code = code
        self.code_label.setText("Kod Microsoft: " + code)
        self.auth_status.setText("Otwórz oficjalną stronę Microsoft i wpisz powyższy kod. Hasła podajesz tylko Microsoft.")
        self.open_link_btn.setEnabled(True)
        self.copy_code_btn.setEnabled(True)

    def _on_account(self, account):
        self._account = account
        self._user_code = None
        self.code_label.clear()
        self.copy_code_btn.setEnabled(False)
        self.open_link_btn.setEnabled(False)
        self.auth_status.setText("Zweryfikowano konto Minecraft Java: " + account.username)
        self.output.append("Zalogowano do Minecraft Java jako: " + account.username)

    def open_login_page(self):
        if self._verification_url in ("https://microsoft.com/devicelogin", "https://www.microsoft.com/devicelogin"):
            QDesktopServices.openUrl(QUrl(self._verification_url))

    def copy_code(self):
        if self._user_code:
            QApplication.clipboard().setText(self._user_code)

    def start_install(self, apply):
        plan, instance, world = (
            self.plan_edit.text().strip(),
            self.instance_edit.text().strip(),
            self.world_edit.text().strip()
        )
        if not plan or not Path(plan).is_file() or not instance or not Path(instance).is_dir():
            QMessageBox.warning(self, "Plan Modrinth", "Wybierz istniejący plik JSON i katalog instancji Minecraft.")
            return
        if apply:
            if not self.acknowledge.isChecked():
                QMessageBox.warning(self, "Instalacja", "Zaznacz potwierdzenie instalacji.")
                return
            confirmation = QMessageBox.question(
                self, "MINEVORA — instalacja",
                "Zainstalować zweryfikowane dodatki w:\n" + instance +
                "\n\nInstalator nie pobiera brakujących zależności ani samego Minecrafta."
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
        worker = OperationWorker(
            "addons", plan=plan, instance=instance, world=world,
            apply=apply, parent=self
        )
        worker.plan_ready.connect(self._on_plan)
        if self._start(worker):
            self.output.append("Weryfikuję plan Modrinth…")

    def _on_plan(self, text):
        self.output.setPlainText(text)

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "MINEVORA", "Operacja nadal trwa. Zamknij okno po zakończeniu weryfikacji lub logowania."
            )
            event.ignore()
            return
        # Explicitly discard tokens on close; no disk cache.
        self._account = None
        event.accept()


def show_services(parent=None):
    """Open from another PySide6 launcher QWidget and return the QDialog."""
    window = MinevoraServicesWindow(parent)
    window.show()
    return window


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    win = MinevoraServicesWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
