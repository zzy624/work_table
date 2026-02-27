# -*-coding:utf-8-*-

import os
import sys
import time
from datetime import datetime
import traceback

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
        # 保存时统一使用UTF-8编码
        with open(self.application_path + f'/config/service', 'w', encoding='utf-8') as file:
            file.write(self.textEdit.toPlainText())
        with open(self.application_path + f'/config/master_account', 'w', encoding='utf-8') as file:
            file.write(self.textEdit_2.toPlainText())
        with open(self.application_path + f'/config/from_account', 'w', encoding='utf-8') as file:
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

    # ==================== 文件编码处理 ====================
    def read_file_with_encoding(self, file_path):
        """智能读取文件，自动检测编码"""
        if not os.path.exists(file_path):
            return ""

        # 按优先级尝试不同编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1']

        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        # 如果都失败，使用二进制模式并忽略错误
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')

    def write_file_with_encoding(self, file_path, content):
        """写入文件，统一使用UTF-8"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # ==================== 下拉框设置 ====================
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

    # ==================== 配置文件操作 ====================
    def on_action_menu_clicked(self, index):
        """打开配置文件对话框"""
        cw = UIConfigDialog(self)
        cw.tabWidget.setCurrentIndex(index)
        try:
            # 确保config目录存在
            config_dir = self.application_path + '/config'
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # 处理 service 文件 - 使用智能读取
            service_file = config_dir + '/service'
            if os.path.exists(service_file):
                content = self.read_file_with_encoding(service_file)
                cw.textEdit.setText(content)
            else:
                self.write_file_with_encoding(service_file, '')

            # 处理 master_account 文件
            master_file = config_dir + '/master_account'
            if os.path.exists(master_file):
                content = self.read_file_with_encoding(master_file)
                cw.textEdit_2.setText(content)
            else:
                self.write_file_with_encoding(master_file, '')

            # 处理 from_account 文件
            from_file = config_dir + '/from_account'
            if os.path.exists(from_file):
                content = self.read_file_with_encoding(from_file)
                cw.textEdit_3.setText(content)
            else:
                self.write_file_with_encoding(from_file, '')

        except Exception as e:
            QMessageBox.warning(self, "警告", f"配置文件处理失败：{str(e)}")

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
        pass

    def on_master_accounts_changed(self, selected_items):
        """主账号选中状态改变"""
        pass

    # ==================== 数据加载 ====================
    def load_combo_data(self):
        """加载下拉框数据"""
        # 确保 config 目录存在
        config_dir = os.path.join(self.application_path, 'config')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 加载从账号到 check_combo_from
        from_account_file = os.path.join(config_dir, 'from_account')
        if os.path.exists(from_account_file):
            try:
                content = self.read_file_with_encoding(from_account_file)
                accounts = [line.strip() for line in content.splitlines() if line.strip()]
                self.check_combo_from.clear()
                if accounts:
                    self.check_combo_from.addItems(accounts)
            except Exception as e:
                print(f"读取从账号配置失败: {e}")
                self.check_combo_from.clear()
        else:
            # 文件不存在，创建空文件
            self.write_file_with_encoding(from_account_file, '')
            self.check_combo_from.clear()

        # 加载主账号到 check_combo_master
        master_account_file = os.path.join(config_dir, 'master_account')
        if os.path.exists(master_account_file):
            try:
                content = self.read_file_with_encoding(master_account_file)
                accounts = [line.strip() for line in content.splitlines() if line.strip()]
                self.check_combo_master.clear()
                if accounts:
                    self.check_combo_master.addItems(accounts)
                    # 默认全选
                    self.check_combo_master.selectAll()
            except Exception as e:
                print(f"读取主账号配置失败: {e}")
                self.check_combo_master.clear()
        else:
            # 文件不存在，创建空文件
            self.write_file_with_encoding(master_account_file, '')
            self.check_combo_master.clear()

    def get_selected_from_accounts(self):
        """获取选中的从账号"""
        return self.check_combo_from.checkedItems()

    def get_selected_master_accounts(self):
        """获取选中的主账号"""
        return self.check_combo_master.checkedItems()

    def on_selection_changed(self):
        """选择状态改变时触发（单选/多选都会触发）"""
        if self.listWidget.currentItem():
            self.set_table(self.W.data_dict[self.listWidget.currentItem().text()].values)

    # ==================== 数据生成 ====================
    @pyqtSlot()
    def on_pushButton_generate_data_clicked(self):
        try:
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
            start_date = date1.toString("yyyy-MM-dd")
            end_date = date2.toString("yyyy-MM-dd")

            if date1 > date2:
                QMessageBox.warning(self, "警告", "开始时间应小于结束时间")
                return

            config_dir = os.path.join(self.application_path, 'config')
            service_file = os.path.join(config_dir, 'service')

            if os.path.exists(service_file):
                try:
                    content = self.read_file_with_encoding(service_file)
                    resource_ip_list = []

                    for line in content.splitlines():
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
                        if reply == QMessageBox.Ok:
                            self.on_action_menu_clicked(0)
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
                    return
            else:
                reply = QMessageBox.warning(self, "提示",
                                            "服务配置文件不存在，请先配置服务器",
                                            QMessageBox.Ok | QMessageBox.Cancel)
                if reply == QMessageBox.Ok:
                    self.on_action_menu_clicked(0)
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("请稍候")
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

            # 更新列表
            self.listWidget.clear()
            for key, value in self.W.data_dict.items():
                font = QFont()
                font.setPointSize(14)
                item = QListWidgetItem(key)
                item.setFont(font)
                self.listWidget.addItem(item)

            # 设置列表宽度
            if self.listWidget.count() > 0:
                max_width = self.listWidget.sizeHintForColumn(0)
                self.listWidget.setMinimumWidth(max_width + 30)
                self.label_8.setMinimumWidth(max_width + 30)

            # 默认第一页数据
            if self.W.data_dict:
                self.listWidget.setCurrentRow(0)
                self.set_table(self.W.data_dict[next(iter(self.W.data_dict))].values)

            dialog.close()
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"崩溃详情：{error_detail}")
            QMessageBox.critical(self, "错误",
                             f"程序发生错误：\n{str(e)}\n\n"
                             f"{error_detail}")

    # ==================== 表格操作 ====================
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
                'original_text': item.text,
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

        # 8. 设置交替行颜色
        self.tableWidget.setAlternatingRowColors(True)

        # 9. 设置选择行为
        self.tableWidget.setSelectionBehavior(self.tableWidget.SelectRows)
        self.tableWidget.setSelectionMode(self.tableWidget.SingleSelection)

        return headers

    def clean_header_text(self, text):
        """清理表头文本"""
        cleaned = text.replace('\n', ' ')
        if len(cleaned) > 20:
            cleaned = cleaned[:20] + "..."
        return cleaned

    def populate_data_rows(self, headers, data_list):
        """填充数据行 - 二维数组版本"""
        self.tableWidget.setEditTriggers(self.tableWidget.NoEditTriggers)
        row_count = len(data_list)
        self.tableWidget.setRowCount(row_count)

        if self.tableWidget.columnCount() == 0:
            self.tableWidget.setColumnCount(len(headers))

        for row, row_data in enumerate(data_list):
            for col, cell_value in enumerate(row_data):
                if col < self.tableWidget.columnCount():
                    item = QTableWidgetItem(str(cell_value))

                    if isinstance(cell_value, (int, float)):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    elif isinstance(cell_value, str):
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)

                    self.tableWidget.setItem(row, col, item)

        self.tableWidget.resizeColumnsToContents()

    def apply_header_item_style(self, header_item, style):
        """应用表头项样式"""
        font_config = style.font
        font = QFont()
        font.setFamily(font_config.name)
        font.setPointSize(font_config.size)
        font.setBold(True)

        header_item.setFont(font)

        if font_config.color:
            try:
                color = QColor(font_config.color)
                header_item.setForeground(QBrush(color))
            except:
                pass

        fill_config = style.fill
        if fill_config.color != '#ffffff':
            try:
                bg_color = QColor(fill_config.color)
                header_item.setBackground(QBrush(bg_color))
            except:
                pass

    # ==================== 导出功能 ====================
    @pyqtSlot()
    def on_exportButton_clicked(self):
        if self.tableWidget.rowCount() == 0:
            QMessageBox.warning(self, "提示", "请先生成数据！")
            return

        table_name = "数据表"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{table_name}_{timestamp}.xlsx"
        default_path = os.path.join(os.path.expanduser("~/Downloads"), default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文件",
            default_path,
            "Excel文件 (*.xlsx);;CSV文件 (*.csv);;所有文件 (*.*)"
        )

        if file_path:
            try:
                if file_path.endswith('.xlsx'):
                    self.export(file_path)
                elif file_path.endswith('.csv'):
                    self.export(file_path)
                else:
                    if not file_path.endswith('.xlsx'):
                        file_path += '.xlsx'
                    self.export(file_path)
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"错误: {str(e)}")

    def export(self, file_path):
        progress_dialog = QProgressDialog("正在导出...", "取消", 0, 100, self)
        progress_dialog.setWindowTitle("导出进度")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.show()
        QApplication.processEvents()

        is_cancelled = False

        def progress_callback(progress: int, status: str):
            nonlocal is_cancelled
            if progress_dialog.wasCanceled():
                is_cancelled = True
                return False
            progress_dialog.setValue(progress)
            QApplication.processEvents()
            return True

        try:
            self.W.export(file_path, progress_callback=progress_callback)

            if is_cancelled:
                QMessageBox.information(self, "导出取消", "导出操作已被用户取消")
            else:
                QMessageBox.information(self, "导出成功", f"文件已保存到:\n{file_path}")

        except Exception as e:
            if not is_cancelled:
                QMessageBox.critical(self, "错误", str(e))
        finally:
            progress_dialog.close()


def get_application_path():
    """获取应用程序路径 - 跨平台兼容版本"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            if sys.platform == 'win32':
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path


if __name__ == '__main__':
    app = QApplication(sys.argv)
    setup_chinese_messagebox()
    dlg = UIMainWindow()
    dlg.show()
    app.exec_()