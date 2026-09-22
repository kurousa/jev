from dotenv import load_dotenv
# 環境変数の読み込み
# .envファイルがカレントディレクトリにあれば、それを読み込む
load_dotenv()

from typesafe_sdk import TypeSafeClient, Choice, Noul

def check_slack_message(message_text: str, channel_type: str = "public", debug: bool = False) -> dict:
    """
    Slackメッセージを受け取り、Jevで規約チェックを行うコア関数
    """
    # 1. 判定に必要なコンテキスト（state）を準備
    state = {
        "message": message_text,
        "channel_type": channel_type
    }
    
    # 2. Jevクライアントで判定リクエストを実行
    with TypeSafeClient() as client:
        response = client.system_one(
            state=state,
            questions={
                # 違反カテゴリの判定（Choice）
                "violation_type": Choice(
                    instructions="メッセージがどの規約違反に該当するか選択してください",
                    criteria={
                        "safe": "問題なし・健全な発言",
                        "confidential_leak": "パスワードや秘密情報、NDA該当情報の漏洩",
                        "harassment": "攻撃的・侮蔑的な発言",
                        "spam": "不適切な連投や無関係な宣伝"
                    }
                ),
                # 即時対応が必要かどうかの判定（Noul: Boolean確率）
                "needs_immediate_action": Noul(
                    instructions="情報漏洩や深刻なハラスメントなど、直ちに非表示化が必要か"
                )
            }
        )
        
    result = {
        "category": response.answers["violation_type"].choice,
        "confidence": response.answers["violation_type"].confidence,
        "needs_action": response.answers["needs_immediate_action"].noul,
    }
    if debug:
        result["message_text"] = message_text
        result["channel_type"] = channel_type

    return result

if __name__ == "__main__":
    # --- 実行テスト ---
    result = check_slack_message("プロジェクトXXXの鍵情報は 123456 です", debug=True)
    print(f"判定対象メッセージ: {result['message_text']}    ({result['channel_type']})")
    print(f"判定カテゴリ: {result['category']} (確信度: {result['confidence']:.2f})")
    print(f"即時対応フラグ: {result['needs_action']}")

    result = check_slack_message("[PR]この商品、今日までセールなんだけど買いかな？ https://example.com", "public", debug=True)
    print(f"判定対象メッセージ: {result['message_text']}    ({result['channel_type']})")
    print(f"判定カテゴリ: {result['category']} (確信度: {result['confidence']:.2f})")
    print(f"即時対応フラグ: {result['needs_action']}")

    result = check_slack_message("XXXさん、このままだとウチだとやっていけないんじゃない？", "public", debug=True)
    print(f"判定対象メッセージ: {result['message_text']}    ({result['channel_type']})")
    print(f"判定カテゴリ: {result['category']} (確信度: {result['confidence']:.2f})")
    print(f"即時対応フラグ: {result['needs_action']}")

    result = check_slack_message("皆さん、今日のランチは何を食べたいですか？", "private", debug=True)
    print(f"判定対象メッセージ: {result['message_text']} ({result['channel_type']})")
    print(f"判定カテゴリ: {result['category']} (確信度: {result['confidence']:.2f})")
    print(f"即時対応フラグ: {result['needs_action']}")

    # debug=False (デフォルト) のテスト: message_text や channel_type が含まれないことを確認
    result_no_debug = check_slack_message("debug=Falseのテストです")
    print(f"\ndebug=False の返り値キー: {list(result_no_debug.keys())}")