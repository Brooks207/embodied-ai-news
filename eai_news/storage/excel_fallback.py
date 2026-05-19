"""
本地 Excel 降级存储
当飞书未配置或写入失败时自动使用
"""
from datetime import datetime
from pathlib import Path

import openpyxl
from loguru import logger

from ..models import NewsItem, CATEGORY_LABELS_ZH

COLUMNS = ["时间", "新闻链接", "发布者", "中文标题", "分类", "相关性评分"]


class ExcelStorage:
    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)

    def _get_or_create_wb(self):
        if self.excel_path.exists():
            wb = openpyxl.load_workbook(self.excel_path)
        else:
            self.excel_path.parent.mkdir(parents=True, exist_ok=True)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "新闻"
            ws.append(COLUMNS)
            wb.save(self.excel_path)
        return wb

    def save_news_item(self, item: NewsItem):
        wb = self._get_or_create_wb()
        ws = wb["新闻"]

        ts = item.published_at or item.created_at
        time_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
        category_label = CATEGORY_LABELS_ZH.get(item.category, "其他")
        title_display = item.title_zh or item.title

        ws.append([
            time_str,
            item.url,
            item.source_name,
            title_display,
            category_label,
            item.relevance_score,
        ])
        wb.save(self.excel_path)
        logger.debug(f"[Excel] saved: {item.title[:60]}")

    def save_batch(self, items: list[NewsItem]):
        if not items:
            return
        wb = self._get_or_create_wb()
        ws = wb["新闻"]
        for item in items:
            ts = item.published_at or item.created_at
            time_str = ts.strftime("%Y-%m-%d %H:%M") if ts else ""
            ws.append([
                time_str,
                item.url,
                item.source_name,
                item.title_zh or item.title,
                CATEGORY_LABELS_ZH.get(item.category, "其他"),
                item.relevance_score,
            ])
        wb.save(self.excel_path)
        logger.info(f"[Excel] saved {len(items)} items to {self.excel_path}")
