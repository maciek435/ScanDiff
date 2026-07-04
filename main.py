import sys
import mss
from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QLineEdit
)
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"A:\Programy\TesseractOCR\tesseract.exe"

class ScreenSelector(QWidget):
    selection_made = pyqtSignal(QPoint, QPoint)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowOpacity(0.3)
        self.showFullScreen()

        self.start_point = None
        self.end_point = None

    def mousePressEvent(self, event):
        self.start_point = event.pos()

    def mouseReleaseEvent(self, event):
        self.end_point = event.pos()
        self.selection_made.emit(self.start_point, self.end_point)
        self.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanDiff")
        self.resize(900, 500)

        main_layout = QVBoxLayout(self)

        self.scan_timer = QTimer(self)
        self.scan_timer.setSingleShot(True)
        self.scan_timer.timeout.connect(self.add_scanned_code)


        # --- górny pasek: przycisk czyszczenia ---
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.btn_clear = QPushButton("Wyczyść")
        self.btn_clear.clicked.connect(self.clear_all)
        top_bar.addWidget(self.btn_clear)
        main_layout.addLayout(top_bar)

        # --- trzy kolumny obok siebie ---
        columns_layout = QHBoxLayout()

        # Kolumna 1: dane z ekranu (OCR)
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Dane z ekranu (OCR)"))
        self.list_ocr = QListWidget()
        self.btn_clear_ocr = QPushButton("Wyczyść kolumnę")
        self.btn_clear_ocr.clicked.connect(self.list_ocr.clear)
        col1.addWidget(self.btn_clear_ocr)
        col1.addWidget(self.list_ocr)
        self.btn_add_data = QPushButton("Dodaj dane")
        self.btn_add_data.clicked.connect(self.add_data_from_screen)
        col1.addWidget(self.btn_add_data)
        columns_layout.addLayout(col1)

        # Kolumna 2: dane ze skanera
        self.list_scanner = QListWidget()
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Dane ze skanera"))
        self.btn_clear_scanner = QPushButton("Wyczyść kolumnę")
        self.btn_clear_scanner.clicked.connect(self.clear_scanner_column)
        col2.addWidget(self.btn_clear_scanner)
        col2.addWidget(self.list_scanner)
        self.scanner_input = QLineEdit()
        self.scanner_input.setPlaceholderText("Zeskanuj kod tutaj (Enter)")
        self.scanner_input.returnPressed.connect(self.add_scanned_code)
        self.scanner_input.textChanged.connect(self.reset_scan_timer)
        col2.addWidget(self.scanner_input)
        columns_layout.addLayout(col2)

        # Kolumna 3: wynik porównania
        self.list_result = QListWidget()
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Wynik porównania"))
        self.btn_clear_result = QPushButton("Wyczyść kolumnę")
        self.btn_clear_result.clicked.connect(self.list_result.clear)
        col3.addWidget(self.btn_clear_result)
        col3.addWidget(self.list_result)
        columns_layout.addLayout(col3)

        main_layout.addLayout(columns_layout)

        # --- przycisk porównaj, na dole, wyśrodkowany ---
        compare_bar = QHBoxLayout()
        compare_bar.addStretch()
        self.btn_compare = QPushButton("Porównaj")
        self.btn_compare.clicked.connect(self.compare_lists)
        compare_bar.addWidget(self.btn_compare)
        compare_bar.addStretch()
        main_layout.addLayout(compare_bar)

        # skaner ma HID-owo "wpisywać" tekst do pola scanner_input,
        # więc od razu dajemy mu focus
        self.scanner_input.setFocus()

    def clear_all(self):
        self.list_scanner.clear()
        self.scanner_input.clear()
        self.list_ocr.clear()
        self.list_result.clear()
        

    def clear_scanner_column(self):
        self.list_scanner.clear()
        self.scanner_input.clear()

    def reset_scan_timer(self):
        self.scan_timer.start(100)

    def on_selection_made(self, start, end):
        print(start, end)
        with mss.mss() as sct:
            monitor = {"left": min(start.x(), end.x()), "top": min(start.y(), end.y()), "width": abs(end.x()-start.x()), "height": abs(end.y()-start.y())}
            screenshot = sct.grab(monitor)
        
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        text = pytesseract.image_to_string(img, config="--psm 6")
        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if line:
                self.list_ocr.addItem(line)

    def add_data_from_screen(self):
        self.selector = ScreenSelector()
        self.selector.selection_made.connect(self.on_selection_made)

    def add_scanned_code(self):
        text = self.scanner_input.text()
        text = text.strip()
        if text:
            self.list_scanner.addItem(text)
        self.scanner_input.clear()

    def compare_lists(self):
        # TODO: krok 7 -> porównanie self.list_ocr vs self.list_scanner,
        # wynik do self.list_result
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())