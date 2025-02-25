"""
Notion日報管理ツールのテスト

Notion APIをモックして、日報が正しく複製されることをテストする。
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
from app import NotionJournalManager, NotionConfig, duplicate_journal


class TestNotionJournalManager(unittest.TestCase):
    """NotionJournalManagerのテストケース"""

    def setUp(self):
        """テスト前の準備"""
        # テスト用の設定
        self.test_api_key = "test_api_key"
        self.test_database_id = "test_database_id"
        self.config = NotionConfig(self.test_api_key, self.test_database_id)

        # モック日付の設定
        self.today = datetime(2025, 2, 25)  # テスト用の「今日」
        self.yesterday = self.today - timedelta(days=1)

        # 日付表示用フォーマット
        self.date_format = '%Y-%m-%d'

    @patch('app.Client')
    @patch('app.datetime')
    def test_duplicate_daily_journal_success(self, mock_datetime, mock_client_class):
        """日報が正常に複製されるケースのテスト"""
        # datetimeモックの設定
        mock_datetime.now.return_value = self.today

        # Notionクライアントモックの設定
        mock_client = mock_client_class.return_value

        # モックの前日の日報ページデータ
        yesterday_page_id = "yesterday_page_id"
        yesterday_date_str = self.yesterday.strftime(self.date_format)

        # データベースクエリの結果をモック
        mock_client.databases.query.return_value = {
            'results': [{
                'id': yesterday_page_id,
                'object': 'page',
                'properties': {
                    'タイトル': {
                        'title': [
                            {
                                'text': {'content': 'Daily Journal'},
                                'type': 'text'
                            },
                            {
                                'type': 'mention',
                                'mention': {
                                    'type': 'date',
                                    'date': {'start': yesterday_date_str}
                                }
                            }
                        ]
                    },
                    '日付': {
                        'date': {'start': yesterday_date_str}
                    }
                }
            }]
        }

        # ページ取得の結果をモック
        mock_client.pages.retrieve.return_value = {
            'id': yesterday_page_id,
            'object': 'page',
            'properties': {
                'タイトル': {
                    'title': [
                        {
                            'text': {'content': 'Daily Journal'},
                            'type': 'text'
                        },
                        {
                            'type': 'mention',
                            'mention': {
                                'type': 'date',
                                'date': {'start': yesterday_date_str}
                            }
                        }
                    ]
                },
                '日付': {
                    'date': {'start': yesterday_date_str}
                }
            },
            'icon': {'type': 'emoji', 'emoji': '📝'},
            'cover': None
        }

        # 新規ページ作成の結果をモック
        new_page_id = "new_page_id"
        today_date_str = self.today.strftime(self.date_format)
        mock_client.pages.create.return_value = {
            'id': new_page_id,
            'object': 'page',
            'properties': {
                'タイトル': {
                    'title': [
                        {
                            'text': {'content': 'Daily Journal'},
                            'type': 'text'
                        },
                        {
                            'type': 'mention',
                            'mention': {
                                'type': 'date',
                                'date': {'start': today_date_str}
                            }
                        }
                    ]
                },
                '日付': {
                    'date': {'start': today_date_str}
                }
            }
        }

        # ブロック取得の結果をモック
        mock_client.blocks.children.list.return_value = {
            'results': [
                {
                    'id': 'block1',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': '今日の作業内容'},
                                'plain_text': '今日の作業内容'
                            }
                        ]
                    },
                    'has_children': False
                },
                {
                    'id': 'block2',
                    'type': 'to_do',
                    'to_do': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': 'タスク1'},
                                'plain_text': 'タスク1'
                            }
                        ],
                        'checked': False
                    },
                    'has_children': False
                },
                {
                    'id': 'block3',
                    'type': 'to_do',
                    'to_do': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': 'タスク2'},
                                'plain_text': 'タスク2'
                            }
                        ],
                        'checked': True
                    },
                    'has_children': False
                }
            ],
            'has_more': False,
            'next_cursor': None
        }

        # ブロック作成の結果をモック
        mock_client.blocks.children.append.return_value = {
            'results': [
                {
                    'id': 'new_block1',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': '今日の作業内容'},
                                'plain_text': '今日の作業内容'
                            }
                        ]
                    }
                },
                {
                    'id': 'new_block2',
                    'type': 'to_do',
                    'to_do': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': 'タスク1'},
                                'plain_text': 'タスク1'
                            }
                        ],
                        'checked': False
                    }
                },
                {
                    'id': 'new_block3',
                    'type': 'to_do',
                    'to_do': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {'content': 'タスク2'},
                                'plain_text': 'タスク2'
                            }
                        ],
                        'checked': True
                    }
                }
            ]
        }

        # テスト対象のインスタンス作成
        manager = NotionJournalManager(self.config)

        # 日報複製を実行
        result = manager.duplicate_daily_journal()

        # アサーション：結果が正しいことを確認
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], new_page_id)

        # モックの呼び出しを検証
        mock_client.databases.query.assert_called_once()
        mock_client.pages.retrieve.assert_called_once_with(yesterday_page_id)

        # ページ作成時に正しいプロパティで呼び出されたか検証
        mock_client.pages.create.assert_called_once()
        create_args = mock_client.pages.create.call_args
        args, kwargs = create_args
        properties = kwargs['properties']

        # 日付が今日の日付に更新されていることを確認
        self.assertEqual(properties['日付']['date']['start'], today_date_str)

        # ブロックがコピーされたことを確認
        mock_client.blocks.children.list.assert_called_once_with(
            block_id=yesterday_page_id,
            start_cursor=None,
            page_size=100
        )

        mock_client.blocks.children.append.assert_called_once()
        append_args = mock_client.blocks.children.append.call_args
        args, kwargs = append_args
        self.assertEqual(kwargs['block_id'], new_page_id)

        # 追加されたブロックの内容を検証
        children = kwargs['children']
        self.assertEqual(len(children), 3)
        self.assertEqual(children[0]['type'], 'paragraph')
        self.assertEqual(children[0]['paragraph']['rich_text'][0]['text']['content'], '今日の作業内容')
        self.assertEqual(children[1]['type'], 'to_do')
        self.assertEqual(children[1]['to_do']['rich_text'][0]['text']['content'], 'タスク1')
        self.assertEqual(children[2]['type'], 'to_do')
        self.assertEqual(children[2]['to_do']['rich_text'][0]['text']['content'], 'タスク2')

    @patch('app.Client')
    @patch('app.datetime')
    def test_duplicate_daily_journal_source_not_found(self, mock_datetime, mock_client_class):
        """前日の日報が存在しない場合のテスト"""
        # datetimeモックの設定
        mock_datetime.now.return_value = self.today

        # Notionクライアントモックの設定
        mock_client = mock_client_class.return_value

        # データベースクエリの結果（前日のページが存在しない）
        mock_client.databases.query.return_value = {
            'results': []
        }

        # テスト対象のインスタンス作成
        manager = NotionJournalManager(self.config)

        # 日報複製を実行
        result = manager.duplicate_daily_journal()

        # アサーション：前日のページがないため、結果はNone
        self.assertIsNone(result)

        # モックの呼び出しを検証
        mock_client.databases.query.assert_called_once()
        mock_client.pages.retrieve.assert_not_called()
        mock_client.pages.create.assert_not_called()

    @patch('app.Client')
    @patch('app.datetime')
    def test_duplicate_daily_journal_api_error(self, mock_datetime, mock_client_class):
        """API呼び出しでエラーが発生する場合のテスト"""
        # datetimeモックの設定
        mock_datetime.now.return_value = self.today

        # Notionクライアントモックの設定
        mock_client = mock_client_class.return_value

        # データベースクエリでエラーをシミュレート
        mock_client.databases.query.side_effect = Exception("API接続エラー")

        # テスト対象のインスタンス作成
        manager = NotionJournalManager(self.config)

        # 日報複製を実行
        result = manager.duplicate_daily_journal()

        # アサーション：エラーが発生したため、結果はNone
        self.assertIsNone(result)

    @patch('app.Client')
    def test_get_page_by_date(self, mock_client_class):
        """指定日付のページ取得機能のテスト"""
        # Notionクライアントモックの設定
        mock_client = mock_client_class.return_value

        # テスト用の日付
        test_date = datetime(2025, 2, 24)
        date_str = test_date.strftime(self.date_format)

        # データベースクエリの結果をモック
        expected_page = {
            'id': 'test_page_id',
            'properties': {
                'タイトル': {'title': [{'text': {'content': 'Daily Journal'}}]},
                '日付': {'date': {'start': date_str}}
            }
        }
        mock_client.databases.query.return_value = {
            'results': [expected_page]
        }

        # テスト対象のインスタンス作成
        manager = NotionJournalManager(self.config)

        # メソッド実行
        result = manager.get_page_by_date(test_date)

        # アサーション
        self.assertEqual(result, expected_page)

        # クエリパラメータを検証
        mock_client.databases.query.assert_called_once()
        call_args = mock_client.databases.query.call_args
        args, kwargs = call_args
        self.assertEqual(kwargs['database_id'], self.test_database_id)
        self.assertEqual(kwargs['filter']['property'], '日付')  # NotionProperty.DATE と一致
        self.assertEqual(kwargs['filter']['date']['equals'], date_str)

    @patch('app.NotionJournalManager')
    def test_duplicate_journal_integration(self, mock_manager_class):
        """duplicate_journal関数の統合テスト"""
        # マネージャーのモック
        mock_manager = mock_manager_class.return_value
        mock_manager.duplicate_daily_journal.return_value = {'id': 'new_page_id'}

        # テスト対象の関数実行
        result = duplicate_journal()

        # アサーション
        self.assertTrue(result)
        mock_manager.duplicate_daily_journal.assert_called_once()


if __name__ == '__main__':
    unittest.main()