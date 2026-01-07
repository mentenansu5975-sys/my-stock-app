import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import time

st.set_page_config(page_title="AI投資顧問・診断モード", layout="wide")

# パスワード認証 (中身は共通)
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
    st.title("🏦 AI投資顧問・診断モード")

    with st.sidebar:
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード", value="4592.T")
        uploaded_file = st.file_uploader("PDFを選択", type="pdf")

    # --- 診断機能：使えるモデルを表示 ---
    if st.checkbox("【トラブル用】利用可能なモデルをチェック"):
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models()]
            st.write("あなたのAPIキーで利用可能なモデル一覧:")
            st.code(models)
        except Exception as e:
            st.error(f"モデル一覧の取得に失敗しました。APIキーが無効かもしれません。: {e}")

    if st.button("分析を開始"):
        try:
            genai.configure(api_key=api_key)
            
            # 安定性の高い「latest」付きの名前に変更
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            news_data = stock.news 

            if not data.empty:
                # 分析実行
                with st.spinner('分析中...'):
                    # PDF読み込み
                    pdf_text = ""
                    if uploaded_file:
                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            pdf_text += page.extract_text()

                    prompt = f"銘柄 {ticker} について、以下のデータから投資判断をしてください。\n株価:{data['Close'].tail(3).to_string()}\nPDF内容:{pdf_text[:1000]}"
                    
                    response = model.generate_content(prompt)
                    st.success("分析完了")
                    st.info(response.text)
            else:
                st.error("株価データが取得できません。")
                
        except Exception as e:
            st.error(f"エラーが発生しました。詳細は以下を確認してください:\n{e}")
