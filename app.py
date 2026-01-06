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
    # RSIの計算 (14日間)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # 移動平均
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
        # デフォルトを6ヶ月にしてより長期を見れるように
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
            
            # 株価データの取得（分析用に1年分取得）
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y") 
            data = add_indicators(data)
            
            if not data.empty:
                # ニュース取得
                news = stock.news
                news_text = "\n".join([f"- {n.get('title')} ({pd.to_datetime(n.get('providerPublishTime'), unit='s').strftime('%Y-%m-%d')})" for n in news[:5]])

                # 統計データの算出（過去3ヶ月分）
                recent_3mo = data.tail(60)
                stats = {
                    "3ヶ月最高値": f"{recent_3mo['High'].max():.1f}",
                    "3ヶ月最安値": f"{recent_3mo['Low'].max():.1f}",
                    "現在のRSI": f"{data.iloc[-1]['RSI']:.1f}",
                    "MA75乖離率": f"{((data.iloc[-1]['Close'] / data.iloc[-1]['MA75']) - 1) * 100:.1f}%"
                }

                # 表示
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価推移 (5日/25日/75日線)")
                    st.line_chart(data[['Close', 'MA5', 'MA25', 'MA75']].tail(120))
                    st.subheader("📊 過熱感 (RSI: 70以上で買われすぎ / 30以下で売られすぎ)")
                    st.line_chart(data['RSI'].tail(120))
                
                with col2:
                    st.subheader("🔢 統計・テクニカル")
                    for k, v in stats.items():
                        st.write(f"**{k}**: {v}")
                    st.write("---")
                    st.subheader("📰 最新ニュース")
                    st.write(news_text)

                # AIへの指示（プロンプト）の強化
                st.subheader("🤖 AIによる多角型・投資判断レポート")
                recent_1mo = data.tail(20).to_string() # 1ヶ月分に拡大
                
                prompt = f"""
                あなたは機関投資家向けのチーフストラテジストです。
                銘柄 {ticker} について、中長期的な視点も含めた投資判断を以下の形式で行ってください。

                【分析用データ（直近20営業日）】
                {recent_1mo}

                【過去3ヶ月の統計値】
                {stats}

                【最新ニュース】
                {news_text}

                【報告内容】
                1. トレンド分析: 短期・中長期の移動平均線の並びから、今のトレンドが本物かどうか判断してください。
                2. 過熱感分析: RSIと乖離率から、現在の価格が「買い時」か「待ち」か判断してください。
                3. 材料分析: ニュースの内容が今後の業績にどう寄与するか、また株価に織り込まれているか推察してください。
                4. 具体的なシナリオ: 上放れした場合の目標値、下振れた場合の損切りラインを論理的に提示してください。
                """
                
                with st.spinner('AIが膨大なデータを精査中...'):
                    response = model.generate_content(prompt)
                    st.success("分析レポート作成完了")
                    st.info(response.text)
            else:
                st.error("データが見つかりませんでした。")
        except Exception as e:
            st.error(f"エラー: {e}")

st.caption("※分析期間を広げ、75日移動平均線とRSIを追加しました。")
