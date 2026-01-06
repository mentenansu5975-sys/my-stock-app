import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

st.set_page_config(page_title="AI株価予測・プロ版", layout="wide")
st.title("📈 高機能AI株価予測アシスタント")

with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", type="password")
    ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
    period = st.selectbox("分析期間", ["3mo", "6mo", "1y"], index=0)

if st.button("詳細分析を開始"):
    if not api_key:
        st.error("APIキーを入力してください。")
    else:
        try:
            # 1. AIの初期設定
            genai.configure(api_key=api_key)
            
            # --- ここから修正したモデル選択ロジック ---
            try:
                # 最新のFlashモデルを試行
                model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
                # 動作確認のために空のテストをしないよう、ここでは定義のみ
            except:
                # 失敗した場合は利用可能なモデルを自動取得
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model = genai.GenerativeModel(available_models[0])
            # --- ここまで ---
            
            # 2. 株価データの取得
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            if not data.empty:
                # 3. テクニカル指標の計算（移動平均）
                data['MA5'] = data['Close'].rolling(window=5).mean()
                data['MA25'] = data['Close'].rolling(window=25).mean()
                
                # 4. 最新ニュースの取得
                news = stock.news
                news_text = ""
                if news:
                    for n in news[:3]: # 直近3件
                        news_text += f"- {n.get('title', '')}\n"
                else:
                    news_text = "直近の関連ニュースは見当たりません。"

                # 5. 画面表示（チャート）
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("株価推移と移動平均線")
                    st.line_chart(data[['Close', 'MA5', 'MA25']])
                
                with col2:
                    st.subheader("現在のステータス")
                    latest = data.iloc[-1]
                    prev_close = data.iloc[-2]['Close']
                    diff = latest['Close'] - prev_close
                    st.metric("現在値", f"{latest['Close']:.1f}円", f"{diff:+.1f}円")
                    st.write("**直近のトピックス:**")
                    st.write(news_text)

                # 6. AIへの詳細な指示
                st.subheader("🤖 AIによる深層分析レポート")
                recent_summary = data[['Close', 'Volume']].tail(10).to_string()
                
                prompt = f"""
                あなたはシニア証券アナリストです。銘柄 {ticker} について分析してください。
                
                【株価・出来高データ（直近10日）】
                {recent_summary}
                
                【最新ニュース】
                {news_text}
                
                【指示】
                1. テクニカル分析（MA5とMA25の関係）から見たトレンド解説。
                2. ニュースが株価に与える影響の考察。
                3. 今後の短期的な見通しと、推奨する投資行動の提案。
                """
                
                with st.spinner('AIが材料とチャートを分析中...'):
                    response = model.generate_content(prompt)
                    st.info(response.text)
                    
            else:
                st.error("データが取得できませんでした。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

st.caption("※この分析は移動平均線とYahoo Financeニュースに基づいています。投資判断は自己責任でお願いします。")         
      
