import streamlit as st
import pandas as pd
import requests
import io
import sys
import subprocess

# 必要な外部ライブラリが足りない場合に自動インストールする仕組み
try:
    import lxml
    import beautifulsoup4
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "lxml", "beautifulsoup4", "html5lib"])

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
    
    # 5・6桁目の競馬場コードを抽出
    track_code = r_id[4:6]
    
    # JRA（中央競馬）の競馬場コード: 01札幌〜10小倉
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
            # スクレイピングの実行
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers)
            response.encoding = response.apparent_encoding
            
            # HTMLから表を抽出
            dfs = pd.read_html(io.StringIO(response.text))
            
            # 出馬表テーブルの特定（通常は最初の大きなテーブル）
            raw_df = dfs[0]
            
            # マルチインデックスの解除（JRA対策）
            if isinstance(raw_df.columns, pd.MultiIndex):
                raw_df.columns = raw_df.columns.get_level_values(-1)
            
            # データの整形（中央・地方で異なる列名に対応）
            cleaned_data = []
            for _, row in raw_df.iterrows():
                # 馬番の抽出
                horse_num = row.get("馬番", row.get("枠番", None))
                if pd.isna(horse_num): continue
                
                # 馬名の抽出
                horse_name = row.get("馬名", "")
                if hasattr(horse_name, "str"):
                    horse_name = horse_name.split()[0]  # 余計な文字を排除
                
                # 人気・オッズの抽出
                popularity = row.get("人気", None)
                odds = row.get("オッズ", row.get("単勝", None))
                
                # 脚質やタイム（netkeibaのテキストから簡易判定、またはデフォルト値）
                # 初心者向けに、人気とオッズをベースにした確実な実力上位判定を行います
                try:
                    pop_val = int(float(str(popularity).strip()))
                except:
                    pop_val = 99  # 不明な場合は下位に
                    
                cleaned_data.append({
                    "馬番": int(float(str(horse_num))),
                    "馬名": str(horse_name).strip(),
                    "人気": pop_val,
                    "オッズ": odds
                })
            
            df = pd.DataFrame(cleaned_data).sort_values("人気").reset_index(drop=True)
            
            if df.empty:
                st.warning("⚠️ 出馬表のデータを正しく解析できませんでした。レースIDが正しいか、または出馬表がすでに公開されているか確認してください。")
            else:
                st.subheader("📊 出馬表データ（実力・人気順ソート）")
                st.dataframe(df, use_container_width=True)
                
                # ----------------------------------------------------
                # 新ロジック：本命軸＋堅実データ重視フォーメーション
                # ----------------------------------------------------
                st.markdown("---")
                st.subheader("🎯 【新方針】データ重視の推奨買い方・資金配分")
                
                # 軸馬（1番人気、または2番人気までの最有力馬）
                jiku_horse = df.iloc[0]["馬番"]
                jiku_name = df.iloc[0]["馬名"]
                
                # 相手・対抗（2〜4番人気の実力上位馬）
                partners = df.iloc[1:4]["馬番"].tolist()
                
                # 紐・穴（5〜8番人気の、コース適性や一発がある範囲）
                hi_horses = df.iloc[4:8]["馬番"].tolist()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"🛡️ **コア投資（予算60%）：ワイド フォーメーション**\n"
                               f"確実に当てるための元本回収シェルターです。\n"
                               f"・**軸（本命）**: {jiku_horse}番（{jiku_name}）\n"
                               f"・**相手（対抗）**: {', '.join(map(str, partners))}番\n"
                               f"・**資金配分**: 各 {int(budget * 0.6 / len(partners) // 100) * 100}円 ずつ購入")
                    
                with col2:
                    st.error(f"🚀 **サテライト投資（予算40%）：3連複 フォーメーション**\n"
                             f"本命を軸にしつつ、中位・穴馬の滑り込みでプラス収支を叩き出す構成です。\n"
                             f"・**1頭目（軸）**: {jiku_horse}番\n"
                             f"・**2頭目（相手）**: {', '.join(map(str, partners))}番\n"
                             f"・**3頭目（紐・穴）**: {', '.join(map(str, partners + hi_horses))}番\n"
                             f"・**資金配分**: 残り予算 {int(budget * 0.4 // 100) * 100}円 を均等に配分")
                    
                st.info("💡 **初心者向けアドバイス**\n"
                        "競馬で最も勝率が高いのは『1番人気が3着以内に入る確率（約60〜70%）』をベースに組むことです。"
                        "このシステムは、その堅実な軸から、データ上崩れにくい上位馬へ手堅く流すロジックに生まれ変わりました。")
                
        except Exception as e:
            st.error(f"❌ データの取得中にエラーが発生しました。まだ出馬表が公開されていない可能性があります。")
            st.caption(f"エラー詳細: {e}")
