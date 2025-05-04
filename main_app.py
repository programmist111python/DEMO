from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QPainter, QPen, QColor, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QFrame,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from DB_prepare import ENGINE, Partner, PartnerType
from partner_discount import calculate_discount, get_partner_total_qty
from partner_product_history import PartnerProductHistoryPage
from material_calculator_page import MaterialCalculatorPage

BASE_DIR = Path(__file__).resolve().parent
APP_ICON_PATH     = BASE_DIR / "resources" / "app_icon.ico"
COMPANY_LOGO_PATH = BASE_DIR / "resources" / "company_logo.png"

def show_message(parent: QWidget, icon: QMessageBox.Icon, title: str, text: str, details: str = ""):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    if details:
        box.setDetailedText(details)
    box.exec()

class ClickableCard(QWidget):
    clicked = Signal(str)  # Сигнал с действием

    def __init__(self, title: str, subtitle: list[str], discount: int, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui(title, subtitle, discount)

    def _build_ui(self, title: str, subtitle: list[str], discount: int):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)
        t_lbl = QLabel(title)
        f = QFont()
        f.setBold(True)
        t_lbl.setFont(f)
        left.addWidget(t_lbl)
        for line in subtitle:
            left.addWidget(QLabel(line))
        root.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(4)
        
        d_lbl = QLabel(f"{discount}%")
        f2 = QFont()
        f2.setPointSize(16)
        f2.setBold(True)
        d_lbl.setFont(f2)
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        right.addWidget(d_lbl)
        
        # Добавляем кнопки действий
        actions = QHBoxLayout()
        actions.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(lambda: self.clicked.emit("edit"))
        actions.addWidget(edit_btn)
        
        history_btn = QPushButton("История")
        history_btn.clicked.connect(lambda: self.clicked.emit("history"))
        actions.addWidget(history_btn)
        
        right.addLayout(actions)
        root.addLayout(right)

    # рамка
    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#A6A6A6"))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 4, 4)

    def mousePressEvent(self, event: QMouseEvent):
        # Отключаем передачу клика на карточку, действия только через кнопки
        super().mousePressEvent(event)

class SideMenuButton(QPushButton):
    def __init__(self, text, icon_path=None, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(50)
        self.setCheckable(True)
        self.setFlat(True)
        
        # Стилизация кнопки
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 20px;
                border: none;
                border-left: 4px solid transparent;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #e0e0e0;
                font-weight: bold;
                border-left: 4px solid #0066cc;
            }
        """)
        
        if icon_path and Path(icon_path).exists():
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))

class PartnerListPage(QWidget):
    def __init__(self, open_form_cb, open_history_cb, parent=None):
        super().__init__(parent)
        self.open_form_cb = open_form_cb
        self.open_history_cb = open_history_cb
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок и кнопка добавления
        header_layout = QHBoxLayout()
        
        title_lbl = QLabel("Партнеры")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        title_lbl.setFont(f)
        header_layout.addWidget(title_lbl)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("Добавить партнёра")
        add_btn.setMinimumWidth(150)
        add_btn.clicked.connect(lambda: self.open_form_cb(None))
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)

        # Список партнеров
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setSpacing(12)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def refresh(self):
        # clear
        while self.vbox.count():
            it = self.vbox.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        with Session(ENGINE) as session:
            partners = (
                session.query(Partner)
                .join(PartnerType)
                .order_by(Partner.name)
                .all()
            )
            for p in partners:
                discount = calculate_discount(get_partner_total_qty(session, p.id))
                subtitle = [
                    f"Директор: {p.director or '—'}",
                    p.phone or "—",
                    f"Рейтинг: {p.rating or '—'}",
                ]
                card = ClickableCard(f"{p.partner_type.name} | {p.name}", subtitle, discount)
                card.clicked.connect(lambda action, obj=p: self._handle_card_action(action, obj))
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self.vbox.addWidget(card)
            self.vbox.addStretch()
    
    def _handle_card_action(self, action: str, partner: Partner):
        if action == "edit":
            self.open_form_cb(partner)
        elif action == "history":
            self.open_history_cb(partner)


EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[\d\s\-\+\(\)]+$")


class PartnerFormPage(QWidget):
    def __init__(self, back_cb, refresh_cb, parent=None):
        super().__init__(parent)
        self._back = back_cb
        self._refresh = refresh_cb
        self.partner: Optional[Partner] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title_lbl = QLabel()
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        self.title_lbl.setFont(f)
        layout.addWidget(self.title_lbl)

        # name
        layout.addWidget(QLabel("Наименование:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # type
        layout.addWidget(QLabel("Тип партнёра:"))
        self.type_combo = QComboBox()
        self._load_types()
        layout.addWidget(self.type_combo)

        # rating
        layout.addWidget(QLabel("Рейтинг:"))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 100)
        layout.addWidget(self.rating_spin)

        # addr
        layout.addWidget(QLabel("Адрес:"))
        self.addr_edit = QLineEdit()
        layout.addWidget(self.addr_edit)

        # director
        layout.addWidget(QLabel("ФИО директора:"))
        self.dir_edit = QLineEdit()
        layout.addWidget(self.dir_edit)

        # phone
        layout.addWidget(QLabel("Телефон:"))
        self.phone_edit = QLineEdit()
        layout.addWidget(self.phone_edit)

        # email
        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_edit)

        # buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        back_btn = QPushButton("Назад")
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        btn_row.addWidget(back_btn)
        layout.addLayout(btn_row)

        save_btn.clicked.connect(self._on_save)
        back_btn.clicked.connect(self._back)

    def _load_types(self):
        self.type_combo.clear()
        with Session(ENGINE) as session:
            for t in session.query(PartnerType).order_by(PartnerType.name):
                self.type_combo.addItem(t.name, t.id)

    def load_partner(self, partner: Optional[Partner]):
        self.partner = partner
        if partner is None:
            self.title_lbl.setText("Новый партнёр")
            self.name_edit.clear()
            self.rating_spin.setValue(0)
            self.addr_edit.clear()
            self.dir_edit.clear()
            self.phone_edit.clear()
            self.email_edit.clear()
            self.type_combo.setCurrentIndex(0)
        else:
            self.title_lbl.setText("Редактирование партнёра")
            self.name_edit.setText(partner.name)
            self.rating_spin.setValue(partner.rating or 0)
            self.addr_edit.setText(partner.legal_address or "")
            self.dir_edit.setText(partner.director or "")
            self.phone_edit.setText(partner.phone or "")
            self.email_edit.setText(partner.email or "")
            idx = self.type_combo.findData(partner.partner_type_id)
            self.type_combo.setCurrentIndex(idx if idx>=0 else 0)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            show_message(self, QMessageBox.Icon.Critical, "Ошибка", "Наименование не может быть пустым")
            return
        email = self.email_edit.text().strip()
        if email and not EMAIL_RE.match(email):
            show_message(self, QMessageBox.Icon.Critical, "Ошибка", "Некорректный email")
            return
        phone = self.phone_edit.text().strip()
        if phone and not PHONE_RE.match(phone):
            show_message(self, QMessageBox.Icon.Critical, "Ошибка", "Телефон содержит недопустимые символы")
            return
        try:
            with Session(ENGINE) as session:
                if self.partner is None:
                    partner = Partner()
                    session.add(partner)
                else:
                    partner = session.get(Partner, self.partner.id)
                partner.name = name
                partner.partner_type_id = self.type_combo.currentData()
                partner.rating = self.rating_spin.value()
                partner.legal_address = self.addr_edit.text().strip()
                partner.director = self.dir_edit.text().strip()
                partner.phone = phone
                partner.email = email
                session.commit()
            show_message(self, QMessageBox.Icon.Information, "Успех", "Данные сохранены")
            self._refresh()
            self._back()
        except SQLAlchemyError as exc:
            show_message(self, QMessageBox.Icon.Critical, "Ошибка сохранения", str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система управления партнерами")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        # Главный контейнер
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Левая панель с меню 
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("background-color: #f8f8f8;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Логотип компании
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем логотип, если файл существует
        if COMPANY_LOGO_PATH.exists():
            logo_lbl = QLabel()
            pixmap = QPixmap(str(COMPANY_LOGO_PATH))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(180, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_lbl.setPixmap(scaled_pixmap)
                logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_layout.addWidget(logo_lbl)
        
        # Название компании
        company_name = QLabel("КОМПАНИЯ")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        company_name.setFont(f)
        company_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(company_name)
        
        left_layout.addWidget(logo_container)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator)
        
        # Кнопки меню
        self.btn_partners = SideMenuButton("Партнеры")
        self.btn_materials = SideMenuButton("Расчет материалов")
        
        left_layout.addWidget(self.btn_partners)
        left_layout.addWidget(self.btn_materials)
        left_layout.addStretch()
        
        # ----- Правая панель с содержимым -----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Стек страниц
        self.stacked = QStackedWidget()
        right_layout.addWidget(self.stacked)
        
        # Создаем страницы
        self.list_page = PartnerListPage(self._open_form, self._open_history)
        self.form_page = PartnerFormPage(self._back_to_list, self._refresh_list)
        self.history_page = PartnerProductHistoryPage(self._back_to_list)
        self.calculator_page = MaterialCalculatorPage()
        
        # Добавляем страницы в стек
        self.stacked.addWidget(self.list_page)      # index 0 - список партнеров
        self.stacked.addWidget(self.form_page)      # index 1 - форма партнера
        self.stacked.addWidget(self.history_page)   # index 2 - история продукции
        self.stacked.addWidget(self.calculator_page) # index 3 - калькулятор материалов
        
        # Соединяем сигналы кнопок меню
        self.btn_partners.clicked.connect(lambda: self._switch_page(0))
        self.btn_materials.clicked.connect(lambda: self._switch_page(3))
        
        # Добавляем панели в главный контейнер
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Устанавливаем начальную страницу
        self._switch_page(0)

    def _refresh_list(self):
        self.list_page.refresh()

    def _open_form(self, partner: Optional[Partner]):
        self.form_page.load_partner(partner)
        self.stacked.setCurrentIndex(1)

    def _open_history(self, partner: Partner):
        self.history_page.load_partner_history(partner)
        self.stacked.setCurrentIndex(2)

    def _back_to_list(self):
        self.stacked.setCurrentIndex(0)
        self._switch_page(0)  # Переключаем и меню
    
    def _switch_page(self, index: int):
        """Переключение между основными страницами"""
        self.stacked.setCurrentIndex(index)
        
        # Обновляем состояние кнопок меню
        self.btn_partners.setChecked(index == 0)
        self.btn_materials.setChecked(index == 3)

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 750)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()