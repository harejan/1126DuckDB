# 使用 Python 3.9 作為基底
FROM python:3.9-slim

# 1. 為了安全性，Hugging Face 要求使用非 root 使用者 (id 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# 2. 設定工作目錄
WORKDIR /app

# 3. 複製套件清單並安裝
# --chown=user 確保權限正確
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 4. 複製所有程式碼 (包含 app.py)
COPY --chown=user . /app

# 5. 啟動 Solara
# 關鍵：Hugging Face 預設 Port 是 7860，這裡必須指定
CMD ["solara", "run", "app.py", "--host=0.0.0.0", "--port=7860"]