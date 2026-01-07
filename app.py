import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import feedparser
import time
import ssl # SSLエラー対策用

# SSL証明書エラーを無視してRSSを取得する設定
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="AI投資顧問・RSS強化版", layout="wide")

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
    st.title("🏦 AI投資顧問・RSS強化版")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード", value="4592.T")
        
        st.header("2. PDFアップロード")
        uploaded_file = st.file_uploader("決算資料PDF", type="pdf")
        
        st.header("3. RSS設定")
        rss_on = st.checkbox("ニュース自動取得を有効化", value=True)
        # より安定して取得できるRSSフィードに変更
        rss_urls = [
            "https://kabutan.jp/news/rss/", # 株探
            "https://www.watch.impress.co.jp/data/rss/1.0/ipw/index.rdf" # 経済ニュース等
        ]

    if st.button("総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # データ取得
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            
            # --- RSS取得ロジックの強化 ---
            rss_text = ""
            if rss_on:
                with st.spinner('ニュースを取得中...'):
                    for url in rss_urls:
                        try:
                            feed = feedparser.parse(url)
                            if feed.entries:
                                for entry in feed.entries[:5]:
                                    rss_text += f"- {entry.title}\n"
                        except Exception as rss_e:
                            st.sidebar.warning(f"RSS取得エラー: {url}")
            
            # PDF解析
            pdf_content = ""
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    pdf_content += page.extract_text()

            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価トレンド")
                    st.line_chart(data['Close'])
                    
                    st.subheader("🌐 自動取得ニュース（最新）")
                    if rss_text:
                        st.write(rss_text)
                    else:
                        st.warning("RSSデータの取得に失敗しました。サイト側の制限の可能性があります。")

                # AIレポート作成
                prompt = f"""
                あなたは証券アナリストです。銘柄 {ticker} を分析してください。
                【市場ニュース】\n{rss_text if rss_text else "取得失敗"}
                【PDF IR情報】\n{pdf_content[:2000] if pdf_content else "なし"}
                【株価推移】\n{data['Close'].tail(5).to_string()}

                指示：
                1. ニュースやPDFから、現在の状況を整理してください。
                2. 具体的な投資判断を提示してください。
                """
                
                with st.spinner('AI分析中...'):
                    time.sleep(2)
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI分析レポート")
                    st.info(response.text)
            else:
                st.error("株価データの取得に失敗しました。")
        except Exception as e:
            st.error(f"エラー: {e}")
