import streamlit as st
import pandas as pd
import requests
import io
import re

# ページ設定
st.set_page_config(page_title="新・競馬投資戦略マシーン", layout="wide")

st.title("🏇 新・競馬投資戦略マシーン（騎手・馬体・独自指数型）")
st.write("オッズ（他人の評価）を一切排除し、騎手の実績、年齢、斤量から馬の真の実力をスコア化して買い目を算出します。")

st.sidebar.header("⚙️ 運用条件設定")
race_id = st.sidebar.text_input("12桁のレースIDを入力", value="202610020705", max_chars=12)
budget = st.sidebar.number_input("1レースの軍資金（円）", min_value=1000, max_value=100000, step=1000, value=5000)

# リーディング上位騎手のボーナスリスト（システム独自の評価基準）
TOP_JOCKEYS = ["川田", "ルメール", "戸崎", "松山", "横山武", "岩田望", "武豊", "坂井", "鮫島克", "菅原明"]

def get_auto_url(r_id):
    if len(r_id) < 6: return None, "Invalid"
    track_code = r_id[4:6]
    jra_codes = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']
    if track_code in jra_codes:
        return f"https://race.netkeiba.com/race/shutuba.html?race_id={r_id}", "JRA（中央競馬）"
    return f"https://nar.netkeiba.com/race/shutuba.html?race_id={r_id}", "NAR（地方競馬）"

if st.button("最新データを取得して予測を実行", type="primary"):
    if len(race_id) != 12:
        st.error("⚠️ レースIDは12桁で入力してください。")
    else:
        url, race_type = get_auto_url(race_id)
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                st.error(f"⚠️ サーバーエラー（コード: {response.status_code}）")
            else:
                raw_data = response.content
                
                try:
                    dfs = pd.read_html(io.BytesIO(raw_data), encoding='euc-jp')
                except Exception:
                    try:
                        dfs = pd.read_html(io.BytesIO(raw_data), encoding='utf-8')
                    except Exception:
                        dfs = []
                
                target_df = None
                for df in dfs:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = ['_'.join(map(str, col)).strip() for col in df.columns]
                    else:
                        df.columns = df.columns.astype(str)
                        
                    df.columns = [re.sub(r'\s+', '', c) for c in df.columns]
                    
                    col_str = "".join(df.columns)
                    if ("馬番" in col_str or "枠番" in col_str) and "馬名" in col_str:
                        target_df = df
                        break

                if target_df is None:
                    st.error("⚠️ 出馬表が見つかりません。")
                else:
                    c_umaban = next((c for c in target_df.columns if "馬番" in c), None)
                    if not c_umaban: c_umaban = next((c for c in target_df.columns if "枠番" in c), None)
                    c_umamei = next((c for c in target_df.columns if "馬名" in c), None)
                    c_kishu = next((c for c in target_df.columns if "騎手" in c), None)
                    c_seirei = next((c for c in target_df.columns if "性齢" in c), None)
                    c_kinryo = next((c for c in target_df.columns if "斤量" in c), None)

                    results = []
                    for _, row in target_df.iterrows():
                        # 馬番
                        baban_str = str(row[c_umaban]) if c_umaban else ""
                        baban_match = re.search(r'\d+', baban_str)
                        if not baban_match: continue
                        umaban = int(baban_match.group())
                        
                        # 馬名
                        name_str = str(row[c_umamei]) if c_umamei else "不明"
                        name = re.sub(r'[\s　]+', ' ', name_str).split()[0]
                        if name == "nan" or not name: continue
                        
                        # 騎手
                        kishu_str = str(row[c_kishu]) if c_kishu else "不明"
                        kishu = re.sub(r'[\s　]+', '', kishu_str)
                        
                        # 性齢
                        seirei = str(row[c_seirei]) if c_seirei else "不明"
                        
                        # 斤量
                        kinryo_str = str(row[c_kinryo]) if c_kinryo else ""
                        kinryo_match = re.search(r'\d+\.\d+', kinryo_str)
                        kinryo = float(kinryo_match.group()) if kinryo_match else 55.0
                        
                        # ==========================================
                        # 独自の期待値スコア計算（オッズに依存しない）
                        # ==========================================
                        score = 50.0  # 基礎点
                        
                        # 1. 騎手ボーナス（トップジョッキーが乗る馬は能力を引き出しやすい）
                        is_top_jockey = any(top_j in kishu for top_j in TOP_JOCKEYS)
                        if is_top_jockey:
                            score += 15.0
                        
                        # 2. 年齢ボーナス（競走馬としてのピークである4〜5歳を評価）
                        if "4" in seirei:
                            score += 10.0
                        elif "5" in seirei:
                            score += 5.0
                            
                        # 3. 斤量（負担重量）によるスピード補正（軽いほどプラス）
                        # 基準を55kgとし、それより軽ければ加点、重ければ減点
                        weight_diff = 55.0 - kinryo
                        score += (weight_diff * 2.0)
                        
                        # 4. 同点回避のための微細な乱数要素（馬番から算出）
                        # 内枠・外枠の有利不利を擬似的に表現（ここでは真ん中の枠を少しだけ評価）
                        frame_bonus = (8 - abs(9 - umaban)) * 0.2
                        score += frame_bonus
                        
                        results.append({
                            "馬番": umaban,
                            "馬名": name,
                            "騎手": kishu,
                            "性齢": seirei,
                            "斤量": kinryo,
                            "総合スコア": round(score, 1)
                        })
                        
                    if not results:
                        st.error("⚠️ 有効な出走馬データが抽出できませんでした。")
                    else:
                        # 総合スコアで明確に順位付け（降順ソート）
                        final_df = pd.DataFrame(results).sort_values("総合スコア", ascending=False).reset_index(drop=True)
                        st.subheader("📊 解析完了：独自スピード＆騎手スコア順")
                        st.dataframe(final_df, use_container_width=True)
                        
                        st.markdown("---")
                        st.subheader("🎯 推奨フォーメーション")
                        
                        jiku = final_df.iloc[0]
                        partners = final_df.iloc[1:4]["馬番"].tolist() if len(final_df) > 1 else []
                        hi_horses = final_df.iloc[4:7]["馬番"].tolist() if len(final_df) > 4 else []
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.success(f"🛡️ **コア投資（予算60%）：ワイド**\n\n"
                                       f"・**軸（スコア1位）**: {jiku['馬番']}番（{jiku['馬名']}）\n\n"
                                       f"・**相手（スコア2〜4位）**: {', '.join(map(str, partners))}番\n\n"
                                       f"・**資金配分**: 各 {int(budget * 0.6 / max(len(partners), 1) // 100) * 100}円")
                        with col2:
                            st.error(f"🚀 **サテライト投資（予算40%）：3連複**\n\n"
                                     f"・**軸**: {jiku['馬番']}番\n\n"
                                     f"・**相手**: {', '.join(map(str, partners))}番\n\n"
                                     f"・**紐**: {', '.join(map(str, partners + hi_horses))}番\n\n"
                                     f"・**資金配分**: 残り {int(budget * 0.4 // 100) * 100}円 を均等配分")

        except Exception as e:
            st.error(f"❌ 深刻なエラーが発生しました: {e}")
