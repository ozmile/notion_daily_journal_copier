import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
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

    def _convert_rich_text(self, rich_text: List[Dict]) -> List[Dict]:
        """link_mentionをテキストリンクに変換"""
        converted = []
        for text in rich_text:
            if text['type'] == 'mention' and text['mention']['type'] == 'link_mention':
                # Notion API を介してデータを操作する際、リンクメンションをそのまま扱うと、
                # 期待通りに表示されない場合があるので、リンクメンションをテキストに変換
                converted.append({
                    'type': 'text',
                    'text': {
                        'content': text['plain_text'],
                        'link': {'url': text['href']}
                    },
                    'annotations': text.get('annotations', {}),
                    'plain_text': text['plain_text']
                })
            else:
                converted.append(text)
        return converted

    def copy_blocks(self, block_id: str, target_block_id: str):
        """ブロックを再帰的にコピー"""
        blocks = self.notion.blocks.children.list(block_id)

        for block in blocks['results']:
            block_type = block['type']
            block_content = block[block_type].copy()

            if 'rich_text' in block_content:
                block_content['rich_text'] = self._convert_rich_text(block_content['rich_text'])

            new_block = {
                "object": "block",
                "type": block_type,
                block_type: block_content
            }

            created_block = self.notion.blocks.children.append(
                block_id=target_block_id,
                children=[new_block]
            )

            if block.get('has_children'):
                self.copy_blocks(block['id'], created_block['results'][0]['id'])

    def duplicate_page(self, source_page: Dict, target_date: datetime) -> Optional[Dict]:
        """ページを丸ごと複製"""
        try:
            # ソースページの完全な情報を取得
            page_content = self.notion.pages.retrieve(source_page['id'])
            logger.info(f"ソースページ取得: {page_content['id']}")

            # 新しいページのプロパティを準備
            today = datetime.now()
            date_str = today.strftime('%Y-%m-%d')
            new_properties = page_content['properties'].copy()
            new_properties['タイトル']['title'][0]['text']['content'] = f"Daily Journal"
            new_properties['作成日']['date']['start'] = date_str
            new_properties['タイトル']['title'][1]['mention']['date']['start'] = date_str

            # 新しいページを作成
            new_page = self.notion.pages.create(
                parent={"database_id": self.database_id},
                properties=new_properties,
                icon=page_content.get('icon'),
                cover=page_content.get('cover')
            )
            logger.info(f"新規ページ作成: {new_page['id']}")

            # ブロックの複製処理を実行
            self.copy_blocks(page_content['id'], new_page['id'])
            logger.info("ブロックの複製が完了しました")

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
