from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QTextEdit, QVBoxLayout,QMessageBox,
    QWidget, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from api.openai_api import get_image_description
from utils.file_handler import get_image_file, encode_image_to_base64
from utils.config import DB_PATH
import sqlite3
import pandas as pd
import os
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("책 표지 분류기")
        self.setGeometry(100, 100, 700, 500)
        self.image_path = None
        self.init_ui()
        self.init_db()

    def init_ui(self):
        self.image_label = QLabel("이미지를 불러오세요")
        self.image_label.setFixedSize(300, 300)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black;")

        self.load_button = QPushButton("이미지 열기")
        self.load_button.clicked.connect(self.load_image)

        #self.text_input = QTextEdit()
        #self.text_input.setPlaceholderText("GPT에게 보낼 추가 프롬프트 입력")
        self.fixed_prompt = "Search the internet for this book's cover and display its title, author, publisher, genre, and rating. Please answer in Korean in the following format: Title : \nAuthor : \nPublisher : \nGenre : \nRating : , without any additional information."

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)

        self.generate_button = QPushButton("책 정보 보기")
        self.generate_button.clicked.connect(self.generate_description)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.image_label)
        top_layout.addWidget(self.load_button)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        #layout.addWidget(self.text_input)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.result_output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS image_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image BLOB,
                prompt TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def load_image(self):
        try:
            path = get_image_file()
            if path:
                pixmap = QPixmap(path).scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio)
                if pixmap.isNull():
                    raise ValueError("이미지를 불러올 수 없습니다.")
                self.image_label.setPixmap(pixmap)
                self.image_path = path
        except Exception as e:
            QMessageBox.warning(self, "오류", f"이미지 불러오기 실패: {e}")


    def generate_description(self):
        if not self.image_path:
            self.result_output.setPlainText("이미지를 먼저 불러와 주세요.")
            return
        
        prompt = self.fixed_prompt#self.text_input.toPlainText()


        base64_image = encode_image_to_base64(self.image_path)
        result = get_image_description(self.image_path, prompt)
        self.result_output.setPlainText(result)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            with open(self.image_path, "rb") as f:
                image_blob = f.read()
            cursor.execute('''
                INSERT INTO image_logs (image, prompt, response) VALUES (?, ?, ?)
            ''', (image_blob, prompt, result))
            conn.commit()
        # --- CSV 누적 저장 ---
        try:
            csv_path = "book_descriptions.csv"  # 모든 기록을 한 파일에 누적

            # GPT 결과를 딕셔너리로 변환
            data_dict = {}
            for line in result.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    data_dict[key.strip()] = value.strip()

            # DataFrame 생성 (1행)
            df_new = pd.DataFrame([{
                "Title": data_dict.get("Title", ""),
                "Author": data_dict.get("Author", ""),
                "Publisher": data_dict.get("Publisher", ""),
                "Genre": data_dict.get("Genre", ""),
                "Rating": data_dict.get("Rating", "")
            }])

            # CSV가 이미 존재하면 이어쓰기
            if os.path.exists(csv_path):
                df_existing = pd.read_csv(csv_path)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new

            # CSV 저장
            df_combined.to_csv(csv_path, index=False, encoding="utf-8-sig")

        except Exception as e:
            pass