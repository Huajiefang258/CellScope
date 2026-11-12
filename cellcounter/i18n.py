"""Small runtime Chinese/English localiser.

The application is authored in Chinese.  Static widget texts are translated by
walking the widget tree; dynamically updated labels are translated by a small
timer (see MainWindow).  Keeping the translations in one table makes it easy to
add another language later.
"""

from __future__ import annotations

import re

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QAbstractButton, QAction, QComboBox, QDoubleSpinBox, QGroupBox, QLabel,
    QLineEdit, QListWidget, QMenu, QSpinBox, QTabWidget, QTableWidget, QWidget,
)

SETTINGS_ORG = "CellScope"
SETTINGS_APP = "CellScope"
SETTINGS_KEY = "ui/language"

ZH = "zh"
EN = "en"
_ZH = ZH
_EN = EN
_language = _ZH


def _read_language() -> str:
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    value = str(s.value(SETTINGS_KEY, _ZH))
    return value if value in (_ZH, _EN) else _ZH


def get_language() -> str:
    return _language


def set_language(language: str) -> None:
    global _language
    _language = language if language in (_ZH, _EN) else _ZH
    s = QSettings(SETTINGS_ORG, SETTINGS_APP)
    s.setValue(SETTINGS_KEY, _language)
    s.sync()


_language = _read_language()


# Static interface strings.  Keys are the Chinese source strings.
_EN_TEXT = {
    # -- results dialog
    "ImageJ 面积测量结果": "ImageJ area results",
    "ImageJ 测量完成": "ImageJ measurement complete",
    "细胞编号": "Cell #",
    "面积 ({unit})": "Area ({unit})",
    "打开 CSV": "Open CSV",
    "打开结果文件夹": "Open results folder",
    "关闭": "Close",
    # -- header / cards
    "CellScope · Cellpose + ImageJ 细胞计数": "CellScope · Cellpose + ImageJ cell counting",
    "Cellpose 自动标注 · 人工校正 · ImageJ 面积测量":
        "Cellpose segmentation · manual correction · ImageJ area measurement",
    "显示样式": "Display style",
    "打开非模态实时样式面板": "Open the non-modal live style panel",
    "批量处理": "Batch",
    "选择多张图像加入批量队列": "Add multiple images to the batch queue",
    "打开图像": "Open image",
    "打开 TIFF / PNG / JPEG 图像 (Ctrl+O)": "Open a TIFF / PNG / JPEG image (Ctrl+O)",
    "操作说明": "Help",
    "1 · 图像与显示": "1 · Image & display",
    "打开图像…    Ctrl+O": "Open image…    Ctrl+O",
    "尚未载入图像": "No image loaded",
    "复合显示": "Composite",
    "显示": "Display",
    "2 · Cellpose 自动标注": "2 · Cellpose segmentation",
    "推荐 cyto3；其他模型可在界面中下载后切换使用。":
        "cyto3 is recommended; other models can be downloaded in the app.",
    "模型": "Model",
    "自动（膜 / 通道 2）": "Auto (membrane / channel 2)",
    "分割来源": "Source",
    "自动": "Auto",
    "膜 / 通道 2": "Membrane / channel 2",
    "直径": "Diameter",
    "高级参数": "Advanced",
    "流阈值、细胞概率阈值、最小面积":
        "Flow threshold, cell probability, minimum area",
    "流阈值": "Flow threshold",
    "细胞概率": "Cell probability",
    "最小面积": "Min area",
    "运行 Cellpose 标注    Ctrl+R": "Run Cellpose    Ctrl+R",
    "模型会先检测细胞，再为每个细胞编号。":
        "Cellpose detects cells first, then numbers each cell.",
    "检查 / 下载当前模型": "Check / download current model",
    "模型不随程序打包；推荐下载 cyto3（快速、通用）。":
        "Models are not bundled; cyto3 is recommended (fast, general).",
    "3 · ImageJ 面积测量": "3 · ImageJ area measurement",
    "未校准（按像素²）": "Uncalibrated (px²)",
    "设置 1 像素对应的物理尺寸；0 表示按像素²测量。":
        "Physical size per pixel; 0 measures in px².",
    "手动标定…": "Calibrate…",
    "输入已知真实长度（如 20 µm），然后在图上点击两点":
        "Enter a known real length (e.g. 20 µm), then click two points",
    "像素尺寸": "Pixel size",
    "载入图像后自动设置": "Set automatically after loading",
    "选择": "Choose",
    "输出": "Output",
    "用 ImageJ 测量并导出    Ctrl+E": "Measure & export with ImageJ    Ctrl+E",
    "测量并导出表格    Ctrl+E": "Measure & export table    Ctrl+E",
    "导出标注图像…    Ctrl+Shift+E": "Export annotated image…    Ctrl+Shift+E",
    "测量并导出表格…": "Measure & export table…",
    "导出标注图像…": "Export annotated image…",
    "导出标注图像": "Export annotated image",
    "测量只导出 CSV 表格；标注图像和标签图请用上方按钮单独导出。":
        "Measurement exports only the CSV table; use the button above to export the annotated image and label map separately.",
    "PNG 图像 (*.png)": "PNG image (*.png)",
    "导出标注图像失败": "Could not export annotated image",
    "将输出标签图、CSV 表格与编号预览图。":
        "Exports a label image, CSV table and numbered preview.",
    "打开上次结果文件夹": "Open last results folder",
    "4 · 批量处理": "4 · Batch",
    "添加文件…": "Add files…",
    "清空": "Clear",
    "拖入图像或点击“添加文件”。": "Drop images here or click “Add files”.",
    # -- toolbar / mode
    "全部计数": "Count all",
    "模式一 · 自动全部计数": "Mode 1 · Count all automatically",
    "逐个确认": "Confirm one by one",
    "模式二 · 逐个确认计数": "Mode 2 · Confirm one by one",
    "撤销 (Ctrl+Z)": "Undo (Ctrl+Z)",
    "重做 (Ctrl+Y)": "Redo (Ctrl+Y)",
    "适应": "Fit",
    "适应窗口 (F)": "Fit window (F)",
    "编号": "Numbers",
    "显示已计数细胞的编号": "Show numbers of counted cells",
    "先打开一张图像，然后运行 Cellpose 自动标注。":
        "Open an image, then run Cellpose.",
    # -- right panel
    "计数概览": "Counts",
    "已计数细胞": "Counted cells",
    "尚未运行 Cellpose": "Cellpose not run yet",
    "已计数": "Counted",
    "未计数·自动": "Uncounted · auto",
    "未计数·手动": "Uncounted · manual",
    "当前模式": "Current mode",
    "全部设为已计数": "Set all counted",
    "按当前模式统一现有细胞的计数状态；不会删除标注，可撤销":
        "Unify the count state; labels are kept and the action can be undone",
    "随机选细胞…": "Random select…",
    "从候选细胞中空间均匀地随机选取指定数量":
        "Spatially uniform random selection from candidate cells",
    "面积 px²": "Area px²",
    "来源": "Source",
    "双击一行可定位到对应细胞。": "Double-click a row to locate the cell.",
    "运行 Cellpose 或手动绘制后，已计数细胞会显示在这里。":
        "Run Cellpose or draw a cell; counted cells will appear here.",
    "把多张图像拖到下方列表，自动排队标注。若当前没有打开图像，第一张完成后会自动载入；可以边校正边让其他图像继续在后台处理。每个文件使用加入队列时的 Cellpose 参数。":
        "Drop several images into the list to queue them automatically. If no image is open, the first finished result is loaded automatically; you can correct it while later images continue in the background. Each file uses the Cellpose settings captured when it was added.",
    # -- menus
    "打开图像…": "Open image…",
    "保存标注…": "Save labels…",
    "载入标注…": "Load labels…",
    "ImageJ 测量并导出…": "Measure & export with ImageJ…",
    "退出": "Quit",
    "撤销": "Undo",
    "重做": "Redo",
    "删除选中细胞": "Delete selected cells",
    "清除全部标注…": "Clear all labels…",
    "随机选细胞…（模式二）": "Random select… (Mode 2)",
    "全部设为已计数（模式一）": "Set all counted (Mode 1)",
    "全部设为未计数": "Set all uncounted",
    "全部设为未计数（模式二）": "Set all uncounted (Mode 2)",
    "适应窗口": "Fit window",
    "实际像素 1:1": "Actual pixels 1:1",
    "显示编号": "Show numbers",
    "授权信息": "License info",
    "关于 CellScope": "About CellScope",
    "文件": "File",
    "编辑": "Edit",
    "视图": "View",
    "帮助": "Help",
    "模式一 · 全部计数": "Mode 1 · Count all",
    "模式二 · 逐个确认": "Mode 2 · Confirm one by one",
    # -- common state
    "没有细胞": "No cells",
    "当前没有可操作的细胞。": "No cells available.",
    "未计数": "Uncounted",
    "手动": "Manual",
    "失败": "Failed",
    "排队": "Queued",
    "处理中…": "Processing…",
    "待校正": "Needs review",
    "校正中": "Reviewing",
    "已保存": "Saved",
    "启动…": "Starting…",
    "批量处理失败": "Batch processing failed",
    "没有结果": "No result",
    "该文件没有可用的自动标注结果。":
        "No automatic segmentation result is available for this file.",
    "未知错误": "Unknown error",
    "清空批量队列": "Clear batch queue",
    "已取消手动标定。": "Manual calibration cancelled.",
    "标定线太短，请重新标定。":
        "The calibration line is too short; please try again.",
    "校正为水平线": "Snap to horizontal",
    "是否校正为水平线来计算比例？": "Use the horizontal line to calculate the scale?",
    "校正为垂直线": "Snap to vertical",
    "是否校正为垂直线来计算比例？": "Use the vertical line to calculate the scale?",
    "（已校正为水平线）": " (snapped to horizontal)",
    "（已校正为垂直线）": " (snapped to vertical)",
    "手动标定比例": "Manual scale calibration",
    "已知真实长度（µm）：": "Known real length (µm):",
    "需要图像": "Image required",
    "请先打开一张图像。": "Please open an image first.",
    "已撤销。": "Undone.",
    "已重做。": "Redone.",
    "暂无标注": "No labels",
    "手动": "Manual",
    "灰度": "Grayscale",
    "复合图像": "Composite image",
    "无法打开图像": "Cannot open image",
    "请稍候": "Please wait",
    "模型正在下载中。": "The model is downloading.",
    "模型已就绪": "Model ready",
    "下载模型": "Download model",
    "准备下载模型…": "Preparing model download…",
    "正在下载模型…": "Downloading model…",
    "下载失败": "Download failed",
    "模型下载完成，可以运行 Cellpose。":
        "Model download complete; Cellpose can now run.",
    "模型下载完成。": "Model download complete.",
    "模型下载失败。": "Model download failed.",
    "模型下载失败": "Model download failed",
    "选择结果输出文件夹": "Choose result output folder",
    "请先打开图像并完成标注。": "Open an image and finish labelling first.",
    "没有已计数细胞": "No counted cells",
    "请先在模式一中运行 Cellpose，或在模式二中点击确认细胞。":
        "Run Cellpose in Mode 1, or confirm cells in Mode 2.",
    "找不到 ImageJ": "ImageJ not found",
    "准备测量失败": "Could not prepare measurement",
    "无法启动 ImageJ。": "Could not start ImageJ.",
    "已取消 ImageJ 测量。": "ImageJ measurement cancelled.",
    "ImageJ 没有返回测量结果。": "ImageJ returned no measurement result.",
    "ImageJ 测量失败": "ImageJ measurement failed",
    "保存结果失败": "Could not save results",
    "正在取消 ImageJ 测量…": "Cancelling ImageJ measurement…",
    "保存标注": "Save labels",
    "保存失败": "Save failed",
    "载入标注": "Load labels",
    "载入失败": "Load failed",
    "找不到原图": "Original image not found",
    "没有可保存的标注": "No labels to save",
    "当前没有细胞标注。": "There are no cell labels.",
    "清除全部标注": "Clear all labels",
    "确定删除全部细胞标注吗？此操作可以撤销。":
        "Delete all cell labels? This can be undone.",
    "已清除全部标注。": "All labels cleared.",
    "批量处理中": "Batch processing",
    "模型文件缺失，请点击“检查 / 下载模型”。":
        "Model files are missing; click “Check / download model”.",
    "Cellpose 运行失败": "Cellpose failed",
    "无法启动 Python worker，请检查 Python 环境。":
        "Could not start the Python worker; check the Python environment.",
    "已取消 Cellpose。": "Cellpose cancelled.",
    "Cellpose 未返回结果。": "Cellpose returned no result.",
    "正在取消 Cellpose…": "Cancelling Cellpose…",
    "已全部计数。": "All cells counted.",
    "请逐个点击确认。": "Confirm cells one by one.",
    # -- style dialog
    "点击选择颜色": "Click to choose a colour",
    "选择颜色": "Choose colour",
    "未计数 · 自动": "Uncounted · auto",
    "未计数 · 手动": "Uncounted · manual",
    "调整会立即生效；可以继续缩放、标注和操作主窗口。":
        "Changes apply immediately; you can keep zooming, labelling and using the main window.",
    "默认边缘和填充同色，取消联动后可分开设置；关闭后自动保存。":
        "Edge and fill share a colour by default; unlink them to set separately. Saved automatically on close.",
    "状态": "State",
    "边缘颜色": "Edge colour",
    "填充颜色": "Fill colour",
    "边缘和填充颜色联动（默认）": "Link edge and fill colours (default)",
    "填充细胞内部（关闭则只显示边缘）": "Fill cell interior (off = edge only)",
    "边缘透明度": "Edge opacity",
    "填充透明度": "Fill opacity",
    "边缘粗细": "Edge width",
    "提示：勾选“填充细胞内部”后才会显示半透明填充；边缘粗细按图像像素计算。":
        "Tip: translucent fill is shown only when “Fill cell interior” is on; edge width is in image pixels.",
    "恢复默认": "Restore defaults",
    # -- random dialog
    "随机选取细胞": "Randomly select cells",
    "使用加权最远点采样：随机选取，同时让细胞在空间上尽量分散。":
        "Weighted farthest-point sampling: random selection, spread spatially as much as possible.",
    "选取后先显示为蓝色，按 Enter 确认计数，Esc 取消。":
        "Selected cells are previewed in blue; press Enter to count, Esc to cancel.",
    "选取数量": "Number to select",
    " 个": " cells",
    "个": " cells",
    "只从未计数细胞中选取": "Only select from uncounted cells",
    "数量等于候选数时会全选；每次运行结果不同。确认计数前不会改变现有计数。":
        "If the number equals the candidates, all are selected. Results vary. Existing counts are unchanged until confirmed.",
    # -- models
    "cyto3 · 推荐（快速）": "cyto3 · recommended (fast)",
    "nuclei（v3 · 细胞核）": "nuclei (v3 · nuclei)",
    "Cellpose-SAM v2（v4 · 高精度 / 较慢）":
        "Cellpose-SAM v2 (v4 · high accuracy / slower)",
    "Cellpose-SAM v1（v4 · 旧版）": "Cellpose-SAM v1 (v4 · legacy)",
    "推荐：CPU 速度快、通用性好，适合大多数细胞。":
        "Recommended: fast on CPU and general-purpose for most cells.",
    "较旧的细胞模型，可用于对比。": "Older cell model for comparison.",
    "初代细胞模型，可用于对比。": "First-generation cell model for comparison.",
    "细胞核模型；请把“分割来源”改为 DAPI / 蓝色通道。":
        "Nuclei model; set Source to DAPI / blue channel.",
    "泛化能力最好，但 CPU 上明显更慢。":
        "Best generalisation, but noticeably slower on CPU.",
    "旧版 Cellpose-SAM，泛化能力较好。":
        "Legacy Cellpose-SAM with good generalisation.",
    # -- license
    "CellScope 授权": "CellScope license",
    "首次使用需要输入工具密钥；验证一次后，本机永久解锁。":
        "Enter the tool key on first use; this PC is permanently unlocked after verification.",
    "请输入工具密钥": "Enter tool key",
    "密钥只用于本机授权，不会上传到网络。":
        "The key is used only for local licensing and is never uploaded.",
    "解锁": "Unlock",
    "密钥不正确，请重新输入。": "Incorrect key; please try again.",
    "授权": "License",
    "本机已永久解锁": "Permanently unlocked on this PC",
    "未解锁": "Not unlocked",
    "打开一张 DAPI / WGS 图像\n或使用“文件 → 打开图像”":
        "Open a DAPI / WGS image\nor use File → Open image",
    "cyto2（v3）": "cyto2 (v3)",
    "cyto（v3）": "cyto (v3)",
    "图像文件": "Image files",
    "所有文件": "All files",
    "CellScope 标注": "CellScope labels",
    "添加到批量处理": "Add to batch",
    "没有候选细胞": "No candidate cells",
    "当前没有可选取的细胞。": "No selectable cells.",
    "随机选取": "Random selection",
    "随机选取功能仅在模式二（逐个确认）中可用。":
        "Random selection is only available in Mode 2.",
    "请先运行 Cellpose 或手动绘制细胞。":
        "Run Cellpose or draw a cell first.",
    "按 Enter 确认计数，按 Esc 取消。":
        "Press Enter to count, Esc to cancel.",
    "随机选取：按 Enter 确认计数，按 Esc 取消。":
        "Random selection: Enter to count, Esc to cancel.",
    "已取消随机计数。": "Random count cancelled.",
    "自动 · 膜 / 通道 2": "Auto · Membrane / channel 2",
    "红 (R)": "Red (R)",
    "绿 (G)": "Green (G)",
    "蓝 (B)": "Blue (B)",
    "红 (R) · 灰度": "Red (R) · grayscale",
    "绿 (G) · 灰度": "Green (G) · grayscale",
    "蓝 (B) · 灰度": "Blue (B) · grayscale",
    "红 (R) · 单通道": "Red (R) · single channel",
    "绿 (G) · 单通道": "Green (G) · single channel",
    "蓝 (B) · 单通道": "Blue (B) · single channel",
    "自动 · 红 (R)": "Auto · Red (R)",
    "自动 · 绿 (G)": "Auto · Green (G)",
    "自动 · 蓝 (B)": "Auto · Blue (B)",
    "已添加手动标注": "Manual cell added",
    "绘制区域太小": "Drawing area is too small",
    "已切换计数状态": "Count state changed",
    "已取消计数": "Count cancelled",
    "框选范围内没有细胞": "No cells in the box selection",
    "已全部计数。": "All cells counted.",
    "请逐个点击确认。": "Confirm cells one by one.",
    "模型文件缺失，请点击“检查 / 下载模型”。":
        "Model files are missing; click “Check / download model”.",
    "没有可保存的标注": "No labels to save",
    "当前没有细胞标注。": "There are no cell labels.",
    "选择结果输出文件夹": "Choose result output folder",
    "批量 Cellpose 失败": "Batch Cellpose failed",
    "无法启动批量 Cellpose worker。":
        "Could not start the batch Cellpose worker.",
    "该图像还在排队或处理中，请稍候。":
        "This image is still queued or processing; please wait.",
    "载入批量结果失败": "Could not load batch result",
    "清空所有批量任务（正在处理的会停止；已保存的标注不会删除，\n但将不再出现在批量列表中）。是否继续？":
        "Clear all batch tasks? Running tasks will stop. Saved labels are not deleted immediately but will no longer appear in the queue.",
    "批量 Cellpose 正在后台运行。请等待完成，或在批量列表清空任务后再手动运行。":
        "Batch Cellpose is running in the background. Wait for it to finish, or clear the batch list before running manually.",
    "CellScope 标注 (*.npz)": "CellScope labels (*.npz)",
    "已切换到模式一：标注和计数保留，无需重跑 Cellpose；可用“全部设为已计数”统一状态。":
        "Switched to Mode 1: labels and counts are kept; no need to re-run Cellpose. Use “Set all counted” to unify states.",
    "已切换到模式二：标注和计数保留，无需重跑 Cellpose；可用“全部设为未计数”统一状态。":
        "Switched to Mode 2: labels and counts are kept; no need to re-run Cellpose. Use “Set all uncounted” to unify states.",
    "正在启动 Cellpose worker…": "Starting Cellpose worker…",
    "Cellpose 正在运行，请稍候…": "Cellpose is running; please wait…",
    "无法启动 Cellpose worker。": "Could not start the Cellpose worker.",
    "正在启动 ImageJ…": "Starting ImageJ…",
    "ImageJ 正在计算每个细胞的面积…":
        "ImageJ is calculating each cell's area…",
    "授权状态：{status}": "License status: {status}",
    "机器码：{machine_code()}": "Machine code: {machine_code()}",
    "授权文件：{license_path()}": "License file: {license_path()}",
}


# Dynamic messages.  Each tuple: (Chinese regex, English replacement,
# English regex, Chinese replacement).  Numbers/paths are captured.
_PATTERNS = [
    (r"^已载入 (.+)。可以运行 Cellpose 自动标注。$",
     r"Loaded \1. Run Cellpose to annotate.",
     r"^Loaded (.+)\. Run Cellpose to annotate\.$",
     r"已载入 \1。可以运行 Cellpose 自动标注。"),
    (r"^已载入批量文件：(.+)$", r"Loaded batch file: \1",
     r"^Loaded batch file: (.+)$", r"已载入批量文件：\1"),
    (r"^手动标定：已知长度 (.+) µm。请在图像上点击两点；Esc 取消。$",
     r"Manual calibration: known length \1 µm. Click two points; Esc to cancel.",
     r"^Manual calibration: known length (.+) µm\. Click two points; Esc to cancel\.$",
     r"手动标定：已知长度 \1 µm。请在图像上点击两点；Esc 取消。"),
    (r"^比例已更新：(.*)$", r"Scale updated: \1",
     r"^Scale updated: (.*)$", r"比例已更新：\1"),
    (r"^已随机选中 (\d+) 个细胞（蓝色）。$",
     r"Selected \1 cells (blue preview).",
     r"^Selected (\d+) cells \(blue preview\)\.$",
     r"已随机选中 \1 个细胞（蓝色）。"),
    (r"(?s)^已随机选中 (\d+) 个细胞（蓝色）。\s*按 Enter 确认计数，按 Esc 取消。$",
     r"Selected \1 cells (blue). Press Enter to count, Esc to cancel.",
     r"(?s)^Selected (\d+) cells \(blue\)\. Press Enter to count, Esc to cancel\.$",
     r"已随机选中 \1 个细胞（蓝色）。按 Enter 确认计数，按 Esc 取消。"),
    (r"^已确认计数 (\d+) 个随机选取的细胞。$",
     r"Counted \1 randomly selected cells.",
     r"^Counted (\d+) randomly selected cells\.$",
     r"已确认计数 \1 个随机选取的细胞。"),
    (r"^(.+)  ·  (排队|处理中…|待校正|校正中|已保存|失败)(?:  \((\d+)/(\d+)\))?$",
     None, None, None),
    (r"^队列 (\d+) · 处理中 (\d+) · 待校正 (\d+) · 失败 (\d+)$",
     r"Queue \1 · processing \2 · to review \3 · failed \4",
     r"^Queue (\d+) · processing (\d+) · to review (\d+) · failed (\d+)$",
     r"队列 \1 · 处理中 \2 · 待校正 \3 · 失败 \4"),
    (r"^自动检出 (\d+) · 手动 (\d+)$",
     r"Auto \1 · manual \2",
     r"^Auto (\d+) · manual (\d+)$",
     r"自动检出 \1 · 手动 \2"),
    (r"^未计数 (\d+) · 共 (\d+)$",
     r"Uncounted \1 · total \2",
     r"^Uncounted (\d+) · total (\d+)$",
     r"未计数 \1 · 共 \2"),
    (r"^共 (\d+) · 计数 (\d+)$",
     r"Total \1 · counted \2",
     r"^Total (\d+) · counted (\d+)$",
     r"共 \1 · 计数 \2"),
    (r"^Cellpose 完成：(\d+) 个细胞。$",
     r"Cellpose complete: \1 cells.",
     r"^Cellpose complete: (\d+) cells\.$",
     r"Cellpose 完成：\1 个细胞。"),
    (r"^完成：(\d+) 个细胞 · (.+) · 直径 (.+)。$",
     r"Done: \1 cells · \2 · diameter \3.",
     r"^Done: (\d+) cells · (.+) · diameter (.+)\.$",
     r"完成：\1 个细胞 · \2 · 直径 \3。"),
    (r"^ImageJ 正在测量 (\d+) 个细胞…（headless）$",
     r"ImageJ measuring \1 cells… (headless)",
     r"^ImageJ measuring (\d+) cells… \(headless\)$",
     r"ImageJ 正在测量 \1 个细胞…（headless）"),
    (r"^完成：(\d+) 个细胞 · (.+)$",
     r"Done: \1 cells · \2",
     r"^Done: (\d+) cells · (.+)$",
     r"完成：\1 个细胞 · \2"),
    (r"^ImageJ 测量完成，已导出：(.+)$",
     r"ImageJ measurement complete; exported: \1",
     r"^ImageJ measurement complete; exported: (.+)$",
     r"ImageJ 测量完成，已导出：\1"),
    (r"^已将 (\d+) 个细胞设为(已计数|未计数)。$",
     r"Set \1 cells to \2.",
     r"^Set (\d+) cells to (Counted|Uncounted)\.$",
     r"已将 \1 个细胞设为\2。"),
    (r"^所有细胞已经是(已计数|未计数)状态。$",
     r"All cells are already \1.",
     r"^All cells are already (Counted|Uncounted)\.$",
     r"所有细胞已经是\1状态。"),
    (r"^已删除细胞 (\d+)$", r"Deleted cell \1",
     r"^Deleted cell (\d+)$", r"已删除细胞 \1"),
    (r"^已删除 (\d+) 个细胞$", r"Deleted \1 cells",
     r"^Deleted (\d+) cells$", r"已删除 \1 个细胞"),
    (r"^已取消 (\d+) 个细胞的计数$", r"Uncounted \1 cells",
     r"^Uncounted (\d+) cells$", r"已取消 \1 个细胞的计数"),
    (r"^已计数 (\d+) 个细胞$", r"Counted \1 cells",
     r"^Counted (\d+) cells$", r"已计数 \1 个细胞"),
    (r"^已保存标注：(.+)$", r"Labels saved: \1",
     r"^Labels saved: (.+)$", r"已保存标注：\1"),
    (r"^候选细胞：(\d+) 个（总细胞 (\d+)，未计数 (\d+)）$",
     r"Candidates: \1 (total \2, uncounted \3)",
     r"^Candidates: (\d+) \(total (\d+), uncounted (\d+)\)$",
     r"候选细胞：\1 个（总细胞 \2，未计数 \3）"),
    (r"^通道 (\d+)$", r"Channel \1",
     r"^Channel (\d+)$", r"通道 \1"),
    (r"^通道 (\d+) · 灰度$", r"Channel \1 · grayscale",
     r"^Channel (\d+) · grayscale$", r"通道 \1 · 灰度"),
    (r"^通道 (\d+) · 单通道$", r"Channel \1 · single channel",
     r"^Channel (\d+) · single channel$", r"通道 \1 · 单通道"),
    (r"^自动 · (.+)$", r"Auto · \1",
     r"^Auto · (.+)$", r"自动 · \1"),
    (r"^检查 / 下载 (.+)$", r"Check / download \1",
     r"^Check / download (.+)$", r"检查 / 下载 \1"),
    (r"(?s)^这条线与水平方向相差 (.*)°。\n是否校正为水平线来计算比例？$",
     r"The line is \1° from horizontal.\nSnap to horizontal for the calculation?",
     r"(?s)^The line is (.*)° from horizontal\.\nSnap to horizontal for the calculation\?$",
     r"这条线与水平方向相差 \1°。\n是否校正为水平线来计算比例？"),
    (r"(?s)^这条线与垂直方向相差 (.*)°。\n是否校正为垂直线来计算比例？$",
     r"The line is \1° from vertical.\nSnap to vertical for the calculation?",
     r"(?s)^The line is (.*)° from vertical\.\nSnap to vertical for the calculation\?$",
     r"这条线与垂直方向相差 \1°。\n是否校正为垂直线来计算比例？"),
    (r"^已计数 (\d+)$", r"Counted \1",
     r"^Counted (\d+)$", r"已计数 \1"),
    (r"^未计数 (\d+)$", r"Uncounted \1",
     r"^Uncounted (\d+)$", r"未计数 \1"),
    (r"^(\d+) 个$", r"\1 cells",
     r"^(\d+) cells$", r"\1 个"),
    (r"^\s*·\s*细胞 (\d+) · (已计数|未计数) · (自动|手动) · (.+) px²$",
     r"   ·   Cell \1 · \2 · \3 · \4 px²",
     r"^\s*·\s*Cell (\d+) · (Counted|Uncounted) · (Auto|Manual) · (.+) px²$",
     r"   ·   细胞 \1 · \2 · \3 · \4 px²"),
    (r"^加载 Cellpose 结果失败：(.+)$",
     r"Could not load Cellpose result: \1",
     r"^Could not load Cellpose result: (.+)$",
     r"加载 Cellpose 结果失败：\1"),
    (r"^已导出标注图像：(.+) · 标签文件：(.+)$",
     r"Annotated image exported: \1 · label file: \2",
     r"^Annotated image exported: (.+) · label file: (.+)$",
     r"已导出标注图像：\1 · 标签文件：\2"),
    (r"^已导出标注图像：(.+)$", r"Annotated image exported: \1",
     r"^Annotated image exported: (.+)$", r"已导出标注图像：\1"),
    (r"^面积 \((.+)\)$", r"Area (\1)",
     r"^Area \((.+)\)$", r"面积 (\1)"),
    (r"^缩放 (\d+)%$", r"Zoom \1%",
     r"^Zoom (\d+)%$", r"缩放 \1%"),
    (r"(?s)^自动检出 (\d+) · 手动 (\d+)\n未计数 (\d+) · 共 (\d+)$",
     r"Auto \1 · manual \2\nUncounted \3 · total \4",
     r"(?s)^Auto (\d+) · manual (\d+)\nUncounted (\d+) · total (\d+)$",
     r"自动检出 \1 · 手动 \2\n未计数 \3 · 共 \4"),
    (r"^已载入标注：(.+)$", r"Labels loaded: \1",
     r"^Labels loaded: (.+)$", r"已载入标注：\1"),
    (r"^自动 · (.+) · 灰度$", r"Auto · \1 · grayscale",
     r"^Auto · (.+) · grayscale$", r"自动 · \1 · 灰度"),
    (r"^(.+) · 灰度$", r"\1 · grayscale",
     r"^(.+) · grayscale$", r"\1 · 灰度"),
    (r"^(.+) · 单通道$", r"\1 · single channel",
     r"^(.+) · single channel$", r"\1 · 单通道"),
]


def _translate_direction(text: str, to_english: bool) -> str:
    if not text:
        return text
    if to_english:
        if text in _EN_TEXT:
            return _EN_TEXT[text]
        for zh_re, en_repl, _en_re, _zh_repl in _PATTERNS:
            if en_repl is None:
                m = re.fullmatch(zh_re, text)
                if m:
                    return _translate_batch_item(text)
                continue
            m = re.fullmatch(zh_re, text)
            if m:
                return m.expand(en_repl)
        if text.startswith("队列 ") and "\n" in text:
            first, rest = text.split("\n", 1)
            m = re.fullmatch(
                r"队列 (\d+) · 处理中 (\d+) · 待校正 (\d+) · 失败 (\d+)", first)
            if m:
                return (f"Queue {m.group(1)} · processing {m.group(2)} · "
                        f"to review {m.group(3)} · failed {m.group(4)}\n{rest}")
    else:
        reverse = {v: k for k, v in _EN_TEXT.items()}
        if text in reverse:
            return reverse[text]
        for _zh_re, _en_repl, en_re, zh_repl in _PATTERNS:
            if zh_repl is None:
                restored = _restore_batch_item(text)
                if restored is not None:
                    return restored
                continue
            m = re.fullmatch(en_re, text)
            if m:
                return m.expand(zh_repl)
    return text


def _translate_batch_item(text: str) -> str:
    m = re.fullmatch(
        r"(.+)  ·  (排队|处理中…|待校正|校正中|已保存|失败)(?:  \((\d+)/(\d+)\))?",
        text)
    if not m:
        return text
    status = {
        "排队": "Queued", "处理中…": "Processing…", "待校正": "Needs review",
        "校正中": "Reviewing", "已保存": "Saved", "失败": "Failed",
    }[m.group(2)]
    out = f"{m.group(1)}  ·  {status}"
    if m.group(3) is not None:
        out += f"  ({m.group(3)}/{m.group(4)})"
    return out


def _restore_batch_item(text: str):
    m = re.fullmatch(
        r"(.+)  ·  (Queued|Processing…|Needs review|Reviewing|Saved|Failed)(?:  \((\d+)/(\d+)\))?",
        text)
    if not m:
        return None
    status = {
        "Queued": "排队", "Processing…": "处理中…", "Needs review": "待校正",
        "Reviewing": "校正中", "Saved": "已保存", "Failed": "失败",
    }[m.group(2)]
    out = f"{m.group(1)}  ·  {status}"
    if m.group(3) is not None:
        out += f"  ({m.group(3)}/{m.group(4)})"
    return out


def translate(text: str) -> str:
    if _language == _EN:
        return _translate_direction(text, True)
    return _translate_direction(text, False)


def _set_text(widget, new: str):
    if new != widget.text():
        widget.setText(new)


def localize_tree(root) -> None:
    if root is None:
        return
    widgets = []
    if isinstance(root, QWidget):
        widgets.append(root)
        widgets.extend(root.findChildren(QWidget))
    for widget in widgets:
        try:
            title = widget.windowTitle()
            new_title = translate(title)
            if new_title != title:
                widget.setWindowTitle(new_title)
            if isinstance(widget, QMenu):
                menu_title = widget.title()
                new_menu_title = translate(menu_title)
                if new_menu_title != menu_title:
                    widget.setTitle(new_menu_title)
            if isinstance(widget, (QLabel, QAbstractButton, QGroupBox)):
                _set_text(widget, translate(widget.text()))
            if isinstance(widget, QLineEdit):
                placeholder = widget.placeholderText()
                new_ph = translate(placeholder)
                if new_ph != placeholder:
                    widget.setPlaceholderText(new_ph)
            if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                special = widget.specialValueText()
                new_special = translate(special)
                if new_special != special:
                    widget.setSpecialValueText(new_special)
                suffix = widget.suffix()
                new_suffix = translate(suffix)
                if new_suffix != suffix:
                    widget.setSuffix(new_suffix)
            if isinstance(widget, QComboBox):
                for i in range(widget.count()):
                    text = widget.itemText(i)
                    new = translate(text)
                    if new != text:
                        widget.setItemText(i, new)
            if isinstance(widget, QTableWidget):
                for col in range(widget.columnCount()):
                    item = widget.horizontalHeaderItem(col)
                    if item is not None:
                        new = translate(item.text())
                        if new != item.text():
                            item.setText(new)
                for row in range(widget.rowCount()):
                    for col in range(widget.columnCount()):
                        item = widget.item(row, col)
                        if item is not None:
                            new = translate(item.text())
                            if new != item.text():
                                item.setText(new)
            if isinstance(widget, QListWidget):
                for i in range(widget.count()):
                    item = widget.item(i)
                    if item is not None:
                        new = translate(item.text())
                        if new != item.text():
                            item.setText(new)
            if isinstance(widget, QTabWidget):
                for i in range(widget.count()):
                    new = translate(widget.tabText(i))
                    if new != widget.tabText(i):
                        widget.setTabText(i, new)
            tip = widget.toolTip()
            new_tip = translate(tip)
            if new_tip != tip:
                widget.setToolTip(new_tip)
        except (AttributeError, RuntimeError):
            continue
    for action in root.findChildren(QAction):
        try:
            text = action.text()
            new = translate(text)
            if new != text:
                action.setText(new)
            tip = action.toolTip()
            new_tip = translate(tip)
            if new_tip != tip:
                action.setToolTip(new_tip)
        except (AttributeError, RuntimeError):
            continue
