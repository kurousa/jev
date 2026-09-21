import os
from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient, Choice, Noul

# 環境変数の読み込み
# .envファイルがカレントディレクトリにあれば、それを読み込む
load_dotenv()

# 環境変数が正しくロードされているか確認（デバッグ用）
# print("Loaded API Key:", os.getenv("TYPESAFE_API_KEY"))

# 入力コンテキスト（state）を定義
states = [{
    "message": "画面にエラー500が出ました。今日中にログインできるように復旧してください。",
    "account_tier": "pro"
}, {
    "message": "来期のシステム導入について、弊社の特殊な業務フローに合わせたカスタマイズの可否を相談したい",
    "account_tier": "enterprise"
}, {
    "message": "請求書の金額が先月と異なっています。確認をお願いします。",
    "account_tier": "pro"
}, {
    "message": "操作がよくわからない。使いにくい。",
    "account_tier": "free"
}]

print(len(states))
for state in states:
    print(f"入力: {state['message']}")
    # Jevへ判定リクエストを実行
    with TypeSafeClient() as client:
        response = client.system_one(
            state=state,
            questions={
                # Choice: 定義したカテゴリ選択肢から最も適切なものを選択
                "department": Choice(
                    instructions="この問い合わせを担当すべきチーム",
                    criteria={
                        "technical": "ログインやシステムの不具合・エラー",
                        "billing": "請求や決済、返金に関する問い合わせ",
                        "sales": "導入検討やプラン変更",
                        "other": "上記のいずれにも当てはまらない"
                    }
                ),
                # Noul: Boolean (Yes/No) の確率判定
                "is_urgent": Noul(
                    instructions="今日中などの具体的な緊急性が提示されているか"
                )
            }
        )

    # Jevの回答結果を取得
    dept_answer = response.answers["department"]
    urgent_answer = response.answers["is_urgent"]

    print(f"分類結果: {dept_answer.choice}")
    print(f"分類の確信度 (Confidence): {dept_answer.confidence}")
    print(f"緊急度判定 (Noul確率): {urgent_answer.noul}")

    # 3. 確信度に応じたルーティング（フォールバック制御）
    if dept_answer.confidence >= 0.8:
        print(f"⚡ [自動処理] 確信度が高いため、{dept_answer.choice} チーム宛に直接チケットを作成します。")
    else:
        print("🐢 [フォールバック] Jevの確信度が低い（迷っている）ため、詳細解析用にLLMへ引き継ぎます。")