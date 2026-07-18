import streamlit as st
import pandas as pd
import requests
import io

# ページ設定
st.set_page_config(page_title="新・競馬投資戦略マシーン", layout="wide")

st.title("🏇 新・競馬投資戦略マシーン（本命軸＆実力データ重視型）")
st.write("12桁のレースIDから中央・地方を自動判別し、1〜3番人気の実力馬を軸に据えた堅実なフォーメーションを提案します。")

# ----------------------------------------------------
# サイドバー：条件設定
# ----------------------------------------------------
st.sidebar.header("⚙️ 運用条件設定")
race_id = st.sidebar.text_input("12桁のレースIDを入力", value="202610010111", max_chars=12)
budget = st.sidebar.number_input("1レースの軍資金（円）", min_value=1000, max_value=100000, step=1000, value=5000)

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
            
            # HTMLからすべての表を抽出
            dfs = pd.read_html(io.StringIO(response.text))
            
            # 確実なデータ抽出のための検品処理：正しい出馬表テーブルを自動で探す
            raw_df = pd.DataFrame()
            for temp_df in dfs:
                temp_cols = temp_df.columns.get_level_values(-1) if isinstance(temp_df.columns, pd.MultiIndex) else temp_df.columns
                if "馬番" in temp_cols or "馬名" in temp_cols:
                    raw_df = temp_df
                    raw_df.columns = temp_cols  # カラム名を平坦化
                    break
            
            if raw_df.empty:
                st.warning("⚠️ 出馬表のデータが見つかりませんでした。レースIDが間違っているか、ページ構造が変更された可能性があります。")
            else:
                cleaned_data = []
                for _, row in raw_df.iterrows():
                    horse_num = row.get("馬番", row.get("枠番", None))
                    
                    # 馬番が空欄の場合はスキップ
                    if pd.isna(horse_num): continue
                    
                    # 馬番が数字に変換できない行（表の中のヘッダー行など）はスキップ
                    try:
                        h_num = int(float(str(horse_num)))
                    except ValueError:
                        continue
                        
                    horse_name = row.get("馬名", "")
                    if hasattr(horse_name, "str"):
                        horse_name = str(horse_name).split()[0]
                    
                    popularity = row.get("人気", None)
                    odds = row.get("オッズ", row.get("単勝", None))
                    
                    try:
                        pop_val = int(float(str(popularity).strip()))
                    except (ValueError, TypeError):
                        pop_val = 99  # 人気データがない場合は99（最下位扱い）にする
                        
                    cleaned_data.append({
                        "馬番": h_num,
                        "馬名": str(horse_name).strip(),
                        "人気": pop_val,
                        "オッズ": odds
                    })
                
                if not cleaned_data:
                    st.warning("⚠️ 有効な出走馬データを抽出できませんでした。")
                else:
                    df = pd.DataFrame(cleaned_data).sort_values("人気").reset_index(drop=True)
                    
                    st.subheader("📊 出馬表データ（人気順ソート）")
                    st.dataframe(df, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("🎯 【新方針】データ重視の推奨買い方・資金配分")
                    
                    # 安全なデータ抽出（出走頭数が少ない場合のエラー回避）
                    jiku_horse = df.iloc[0]["馬番"] if len(df) > 0 else "-"
                    jiku_name = df.iloc[0]["馬名"] if len(df) > 0 else "-"
                    
                    partners = df.iloc[1:4]["馬番"].tolist() if len(df) > 1 else []
                    hi_horses = df.iloc[4:8]["馬番"].tolist() if len(df) > 4 else []
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.success(f"🛡️ **コア投資（予算60%）：ワイド フォーメーション**\n\n"
                                   f"・**軸（本命）**: {jiku_horse}番（{jiku_name}）\n\n"
                                   f"・**相手（対抗）**: {', '.join(map(str, partners))}番\n\n"
                                   f"・**資金配分**: 各 {int(budget * 0.6 / max(len(partners), 1) // 100) * 100}円")
                        
                    with col2:
                        st.error(f"🚀 **サテライト投資（予算40%）：3連複 フォーメーション**\n\n"
                                 f"・**1頭目（軸）**: {jiku_horse}番\n\n"
                                 f"・**2頭目（相手）**: {', '.join(map(str, partners))}番\n\n"
                                 f"・**3頭目（紐・穴）**: {', '.join(map(str, partners + hi_horses))}番\n\n"
                                 f"・**資金配分**: 残り予算 {int(budget * 0.4 // 100) * 100}円 を均等配分")
                
        except Exception as e:
            st.error(f"❌ データの取得・解析中にエラーが発生しました。")
            st.caption(f"エラー詳細: {e}")
