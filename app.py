from flask import Flask, render_template, abort, redirect, url_for, request, session, flash
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from datetime import datetime, timedelta
from pathlib import Path
import json
from flask_admin.form import FileUploadField
import os


# ---- Flask básico
app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"
app.config["ADMIN_USER"] = "j"        # CAMBIALO
app.config["ADMIN_PASSWORD"] = "j"    # CAMBIALO
app.config["UPLOAD_FOLDER"] = os.path.join(Path(__file__).parent, "static", "uploads")
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)


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
    image_file = db.Column(db.String(500), nullable=True)  # archivo subido
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

# === NUEVO: Ventas por producto ===
class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product = db.relationship("Product", backref=db.backref("ventas", lazy=True))
    color = db.Column(db.String(50), nullable=True)

    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    costo_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    entregado = db.Column(db.Boolean, nullable=False, default=False)

    @property
    def total_venta(self):
        return float(self.precio_venta or 0) * (self.cantidad or 0)

    @property
    def total_costo(self):
        return float(self.costo_unitario or 0) * (self.cantidad or 0)

    @property
    def ganancia(self):
        return self.total_venta - self.total_costo

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

    form_columns = ["name", "slug", "description", "price", "image_url", "image_file", "category"]
    column_list = ["name", "category", "price", "slug"]

    column_labels = {
        "image_url": "Imagen (URL)",
        "image_file": "Imagen (archivo)",
        "category": "Categoría",
        "name": "Producto",
        "price": "Precio",
        "slug": "Slug",
    }

    form_widget_args = {
        "name": {"class": "form-control form-control-sm"},
        "slug": {"class": "form-control form-control-sm"},
        "price": {"class": "form-control form-control-sm"},
        "image_url": {"class": "form-control form-control-sm"},
        "description": {"rows": 3, "style": "resize:vertical;"},
    }

    form_overrides = {
        "image_file": FileUploadField
    }
    form_args = {
        "image_file": {
            "label": "Subir imagen",
            "base_path": app.config["UPLOAD_FOLDER"],
            "allow_overwrite": False
        }
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

class VentaAdmin(_AuthMixin, ModelView):
    extra_css = ["/static/admin.css"]
    create_modal = True
    edit_modal = True
    details_modal = True
    category = "Ventas"

    # Columnas que se muestran en la tabla
    column_list = [
        "product",
        "color",
        "fecha",
        "precio_venta",
        "cantidad",
        "total_venta",
        "costo_unitario",
        "entregado",
    ]

    column_labels = {
        "product": "Producto",
        "color": "Color",
        "fecha": "Fecha",
        "precio_venta": "Precio Venta",
        "cantidad": "Cantidad",
        "total_venta": "Total",
        "costo_unitario": "Costo Unitario",
        "entregado": "¿Entregado?",
    }

    # Campos del formulario
    form_columns = [
        "product",
        "color",
        "fecha",
        "precio_venta",
        "cantidad",
        "costo_unitario",
        "entregado",
    ]

    form_widget_args = {
        "color": {"class": "form-control form-control-sm"},
        "fecha": {"class": "form-control form-control-sm"},
        "precio_venta": {"class": "form-control form-control-sm"},
        "cantidad": {"class": "form-control form-control-sm"},
        "costo_unitario": {"class": "form-control form-control-sm"},
    }

    # 🔥 Importante: mostrar solo el nombre del producto en el combo
    form_args = {
        "product": {
            "query_factory": lambda: Product.query.order_by(Product.name),
            "get_label": "name",
        }
    }

    # Formato de la columna entregado
    column_formatters = {
        "entregado": lambda v, c, m, p: "Sí" if m.entregado else "No"
    }

class ResumenVentasView(_AuthMixin, BaseView):
    extra_css = ["/static/admin.css"]
    category = "Ventas"

    @expose("/", methods=["GET", "POST"])
    def index(self):
        # --- Filtros de fecha ---
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        periodo = request.args.get("periodo")

        today = datetime.utcnow().date()

        if periodo == "hoy":
            desde = today
            hasta = today

        elif periodo == "semana":
            desde = today - timedelta(days=today.weekday())
            hasta = today

        elif periodo == "mes":
            desde = today.replace(day=1)
            hasta = today

        elif periodo == "anio":
            desde = today.replace(month=1, day=1)
            hasta = today

        # Convertir strings a fechas
        if desde:
            desde = datetime.strptime(str(desde), "%Y-%m-%d").date()
        if hasta:
            hasta = datetime.strptime(str(hasta), "%Y-%m-%d").date()

        # Query base
        ventas_query = Venta.query

        if desde:
            ventas_query = ventas_query.filter(Venta.fecha >= desde)
        if hasta:
            ventas_query = ventas_query.filter(Venta.fecha <= hasta)

        ventas = ventas_query.all()

        # ---- Cálculos ----
        total_ventas = len(ventas)
        total_unidades = sum(v.cantidad or 0 for v in ventas)
        total_ingresos = sum(v.total_venta for v in ventas)
        total_costos = sum(v.total_costo for v in ventas)
        total_ganancia = sum(v.ganancia for v in ventas)

        # Resumen por producto
        productos_stats = {}
        for v in ventas:
            nombre = v.product.name if v.product else "Sin producto"

            if nombre not in productos_stats:
                productos_stats[nombre] = {
                    "cantidad": 0,
                    "ingresos": 0.0,
                    "costos": 0.0,
                    "ganancia": 0.0,
                }

            productos_stats[nombre]["cantidad"] += v.cantidad or 0
            productos_stats[nombre]["ingresos"] += v.total_venta
            productos_stats[nombre]["costos"] += v.total_costo
            productos_stats[nombre]["ganancia"] += v.ganancia

        productos_ordenados = sorted(
            productos_stats.items(),
            key=lambda item: item[1]["ingresos"],
            reverse=True,
        )

        return self.render(
            "admin/resumen_ventas.html",
            total_ventas=total_ventas,
            total_unidades=total_unidades,
            total_ingresos=total_ingresos,
            total_costos=total_costos,
            total_ganancia=total_ganancia,
            productos_ordenados=productos_ordenados,
            desde=desde,
            hasta=hasta,
        )

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
admin.add_view(SolicitudAdmin(SolicitudArticulo, db.session))
admin.add_view(VentaAdmin(Venta, db.session))
admin.add_view(ResumenVentasView(name="Resumen de Ventas", endpoint="resumen_ventas"))

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
