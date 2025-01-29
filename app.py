import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from notion_client import Client, APIResponseError

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NotionJournalManager:
    def __init__(self):
        self.api_key = os.environ.get("NOTION_API_KEY")
        self.database_id = os.environ.get("NOTION_DAILY_JOURNAL_DATABASE_ID")

        if not self.api_key or not self.database_id:
            logger.error("Environment variables are not set.")
            raise ValueError("Environment variables are not set.")

        self.notion = Client(auth=self.api_key)

    def get_page_by_date(self, target_date: datetime) -> Optional[Dict]:
        """Retrieve the page for the specified date."""
        date_str = target_date.strftime('%Y-%m-%d')
        query_params = {
            "database_id": self.database_id,
            "filter": {
                "property": "作成日",
                "date": {
                    "equals": date_str
                }
            },
            "page_size": 1,
            "sorts": [{
                "property": "作成日",
                "direction": "descending"
            }]
        }

        try:
            response = self.notion.databases.query(**query_params)
            if 'results' in response and response['results']:
                return response['results'][0]
            else:
                logger.warning("No results found for the specified date.")
                return None
        except APIResponseError as e:
            logger.error(f"API response error: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None

    def duplicate_page(self, source_page: Dict, target_date: datetime) -> Optional[Dict]:
        """ページを複製して新しい日付で作成"""
        try:
            # 既存ページのコンテンツを取得
            source_blocks = self.notion.blocks.children.list(source_page['id'])

            # 新しいページを作成
            date_str = target_date.strftime('%Y-%m-%d')
            new_page = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "タイトル": {
                        "title": [{"text": {"content": f"Daily Journal {date_str}"}}]
                    },
                    "作成日": {
                        "date": {"start": date_str}
                    }
                }
            )

            # コンテンツをコピー
            if 'results' in source_blocks:
                for block in source_blocks['results']:
                    # ブロックタイプとコンテンツを保持
                    block_data = {
                        "object": "block",
                        "type": block['type'],
                        block['type']: block[block['type']]
                    }
                    # 新しいページにブロックを追加
                    self.notion.blocks.children.append(
                        block_id=new_page['id'],
                        children=[block_data]
                    )
                logger.info("コンテンツを複製しました")

            return new_page

        except Exception as e:
            logger.error(f"ページの複製中にエラーが発生: {e}")
            return None

if __name__ == '__main__':
    manager = NotionJournalManager()
    yesterday = datetime.now() - timedelta(days=1)
    source_page = manager.get_page_by_date(yesterday)

    if source_page:
        new_page = manager.duplicate_page(source_page, datetime.now())
        if new_page:
            logger.info("ページを複製しました")
    else:
        logger.info("No page found for today.")
