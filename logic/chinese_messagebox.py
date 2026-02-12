from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

def setup_chinese_messagebox():
    """全局设置消息框为中文"""

    def create_chinese_messagebox(icon, title, text, buttons, default_button, parent):
        msg_box = QMessageBox(icon, title, text, QMessageBox.NoButton, parent)

        # 按钮映射
        btn_map = {
            QMessageBox.Ok: ("确定", QMessageBox.AcceptRole),
            QMessageBox.Cancel: ("取消", QMessageBox.RejectRole),
            QMessageBox.Yes: ("是", QMessageBox.YesRole),
            QMessageBox.No: ("否", QMessageBox.NoRole),
            QMessageBox.Save: ("保存", QMessageBox.AcceptRole),
            QMessageBox.Open: ("打开", QMessageBox.AcceptRole),
            QMessageBox.Close: ("关闭", QMessageBox.RejectRole),
            QMessageBox.Apply: ("应用", QMessageBox.ApplyRole),
            QMessageBox.Reset: ("重置", QMessageBox.ResetRole),
            QMessageBox.Help: ("帮助", QMessageBox.HelpRole),
            QMessageBox.Abort: ("中止", QMessageBox.RejectRole),
            QMessageBox.Retry: ("重试", QMessageBox.AcceptRole),
            QMessageBox.Ignore: ("忽略", QMessageBox.AcceptRole),
        }

        added_buttons = {}
        for btn_type, (btn_text, btn_role) in btn_map.items():
            if buttons & btn_type:
                button = msg_box.addButton(btn_text, btn_role)
                added_buttons[btn_type] = button

        if default_button in added_buttons:
            msg_box.setDefaultButton(added_buttons[default_button])

        msg_box.exec_()

        clicked = msg_box.clickedButton()
        for btn_type, button in added_buttons.items():
            if clicked == button:
                return btn_type
        return QMessageBox.Cancel

    # 替换静态方法
    QMessageBox.warning = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
        create_chinese_messagebox(QMessageBox.Warning, title, text, buttons, defaultButton, parent)
    )

    QMessageBox.information = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
        create_chinese_messagebox(QMessageBox.Information, title, text, buttons, defaultButton, parent)
    )

    QMessageBox.critical = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Ok, defaultButton=QMessageBox.NoButton:
        create_chinese_messagebox(QMessageBox.Critical, title, text, buttons, defaultButton, parent)
    )

    QMessageBox.question = staticmethod(
        lambda parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, defaultButton=QMessageBox.NoButton:
        create_chinese_messagebox(QMessageBox.Question, title, text, buttons, defaultButton, parent)
    )