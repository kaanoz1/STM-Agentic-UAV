# Geliştirme Aşamasında Kullanılan Teknolojiler


## Container Dışında

Windows: Microsoft Windows [Version 10.0.26200.9168] \
WSL Versiyon: 2.7.11.0 \
WSL Dağıtımı: Ubuntu-24.04 \
Direct3D Version: 1.611.1-81528511 \
Docker Versiyonu: 29.6.2, build dfc4efb \
VS Code Versiyonu: 1.131.0 \
Kullanılan Ekran Kartı:  NVIDIA GeForce RTX 2080 Super

## Container içerisinde:

### İşletim Sistemi ve Orta Katman
Container OS: Ubuntu 22.04.5 LTS \
ROS 2 Distributon: Humble Hawksbill \
Root Docker İmajı: osrf/ros:humble-desktop-full \
Uzak Masaüstü: XFCE4 + TigerVNC + noVNC + xRDP

### Simülasyon
Versiyon: R2025a \
World Dosya Formatı: VRML_SIM R2023b \
Webots ROS 2 Köprüsü: ros-humble-webots-ros2 \
İHA Modeli: DJI Mavic 2 PRO (Mavic2Pro PROTO) \
Kamera: 400x240, bgra8 \
LiDAR:  360 derece, 1D, 0.15-100 m menzil

### Python
Python: 3.10.12
Package Manager: uv 0.12.5

### AI Kütüphane Versiyonları
torch: 2.12.1 (CUDA 13.0) \
torchvision: 0.27.1 \
ultralytics: 8.4.121 \
clip-anytorch: 2.6.0 \
opencv-python: 4.11.0.86 \
numpy: 1.26.4 \
Nesne Tespit Modeli: YOLO-World (yolov8x-worldv2) \
NVIDIA Sürücü: 610.88

### RAI
RAI Framework (Robotec.AI) \
langchain: 1.2.15 \
langchain-core: 1.2.28 \
langchain-google-genai: 2.1.12 \
Streamlit: 1.55.0

### LLM 
LLM: google/gemini-3.1-flash-lite-preview, başka bir LLM'de tercih edilebilir.