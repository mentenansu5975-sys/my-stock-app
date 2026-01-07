import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import feedparser
import time
import ssl

# SSL証明書エラーを無視してRSSを取得する設定（エラー対策）
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・完全版", layout="wide")

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
    st.title("🏦 AI投資顧問・完全版（RSS＆期間選択対応）")

    # --- サイドバーの設定 ---
    with st.sidebar:
        st.header("1. 銘柄・チャート設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4592.T)", value="4592.T")
        
        # 【追加】期間選択機能
        period_choice = st.selectbox(
            "表示期間を選択",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            format_func=lambda x: {"1mo":"1ヶ月", "3mo":"3ヶ月", "6mo":"半年", "1y":"1年", "2y":"2年", "5y":"5年"}[x],
            index=3 # デフォルトは1年
        )
        
        st.header("2. 資料アップロード")
        uploaded_file = st.file_uploader("決算資料PDFを選択", type="pdf")
        
        st.header("3. 外部・RSS設定")
        # 【追加】株探リンク
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")
        
        rss_on = st.checkbox("RSSニュース取得を有効化", value=True)
        # 代表的なRSSフィード
        rss_urls = [
            "https://kabutan.jp/news/rss/",
            "https://www.watch.impress.co.jp/data/rss/1.0/ipw/index.rdf"
        ]
        st.info("※RSSが失敗する場合はサイドバーの警告を確認してください。")

    # --- メイン処理 ---
    if st.button("総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            # あなたの環境でリストにあった最新かつ安定なモデルを使用
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # --- 1. 株価データの取得（選択した期間で取得） ---
            stock = yf.Ticker(ticker)
            data = stock.history(period=period_choice)
            
            # --- 2. RSSニュースの自動取得 ---
            rss_text = ""
            if rss_on:
                with st.spinner('最新マーケット情報をRSS取得中...'):
                    for url in rss_urls:
                        try:
                            feed = feedparser.parse(url)
                            if feed.entries:
                                for entry in feed.entries[:5]:
                                    rss_text += f"- {entry.title}\n"
                        except Exception:
                            pass # 個別のRSSエラーは無視して続行

            # --- 3. PDF解析 ---
            pdf_content = ""
            if uploaded_file:
                with st.spinner('PDFを解析中...'):
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        pdf_content += page.extract_text()

            # --- 4. 画面表示とAI分析 ---
            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({ticker}) - 期間: {period_choice}")
                    st.line_chart(data['Close'])
                    
                    st.subheader("🌐 RSS最新ニュース見出し")
                    st.write(rss_text if rss_text else "取得なし（またはオフ）")

                # AIへの詳細指示
                prompt = f"""
                あなたはシニア証券アナリストです。銘柄 {ticker} について総合的に判断してください。
                
                【直近のニュース見出し】\n{rss_text if rss_text else "なし"}
                【最新IR資料(PDF)】\n{pdf_content[:2500] if pdf_content else "なし"}
                【株価推移データ】\n{data['Close'].tail(7).to_string()}

                指示：
                1. マクロ環境（ニュース）とこの銘柄の状況を照らし合わせてください。
                2. チャート推移から見た売買ポイントを解説してください。
                3. 明確な投資判断とその根拠、想定されるリスクを述べてください。
                """
                
                with st.spinner('AIが最終レポートを作成中...'):
                    # 429エラー(クォータ制限)対策で微調整
                    time.sleep(2)
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI総合投資判断")
                    st.info(response.text)
            else:
                st.error("株価データが取得できません。銘柄コードが正しいか確認してください。")
        except Exception as e:
            if "429" in str(e):
                st.error("【回数制限】Google AIの無料枠上限に達しました。1〜2分待ってからやり直すか、明日までお待ちください。")
            else:
                st.error(f"エラーが発生しました: {e}")

st.caption("※RSS・SSL対策・期間選択を統合した完全版です。")
