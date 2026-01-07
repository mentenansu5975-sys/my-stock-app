import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import feedparser
import time
import ssl

# SSLエラー対策（RSS取得を安定させるため）
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・プロフェッショナル", layout="wide")

# パスワード認証機能
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
    st.title("🏦 AI投資顧問・プロフェッショナル（多重ニュース取得版）")

    # --- サイドバー設定 ---
    with st.sidebar:
        st.header("1. 銘柄・チャート設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4592.T)", value="4592.T")
        
        # 期間選択
        period_choice = st.selectbox(
            "チャート表示期間",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            format_func=lambda x: {"1mo":"1ヶ月", "3mo":"3ヶ月", "6mo":"半年", "1y":"1年", "2y":"2年", "5y":"5年"}[x],
            index=3
        )
        
        st.header("2. 資料アップロード")
        uploaded_file = st.file_uploader("決算短信などのPDFを選択", type="pdf")
        
        st.header("3. 外部・RSS設定")
        code_only = ticker.split('.')[0]
        # 株探リンク
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")
        
        rss_on = st.checkbox("自動ニュース取得(RSS/Yahoo)を有効化", value=True)
        # RSSフィードのリスト
        rss_urls = [
            "https://kabutan.jp/news/rss/",
            "https://www.watch.impress.co.jp/data/rss/1.0/ipw/index.rdf"
        ]

    # --- メイン画面の入力欄（RSSがダメな時のための手動入力） ---
    st.subheader("📝 最新ニュース・IR本文（コピペ用）")
    manual_news = st.text_area("株探のニュース本文などをここに貼ると、分析精度が劇的に上がります。", height=100)

    # --- 分析実行 ---
    if st.button("総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            # あなたの環境で最も安定しているモデル名
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # 1. 株価データ取得
            stock = yf.Ticker(ticker)
            data = stock.history(period=period_choice)
            
            # 2. 多重ニュース取得ロジック
            combined_news = ""
            if rss_on:
                with st.spinner('最新ニュースを収集中...'):
                    # Yahoo Finance経由
                    try:
                        yf_news = stock.news
                        if yf_news:
                            for n in yf_news[:5]:
                                combined_news += f"- [Yahoo] {n.get('title')}\n"
                    except: pass
                    
                    # RSSフィード経由
                    for url in rss_urls:
                        try:
                            feed = feedparser.parse(url)
                            for entry in feed.entries[:3]:
                                combined_news += f"- [RSS] {entry.title}\n"
                        except: continue

            # 3. PDF解析
            pdf_content = ""
            if uploaded_file:
                with st.spinner('PDFを解析中...'):
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        pdf_content += page.extract_text()

            # 4. 画面表示
            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({ticker})")
                    st.line_chart(data['Close'])
                    
                    st.subheader("🌐 取得できた最新ニュース")
                    if combined_news:
                        st.write(combined_news)
                    else:
                        st.write("自動取得ニュースなし。手動入力を活用してください。")

                # AIレポート作成
                prompt = f"""
                あなたはプロの投資家です。銘柄 {ticker} について総合分析をしてください。
                【自動取得ニュース】\n{combined_news if combined_news else "なし"}
                【手動入力ニュース】\n{manual_news if manual_news else "なし"}
                【PDF IR資料】\n{pdf_content[:2500] if pdf_content else "なし"}
                【直近株価データ】\n{data['Close'].tail(5).to_string()}

                指示：
                1. ニュース、PDF、株価の3点から、現在の状況を「買い・売り・様子見」で判断してください。
                2. バイオ銘柄等の場合は、承認状況などの専門的な進捗を重視してください。
                3. 具体的な判断の根拠を、初心者にもわかりやすく提示してください。
                """
                
                with st.spinner('AIがレポートを作成中...'):
                    time.sleep(2) # 回数制限対策
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI総合投資判断")
                    st.info(response.text)
            else:
                st.error("株価データの取得に失敗しました。")
        except Exception as e:
            if "429" in str(e):
                st.error("【回数制限】1分ほど待ってから再度お試しください。")
            else:
                st.error(f"エラーが発生しました: {e}")

st.caption("※RSS/Yahooニュース多重取得・期間選択・手動入力対応の完全版です。")
