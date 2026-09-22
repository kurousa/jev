from dotenv import load_dotenv
# 環境変数の読み込み
# .envファイルがカレントディレクトリにあれば、それを読み込む
load_dotenv()

from typesafe_sdk import TypeSafeClient, Choice, Noul

def call_llm_fallback(message_text: str, channel_type: str) -> dict:
    """
    Jev で判定困難だった複雑な文脈を、LLM (System Two) で精査する関数

    Note: 本来は、ここで実際にLLMのAPIを叩いて判定を行うが、今回はデモのため
          固定値を返している。
    """
    # じっくり文章と文脈を読み解くプロンプト処理
    return {
        "category": "confidential_leak",
        "needs_action": True,
        "reason": "文脈から機密情報が漏洩していると判断しました。"
    }

def check_slack_message(message_text: str, channel_type: str = "public", debug: bool = False) -> dict:
    """
    Slackメッセージを受け取り、Jev(System One)で規約チェックを行うコア関数
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

def check_slack_message_with_fallback(message_text: str, channel_type: str = "public", confidence_threshold: float = 0.75, debug: bool = False) -> dict:
    """
    Jev の確信度に応じて LLM へフォールバックするハイブリッド判定関数
    """
    # 1. まずは爆速の Jev で一次判定！
    jev_result = check_slack_message(message_text, channel_type, debug)
    
    # 2. 確信度が閾値（例: 0.75）以上なら Jev の判定をそのまま採用（高速・低コスト）
    if jev_result["confidence"] >= confidence_threshold:
        return {
            "category": jev_result["category"],
            "needs_action": jev_result["needs_action"],
            "confidence": jev_result["confidence"],
            "engine": "Jev (System One)"
        }
    
    # 3. 確信度が低く Jev が迷った場合は、LLM へバトンタッチ！
    print(f"⚠️ [Jev 確信度低 ({jev_result['confidence']:.2f})] -> LLM へフォールバック中...")
    llm_result = call_llm_fallback(message_text, channel_type)
    
    result = {
        "category": llm_result["category"],
        "needs_action": llm_result["needs_action"],
        "confidence": 1.0, # LLMによる精査結果
        "engine": f"LLM Fallback (理由: {llm_result.get('reason')})",
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

    result_with_fallback = check_slack_message_with_fallback("〇〇さん、さすがにその重要な機密仕様のファイルを社外の友人にうっかり見せちゃったりは…しないですよねー？ハハッ", "public", debug=True)
    print(f"\n---LLM Fallback Test ---")
    print(f"判定対象メッセージ: {result_with_fallback['message_text']}    ({result_with_fallback['channel_type']})")
    print(f"判定カテゴリ: {result_with_fallback['category']} (確信度: {result_with_fallback['confidence']:.2f})")
    print(f"即時対応フラグ: {result_with_fallback['needs_action']}")
    print(f"実行エンジン: {result_with_fallback['engine']}")
