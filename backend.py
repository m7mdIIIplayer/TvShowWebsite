import os
import socket
import json
import sys
import signal
import psutil
import threading
import time
import uvicorn
# لن نحتاج إلى http.server بعد الآن
# من مكتبة Tornado سنستوردها داخل الدالة الخاصة بالخادم الثابت

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

# إعداد المتغيرات البيئية
os.environ['FONTCONFIG_PATH'] = '/etc/fonts'
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--renderer-process-limit=16 --disable-gpu --enable-zero-copy --disable-gpu-compositing"

# تحديد الدليل الأساسي وWEB_DIR (حيث توجد ملفات الويب)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = BASE_DIR  # يمكنك تعديل هذا إذا كانت ملفات الويب موجودة في مجلد فرعي

# ------------------ إعداد FastAPI ------------------
app = FastAPI()

# السماح بالطلبات من عدة منافذ localhost (حسب حاجتك)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{port}" for port in range(8002, 8050)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إعداد دليل ملف watchlist وقاعدة بيانات JSON الخاصة به
WATCHLIST_DIR = os.path.join("MyLibrary", "WatchList")
WATCHLIST_FILE = os.path.join(WATCHLIST_DIR, "watchlist.json")
os.makedirs(WATCHLIST_DIR, exist_ok=True)

# نموذج الفيلم للتحقق من البيانات
class Movie(BaseModel):
    title: str
    cate: str
    year: str
    Runtime: str
    Rating: str
    imdb: str
    description: str
    video_url: str
    image_url: str

# دوال تحميل وحفظ watchlist
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as file:
            return json.load(file)
    return {"watchlist": []}

def save_watchlist():
    with open(WATCHLIST_FILE, "w") as file:
        json.dump(watchlist, file, indent=4)
    print(f"تم حفظ قائمة المشاهدة في {WATCHLIST_FILE}")

def save_watchlist_as_html():
    html_file_path = os.path.join(WATCHLIST_DIR, "watchlist.html")
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Watchlist</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        <link rel="stylesheet" href="MoviesSectionCssFormat/Movies.css">
    </head>
    <body>
        <div class="header">
            <button class="back-button" onclick="window.location.href='../TheMainApp.html';">
                <i class="fas fa-arrow-left back-btn" style="color: #ffffff;"></i>
            </button>
            My Watchlist
        </div>
        <div class="movies-container" id="movies-container">
            {movies_grid}
        </div>
    </body>
    </html>
    """
    movies_grid = ""
    for movie in watchlist["watchlist"]:
        movies_grid += f"""
        <div class="movie">
            <a href="movie_details.html?title={movie['title']}">
                <img src="{movie['image_url']}" alt="{movie['title']}">
                <div class="movie-title">{movie['title']}</div>
            </a>
        </div>
        """
    final_html = html_template.format(movies_grid=movies_grid)
    with open(html_file_path, "w", encoding="utf-8") as html_file:
        html_file.write(final_html)
    print(f"تم حفظ قائمة المشاهدة كملف HTML في {html_file_path}")

# نقطة النهاية لاسترجاع watchlist
@app.get("/get-watchlist")
async def get_watchlist_endpoint():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as file:
                watchlist_data = json.load(file)
            print("تم تحميل قائمة المشاهدة:", watchlist_data)
            return {"watchlist": watchlist_data.get("watchlist", [])}
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="خطأ في فك تشفير JSON لقائمة المشاهدة")
    else:
        raise HTTPException(status_code=404, detail="لم يتم العثور على ملف قائمة المشاهدة")

# تحميل watchlist عند بدء التشغيل
watchlist = load_watchlist()

@app.post("/toggle-watchlist")
async def toggle_watchlist(movie: Movie):
    global watchlist
    try:
        existing_movie = next((m for m in watchlist["watchlist"] if m["title"] == movie.title), None)
        if existing_movie:
            watchlist["watchlist"] = [m for m in watchlist["watchlist"] if m["title"] != movie.title]
            save_watchlist()
            save_watchlist_as_html()
            return {"message": "تم إزالة الفيلم من قائمة المشاهدة!"}
        else:
            watchlist["watchlist"].append(movie.dict())
            save_watchlist()
            save_watchlist_as_html()
            return {"message": "تم إضافة الفيلم إلى قائمة المشاهدة!"}
    except Exception as e:
        print(f"خطأ أثناء تبديل الفيلم في قائمة المشاهدة: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء تحديث قائمة المشاهدة")

@app.post("/add-to-watchlist")
async def add_to_watchlist(movie: Movie):
    global watchlist
    try:
        if any(m["title"] == movie.title for m in watchlist["watchlist"]):
            raise HTTPException(status_code=400, detail="الفيلم موجود بالفعل في قائمة المشاهدة")
        watchlist["watchlist"].append(movie.dict())
        save_watchlist()
        save_watchlist_as_html()
        return {"message": "تم إضافة الفيلم إلى قائمة المشاهدة!"}
    except Exception as e:
        print(f"خطأ أثناء إضافة الفيلم إلى قائمة المشاهدة: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إضافة الفيلم إلى قائمة المشاهدة")

# ------------------ خادم الملفات الثابتة باستخدام Tornado ------------------
def start_tornado_static_server(port):
    import tornado.ioloop
    import tornado.web

    # إعداد تطبيق Tornado لتقديم الملفات من الدليل WEB_DIR
    tornado_app = tornado.web.Application([
        # تخدم جميع الطلبات من خلال StaticFileHandler، وتعيد ملف TheMainApp.html افتراضيًا
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": WEB_DIR, "default_filename": "TheMainApp.html"}),
    ])
    print(f"خادم الملفات الثابتة (Tornado) يعمل على المنفذ: {port}")
    tornado_app.listen(port)
    tornado.ioloop.IOLoop.current().start()

# ------------------ دوال إدارة المنافذ والتنظيف ------------------
def stop_process_on_port(port, exclude_pid=None):
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port:
            try:
                if conn.pid == exclude_pid:
                    continue
                proc = psutil.Process(conn.pid)
                print(f"إنهاء العملية {proc.pid} على المنفذ {port}")
                proc.terminate()
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            except Exception as e:
                print(f"خطأ عند إيقاف العملية على المنفذ {port}: {e}")

def ensure_ports_are_free(ports):
    current_pid = os.getpid()
    for port in ports:
        print(f"فحص المنفذ {port}...")
        try:
            stop_process_on_port(port, exclude_pid=current_pid)
        except Exception as e:
            print(f"فشل في التأكد من حرية المنفذ {port}: {e}")

def find_free_port(start_port=8000):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                s.close()
                return port
            except OSError:
                port += 1

def cleanup_and_exit(signum, frame):
    print("جاري الإغلاق...")
    os.system("pkill chrome")
    os.system("pkill chromium")
    os._exit(0)

# ------------------ تشغيل FastAPI ------------------
def start_fastapi():
    print("تشغيل خادم FastAPI على المنفذ 8031")
    uvicorn.run(app, host="0.0.0.0", port=8031, log_level="info")

# ------------------ واجهة المستخدم باستخدام PyQt6 ------------------
class WebApp(QMainWindow):
    def __init__(self, static_port):
        super().__init__()
        self.setWindowTitle("عارض الويب باستخدام PyQt6")
        self.showFullScreen()

        # إعداد متصفح QWebEngine مع ملف تعريف مخصص
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
        profile = QWebEngineProfile("CustomProfile", self)
        profile.setCachePath(os.path.join(BASE_DIR, "cache"))
        profile.setHttpCacheMaximumSize(500 * 1024 * 1024)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        profile.clearHttpCache()

        self.browser = QWebEngineView()
        page = QWebEnginePage(profile, self.browser)
        self.browser.setPage(page)
        # تحميل الصفحة الرئيسية من خادم الملفات الثابتة
        self.browser.setUrl(QUrl(f"http://localhost:{static_port}/TheMainApp.html"))
        QTimer.singleShot(2000, self.browser.reload)

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            sys.exit(0)

def start_pyqt(static_port):
    qt_app = QApplication(sys.argv)
    window = WebApp(static_port)
    window.show()
    sys.exit(qt_app.exec())

# ------------------ التنفيذ الرئيسي ------------------
if __name__ == '__main__':
    try:
        # التأكد من توافر المنافذ المطلوبة
        ensure_ports_are_free([8005, 8031])
        signal.signal(signal.SIGINT, cleanup_and_exit)
        signal.signal(signal.SIGTERM, cleanup_and_exit)
        
        # إيجاد منفذ متاح لخادم الملفات الثابتة (بدلاً من http.server)
        static_port = find_free_port(8005)
        
        # بدء خادم الملفات الثابتة باستخدام Tornado في خيط منفصل
        static_server_thread = threading.Thread(target=start_tornado_static_server, args=(static_port,), daemon=True)
        static_server_thread.start()
        
        # بدء خادم FastAPI في خيط منفصل
        fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
        fastapi_thread.start()
        
        # الانتظار قليلاً للتأكد من بدء الخوادم
        time.sleep(2)
        
        # بدء PyQt6 لتحميل الصفحة من خادم الملفات الثابتة
        start_pyqt(static_port)
        
    except Exception as e:
        print(f"خطأ أثناء بدء التطبيق: {e}")
