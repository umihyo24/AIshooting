# 半オートSTG『指示と本能』仕様書 v0.91（AI行動詳細版）

---

## AI行動ロジック詳細

### 1. 行動カテゴリ

* **通常射撃**：低コスト、連射ベース。
* **強攻撃**：EN高消費、DPS高。HT上昇大。
* **接近行動**：敵に近づく。近距離武器や火力集中に必須。
* **距離維持**：中距離を保とうとする行動。
* **回避**：弾幕回避やステップ回避を優先。
* **ステップ（無敵回避）**：短距離ダッシュ。CTあり。
* **必殺技**：予約後、溜め→発動。

---

### 2. 行動決定フロー

1. **センサー情報取得**（200msごと）

   * `threatLevel`：自機周辺 64px 以内の敵弾密度
   * `targetScore`：最寄り敵の重要度（Boss > Elite > Mob）
   * `dist`：ターゲットとの距離
   * `resources`：EN, HT, 必殺ゲージ, HP残量
2. **状況バイアス設定**

   * `if threatLevel > 0.7 → 回避Bias +40`
   * `if EN < 20 → 強攻撃Bias -30`
   * `if HT > 70 → 攻撃系Bias -20, 回避Bias +20`
   * `if HP < 30% → 距離維持Bias +20`
3. **指示バイアス合成**

   * プレイヤー指示で行動Biasを加算（例：「おもいっきり」=攻撃+40）
4. **性格補正**

   * Aggressive：攻撃系Bias×1.3、回避系Bias×0.7
   * Prudent：回避系Bias×1.3、攻撃系Bias×0.8
   * Skittish：距離維持Bias+20、必殺を後回し
5. **最終行動選択**

   * `weightedChoice(行動Bias)` で行動確定
   * 実行までに `反映遅延 = baseDelay * (1 - SYNC%) ± rng(80ms)`

---

### 3. 行動例

* **雑魚密集時**

  * threatLevel中、EN高 → 「おもいっきり」で範囲攻撃多発
* **ボス大技予兆中**

  * threatLevel高 → 回避Bias +50、指示が「おもいっきり」でも攻撃せず避け行動優先
* **HP赤字・必殺ゲージ100%**

  * personality=Aggressive → 自爆覚悟で必殺発動
  * personality=Prudent → 温存指示でなければ回避優先、必殺後回し

---

### 4. 個性成長要素

* バトル後に性格傾向が少し変化：

  * 攻撃で勝利：Aggressive化+5%
  * 被弾多い勝利：Prudent化+5%
  * 敗北時：Skittish化+10%
* 恒久的にAIの判断がプレイヤーのスタイルに寄っていく。

---

### 5. 疑似コード例

```pseudo
function think(ctx, orderBias, personality):
  weights = baseWeights.copy()

  // 状況バイアス
  if ctx.threat > 0.7: weights[evade] += 40
  if ctx.EN < 20:     weights[strongAttack] -= 30
  if ctx.HT > 70:     weights[attack] -= 20; weights[evade] += 20
  if ctx.HP < 0.3:    weights[keepDist] += 20

  // 指示反映
  for action in weights:
    weights[action] += orderBias[action]

  // 性格補正
  if personality == Aggressive:
    weights[attack] *= 1.3; weights[evade] *= 0.7
  if personality == Prudent:
    weights[evade] *= 1.3; weights[attack] *= 0.8
  if personality == Skittish:
    weights[keepDist] += 20; weights[special] -= 15

  // 遅延と行動選択
  delay = baseDelay*(1 - ctx.SYNC) + random(-0.08,0.08)
  after(delay): execute(weightedChoice(weights))
```