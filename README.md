# Notion Daily Journal Manager
## 概要
このスクリプトは、Notion API を利用して、前日の日報ページを自動的に複製し、新しい日報ページを作成します。これにより、手動でのコピー作業を省略し、日々の業務報告の作成を効率化できます。

## 必要条件
- Python 3.8 以上
- Notion API キー
- Notion データベース ID

## インストール
リポジトリをクローンします。

```.bash
git clone https://github.com/ozmile/notion_client.git
cd notion_client
```

必要なパッケージをインストールします。

```.bash
pip install -r requirements.txt
```

## 環境変数の設定
### Notion API キーの取得
Notion API のサイトで新規インテグレーション（Internalタイプ）を作成し、Tokenをコピーして `NOTION_API_KEY`に設定。

### データベース ID の取得
Notionの日報データベースを開き、URL内の`https://www.notion.so/workspace/【データベースID】?v=...` からデータベースIDをコピーし、`NOTION_DAILY_JOURNAL_DATABASE_ID`に設定。

### .env ファイルの作成
プロジェクトのルートディレクトリに .env を作成し、以下を記述：

```.bash
NOTION_API_KEY=your_api_key
NOTION_DAILY_JOURNAL_DATABASE_ID=your_database_id
```
※お好みで .bashrc などに設定しても構いません。

### Notion のページでコネクトを有効化
1. データベースを開き、ページ右上の「...」をクリック
2. 「コネクト」を選択し、作成したインテグレーションを追加

## 使用方法
環境変数を設定した後、以下のコマンドでスクリプトを実行できます。

```.bash
python app.py
```
スクリプトを定期的に実行することで、毎日自動的に前日の日報が複製されます。

## 免責事項
- 本ソフトウェアは「現状のまま」で提供され、明示または黙示を問わず、いかなる種類の保証もありません。
- 作者は、本ソフトウェアの使用または使用不能から生じるいかなる損害についても責任を負いません。
- Notion のデータベースや設定に関する変更は、ユーザーの責任において行ってください。
- API の仕様変更により、予告なく動作が変更される可能性があります。

## 既知の制限事項
- 特定のブロックタイプ（例：リンクメンション）の複製に制限がある場合があります。
- 大量のブロックを含むページの複製は、API の制限により失敗する可能性があります。
- 一部のリッチテキスト形式が正しく複製されない場合があります。

## 貢献方法
バグ報告や機能提案は、Issue を通じて行ってください。プルリクエストも歓迎します。

## サポート
- 本ソフトウェアは個人利用を想定しており、商用サポートは提供していません。
- バグ報告やプルリクエストは歓迎しますが、対応を保証するものではありません。
- セキュリティ上の問題は、Issue 作成前に作者に直接連絡してください。

## ライセンス

MIT License

Copyright (c) 2025 ozmile

本ソフトウェアおよび関連文書ファイル（以下「ソフトウェア」）の複製を取得する全ての人に対し、
ソフトウェアを無制限に扱うことを無償で許可します。これには、ソフトウェアの複製を使用、複写、
変更、結合、掲載、頒布、サブライセンス、および/または販売する権利、およびソフトウェアを提供する
相手に同じことを許可する権利も無制限に含まれます。

上記の著作権表示および本許諾表示を、ソフトウェアのすべての複製または重要な部分に記載するものとします。

ソフトウェアは「現状のまま」で、明示であるか暗黙であるかを問わず、何らの保証もなく提供されます。
ここでいう保証とは、商品性、特定の目的への適合性、および権利非侵害についての保証も含みますが、
それに限定されるものではありません。作者または著作権者は、契約行為、不法行為、またはそれ以外で
あろうと、ソフトウェアに起因または関連し、あるいはソフトウェアの使用またはその他の扱いによって
生じる一切の請求、損害、その他の義務について何らの責任も負わないものとします。
