import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import numpy as np
import time

# 1. ページの設定
st.set_page_config(page_title="AI投資顧問・IR統合版", layout="wide")

# 2. パスワード認証
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("🔒 ログインが必要です")
    user_password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if user_password == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません")
    return False

# 3. 指標計算
def add_indicators(df):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA25'] = df['Close'].rolling(window=25).mean()
    df['MA75'] = df['Close'].rolling(window=75).mean()
    return df

if check_password():
    st.title("🏦 AI投資顧問・IR/アナリスト統合版")

    with st.sidebar:
        st.header("分析条件")
        api_key = st.secrets["GEMINI_API_KEY"]
        ticker = st.text_input("銘柄コード (例: 4588.T)", value="4588.T")
        period = st.selectbox("チャート表示期間", ["1y", "2y", "5y"], index=0)
        if st.button("ログアウト"):
            st.session_state["password_correct"] = False
            st.rerun()

    if st.button("深層IR分析を開始"):
        try:
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in models if "gemini-1.5-flash" in m), models[0])
            model = genai.GenerativeModel(target_model)
            
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y") # 統計用に2年分取得
            data = add_indicators(data)
            
            # --- 【新機能】多角的なIR/市場データの取得 ---
            info = stock.info
            
            # アナリストの評価
            recommendations = stock.recommendations
            recom_summary = recommendations.tail(5).to_string() if recommendations is not None else "データなし"
            
            # IRスケジュール（決算日など）
            calendar = stock.calendar
            calendar_info = str(calendar) if calendar is not None else "未定"
            
            # 株主還元（配当・分割）
            actions = stock.actions.tail(5)
            actions_info = actions.to_string() if not actions.empty else "直近の配当・分割なし"
            
            # 企業概要（AIが事業内容を理解するため）
            business_summary = info.get('longBusinessSummary', '概要データなし')[:500] + "..."

            if not data.empty:
                # ニュース取得（件数を10件に増加）
                news = stock.news
                news_list = []
                if news:
                    for n in news[:10]:
                        raw_time = n.get('providerPublishTime')
                        date_str = pd.to_datetime(raw_time, unit='s').strftime('%Y-%m-%d') if raw_time else "不明"
                        news_list.append(f"- {n.get('title')} ({date_str})")
                    news_text = "\n".join(news_list)
                else:
                    news_text = "関連ニュースなし"

                # 画面表示
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader("📈 2年チャート (5/25/75日線)")
                    st.line_chart(data[['Close', 'MA5', 'MA25', 'MA75']].tail(250))
                    st.subheader("📰 最新ニュース・材料 (10件)")
                    st.write(news_text)
                
                with col2:
                    st.subheader("🗓️ IR/アナリスト情報")
                    st.write("**次回決算/予定:**")
                    st.write(calendar_info)
                    st.write("**アナリスト評価(直近):**")
                    st.code(recom_summary)
                    st.write("**株主還元履歴:**")
                    st.code(actions_info)
                    st.write("---")
                    st.write("**時価総額:**", f"{info.get('marketCap', 0) / 100000000:.1f} 億円")
                    st.write("**PBR:**", info.get('priceToBook', 'N/A'))
                    st.write("**自己資本比率:**", info.get('debtToEquity', 'N/A'))

                # AIレポート作成
                st.subheader("🤖 AIによる過去1年の総括と将来予測")
                # 過去1年の4半期ごとの動きをAIに伝えやすくするため月別データを抽出
                monthly_data = data.resample('ME').last().tail(12).to_string()
                
                prompt = f"""
                あなたはプロの投資戦略家（ストラテジスト）です。
                銘柄 {info.get('longName')} ({ticker}) について、過去1年の動きを総括し、今後の展望をレポートしてください。

                【事業内容】
                {business_summary}

                【過去1年の月次株価推移】
                {monthly_data}

                【IR・アナリストデータ】
                予定: {calendar_info}
                アナリスト動向: {recom_summary}
                配当・分割: {actions_info}

                【最新ニュース材料】
                {news_text}

                【指示：プロの視点で深掘りしてください】
                1. 過去1年の振り返り: チャートとニュースを照らし合わせ、何が株価を動かしたのか（決算、IR、外部要因）を時系列で推察してください。
                2. ファンダメンタルズ評価: 現在の時価総額や財務状況から、この企業の「成長性」と「倒産/減配リスク」を評価してください。
                3. アナリストとの乖離: プロの予想（Recommendations）と実際の値動きに乖離があるか、あるならその理由を考察してください。
                4. 投資家への最終助言: 次回のIR（決算）に向けて、今仕込むべきか、決算を見てから動くべきか、具体的な戦略を提示してください。
                """
                
                with st.spinner('AIが1年分のIR資料と市場データを照合中...'):
                    time.sleep(1) # API制限対策
                    response = model.generate_content(prompt)
                    st.success("深層レポート作成完了")
                    st.info(response.text)
            else:
                st.error("株価データを取得できませんでした。")
        except Exception as e:
            st.error(f"分析中にエラーが発生しました: {e}")

st.caption("※IRスケジュール、アナリスト評価、株主還元の項目を統合しました。")
