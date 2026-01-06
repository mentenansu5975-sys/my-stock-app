import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

# 1. ページの設定（一番最初に書く必要があります）
st.set_page_config(page_title="AI株価予測・マイポータル", layout="wide")

# 2. パスワード認証関数
def check_password():
    """パスワードが正しいかチェックする関数"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # すでに認証済みならTrueを返す
    if st.session_state["password_correct"]:
        return True

    # ログイン画面を表示
    st.title("🔒 ログインが必要です")
    user_password = st.text_input("パスワードを入力してください", type="password")
    
    if st.button("ログイン"):
        # Secretsに設定したパスワードと一致するか確認
        if user_password == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません")
    return False

# 3. 認証が成功したときだけメインアプリを表示
if check_password():
    
    st.title("📈 高機能AI株価予測アシスタント")

    # サイドバーの設定
    with st.sidebar:
        st.header("設定")
        try:
            # SecretsからAPIキーを取得
            api_key = st.secrets["GEMINI_API_KEY"]
        except:
            st.error("Secretsに 'GEMINI_API_KEY' が設定されていません。")
            st.stop()
            
        ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
        period = st.selectbox("分析期間", ["3mo", "6mo", "1y"], index=0)
        
        if st.button("ログアウト"):
            st.session_state["password_correct"] = False
            st.rerun()

    # メイン処理
    if st.button("詳細分析を開始"):
        try:
            # AIの初期設定
            genai.configure(api_key=api_key)
            
            with st.spinner('利用可能なAIモデルを探索中...'):
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])
                model = genai.GenerativeModel(target_model)
            
            # 株価データの取得
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            if not data.empty:
                # テクニカル指標の計算
                data['MA5'] = data['Close'].rolling(window=5).mean()
                data['MA25'] = data['Close'].rolling(window=25).mean()
                
                # ニュース取得
                news = stock.news
                news_text = ""
                if news:
                    for n in news[:3]:
                        news_text += f"- {n.get('title', '')}\n"
                else:
                    news_text = "直近の関連ニュースは見当たりません。"

                # 画面表示
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📊 株価推移と移動平均線")
                    st.line_chart(data[['Close', 'MA5', 'MA25']])
                
                with col2:
                    st.subheader("📌 現在のステータス")
                    latest = data.iloc[-1]
                    prev_close = data.iloc[-2]['Close']
                    diff = latest['Close'] - prev_close
                    st.metric("現在値", f"{latest['Close']:.1f}円", f"{diff:+.1f}円")
                    st.write("**最新トピックス:**")
                    st.write(news_text)

                # AIレポート作成
                st.subheader("🤖 AIアナリストによる詳細予測")
                recent_summary = data[['Close', 'Volume']].tail(10).to_string()
                
                prompt = f"""
                あなたはプロの証券アナリストです。銘柄 {ticker} について分析してください。
                【直近10日の株価データ】\n{recent_summary}\n
                【最新ニュース】\n{news_text}\n
                1. テクニカル面(MA5/25)の評価
                2. ニュースの影響
                3. 短期展望とアドバイス
                を専門的に解説してください。
                """
                
                with st.spinner('AIがレポートを作成中...'):
                    response = model.generate_content(prompt)
                    st.info(response.text)
                    
            else:
                st.error("データが見つかりませんでした。")
                
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

    st.caption("※このアプリは非公開設定です。")
