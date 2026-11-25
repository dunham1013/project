import os
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

BONUS_STREAK = 3
BONUS_POINT = 5

TYPE_LABELS = {"OX": "OX 퀴즈", "MCQ": "객관식", "SHORT": "주관식"}
ALL_RANK = "(모두)"


def format_answer(q: dict, ans: str) -> str:
    """객관식은 '3. items()'처럼 보기 내용을 함께 보여준다."""
    if q["q_type"] == "MCQ" and ans.isdigit():
        opt = q.get(f"opt{ans}")
        if opt:
            return f"{ans}. {opt}"
    return ans


class QuizGameApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("과목별 퀴즈 게임 (OX / 객관식 / 주관식)")
        self.root.geometry("860x640")

        self.conn = None
        self.questions: list[dict] = []
        self.current_index: int = 0
        self.score: int = 0
        self.correct_count: int = 0
        self.current_subject: str = "전체"
        self.current_nickname: str = ""
        self.answer_var = tk.StringVar(value="")

        self.time_limit: int = 0
        self.use_bonus: bool = False
        self.streak: int = 0
        self.remaining: int = 0
        self._timer_id = None
        self.wrong_list: list[dict] = []
        self.note_win = None
        self.manager_win = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        top_frame = ttk.LabelFrame(self.root, text="MySQL 접속 및 플레이어 설정", padding=10)
        top_frame.pack(fill="x", padx=12, pady=(10, 6))

        ttk.Label(top_frame, text="호스트:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.host_entry = ttk.Entry(top_frame, width=12)
        self.host_entry.insert(0, os.environ.get("MYSQL_HOST", "127.0.0.1"))
        self.host_entry.grid(row=0, column=1, padx=(0, 8))

        ttk.Label(top_frame, text="사용자:").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.user_entry = ttk.Entry(top_frame, width=9)
        self.user_entry.insert(0, os.environ.get("MYSQL_USER", "root"))
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

        ttk.Label(top_frame, text="제한시간(초):").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(8, 0))
        self.time_spin = ttk.Spinbox(top_frame, from_=0, to=120, width=10)
        self.time_spin.set("0")
        self.time_spin.grid(row=2, column=1, padx=(0, 8), pady=(8, 0))

        self.bonus_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top_frame, text="연속 정답 보너스", variable=self.bonus_var).grid(
            row=2, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )

        self.manage_btn = ttk.Button(top_frame, text="문제 관리", command=self.open_manager)
        self.manage_btn.grid(row=2, column=5, padx=(0, 8), pady=(8, 0))

        self.note_btn = ttk.Button(top_frame, text="오답 노트", command=self.show_wrong_notes)
        self.note_btn.grid(row=2, column=6, pady=(8, 0))

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
        self.timer_var = tk.StringVar(value="")
        ttk.Label(info_row, textvariable=self.progress_var, font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Label(info_row, textvariable=self.timer_var, foreground="#dc2626").pack(side="left", padx=16)
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

        rank_top = ttk.Frame(rank_frame)
        rank_top.pack(fill="x", pady=(0, 6))
        ttk.Label(rank_top, text="과목:").pack(side="left")
        self.rank_combo = ttk.Combobox(rank_top, values=[ALL_RANK], state="readonly", width=14)
        self.rank_combo.set(ALL_RANK)
        self.rank_combo.pack(side="left", padx=(4, 0))
        self.rank_combo.bind("<<ComboboxSelected>>", lambda event: self.refresh_leaderboard())

        rank_cols = ("rank", "nickname", "subject", "score")
        self.rank_tree = ttk.Treeview(rank_frame, columns=rank_cols, show="headings", height=14)
        self.rank_tree.heading("rank", text="순위")
        self.rank_tree.heading("nickname", text="닉네임")
        self.rank_tree.heading("subject", text="과목")
        self.rank_tree.heading("score", text="점수")

        self.rank_tree.column("rank", width=45, anchor="center")
        self.rank_tree.column("nickname", width=85, anchor="w")
        self.rank_tree.column("subject", width=80, anchor="w")
        self.rank_tree.column("score", width=55, anchor="e")
        self.rank_tree.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(
            value="비밀번호를 입력하고 [DB 초기화/연결]을 눌러주세요. (환경변수 MYSQL_PASSWORD도 사용 가능)"
        )
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=(12, 4)).pack(fill="x")

    def _open_connection(self, database: str | None = None):
        host = self.host_entry.get().strip() or "127.0.0.1"
        user = self.user_entry.get().strip() or "root"
        password = self.pw_entry.get() or os.environ.get("MYSQL_PASSWORD", "")

        if not password:
            messagebox.showwarning("입력 확인", "MySQL 비밀번호를 입력하거나 환경변수 MYSQL_PASSWORD를 설정해주세요.")
            return None

        kwargs = {
            "host": host,
            "port": 3306,
            "user": user,
            "password": password,
            "charset": "utf8mb4",
            "autocommit": True,
        }
        if database:
            kwargs["database"] = database

        return pymysql.connect(**kwargs)

    def _get_conn(self):
        """이미 열린 연결이 있으면 재사용하고, 끊겼으면 다시 연결한다."""
        if self.conn is not None and self.conn.open:
            try:
                self.conn.ping(reconnect=True)
                return self.conn
            except pymysql.MySQLError:
                self.conn = None

        conn = self._open_connection(database="quiz_db")
        if conn is not None:
            self.conn = conn
        return self.conn

    def _close_conn(self):
        if self.conn is not None:
            try:
                if self.conn.open:
                    self.conn.close()
            except pymysql.MySQLError:
                pass
        self.conn = None

    def on_close(self):
        self._stop_timer()
        self._close_conn()
        self.root.destroy()

    def init_database(self):
        try:
            self._close_conn()
            conn = self._open_connection()
            if conn is None:
                return
            self.conn = conn

            with conn.cursor() as cursor:
                cursor.execute("CREATE DATABASE IF NOT EXISTS quiz_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.select_db("quiz_db")

            with conn.cursor() as cursor:
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

            self._reload_subjects()
            self.status_var.set("quiz_db 연결 및 테이블/샘플 문제 준비 완료!")
            self.refresh_leaderboard()
            messagebox.showinfo("연결 완료", "MySQL quiz_db 준비가 완료되었습니다.")

        except pymysql.MySQLError as err:
            self._close_conn()
            messagebox.showerror("DB 오류", f"초기화 실패:\n{err}")

    def _reload_subjects(self):
        """questions 테이블의 과목 목록을 읽어 과목/랭킹 콤보박스를 갱신한다."""
        conn = self._get_conn()
        if conn is None:
            return
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT subject FROM questions ORDER BY subject")
            subjects = ["전체"] + [row[0] for row in cursor.fetchall()]

        self.subject_combo["values"] = subjects
        if self.subject_combo.get() not in subjects:
            self.subject_combo.set("전체")

        rank_values = [ALL_RANK] + subjects
        self.rank_combo["values"] = rank_values
        if self.rank_combo.get() not in rank_values:
            self.rank_combo.set(ALL_RANK)

    def start_quiz(self):
        nickname = self.nick_entry.get().strip()
        if not nickname:
            messagebox.showwarning("입력 확인", "닉네임을 입력해주세요.")
            return

        try:
            limit = int(self.time_spin.get().strip() or "0")
        except ValueError:
            messagebox.showwarning("입력 확인", "제한시간은 숫자(초)로 입력해주세요. (0이면 제한 없음)")
            return
        limit = max(0, min(limit, 600))

        subject = self.subject_combo.get() or "전체"

        try:
            conn = self._get_conn()
            if conn is None:
                return

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
            self._stop_timer()
            self.questions = rows
            self.current_index = 0
            self.score = 0
            self.correct_count = 0
            self.streak = 0
            self.wrong_list = []
            self.time_limit = limit
            self.use_bonus = bool(self.bonus_var.get())
            self.current_subject = subject
            self.current_nickname = nickname
            self.submit_btn.configure(state="normal")

            self._render_question()
            self.status_var.set(f"[{subject}] 퀴즈 시작! 총 {len(self.questions)}문제")

        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제를 불러오지 못했습니다:\n{err}")

    def _render_question(self):
        for widget in self.answer_container.winfo_children():
            widget.destroy()

        total = len(self.questions)
        q = self.questions[self.current_index]
        q_type = q["q_type"]

        type_label = TYPE_LABELS.get(q_type, q_type)
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

        self._start_timer()

    def _start_timer(self):
        self._stop_timer()
        if self.time_limit <= 0:
            self.timer_var.set("")
            return
        self.remaining = self.time_limit
        self._tick()

    def _tick(self):
        self.timer_var.set(f"남은 시간: {self.remaining}초")
        if self.remaining <= 0:
            self._timer_id = None
            self._on_timeout()
            return
        self.remaining -= 1
        self._timer_id = self.root.after(1000, self._tick)

    def _stop_timer(self):
        if self._timer_id is not None:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def _on_timeout(self):
        if not self.questions or self.current_index >= len(self.questions):
            return
        typed = self.answer_var.get().strip()
        self._finish_question(False, typed or "(시간 초과)", timed_out=True)

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

        self._finish_question(is_correct, user_ans)

    def _finish_question(self, is_correct: bool, user_ans: str, timed_out: bool = False):
        self._stop_timer()
        q = self.questions[self.current_index]
        correct_ans = str(q["answer"]).strip()

        if is_correct:
            self.streak += 1
            bonus = BONUS_POINT if (self.use_bonus and self.streak >= BONUS_STREAK) else 0
            self.score += 10 + bonus
            self.correct_count += 1
            if bonus:
                msg = f"정답입니다! (+10점, 연속 정답 보너스 +{bonus}점)\n현재 점수: {self.score}점"
            else:
                msg = f"정답입니다! (+10점)\n현재 점수: {self.score}점"
            messagebox.showinfo("정답!", msg)
        else:
            self.streak = 0
            self.wrong_list.append(
                {
                    "q": q,
                    "user_ans": user_ans,
                    "correct_ans": correct_ans,
                    "timed_out": timed_out,
                }
            )
            if timed_out:
                messagebox.showerror("시간 초과!", f"시간이 초과되었습니다.\n정답: {correct_ans}")
            else:
                messagebox.showerror("오답!", f"아쉽지만 오답입니다.\n정답: {correct_ans}")

        self.current_index += 1
        if self.current_index < len(self.questions):
            self._render_question()
        else:
            self.submit_btn.configure(state="disabled")
            self._finish_quiz()

    def _finish_quiz(self):
        self._stop_timer()
        self.timer_var.set("")
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

        if self.wrong_list:
            self.show_wrong_notes()

    def _save_score(self, nickname: str, subject: str, score: int, correct_count: int, total_count: int):
        try:
            conn = self._get_conn()
            if conn is None:
                return
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
            messagebox.showerror("DB 오류", f"점수 저장 실패:\n{err}")

    def refresh_leaderboard(self):
        subject_filter = self.rank_combo.get()
        try:
            conn = self._get_conn()
            if conn is None:
                return

            with conn.cursor() as cursor:
                if subject_filter in ("", ALL_RANK):
                    cursor.execute(
                        """
                        SELECT nickname, subject, score
                        FROM quiz_scores
                        ORDER BY score DESC, played_at ASC
                        LIMIT 10
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT nickname, subject, score
                        FROM quiz_scores
                        WHERE subject = %s
                        ORDER BY score DESC, played_at ASC
                        LIMIT 10
                        """,
                        (subject_filter,),
                    )
                rows = cursor.fetchall()

            for item in self.rank_tree.get_children():
                self.rank_tree.delete(item)

            for idx, (nick, subj, sc) in enumerate(rows, start=1):
                self.rank_tree.insert("", "end", values=(idx, nick, subj, sc))

        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"랭킹 조회 실패:\n{err}")

    def show_wrong_notes(self):
        if not self.wrong_list:
            messagebox.showinfo("오답 노트", "표시할 오답이 없습니다.")
            return

        if self.note_win is not None and self.note_win.winfo_exists():
            self.note_win.destroy()

        win = tk.Toplevel(self.root)
        win.title("오답 노트")
        win.geometry("560x480")
        self.note_win = win

        ttk.Label(
            win,
            text=f"{self.current_nickname}님의 오답 {len(self.wrong_list)}문제 ({self.current_subject})",
            font=("TkDefaultFont", 11, "bold"),
            padding=10,
        ).pack(anchor="w")

        body = ttk.Frame(win)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        text = tk.Text(body, wrap="word", font=("TkDefaultFont", 10), padx=8, pady=8)
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        for no, item in enumerate(self.wrong_list, start=1):
            q = item["q"]
            type_label = TYPE_LABELS.get(q["q_type"], q["q_type"])
            mine = format_answer(q, item["user_ans"])
            correct = format_answer(q, item["correct_ans"])
            text.insert("end", f"[{no}] [{q['subject']}] · [{type_label}]\n")
            text.insert("end", f"문제: {q['question']}\n")
            text.insert("end", f"내 답: {mine}\n")
            text.insert("end", f"정답: {correct}\n\n")
        text.configure(state="disabled")

        ttk.Button(win, text="닫기", command=win.destroy).pack(pady=(0, 10))

    def open_manager(self):
        try:
            conn = self._get_conn()
            if conn is None:
                return
        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"DB에 연결하지 못했습니다:\n{err}")
            return

        if self.manager_win is not None and self.manager_win.winfo_exists():
            self.manager_win.lift()
            return
        self.manager_win = QuestionManager(self)


class QuestionManager(tk.Toplevel):
    """questions 테이블의 문제를 추가 / 수정 / 삭제하는 창."""

    def __init__(self, app: QuizGameApp):
        super().__init__(app.root)
        self.app = app
        self.title("문제 관리")
        self.geometry("880x620")

        self.rows: dict[int, dict] = {}
        self.selected_id: int | None = None
        self.subject_var = tk.StringVar()
        self.type_var = tk.StringVar(value="OX")
        self.answer_var = tk.StringVar()
        self.opt_vars = [tk.StringVar() for _ in range(4)]

        self._build()
        self.load_questions()

    def _build(self):
        list_frame = ttk.LabelFrame(self, text="등록된 문제", padding=8)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(10, 6))

        cols = ("id", "subject", "q_type", "question", "answer")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=9)
        for col, text, width, anchor in (
            ("id", "번호", 50, "center"),
            ("subject", "과목", 100, "w"),
            ("q_type", "유형", 70, "center"),
            ("question", "문제", 470, "w"),
            ("answer", "정답", 110, "w"),
        ):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.LabelFrame(self, text="문제 입력 / 수정", padding=10)
        form.pack(fill="x", padx=12, pady=(0, 6))

        ttk.Label(form, text="과목:").grid(row=0, column=0, sticky="w")
        subjects = [s for s in self.app.subject_combo["values"] if s != "전체"]
        self.subject_combo = ttk.Combobox(form, textvariable=self.subject_var, values=subjects, width=16)
        self.subject_combo.grid(row=0, column=1, sticky="w", padx=(4, 16))

        ttk.Label(form, text="유형:").grid(row=0, column=2, sticky="w")
        self.type_combo = ttk.Combobox(
            form, textvariable=self.type_var, values=["OX", "MCQ", "SHORT"], state="readonly", width=10
        )
        self.type_combo.grid(row=0, column=3, sticky="w", padx=(4, 16))
        self.type_combo.bind("<<ComboboxSelected>>", lambda event: self._update_form_state())

        ttk.Label(form, text="문제:").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        self.q_text = tk.Text(form, height=3, width=70, wrap="word")
        self.q_text.grid(row=1, column=1, columnspan=5, sticky="w", padx=(4, 0), pady=(8, 0))

        self.opt_entries = []
        for i in range(4):
            ttk.Label(form, text=f"보기{i + 1}:").grid(row=2 + i // 2, column=(i % 2) * 3, sticky="w", pady=(8, 0))
            entry = ttk.Entry(form, textvariable=self.opt_vars[i], width=32)
            entry.grid(row=2 + i // 2, column=(i % 2) * 3 + 1, columnspan=2, sticky="w", padx=(4, 16), pady=(8, 0))
            self.opt_entries.append(entry)

        ttk.Label(form, text="정답:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.answer_var, width=20).grid(
            row=4, column=1, sticky="w", padx=(4, 16), pady=(8, 0)
        )
        self.hint_var = tk.StringVar()
        ttk.Label(form, textvariable=self.hint_var, foreground="#2563eb").grid(
            row=4, column=2, columnspan=4, sticky="w", pady=(8, 0)
        )

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Button(btn_row, text="새 문제 (입력칸 비우기)", command=self.clear_form).pack(side="left")
        ttk.Button(btn_row, text="새로고침", command=self.load_questions).pack(side="left", padx=6)
        ttk.Button(btn_row, text="삭제", command=self.delete_question).pack(side="right")
        ttk.Button(btn_row, text="수정", command=self.update_question).pack(side="right", padx=6)
        ttk.Button(btn_row, text="추가", command=self.add_question).pack(side="right")

        self._update_form_state()

    def _update_form_state(self):
        q_type = self.type_var.get()
        state = "normal" if q_type == "MCQ" else "disabled"
        for entry in self.opt_entries:
            entry.configure(state=state)
        self.hint_var.set(
            {
                "OX": "정답: O 또는 X",
                "MCQ": "정답: 보기 번호(1~4), 보기는 2개 이상 입력",
                "SHORT": "정답: 단어 (대소문자·앞뒤 공백은 무시하고 채점)",
            }.get(q_type, "")
        )

    def clear_form(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        self.subject_var.set("")
        self.type_var.set("OX")
        self.q_text.delete("1.0", tk.END)
        for var in self.opt_vars:
            var.set("")
        self.answer_var.set("")
        self._update_form_state()

    def load_questions(self):
        try:
            conn = self.app._get_conn()
            if conn is None:
                return
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT * FROM questions ORDER BY id")
                rows = cursor.fetchall()
        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제 목록 조회 실패:\n{err}", parent=self)
            return

        self.rows = {row["id"]: row for row in rows}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            question = row["question"].replace("\n", " ")
            self.tree.insert(
                "", "end", iid=str(row["id"]),
                values=(row["id"], row["subject"], row["q_type"], question, row["answer"]),
            )
        self.selected_id = None

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        row = self.rows.get(int(selection[0]))
        if row is None:
            return
        self.selected_id = row["id"]
        self.subject_var.set(row["subject"])
        self.type_var.set(row["q_type"])
        self.q_text.delete("1.0", tk.END)
        self.q_text.insert("1.0", row["question"])
        self._update_form_state()
        for i in range(4):
            self.opt_vars[i].set(row.get(f"opt{i + 1}") or "")
        self.answer_var.set(row["answer"])

    def _read_form(self):
        subject = self.subject_var.get().strip()
        q_type = self.type_var.get()
        question = self.q_text.get("1.0", tk.END).strip()
        answer = self.answer_var.get().strip()
        opts = [var.get().strip() for var in self.opt_vars]

        if not subject or not question or not answer:
            messagebox.showwarning("입력 확인", "과목, 문제, 정답을 모두 입력해주세요.", parent=self)
            return None

        if q_type == "OX":
            answer = answer.upper()
            if answer not in ("O", "X"):
                messagebox.showwarning("입력 확인", "OX 문제의 정답은 O 또는 X여야 합니다.", parent=self)
                return None
            opts = [None] * 4
        elif q_type == "MCQ":
            if sum(1 for opt in opts if opt) < 2:
                messagebox.showwarning("입력 확인", "객관식은 보기를 2개 이상 입력해주세요.", parent=self)
                return None
            if answer not in ("1", "2", "3", "4") or not opts[int(answer) - 1]:
                messagebox.showwarning("입력 확인", "정답은 입력한 보기의 번호(1~4)여야 합니다.", parent=self)
                return None
            opts = [opt or None for opt in opts]
        else:
            opts = [None] * 4

        return (subject, q_type, question, *opts, answer)

    def _after_change(self):
        self.load_questions()
        try:
            self.app._reload_subjects()
        except pymysql.MySQLError:
            pass
        self.subject_combo["values"] = [s for s in self.app.subject_combo["values"] if s != "전체"]

    def add_question(self):
        data = self._read_form()
        if data is None:
            return
        try:
            conn = self.app._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO questions (subject, q_type, question, opt1, opt2, opt3, opt4, answer)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    data,
                )
            conn.commit()
        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제 추가 실패:\n{err}", parent=self)
            return
        self._after_change()
        self.clear_form()
        messagebox.showinfo("완료", "문제를 추가했습니다.", parent=self)

    def update_question(self):
        if self.selected_id is None:
            messagebox.showwarning("선택 확인", "수정할 문제를 목록에서 선택해주세요.", parent=self)
            return
        data = self._read_form()
        if data is None:
            return
        try:
            conn = self.app._get_conn()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE questions
                    SET subject = %s, q_type = %s, question = %s,
                        opt1 = %s, opt2 = %s, opt3 = %s, opt4 = %s, answer = %s
                    WHERE id = %s
                    """,
                    (*data, self.selected_id),
                )
            conn.commit()
        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제 수정 실패:\n{err}", parent=self)
            return
        self._after_change()
        messagebox.showinfo("완료", "문제를 수정했습니다.", parent=self)

    def delete_question(self):
        if self.selected_id is None:
            messagebox.showwarning("선택 확인", "삭제할 문제를 목록에서 선택해주세요.", parent=self)
            return
        if not messagebox.askyesno("삭제 확인", f"{self.selected_id}번 문제를 삭제할까요?", parent=self):
            return
        try:
            conn = self.app._get_conn()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM questions WHERE id = %s", (self.selected_id,))
            conn.commit()
        except pymysql.MySQLError as err:
            messagebox.showerror("DB 오류", f"문제 삭제 실패:\n{err}", parent=self)
            return
        self._after_change()
        self.clear_form()


if __name__ == "__main__":
    root = tk.Tk()
    app = QuizGameApp(root)
    root.mainloop()
