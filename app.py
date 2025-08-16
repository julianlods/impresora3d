from flask import Flask, render_template, abort, redirect, url_for, request, session, flash
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
from pathlib import Path
import json

# ---- Flask básico
app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"
app.config["ADMIN_USER"] = "j"        # CAMBIALO
app.config["ADMIN_PASSWORD"] = "j"    # CAMBIALO

# ---- Base de datos (SQLite)
from flask_sqlalchemy import SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///catalog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---- Modelos
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Category {self.name}>"

    def __str__(self):
        return self.name  # para que en el admin se vea el nombre

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    category = db.relationship("Category", backref=db.backref("products", lazy=True))

    def __repr__(self):
        return f"<Product {self.name}>"

# === NUEVO: Solicitudes de artículos ===
class SolicitudArticulo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<SolicitudArticulo {self.nombre}>"

# ---- Admin
class _AuthMixin:
    def is_accessible(self):
        return session.get("admin", False)
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login", next=request.url))

class CategoryAdmin(_AuthMixin, ModelView):
    extra_css = ["/static/admin.css"]
    create_modal = True
    edit_modal = True
    details_modal = True
    category = "Catálogo"
    form_columns = ["name", "slug", "description"]
    form_widget_args = {
        "name": {"class": "form-control form-control-sm"},
        "slug": {"class": "form-control form-control-sm"},
        "description": {"rows": 3, "style": "resize:vertical;"},
    }

class ProductAdmin(_AuthMixin, ModelView):
    extra_css = ["/static/admin.css"]
    create_modal = True
    edit_modal = True
    details_modal = True
    category = "Catálogo"

    form_columns = ["name", "slug", "description", "price", "image_url", "category"]
    column_list = ["name", "category", "price", "slug"]
    column_labels = {
        "image_url": "Imagen (URL)",
        "category": "Categoría",
        "name": "Producto",
        "price": "Precio",
        "slug": "Slug",
    }
    column_sortable_list = ["name", ("category", "category.name"), "price", "slug"]
    column_searchable_list = ["name", "slug", "description", "category.name"]
    form_widget_args = {
        "name": {"class": "form-control form-control-sm"},
        "slug": {"class": "form-control form-control-sm"},
        "price": {"class": "form-control form-control-sm"},
        "image_url": {"class": "form-control form-control-sm"},
        "description": {"rows": 3, "style": "resize:vertical;"},
    }
    form_ajax_refs = {
        "category": {"fields": ("name", "slug")}
    }

class SolicitudAdmin(_AuthMixin, ModelView):
    extra_css = ["/static/admin.css"]
    can_view_details = True
    column_list = ["nombre", "created_at"]
    column_labels = {"nombre": "Artículo", "created_at": "Recibida"}
    column_default_sort = ("created_at", True)
    form_columns = ["nombre"]
    category = "Solicitudes"

class SecureIndexView(_AuthMixin, AdminIndexView):
    extra_css = ["/static/admin.css"]
    # Ocultar "Home" vacío del menú
    def is_visible(self):
        return False

admin = Admin(
    app,
    name="El Sultán - Admin",
    index_view=SecureIndexView(url="/admin"),
    template_mode="bootstrap4",
)
admin.add_view(CategoryAdmin(Category, db.session))
admin.add_view(ProductAdmin(Product, db.session))
admin.add_view(SolicitudAdmin(SolicitudArticulo, db.session))  # NUEVA SOLAPA

# ---- Utilidades (para tu footer y el menú)
@app.context_processor
def inject_year():
    return {"current_year": datetime.now().year}

# --- Contexto global: categorías para el menú
@app.context_processor
def inject_globals():
    cats = Category.query.order_by(Category.name).all()
    return {"nav_categories": cats, "current_year": datetime.now().year}

# ---- FRONT EXISTENTE (sigue leyendo tu JSON de prueba)
DATA_PATH = Path(__file__).parent / "data" / "impresoras.json"

def load_data():
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.route("/")
def home():
    productos = Product.query.order_by(Product.id.desc()).limit(12).all()
    return render_template("index.html", productos=productos)

@app.route("/impresoras/<slug>")
def detalle(slug):
    impresoras = load_data()
    item = next((i for i in impresoras if i.get("slug") == slug), None)
    if not item:
        abort(404)
    return render_template("detalle.html", i=item)

@app.route("/quienes-somos")
def quienes_somos():
    return render_template("quienes_somos.html")

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

# --- Catálogo: todos los productos
@app.route("/catalogo")
def catalogo():
    categorias = Category.query.order_by(Category.name).all()
    return render_template("catalogo.html", categorias=categorias)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if u == app.config["ADMIN_USER"] and p == app.config["ADMIN_PASSWORD"]:
            session["admin"] = True
            return redirect(request.args.get("next") or url_for("admin.index"))
        error = "Usuario o contraseña inválidos."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/producto/<slug>")
def producto(slug):
    p = Product.query.filter_by(slug=slug).first_or_404()
    return render_template("producto.html", p=p)

@app.route("/categoria/<slug>")
def categoria(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    productos = Product.query.filter_by(category_id=cat.id).order_by(Product.name).all()
    return render_template("categoria.html", categoria=cat, productos=productos)

# ---- Inicializar DB (ejecutar 1 sola vez)
@app.route("/initdb")
def initdb():
    db.create_all()
    return "DB creada OK"

# ---- Guardar solicitud y avisar al usuario
@app.route("/solicitar-articulo", methods=["POST"])
def solicitar_articulo():
    nombre = request.form.get("nombre_articulo", "").strip()
    if nombre:
        s = SolicitudArticulo(nombre=nombre)
        db.session.add(s)
        db.session.commit()
        flash("Tu solicitud fue enviada. ¡Gracias!", "success")
    else:
        flash("Necesitás indicar el nombre del artículo.", "error")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
