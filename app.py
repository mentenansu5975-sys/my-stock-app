import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import feedparser
import time
import ssl
import urllib.parse

# SSLエラー対策
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="AI投資顧問・安定版", layout="wide")

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
    st.title("🏦 AI投資顧問・プロ（エラー対策済み安定版）")

    with st.sidebar:
        st.header("1. 設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4592.T)", value="4592.T")
        period_choice = st.selectbox("期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
        uploaded_file = st.file_uploader("PDFを選択", type="pdf")
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={ticker.split('.')[0]})")

    st.subheader("📝 最新ニュース本文（コピペ）")
    manual_news = st.text_area("詳細情報をここに貼ると精度が上がります", height=100)

    if st.button("総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            stock = yf.Ticker(ticker)
            data = stock.history(period=period_choice)
            
            combined_news = ""
            # Yahooニュース取得
            try:
                yf_news = stock.news
                if yf_news:
                    for n in yf_news[:5]: combined_news += f"- {n.get('title')}\n"
            except: pass
            
            # Googleニュース取得
            try:
                query = urllib.parse.quote(f"{ticker} ニュース")
                feed = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja")
                for entry in feed.entries[:5]: combined_news += f"- {entry.title}\n"
            except: pass

            # PDF解析（文字数を制限してパンクを防止）
            pdf_content = ""
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                for page in reader.pages[:10]: # 最初の10ページに限定
                    pdf_content += page.extract_text()
                pdf_content = pdf_content[:5000] # 最大5000文字に制限

            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.line_chart(data['Close'])
                    st.write("【取得ニュース】\n", combined_news if combined_news else "なし")

                # AIレポート作成
                prompt = f"""銘柄{ticker}を分析せよ。
                ニュース:{combined_news}
                手動入力:{manual_news}
                PDF内容:{pdf_content}
                株価推移:{data['Close'].tail(5).to_string()}
                指示:最新材料を元に、買い・売り・様子見を根拠と共に判断せよ。"""
                
                with st.spinner('分析中...'):
                    time.sleep(1)
                    response = model.generate_content(prompt)
                    
                    # --- 安全な回答取得処理 ---
                    if response.candidates and response.candidates[0].content.parts:
                        st.subheader("🤖 AI総合投資判断")
                        st.info(response.text)
                    else:
                        st.error(f"AIが回答を生成できませんでした。理由コード: {response.candidates[0].finish_reason}")
                        st.warning("入力したニュースやPDFの内容が不適切、または長すぎる可能性があります。内容を減らして試してください。")
            else:
                st.error("株価データが取得できません。")
        except Exception as e:
            st.error(f"システムエラー: {e}")
