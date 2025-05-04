from __future__ import annotations
from typing import Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDoubleValidator
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QComboBox,
    QSpinBox,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from sqlalchemy.orm import Session

from DB_prepare import ENGINE, ProductType, MaterialType
from material_calculator import calculate_material_quantity


class MaterialCalculatorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Заголовок
        title_lbl = QLabel("Расчет количества материала")
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        title_lbl.setFont(f)
        layout.addWidget(title_lbl)

        # Группа для ввода параметров
        params_group = QGroupBox("Параметры расчета")
        form_layout = QFormLayout(params_group)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 15, 15, 15)

        # Тип продукции
        self.product_type_combo = QComboBox()
        form_layout.addRow("Тип продукции:", self.product_type_combo)

        # Тип материала
        self.material_type_combo = QComboBox()
        form_layout.addRow("Тип материала:", self.material_type_combo)

        # Количество продукции
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 10000)
        self.quantity_spin.setValue(1)
        form_layout.addRow("Количество продукции:", self.quantity_spin)

        # Параметр 1
        self.param1_edit = QLineEdit()
        self.param1_edit.setValidator(QDoubleValidator(0.01, 10000.0, 2))
        self.param1_edit.setText("1.0")
        form_layout.addRow("Параметр продукции 1:", self.param1_edit)

        # Параметр 2
        self.param2_edit = QLineEdit()
        self.param2_edit.setValidator(QDoubleValidator(0.01, 10000.0, 2))
        self.param2_edit.setText("1.0")
        form_layout.addRow("Параметр продукции 2:", self.param2_edit)

        layout.addWidget(params_group)

        # Кнопка расчета
        calculate_btn = QPushButton("Рассчитать")
        calculate_btn.clicked.connect(self._calculate)
        calculate_btn.setMinimumHeight(40)
        layout.addWidget(calculate_btn)

        # Результат
        result_group = QGroupBox("Результат расчета")
        result_layout = QVBoxLayout(result_group)
        
        self.result_label = QLabel("Для расчета необходимого количества материала введите данные и нажмите кнопку")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)
        result_layout.addWidget(self.result_label)
        
        layout.addWidget(result_group)
        
        # Дополнительная информация о коэффициентах
        info_label = QLabel("* При расчете учитывается коэффициент типа продукции и процент брака материала")
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        # Растягивающийся элемент в конце
        layout.addStretch()

    def _load_data(self):
        """Загрузка данных в комбобоксы"""
        try:
            with Session(ENGINE) as session:
                # Загрузка типов продукции
                product_types = session.query(ProductType).order_by(ProductType.name).all()
                for p_type in product_types:
                    self.product_type_combo.addItem(p_type.name, p_type.id)
                
                # Загрузка типов материалов
                material_types = session.query(MaterialType).order_by(MaterialType.name).all()
                for m_type in material_types:
                    defect_percent = f"{float(m_type.defect_percentage):.4f}%" if m_type.defect_percentage else "0%"
                    self.material_type_combo.addItem(f"{m_type.name} (брак: {defect_percent})", m_type.id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки данных", f"Не удалось загрузить данные: {str(e)}")

    def _parse_inputs(self) -> Tuple[int, int, int, float, float]:
        """Парсинг и валидация входных данных"""
        product_type_id = self.product_type_combo.currentData()
        material_type_id = self.material_type_combo.currentData()
        quantity = self.quantity_spin.value()
        
        try:
            param1 = float(self.param1_edit.text().replace(',', '.'))
            param2 = float(self.param2_edit.text().replace(',', '.'))
            
            if param1 <= 0 or param2 <= 0:
                raise ValueError("Параметры продукции должны быть положительными числами")
                
            return product_type_id, material_type_id, quantity, param1, param2
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка ввода", str(e))
            return None, None, None, None, None

    def _calculate(self):
        """Выполнение расчета и отображение результата"""
        inputs = self._parse_inputs()
        if None in inputs:
            return
            
        product_type_id, material_type_id, quantity, param1, param2 = inputs
        
        result = calculate_material_quantity(
            product_type_id=product_type_id,
            material_type_id=material_type_id,
            quantity=quantity,
            param1=param1,
            param2=param2
        )
        
        if result == -1:
            self.result_label.setText(
                "<span style='color: red;'>Невозможно выполнить расчет. "
                "Проверьте входные данные или наличие выбранных типов в системе.</span>"
            )
        else:
            product_type_name = self.product_type_combo.currentText()
            material_type_name = self.material_type_combo.currentText().split(" (")[0]
            
            self.result_label.setText(
                f"<div style='text-align: center;'>"
                f"<p><b>Для производства {quantity} ед. продукции типа \"{product_type_name}\"</b></p>"
                f"<p>требуется <b style='font-size: 16px; color: #0066cc;'>{result} ед.</b> "
                f"материала типа \"{material_type_name}\"</p>"
                f"<p>(с учетом параметров продукции {param1} × {param2} и возможного брака)</p>"
                f"</div>"
            )
