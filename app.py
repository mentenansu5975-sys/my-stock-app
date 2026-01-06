import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

# 1. ページの設定
st.set_page_config(page_title="AI株価予測・プロ版", layout="wide")
st.title("📈 高機能AI株価予測アシスタント")

# 2. サイドバーの設定（APIキーはSecretsから読み込むので入力欄はなし）
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

# 3. メイン処理
if st.button("詳細分析を開始"):
    try:
        # AIの初期設定
        genai.configure(api_key=api_key)
        
        # 利用可能なモデルを自動取得するロジック
        with st.spinner('AIモデルを確認中...'):
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # 1.5 Flash を優先的に探し、なければリストの先頭を使う
            target_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])
            model = genai.GenerativeModel(target_model)
        
        # 株価データの取得
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        
        if not data.empty:
            # テクニカル指標（移動平均線）の計算
            data['MA5'] = data['Close'].rolling(window=5).mean()
            data['MA25'] = data['Close'].rolling(window=25).mean()
            
            # 最新ニュースの取得
            news = stock.news
            news_text = ""
            if news:
                for n in news[:3]:
                    news_text += f"- {n.get('title', '')}\n"
            else:
                news_text = "直近の関連ニュースは見当たりません。"

            # 画面表示：左側にチャート、右側に数値
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

            # AIによる分析レポート作成
            st.subheader("🤖 AIアナリストによる詳細予測")
            recent_summary = data[['Close', 'Volume']].tail(10).to_string()
            
            prompt = f"""
            あなたはプロの証券アナリストです。銘柄 {ticker} について分析してください。
            
            【データ】
            株価推移(直近10日):
            {recent_summary}
            
            最新ニュース:
            {news_text}
            
            【指示】
            1. テクニカル（MA5/25）から見た現状の強弱。
            2. ニュースが今後の材料としてどう働くか。
            3. 短期的な展望と、投資家へのアドバイス。
            """
            
            with st.spinner('AIがレポートを作成しています...'):
                response = model.generate_content(prompt)
                st.info(response.text)
                
        else:
            st.error("株価データが見つかりませんでした。銘柄コードを確認してください。")
            
    except Exception as e:
        st.error(f"実行中にエラーが発生しました: {e}")

st.caption("※投資の最終決定はご自身の判断で行ってください。")
