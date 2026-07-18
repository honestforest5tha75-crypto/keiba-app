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
            
            dfs = pd.read_html(io.StringIO(response.text))
            raw_df = dfs[0]
            
            if isinstance(raw_df.columns, pd.MultiIndex):
                raw_df.columns = raw_df.columns.get_level_values(-1)
            
            cleaned_data = []
            for _, row in raw_df.iterrows():
                horse_num = row.get("馬番", row.get("枠番", None))
                if pd.isna(horse_num): continue
                
                horse_name = row.get("馬名", "")
                if hasattr(horse_name, "str"):
                    horse_name = horse_name.split()[0]
                
                popularity = row.get("人気", None)
                odds = row.get("オッズ", row.get("単勝", None))
                
                try:
                    pop_val = int(float(str(popularity).strip()))
                except:
                    pop_val = 99
                    
                cleaned_data.append({
                    "馬番": int(float(str(horse_num))),
                    "馬名": str(horse_name).strip(),
                    "人気": pop_val,
                    "オッズ": odds
                })
            
            df = pd.DataFrame(cleaned_data).sort_values("人気").reset_index(drop=True)
            
            if df.empty:
                st.warning("⚠️ データを解析できませんでした。")
            else:
                st.subheader("📊 出馬表データ（人気順ソート）")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("---")
                st.subheader("🎯 【新方針】データ重視の推奨買い方・資金配分")
                
                jiku_horse = df.iloc[0]["馬番"]
                jiku_name = df.iloc[0]["馬名"]
                partners = df.iloc[1:4]["馬番"].tolist()
                hi_horses = df.iloc[4:8]["馬番"].tolist()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"🛡️ **コア投資（予算60%）：ワイド フォーメーション**\n"
                               f"・**軸（本命）**: {jiku_horse}番（{jiku_name}）\n"
                               f"・**相手（対抗）**: {', '.join(map(str, partners))}番\n"
                               f"・**資金配分**: 各 {int(budget * 0.6 / len(partners) // 100) * 100}円")
                    
                with col2:
                    st.error(f"🚀 **サテライト投資（予算40%）：3連複 フォーメーション**\n"
                             f"・**1頭目（軸）**: {jiku_horse}番\n"
                             f"・**2頭目（相手）**: {', '.join(map(str, partners))}番\n"
                             f"・**3頭目（紐・穴）**: {', '.join(map(str, partners + hi_horses))}番\n"
                             f"・**資金配分**: 残り予算 {int(budget * 0.4 // 100) * 100}円 を均等配分")
                
        except Exception as e:
            st.error(f"❌ データの取得中にエラーが発生しました。")
            st.caption(f"エラー詳細: {e}")
