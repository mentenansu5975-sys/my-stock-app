import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import time

st.set_page_config(page_title="AI投資顧問・最新モデル版", layout="wide")

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
    st.title("🏦 AI投資顧問・最新モデル運用版")

    with st.sidebar:
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4592.T)", value="4592.T")
        uploaded_file = st.file_uploader("決算資料PDFを選択", type="pdf")
        st.info("あなたの環境では最新の Gemini 2.0/2.5 が利用可能です。")

    if st.button("最新モデルで分析を開始"):
        try:
            genai.configure(api_key=api_key)
            
            # --- あなたのリストにある「確実に存在する最新モデル」を指定 ---
            # experimentalではない安定版の 2.0 flash を使用します
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            news_data = stock.news 

            if not data.empty:
                with st.spinner('最新AI (Gemini 2.0) が分析中...'):
                    # PDF解析
                    pdf_text = ""
                    if uploaded_file:
                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            pdf_text += page.extract_text()

                    # ニュース抽出
                    news_text = ""
                    if news_data:
                        for n in news_data[:5]:
                            news_text += f"- {n.get('title')}\n"

                    # プロンプト（指示）
                    prompt = f"""
                    あなたは最新鋭のAIアナリストです。銘柄 {ticker} を分析してください。
                    
                    【最新ニュース】\n{news_text}
                    【PDF資料】\n{pdf_text[:2000] if pdf_text else "なし"}
                    【株価推移】\n{data['Close'].tail(7).to_string()}

                    指示：
                    1. ニュースやPDFから、現在の企業のフェーズ（承認状況、業績等）を正しく把握してください。
                    2. 直近の株価推移とあわせて、今後の「買い時」をプロの視点で提言してください。
                    """
                    
                    # 回数制限（429）を避けるために実行前に少し待機
                    time.sleep(2)
                    response = model.generate_content(prompt)
                    
                    st.success("分析が完了しました！")
                    st.info(response.text)
            else:
                st.error("株価データが取得できません。")
                
        except Exception as e:
            if "429" in str(e):
                st.error("【回数制限】最新モデルは利用者が多いため、1分ほど空けてから再度お試しください。")
            else:
                st.error(f"エラーが発生しました: {e}")

st.caption("※利用可能リストに基づき、モデルを gemini-2.0-flash に最適化しました。")
