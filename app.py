"""
Notion日報管理ツール

Notionの日報データベースを操作し、前日の日報を複製するためのツール。
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any

from dotenv import load_dotenv
from notion_client import Client, APIResponseError

# 定数定義
class NotionProperty(str, Enum):
    """Notionプロパティ名の定数"""
    TITLE = "タイトル"
    DATE = "日付"

# 設定
DEFAULT_BATCH_SIZE = 100
DEFAULT_TITLE = "Daily Journal"

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
    """Notion API設定クラス"""
    api_key: str
    database_id: str

class NotionError(Exception):
    """Notionの操作に関するカスタムエラー"""
    pass

class NotionJournalManager:
    """Notion日報管理クラス

    Notionの日報データベースの操作を担当するクラス。
    日報の取得、作成、複製などの機能を提供する。
    """

    def __init__(self, config: Optional[NotionConfig] = None):
        """NotionJournalManagerの初期化

        Args:
            config: Notion API設定。Noneの場合は環境変数から読み込む

        Raises:
            NotionError: API設定が不完全な場合
        """
        self.config = self._initialize_config(config)
        self.client = Client(auth=self.config.api_key)

    def _initialize_config(self, config: Optional[NotionConfig]) -> NotionConfig:
        """設定を初期化

        Args:
            config: 既存の設定、またはNone

        Returns:
            初期化された設定オブジェクト

        Raises:
            NotionError: 必要な環境変数がない場合
        """
        if config is not None:
            return config

        api_key = os.environ.get("NOTION_API_KEY")
        database_id = os.environ.get("NOTION_DAILY_JOURNAL_DATABASE_ID")

        if not api_key or not database_id:
            raise NotionError("環境変数 NOTION_API_KEY または NOTION_DAILY_JOURNAL_DATABASE_ID が設定されていません")

        return NotionConfig(api_key, database_id)

    def get_page_by_date(self, target_date: datetime) -> Optional[Dict[str, Any]]:
        """指定日付のページを取得

        Args:
            target_date: 取得する日報の日付

        Returns:
            取得したページ情報、存在しない場合はNone
        """
        date_str = target_date.strftime('%Y-%m-%d')
        try:
            response = self.client.databases.query(
                database_id=self.config.database_id,
                filter={
                    "property": NotionProperty.DATE,
                    "date": {"equals": date_str}
                },
                page_size=1,
                sorts=[{"property": NotionProperty.DATE, "direction": "descending"}]
            )
            return response['results'][0] if response.get('results') else None

        except APIResponseError as e:
            logger.error(f"APIエラー（ページ取得）: {e}")
            return None
        except Exception as e:
            logger.error(f"予期せぬエラー（ページ取得）: {e}")
            return None

    def create_page(self, properties: Dict[str, Any], icon: Optional[Dict] = None,
                   cover: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """新規ページを作成

        Args:
            properties: ページのプロパティ
            icon: ページのアイコン設定
            cover: ページのカバー画像設定

        Returns:
            作成されたページ情報、失敗した場合はNone
        """
        try:
            return self.client.pages.create(
                parent={"database_id": self.config.database_id},
                properties=properties,
                icon=icon,
                cover=cover
            )
        except APIResponseError as e:
            logger.error(f"APIエラー（ページ作成）: {e}")
            return None
        except Exception as e:
            logger.error(f"予期せぬエラー（ページ作成）: {e}")
            return None

    def _convert_rich_text(self, rich_text: List[Dict]) -> List[Dict]:
        """リッチテキスト内のリンクメンションを適切な形式に変換

        Notion API を介してデータを操作する際、リンクメンションをそのまま扱うと、
        期待通りに表示されない場合があるため、リンクメンションをlink形式に変換する。

        Args:
            rich_text: 変換元のリッチテキスト配列

        Returns:
            変換後のリッチテキスト配列
        """
        converted = []
        for text in rich_text:
            if (text['type'] == 'mention' and
                text.get('mention', {}).get('type') == 'link_mention'):
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

    def _fetch_blocks(self, block_id: str, batch_size: int) -> List[Dict[str, Any]]:
        """ブロックの子要素をすべて取得

        Args:
            block_id: 親ブロックID
            batch_size: 一度に取得する件数

        Returns:
            取得したブロック情報のリスト

        Raises:
            APIResponseError: API呼び出しエラー
        """
        blocks_buffer = []
        has_more = True
        start_cursor = None

        while has_more:
            response = self.client.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor,
                page_size=batch_size
            )
            blocks_buffer.extend(response['results'])
            has_more = response.get('has_more', False)
            start_cursor = response.get('next_cursor')

        return blocks_buffer

    def _prepare_blocks_for_copy(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """複製用にブロック情報を準備

        Args:
            blocks: 元のブロック情報

        Returns:
            複製用に処理したブロック情報
        """
        new_blocks = []
        for block in blocks:
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
        return new_blocks

    def _append_blocks(self, target_id: str, blocks: List[Dict[str, Any]],
                      batch_size: int) -> List[Dict[str, Any]]:
        """ブロックをバッチで追加

        Args:
            target_id: 追加先のページID
            blocks: 追加するブロック情報
            batch_size: 一度に追加する件数

        Returns:
            作成されたブロックのリスト

        Raises:
            APIResponseError: API呼び出しエラー
        """
        created_blocks = []
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            response = self.client.blocks.children.append(
                block_id=target_id,
                children=batch
            )
            created_blocks.extend(response['results'])
        return created_blocks

    def copy_blocks(self, source_id: str, target_id: str, batch_size: int = DEFAULT_BATCH_SIZE) -> bool:
        """ブロックを再帰的に複製

        Args:
            source_id: コピー元のページID
            target_id: コピー先のページID
            batch_size: 一度に処理するブロック数

        Returns:
            成功したらTrue、失敗したらFalse
        """
        try:
            # すべてのブロックを取得
            blocks_buffer = self._fetch_blocks(source_id, batch_size)

            # 複製用にブロックを準備
            new_blocks = self._prepare_blocks_for_copy(blocks_buffer)

            # バッチでブロックを追加
            created_blocks = self._append_blocks(target_id, new_blocks, batch_size)

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
            logger.error(f"APIエラー（ブロックコピー）: {e}")
            return False
        except Exception as e:
            logger.error(f"予期せぬエラー（ブロックコピー）: {e}")
            return False

    def _update_properties_for_today(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """プロパティを今日の日付用に更新

        Args:
            properties: 更新するプロパティ

        Returns:
            更新したプロパティ
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        new_properties = properties.copy()

        # タイトル更新
        if (NotionProperty.TITLE in new_properties and
            len(new_properties[NotionProperty.TITLE].get('title', [])) > 0):
            new_properties[NotionProperty.TITLE]['title'][0]['text']['content'] = DEFAULT_TITLE

            # 日付メンションの更新
            if len(new_properties[NotionProperty.TITLE].get('title', [])) > 1:
                title_parts = new_properties[NotionProperty.TITLE]['title']
                for part in title_parts:
                    if (part.get('type') == 'mention' and
                        part.get('mention', {}).get('type') == 'date'):
                        part['mention']['date']['start'] = date_str

        # 日付プロパティ更新
        if NotionProperty.DATE in new_properties:
            new_properties[NotionProperty.DATE]['date']['start'] = date_str

        return new_properties

    def duplicate_daily_journal(self) -> Optional[Dict[str, Any]]:
        """前日の日報を複製して今日の日報を作成

        Returns:
            作成された新しい日報ページの情報、失敗した場合はNone
        """
        try:
            # 前日の日報を取得
            yesterday = datetime.now() - timedelta(days=1)
            source_page = self.get_page_by_date(yesterday)

            if not source_page:
                logger.info("前日のページが見つかりません")
                return None

            # ページ内容を取得
            page_content = self.client.pages.retrieve(source_page['id'])

            # プロパティの更新
            new_properties = self._update_properties_for_today(page_content['properties'])

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

def create_journal_manager() -> Optional[NotionJournalManager]:
    """日報管理マネージャーを生成

    Returns:
        設定済みのNotionJournalManagerインスタンスまたはNone
    """
    try:
        return NotionJournalManager()
    except NotionError as e:
        logger.error(f"初期化エラー: {e}")
        return None
    except Exception as e:
        logger.error(f"予期せぬエラー: {e}")
        return None

def duplicate_journal() -> bool:
    """日報複製の実行

    Returns:
        成功した場合はTrue、失敗した場合はFalse
    """
    manager = create_journal_manager()
    if not manager:
        return False

    result = manager.duplicate_daily_journal()
    if result:
        logger.info("日報の複製が完了しました")
        return True
    else:
        logger.warning("日報の複製に失敗しました")
        return False

def main():
    """プログラムのエントリーポイント"""
    exit_code = 0

    if not duplicate_journal():
        exit_code = 1

    # 実行環境に応じてexit_codeを使用できる
    # sys.exit(exit_code) などが可能

if __name__ == '__main__':
    main()
