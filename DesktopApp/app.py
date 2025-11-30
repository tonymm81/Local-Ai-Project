import sys
import os
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QTextEdit, QLabel

API_URL = os.getenv("API_URL", "http://127.0.0.1:5001/admin/reset")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Reset")
        self.resize(480, 360)
        layout = QVBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("API key")
        self.btn = QPushButton("Run reset")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(QLabel("API key"))
        layout.addWidget(self.key_input)
        layout.addWidget(self.btn)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log)
        self.setLayout(layout)
        self.btn.clicked.connect(self.run_reset)

    def run_reset(self):
        key = self.key_input.text().strip()
        try:
            r = requests.post(API_URL, headers={"x-api-key": key}, timeout=10)
            self.log.append(f"Status: {r.status_code}  Body: {r.text}")
        except Exception as e:
            self.log.append(f"Error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
