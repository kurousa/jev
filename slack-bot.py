import os
from dotenv import load_dotenv
# 環境変数の読み込み
# .envファイルがカレントディレクトリにあれば、それを読み込む
load_dotenv()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from jev_checker import check_slack_message

# Boltアプリの初期化
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def get_channel_type(client, channel_id):
    try:
        conversations_response = client.conversations_info(channel=channel_id)
        is_private = conversations_response["channel"].get("is_private", False)
        return "private" if is_private else "public"
    except Exception as e:
        print(f"チャンネル情報の取得に失敗しました: {e}")
        return "public"  

# チャンネルに投稿された全メッセージをリアルタイムで監視・受信
@app.message("")
def handle_message_events(message, say, client):
    user_id = message.get("user")
    text = message.get("text", "")
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
    # print(f"jev の判定結果: {result}")

    # 2. Jevの判定結果に応じたアクション
    if result["category"] != "safe" and result["confidence"] > 0.5:
        # 該当発言のスレッドに対して警告メッセージを投稿
        say(
            text=f"⚠️ <@{user_id}> さん、送信されたメッセージに規約違反の可能性があります（判定: {result['category']}）。",
            thread_ts=thread_ts
        )
        
if __name__ == "__main__":
    # Socket Modeでボットを起動
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()