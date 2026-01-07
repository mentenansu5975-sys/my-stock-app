import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
import pandas as pd
import time

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・最終安定版", layout="wide")

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
    st.title("🏦 AI投資顧問・最終安定版")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 7203.T)", value="4592.T")
        
        st.header("2. PDFアップロード")
        uploaded_file = st.file_uploader("決算資料PDFを選択", type="pdf")
        
        st.header("3. 外部サイト")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")

    if st.button("分析を開始"):
        try:
            # --- API接続の安定化設定 ---
            genai.configure(api_key=api_key)
            
            # モデルの初期化（もっとも標準的な呼び出し方）
            model = genai.GenerativeModel('gemini-1.5-flash')
            
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
                # ニュース抽出
                news_text = ""
                if news_data:
                    for n in news_data[:10]:
                        news_text += f"- {n.get('title')}\n"

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"📈 株価トレンド ({ticker})")
                    st.line_chart(data['Close'])
                    st.subheader("📰 直近ニュース見出し")
                    st.write(news_text if news_text else "ニュースなし")

                # AIへの詳細な指示
                prompt = f"""
                あなたは証券アナリストです。銘柄 {ticker} を分析してください。
                
                【最新ニュース】\n{news_text}
                【PDF情報】\n{pdf_content if pdf_content else "なし"}
                【最新株価データ】\n{data['Close'].tail(5).to_string()}

                【指示】
                1. 直近のIRやニュースから、今の「買い材料・売り材料」を明確にしてください。
                2. バイオ等の場合は、承認状況や薬価等の最新フェーズを考慮してください。
                3. 具体的な「投資判断」と「目標ライン」を提示してください。
                """
                
                with st.spinner('AIが最新データを読み込み中...'):
                    # サーバー側の負荷分散のため、ほんの少し待機
                    time.sleep(2)
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        st.subheader("🤖 AI分析レポート")
                        st.info(response.text)
                    else:
                        st.warning("AIから回答が得られませんでした。もう一度お試しください。")

            else:
                st.error("株価データが取得できませんでした。コードが正しいか確認してください。")
                
        except Exception as e:
            # エラーメッセージをより詳細に表示
            if "404" in str(e):
                st.error("モデルが見つかりません。APIキーの設定やGoogle AI Studioの利用規約を確認してください。")
            elif "429" in str(e):
                st.error("回数制限です。1分ほど待ってから再度「分析を開始」を押してください。")
            else:
                st.error(f"エラーが発生しました: {e}")

st.caption("※API接続を最も標準的な形式に修正しました。")
