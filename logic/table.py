import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union, Tuple, TYPE_CHECKING, Callable
from enum import Enum
import pandas as pd
import xlsxwriter
from datetime import datetime
import os
import json,time
import inspect
from functools import wraps

# 条件导入，用于类型提示
if TYPE_CHECKING:
    from xlsxwriter.workbook import Workbook
    from xlsxwriter.worksheet import Worksheet
else:
    # 运行时使用占位符
    Workbook = Any
    Worksheet = Any


# ==================== 进度管理相关 ====================

def progress_callback_decorator(func):
    """进度回调装饰器，正确处理回调返回值"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()

        sig = inspect.signature(func)
        bound_args = sig.bind(self, *args, **kwargs)
        bound_args.apply_defaults()
        # 从参数中提取进度回调函数
        progress_callback = bound_args.arguments.get('progress_callback')

        # 情况1: 没有回调函数 - 打印详细信息
        if progress_callback is None:
            print(f"{'='*50}")
            print(f"开始执行: {func.__name__}")
            print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")

            # 创建一个打印到控制台的回调，并记录是否继续
            should_continue = True

            def console_callback(progress: int, status: str):
                nonlocal should_continue
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] [进度 {progress:3d}%] {status}")
                # 控制台回调总是返回True，表示继续
                return True

            progress_callback = console_callback
            progress_manager = ProgressManager(progress_callback)
            kwargs['progress_manager'] = progress_manager

            try:
                result = func(self, *args, **kwargs)
                elapsed_time = time.time() - start_time
                progress_manager.finish()

                print(f"{'='*50}")
                print(f"执行完成: {func.__name__}")
                print(f"耗时: {elapsed_time:.2f} 秒")
                print(f"完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*50}")

                return result

            except Exception as e:
                elapsed_time = time.time() - start_time
                print(f"{'='*50}")
                print(f"执行失败: {func.__name__}")
                print(f"错误: {e}")
                print(f"耗时: {elapsed_time:.2f} 秒")
                print(f"{'='*50}")

                progress_manager.error(str(e))
                raise

            finally:
                progress_manager.cleanup()

        # 情况2: 有回调函数 - 不打印，只执行回调并处理返回值
        else:
            # 创建进度管理器
            progress_manager = ProgressManager(progress_callback)
            kwargs['progress_manager'] = progress_manager

            try:
                # 执行原函数
                result = func(self, *args, **kwargs)
                progress_manager.finish()
                return result

            except Exception as e:
                progress_manager.error(str(e))
                raise

            finally:
                progress_manager.cleanup()

    return wrapper


class ProgressManager:
    """进度管理器，带详细日志"""

    def __init__(self, callback: Callable[[int, str], None]):
        """
        初始化进度管理器
        """
        self.callback = callback
        self.total_sheets = 0
        self.current_sheet = 0
        self.sheet_progress = 0
        self.is_cancelled = False
        self.start_time = time.time()
        self.last_update_time = self.start_time

    def start_export(self, total_sheets: int):
        """开始导出"""
        self.total_sheets = total_sheets
        self.current_sheet = 0
        self.sheet_progress = 0
        self.is_cancelled = False

        print(f"[INFO] 开始导出Excel文件")
        print(f"[INFO] 总共有 {total_sheets} 个sheet需要处理")
        self.update(0, "开始导出...")

    def start_sheet(self, sheet_name: str, sheet_index: int):
        """开始处理一个sheet"""
        if self.is_cancelled:
            print(f"[WARN] 操作已取消，跳过sheet: {sheet_name}")
            return False

        self.current_sheet = sheet_index
        self.sheet_progress = 0

        print(f"[INFO] 开始处理第 {sheet_index}/{self.total_sheets} 个sheet: {sheet_name}")

        # 计算整体进度
        if self.total_sheets > 0:
            base_progress = int((sheet_index - 1) / self.total_sheets * 100)
        else:
            base_progress = 0

        self.update(base_progress, f"正在处理: {sheet_name}")
        return True

    def update_sheet_progress(self, progress: int, status: str = None):
        """更新当前sheet的进度"""
        if self.is_cancelled:
            return False

        self.sheet_progress = min(max(progress, 0), 100)

        # 计算整体进度
        if self.total_sheets > 0:
            # 每个sheet的权重
            sheet_weight = 100 / self.total_sheets
            # 当前sheet的进度在整体进度中的贡献
            sheet_contribution = int(self.sheet_progress * sheet_weight / 100)
            # 之前sheet的基础进度
            base_progress = int((self.current_sheet - 1) / self.total_sheets * 100)
            # 整体进度
            overall_progress = min(base_progress + sheet_contribution, 100)
        else:
            overall_progress = self.sheet_progress

        message = status if status else f"处理进度: {progress}%"

        # 添加时间间隔，避免打印太频繁
        current_time = time.time()
        if current_time - self.last_update_time > 0.5 or overall_progress == 100:
            print(f"[PROGRESS] 整体进度: {overall_progress:3d}%, Sheet进度: {self.sheet_progress:3d}%, 状态: {message}")
            self.last_update_time = current_time

        return self.update(overall_progress, message)

    def update(self, progress: int, status: str):
        """更新进度"""
        try:
            # 回调函数可以返回False来取消操作
            result = self.callback(progress, status)
            if result is False:
                self.is_cancelled = True
                print("[WARN] 用户取消了导出操作")
            return True
        except Exception as e:
            print(f"[ERROR] 进度回调出错: {e}")
            return False

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True
        self.update(0, "操作已取消")
        print("[INFO] 导出操作被取消")

    def error(self, error_message: str):
        """报告错误"""
        print(f"[ERROR] 导出过程中发生错误: {error_message}")
        self.update(0, f"错误: {error_message}")

    def finish(self):
        """完成导出"""
        if not self.is_cancelled:
            elapsed_time = time.time() - self.start_time
            print(f"[INFO] 导出成功完成")
            print(f"[INFO] 总耗时: {elapsed_time:.2f} 秒")
            self.update(100, "导出完成")
        else:
            elapsed_time = time.time() - self.start_time
            print(f"[INFO] 导出被取消")
            print(f"[INFO] 已耗时: {elapsed_time:.2f} 秒")

    def cleanup(self):
        """清理资源"""
        print("[INFO] 进度管理器清理完成")


# ==================== 枚举定义 ====================

class HorizontalAlignment(Enum):
    """水平对齐"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"
    FILL = "fill"
    CENTER_ACROSS = "center_across"
    DISTRIBUTED = "distributed"


class VerticalAlignment(Enum):
    """垂直对齐"""
    TOP = "top"
    CENTER = "vcenter"
    BOTTOM = "bottom"
    JUSTIFY = "vjustify"
    DISTRIBUTED = "vdistributed"


class BorderStyle(Enum):
    """边框样式"""
    NONE = 0
    THIN = 1
    MEDIUM = 2
    DASHED = 3
    DOTTED = 4
    THICK = 5
    DOUBLE = 6
    HAIR = 7


class FontStyle(Enum):
    """字体样式"""
    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"


# ==================== 样式配置类 ====================

@dataclass
class BorderConfig:
    """边框配置"""
    style: BorderStyle = BorderStyle.THIN
    color: str = "#000000"  # 黑色

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style": self.style.value,
            "color": self.color
        }


@dataclass
class CellBorder:
    """单元格边框"""
    left: Optional[BorderConfig] = None
    right: Optional[BorderConfig] = None
    top: Optional[BorderConfig] = None
    bottom: Optional[BorderConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.left:
            result["left"] = self.left.to_dict()
        if self.right:
            result["right"] = self.right.to_dict()
        if self.top:
            result["top"] = self.top.to_dict()
        if self.bottom:
            result["bottom"] = self.bottom.to_dict()
        return result


@dataclass
class FontConfig:
    """字体配置"""
    name: str = "微软雅黑"
    size: int = 11
    color: str = "#000000"  # 黑色
    style: FontStyle = FontStyle.NORMAL
    underline: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
            "color": self.color,
            "style": self.style.value,
            "underline": self.underline
        }


@dataclass
class FillConfig:
    """填充配置"""
    color: str = "#FFFFFF"  # 白色
    pattern: str = "solid"  # solid, pattern_75, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color": self.color,
            "pattern": self.pattern
        }


@dataclass
class CellStyle:
    """单元格样式配置"""
    font: Optional[FontConfig] = None
    fill: Optional[FillConfig] = None
    border: Optional[CellBorder] = None
    horizontal: HorizontalAlignment = HorizontalAlignment.LEFT
    vertical: VerticalAlignment = VerticalAlignment.CENTER
    wrap_text: bool = False
    shrink_to_fit: bool = False
    rotation: int = 0  # 0-90度旋转
    indent: int = 0  # 缩进级别
    num_format: str = "General"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "horizontal": self.horizontal.value,
            "vertical": self.vertical.value,
            "wrap_text": self.wrap_text,
            "shrink_to_fit": self.shrink_to_fit,
            "rotation": self.rotation,
            "indent": self.indent,
            "num_format": self.num_format
        }

        if self.font:
            result["font"] = self.font.to_dict()
        if self.fill:
            result["fill"] = self.fill.to_dict()
        if self.border:
            result["border"] = self.border.to_dict()

        return result


# ==================== 表头配置类 ====================

@dataclass
class HeaderItem:
    """表头项"""
    text: str  # 显示文本
    row_span: int = 1  # 跨行数
    col_span: int = 1  # 跨列数
    style: Optional[CellStyle] = None  # 单独样式（优先于整体样式）

    def __post_init__(self):
        if self.row_span < 1:
            self.row_span = 1
        if self.col_span < 1:
            self.col_span = 1


@dataclass
class HeaderRow:
    """表头行"""
    items: List[HeaderItem]  # 该行的表头项
    height: int = 25  # 行高

    @property
    def item_count(self) -> int:
        """有效项目数（考虑col_span）"""
        return sum(item.col_span for item in self.items)


@dataclass
class HeaderConfig:
    """表头配置"""
    rows: List[HeaderRow]  # 多行表头
    overall_style: Optional[CellStyle] = None  # 整体样式
    merge_headers: bool = True  # 是否合并跨行跨列的单元格

    def __post_init__(self):
        """验证表头配置"""
        if not self.rows:
            raise ValueError("表头必须至少有一行")

        # 检查每行的项目数是否一致（考虑col_span）
        first_row_span = self.rows[0].item_count
        for i, row in enumerate(self.rows[1:], 1):
            if row.item_count != first_row_span:
                raise ValueError(f"第{i + 1}行的表头项跨列总数({row.item_count})与第一行({first_row_span})不一致")

    @property
    def row_count(self) -> int:
        """表头行数"""
        return len(self.rows)

    @property
    def col_count(self) -> int:
        """表头列数（考虑跨列）"""
        return self.rows[0].item_count if self.rows else 0

    def get_header_grid(self) -> List[List[Optional[Tuple[HeaderItem, int, int]]]]:
        """
        获取表头网格表示
        返回: List[List[Tuple[HeaderItem, row_index, col_index]]]
        """
        if not self.rows:
            return []

        # 初始化网格
        grid = [[None for _ in range(self.col_count)] for _ in range(self.row_count)]

        for row_idx, row in enumerate(self.rows):
            col_idx = 0
            for item in row.items:
                # 标记此单元格被占用
                for r in range(row_idx, min(row_idx + item.row_span, self.row_count)):
                    for c in range(col_idx, min(col_idx + item.col_span, self.col_count)):
                        if grid[r][c] is None:
                            grid[r][c] = (item, row_idx, col_idx)

                col_idx += item.col_span

        return grid


# ==================== 数据样式配置 ====================

@dataclass
class DataCellStyle:
    """数据单元格样式配置"""
    style: Optional[CellStyle] = None  # 单元格样式
    conditional_styles: List[Dict[str, Any]] = field(default_factory=list)  # 条件格式

    def add_conditional_style(self, condition: str, style: CellStyle,
                              formula: Optional[str] = None):
        """添加条件格式"""
        self.conditional_styles.append({
            "condition": condition,
            "style": style,
            "formula": formula
        })


@dataclass
class ColumnStyleConfig:
    """列样式配置"""
    column_name: str  # 列名
    default_style: Optional[CellStyle] = None  # 默认样式
    header_style: Optional[CellStyle] = None  # 该列的表头样式（覆盖整体样式）
    width: Optional[int] = None  # 列宽
    hidden: bool = False  # 是否隐藏列

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "width": self.width,
            "hidden": self.hidden
        }


@dataclass
class RowStyleConfig:
    """行样式配置"""
    row_index: int  # 行索引（0-based，相对于数据起始行）
    style: Optional[CellStyle] = None  # 整行样式
    height: Optional[int] = None  # 行高

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_index": self.row_index,
            "height": self.height
        }


@dataclass
class CellStyleConfig:
    """单元格样式配置"""
    row_index: int  # 行索引
    col_index: int  # 列索引
    style: CellStyle  # 单元格样式

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_index": self.row_index,
            "col_index": self.col_index
        }


# ==================== 表格配置类 ====================

@dataclass
class TableConfig:
    """表格配置"""
    name: str  # 表格名称
    header: HeaderConfig  # 表头配置
    data_columns: List[str]  # 数据列名（必须与表头列数匹配）

    # 样式配置
    column_styles: Dict[str, ColumnStyleConfig] = field(default_factory=dict)
    row_styles: Dict[int, RowStyleConfig] = field(default_factory=dict)
    cell_styles: Dict[Tuple[int, int], CellStyleConfig] = field(default_factory=dict)

    # 表格设置
    freeze_pane: Optional[str] = None  # 冻结窗格，如"A2"
    auto_filter: bool = True  # 是否启用自动筛选
    show_gridlines: bool = True  # 是否显示网格线
    zoom_scale: int = 100  # 缩放比例

    def __post_init__(self):
        """验证配置"""
        # 检查数据列数是否与表头列数匹配
        if len(self.data_columns) != self.header.col_count:
            raise ValueError(
                f"数据列数({len(self.data_columns)})与表头列数({self.header.col_count})不匹配"
            )

    def get_column_style(self, column_name: str) -> Optional[ColumnStyleConfig]:
        """获取列样式配置"""
        return self.column_styles.get(column_name)

    def get_row_style(self, row_index: int) -> Optional[RowStyleConfig]:
        """获取行样式配置"""
        return self.row_styles.get(row_index)

    def get_cell_style(self, row_index: int, col_index: int) -> Optional[CellStyleConfig]:
        """获取单元格样式配置"""
        return self.cell_styles.get((row_index, col_index))

    def copy(self, new_name: Optional[str] = None) -> 'TableConfig':
        """复制配置"""
        import copy

        new_config = TableConfig(
            name=new_name if new_name else self.name + "_copy",
            header=self.header,  # HeaderConfig是只读的，直接引用
            data_columns=self.data_columns.copy(),
            column_styles={k: ColumnStyleConfig(**v.__dict__)
                           for k, v in self.column_styles.items()},
            row_styles=self.row_styles.copy(),
            cell_styles=self.cell_styles.copy(),
            freeze_pane=self.freeze_pane,
            auto_filter=self.auto_filter,
            show_gridlines=self.show_gridlines,
            zoom_scale=self.zoom_scale
        )
        return new_config


# ==================== 多Sheet Excel表格类 ====================

@dataclass
class MultiSheetExcelTable:
    """支持多个sheet的Excel表格，可相同或不同表结构"""

    title: str  # 表格主标题
    sheet_configs: Dict[str, TableConfig]  # sheet名称 -> 表格配置
    sheet_data: Dict[str, pd.DataFrame]  # sheet名称 -> 数据

    # 样式缓存
    _style_cache: Dict[str, xlsxwriter.format.Format] = field(default_factory=dict, repr=False)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "created_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "sheet_count": 0
    })

    def __post_init__(self):
        """初始化验证"""
        # 验证每个sheet的数据与配置匹配
        for sheet_name, config in self.sheet_configs.items():
            data = self.sheet_data.get(sheet_name)
            if data is not None and not data.empty:
                # 检查DataFrame列名与配置是否匹配
                missing_columns = set(config.data_columns) - set(data.columns)
                if missing_columns:
                    raise ValueError(f"Sheet '{sheet_name}' DataFrame缺少配置的列: {missing_columns}")

                # 重新排序列以匹配配置顺序
                self.sheet_data[sheet_name] = data[config.data_columns]

        # 更新元数据
        self.metadata["sheet_count"] = len(self.sheet_configs)

    @classmethod
    def create_with_shared_config(
            cls,
            title: str,
            sheet_names: List[str],
            shared_config: TableConfig,
            data_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> 'MultiSheetExcelTable':
        """
        创建具有相同表结构的多个sheet

        Args:
            title: 表格标题
            sheet_names: sheet名称列表
            shared_config: 共享的表结构配置
            data_dict: 各sheet的数据字典（可选）
        """
        sheet_configs = {}
        sheet_data = {}

        for sheet_name in sheet_names:
            # 复制配置给每个sheet（保持独立）
            sheet_configs[sheet_name] = shared_config.copy(sheet_name)

            # 设置数据
            if data_dict and sheet_name in data_dict:
                sheet_data[sheet_name] = data_dict[sheet_name].copy()
            else:
                # 创建空的DataFrame
                sheet_data[sheet_name] = pd.DataFrame(columns=shared_config.data_columns)

        return cls(
            title=title,
            sheet_configs=sheet_configs,
            sheet_data=sheet_data
        )

    def add_sheet(
            self,
            sheet_name: str,
            config: TableConfig,
            data: Optional[pd.DataFrame] = None
    ):
        """添加一个sheet"""
        if sheet_name in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 已存在")

        self.sheet_configs[sheet_name] = config

        if data is not None and not data.empty:
            # 验证并重新排序列
            missing_columns = set(config.data_columns) - set(data.columns)
            if missing_columns:
                raise ValueError(f"DataFrame缺少配置的列: {missing_columns}")
            self.sheet_data[sheet_name] = data[config.data_columns]
        else:
            self.sheet_data[sheet_name] = pd.DataFrame(columns=config.data_columns)

        # 更新元数据
        self.metadata["sheet_count"] = len(self.sheet_configs)
        self.metadata["last_modified"] = datetime.now().isoformat()

    def remove_sheet(self, sheet_name: str):
        """删除一个sheet"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        del self.sheet_configs[sheet_name]
        if sheet_name in self.sheet_data:
            del self.sheet_data[sheet_name]

        # 更新元数据
        self.metadata["sheet_count"] = len(self.sheet_configs)

    def get_sheet_info(self, sheet_name: str) -> Dict[str, Any]:
        """获取sheet信息"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        config = self.sheet_configs[sheet_name]
        data = self.sheet_data.get(sheet_name, pd.DataFrame())

        return {
            'name': sheet_name,
            'config': config,
            'row_count': len(data),
            'col_count': len(config.data_columns),
            'data_columns': config.data_columns,
            'header_rows': config.header.row_count
        }

    def list_sheets(self) -> List[Dict[str, Any]]:
        """列出所有sheet信息"""
        sheets_info = []
        for sheet_name in self.sheet_configs.keys():
            sheets_info.append(self.get_sheet_info(sheet_name))
        return sheets_info

    # ========== 样式设置方法 ==========

    def set_sheet_column_style(self, sheet_name: str, column_name: str,
                               style: CellStyle, width: Optional[int] = None):
        """设置指定sheet的列样式"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        config = self.sheet_configs[sheet_name]
        column_style = config.column_styles.get(column_name, ColumnStyleConfig(column_name))
        column_style.default_style = style
        if width is not None:
            column_style.width = width
        config.column_styles[column_name] = column_style

    def set_sheet_row_style(self, sheet_name: str, row_index: int,
                            style: CellStyle, height: Optional[int] = None):
        """设置指定sheet的行样式"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        config = self.sheet_configs[sheet_name]
        row_style = config.row_styles.get(row_index, RowStyleConfig(row_index))
        row_style.style = style
        if height is not None:
            row_style.height = height
        config.row_styles[row_index] = row_style

    def set_sheet_cell_style(self, sheet_name: str, row_index: int,
                             col_index: int, style: CellStyle):
        """设置指定sheet的单元格样式"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        config = self.sheet_configs[sheet_name]
        config.cell_styles[(row_index, col_index)] = CellStyleConfig(
            row_index=row_index,
            col_index=col_index,
            style=style
        )

    def set_column_style_for_all_sheets(self, column_name: str,
                                        style: CellStyle, width: Optional[int] = None):
        """为所有sheet设置相同列的样式"""
        for sheet_name in self.sheet_configs.keys():
            self.set_sheet_column_style(sheet_name, column_name, style, width)

    # ========== 数据操作方法 ==========

    def update_sheet_data(self, sheet_name: str, data: pd.DataFrame):
        """更新指定sheet的数据"""
        if sheet_name not in self.sheet_configs:
            raise ValueError(f"Sheet '{sheet_name}' 不存在")

        config = self.sheet_configs[sheet_name]

        # 验证数据列
        missing_columns = set(config.data_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"DataFrame缺少配置的列: {missing_columns}")

        # 重新排序列并更新数据
        self.sheet_data[sheet_name] = data[config.data_columns]
        self.metadata["last_modified"] = datetime.now().isoformat()

    def get_sheet_data(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """获取指定sheet的数据"""
        return self.sheet_data.get(sheet_name)

    # ========== Excel输出方法 ==========

    @progress_callback_decorator
    def to_excel(self, output_path: str, include_index_sheet: bool = True,
                 progress_callback: Optional[Callable[[int, str], None]] = None,
                 progress_manager: Optional[ProgressManager] = None):
        """
        写入Excel文件，支持多个sheet，带进度回调

        Args:
            output_path: 输出文件路径
            include_index_sheet: 是否包含目录页
            progress_callback: 进度回调函数 (progress: int, status: str) -> None
            progress_manager: 进度管理器（通过装饰器自动传递）
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 通知开始导出
            if progress_manager:
                progress_manager.start_export(len(self.sheet_configs))
                if progress_manager.is_cancelled:
                    print("导出已取消")
                    return None

            # 创建Excel写入器，启用 nan_inf_to_errors 选项
            with pd.ExcelWriter(
                    output_path,
                    engine='xlsxwriter',
                    engine_kwargs={'options': {
                        'nan_inf_to_errors': True,  # 关键：处理NaN/INF值
                        'remove_timezone': True,
                        'strings_to_numbers': True,
                        'strings_to_formulas': False,
                        'strings_to_urls': False
                    }}
            ) as writer:
                workbook = writer.book

                # 为每个sheet写入数据
                for sheet_index, (sheet_name, config) in enumerate(self.sheet_configs.items(), 1):

                    # 通知开始处理当前sheet
                    if progress_manager:
                        if not progress_manager.start_sheet(sheet_name, sheet_index):
                            print(f"处理 {sheet_name} 时被取消")
                            break
                        if progress_manager.is_cancelled:
                            print("导出已取消")
                            break

                    data = self.sheet_data.get(sheet_name)

                    if data is None or data.empty:
                        # 如果数据为空，创建空DataFrame
                        data = pd.DataFrame(columns=config.data_columns)
                    else:
                        # 预处理数据，确保没有NaN/INF
                        if progress_manager:
                            progress_manager.update_sheet_progress(5, "预处理数据...")
                        data = self._preprocess_data(data.copy())

                    # 创建worksheet
                    worksheet = workbook.add_worksheet(sheet_name)

                    # 应用样式并写入数据，传递进度管理器
                    try:
                        self._apply_sheet_styles(
                            workbook, worksheet, config, data,
                            progress_manager=progress_manager
                        )
                    except Exception as e:
                        print(f"应用样式到sheet '{sheet_name}' 时出错: {e}")
                        # 创建空worksheet
                        worksheet = workbook.add_worksheet(sheet_name)
                        self._apply_sheet_styles(
                            workbook, worksheet, config,
                            pd.DataFrame(columns=config.data_columns),
                            progress_manager=progress_manager
                        )

                    # 保存worksheet引用到writer中
                    writer.sheets[sheet_name] = worksheet

                # 如果被取消，删除文件
                if progress_manager and progress_manager.is_cancelled:
                    writer.close()
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    print("导出已取消，文件已删除")
                    return None

                # 添加目录页（可选）
                if include_index_sheet:
                    try:
                        if progress_manager:
                            progress_manager.update(95, "创建目录页...")
                        self._add_index_sheet(workbook)
                    except Exception as e:
                        print(f"创建目录页时出错: {e}")

            print(f"✅ 文件已保存: {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            # 尝试使用更简单的保存方式
            return self._fallback_save(output_path, progress_manager)

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理数据，处理NaN和INF值"""
        if data.empty:
            return data

        # 复制数据以避免修改原数据
        processed_data = data.copy()

        for column in processed_data.columns:
            # 检查是否是数值列
            if pd.api.types.is_numeric_dtype(processed_data[column]):
                try:
                    # 处理INF值
                    mask_inf = np.isinf(processed_data[column])
                    if mask_inf.any():
                        # 替换INF为NaN
                        processed_data.loc[mask_inf, column] = np.nan

                    # 处理NaN值
                    processed_data[column] = processed_data[column].fillna('')

                except Exception as e:
                    print(f"处理列 '{column}' 时出错: {e}")
                    # 如果处理失败，转换为字符串
                    processed_data[column] = processed_data[column].astype(str)

        return processed_data

    def _apply_sheet_styles(
            self,
            workbook: Workbook,
            worksheet: Worksheet,
            config: TableConfig,
            data: pd.DataFrame,
            progress_manager: Optional[ProgressManager] = None
    ):
        """应用单个sheet的样式"""
        # 应用表格设置
        self._apply_table_settings(worksheet, config)

        if progress_manager:
            progress_manager.update_sheet_progress(10, "设置表格格式...")

        # 写入表头
        self._write_headers(workbook, worksheet, config)

        if progress_manager:
            progress_manager.update_sheet_progress(30, "写入表头...")

        # 写入数据
        self._write_data_safe(workbook, worksheet, config, data, progress_manager)

        if progress_manager:
            progress_manager.update_sheet_progress(95, "完成当前sheet...")

    def _apply_table_settings(
            self,
            worksheet: Worksheet,
            config: TableConfig
    ):
        """应用表格设置"""
        # 设置缩放比例
        worksheet.set_zoom(config.zoom_scale)

        # 设置是否显示网格线
        worksheet.hide_gridlines(not config.show_gridlines)

        # 设置冻结窗格
        if config.freeze_pane:
            worksheet.freeze_panes(config.freeze_pane)

    def _write_headers(
            self,
            workbook: Workbook,
            worksheet: Worksheet,
            config: TableConfig
    ):
        """写入多行表头"""
        global cell_format
        header_config = config.header
        grid = header_config.get_header_grid()

        # 写入表头内容并应用样式
        for row_idx in range(header_config.row_count):
            worksheet.set_row(row_idx, config.header.rows[row_idx].height)

            for col_idx in range(header_config.col_count):
                cell_info = grid[row_idx][col_idx]
                if cell_info:
                    item, start_row, start_col = cell_info

                    # 如果是跨行跨列单元格的起始位置，写入内容
                    if row_idx == start_row and col_idx == start_col:
                        # 获取样式（优先使用单项样式，其次整体样式）
                        style = item.style or header_config.overall_style

                        # 写入单元格
                        if style:
                            cell_format = self._create_cell_format(workbook, style)
                            worksheet.write(row_idx, col_idx, item.text, cell_format)
                        else:
                            worksheet.write(row_idx, col_idx, item.text)

                        # 合并单元格（如果需要）
                        if header_config.merge_headers and (item.row_span > 1 or item.col_span > 1):
                            end_row = min(start_row + item.row_span - 1, header_config.row_count - 1)
                            end_col = min(start_col + item.col_span - 1, header_config.col_count - 1)
                            if start_row != end_row or start_col != end_col:
                                worksheet.merge_range(
                                    start_row, start_col,
                                    end_row, end_col,
                                    item.text,
                                    cell_format if style else None
                                )

    def _write_data_safe(
            self,
            workbook: Workbook,
            worksheet: Worksheet,
            config: TableConfig,
            data: pd.DataFrame,
            progress_manager: Optional[ProgressManager] = None
    ):
        """安全的写入数据方法，带进度更新"""
        data_start_row = config.header.row_count

        # ========== 设置列宽 ==========
        if progress_manager:
            progress_manager.update_sheet_progress(35, "设置列宽...")

        for col_idx, column_name in enumerate(config.data_columns):
            column_style = config.get_column_style(column_name)
            width = column_style.width if column_style else 12

            # 根据列名长度自动调整宽度
            if width is None:
                # 使用列名长度
                width = max(len(str(column_name)), 12)
                # 或者可以检查数据的最大长度（如果有数据的话）
                if not data.empty and column_name in data.columns:
                    try:
                        # 计算该列数据的最大长度
                        max_data_len = data[column_name].astype(str).str.len().max()
                        width = max(width, int(max_data_len) + 2)  # 加2个字符的边距
                    except:
                        pass

            # 应用列宽
            worksheet.set_column(col_idx, col_idx, width)

            # 隐藏列（如果需要）
            if column_style and column_style.hidden:
                worksheet.set_column(col_idx, col_idx, None, None, {'hidden': True})

        # ========== 处理数据为空的情况 ==========
        if data.empty:
            print(f"数据为空，不写入数据行")
            return

        # ========== 检查并清理数据 ==========
        if progress_manager:
            progress_manager.update_sheet_progress(40, "预处理数据...")

        # 检查第一行是否是列名
        if len(data) > 0:
            first_row_values = data.iloc[0].tolist()
            column_names = config.data_columns

            # 比较第一行数据是否与列名匹配
            is_column_row = True
            for i in range(min(len(first_row_values), len(column_names))):
                if str(first_row_values[i]) != str(column_names[i]):
                    is_column_row = False
                    break

            # 如果是列名行，移除它
            if is_column_row:
                print(f"检测到第一行是列名，已移除: {first_row_values}")
                data = data.iloc[1:].reset_index(drop=True)

        # 如果处理后数据为空，直接返回
        if data.empty:
            print(f"处理后数据为空")
            return

        # ========== 写入数据行 ==========
        total_rows = len(data)

        for df_row_idx in range(total_rows):
            # 检查是否取消
            if progress_manager and progress_manager.is_cancelled:
                return

            excel_row_idx = data_start_row + df_row_idx

            # 设置行高
            row_style = config.get_row_style(df_row_idx)
            if row_style and row_style.height:
                worksheet.set_row(excel_row_idx, row_style.height)

            # 写入每一列
            row_data = data.iloc[df_row_idx]
            for col_idx, column_name in enumerate(config.data_columns):
                try:
                    # 获取单元格值
                    if column_name in data.columns:
                        cell_value = row_data[column_name]
                    else:
                        # 如果列名不在数据中，尝试按位置获取
                        cell_value = row_data.iloc[col_idx] if col_idx < len(row_data) else ''

                    # 安全处理cell_value
                    cell_value = self._safe_cell_value(cell_value)

                    # 获取单元格样式
                    cell_style = None

                    # 1. 检查单元格特定样式
                    cell_style_config = config.get_cell_style(df_row_idx, col_idx)
                    if cell_style_config:
                        cell_style = cell_style_config.style

                    # 2. 检查行样式
                    if cell_style is None and row_style and row_style.style:
                        cell_style = row_style.style

                    # 3. 检查列样式
                    if cell_style is None:
                        column_style = config.get_column_style(column_name)
                        if column_style and column_style.default_style:
                            cell_style = column_style.default_style

                    # 写入单元格
                    if cell_style:
                        cell_format = self._create_cell_format(workbook, cell_style)
                        worksheet.write(excel_row_idx, col_idx, cell_value, cell_format)
                    else:
                        worksheet.write(excel_row_idx, col_idx, cell_value)

                except Exception as e:
                    print(f"写入单元格 ({df_row_idx}, {col_idx}) 时出错: {e}")
                    worksheet.write(excel_row_idx, col_idx, '')

            # 每处理10行或每10%更新一次进度
            if progress_manager and (df_row_idx % 10 == 0 or df_row_idx == total_rows - 1):
                row_progress = int((df_row_idx + 1) / total_rows * 100 * 0.5)  # 写入数据占50%权重
                sheet_progress = 40 + row_progress  # 从40%开始
                progress_manager.update_sheet_progress(
                    min(sheet_progress, 90),
                    f"写入数据: {df_row_idx + 1}/{total_rows}"
                )

        # ========== 设置自动筛选 ==========
        if progress_manager:
            progress_manager.update_sheet_progress(92, "设置自动筛选...")

        if config.auto_filter and not data.empty:
            try:
                last_row = data_start_row + len(data) - 1
                last_col = len(config.data_columns) - 1
                worksheet.autofilter(data_start_row - 1, 0, last_row, last_col)
            except Exception as e:
                print(f"设置自动筛选时出错: {e}")

    def _safe_cell_value(self, value):
        """安全处理单元格值"""
        if value is None:
            return ''

        # 检查是否是NaN
        if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
            return ''

        # 检查是否是INF
        if isinstance(value, float) and (np.isinf(value) or value == float('inf') or value == float('-inf')):
            return ''

        # 检查是否是numpy类型
        if isinstance(value, (np.int64, np.float64)):
            return value.item()

        return value

    def _create_cell_format(
            self,
            workbook: xlsxwriter.Workbook,
            style: CellStyle
    ) -> xlsxwriter.format.Format:
        """创建单元格格式"""
        # 使用缓存
        style_key = json.dumps(style.to_dict(), sort_keys=True)
        if style_key in self._style_cache:
            return self._style_cache[style_key]

        format_dict = {}

        # 字体
        if style.font:
            font_dict = {}
            if style.font.name:
                font_dict['font_name'] = style.font.name
            if style.font.size:
                font_dict['font_size'] = style.font.size
            if style.font.color:
                font_dict['font_color'] = style.font.color
            if style.font.style == FontStyle.BOLD:
                font_dict['bold'] = True
            elif style.font.style == FontStyle.ITALIC:
                font_dict['italic'] = True
            elif style.font.style == FontStyle.BOLD_ITALIC:
                font_dict['bold'] = True
                font_dict['italic'] = True
            if style.font.underline:
                font_dict['underline'] = True

            format_dict.update(font_dict)

        # 填充
        if style.fill:
            format_dict['bg_color'] = style.fill.color
            if style.fill.pattern != 'solid':
                format_dict['pattern'] = style.fill.pattern

        # 对齐
        format_dict['align'] = style.horizontal.value
        format_dict['valign'] = style.vertical.value

        # 文本控制
        format_dict['text_wrap'] = style.wrap_text
        format_dict['shrink'] = style.shrink_to_fit

        # 旋转
        if style.rotation:
            format_dict['rotation'] = style.rotation

        # 缩进
        if style.indent:
            format_dict['indent'] = style.indent

        # 数字格式
        if style.num_format != "General":
            format_dict['num_format'] = style.num_format

        # 边框
        if style.border:
            border_props = {}
            if style.border.left:
                border_props['left'] = style.border.left.style.value
                border_props['left_color'] = style.border.left.color
            if style.border.right:
                border_props['right'] = style.border.right.style.value
                border_props['right_color'] = style.border.right.color
            if style.border.top:
                border_props['top'] = style.border.top.style.value
                border_props['top_color'] = style.border.top.color
            if style.border.bottom:
                border_props['bottom'] = style.border.bottom.style.value
                border_props['bottom_color'] = style.border.bottom.color

            format_dict.update(border_props)

        # 创建格式对象
        try:
            cell_format = workbook.add_format(format_dict)
            self._style_cache[style_key] = cell_format
            return cell_format
        except Exception as e:
            print(f"创建单元格格式时出错: {e}")
            # 返回默认格式
            return workbook.add_format()

    def _add_index_sheet(self, workbook: xlsxwriter.Workbook):
        """添加目录页"""
        worksheet = workbook.add_worksheet('目录')

        # 写入标题
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center'
        })
        worksheet.merge_range('A1:D1', f'表格目录 - {self.title}', title_format)

        # 写入表头
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })

        headers = ['序号', 'Sheet名称', '数据行数', '数据列数', '备注']
        for i, header in enumerate(headers):
            worksheet.write(2, i, header, header_format)

        # 写入sheet信息
        row = 3
        for i, (sheet_name, config) in enumerate(self.sheet_configs.items(), 1):
            data = self.sheet_data.get(sheet_name, pd.DataFrame())
            row_count = len(data)
            col_count = len(config.data_columns)

            worksheet.write(row, 0, i)
            worksheet.write(row, 1, sheet_name)
            worksheet.write(row, 2, row_count)
            worksheet.write(row, 3, col_count)

            # 备注信息
            remark = f"表头行数: {config.header.row_count}"
            if config.freeze_pane:
                remark += f", 冻结: {config.freeze_pane}"
            worksheet.write(row, 4, remark)

            # 添加超链接到对应sheet
            link_format = workbook.add_format({
                'font_color': 'blue',
                'underline': 1
            })
            worksheet.write_url(
                row, 1,
                f"internal:'{sheet_name}'!A1",
                link_format,
                sheet_name
            )

            row += 1

        # 设置列宽
        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 30)

    def _fallback_save(self, output_path: str,
                       progress_manager: Optional[ProgressManager] = None) -> Optional[str]:
        """备用保存方法，使用openpyxl引擎，带进度"""
        try:
            print("尝试使用openpyxl引擎保存...")

            if progress_manager:
                progress_manager.update(50, "使用备用引擎保存...")

            # 使用openpyxl引擎
            with pd.ExcelWriter(
                    output_path,
                    engine='openpyxl'
            ) as writer:
                total_sheets = len(self.sheet_configs)

                for sheet_index, (sheet_name, config) in enumerate(self.sheet_configs.items(), 1):
                    if progress_manager:
                        if progress_manager.is_cancelled:
                            break
                        sheet_progress = int((sheet_index / total_sheets) * 100)
                        progress_manager.update(sheet_progress, f"处理: {sheet_name}")

                    data = self.sheet_data.get(sheet_name)

                    if data is None or data.empty:
                        data = pd.DataFrame(columns=config.data_columns)
                    else:
                        data = self._preprocess_data(data.copy())

                    data.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )

            if progress_manager and progress_manager.is_cancelled:
                if os.path.exists(output_path):
                    os.remove(output_path)
                print("备用保存已取消")
                return None

            print(f"✅ 使用openpyxl引擎保存成功: {output_path}")

            if progress_manager:
                progress_manager.update(100, "备用引擎保存完成")

            return output_path

        except Exception as e:
            print(f"❌ 备用保存方法也失败: {e}")

            if progress_manager:
                progress_manager.update(0, f"保存失败: {e}")

            return None

class StyleBuilder:
    """样式构建器，简化样式创建"""

    @staticmethod
    def create_header_style(
            bg_color: str = "#4F81BD",
            font_color: str = "#FFFFFF",
            font_size: int = 11,
            border: bool = True,
            horizontal: HorizontalAlignment = HorizontalAlignment.LEFT,
            vertical: VerticalAlignment = VerticalAlignment.CENTER,
            font_style: FontStyle = FontStyle.NORMAL,
    ) -> CellStyle:
        """创建表头样式"""
        font_config = FontConfig(
            color=font_color,
            size=font_size,
            style=font_style
        )

        fill_config = FillConfig(color=bg_color)

        border_config = None
        if border:
            border_config = CellBorder(
                left=BorderConfig(BorderStyle.THIN, "#000000"),
                right=BorderConfig(BorderStyle.THIN, "#000000"),
                top=BorderConfig(BorderStyle.THIN, "#000000"),
                bottom=BorderConfig(BorderStyle.THIN, "#000000")
            )

        return CellStyle(
            font=font_config,
            fill=fill_config,
            border=border_config,
            horizontal=horizontal,
            vertical=vertical,
            wrap_text=True,
        )

    @staticmethod
    def create_data_style(
            font_color: str = "#000000",
            font_size: int = 10,
            alternate_bg: bool = False,
            row_index: Optional[int] = None
    ) -> CellStyle:
        """创建数据样式"""
        bg_color = "#F5F5F5" if alternate_bg and row_index and row_index % 2 == 1 else "#FFFFFF"

        font_config = FontConfig(
            color=font_color,
            size=font_size
        )

        fill_config = FillConfig(color=bg_color)

        border_config = CellBorder(
            bottom=BorderConfig(BorderStyle.THIN, "#E0E0E0")
        )

        return CellStyle(
            font=font_config,
            fill=fill_config,
            border=border_config,
            horizontal=HorizontalAlignment.LEFT,
            vertical=VerticalAlignment.CENTER
        )

    @staticmethod
    def create_number_style(
            num_format: str = "#,##0.00",
            font_color: str = "#000000",
            align: HorizontalAlignment = HorizontalAlignment.RIGHT
    ) -> CellStyle:
        """创建数字样式"""
        return CellStyle(
            font=FontConfig(color=font_color),
            horizontal=align,
            num_format=num_format
        )

    @staticmethod
    def create_currency_style(
            symbol: str = "¥",
            font_color: str = "#1B5E20",
            bold: bool = False
    ) -> CellStyle:
        """创建货币样式"""
        return CellStyle(
            font=FontConfig(
                color=font_color,
                style=FontStyle.BOLD if bold else FontStyle.NORMAL
            ),
            horizontal=HorizontalAlignment.RIGHT,
            num_format=f'{symbol}#,##0.00'
        )

    @staticmethod
    def create_percentage_style(
            font_color: str = "#0D47A1",
            bold: bool = False
    ) -> CellStyle:
        """创建百分比样式"""
        return CellStyle(
            font=FontConfig(
                color=font_color,
                style=FontStyle.BOLD if bold else FontStyle.NORMAL
            ),
            horizontal=HorizontalAlignment.RIGHT,
            num_format="0.00%"
        )

    @staticmethod
    def create_highlight_style(
            bg_color: str = "#FFF9C4",
            font_color: str = "#F57C00",
            bold: bool = True
    ) -> CellStyle:
        """创建高亮样式"""
        return CellStyle(
            font=FontConfig(
                color=font_color,
                style=FontStyle.BOLD if bold else FontStyle.NORMAL
            ),
            fill=FillConfig(color=bg_color),
            border=CellBorder(
                left=BorderConfig(BorderStyle.THIN, "#FFB74D"),
                right=BorderConfig(BorderStyle.THIN, "#FFB74D"),
                top=BorderConfig(BorderStyle.THIN, "#FFB74D"),
                bottom=BorderConfig(BorderStyle.THIN, "#FFB74D")
            )
        )


# ==================== 使用示例 ====================

def create_sales_report_example():
    """创建销售报表示例（相同表结构）"""

    # 1. 创建共享的表头配置
    header_rows = [
        HeaderRow(items=[
            HeaderItem(text="季度销售报表", col_span=4)
        ], height=30),
        HeaderRow(items=[
            HeaderItem(text="产品ID"),
            HeaderItem(text="产品名称"),
            HeaderItem(text="销售额"),
            HeaderItem(text="利润")
        ], height=25)
    ]

    header_config = HeaderConfig(
        rows=header_rows,
        overall_style=StyleBuilder.create_header_style()
    )

    # 2. 创建共享的表格配置
    shared_config = TableConfig(
        name="季度销售",  # 基础名称，会被复制时覆盖
        header=header_config,
        data_columns=["product_id", "product_name", "sales", "profit"]
    )

    # 3. 各季度数据
    quarterly_data = {
        "Q1": pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003'],
            'product_name': ['产品A', '产品B', '产品C'],
            'sales': [150000, 200000, 120000],
            'profit': [45000, 60000, 36000]
        }),
        "Q2": pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003', 'P004'],
            'product_name': ['产品A', '产品B', '产品C', '产品D'],
            'sales': [180000, 220000, 140000, 90000],
            'profit': [54000, 66000, 42000, 27000]
        }),
        "Q3": pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003'],
            'product_name': ['产品A', '产品B', '产品C'],
            'sales': [210000, 240000, 160000],
            'profit': [63000, 72000, 48000]
        }),
        "Q4": pd.DataFrame({
            'product_id': ['P001', 'P002', 'P003', 'P004'],
            'product_name': ['产品A', '产品B', '产品C', '产品D'],
            'sales': [240000, 280000, 180000, 120000],
            'profit': [72000, 84000, 54000, 36000]
        })
    }

    # 4. 创建多sheet表格
    multi_sheet_table = MultiSheetExcelTable.create_with_shared_config(
        title="2024年销售报表",
        sheet_names=["第一季度", "第二季度", "第三季度", "第四季度"],
        shared_config=shared_config,
        data_dict={
            "第一季度": quarterly_data["Q1"],
            "第二季度": quarterly_data["Q2"],
            "第三季度": quarterly_data["Q3"],
            "第四季度": quarterly_data["Q4"]
        }
    )

    # 5. 为各sheet设置样式
    for sheet_name in multi_sheet_table.sheet_configs.keys():
        # 设置数字列样式
        multi_sheet_table.set_sheet_column_style(
            sheet_name, "sales",
            StyleBuilder.create_number_style("#,##0"),
            width=15
        )
        multi_sheet_table.set_sheet_column_style(
            sheet_name, "profit",
            StyleBuilder.create_number_style("#,##0"),
            width=15
        )

    # 6. 生成Excel
    output_path = multi_sheet_table.to_excel("2024年季度销售报表.xlsx")
    print(f"生成文件: {output_path}")

    return multi_sheet_table


def create_mixed_structure_example():
    """创建混合表结构示例（不同表结构）"""

    # 1. 创建客户信息sheet配置
    customer_header = HeaderConfig(
        rows=[
            HeaderRow(items=[
                HeaderItem(text="客户信息表", col_span=4)
            ], height=30),
            HeaderRow(items=[
                HeaderItem(text="客户ID"),
                HeaderItem(text="客户名称"),
                HeaderItem(text="联系人"),
                HeaderItem(text="电话")
            ], height=25)
        ],
        overall_style=StyleBuilder.create_header_style("#2E7D32")
    )

    customer_config = TableConfig(
        name="客户信息",
        header=customer_header,
        data_columns=["customer_id", "customer_name", "contact", "phone"]
    )

    # 2. 创建订单信息sheet配置
    order_header = HeaderConfig(
        rows=[
            HeaderRow(items=[
                HeaderItem(text="订单信息表", col_span=6)
            ], height=30),
            HeaderRow(items=[
                HeaderItem(text="订单ID"),
                HeaderItem(text="客户ID"),
                HeaderItem(text="产品"),
                HeaderItem(text="数量"),
                HeaderItem(text="单价"),
                HeaderItem(text="总金额")
            ], height=25)
        ],
        overall_style=StyleBuilder.create_header_style("#1565C0")
    )

    order_config = TableConfig(
        name="订单信息",
        header=order_header,
        data_columns=["order_id", "customer_id", "product", "quantity", "price", "amount"]
    )

    # 3. 创建产品信息sheet配置
    product_header = HeaderConfig(
        rows=[
            HeaderRow(items=[
                HeaderItem(text="产品信息表", col_span=5)
            ], height=30),
            HeaderRow(items=[
                HeaderItem(text="产品ID"),
                HeaderItem(text="产品名称"),
                HeaderItem(text="类别"),
                HeaderItem(text="库存"),
                HeaderItem(text="单价")
            ], height=25)
        ],
        overall_style=StyleBuilder.create_header_style("#7B1FA2")
    )

    product_config = TableConfig(
        name="产品信息",
        header=product_header,
        data_columns=["product_id", "product_name", "category", "stock", "unit_price"]
    )

    # 4. 创建多sheet表格
    multi_sheet_table = MultiSheetExcelTable(
        title="业务管理系统数据",
        sheet_configs={},
        sheet_data={}
    )

    # 5. 添加不同表结构的sheet
    # 客户信息
    customer_data = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'customer_name': ['ABC公司', 'XYZ企业', 'DEF集团'],
        'contact': ['张三', '李四', '王五'],
        'phone': ['13800138001', '13800138002', '13800138003']
    })
    multi_sheet_table.add_sheet("客户信息", customer_config, customer_data)

    # 订单信息
    order_data = pd.DataFrame({
        'order_id': ['O001', 'O002', 'O003', 'O004'],
        'customer_id': ['C001', 'C002', 'C001', 'C003'],
        'product': ['产品A', '产品B', '产品C', '产品A'],
        'quantity': [10, 20, 15, 30],
        'price': [100.00, 150.00, 80.00, 100.00],
        'amount': [1000.00, 3000.00, 1200.00, 3000.00]
    })
    multi_sheet_table.add_sheet("订单信息", order_config, order_data)

    # 产品信息
    product_data = pd.DataFrame({
        'product_id': ['P001', 'P002', 'P003', 'P004'],
        'product_name': ['产品A', '产品B', '产品C', '产品D'],
        'category': ['电子产品', '家居用品', '办公用品', '食品饮料'],
        'stock': [100, 50, 200, 150],
        'unit_price': [100.00, 150.00, 80.00, 50.00]
    })
    multi_sheet_table.add_sheet("产品信息", product_config, product_data)

    # 6. 为各sheet设置不同的样式
    # 设置订单金额列样式
    multi_sheet_table.set_sheet_column_style(
        "订单信息", "amount",
        StyleBuilder.create_currency_style(bold=True),
        width=15
    )

    # 设置产品价格列样式
    multi_sheet_table.set_sheet_column_style(
        "产品信息", "unit_price",
        StyleBuilder.create_currency_style(),
        width=12
    )

    # 7. 添加一个汇总sheet（不同表结构）
    summary_header = HeaderConfig(
        rows=[
            HeaderRow(items=[
                HeaderItem(text="业务汇总表", col_span=4)
            ], height=30),
            HeaderRow(items=[
                HeaderItem(text="统计项"),
                HeaderItem(text="数量"),
                HeaderItem(text="总金额"),
                HeaderItem(text="备注")
            ], height=25)
        ],
        overall_style=StyleBuilder.create_header_style("#F57C00")
    )

    summary_config = TableConfig(
        name="业务汇总",
        header=summary_header,
        data_columns=["item", "count", "total_amount", "remark"]
    )

    summary_data = pd.DataFrame({
        'item': ['客户总数', '订单总数', '产品总数', '订单总金额'],
        'count': [3, 4, 4, None],
        'total_amount': [None, None, None, 8200.00],
        'remark': ['3家企业客户', '4笔订单', '4种产品', '¥8,200.00']
    })

    multi_sheet_table.add_sheet("业务汇总", summary_config, summary_data)

    # 8. 生成Excel
    output_path = multi_sheet_table.to_excel("业务管理系统.xlsx")
    print(f"生成文件: {output_path}")
    print(f"包含sheet: {list(multi_sheet_table.sheet_configs.keys())}")

    return multi_sheet_table


# ==================== 主执行 ====================

if __name__ == "__main__":
    print("=== 多Sheet Excel表格生成示例 ===")

    print("\n1. 创建相同表结构的销售报表...")
    sales_report = create_sales_report_example()

    print("\n2. 创建不同表结构的业务管理系统...")
    business_system = create_mixed_structure_example()

    print("\n所有示例完成！")
