import sys
import mss
from PIL import Image, ImageStat, ImageOps
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QRect, QSettings
from PyQt6.QtGui import QKeySequence, QPainter, QPen

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QLineEdit, QAbstractItemView, QCheckBox, QSpinBox
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
        self.current_point = None
        self.start_point = None
        self.end_point = None

    def mouseMoveEvent(self, event):
        if self.start_point is not None:
            self.current_point = event.pos()
            self.update()

    def paintEvent(self, event):
        if self.start_point and self.current_point:
            painter = QPainter(self)
            pen = QPen(Qt.GlobalColor.red, 2)  
            painter.setPen(pen)
            painter.drawRect(QRect(self.start_point, self.current_point).normalized())

    def mousePressEvent(self, event):
        self.start_point = event.pos()

    def mouseReleaseEvent(self, event):
        self.end_point = event.pos()
        self.selection_made.emit(self.mapToGlobal(self.start_point), self.mapToGlobal(self.end_point))
        self.close()

class DeletableListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
        elif event.matches(QKeySequence.StandardKey.Copy):
            output = []
            for text in self.selectedItems():
                text = text.text()
                output.append(text)
            output = "\n".join(output)
            QApplication.clipboard().setText(output)
        else:
            super().keyPressEvent(event)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScanDiff")
        self.resize(900, 500)

        main_layout = QVBoxLayout(self)
        self.settings = QSettings("ScanDiff", "ScanDiff")
        self.scan_timer = QTimer(self)
        self.scan_timer.setSingleShot(True)
        self.scan_timer.timeout.connect(self.add_scanned_code)


        # --- górny pasek: przycisk czyszczenia ---
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        options_bar = QHBoxLayout()
        self.chk_invert = QCheckBox("Odwracaj kolory (ciemny motyw)")
        options_bar.addWidget(self.chk_invert)
        options_bar.addWidget(QLabel("Skala OCR:"))
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(1, 5)
        self.spin_scale.setSuffix("x")
        self.chk_invert.setChecked(self.settings.value("invert_colors", True, type=bool))
        self.spin_scale.setValue(self.settings.value("ocr_scale", 3, type=int))
        self.chk_invert.stateChanged.connect(
            lambda: self.settings.setValue("invert_colors", self.chk_invert.isChecked())
        )
        self.spin_scale.valueChanged.connect(
            lambda: self.settings.setValue("ocr_scale", self.spin_scale.value())
        )

        options_bar.addWidget(self.spin_scale)
        options_bar.addStretch()
        main_layout.addLayout(options_bar)
        self.btn_clear = QPushButton("Wyczyść")
        self.btn_clear.clicked.connect(self.clear_all)
        top_bar.addWidget(self.btn_clear)
        main_layout.addLayout(top_bar)

        # --- trzy kolumny obok siebie ---
        columns_layout = QHBoxLayout()

        # Kolumna 1: dane z ekranu (OCR)
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Dane z ekranu"))
        self.list_ocr = DeletableListWidget()
        self.btn_clear_ocr = QPushButton("Wyczyść kolumnę")
        self.btn_clear_ocr.clicked.connect(self.list_ocr.clear)
        col1.addWidget(self.btn_clear_ocr)
        col1.addWidget(self.list_ocr)
        self.btn_add_data = QPushButton("Dodaj dane")
        self.btn_add_data.clicked.connect(self.add_data_from_screen)
        col1.addWidget(self.btn_add_data)
        columns_layout.addLayout(col1)

        # Kolumna 2: dane ze skanera
        self.list_scanner = DeletableListWidget()
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
        self.list_result = DeletableListWidget()
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
        img = img.convert("L")
        if self.chk_invert.isChecked():
            avg_brightness = ImageStat.Stat(img).mean[0]
            if avg_brightness < 128:
                img = ImageOps.invert(img)

        scale = self.spin_scale.value()
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
        # img.save("img.jpg")  

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
        self.list_result.clear()
        ocr_elements = []
        scanner_elements = []
        for i in range(self.list_ocr.count()):
            item = self.list_ocr.item(i).text()
            ocr_elements.append(item)
        for i in range(self.list_scanner.count()):
            item = self.list_scanner.item(i).text()
            scanner_elements.append(item)
        
        ocr_set = set(ocr_elements)
        scanner_set = set(scanner_elements)

        missing = ocr_set - scanner_set
        extra = scanner_set - ocr_set
        
        if not missing and not extra:
            self.list_result.addItem("Brak różnic")
        else:
            if missing:
                self.list_result.addItem(f"BRAK W SKANOWANIU:")
                for item in sorted(missing):
                    self.list_result.addItem(item)
            if extra:
                self.list_result.addItem(f"NADMIAR W SKANOWANIU:")
                for item in sorted(extra):
                    self.list_result.addItem(item)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())