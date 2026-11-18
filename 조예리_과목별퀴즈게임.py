import random
import tkinter as tk
from tkinter import messagebox, ttk
import pymysql

SAMPLE_QUESTIONS = [

    ("파이썬", "OX", "파이썬에서 리스트(list)는 변경 가능한(mutable) 자료형이다.", None, None, None, None, "O"),
    ("데이터베이스", "OX", "SQL의 SELECT 문은 테이블의 데이터를 삭제할 때 사용한다.", None, None, None, None, "X"),
    ("네트워크", "OX", "HTTP는 기본적으로 상태를 유지하지 않는(stateless) 프로토콜이다.", None, None, None, None, "O"),

    ("파이썬", "MCQ", "다음 중 파이썬 딕셔너리에서 키와 값 쌍을 순회할 때 사용하는 메서드는?", "keys()", "values()", "items()", "pairs()", "3"),
    ("데이터베이스", "MCQ", "관계형 데이터베이스에서 테이블 간 관계를 나타내고 중복을 줄이기 위해 사용하는 키는?", "Primary Key", "Foreign Key", "Index", "View", "2"),
    ("네트워크", "MCQ", "도메인 이름(예: example.com)을 IP 주소로 변환해 주는 프로토콜은?", "FTP", "DNS", "SMTP", "ARP", "2"),

    ("파이썬", "SHORT", "파이썬에서 반복문을 즉시 종료할 때 사용하는 예약어는?", None, None, None, None, "break"),
    ("데이터베이스", "SHORT", "데이터베이스에서 중복된 행을 제거하고 조회할 때 쓰는 키워드는?", None, None, None, None, "DISTINCT"),
    ("네트워크", "SHORT", "컴퓨터 네트워크에서 패킷의 최적 경로를 찾아 전달하는 장비는?", None, None, None, None, "라우터"),
]

class QuizGameApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("과목별 퀴즈 게임 (OX / 객관식 / 주관식)")
        self.root.geometry("760x580")

        self.questions: list[dict] = []
        self.current_index: int = 0
        self.score: int = 0
        self.correct_count: int = 0
        self.current_subject: str = "전체"
        self.current_nickname: str = ""
        self.answer_var = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self):

        top_frame = ttk.LabelFrame(self.root, text="MySQL 접속 및 플레이어 설정", padding=10)
        top_frame.pack(fill="x", padx=12, pady=(10, 6))

        ttk.Label(top_frame, text="호스트:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.host_entry = ttk.Entry(top_frame, width=12)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1, padx=(0, 8))

        ttk.Label(top_frame, text="사용자:").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.user_entry = ttk.Entry(top_frame, width=9)
        self.user_entry.insert(0, "root")
        self.user_entry.grid(row=0, column=3, padx=(0, 8))

        ttk.Label(top_frame, text="비밀번호:").grid(row=0, column=4, sticky="w", padx=(0, 4))
        self.pw_entry = ttk.Entry(top_frame, width=12, show="*")
        self.pw_entry.grid(row=0, column=5, padx=(0, 8))

        self.init_btn = ttk.Button(top_frame, text="DB 초기화/연결", command=self.init_database)
        self.init_btn.grid(row=0, column=6, padx=(0, 8))

        ttk.Label(top_frame, text="닉네임:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        self.nick_entry = ttk.Entry(top_frame, width=12)
        self.nick_entry.insert(0, "플레이어1")
        self.nick_entry.grid(row=1, column=1, padx=(0, 8), pady=(8, 0))

        ttk.Label(top_frame, text="과목:").grid(row=1, column=2, sticky="w", padx=(0, 4), pady=(8, 0))
        self.subject_combo = ttk.Combobox(
            top_frame,
            values=["전체", "파이썬", "데이터베이스", "네트워크"],
            state="readonly",
            width=12,
        )
        self.subject_combo.set("전체")
        self.subject_combo.grid(row=1, column=3, padx=(0, 8), pady=(8, 0))

        self.start_btn = ttk.Button(top_frame, text="퀴즈 시작", command=self.start_quiz)
        self.start_btn.grid(row=1, column=5, padx=(0, 8), pady=(8, 0))

        self.rank_btn = ttk.Button(top_frame, text="랭킹 보기", command=self.refresh_leaderboard)
        self.rank_btn.grid(row=1, column=6, pady=(8, 0))

        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        quiz_frame = ttk.LabelFrame(main_pane, text="퀴즈 풀이", padding=14)
        rank_frame = ttk.LabelFrame(main_pane, text="명예의 전당 (Top 10)", padding=10)
        main_pane.add(quiz_frame, weight=3)
        main_pane.add(rank_frame, weight=2)

        info_row = ttk.Frame(quiz_frame)
        info_row.pack(fill="x", pady=(0, 10))

        self.progress_var = tk.StringVar(value="문제: 0 / 0")
        self.score_var = tk.StringVar(value="점수: 0점")
        ttk.Label(info_row, textvariable=self.progress_var, font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Label(info_row, textvariable=self.score_var, font=("TkDefaultFont", 10, "bold")).pack(side="right")

        self.q_badge_var = tk.StringVar(value="DB 초기화/연결 후 [퀴즈 시작]을 눌러주세요.")
        ttk.Label(quiz_frame, textvariable=self.q_badge_var, foreground="#2563eb").pack(anchor="w", pady=(0, 6))

        self.q_text = tk.Text(quiz_frame, height=4, wrap="word", font=("TkDefaultFont", 11))
        self.q_text.pack(fill="x", pady=(0, 12))
        self.q_text.configure(state="disabled")

        self.answer_container = ttk.Frame(quiz_frame)
        self.answer_container.pack(fill="both", expand=True)

        self.submit_btn = ttk.Button(quiz_frame, text="정답 제출", command=self.submit_answer, state="disabled")
        self.submit_btn.pack(anchor="e", pady=(10, 0))

        rank_cols = ("rank", "nickname", "subject", "score")
        self.rank_tree = ttk.Treeview(rank_frame, columns=rank_cols, show="headings", height=16)
        self.rank_tree.heading("rank", text="순위")
        self.rank_tree.heading("nickname", text="닉네임")
        self.rank_tree.heading("subject", text="과목")
        self.rank_tree.heading("score", text="점수")

        self.rank_tree.column("rank", width=45, anchor="center")
        self.rank_tree.column("nickname", width=85, anchor="w")
        self.rank_tree.column("subject", width=80, anchor="w")
        self.rank_tree.column("score", width=55, anchor="e")
        self.rank_tree.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="비밀번호를 입력하고 [DB 초기화/연결]을 눌러주세요.")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 4)).pack(fill="x")

    def _connect_server(self, database: str | None = None):
        host = self.host_entry.get().strip() or "127.0.0.1"
        user = self.user_entry.get().strip() or "root"
        password = self.pw_entry.get()

        if not password:
            messagebox.showwarning("입력 확인", "MySQL 비밀번호를 입력해주세요.")
            return None

        kwargs = {
            "host": host,
            "port": 3306,
            "user": user,
            "password": password,
            "charset": "utf8mb4",
            "autocommit": False,
        }
        if database:
            kwargs["database"] = database

        return pymysql.connect(**kwargs)

    def init_database(self):
        conn = self._connect_server()
        if conn is None:
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute("CREATE DATABASE IF NOT EXISTS quiz_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                cursor.execute("USE quiz_db")

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS questions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        subject VARCHAR(50) NOT NULL,
                        q_type ENUM('OX', 'MCQ', 'SHORT') NOT NULL,
                        question TEXT NOT NULL,
                        opt1 VARCHAR(200),
                        opt2 VARCHAR(200),
                        opt3 VARCHAR(200),
                        opt4 VARCHAR(200),
                        answer VARCHAR(200) NOT NULL
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS quiz_scores (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nickname VARCHAR(50) NOT NULL,
                        subject VARCHAR(50) NOT NULL,
                        score INT NOT NULL,
                        correct_count INT NOT NULL,
                        total_count INT NOT NULL,
                        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute("SELECT COUNT(*) FROM questions")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        """
                        INSERT INTO questions (subject, q_type, question, opt1, opt2, opt3, opt4, answer)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        SAMPLE_QUESTIONS,
                    )

                cursor.execute("SELECT DISTINCT subject FROM questions ORDER BY subject")
                subjects = ["전체"] + [row[0] for row in cursor.fetchall()]
                self.subject_combo["values"] = subjects
                if self.subject_combo.get() not in subjects:
                    self.subject_combo.set("전체")

            conn.commit()
            self.status_var.set("quiz_db 연결 및 테이블/샘플 문제 준비 완료!")
            self.refresh_leaderboard()
            messagebox.showinfo("연결 완료", "MySQL quiz_db 준비가 완료되었습니다.")

        except pymysql.MySQLError as err:
            conn.rollback()
            messagebox.showerror("DB 오류", f"초기화 실패:\n{err}")
        finally:
            if conn.open:
                conn.close()

    def start_quiz(self):
        nickname = self.nick_entry.get().strip()
        if not nickname:
            messagebox.showwarning("입력 확인", "닉네임을 입력해주세요.")
            return

        subject = self.subject_combo.get() or "전체"
        conn = self._connect_server(database="quiz_db")
        if conn is None:
            return

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if subject == "전체":
                    cursor.execute("SELECT * FROM questions")
                else:
                    cursor.execute("SELECT * FROM questions WHERE subject = %s", (subject,))
                rows = cursor.fetchall()

            if not rows:
                messagebox.showinfo("문제 없음", f"'{subject}' 과목에 등록된 문제가 없습니다.")
                return

            random.shuffle(rows)
            self.questions = rows
            self.current_index = 0
            self.score = 0
            self.correct_count = 0
            self.current_subject = subject
            self.current_nickname = nickname
            self.submit_btn.configure(state="normal")

            self._render_question()
            self.status_var.set(f"[{subject}] 퀴즈 시작! 총 {len(self.questions)}문제")

        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제를 불러오지 못했습니다:\n{err}")
        finally:
            if conn.open:
                conn.close()

    def _render_question(self):
        for widget in self.answer_container.winfo_children():
            widget.destroy()

        total = len(self.questions)
        q = self.questions[self.current_index]
        q_type = q["q_type"]

        type_label = {"OX": "OX 퀴즈", "MCQ": "객관식", "SHORT": "주관식"}.get(q_type, q_type)
        self.progress_var.set(f"문제: {self.current_index + 1} / {total}")
        self.score_var.set(f"점수: {self.score}점")
        self.q_badge_var.set(f"[{q['subject']}] · [{type_label}]")

        self.q_text.configure(state="normal")
        self.q_text.delete("1.0", tk.END)
        self.q_text.insert("1.0", q["question"])
        self.q_text.configure(state="disabled")

        self.answer_var.set("")

        if q_type == "OX":
            ttk.Radiobutton(self.answer_container, text="O (맞다)", variable=self.answer_var, value="O").pack(
                anchor="w", pady=4
            )
            ttk.Radiobutton(self.answer_container, text="X (틀리다)", variable=self.answer_var, value="X").pack(
                anchor="w", pady=4
            )
        elif q_type == "MCQ":
            for idx in range(1, 5):
                opt_text = q.get(f"opt{idx}")
                if opt_text:
                    ttk.Radiobutton(
                        self.answer_container,
                        text=f"{idx}. {opt_text}",
                        variable=self.answer_var,
                        value=str(idx),
                    ).pack(anchor="w", pady=3)
        else:
            ttk.Label(self.answer_container, text="정답 입력:").pack(anchor="w", pady=(0, 4))
            entry = ttk.Entry(self.answer_container, textvariable=self.answer_var, width=32)
            entry.pack(anchor="w")
            entry.focus()
            entry.bind("<Return>", lambda event: self.submit_answer())

    def submit_answer(self):
        if not self.questions or self.current_index >= len(self.questions):
            return

        user_ans = self.answer_var.get().strip()
        if not user_ans:
            messagebox.showwarning("답안 확인", "정답을 선택하거나 입력해주세요.")
            return

        q = self.questions[self.current_index]
        correct_ans = str(q["answer"]).strip()

        if q["q_type"] == "SHORT":
            is_correct = user_ans.casefold() == correct_ans.casefold()
        else:
            is_correct = user_ans.upper() == correct_ans.upper()

        if is_correct:
            self.score += 10
            self.correct_count += 1
            messagebox.showinfo("정답!", f"정답입니다! (+10점)\n현재 점수: {self.score}점")
        else:
            messagebox.showerror("오답!", f"아쉽지만 오답입니다.\n정답: {correct_ans}")

        self.current_index += 1
        if self.current_index < len(self.questions):
            self._render_question()
        else:
            self.submit_btn.configure(state="disabled")
            self._finish_quiz()

    def _finish_quiz(self):
        total = len(self.questions)
        self.score_var.set(f"점수: {self.score}점")
        self._save_score(self.current_nickname, self.current_subject, self.score, self.correct_count, total)
        self.refresh_leaderboard()

        messagebox.showinfo(
            "퀴즈 종료",
            f"{self.current_nickname}님 수고하셨습니다!\n\n"
            f"과목: {self.current_subject}\n"
            f"최종 점수: {self.score}점\n"
            f"정답 수: {self.correct_count} / {total}문제",
        )
        self.status_var.set(f"퀴즈 완료! {self.current_nickname}님 {self.score}점 기록 저장됨")

    def _save_score(self, nickname: str, subject: str, score: int, correct_count: int, total_count: int):
        conn = self._connect_server(database="quiz_db")
        if conn is None:
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO quiz_scores (nickname, subject, score, correct_count, total_count)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nickname, subject, score, correct_count, total_count),
                )
            conn.commit()
        except pymysql.MySQLError as err:
            conn.rollback()
            messagebox.showerror("DB 오류", f"점수 저장 실패:\n{err}")
        finally:
            if conn.open:
                conn.close()

    def refresh_leaderboard(self):
        conn = self._connect_server(database="quiz_db")
        if conn is None:
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT nickname, subject, score
                    FROM quiz_scores
                    ORDER BY score DESC, played_at ASC
                    LIMIT 10
                    """
                )
                rows = cursor.fetchall()

            for item in self.rank_tree.get_children():
                self.rank_tree.delete(item)

            for idx, (nick, subj, sc) in enumerate(rows, start=1):
                self.rank_tree.insert("", "end", values=(idx, nick, subj, sc))

        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"랭킹 조회 실패:\n{err}")
        finally:
            if conn.open:
                conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizGameApp(root)
    root.mainloop()