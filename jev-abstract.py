from enum import Enum
from dataclasses import dataclass

# 1. Jevに判定させたい「型（Enum）」をあらかじめ定義
class Category(str, Enum):
    TECH_SUPPORT = "技術トラブル"
    BILLING = "料金問い合わせ"
    FEATURE_REQUEST = "機能要望"
    UNCERTAIN = "判定不能" # 確信度が低い場合

@dataclass
class JevResult:
    category: Category
    confidence: float # 確信度 (0.0 ～ 1.0)

# 2. Jevモデルの疑似関数（文章を生成せず、型の確率だけを返す）
def jev_predict(text: str) -> JevResult:
    # 内部処理：トークン生成をスキップし、型の確率（Logits）のみを計算
    if "エラー" in text or "バグ" in text:
        return JevResult(Category.TECH_SUPPORT, confidence=0.98)
    elif "いくら" in text or "決済" in text:
        return JevResult(Category.BILLING, confidence=0.95)
    else:
        # 複雑・曖昧な入力は確信度を低く返す
        return JevResult(Category.UNCERTAIN, confidence=0.30)

# 3. 実行とルーティング（ハイブリッド処理）
def process_inquiry(user_text: str):
    print(f"入力: 「{user_text}」")
    
    # まずは爆速のJevで判定！
    result = jev_predict(user_text)
    
    # 確信度が80%以上ならJevの結果を採用して即終了（高速・低コスト）
    if result.confidence >= 0.8:
        print(f"⚡ [Jevで超高速判定] 分類: {result.category.value} (確信度: {result.confidence * 100}%)")
    else:
        # 確信度が低い場合のみ、じっくり考えるLLMへ回す！
        print(f"🐢 [Jevでは判定困難 (確信度 {result.confidence * 100}%)] -> 重厚なLLMへフォールバックして解釈中...")

# --- テスト実行 ---
process_inquiry("画面にエラーコード500が表示されて動かない")
print("-" * 40)
process_inquiry("来期のシステム導入について、弊社の特殊な業務フローに合わせたカスタマイズの可否を相談したい")