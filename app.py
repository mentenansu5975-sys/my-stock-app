import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・安定版", layout="wide")

# パスワード認証
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]: return True
    st.title("🔒 ログインが必要です")
    user_password = st.text_input("パスワード入力", type="password")
    if st.button("ログイン"):
        if user_password == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("パスワードが違います")
    return False

if check_password():
    st.title("🏦 AI投資顧問・安定版（モデル自動最適化）")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 7203.T)", value="4592.T")
        
        st.header("2. PDFアップロード")
        uploaded_file = st.file_uploader("決算資料PDFがあれば選択", type="pdf")
        
        st.header("3. 外部サイト確認")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")

    if st.button("分析を開始"):
        try:
            # AIの設定
            genai.configure(api_key=api_key)
            
            # --- 【修正ポイント】利用可能な最新モデルを自動的に探す ---
            with st.spinner('AIモデルを確認中...'):
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # gemini-1.5-flash または gemini-2.0-flash を優先的に探し、なければ最初の一つを使う
                target_model = next((m for m in available_models if "gemini-1.5-flash" in m), 
                                    next((m for m in available_models if "gemini-2.0-flash" in m), available_models[0]))
                model = genai.GenerativeModel(target_model)
            
            # データの取得
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            news_data = stock.news 
            
            # PDF解析
            pdf_content = ""
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    pdf_content += page.extract_text()

            if not data.empty:
                # ニュースを抽出
                news_text = ""
                for n in news_data[:8]:
                    news_text += f"- タイトル: {n.get('title')}\n"

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({ticker})")
                    st.line_chart(data['Close'])
                    st.subheader("📰 直近ニュース見出し")
                    st.write(news_text if news_text else "ニュースなし")

                # AIレポート作成
                prompt = f"""
                あなたはプロの投資アナリストです。銘柄 {ticker} について最新情報を統合してレポートしてください。
                
                【最新ニュース見出し】
                {news_text}
                
                【PDFから抽出したIRテキスト】
                {pdf_content if pdf_content else "なし"}

                【株価推移】
                {data['Close'].tail(5).to_string()}

                【指示】
                1. 最新のIR/ニュースから、この企業の現在の状況（ポジティブかネガティブか）を整理してください。
                2. 株価の動きとニュースに矛盾がないか分析してください。
                3. 具体的な売買判断と、その根拠を提示してください。
                """
                
                with st.spinner(f'モデル {target_model} を使用して分析中...'):
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI分析レポート")
                    st.info(response.text)
            else:
                st.error("株価データの取得に失敗しました。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

st.caption("※モデル名を自動取得する仕様に修正しました。")
