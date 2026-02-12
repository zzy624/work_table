# -*-coding:utf-8-*-

import os
import sys
import time
from datetime import datetime

from PyQt5.QtCore import pyqtSlot, Qt, QThread, pyqtSignal, QEvent, QDate
from PyQt5.QtGui import QIntValidator, QColor, QFont, QBrush
from PyQt5.QtWidgets import (QApplication, QMainWindow, QListWidgetItem,
                             QDialog, QTableWidgetItem, QMessageBox, QSlider,
                             QComboBox, QStyledItemDelegate, QHBoxLayout, QPushButton, QComboBox, QGroupBox, QLineEdit,
                             QLabel, QVBoxLayout, QFileDialog, QProgressDialog)

from logic.work_table import WorkTable
from logic.chinese_messagebox import setup_chinese_messagebox
from ui.pyui.ui_config import Ui_Dialog
from ui.pyui.ui_main import Ui_MainWindow
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning,
                        message="sipPyTypeDict.*deprecated")

tab_bar_stylesheet = """
            QTabBar::tab {
                background-color: lightgray;
                color: rgb(38, 38, 38);
                border-radius: 2px; /* 设置圆角半径 */
                padding:5px;
            }

            QTabBar::tab:selected {
                background-color: rgb(20, 133, 255);
                color: rgb(255, 255, 255);
            }
        """


class CheckableComboBox(QComboBox):
    """支持多选的 QComboBox，保持原有外观"""

    selectionChanged = pyqtSignal(list)
    emptyClicked = pyqtSignal()

    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)

        # 保持原有外观，设置为可编辑但只读
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().installEventFilter(self)

        # 使用自定义委托显示复选框
        self.setItemDelegate(QStyledItemDelegate())

        # 模型数据改变时更新显示文本
        self.model().dataChanged.connect(self.updateText)
        self.model().dataChanged.connect(self.emitSelectionChanged)

        # 点击下拉框时不选中文本
        self.lineEdit().selectionChanged.connect(lambda: self.lineEdit().setSelection(0, 0))

        # 安装事件过滤器
        self.installEventFilter(self)

        # 设置下拉框最大高度
        self.view().setMaximumHeight(200)

    def showPopup(self):
        """重写showPopup方法"""
        if self.count() == 0:
            # 没有内容，发射信号
            self.emptyClicked.emit()
        else:
            super().showPopup()

    def eventFilter(self, obj, event):
        """事件过滤器"""
        # 点击编辑框时显示/隐藏下拉框
        if obj == self.lineEdit() and event.type() == QEvent.MouseButtonRelease:
            if self.view().isVisible():
                self.hidePopup()
            else:
                self.showPopup()
            return True

        # 关闭下拉框时更新显示
        if obj == self and event.type() == QEvent.Hide:
            if event.spontaneous():
                self.updateText()

        return super(CheckableComboBox, self).eventFilter(obj, event)

    def addItems(self, texts):
        """批量添加项目"""
        for text in texts:
            self.addItem(text)

    def addItem(self, text, userData=None):
        """添加单个项目"""
        super(CheckableComboBox, self).addItem(text, userData)

        # 为新项目设置复选框
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)

    def itemChecked(self, index):
        """检查项目是否选中"""
        item = self.model().item(index, 0)
        return item.checkState() == Qt.Checked

    def setItemChecked(self, index, checked=True):
        """设置项目选中状态"""
        item = self.model().item(index, 0)
        if checked:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        self.updateText()

    def checkedItems(self):
        """获取所有选中的项目"""
        checked_items = []
        for i in range(self.count()):
            if self.itemChecked(i):
                checked_items.append(self.itemText(i))
        return checked_items

    def updateText(self):
        """更新显示文本"""
        checked_items = self.checkedItems()
        if checked_items:
            if len(checked_items) <= 5:
                text = ", ".join(checked_items)
            else:
                text = f"已选中 {len(checked_items)} 项"
        else:
            text = "请选择..."

        self.lineEdit().setText(text)

    def emitSelectionChanged(self):
        """发射选中状态改变信号"""
        self.selectionChanged.emit(self.checkedItems())

    def selectAll(self):
        """全选"""
        for i in range(self.count()):
            self.setItemChecked(i, True)

    def selectNone(self):
        """全不选"""
        for i in range(self.count()):
            self.setItemChecked(i, False)


class UIConfigDialog(QDialog, Ui_Dialog):
    def __init__(self, parent=None, index=0):
        super(UIConfigDialog, self).__init__(parent)
        self.setupUi(self)
        self.tabWidget.setStyleSheet(tab_bar_stylesheet)
        self.tabWidget.setCurrentIndex(index)
        self.application_path = get_application_path()
        self.parent_window = parent

        self.textEdit.setPlaceholderText("支持格式示例：\n"
                                                    "• 服务器1 192.168.1.1 (空格)\n"
                                                    "• 服务器1\t192.168.1.1 (Tab)\n"
                                                    "• 服务器1,192.168.1.1 (逗号)\n"
                                                    "• 服务器1:192.168.1.1 (冒号)\n")

    @pyqtSlot()
    def on_pushButton_save_config_clicked(self):
        with open(self.application_path + f'/config/service', 'w') as file:
            file.write(self.textEdit.toPlainText())
        with open(self.application_path + f'/config/master_account', 'w') as file:
            file.write(self.textEdit_2.toPlainText())
        with open(self.application_path + f'/config/from_account', 'w') as file:
            file.write(self.textEdit_3.toPlainText())
        self.parent_window.load_combo_data()
        QMessageBox.information(self, "提示", "配置已更新")
        self.reject()

    @pyqtSlot()
    def on_pushButton_quit_config_clicked(self):
        self.reject()


class UIMainWindow(QMainWindow, Ui_MainWindow):
    W = WorkTable()

    def __init__(self):
        super(UIMainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint |
                            Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)

        # 初始化 application_path
        self.application_path = get_application_path()

        # 替换原有的 QComboBox 为 CheckableComboBox
        self.setup_checkable_combobox()

        # 连接空数据点击信号
        self.check_combo_from.emptyClicked.connect(lambda: self.on_action_menu_clicked(1))
        self.check_combo_master.emptyClicked.connect(lambda: self.on_action_menu_clicked(2))

        # 连接信号
        self.setup_connections()

        # 加载数据
        self.load_combo_data()
        self.header = None

        # 设置初始时间
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit_2.setDate(QDate.currentDate())

        # 设置statusBar
        self.statusBar().showMessage('版本：v1.0.0')

    def setup_checkable_combobox(self):
        """设置可多选的下拉框"""
        # 创建从账号多选下拉框
        self.check_combo_from = CheckableComboBox(self)
        self.check_combo_from.lineEdit().setPlaceholderText("请选择或配置从账号")

        # 创建主账号多选下拉框
        self.check_combo_master = CheckableComboBox(self)
        self.check_combo_master.lineEdit().setPlaceholderText("请选择或配置主账号")

        # 替换原有的 QComboBox
        self.replace_combo_widgets()

    def replace_combo_widgets(self):
        """替换原有的下拉框控件"""
        # 保存原有的最小/最大尺寸
        from_size = self.comboBox.minimumSize()
        master_size = self.comboBox_2.minimumSize()

        # 从布局中移除原有的控件
        self.horizontalLayout_2.removeWidget(self.comboBox)
        self.horizontalLayout_2.removeWidget(self.comboBox_2)

        # 设置新控件的最小尺寸
        self.check_combo_from.setMinimumSize(from_size)
        self.check_combo_master.setMinimumSize(master_size)
        self.check_combo_from.setFocus()
        # 添加新的多选下拉框到布局（保持原有顺序）
        # 找到 label_3 和 label_4 的位置
        for i in range(self.horizontalLayout_2.count()):
            widget = self.horizontalLayout_2.itemAt(i).widget()
            if widget == self.label_3:
                # 在 label_3 后面插入从账号下拉框
                self.horizontalLayout_2.insertWidget(i + 1, self.check_combo_from)
            elif widget == self.label_4:
                # 在 label_4 后面插入主账号下拉框
                self.horizontalLayout_2.insertWidget(i + 1, self.check_combo_master)

        self.check_combo_from.setFocusPolicy(Qt.StrongFocus)
        self.check_combo_master.setFocusPolicy(Qt.StrongFocus)

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.check_combo_from.setFocus())

        # 隐藏原有的控件（不删除，以备后用）
        self.comboBox.hide()
        self.comboBox_2.hide()

    # 打开配置文件对话框
    def on_action_menu_clicked(self, index):
        cw = UIConfigDialog(self)
        cw.tabWidget.setCurrentIndex(index)
        try:
            # 确保config目录存在
            config_dir = self.application_path + '/config'
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # 处理 service 文件
            service_file = config_dir + '/service'
            if os.path.exists(service_file):
                with open(service_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    cw.textEdit.setText(content)
            else:
                # 创建空文件并设置默认提示
                with open(service_file, 'w', encoding='utf-8') as file:
                    file.write('')

            # 处理 master_account 文件
            master_file = config_dir + '/master_account'
            if os.path.exists(master_file):
                with open(master_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    cw.textEdit_2.setText(content)
            else:
                # 创建空文件并设置默认提示
                with open(master_file, 'w', encoding='utf-8') as file:
                    file.write('')

            # 处理 from_account 文件
            from_file = config_dir + '/from_account'
            if os.path.exists(from_file):
                with open(from_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    cw.textEdit_3.setText(content)
            else:
                # 创建空文件并设置默认提示
                with open(from_file, 'w', encoding='utf-8') as file:
                    file.write('')

        except Exception as e:
            QMessageBox.warning(self, "警告", f"配置文件处理失败：{str(e)}")

        # 执行对话框的模态运行，阻止用户与应用程序其他部分的交互
        cw.exec_()

    def setup_connections(self):
        """设置信号连接"""
        self.action_service.triggered.connect(lambda: self.on_action_menu_clicked(0))
        self.action_master_account.triggered.connect(lambda: self.on_action_menu_clicked(2))
        self.action_from_account.triggered.connect(lambda: self.on_action_menu_clicked(1))
        self.listWidget.itemSelectionChanged.connect(self.on_selection_changed)
        # self.exportButton.clicked.connect(lambda: self.on_exportButton_clicked)

        # 连接多选下拉框信号
        self.check_combo_from.selectionChanged.connect(self.on_from_accounts_changed)
        self.check_combo_master.selectionChanged.connect(self.on_master_accounts_changed)

    def on_from_accounts_changed(self, selected_items):
        """从账号选中状态改变"""


    def on_master_accounts_changed(self, selected_items):
        """主账号选中状态改变"""

    def load_combo_data(self):
        """加载下拉框数据"""
        # 确保 config 目录存在
        config_dir = os.path.join(self.application_path, 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            print(f"创建配置目录: {config_dir}")

        # 加载从账号到 check_combo_from
        from_account_file = os.path.join(config_dir, 'from_account')
        if os.path.exists(from_account_file):
            try:
                with open(from_account_file, 'r', encoding='utf-8') as f:
                    accounts = [line.strip() for line in f if line.strip()]
                    self.check_combo_from.clear()
                    self.check_combo_from.addItems(accounts)
                    # 默认全选
                    # self.check_combo_from.selectAll()
                    # print(f"加载从账号: {len(accounts)} 个")
            except Exception as e:
                print(f"读取从账号配置失败: {e}")
                self.check_combo_from.clear()
                self.check_combo_from.addItems([])
                self.check_combo_from.selectAll()
        else:
            # 文件不存在，创建默认配置
            self.check_combo_from.clear()
            self.check_combo_from.selectAll()
            print(f"创建默认从账号配置: {from_account_file}")

        # 加载主账号到 check_combo_master
        master_account_file = os.path.join(config_dir, 'master_account')
        if os.path.exists(master_account_file):
            try:
                with open(master_account_file, 'r', encoding='utf-8') as f:
                    accounts = [line.strip() for line in f if line.strip()]
                    self.check_combo_master.clear()
                    self.check_combo_master.addItems(accounts)
                    # 默认全选
                    self.check_combo_master.selectAll()
                    # print(f"加载主账号: {len(accounts)} 个")
            except Exception as e:
                print(f"读取主账号配置失败: {e}")
                self.check_combo_master.clear()
                self.check_combo_master.addItems([])
                self.check_combo_master.selectAll()
        else:
            # 文件不存在，创建默认配置
            self.check_combo_master.clear()
            self.check_combo_master.selectAll()
            print(f"创建默认主账号配置: {master_account_file}")

    def get_selected_from_accounts(self):
        """获取选中的从账号"""
        return self.check_combo_from.checkedItems()

    def get_selected_master_accounts(self):
        """获取选中的主账号"""
        return self.check_combo_master.checkedItems()

    def on_selection_changed(self):
        """选择状态改变时触发（单选/多选都会触发）"""
        self.set_table(self.W.data_dict[self.listWidget.currentItem().text()].values)

    @pyqtSlot()
    def on_pushButton_generate_data_clicked(self):
        start_date = datetime.strptime(self.dateEdit.text(), "%Y/%m/%d").strftime("%Y-%m-%d")
        end_date = datetime.strptime(self.dateEdit_2.text(), "%Y/%m/%d").strftime("%Y-%m-%d")
        resource_ip_list = []
        master_account_list = self.get_selected_master_accounts()
        from_account_list = self.get_selected_from_accounts()

        if not master_account_list:
            QMessageBox.warning(self, "警告", "请选择至少一个主账号")
            return

        if not from_account_list:
            QMessageBox.warning(self, "警告", "请选择至少一个从账号")
            return

        date1 = self.dateEdit.date()
        date2 = self.dateEdit_2.date()

        if date1 > date2:
            QMessageBox.warning(self, "警告", "开始时间应小于结束时间")
            return

        config_dir = os.path.join(self.application_path, 'config')
        from_account_file = os.path.join(config_dir, 'service')
        if os.path.exists(from_account_file):
            try:
                with open(from_account_file, 'r', encoding='utf-8') as f:
                    resource_ip_list = []
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        # 支持多种分隔符：空格、Tab、逗号、冒号、竖线、分号
                        for sep in ['\t', ' ', ',', ':', '|', ';']:
                            if sep in line:
                                parts = line.split(sep)
                                parts = [p.strip() for p in parts if p.strip()]
                                if len(parts) >= 2:
                                    resource_ip_list.append(f"{parts[0]} {parts[1]}")
                                    break
                        else:
                            # 没有找到分隔符，整行作为单个项处理（IP或服务器名）
                            if line:
                                resource_ip_list.append(line)

                    if len(resource_ip_list) == 0:
                        reply = QMessageBox.warning(self, "提示",
                                                    "服务配置信息不存在，请先配置服务器",
                                                    QMessageBox.Ok | QMessageBox.Cancel)
                        # 判断用户点击了哪个按钮
                        if reply == QMessageBox.Ok:
                            self.on_action_menu_clicked(0)
                        elif reply == QMessageBox.Cancel:
                            pass
                        return

            except Exception as e:
                QMessageBox.warning(self, "提示",
                                f"服务配置加载失败\n\n"
                                f"支持格式示例：\n"
                                f"• 服务器1 192.168.1.1 (空格)\n"
                                f"• 服务器1\t192.168.1.1 (Tab)\n"
                                f"• 服务器1,192.168.1.1 (逗号)\n"
                                f"• 服务器1:192.168.1.1 (冒号)\n"
                                f"错误信息: {str(e)}")

            dialog = QDialog(self)
            dialog.setWindowTitle("请稍候")

            # 正确的链式调用方式
            dialog.setLayout(QVBoxLayout())
            dialog.layout().addWidget(QLabel("加载中...", alignment=Qt.AlignCenter))

            dialog.setFixedSize(140, 60)
            dialog.setWindowModality(Qt.WindowModal)
            dialog.show()
            self.W.generate_timesheet_data(
                start_date,
                end_date,
                resource_ip_list,
                from_account_list,
                master_account_list
            )

            # 获取表头
            self.header = self.W.header
            self.listWidget.clear()
            for key, value in self.W.data_dict.items():
                font = QFont()
                font.setPointSize(14)  # 设置字体大小为12
                item = QListWidgetItem(key)
                item.setFont(font)  # 应用到列表项
                self.listWidget.addItem(item)
            # 设置页宽度
            self.listWidget.setMinimumWidth(self.listWidget.sizeHintForColumn(0) + 10)
            self.label_8.setMinimumWidth(self.listWidget.sizeHintForColumn(0) + 10)
            # 默认第一页数据
            self.listWidget.setCurrentRow(0)
            self.set_table(self.W.data_dict[next(iter(self.W.data_dict))].values)

            dialog.close()

    def set_table(self, data_list):
        headers = self.setup_table_from_header(self.header)
        self.populate_data_rows(headers, data_list)

    def setup_table_from_header(self, header_row, data_list=None):
        """从 HeaderRow 对象设置完整表格"""
        # 1. 清空表格
        self.tableWidget.clear()
        self.tableWidget.setRowCount(0)

        # 2. 提取表头信息
        headers = []
        for item in header_row.items:
            headers.append({
                'text': item.text,
                'original_text': item.text,  # 保存原始文本
                'display_text': self.clean_header_text(item.text),
                'row_span': item.row_span,
                'col_span': item.col_span,
                'style': item.style
            })

        # 3. 设置列数
        column_count = len(headers)
        self.tableWidget.setColumnCount(column_count)

        # 4. 设置表头
        display_labels = [h['display_text'] for h in headers]
        self.tableWidget.setHorizontalHeaderLabels(display_labels)

        # 5. 应用表头样式
        for col, header in enumerate(headers):
            header_item = self.tableWidget.horizontalHeaderItem(col)
            if header_item:
                self.apply_header_item_style(header_item, header['style'])

        # 6. 如果有数据，填充数据
        if data_list:
            self.tableWidget.setRowCount(len(data_list))
            self.populate_data_rows(headers, data_list)

        # 7. 调整列宽
        self.tableWidget.resizeColumnsToContents()

        # 8. 可选：设置交替行颜色
        self.tableWidget.setAlternatingRowColors(True)

        # 9. 设置选择行为
        self.tableWidget.setSelectionBehavior(self.tableWidget.SelectRows)
        self.tableWidget.setSelectionMode(self.tableWidget.SingleSelection)

        return headers

    def clean_header_text(self, text):
        """清理表头文本"""
        # 去掉换行符，用空格代替
        cleaned = text.replace('\n', ' ')

        # 可选：限制长度
        if len(cleaned) > 20:
            cleaned = cleaned[:20] + "..."

        return cleaned

    def populate_data_rows(self, headers, data_list):
        """填充数据行 - 二维数组版本"""
        # 设置表格不可编辑
        self.tableWidget.setEditTriggers(self.tableWidget.NoEditTriggers)
        # 设置行数
        row_count = len(data_list)
        self.tableWidget.setRowCount(row_count)

        # 设置列数（如果还没设置）
        if self.tableWidget.columnCount() == 0:
            self.tableWidget.setColumnCount(len(headers))

        # 直接按行列填充
        for row, row_data in enumerate(data_list):
            for col, cell_value in enumerate(row_data):
                if col < self.tableWidget.columnCount():  # 防止索引越界
                    item = QTableWidgetItem(str(cell_value))

                    # 根据数据类型设置对齐方式
                    if isinstance(cell_value, (int, float)):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    elif isinstance(cell_value, str):
                        # 字符串左对齐
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)

                    self.tableWidget.setItem(row, col, item)

        # 调整列宽适应内容
        self.tableWidget.resizeColumnsToContents()

    def apply_header_item_style(self, header_item, style):
        """应用表头项样式"""
        font_config = style.font
        font = QFont()
        font.setFamily(font_config.name)
        font.setPointSize(font_config.size)
        font.setBold(True)  # 表头通常加粗

        header_item.setFont(font)

        # 设置文本颜色
        if font_config.color:
            try:
                color = QColor(font_config.color)
                header_item.setForeground(QBrush(color))
            except:
                pass

        # 设置背景色
        fill_config = style.fill
        if fill_config.color != '#ffffff':
            try:
                bg_color = QColor(fill_config.color)
                header_item.setBackground(QBrush(bg_color))
            except:
                pass

    @pyqtSlot()
    def on_exportButton_clicked(self):
        if self.tableWidget.rowCount() == 0:
            QMessageBox.warning(self, "提示", "请先生成数据！")
            return
        # 1. 获取表名
        table_name = "数据表"  # 替换为实际的表名获取逻辑

        # 2. 生成默认文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{table_name}_{timestamp}.xlsx"
        default_path = os.path.join(os.path.expanduser("~/Downloads"), default_name)

        # 3. 打开保存对话框，用户可以修改文件名
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文件",
            default_path,  # 默认文件名
            "Excel文件 (*.xlsx);;CSV文件 (*.csv);;所有文件 (*.*)"
        )

        # 4. 执行导出
        if file_path:
            try:
                # 根据扩展名选择导出方式
                if file_path.endswith('.xlsx'):
                    self.export(file_path)
                elif file_path.endswith('.csv'):
                    self.export(file_path)
                else:
                    # 默认导出为Excel
                    if not file_path.endswith('.xlsx'):
                        file_path += '.xlsx'
                    self.export(file_path)
                return

            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"错误: {str(e)}")

    def export(self, file_path):
        # 创建进度对话框
        progress_dialog = QProgressDialog("正在导出...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("导出进度")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.show()
        QApplication.processEvents()

        # 跟踪取消状态
        is_cancelled = False

        def progress_callback(progress: int, status: str):
            nonlocal is_cancelled

            # 检查是否取消
            if progress_dialog.wasCanceled():
                is_cancelled = True
                return False  # 取消导出

            # 更新进度
            progress_dialog.setValue(progress)
            # progress_dialog.setLabelText(f"{progress}%")
            QApplication.processEvents()

            return True

        try:
            # 执行导出
            self.W.export(file_path, progress_callback=progress_callback)

            # 根据结果显示不同消息
            if is_cancelled:
                QMessageBox.information(self, "导出取消", "导出操作已被用户取消")
            else:
                QMessageBox.information(self, "导出成功", f"文件已保存到:\n{file_path}")

        except Exception as e:
            if not is_cancelled:  # 如果不是用户取消的错误
                QMessageBox.critical(self, "错误", str(e))

        finally:
            progress_dialog.close()


def get_application_path():
    """获取应用程序路径 - 跨平台兼容版本"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的程序
        if hasattr(sys, '_MEIPASS'):
            # Windows 单文件打包：_MEIPASS 是临时解压目录
            # 我们需要获取 exe 所在目录，而不是临时目录
            if sys.platform == 'win32':
                # Windows：获取 exe 文件所在目录
                base_path = os.path.dirname(sys.executable)
            else:
                # macOS/Linux：使用 _MEIPASS
                base_path = sys._MEIPASS
        else:
            # 文件夹打包或非 Windows 平台
            base_path = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        base_path = os.path.dirname(os.path.abspath(__file__))

    return base_path


if __name__ == '__main__':
    app = QApplication(sys.argv)
    setup_chinese_messagebox()
    dlg = UIMainWindow()
    dlg.show()
    app.exec_()
