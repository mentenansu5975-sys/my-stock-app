import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import feedparser # RSS読み込み用
import time

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・RSSニュース版", layout="wide")

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
    st.title("🏦 AI投資顧問・RSSニュース＆最新IR解析")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 7203.T)", value="4592.T")
        
        st.header("2. 資料アップロード")
        uploaded_file = st.file_uploader("決算短信などのPDFを選択", type="pdf")
        
        st.header("3. 外部情報リンク")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を確認](https://kabutan.jp/stock/news?code={code_only})")
        st.markdown("---")
        
        st.header("4. RSSニュース設定")
        rss_on = st.checkbox("全体市況RSSを読み込む", value=True)
        # 代表的な投資ニュースのRSSフィード
        rss_urls = [
            "https://kabutan.jp/news/rss/", # 株探 最新ニュース
            "https://www.nikkei.com/rss/category/market.rdf" # 日経マーケット
        ]

    # メイン画面
    if st.button("分析を開始"):
        try:
            genai.configure(api_key=api_key)
            # あなたの環境で最も安定して動く可能性が高いモデルを指定
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # --- 1. 株価データの取得 ---
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            
            # --- 2. RSSニュースの自動取得 ---
            rss_text = ""
            if rss_on:
                with st.spinner('RSSフィードから最新市況を取得中...'):
                    for url in rss_urls:
                        feed = feedparser.parse(url)
                        for entry in feed.entries[:5]: # 各サイト上位5件
                            rss_text += f"- {entry.title} ({entry.link})\n"

            # --- 3. PDF解析 ---
            pdf_content = ""
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    pdf_content += page.extract_text()

            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({ticker})")
                    st.line_chart(data['Close'])
                    
                    st.subheader("🌐 最新マーケット見出し (RSS自動取得)")
                    if rss_text:
                        st.write(rss_text)
                    else:
                        st.write("RSS情報の取得に失敗、またはオフです。")

                # --- 4. AIレポート作成 ---
                prompt = f"""
                あなたはシニア投資アナリストです。銘柄 {ticker} について総合分析してください。

                【全体市況・最新ニュース (RSS)】
                {rss_text if rss_text else "取得なし"}

                【PDFから抽出した最新IR】
                {pdf_content[:3000] if pdf_content else "なし"}

                【直近の株価推移】
                {data['Close'].tail(5).to_string()}

                【指示】
                1. RSSの全体市況がこの銘柄に与える影響（地合い）を分析してください。
                2. PDFや株価から、この企業の直近の強みと弱みを整理してください。
                3. 具体的な「買い」「売り」「様子見」の判断と、その根拠を提示してください。
                """
                
                with st.spinner('AIが情報を統合して分析中...'):
                    time.sleep(2) # 429エラー対策
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI総合分析レポート")
                    st.info(response.text)
            else:
                st.error("株価データが取得できません。コードを確認してください。")
        except Exception as e:
            if "429" in str(e):
                st.error("【回数制限】無料枠の上限です。1〜2分待ってから再度お試しいただくか、明日お試しください。")
            else:
                st.error(f"エラーが発生しました: {e}")

st.caption("※RSS機能と最新モデル接続を統合しました。")
