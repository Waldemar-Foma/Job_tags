from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QTextEdit,
                             QProgressBar, QLabel, QStatusBar)
from moviepy.editor import VideoFileClip
import speech_recognition as sr
from transformers import pipeline
import os


class VideoProcessingThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, task, *args):
        super().__init__()
        self.task = task
        self.args = args

    def run(self):
        if self.task == "extract_audio":
            self.extract_audio(*self.args)
        elif self.task == "audio_to_text":
            self.audio_to_text(*self.args)

    def extract_audio(self, video_path):
        video = VideoFileClip(video_path)
        audio_path = "audio.wav"
        video.audio.write_audiofile(audio_path)
        self.progress.emit(100)
        self.finished.emit("Звук извлечен из видео.")
        video.close()

    def audio_to_text(self, audio_path):
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")
        self.progress.emit(100)
        self.finished.emit(f"Текст из аудио: {text}")


class VideoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализ видео")
        self.setGeometry(100, 100, 800, 600)

        self.upload_button = QPushButton("Загрузить видео")
        self.extract_audio_button = QPushButton("Извлечь звук")
        self.audio_to_text_button = QPushButton("Перевести звук в текст")
        self.analyze_text_button = QPushButton("Анализ текста")
        self.result_text = QTextEdit()
        self.progress_bar = QProgressBar()
        self.drop_area = QLabel("Перетащите видеофайл сюда")
        self.drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_area.setAcceptDrops(True)
        self.drop_area.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                color: #666;
                border: 2px dashed #ddd;
                font-size: 16px;
                padding: 40px;
                border-radius: 10px;
            }
            QLabel:hover {
                border-color: #ff9f1c;
            }
        """)

        # Статус-бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #1f2a44;
                color: #f5f6fa;
                font-size: 14px;
                padding: 5px;
            }
        """)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QPushButton {
                background-color: #1f2a44;
                color: #f5f6fa;
                font-size: 16px;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                transition: background-color 0.3s;
            }
            QPushButton:hover {
                background-color: #ff9f1c;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #ddd;
                padding: 15px;
                font-size: 16px;
                color: #333;
                border-radius: 8px;
                box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
            }
            QProgressBar {
                background-color: #f0f0f0;
                color: #333;
                font-size: 14px;
                height: 20px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #ff9f1c;
                width: 10px;
            }
        """)

        self.upload_button.clicked.connect(self.upload_video)
        self.extract_audio_button.clicked.connect(self.start_extract_audio)
        self.audio_to_text_button.clicked.connect(self.start_audio_to_text)
        self.analyze_text_button.clicked.connect(self.analyze_text)

        layout = QVBoxLayout()
        layout.addWidget(self.upload_button)
        layout.addWidget(self.drop_area)
        layout.addWidget(self.extract_audio_button)
        layout.addWidget(self.audio_to_text_button)
        layout.addWidget(self.analyze_text_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.result_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.video_path = ""
        self.audio_path = ""
        self.text = ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.video_path = urls[0].toLocalFile()
            if os.path.splitext(self.video_path)[1] in ['.mp4', '.avi']:
                self.result_text.setText(f"Видео загружено: {self.video_path}")
                self.status_bar.showMessage("Видео успешно загружено", 5000)
            else:
                self.result_text.setText("Формат файла не поддерживается.")
                self.status_bar.showMessage("Ошибка: неподдерживаемый формат файла", 5000)

    def upload_video(self):
        file_dialog = QFileDialog()
        self.video_path, _ = file_dialog.getOpenFileName(self, "Выберите видеофайл", "", "Video Files (*.mp4 *.avi)")
        if self.video_path:
            self.result_text.setText(f"Видео загружено: {self.video_path}")
            self.status_bar.showMessage("Видео успешно загружено", 5000)

    def start_extract_audio(self):
        if not self.video_path:
            self.result_text.setText("Сначала загрузите видео.")
            self.status_bar.showMessage("Ошибка: загрузите видео перед извлечением аудио", 5000)
            return
        self.progress_bar.setValue(0)
        self.thread = VideoProcessingThread("extract_audio", self.video_path)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.update_result)
        self.thread.start()

    def start_audio_to_text(self):
        if not os.path.exists("audio.wav"):
            self.result_text.setText("Сначала извлеките звук.")
            self.status_bar.showMessage("Ошибка: извлеките звук перед конвертацией", 5000)
            return
        self.progress_bar.setValue(0)
        self.thread = VideoProcessingThread("audio_to_text", "audio.wav")
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.update_result)
        self.thread.start()

    def update_result(self, message):
        self.result_text.setText(message)

    def analyze_text(self):
        if not self.text:
            self.result_text.setText("Сначала переведите звук в текст.")
            self.status_bar.showMessage("Ошибка: переведите звук в текст перед анализом", 5000)
            return
        classifier = pipeline("sentiment-analysis", model="cointegrated/rubert-tiny")
        result = classifier(self.text)
        self.result_text.setText(f"Анализ текста: {result}")
        self.status_bar.showMessage("Анализ текста завершен", 5000)


app = QApplication([])
window = VideoApp()
window.show()
app.exec()
