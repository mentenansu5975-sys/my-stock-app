import streamlit as st
import yfinance as yf
import google.generativeai as genai

# 1. 見た目を整える
st.set_page_config(page_title="AI株価予測アプリ", layout="centered")
st.title("🚀 AI株価予測アシスタント")
st.write("銘柄コードを入力すると、AIが最新データから予測を立てます。")

# 2. サイドバーの設定
with st.sidebar:
    st.header("設定")
    # APIキーを入力する欄（Colabで成功したキーを入れてください）
    api_key = st.text_input("Gemini API Keyを入力", type="password")
    # 銘柄コードの入力
    ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
    st.info("日本株は末尾に .T をつけてください（例: 7203.T）")

# 3. メイン処理
if st.button("分析を開始"):
    if not api_key:
        st.error("左側のサイドバーにAPIキーを入力してください。")
    else:
        try:
            # AIの初期設定
            genai.configure(api_key=api_key)
            
            # 【重要】Colabで成功した「自動モデル選択」ロジック
            with st.spinner('AIモデルを確認中...'):
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                if not available_models:
                    st.error("利用可能なAIモデルが見つかりませんでした。")
                    st.stop()
                target_model = available_models[0]
                model = genai.GenerativeModel(target_model)
            
            # 株価データの取得
            with st.spinner('株価データを取得中...'):
                data = yf.download(ticker, period="1mo")
            
            if not data.empty:
                # 株価チャートの表示
                st.subheader(f"📈 {ticker} の株価推移")
                st.line_chart(data['Close'])
                
                # AI分析の実行
                st.subheader("🤖 AIによる短期予測レポート")
                recent_prices = data['Close'].tail(7).to_string()
                
                # AIへの指示文
                prompt = f"""
                あなたはプロの投資家です。
                以下の銘柄 {ticker} の直近株価データに基づき、
                今後の短期的な展望を100文字程度で予測してください。
                
                【直近価格データ】
                {recent_prices}
                """
                
                with st.spinner('AIが思考中...'):
                    response = model.generate_content(prompt)
                    st.success("分析が完了しました！")
                    st.write(response.text)
                    
            else:
                st.error("株価データが見つかりませんでした。銘柄コードが正しいか確認してください。")
                
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info("1分間に何度も実行すると制限がかかる場合があります。少し待ってからお試しください。")

# フッター
st.caption("※このアプリは投資の助言を行うものではありません。自己責任でご利用ください。")
