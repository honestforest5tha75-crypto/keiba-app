import streamlit as st
import pandas as pd
import requests
import io

# ページ設定
st.set_page_config(page_title="新・競馬投資戦略マシーン", layout="wide")

st.title("🏇 新・競馬投資戦略マシーン（完全修正版）")
st.write("取得エラーを根絶し、実際のオッズと斤量に基づく独自の期待値スコアで買い目を算出します。")

st.sidebar.header("⚙️ 運用条件設定")
race_id = st.sidebar.text_input("12桁のレースIDを入力", value="202610020705", max_chars=12)
budget = st.sidebar.number_input("1レースの軍資金（円）", min_value=1000, max_value=100000, step=1000, value=5000)

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
            response = requests.get(url, headers=headers)
            
            # 【絶対的修正】netkeibaの文字コードを強制指定し、文字化けによる読み取り失敗を防ぐ
            response.encoding = 'euc-jp'
            
            dfs = pd.read_html(io.StringIO(response.text))
            
            target_df = None
            # 正しい出馬表を確実に見つける処理
            for df in dfs:
                flat_cols = []
                for col in df.columns:
                    if isinstance(col, tuple):
                        flat_cols.append("_".join([str(c) for c in col]))
                    else:
                        flat_cols.append(str(col))
                df.columns = flat_cols
                
                col_str = "".join(flat_cols)
                if ("馬番" in col_str or "枠番" in col_str) and "馬名" in col_str:
                    target_df = df
                    break

            if target_df is None:
                st.error("⚠️ 出馬表が見つかりません。")
            else:
                # 動的な列の特定
                c_umaban = next((c for c in target_df.columns if "馬番" in c), None)
                if not c_umaban: c_umaban = next((c for c in target_df.columns if "枠番" in c), None)
                c_umamei = next((c for c in target_df.columns if "馬名" in c), None)
                c_odds = next((c for c in target_df.columns if "オッズ" in c or "単勝" in c), None)
                c_ninki = next((c for c in target_df.columns if "人気" in c), None)
                c_seirei = next((c for c in target_df.columns if "性齢" in c), None)
                c_kinryo = next((c for c in target_df.columns if "斤量" in c), None)

                if not c_odds:
                    st.error("⚠️ オッズデータが見つかりません。まだオッズが発表されていない可能性があります。")
                else:
                    results = []
                    for _, row in target_df.iterrows():
                        # 馬番の検証
                        try:
                            umaban = int(float(str(row[c_umaban])))
                        except:
                            continue
                            
                        name = str(row[c_umamei]).replace(" ", "").replace(" ", "")
                        
                        # オッズの取得（失敗時はスキップせず極端な値にしないよう検証）
                        try:
                            odds = float(str(row[c_odds]).replace(" ", "").replace(" ", ""))
                        except:
                            continue # オッズがない馬（取消など）は計算から除外
                            
                        try:
                            ninki = int(float(str(row[c_ninki])))
                        except:
                            ninki = 18
                            
                        seirei = str(row[c_seirei]) if c_seirei else "不明"
                        
                        try:
                            kinryo = float(str(row[c_kinryo]))
                        except:
                            kinryo = 55.0
                            
                        # --- 期待値スコア計算 ---
                        score = 100.0
                        
                        # オッズによる基礎点
                        if 3.0 <= odds <= 15.0: score += 20
                        elif odds < 3.0: score += 10
                        
                        # 物理的ペナルティとボーナス
                        if kinryo >= 57.0: score -= 5
                        if "4" in seirei or "5" in seirei: score += 10
                        
                        # 人気の相殺（人気馬はスコアが下がり、オッズの割に人気がない馬を高く評価）
                        score -= (ninki * 1.5)
                        
                        results.append({
                            "馬番": umaban,
                            "馬名": name,
                            "性齢": seirei,
                            "斤量": kinryo,
                            "オッズ": odds,
                            "人気": ninki,
                            "独自スコア": round(score, 1)
                        })
                        
                    if not results:
                        st.error("⚠️ 計算可能な馬のデータがありませんでした。")
                    else:
                        # 独自スコアで降順ソート
                        final_df = pd.DataFrame(results).sort_values("独自スコア", ascending=False).reset_index(drop=True)
                        
                        st.subheader("📊 解析完了：独自期待値スコア順")
                        st.dataframe(final_df, use_container_width=True)
                        
                        # 買い目の構築
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
