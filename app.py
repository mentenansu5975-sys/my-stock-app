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

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・Googleニュース連携版", layout="wide")

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
    st.title("🏦 AI投資顧問・プロ仕様（Googleニュース＆多重取得版）")

    # --- サイドバー設定 ---
    with st.sidebar:
        st.header("1. 銘柄・チャート設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4592.T)", value="4592.T")
        
        period_choice = st.selectbox(
            "チャート表示期間",
            options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            format_func=lambda x: {"1mo":"1ヶ月", "3mo":"3ヶ月", "6mo":"半年", "1y":"1年", "2y":"2年", "5y":"5年"}[x],
            index=3
        )
        
        st.header("2. 資料アップロード")
        uploaded_file = st.file_uploader("決算資料PDFを読み込む", type="pdf")
        
        st.header("3. 外部・ニュース設定")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")
        
        rss_on = st.checkbox("Googleニュース自動取得を有効化", value=True)

    # --- メイン画面：手動入力欄 ---
    st.subheader("📝 最新ニュース・IR本文（コピペ用）")
    manual_news = st.text_area("株探などの詳細なニュース本文をここに貼ると、AIの分析精度が最大化されます。", height=100)

    # --- 分析実行 ---
    if st.button("総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-flash-latest')
            
            # 1. 株価データ取得
            stock = yf.Ticker(ticker)
            data = stock.history(period=period_choice)
            stock_info = stock.info
            company_name = stock_info.get('longName', ticker)
            
            # 2. 多重ニュース取得ロジック（GoogleニュースRSS & Yahoo Finance）
            combined_news = ""
            if rss_on:
                with st.spinner('最新ニュースを検索中...'):
                    # A. Yahoo Finance ニュース
                    try:
                        yf_news = stock.news
                        if yf_news:
                            for n in yf_news[:5]:
                                combined_news += f"- [Yahoo] {n.get('title')}\n"
                    except: pass
                    
                    # B. GoogleニュースRSS (キーワード検索)
                    try:
                        query = urllib.parse.quote(f"{company_name} ニュース")
                        gn_url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
                        feed = feedparser.parse(gn_url)
                        for entry in feed.entries[:8]:
                            combined_news += f"- [Google] {entry.title}\n"
                    except: pass

            # 3. PDF解析
            pdf_content = ""
            if uploaded_file:
                with st.spinner('PDFを解析中...'):
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        pdf_content += page.extract_text()

            # 4. 画面表示とレポート生成
            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({company_name})")
                    st.line_chart(data['Close'])
                    
                    st.subheader("🌐 最新ニュース見出し")
                    if combined_news:
                        st.write(combined_news)
                    else:
                        st.write("自動ニュース取得なし。手動入力を活用してください。")

                # AIプロンプト
                prompt = f"""
                あなたは機関投資家レベルのアナリストです。銘柄 {company_name} ({ticker}) を分析してください。
                【ニュース】\n{combined_news if combined_news else "なし"}
                【手動入力材料】\n{manual_news if manual_news else "なし"}
                【PDF IR資料】\n{pdf_content[:3000] if pdf_content else "なし"}
                【最新株価データ】\n{data['Close'].tail(7).to_string()}

                指示：
                1. 現在の「買い材料」と「売り材料」を整理してください。
                2. バイオ株等の場合は治験進捗や承認リスクを、他業種の場合は業績推移を重視してください。
                3. 明確な「投資判断（買い・売り・様子見）」と、その具体的な理由を述べてください。
                """
                
                with st.spinner('AIが精密レポートを作成中...'):
                    time.sleep(1)
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI総合投資判断")
                    st.info(response.text)
            else:
                st.error("株価データが取得できません。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

st.caption("※Googleニュース連携・Yahoo多重取得・期間選択対応。最も安定した構成です。")
