import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv
from notion_client import Client, APIResponseError
from typing import Optional, Dict, List, Any

# .env の環境変数を読み込む
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NotionConfig:
    api_key: str
    database_id: str

class NotionError(Exception):
    """Notionの操作に関するカスタムエラー"""
    pass

class NotionJournalManager:
    def __init__(self, config: Optional[NotionConfig] = None):
        if config is None:
            api_key = os.environ.get("NOTION_API_KEY")
            database_id = os.environ.get("NOTION_DAILY_JOURNAL_DATABASE_ID")

            if not api_key or not database_id:
                raise NotionError("環境変数が設定されていません")

            self.config = NotionConfig(api_key, database_id)
        else:
            self.config = config

        self.client = Client(auth=self.config.api_key)

    def get_page_by_date(self, target_date: datetime) -> Optional[Dict[str, Any]]:
        """指定日付のページを取得"""
        date_str = target_date.strftime('%Y-%m-%d')
        try:
            response = self.client.databases.query(
                database_id=self.config.database_id,
                filter={
                    "property": "日付",
                    "date": {"equals": date_str}
                },
                page_size=1,
                sorts=[{"property": "日付", "direction": "descending"}]
            )
            return response['results'][0] if response.get('results') else None

        except APIResponseError as e:
            logger.error(f"APIエラー: {e}")
            return None

    def create_page(self, properties: Dict[str, Any], icon: Optional[Dict] = None,
                   cover: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """新規ページを作成"""
        try:
            return self.client.pages.create(
                parent={"database_id": self.config.database_id},
                properties=properties,
                icon=icon,
                cover=cover
            )
        except APIResponseError as e:
            logger.error(f"ページ作成エラー: {e}")
            return None

    # Notion API を介してデータを操作する際、リンクメンションをそのまま扱うと、
    # 期待通りに表示されない場合があるので、リンクメンションをlink形式に変換
    def _convert_rich_text(self, rich_text: List[Dict]) -> List[Dict]:
        converted = []
        for text in rich_text:
            if text['type'] == 'mention' and text['mention']['type'] == 'link_mention':
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

    def copy_blocks(self, source_id: str, target_id: str, batch_size: int = 100) -> bool:
        """ブロックを再帰的に複製"""
        try:
            # すべてのブロックを一度に取得
            blocks_buffer = []
            has_more = True
            start_cursor = None

            while has_more:
                response = self.client.blocks.children.list(
                    block_id=source_id,
                    start_cursor=start_cursor,
                    page_size=batch_size
                )
                blocks_buffer.extend(response['results'])
                has_more = response.get('has_more', False)
                start_cursor = response.get('next_cursor')

            # バッチ処理用の新しいブロックを準備
            new_blocks = []
            for block in blocks_buffer:
                block_type = block['type']
                block_content = block[block_type].copy()

                # リッチテキストの変換
                if 'rich_text' in block_content:
                    block_content['rich_text'] = self._convert_rich_text(block_content['rich_text'])

                new_blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: block_content
                })

            # バッチでブロックを追加
            created_blocks = []
            for i in range(0, len(new_blocks), batch_size):
                batch = new_blocks[i:i + batch_size]
                response = self.client.blocks.children.append(
                    block_id=target_id,
                    children=batch
                )
                created_blocks.extend(response['results'])

            # 子ブロックを持つものを再帰的に処理
            for source_block, created_block in zip(blocks_buffer, created_blocks):
                if source_block.get('has_children'):
                    self.copy_blocks(
                        source_block['id'],
                        created_block['id'],
                        batch_size=batch_size
                    )

            return True

        except APIResponseError as e:
            logger.error(f"ブロックコピーエラー: {e}")
            return False

    def duplicate_daily_journal(self) -> Optional[Dict[str, Any]]:
        """日報を複製"""
        try:
            yesterday = datetime.now() - timedelta(days=1)
            source_page = self.get_page_by_date(yesterday)

            if not source_page:
                logger.info("前日のページが見つかりません")
                return None

            page_content = self.client.pages.retrieve(source_page['id'])

            # プロパティの更新
            date_str = datetime.now().strftime('%Y-%m-%d')
            new_properties = page_content['properties'].copy()
            new_properties['タイトル']['title'][0]['text']['content'] = "Daily Journal"
            new_properties['日付']['date']['start'] = date_str
            new_properties['タイトル']['title'][1]['mention']['date']['start'] = date_str

            # 新規ページ作成
            new_page = self.create_page(
                properties=new_properties,
                icon=page_content.get('icon'),
                cover=page_content.get('cover')
            )

            if new_page and self.copy_blocks(page_content['id'], new_page['id']):
                logger.info(f"日報を複製しました: {new_page['id']}")
                return new_page

            return None

        except Exception as e:
            logger.error(f"日報複製エラー: {e}")
            return None

def main():
    try:
        manager = NotionJournalManager()
        if manager.duplicate_daily_journal():
            logger.info("日報の複製が完了しました")
    except NotionError as e:
        logger.error(f"初期化エラー: {e}")
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}")

if __name__ == '__main__':
    main()
