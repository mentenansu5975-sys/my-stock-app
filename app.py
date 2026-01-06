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

# 3. テクニカル指標計算用関数
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
    st.title("🏦 AI投資顧問・エグゼクティブ版")

    with st.sidebar:
        st.header("分析条件")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
        period = st.selectbox("分析スパン", ["6mo", "1y", "2y"], index=0)
        
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
            
            if not data.empty:
                # --- 【修正箇所】ニュース取得のエラー対策 ---
                news = stock.news
                news_list = []
                if news:
                    for n in news[:5]:
                        title = n.get('title', 'No Title')
                        # 日付が取得できない場合(None)への対策
                        raw_time = n.get('providerPublishTime')
                        if raw_time:
                            date_str = pd.to_datetime(raw_time, unit='s').strftime('%Y-%m-%d')
                        else:
                            date_str = "不明"
                        news_list.append(f"- {title} ({date_str})")
                    news_text = "\n".join(news_list)
                else:
                    news_text = "直近の関連ニュースは見当たりません。"

                # 統計データの算出
                recent_3mo = data.tail(60)
                stats = {
                    "3ヶ月最高値": f"{recent_3mo['High'].max():.1f}",
                    "3ヶ月最安値": f"{recent_3mo['Low'].min():.1f}", # minに修正
                    "現在のRSI": f"{data.iloc[-1]['RSI']:.1f}",
                    "MA75乖離率": f"{((data.iloc[-1]['Close'] / data.iloc[-1]['MA75']) - 1) * 100:.1f}%"
                }

                # 表示
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価推移 (5/25/75日線)")
                    st.line_chart(data[['Close', 'MA5', 'MA25', 'MA75']].tail(120))
                    st.subheader("📊 過熱感 (RSI)")
                    st.line_chart(data['RSI'].tail(120))
                
                with col2:
                    st.subheader("🔢 統計・テクニカル")
                    for k, v in stats.items():
                        st.write(f"**{k}**: {v}")
                    st.write("---")
                    st.subheader("📰 最新ニュース")
                    st.write(news_text)

                # AIレポート作成
                st.subheader("🤖 AIによる多角型・投資判断レポート")
                recent_1mo = data.tail(20).to_string()
                
                prompt = f"""
                あなたは機関投資家向けのチーフストラテジストです。銘柄 {ticker} を分析してください。
                
                【直近20日のデータ】\n{recent_1mo}\n
                【過去3ヶ月の統計】\n{stats}\n
                【最新ニュース】\n{news_text}\n
                
                1. トレンド分析: 短期・中長期の移動平均線から判断。
                2. 過熱感分析: RSIと乖離率から判断。
                3. 材料分析: ニュースが株価に与える影響。
                4. 具体的なシナリオ: 目標値と損切りライン。
                """
                
                with st.spinner('AIが分析中...'):
                    response = model.generate_content(prompt)
                    st.info(response.text)
            else:
                st.error("データが見つかりませんでした。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

st.caption("※ニュースの日付取得エラーを修正しました。")
