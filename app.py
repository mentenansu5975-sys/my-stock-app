import streamlit as st
import yfinance as yf
import google.generativeai as genai

# 1. 見た目を整える
st.title("🚀 AI株価予測アシスタント")
st.write("銘柄コードを入力すると、最新の推移からAIが予測を立てます。")

# 2. 設定（サイドバーにAPIキーを入れる欄を作る）
with st.sidebar:
    api_key = st.text_input("Gemini API Keyを入力", type="password")
    ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")

if st.button("分析を開始"):
    if not api_key:
        st.error("APIキーを入力してください。")
    else:
        # AIの準備
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 株価データの取得
        with st.spinner('データを取得中...'):
            data = yf.download(ticker, period="1mo")
            
        if not data.empty:
            # グラフの表示
            st.subheader(f"{ticker} の株価推移（直近1ヶ月）")
            st.line_chart(data['Close'])
            
            # AI分析
            st.subheader("🤖 AIによる分析レポート")
            recent_prices = data['Close'].tail(7).to_string()
            prompt = f"銘柄{ticker}の直近価格推移:\n{recent_prices}\nこれに基づき、短期的な展望を初心者にわかりやすく解説して。"
            
            response = model.generate_content(prompt)
            st.write(response.text)
        else:
            st.error("株価データが見つかりませんでした。")
