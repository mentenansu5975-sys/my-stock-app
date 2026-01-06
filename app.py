import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import numpy as np

# 1. ページの設定
st.set_page_config(page_title="AI投資顧問・エグゼクティブ", layout="wide")

# 2. パスワード認証
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("🔒 ログインが必要です")
    user_password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if user_password == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません")
    return False

# 3. テクニカル指標計算
def add_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA25'] = df['Close'].rolling(window=25).mean()
    df['MA75'] = df['Close'].rolling(window=75).mean()
    return df

if check_password():
    st.title("🏦 AI投資顧問・エグゼクティブ版 (FUNDAMENTALS)")

    with st.sidebar:
        st.header("分析条件")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
        period = st.selectbox("チャート期間", ["6mo", "1y", "2y"], index=0)
        if st.button("ログアウト"):
            st.session_state["password_correct"] = False
            st.rerun()

    if st.button("深層分析を開始"):
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])
            model = genai.GenerativeModel(target_model)
            
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y") 
            data = add_indicators(data)
            
            # --- 【新機能】ファンダメンタルズ/IR情報の取得 ---
            info = stock.info
            fundamentals = {
                "会社名": info.get('longName', 'N/A'),
                "時価総額": f"{info.get('marketCap', 0) / 100000000:.1f} 億円",
                "PER": info.get('trailingPE', 'N/A'),
                "PBR": info.get('priceToBook', 'N/A'),
                "配当利回り": f"{info.get('dividendYield', 0) * 100:.2f} %" if info.get('dividendYield') else "無配",
                "ROE": f"{info.get('returnOnEquity', 0) * 100:.2f} %" if info.get('returnOnEquity') else "N/A",
                "EPS": info.get('trailingEps', 'N/A'),
                "自己資本比率": f"{info.get('debtToEquity', 0):.2f}"
            }

            if not data.empty:
                # ニュース取得
                news = stock.news
                news_list = []
                if news:
                    for n in news[:5]:
                        raw_time = n.get('providerPublishTime')
                        date_str = pd.to_datetime(raw_time, unit='s').strftime('%Y-%m-%d') if raw_time else "不明"
                        news_list.append(f"- {n.get('title')} ({date_str})")
                    news_text = "\n".join(news_list)
                else:
                    news_text = "直近の関連ニュースは見当たりません。"

                # 表示
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価推移 (5/25/75日線)")
                    st.line_chart(data[['Close', 'MA5', 'MA25', 'MA75']].tail(120))
                    st.subheader("📊 過熱感 (RSI)")
                    st.line_chart(data['RSI'].tail(120))
                
                with col2:
                    st.subheader("🏦 ファンダメンタルズ/財務")
                    for k, v in fundamentals.items():
                        st.write(f"**{k}**: {v}")
                    st.write("---")
                    st.subheader("📰 直近IR/ニュース")
                    st.write(news_text)

                # AIレポート作成
                st.subheader("🤖 AIによる財務・技術・材料の統合分析")
                recent_1mo = data.tail(20).to_string()
                
                prompt = f"""
                あなたはプロの証券アナリストとして、{fundamentals['会社名']} ({ticker}) を分析してください。
                
                【財務データ（ファンダメンタルズ）】
                {fundamentals}
                
                【テクニカル・推移】
                直近20日の推移: {recent_1mo}
                現在のRSI: {data.iloc[-1]['RSI']:.1f}
                
                【最新材料】
                {news_text}
                
                【指示】
                1. 財務健全性: PER/PBR、ROEから見て、現在の株価は割安か割高か、財務面から評価してください。
                2. 総合判断: チャートの過熱感と、IR/ニュースの材料を総合し、今買うべきか待つべきかを結論付けてください。
                3. リスク要因: バイオ銘柄などの場合、パイプラインや資金繰りに関する懸念点があれば指摘してください。
                4. 目標価格設定: 直近のボラティリティから、現実的な目標値と損切りラインを算出してください。
                """
                
                with st.spinner('AIが財務・IR・チャートを統合分析中...'):
                    response = model.generate_content(prompt)
                    st.info(response.text)
            else:
                st.error("データが見つかりませんでした。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

st.caption("※ファンダメンタルズ（PER/PBR/時価総額など）の項目を追加しました。")
