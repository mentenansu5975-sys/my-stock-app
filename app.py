import streamlit as st
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader

# 1. ページ設定
st.set_page_config(page_title="AI投資顧問・自動ニュース版", layout="wide")

# パスワード認証（共通）
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
    st.title("🏦 AI投資顧問・全業種/自動ニュース対応版")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 7203.T)", value="4592.T")
        
        st.header("2. PDFアップロード")
        uploaded_file = st.file_uploader("決算資料PDFがあれば選択", type="pdf")
        
        st.header("3. 外部サイト確認")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を開く](https://kabutan.jp/stock/news?code={code_only})")

    # メイン画面
    if st.button("最新ニュース取得と総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # 株価とニュースの取得
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            news_data = stock.news # ここで最新ニュースを自動取得
            
            # PDF解析
            pdf_content = ""
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    pdf_content += page.extract_text()

            if not data.empty:
                # ニュースをテキスト化
                news_text = ""
                for n in news_data[:8]:
                    news_text += f"- タイトル: {n.get('title')}\n  要約: {n.get('summary', 'なし')}\n"

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価トレンド")
                    st.line_chart(data['Close'])
                    st.subheader("📰 自動取得された最新ニュース")
                    st.write(news_text if news_text else "ニュースは見つかりませんでした")

                # AIレポート作成
                prompt = f"""
                あなたはプロの投資アナリストです。
                
                【最新ニュース（自動取得）】
                {news_text}
                
                【PDFから抽出した最新IR】
                {pdf_content if pdf_content else "添付なし"}

                【株価・財務データ要約】
                {data.tail(5).to_string()}

                【指示】
                1. 「自動取得ニュース」と「PDF資料」を照らし合わせ、最新の企業の状況を解説してください。
                2. 特に、ニュースがポジティブかネガティブか、短期的・長期的な影響を分析してください。
                3. 今後の株価に影響を与える「次のイベント（決算、新製品、承認など）」を推測してください。
                4. 具体的な売買判断（買い・売り・ステイ）を根拠と共に提示してください。
                """
                
                with st.spinner('情報を統合して分析中...'):
                    response = model.generate_content(prompt)
                    st.subheader("🤖 AI総合分析レポート")
                    st.info(response.text)
            else:
                st.error("データの取得に失敗しました。")
        except Exception as e:
            st.error(f"エラー: {e}")
