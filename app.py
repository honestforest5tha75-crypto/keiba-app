import streamlit as st
import pandas as pd
import requests
import io
import re

# ページ設定
st.set_page_config(page_title="新・競馬投資戦略マシーン", layout="wide")

st.title("🏇 新・競馬投資戦略マシーン（本命＆大穴 独立分析型）")
st.write("騎手・馬齢・斤量のデータから「堅実スコア」と「大穴スコア」の2軸を計算し、手堅い的中と一発逆転の両方を提案します。")

st.sidebar.header("⚙️ 運用条件設定")
race_id = st.sidebar.text_input("12桁のレースIDを入力", value="202610020705", max_chars=12)
budget = st.sidebar.number_input("1レースの軍資金（円）", min_value=1000, max_value=100000, step=1000, value=5000)

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
                        baban_str = str(row[c_umaban]) if c_umaban else ""
                        baban_match = re.search(r'\d+', baban_str)
                        if not baban_match: continue
                        umaban = int(baban_match.group())
                        
                        name_str = str(row[c_umamei]) if c_umamei else "不明"
                        name = re.sub(r'[\s　]+', ' ', name_str).split()[0]
                        if name == "nan" or not name: continue
                        
                        kishu_str = str(row[c_kishu]) if c_kishu else "不明"
                        kishu = re.sub(r'[\s　]+', '', kishu_str)
                        
                        seirei = str(row[c_seirei]) if c_seirei else "不明"
                        
                        kinryo_str = str(row[c_kinryo]) if c_kinryo else ""
                        kinryo_match = re.search(r'\d+\.\d+', kinryo_str)
                        kinryo = float(kinryo_match.group()) if kinryo_match else 55.0
                        
                        # ==========================================
                        # エンジン1：堅実スコア（本命狙い用）
                        # ==========================================
                        solid_score = 50.0
                        if any(top_j in kishu for top_j in TOP_JOCKEYS): solid_score += 15.0
                        if "4" in seirei: solid_score += 10.0
                        elif "5" in seirei: solid_score += 5.0
                        solid_score += ((55.0 - kinryo) * 2.0)
                        solid_score += (8 - abs(9 - umaban)) * 0.2
                        
                        # ==========================================
                        # エンジン2：大穴スコア（波乱狙い用）
                        # ==========================================
                        ana_score = 50.0
                        # 有名騎手は過剰人気になるため大穴ロジックでは減点
                        if any(top_j in kishu for top_j in TOP_JOCKEYS): 
                            ana_score -= 10.0
                        else:
                            ana_score += 10.0 # マイナー騎手の思い切った騎乗を評価
                            
                        # 軽い斤量を極端に高く評価（逃げ残り・追い込み警戒）
                        ana_score += ((55.0 - kinryo) * 5.0)
                        
                        # 3歳馬（成長力）や6歳以上（実績馬の復活）を評価
                        if "3" in seirei or "6" in seirei or "7" in seirei:
                            ana_score += 10.0
                            
                        # 展開がハマれば怖い最内枠・大外枠を評価
                        if umaban <= 2 or umaban >= 15:
                            ana_score += 10.0

                        results.append({
                            "馬番": umaban,
                            "馬名": name,
                            "騎手": kishu,
                            "性齢": seirei,
                            "斤量": kinryo,
                            "堅実スコア": round(solid_score, 1),
                            "大穴スコア": round(ana_score, 1)
                        })
                        
                    if not results:
                        st.error("⚠️ 有効な出走馬データが抽出できませんでした。")
                    else:
                        base_df = pd.DataFrame(results)
                        solid_df = base_df.sort_values("堅実スコア", ascending=False).reset_index(drop=True)
                        ana_df = base_df.sort_values("大穴スコア", ascending=False).reset_index(drop=True)
                        
                        st.subheader("📊 解析完了：全頭のスコア一覧")
                        st.dataframe(solid_df, use_container_width=True)
                        
                        st.markdown("---")
                        st.subheader("🎯 投資ポートフォリオ提案")
                        
                        # 堅実プランの抽出
                        jiku_solid = solid_df.iloc[0]
                        partners_solid = solid_df.iloc[1:4]["馬番"].tolist() if len(solid_df) > 1 else []
                        
                        # 大穴プランの抽出
                        jiku_ana = ana_df.iloc[0]
                        partners_ana = ana_df.iloc[1:3]["馬番"].tolist() if len(ana_df) > 1 else []
                        hi_horses_ana = ana_df.iloc[3:6]["馬番"].tolist() if len(ana_df) > 3 else []
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.success(f"🛡️ **堅実プラン（予算60%）：ワイド中心**\n\n"
                                       f"*堅実スコア上位で構成し、手堅く元本回収を狙うシェルターです。*\n\n"
                                       f"・**軸（本命）**: {jiku_solid['馬番']}番（{jiku_solid['馬名']}）\n\n"
                                       f"・**相手**: {', '.join(map(str, partners_solid))}番\n\n"
                                       f"・**資金配分**: 各 {int(budget * 0.6 / max(len(partners_solid), 1) // 100) * 100}円")
                        with col2:
                            st.error(f"🚀 **大穴プラン（予算40%）：3連複中心**\n\n"
                                     f"*過小評価されている軽斤量馬やマイナー騎手を軸に一発を狙います。*\n\n"
                                     f"・**軸（大穴）**: {jiku_ana['馬番']}番（{jiku_ana['馬名']}）\n\n"
                                     f"・**相手**: {', '.join(map(str, partners_ana))}番\n\n"
                                     f"・**紐**: {', '.join(map(str, partners_ana + hi_horses_ana))}番\n\n"
                                     f"・**資金配分**: 残り {int(budget * 0.4 // 100) * 100}円 を均等配分")

        except Exception as e:
            st.error(f"❌ 深刻なエラーが発生しました: {e}")
