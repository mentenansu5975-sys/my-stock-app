import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

st.set_page_config(page_title="プロ版・AI株価予測", layout="wide")
st.title("📈 高機能AI株価予測アシスタント")

with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", type="password")
    ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
    period = st.selectbox("分析期間", ["1mo", "3mo", "6mo"])

if st.button("詳細分析を開始"):
    if not api_key:
        st.error("APIキーを入力してください。")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 1. データの取得
            data = yf.download(ticker, period=period)
            
            if not data.empty:
                # 2. テクニカル指標の計算（簡易版）
                # 移動平均線（5日・25日）
                data['MA5'] = data['Close'].rolling(window=5).mean()
                data['MA25'] = data['Close'].rolling(window=25).mean()
                
                # 3. 画面表示（チャート）
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("株価推移と移動平均線")
                    st.line_chart(data[['Close', 'MA5', 'MA25']])
                
                with col2:
                    st.subheader("最新の数値")
                    latest = data.iloc[-1]
                    st.metric("現在値", f"{latest['Close']:.1f}円")
                    st.write(f"5日平均: {latest['MA5']:.1f}円")

                # 4. AIへの詳細な指示（プロンプト）の作成
                st.subheader("🤖 AIによる詳細投資判断")
                
                # 直近10日間のデータを抽出
                recent_summary = data[['Close', 'Volume']].tail(10).to_string()
                
                prompt = f"""
                あなたはシニア証券アナリストとして、銘柄 {ticker} を分析してください。
                
                【株価・出来高データ（直近10日）】
                {recent_summary}
                
                【分析の指示】
                1. 現在のトレンド（上昇・下落・横ばい）を判断してください。
                2. 出来高の変化から、投資家の関心度を推測してください。
                3. 今後1週間程度の「買い」か「売り」かの投資判断とその理由、注意すべきリスクを専門的に解説してください。
                4. 初心者が次に取るべきアクション（例：押し目買いを待つ、一旦利確するなど）を提案してください。
                """
                
                with st.spinner('深層分析中...'):
                    response = model.generate_content(prompt)
                    st.info(response.text)
                    
            else:
                st.error("データが取得できませんでした。")
        except Exception as e:
            st.error(f"エラー: {e}")

st.caption("※移動平均線(MA)を表示しています。MA5がMA25を上に抜けるとゴールデンクロスの可能性があります。")
