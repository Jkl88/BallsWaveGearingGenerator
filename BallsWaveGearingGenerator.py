import sys
import base64
import numpy as np
import ezdxf
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QLabel,
    QGraphicsScene, QGraphicsView, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QPixmap

class WaveReducerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Настройки: если значение отсутствует, задаем значение по умолчанию
        self.settings = QSettings("WaveReducer", "Settings")
        res_val = self.settings.value("RESOLUTION")
        self.RESOLUTION = int(res_val) if res_val is not None else 600
        self.i = int(self.settings.value("i", 17))
        self.dsh = float(self.settings.value("dsh", 6))
        self.Rout = float(self.settings.value("Rout", 38))
        self.wall_thickness = float(self.settings.value("wall_thickness", 5))
        # Вычисляем D как Rout*2 + внешняя стенка
        self.D = self.Rout * 2 + self.wall_thickness

        self.BASE_WHEEL_SHAPE = bool(self.settings.value("BASE_WHEEL_SHAPE", True))
        self.SEPARATOR = bool(self.settings.value("SEPARATOR", True))
        self.ECCENTRIC = bool(self.settings.value("ECCENTRIC", True))

        self.init_ui()
        # При загрузке сразу показываем предпросмотр
        self.update_preview()

    def init_ui(self):
        self.setWindowTitle("Wave Reducer Profile Generator")
        self.setGeometry(100, 100, 1000, 600)

        widget = QWidget()
        self.setCentralWidget(widget)

        main_layout = QHBoxLayout()  # Поля ввода слева, предпросмотр справа

        left_layout = QVBoxLayout()
        form_layout = QFormLayout()

        # QSpinBox и QDoubleSpinBox с фиксированным количеством знаков после запятой
        self.resolution_input = QSpinBox()
        self.resolution_input.setRange(1, 10000)
        self.resolution_input.setValue(self.RESOLUTION)

        self.i_input = QSpinBox()
        self.i_input.setRange(1, 100)
        self.i_input.setValue(self.i)

        self.dsh_input = QDoubleSpinBox()
        self.dsh_input.setRange(0.1, 1000)
        self.dsh_input.setSingleStep(0.1)
        self.dsh_input.setDecimals(2)
        self.dsh_input.setValue(self.dsh)

        self.rout_input = QDoubleSpinBox()
        self.rout_input.setRange(0.1, 1000)
        self.rout_input.setSingleStep(0.1)
        self.rout_input.setDecimals(2)
        self.rout_input.setValue(self.Rout)

        self.wall_thickness_input = QDoubleSpinBox()
        self.wall_thickness_input.setRange(0.1, 1000)
        self.wall_thickness_input.setSingleStep(0.1)
        self.wall_thickness_input.setDecimals(2)
        self.wall_thickness_input.setValue(self.wall_thickness)

        form_layout.addRow("RESOLUTION:", self.resolution_input)
        form_layout.addRow("Передаточное число (i):", self.i_input)
        form_layout.addRow("Диаметр шариков (dsh):", self.dsh_input)
        form_layout.addRow("Внешний радиус (Rout):", self.rout_input)
        form_layout.addRow("Внешняя стенка редуктора:", self.wall_thickness_input)

        # Чекбоксы для флагов
        self.base_wheel_shape_check = QCheckBox("Профиль жесткого колеса (BASE_WHEEL_SHAPE)")
        self.base_wheel_shape_check.setChecked(self.BASE_WHEEL_SHAPE)

        self.separator_check = QCheckBox("Сепаратор (SEPARATOR)")
        self.separator_check.setChecked(self.SEPARATOR)

        self.eccentric_check = QCheckBox("Эксцентрик (ECCENTRIC)")
        self.eccentric_check.setChecked(self.ECCENTRIC)

        form_layout.addRow(self.base_wheel_shape_check)
        form_layout.addRow(self.separator_check)
        form_layout.addRow(self.eccentric_check)

        left_layout.addLayout(form_layout)

        # Кнопка для генерации профиля
        self.generate_button = QPushButton("Сгенерировать профиль")
        self.generate_button.clicked.connect(self.generate_profile)
        left_layout.addWidget(self.generate_button)

        # Поле для вывода результатов
        self.result_label = QLabel("Результаты:")
        self.result_label.setWordWrap(True)
        left_layout.addWidget(self.result_label)

        # Добавляем логотип под полем вывода результатов
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Логотип "TR" в красном круге (PNG) в base64 - одной строкой
        logo_base64 = b"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"
        logo_data = base64.b64decode(logo_base64)
        logo_pixmap = QPixmap()
        logo_pixmap.loadFromData(logo_data, "PNG")
        self.logo_label.setPixmap(logo_pixmap)
        left_layout.addWidget(self.logo_label)

        main_layout.addLayout(left_layout)

        # Предпросмотр
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        # Устанавливаем размер чуть меньше, чтобы не было полос прокрутки
        self.view.setFixedSize(600, 600)
        main_layout.addWidget(self.view)

        widget.setLayout(main_layout)

        # Включаем сглаживание
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Подключаем обновление при изменении параметров
        self.rout_input.valueChanged.connect(self.update_preview)
        self.wall_thickness_input.valueChanged.connect(self.update_preview)
        self.dsh_input.valueChanged.connect(self.update_preview)
        self.i_input.valueChanged.connect(self.update_preview)
        self.resolution_input.valueChanged.connect(self.update_preview)
        self.base_wheel_shape_check.stateChanged.connect(self.update_preview)
        self.separator_check.stateChanged.connect(self.update_preview)
        self.eccentric_check.stateChanged.connect(self.update_preview)

    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Ошибка ввода")
        msg.exec()

    def update_preview(self):
        # Обновляем D как Rout*2 + внешняя стенка
        Rout = self.rout_input.value()
        wall_thickness = self.wall_thickness_input.value()
        self.D = Rout * 2 + wall_thickness

        # Обновляем остальные параметры
        self.RESOLUTION = self.resolution_input.value()
        self.i = self.i_input.value()
        self.dsh = self.dsh_input.value()
        self.Rout = self.rout_input.value()
        self.wall_thickness = self.wall_thickness_input.value()

        self.BASE_WHEEL_SHAPE = self.base_wheel_shape_check.isChecked()
        self.SEPARATOR = self.separator_check.isChecked()
        self.ECCENTRIC = self.eccentric_check.isChecked()

        self.calculate_and_plot_preview()

    def calculate_and_plot_preview(self):
        # Выполняем расчёты (в мм)
        e = 0.2 * self.dsh
        zg = (self.i + 1) * 1
        zsh = self.i
        Rin = self.Rout - 2 * e
        rsh = self.dsh / 2
        rd = Rin + e - self.dsh
        hc = 2.2 * e
        Rsep_m = rd + rsh
        Rsep_out = Rsep_m + hc / 2
        Rsep_in = Rsep_m - hc / 2

        # Проверяем условие: минимальный Rout = ((1.03*dsh)/sin(pi/zg)) + 0.4*dsh
        min_Rout = ((1.03 * self.dsh) / np.sin(np.pi / zg)) + 0.4 * self.dsh
        if self.Rout <= min_Rout:
            error_message = f"Ошибка: Внешний радиус (Rout) должен быть больше: {min_Rout:.2f} мм."
            self.result_label.setText(error_message)
            self.scene.clear()
            return

        theta = np.linspace(0, 2 * np.pi, self.RESOLUTION)
        S = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * theta), 2))
        l = e * np.cos(zg * theta) + S
        Xi = np.arctan2(e * zg * np.sin(zg * theta), S)
        x = l * np.sin(theta) + rsh * np.sin(theta + Xi)
        y = l * np.cos(theta) + rsh * np.cos(theta + Xi)

        self.scene.clear()
        # Косметическое перо: фиксированная толщина линии
        pen = QPen(Qt.GlobalColor.blue)
        pen.setWidth(1)
        pen.setCosmetic(True)

        # Если профиль жесткого колеса включён, рисуем базовый контур и внешнюю стенку
        if self.BASE_WHEEL_SHAPE:
            path = QPainterPath()
            if len(x) > 0:
                path.moveTo(x[0], y[0])
                for j in range(1, len(x)):
                    path.lineTo(x[j], y[j])
            self.scene.addPath(path, pen)
            self.scene.addEllipse(-self.D/2, -self.D/2, self.D, self.D, pen)

        # Сепаратор
        if self.SEPARATOR:
            sep_pen = QPen(Qt.GlobalColor.green)
            sep_pen.setWidth(1)
            sep_pen.setCosmetic(True)
            # Вертикальная линия от (0,0) до (0,e)
            self.scene.addLine(0, 0, 0, e, sep_pen)
            # Горизонтальная линия на уровне 0 от (-6,0) до (6,0)
            self.scene.addLine(-6, 0, 6, 0, sep_pen)
            # Горизонтальная линия на уровне e от (-3,e) до (3,e)
            self.scene.addLine(-3, e, 3, e, sep_pen)
            self.scene.addEllipse(-Rsep_out, -Rsep_out, Rsep_out*2, Rsep_out*2, sep_pen)
            self.scene.addEllipse(-Rsep_in, -Rsep_in, Rsep_in*2, Rsep_in*2, sep_pen)

        # Эксцентрик
        if self.ECCENTRIC:
            ecc_pen = QPen(Qt.GlobalColor.red)
            ecc_pen.setWidth(1)
            ecc_pen.setCosmetic(True)
            self.scene.addEllipse(-rd, e - rd, rd*2, rd*2, ecc_pen)

        self.fit_view_to_scene()
        self.result_label.setText("Параметры корректны.")

    def fit_view_to_scene(self):
        items_rect = self.scene.itemsBoundingRect()
        margin = 10
        scene_rect = items_rect.adjusted(-margin, -margin, margin, margin)
        self.scene.setSceneRect(scene_rect)
        self.view.resetTransform()
        scale_factor = min(self.view.width() / scene_rect.width(),
                           self.view.height() / scene_rect.height())
        self.view.scale(scale_factor, scale_factor)

    def generate_profile(self):
        if not self.resolution_input.value() or not self.i_input.value() or not self.dsh_input.value() or not self.rout_input.value() or not self.wall_thickness_input.value():
            self.show_error_message("Пожалуйста, заполните все поля!")
            return

        self.RESOLUTION = self.resolution_input.value()
        self.i = self.i_input.value()
        self.dsh = self.dsh_input.value()
        self.Rout = self.rout_input.value()
        self.wall_thickness = self.wall_thickness_input.value()
        self.D = self.Rout * 2 + self.wall_thickness

        self.BASE_WHEEL_SHAPE = self.base_wheel_shape_check.isChecked()
        self.SEPARATOR = self.separator_check.isChecked()
        self.ECCENTRIC = self.eccentric_check.isChecked()

        OUT_FILE = f"vptc_{self.i}_{self.dsh:.2f}_{self.Rout:.2f}.dxf"
        self.calculate_and_plot(OUT_FILE)

    def calculate_and_plot(self, OUT_FILE):
        e = 0.2 * self.dsh
        zg = (self.i + 1) * 1
        zsh = self.i
        Rin = self.Rout - 2 * e
        rsh = self.dsh / 2
        rd = Rin + e - self.dsh
        hc = 2.2 * e
        Rsep_m = rd + rsh
        Rsep_out = Rsep_m + hc / 2
        Rsep_in = Rsep_m - hc / 2

        min_Rout = ((1.03 * self.dsh) / np.sin(np.pi / zg)) + 0.4 * self.dsh
        if self.Rout <= min_Rout:
            error_message = f"Ошибка: Внешний радиус (Rout) должен быть больше: {min_Rout:.2f} мм."
            self.result_label.setText(error_message)
            return

        theta = np.linspace(0, 2 * np.pi, self.RESOLUTION)
        S = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * theta), 2))
        l = e * np.cos(zg * theta) + S
        Xi = np.arctan2(e * zg * np.sin(zg * theta), S)
        x = l * np.sin(theta) + rsh * np.sin(theta + Xi)
        y = l * np.cos(theta) + rsh * np.cos(theta + Xi)
        xy = np.stack((x, y), axis=1)

        doc = ezdxf.new("R2000")
        msp = doc.modelspace()

        if self.BASE_WHEEL_SHAPE:
            msp.add_lwpolyline(xy, dxfattribs={'layer': 'BASE', 'color': 1, 'linetype': 'CONTINUOUS'})
            msp.add_circle((0, 0), radius=self.D/2, dxfattribs={'layer': 'BASE', 'color': 1, 'linetype': 'CONTINUOUS'})
        if self.SEPARATOR:
            msp.add_circle((0, 0), radius=Rsep_out, dxfattribs={'layer': 'SEP', 'color': 3, 'linetype': 'DASHED'})
            msp.add_circle((0, 0), radius=Rsep_in, dxfattribs={'layer': 'SEP', 'color': 3, 'linetype': 'DASHED'})
        if self.ECCENTRIC:
            msp.add_lwpolyline([[0, 0], [0, e]], dxfattribs={'layer': 'ECC', 'color': 5, 'linetype': 'CENTER'})
            msp.add_lwpolyline([[-6, 0], [6, 0]], dxfattribs={'layer': 'ECC', 'color': 5, 'linetype': 'CENTER'})
            msp.add_lwpolyline([[-3, e], [3, e]], dxfattribs={'layer': 'ECC', 'color': 5, 'linetype': 'CENTER'})
            msp.add_circle((0, e), radius=rd, dxfattribs={'layer': 'ECC', 'color': 5, 'linetype': 'CENTER'})

        doc.saveas(OUT_FILE)
        params_text = f"""
        Основные параметры ВПТК:
        - Передаточное число: {self.i}
        - Эксцентриситет: {e:.2f} мм
        - Радиус эксцентрика: {rd:.2f} мм
        - Внутренний радиус профиля жесткого колеса: {Rin:.2f} мм
        - Число шариков: {zsh}
        - Делительный радиус сепаратора: {Rsep_m:.2f} мм
        - Толщина сепаратора: {hc:.2f} мм
        """
        self.result_label.setText(f"Профиль построен и сохранён в файл: {OUT_FILE}\n{params_text}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WaveReducerApp()
    window.show()
    sys.exit(app.exec())
