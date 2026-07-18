import streamlit as st
import pandas as pd
import requests
import io

# ページ設定
st.set_page_config(page_title="新・競馬投資戦略マシーン", layout="wide")

st.title("🏇 新・競馬投資戦略マシーン（本命・大穴ハイブリッド型）")
st.write("12桁のレースIDから中央・地方を自動判別し、堅実な的中から一発大穴狙いまで、状況に合わせたフォーメーションを提案します。")

# ----------------------------------------------------
# サイドバー：条件設定
# ----------------------------------------------------
st.sidebar.header("⚙️ 運用条件設定")
race_id = st.sidebar.text_input("12桁のレースIDを入力", value="202610010111", max_chars=12)
budget = st.sidebar.number_input("1レースの軍資金（円）", min_value=1000, max_value=100000, step=1000, value=5000)

strategy = st.sidebar.radio("📊 投資戦略（モード）を選択", 
                            ["🛡️ 堅実・本命重視（的中率優先）", "🔥 大穴・波乱狙い（回収率爆発）"])

# ----------------------------------------------------
# 中央・地方の自動URL判定ロジック
# ----------------------------------------------------
def get_auto_url(r_id):
    if len(r_id) < 6:
        return None, "Invalid"
    
    track_code = r_id[4:6]
    jra_codes = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']
    
    if track_code in jra_codes:
        return f"https://race.netkeiba.com/race/shutuba.html?race_id={r_id}", "JRA（中央競馬）"
    else:
        return f"https://nar.netkeiba.com/race/shutuba.html?race_id={r_id}", "NAR（地方競馬）"

# ----------------------------------------------------
# メイン処理
# ----------------------------------------------------
if st.button("最新データを取得してフォーメーションを構築", type="primary"):
    if len(race_id) != 12 or not race_id.isdigit():
        st.error("⚠️ レースIDは12桁の半角数字で入力してください。")
    else:
        url, race_type = get_auto_url(race_id)
        st.info(f"🔍 判定結果: **{race_type}** のページへアクセスしています...")
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            response.encoding = response.apparent_encoding
            
            dfs = pd.read_html(io.StringIO(response.text))
            
            raw_df = pd.DataFrame()
            for temp_df in dfs:
                # カラムの平坦化（JRAの複雑な表構造に対応）
                temp_cols = temp_df.columns.get_level_values(-1) if isinstance(temp_df.columns, pd.MultiIndex) else temp_df.columns
                
                # 【修正の核心】「馬番(または枠番)」と「馬名」の両方が揃っている本物の出馬表だけを厳格に探す
                col_list = list(temp_cols)
                has_horse_num = ("馬番" in col_list) or ("枠番" in col_list)
                has_horse_name = "馬名" in col_list
                
                if has_horse_num and has_horse_name:
                    raw_df = temp_df
                    raw_df.columns = temp_cols
                    break
            
            if raw_df.empty:
                st.warning("⚠️ 出馬表のデータが見つかりませんでした。URLやレースIDが正しいか確認してください。")
            else:
                cleaned_data = []
                for _, row in raw_df.iterrows():
                    # 馬番の取得（地方・中央の表記揺れに対応）
                    horse_num = None
                    if "馬番" in raw_df.columns:
                        horse_num = row["馬番"]
                    elif "枠番" in raw_df.columns:
                        horse_num = row["枠番"]
                        
                    if pd.isna(horse_num): continue
                    
                    try:
                        h_num = int(float(str(horse_num)))
                    except ValueError:
                        continue
                        
                    horse_name = row.get("馬名", "")
                    if hasattr(horse_name, "str"):
                        horse_name = str(horse_name).split()[0]
                    else:
                        horse_name = str(horse_name)
                    
                    # 人気・オッズの取得
                    popularity = row.get("人気", None)
                    odds = row.get("オッズ", row.get("単勝", None))
                    
                    try:
                        pop_val = int(float(str(popularity).strip()))
                    except (ValueError, TypeError, AttributeError):
                        pop_val = 99  # 人気不明の場合は最下位扱い
                        
                    cleaned_data.append({
                        "馬番": h_num,
                        "馬名": str(horse_name).strip(),
                        "人気": pop_val,
                        "オッズ": odds
                    })
                
                if not cleaned_data:
                    st.warning("⚠️ ページから有効な出走馬データを抽出できませんでした。")
                else:
                    df = pd.DataFrame(cleaned_data).sort_values("人気").reset_index(drop=True)
                    
                    st.subheader("📊 出馬表データ（人気順ソート）")
                    st.dataframe(df, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader(f"🎯 選択中の戦略: {strategy}")
                    
                    if "堅実" in strategy:
                        jiku_index = 0
                        partners_range = (1, 4)
                        hi_range = (4, 8)
                        mode_msg = "堅実な軸からデータ上崩れにくい上位馬へ手堅く流すロジックです。"
                    else:
                        jiku_index = min(4, len(df)-1) if len(df) > 4 else 0
                        partners_range = (0, 3)
                        hi_range = (7, 12)
                        mode_msg = "実力がありながら過小評価されている中穴を軸に、人気馬と超大穴を絡めて一発を狙うロジックです。"

                    # エラー回避のための安全なデータ取得
                    jiku_horse = df.iloc[jiku_index]["馬番"] if len(df) > jiku_index else "-"
                    jiku_name = df.iloc[jiku_index]["馬名"] if len(df) > jiku_index else "-"
                    
                    partners = df.iloc[partners_range[0]:partners_range[1]]["馬番"].tolist() if len(df) > partners_range[0] else []
                    hi_horses = df.iloc[hi_range[0]:hi_range[1]]["馬番"].tolist() if len(df) > hi_range[0] else []
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.success(f"🛡️ **コア投資（予算60%）：ワイド フォーメーション**\n\n"
                                   f"・**軸**: {jiku_horse}番（{jiku_name}）\n\n"
                                   f"・**相手**: {', '.join(map(str, partners))}番\n\n"
                                   f"・**資金配分**: 各 {int(budget * 0.6 / max(len(partners), 1) // 100) * 100}円")
                        
                    with col2:
                        st.error(f"🚀 **サテライト投資（予算40%）：3連複 フォーメーション**\n\n"
                                 f"・**1頭目（軸）**: {jiku_horse}番\n\n"
                                 f"・**2頭目（相手）**: {', '.join(map(str, partners))}番\n\n"
                                 f"・**3頭目（紐・大穴）**: {', '.join(map(str, partners + hi_horses))}番\n\n"
                                 f"・**資金配分**: 残り予算 {int(budget * 0.4 // 100) * 100}円 を均等配分")
                        
                    st.info(f"💡 **システムからのアドバイス**\n{mode_msg}")
                
        except Exception as e:
            st.error(f"❌ データの取得・解析中にエラーが発生しました。")
            st.caption(f"エラー詳細: {e}")
