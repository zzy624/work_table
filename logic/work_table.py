from datetime import datetime, timedelta
from .table import HeaderRow, HeaderItem, HeaderConfig, StyleBuilder, TableConfig, MultiSheetExcelTable, \
    HorizontalAlignment, ColumnStyleConfig, FontStyle
import pandas as pd
import os

class TableTemplates:
    @staticmethod
    def work_table() -> TableConfig:
        """财务报表模板"""

        header_rows = [
            HeaderRow(items=[
                HeaderItem(text='''【文件导入说明】：
    1、导入文件模版，前三行为模版固定内容，请勿删除，否则会影响导入数据内容；
    2、“*”必填项；无“*”红色字体为有条件必填字段，请仔细阅读填写说明；无“*”黑色字体为非必填字段
    3、系统通过“设备IP”查询设备信息时，4A侧存在多个设备的情况，即“设备IP”不能唯一确定“设备”，系统默认取第一个设备。为了准确定位设备信息，请用户填写导入信息时，尽量补充“设备名称”
    4、系统从账号批量临时申请导入时，由于系统需进行业务校验，因此为避免调用4A接口校验主账号及设备信息超时，建议用户单个导入文件的记录数不超过100条，如遇数量较大操作时，可分批次导入，即导入文件拆分为多个小批次文件操作。
    ''', col_span=11, style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color="#000000",
                                                             font_size=14, horizontal=HorizontalAlignment.LEFT,
                                                             )),
            ]),
            HeaderRow(items=[
                HeaderItem(text='''*归属资源池\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*设备IP\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*设备名称''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#000000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''数据库实例名''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#000000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*数据库类型\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''端口号''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#000000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*从账号名\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*当前归属主账号\n（有条件必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#3B80CB',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''申请归属主账号\n（有条件必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#3B80CB',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*授权开始时间\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
                HeaderItem(text='''*授权结束时间\n（必填）''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#ff0000',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.BOLD
                                                                  )),
            ], height=50),

            HeaderRow(items=[
                HeaderItem(text='''必填，填写归属资源池信息''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''必填，填写添加从账号的设备IP，系统将根据IP从4a系统中查询对应设备信息''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''非必填，可根据4a侧返回信息进行赋值''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''账号所属设备类型为“数据库”时，非必填，可根据此字段从4A系统查询对应设备信息''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''账号所属设备类型为“数据库”时，必填，需根据此字段查询对应设备信息''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''账号所属设备类型为“数据库”时，非必填，可根据此字段从4A系统查询对应设备信息''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''必填；填写需要添加的从账号名称''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(
                    text='''有条件必填，当业务类型选择主从授权延期申请时必填，用于查询设备信息，填写账号使用者的4a主账号名，IT公司移动用户必须输入主账号全称，如zhm@hq.cmcc''',
                    style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                           font_size=14,
                                                           horizontal=HorizontalAlignment.CENTER,
                                                           font_style=FontStyle.ITALIC
                                                           )),
                HeaderItem(
                    text='''当业务类型选择主从授权延期申请时非必填，当申请单业务类型为运维账号临时申请、程序账号临时申请、管理账号临时使用、超级账号临时使用或者程序账号授权报备时必填，填写账号使用者的4a主账号名，IT公司移动用户必须输入主账号全称，如zhm@hq.cmcc''',
                    style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                           font_size=14,
                                                           horizontal=HorizontalAlignment.CENTER,
                                                           font_style=FontStyle.ITALIC
                                                           )),
                HeaderItem(text='''必填，格式示例“2019-01-02 06:08:35”
    授权有效期开始时间业务限制：
    （1）主从授权的有效期必须在“归属主账号”的有效期内；''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
                HeaderItem(text='''必填，格式示例“2019-01-02 06:08:35”
    授权有效期结束时间业务限制：
    （3）对于程序账号的临时授权，请确保不超过8小时；而合作伙伴在临时使用涉及敏感权限时，授权期限不得超过30天。请按照业务限制要求设置授权结束时间以确保授权实施成功''',
                           style=StyleBuilder.create_header_style(bg_color='#ffffff', font_color='#827C7C',
                                                                  font_size=14,
                                                                  horizontal=HorizontalAlignment.CENTER,
                                                                  font_style=FontStyle.ITALIC
                                                                  )),
            ], height=300)
        ]

        return TableConfig(
            freeze_pane="A4",
            name="",
            header=HeaderConfig(
                rows=header_rows,
            ),
            data_columns=[
                "resource_pool", "ip", "name", "db_name", "db_type", "port", "from_account",
                "current_master_account",
                "apply_master_account", "start_time", "end_time"
            ],
            column_styles={
                "resource_pool": ColumnStyleConfig(column_name="resource_pool", width=15),
                "ip": ColumnStyleConfig(column_name="ip", width=16),
                "name": ColumnStyleConfig(column_name="name", width=16),
                "db_name": ColumnStyleConfig(column_name="db_name", width=20),
                "db_type": ColumnStyleConfig(column_name="db_type", width=20),
                "port": ColumnStyleConfig(column_name="port", width=12),
                "from_account": ColumnStyleConfig(column_name="from_account", width=20),
                "current_master_account": ColumnStyleConfig(column_name="current_master_account", width=30),
                "apply_master_account": ColumnStyleConfig(column_name="apply_master_account", width=30),
                "start_time": ColumnStyleConfig(column_name="start_time", width=30),
                "end_time": ColumnStyleConfig(column_name="end_time", width=30)
            }
        )


class WorkTable(object):

    def __init__(self):
        self.excel_table = None
        self.data_dict = None
        self.template_config = TableTemplates.work_table()
        self.header = self.template_config.header.rows[1]

    def template(self):
        """从模板配置创建表格"""
        # template_config =

        # self.header = template_config.header
        # data_dict = generate_february_sheets()

        sheet_names = list(self.data_dict.keys())
        # data = pd.DataFrame(columns=template_config.data_columns)

        # 4. 创建并保存
        self.excel_table = MultiSheetExcelTable.create_with_shared_config(
            title="",
            sheet_names=sheet_names,
            shared_config=self.template_config,
            data_dict=self.data_dict
        )

    def generate_timesheet_data(
            self,
            start_date: str,
            end_date: str,
            resource_ip_list: list,
            account_list: list,
            current_master_account_list: list,
            name_list: list = None,
            db_name_list: list = None,
            db_type_list: list = None,
            port_list: list = None,
            include_sheetname_prefix: bool = True
    ):
        """
        生成任意时间周期的工作表数据

        Args:
            start_date: 开始日期，格式如 "2026-02-01"
            end_date: 结束日期，格式如 "2026-02-28"
            resource_ip_list: 包含"资源池 IP"格式的列表
            account_list: from_account列表
            current_master_account_list: master_account列表
            name_list: 服务器名称列表（可选）
            db_name_list: 数据库名称列表（可选）
            db_type_list: 数据库类型列表（可选）
            port_list: 端口列表（可选）
            include_sheetname_prefix: 是否在sheet名称中包含月份前缀

        Returns:
            Dict[str, pd.DataFrame]: sheet名称 -> 数据DataFrame
        """
        # 定义三个时间段对应的时间
        time_slots = {
            "晨": {"start_hour": 0, "end_hour": 8},
            "昼": {"start_hour": 8, "end_hour": 16},
            "夜": {"start_hour": 16, "end_hour": 24}
        }

        # 解析日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # 计算天数
        delta_days = (end_dt - start_dt).days + 1

        print(f"日期范围: {start_date} 到 {end_date}")
        print(f"总天数: {delta_days}")
        print(f"资源池-IP数量: {len(resource_ip_list)}")
        print(f"from_account数量: {len(account_list)}")
        print(f"master_account数量: {len(current_master_account_list)}")

        # 计算理论行数
        total_rows = len(resource_ip_list) * len(account_list) * len(current_master_account_list)
        print(f"理论总行数（每个sheet）: {total_rows}")
        print(f"理论总数据量: {total_rows * delta_days * len(time_slots)} 行")

        data_dict = {}

        # 遍历每一天
        for day_offset in range(delta_days):
            current_date = start_dt + timedelta(days=day_offset)
            month = current_date.month
            day = current_date.day

            # 格式化日期字符串
            date_str_ymd = f"{current_date.year}-{month:02d}-{day:02d}"

            # 为每个时间段创建sheet
            for period_name, time_info in time_slots.items():
                # 生成sheet名称
                if include_sheetname_prefix:
                    sheet_name = f"{month}月{day}日{period_name}"
                else:
                    sheet_name = f"{day}日{period_name}"

                # 收集所有行的数据
                all_rows = []

                # 三层嵌套：resource_ip × account × master_account
                for resource_ip_idx, resource_ip in enumerate(resource_ip_list):
                    # 分割resource_pool和ip
                    parts = resource_ip.split()
                    if len(parts) > 1:
                        # 如果分割后有多个部分，最后一个作为IP，其余作为resource_pool
                        resource_pool = ' '.join(parts[:-1])
                        ip = parts[-1]
                    elif len(parts) == 1:
                        # 只有一个部分，整个作为resource_pool
                        resource_pool = parts[0]
                        ip = ""
                    else:
                        resource_pool = ""
                        ip = ""

                    # 获取对应的其他字段（使用循环索引）
                    # name = name_list[resource_ip_idx % len(name_list)]
                    # db_name = db_name_list[resource_ip_idx % len(db_name_list)]
                    # db_type = db_type_list[resource_ip_idx % len(db_type_list)]
                    # port = port_list[resource_ip_idx % len(port_list)]

                    for from_account in account_list:
                        for master_account in current_master_account_list:
                            # 构建时间
                            start_time = f"{date_str_ymd} {time_info['start_hour']:02d}:00:00"
                            end_time = f"{date_str_ymd} {time_info['end_hour']:02d}:00:00"

                            # 创建一行数据
                            row = {
                                "resource_pool": resource_pool,
                                "ip": ip,
                                "name": "",
                                "db_name": "",
                                "db_type": "",
                                "port": "",
                                "from_account": from_account,
                                "current_master_account": master_account,
                                "apply_master_account": master_account,
                                "start_time": start_time,
                                "end_time": end_time
                            }
                            all_rows.append(row)

                # 创建DataFrame
                data_dict[sheet_name] = pd.DataFrame(all_rows)

        print(f"共生成 {len(data_dict)} 个sheet")
        self.data_dict = data_dict

    def export(self, file_path: str, progress_callback=None):
        self.template()
        self.excel_table.to_excel(file_path, False, progress_callback)


if __name__ == '__main__':
    w = WorkTable()

    def my_callback(progress: int, status: str):
        print(f"我的回调: {progress}% - {status}")
        return True

    resource_ip_list = []
    from_account_list = []
    master_account_list = []
    try:
        # 获取当前文件的绝对路径的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 构建配置文件绝对路径
        service_file = os.path.join(current_dir, '..', 'config', 'service')
        from_account_file = os.path.join(current_dir, '..', 'config', 'from_account')
        master_account_file = os.path.join(current_dir, '..', 'config', 'master_account')

        # 加载配置文件
        with open(service_file, 'r', encoding='utf-8') as f:
            resource_ip_list = [line.strip() for line in f if line.strip()]
            print(f"加载服务器: {len(resource_ip_list)} 个")

        with open(from_account_file, 'r', encoding='utf-8') as f:
            from_account_list = [line.strip() for line in f if line.strip()]
            print(f"加载from_account: {len(from_account_list)} 个")

        with open(master_account_file, 'r', encoding='utf-8') as f:
            master_account_list = [line.strip() for line in f if line.strip()]
            print(f"加载master_account: {len(master_account_list)} 个")

    except FileNotFoundError as e:
        print(f"配置文件未找到: {e}")
    except Exception as e:
        print(f"加载配置文件出错: {e}")
    w.generate_timesheet_data(
        "2026-02-01",
        "2026-02-08",
        resource_ip_list,
        from_account_list,
        master_account_list
    )

    w.export("111.xlsx", progress_callback=my_callback)
