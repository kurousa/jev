import os
import logging
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from jev_checker import check_slack_message

# 環境変数の読み込み
# .envファイルがカレントディレクトリにあれば、それを読み込む
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def respond_ack(ack):
    """
    Slackのメッセージ受信時に、3秒ルール（タイムアウト）回避用の即時承認応答を行う関数
    """
    ack()

def get_channel_type(client, channel_id):
    """
    Slackのチャンネル種別を取得する関数
    """
    try:
        conversations_response = client.conversations_info(channel=channel_id)
        is_private = conversations_response["channel"].get("is_private", False)
        return "private" if is_private else "public"
    except Exception as e:
        print(f"チャンネル情報の取得に失敗しました: {e}")
        return "public"  

def process_message_event(message, say, client):
    """
    Slackで受信したメッセージを処理する関数
    """
    user_id = message.get("user")
    text = message.get("text", "")
    # ボット自身の投稿や空メッセージは無視
    if message.get("subtype") == "bot_message" or not text:
        return
    channel_id = message.get("channel")
    thread_ts = message.get("ts") # メッセージのタイムスタンプ
    channel_type = get_channel_type(client, channel_id) # 対象チャンネルの公開状態を取得
    # print(f"受信メッセージ: {text} ({channel_type})")
    # print(f"発信者ID: {user_id}")
    # print(f"チャンネルID: {channel_id}")
    # print(f"スレッドID: {thread_ts}")
    # print(f"チャンネルタイプ: {channel_type}")
    
    # 1. キャッチしたテキストを Jev に渡して高速チェック
    result = check_slack_message(message_text=text, channel_type=channel_type)
    logger.info(f"jev の判定結果: {result}")
    if result.get("error"):
        logger.error(f"判定処理スキップ: {result['error']}")
        return

    # 即時対応フラグが立った場合、または緊急度スコアが高い場合に対応
    if result["needs_immediate_action"] >= 0.5 or result["urgency_score"] >= 0.8:
        say(
            text=(
                f"⚠️ <@{user_id}> さん、[{channel_type.upper()} チャンネル] 送信メッセージに規約違反の可能性があります。\n"
                f"・判定カテゴリ: `{result['category']}`\n"
                f"・確信度: `{result['confidence']:.2f}`\n"
                f"・緊急度スコア: `{result['urgency_score']:.2f}`"
            ),
            thread_ts=thread_ts
        )

# Boltアプリの初期化
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
# メッセージ受信イベントの設定
app.message("")(ack=respond_ack, lazy=[process_message_event])

if __name__ == "__main__":
    if not os.environ.get("SLACK_APP_TOKEN"):
        raise ValueError("SLACK_APP_TOKENが設定されていません。.\n.envファイルまたは環境変数を確認してください。")

    print("✅ Slack ボットが起動しました！")

    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
