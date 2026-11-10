from flask import Flask, render_template_string, request, redirect, session, url_for
import json
import os
import io
import base64
import qrcode
import urllib.request
import urllib.parse
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = "SANDY_SECRET_2026"

BASE = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(BASE, "menu.json")
SETTINGS_FILE = os.path.join(BASE, "settings.json")
IMAGE_DIR = os.path.join(BASE, "static", "images")
PASSWORD = "1234"

os.makedirs(IMAGE_DIR, exist_ok=True)

DEFAULT_MENU = [
    {"name": "فرخة مشوية", "price": 250},
    {"name": "نصف فرخة", "price": 130},
    {"name": "ربع فرخة", "price": 70},
    {"name": "كفتة مشوية", "price": 120},
    {"name": "شيش طاووق", "price": 110},
    {"name": "مشويات مشكلة", "price": 200}
]

DEFAULT_SETTINGS = {
    "restaurant": "SANDY",
    "subtitle": "مطعم ساندي للمشويات",
    "phone": "",
    "address": ""
}


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, type(default)):
                    return data
        except Exception:
            pass
    return default.copy()


menu = load_json(MENU_FILE, DEFAULT_MENU)
settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

# كلمات بحث مناسبة لبعض الأصناف المعروفة
IMAGE_SEARCH_TERMS = {
    "فرخة مشوية": "roast grilled whole chicken food",
    "نصف فرخة": "grilled half chicken food",
    "ربع فرخة": "grilled chicken quarter food",
    "كفتة مشوية": "kofta kebab grilled meat food",
    "شيش طاووق": "shish tawook chicken kebab food",
    "مشويات مشكلة": "mixed grilled meat platter food",
    "أرز": "cooked rice food",
    "بطاطس": "french fries food",
    "سلطة": "fresh salad food",
    "طرب": "grilled lamb caul fat kofta food",
    "حمام": "roasted pigeon food",
    "محشي": "egyptian mahshi stuffed vegetables food"
}


def save_menu():
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=4)


def save_settings():
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def search_term_for_food(name):
    if name in IMAGE_SEARCH_TERMS:
        return IMAGE_SEARCH_TERMS[name]

    # بحث عام باسم الصنف؛ قد تكون النتيجة تقريبية
    return name + " food dish"


def download_food_image(item):
    """يبحث عن صورة في Wikimedia Commons ويحفظ نسخة محلية."""
    if item.get("image"):
        existing = os.path.join(BASE, item["image"].lstrip("/"))
        if os.path.exists(existing):
            return True

    if item.get("image_checked"):
        return False

    item["image_checked"] = True
    query = search_term_for_food(item.get("name", ""))

    try:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": "filetype:bitmap " + query,
            "gsrnamespace": 6,
            "gsrlimit": 8,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 700,
            "format": "json"
        }
        api_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "SANDY-Restaurant-App/1.0 (food menu image search)"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))

        pages = result.get("query", {}).get("pages", {})
        candidates = list(pages.values())

        for candidate in candidates:
            info_list = candidate.get("imageinfo", [])
            if not info_list:
                continue

            image_url = info_list[0].get("thumburl") or info_list[0].get("url")
            if not image_url or not image_url.startswith("https://upload.wikimedia.org/"):
                continue

            image_req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "SANDY-Restaurant-App/1.0"}
            )
            with urllib.request.urlopen(image_req, timeout=20) as image_response:
                image_data = image_response.read(8 * 1024 * 1024 + 1)
                content_type = image_response.headers.get("Content-Type", "")

            if len(image_data) > 8 * 1024 * 1024:
                continue
            if not content_type.startswith("image/"):
                continue

            extension = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
            if extension == ".jpe":
                extension = ".jpg"

            filename = uuid.uuid4().hex + extension
            full_path = os.path.join(IMAGE_DIR, filename)

            with open(full_path, "wb") as f:
                f.write(image_data)

            item["image"] = "static/images/" + filename
            item["image_checked"] = True
            return True

    except Exception as error:
        print("تعذر تحميل صورة الصنف", item.get("name"), error)

    return False


def prepare_menu_images():
    changed = False
    for item in menu:
        if not item.get("image") and not item.get("image_checked"):
            download_food_image(item)
            changed = True
    if changed:
        save_menu()


STYLE = """
<style>
* { box-sizing: border-box; }
body {
    background: #fff4e8;
    font-family: Tahoma, Arial, sans-serif;
    direction: rtl;
    text-align: center;
    margin: 0;
    color: #333;
}
header {
    background: #ff6500;
    color: white;
    padding: 20px;
}
.card {
    background: white;
    margin: 15px auto;
    padding: 18px;
    border-radius: 15px;
    box-shadow: 0 2px 7px #ddd;
    max-width: 550px;
}
button {
    background: #ff6500;
    color: white;
    border: 0;
    padding: 12px 20px;
    border-radius: 8px;
    margin: 5px;
    font-size: 16px;
}
input {
    padding: 12px;
    margin: 7px;
    border: 1px solid #ccc;
    border-radius: 8px;
    width: 90%;
    font-size: 16px;
}
input[type=checkbox] { width: auto; }
a {
    color: #ff6500;
    text-decoration: none;
    font-weight: bold;
}
.price { color: #e65b00; }
.food-image {
    width: 100%;
    max-width: 320px;
    height: 190px;
    object-fit: cover;
    border-radius: 12px;
    display: block;
    margin: 10px auto;
}
.no-image {
    background: #fff0e2;
    border-radius: 12px;
    padding: 35px 10px;
    margin: 10px auto;
    max-width: 320px;
    color: #9b6038;
}
footer { padding: 20px; }
</style>
"""


def page(content, **data):
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>SANDY</title>
    """ + STYLE + """
    </head>
    <body>
    """ + content + """
    </body>
    </html>
    """, **data)


def admin_required():
    return session.get("admin") is True


@app.route("/")
def home():
    prepare_menu_images()

    content = """
    <header>
        <h1>{{ settings.restaurant }} 🍗</h1>
        <h3>{{ settings.subtitle }}</h3>
        <p>أهلاً وسهلاً بكم</p>
    </header>

    <h2>قائمة الطعام</h2>

    {% for item in menu %}
    <div class="card">
        {% if item.image %}
            <img class="food-image" src="/{{ item.image }}" alt="{{ item.name }}">
        {% else %}
            <div class="no-image">لا توجد صورة متاحة لهذا الصنف حالياً</div>
        {% endif %}
        <h3>{{ item.name }}</h3>
        <h2 class="price">{{ item.price }} جنيه</h2>

        <form method="POST" action="/add_to_cart">
            <input type="hidden" name="name" value="{{ item.name }}">
            <input type="number" name="quantity" value="1" min="1" max="50" required>
            <button type="submit">أضف للسلة 🛒</button>
        </form>
    </div>
    {% endfor %}

    <div class="card">
        <h3>تواصل معنا</h3>
        <p>{{ settings.phone }}</p>
        <p>{{ settings.address }}</p>
        <a href="/cart">سلة المشتريات 🛒</a>
    </div>

    <div class="card"><a href="/qr">رمز QR Code 📱</a></div>

    <footer><a href="/admin">إدارة المطعم ⚙️</a></footer>
    """
    return page(content, menu=menu, settings=settings)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == PASSWORD:
            session["admin"] = True
            return redirect("/admin")

        return page("""
        <header><h2>إدارة مطعم SANDY</h2></header>
        <div class="card">
            <h2 style="color:red">الرقم السري غير صحيح</h2>
            <a href="/admin">حاول مرة أخرى</a>
        </div>
        """)

    if not admin_required():
        return page("""
        <header><h2>إدارة مطعم SANDY</h2></header>
        <div class="card">
            <h3>تسجيل دخول الإدارة</h3>
            <form method="POST" action="/admin">
                <label for="password">الرقم السري</label>
                <input type="password" id="password" name="password"
                       placeholder="أدخل الرقم السري" autocomplete="current-password" required>
                <p>
                    <input type="checkbox" onclick="
                    var p=document.getElementById('password');
                    p.type=p.type==='password'?'text':'password';">
                    إظهار الرقم السري
                </p>
                <button type="submit">دخول الإدارة</button>
            </form>
        </div>
        <a href="/">الرئيسية</a>
        """)

    prepare_menu_images()

    content = """
    <header>
        <h2>لوحة تحكم SANDY</h2>
        <p>إدارة المطعم</p>
    </header>

    <div class="card">
        <h3>إعدادات المطعم</h3>
        <form method="POST" action="/save_settings">
            <input name="restaurant" value="{{ settings.restaurant }}" placeholder="اسم المطعم" required>
            <input name="subtitle" value="{{ settings.subtitle }}" placeholder="وصف المطعم">
            <input name="phone" value="{{ settings.phone }}" placeholder="رقم الهاتف">
            <input name="address" value="{{ settings.address }}" placeholder="عنوان المطعم">
            <button type="submit">حفظ بيانات المطعم</button>
        </form>
    </div>

    <h3>الأصناف الحالية</h3>
    {% for item in menu %}
    <div class="card">
        {% if item.image %}
            <img class="food-image" src="/{{ item.image }}" alt="{{ item.name }}">
        {% endif %}
        <form method="POST" action="/update">
            <input type="hidden" name="old_name" value="{{ item.name }}">
            <input name="name" value="{{ item.name }}" required>
            <input type="number" name="price" value="{{ item.price }}" min="0" required>
            <button type="submit">حفظ التعديل</button>
        </form>
        <form method="POST" action="/delete">
            <input type="hidden" name="name" value="{{ item.name }}">
            <button type="submit">حذف الصنف</button>
        </form>
    </div>
    {% endfor %}

    <div class="card">
        <h3>إضافة صنف جديد</h3>
        <form method="POST" action="/add">
            <input name="name" placeholder="اسم الصنف" required>
            <input type="number" name="price" placeholder="السعر بالجنيه" min="0" required>
            <button type="submit">إضافة الصنف وتحميل صورته</button>
        </form>
        <p>سيحاول التطبيق البحث عن صورة مناسبة وحفظها تلقائياً.</p>
    </div>

    <div class="card"><a href="/qr">عرض QR Code</a></div>
    <p><a href="/">الرئيسية</a></p>
    <p><a href="/logout">تسجيل الخروج</a></p>
    """
    return page(content, menu=menu, settings=settings)


@app.route("/save_settings", methods=["POST"])
def save_settings_route():
    if not admin_required():
        return redirect("/admin")

    settings["restaurant"] = request.form.get("restaurant", "SANDY").strip()
    settings["subtitle"] = request.form.get("subtitle", "").strip()
    settings["phone"] = request.form.get("phone", "").strip()
    settings["address"] = request.form.get("address", "").strip()
    save_settings()
    return redirect("/admin")


@app.route("/add", methods=["POST"])
def add():
    if not admin_required():
        return redirect("/admin")

    name = request.form.get("name", "").strip()
    try:
        price = int(request.form.get("price", 0))
        if price < 0:
            return "السعر غير صحيح"
    except ValueError:
        return "السعر غير صحيح"

    if name:
        new_item = {"name": name, "price": price}
        download_food_image(new_item)
        menu.append(new_item)
        save_menu()

    return redirect("/admin")


@app.route("/update", methods=["POST"])
def update():
    if not admin_required():
        return redirect("/admin")

    old_name = request.form.get("old_name", "")
    new_name = request.form.get("name", "").strip()
    try:
        price = int(request.form.get("price", 0))
        if price < 0:
            return "السعر غير صحيح"
    except ValueError:
        return "السعر غير صحيح"

    for item in menu:
        if item["name"] == old_name:
            item["name"] = new_name
            item["price"] = price
            break

    save_menu()
    return redirect("/admin")


@app.route("/delete", methods=["POST"])
def delete():
    if not admin_required():
        return redirect("/admin")

    name = request.form.get("name", "")
    menu[:] = [item for item in menu if item["name"] != name]
    save_menu()
    return redirect("/admin")


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    name = request.form.get("name", "")
    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        return redirect("/")

    item = next((x for x in menu if x["name"] == name), None)
    if item and 1 <= quantity <= 50:
        cart = session.get("cart", {})
        cart[name] = cart.get(name, 0) + quantity
        session["cart"] = cart

    return redirect("/cart")


@app.route("/cart")
def cart_page():
    cart = session.get("cart", {})
    items = []
    total = 0

    for item in menu:
        quantity = cart.get(item["name"], 0)
        if quantity > 0:
            subtotal = item["price"] * quantity
            total += subtotal
            items.append({
                "name": item["name"],
                "price": item["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })

    content = """
    <header><h2>سلة مشتريات SANDY 🛒</h2></header>
    {% if not items %}
    <div class="card"><h3>السلة فارغة</h3></div>
    {% endif %}
    {% for item in items %}
    <div class="card">
        <h3>{{ item.name }}</h3>
        <p>السعر: {{ item.price }} جنيه</p>
        <p>الكمية: {{ item.quantity }}</p>
        <h3>الإجمالي: {{ item.subtotal }} جنيه</h3>
        <form method="POST" action="/remove_from_cart">
            <input type="hidden" name="name" value="{{ item.name }}">
            <button type="submit">حذف الصنف</button>
        </form>
    </div>
    {% endfor %}
    <div class="card">
        <h2>الإجمالي الكلي: {{ total }} جنيه</h2>
        <a href="/">العودة للمنيو</a>
    </div>
    """
    return page(content, items=items, total=total)


@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    cart = session.get("cart", {})
    name = request.form.get("name", "")
    cart.pop(name, None)
    session["cart"] = cart
    return redirect("/cart")


@app.route("/qr")
def qr_page():
    url = request.url_root
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    content = """
    <header>
        <h2>{{ settings.restaurant }} 🍗</h2>
        <p>رمز QR لقائمة الطعام</p>
    </header>
    <div class="card">
        <h3>امسح الرمز لفتح قائمة الطعام</h3>
        <img src="data:image/png;base64,{{ qr_image }}"
             alt="QR Code" style="width:250px;max-width:90%;height:auto;">
        <p>{{ url }}</p>
        <button onclick="window.print()">طباعة الرمز</button>
    </div>
    <a href="/">العودة للرئيسية</a>
    """
    return page(content, qr_image=qr_image, settings=settings, url=url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
