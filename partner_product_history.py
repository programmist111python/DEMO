from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from sqlalchemy.orm import Session

from DB_prepare import ENGINE, Partner, PartnerProduct, Product


class PartnerProductHistoryPage(QWidget):
    def __init__(self, back_cb, parent=None):
        super().__init__(parent)
        self._back = back_cb
        self.partner: Optional[Partner] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("История реализации продукции")
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        self.title_lbl.setFont(f)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        back_btn = QPushButton("Назад")
        back_btn.clicked.connect(self._back)
        header_layout.addWidget(back_btn)
        layout.addLayout(header_layout)

        # Partner info
        self.partner_lbl = QLabel()
        self.partner_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f2 = QFont()
        f2.setBold(True)
        self.partner_lbl.setFont(f2)
        layout.addWidget(self.partner_lbl)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Наименование продукции", "Количество", "Дата продажи"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

    def load_partner_history(self, partner: Partner):
        """Загрузка истории реализации продукции для партнера"""
        self.partner = partner
        self.partner_lbl.setText(f"Партнер: {partner.name} ({partner.partner_type.name})")
        
        # Очистка таблицы
        self.table.setRowCount(0)
        
        with Session(ENGINE) as session:
            # Получаем партнера с присоединенными данными
            partner_obj = (
                session.query(Partner)
                .filter(Partner.id == partner.id)
                .first()
            )
            
            if not partner_obj:
                return
            
            # Загружаем историю реализации продукции
            partner_products = (
                session.query(PartnerProduct, Product)
                .join(Product, PartnerProduct.product_id == Product.id)
                .filter(PartnerProduct.partner_id == partner.id)
                .order_by(PartnerProduct.sale_date.desc())
                .all()
            )
            
            # Заполняем таблицу
            for i, (pp, product) in enumerate(partner_products):
                self.table.insertRow(i)
                
                # Наименование продукции
                self.table.setItem(i, 0, QTableWidgetItem(product.name))
                
                # Количество
                qty_item = QTableWidgetItem(str(pp.quantity))
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 1, qty_item)
                
                # Дата продажи
                date_str = pp.sale_date.strftime("%d.%m.%Y") if pp.sale_date else "—"
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 2, date_item)