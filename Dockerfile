# Hafif ve uyumlu bir Python tabanı
FROM python:3.9-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli sistem paketlerini ve Rclone'u yükle
# curl ve unzip rclone kurulumu için gerekli
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Rclone Kurulumu (Betik ile en son sürümü çeker ve kurar)
# Doğrudan binary kurulumu için script kullanmak en güvenli ve mimari bağımsız yoldur (ARM/AMD otomatik algılar)
RUN curl https://rclone.org/install.sh | bash

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PYTHONPATH ayarı (Import sorunlarını önlemek için)
ENV PYTHONPATH=/app

# Uygulama kodlarını kopyala
COPY . .

# Streamlit portunu dışarı aç
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Uygulamayı başlat
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0"]
