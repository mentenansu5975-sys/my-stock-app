import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import time

st.set_page_config(page_title="AI投資顧問・万能版", layout="wide")

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
    st.title("🏦 AI投資顧問・万能版（全業種・最新IR対応）")

    with st.sidebar:
        st.header("1. 銘柄設定")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 7203.T, 4592.T)", value="7203.T")
        
        st.header("2. 一次ソース（最新情報）")
        code_only = ticker.split('.')[0]
        st.markdown(f"👉 [株探で最新情報を確認](https://kabutan.jp/stock/news?code={code_only})")
        st.info("↑ここで最新の「決算」や「修正」を確認し、重要なテキストを下の欄に貼ってください。")

    # 手動入力欄
    st.subheader("📝 最新のIR情報や気になるニュースを貼り付けてください")
    manual_ir = st.text_area("決算短信の要約、月次データ、適時開示の内容など", 
                             placeholder="例：今期の純利益を20%上方修正。増配も発表。原材料高は懸念材料。", height=150)

    if st.button("AI総合分析を開始"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y")
            info = stock.info

            if not data.empty:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 株価トレンド")
                    st.line_chart(data['Close'].tail(200))
                with col2:
                    st.subheader("📊 財務指標")
                    st.write(f"**会社名:** {info.get('longName', 'N/A')}")
                    st.write(f"**時価総額:** {info.get('marketCap', 0) // 100000000}億円")
                    st.write(f"**PER:** {info.get('trailingPE', 'N/A')}")
                    st.write(f"**PBR:** {info.get('priceToBook', 'N/A')}")
                    st.write(f"**業種:** {info.get('sector', 'N/A')}")

                # AIへの指示（全業種対応プロンプト）
                prompt = f"""
                あなたは、あらゆる業種に精通したトップクラスの証券アナリストです。
                対象銘柄: {info.get('longName')} ({ticker})

                【ユーザー提供の最新・最優先情報】
                {manual_ir if manual_ir else "特になし。公開データのみで分析せよ。"}

                【市場データ】
                業種: {info.get('sector')}
                直近株価推移: {data['Close'].tail(20).to_string()}
                財務指標: PER {info.get('trailingPE')}, PBR {info.get('priceToBook')}
                
                【指示】
                1. 業種特有の分析: この銘柄の属する「{info.get('sector')}」という業種の特性（景気敏感、ディフェンシブ、成長期待など）を考慮して分析してください。
                2. 最新情報の評価: ユーザーが提供したIR情報がある場合、それが「株価に織り込み済みか」「今後さらに上振れる材料か」をプロの視点で評価してください。
                3. 財務とチャートの統合: 財務面（割安・割高）とチャート面（トレンド）が一致しているか、矛盾しているならその理由を考察してください。
                4. 投資アクション: 具体的な「買い」「売り」「様子見」の判断と、その根拠となる目標株価・損切りラインを提示してください。
                """
                
                with st.spinner('各業種専門の知見を統合して分析中...'):
                    response = model.generate_content(prompt)
                    st.success("多角分析レポート完了")
                    st.info(response.text)
            else:
                st.error("株価データを取得できませんでした。")
        except Exception as e:
            st.error(f"エラー: {e}")

st.caption("※全業種対応版。最新の決算内容を貼り付けることで真価を発揮します。")
