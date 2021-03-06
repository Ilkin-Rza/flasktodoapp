from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

#Istifadeci girisi decoratoru
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu səhifəni görmək üçün zəhmət olmasa hesabınıza daxil olun","danger")
            return redirect(url_for("login"))
    return decorated_function

# Istifadeci girisi Forumu
class RegisterForm(Form):
    name=StringField("Ad Soyad",validators=[validators.Length(min=4,max=25)])
    username=StringField("Istifadəçi adı",validators=[validators.Length(min=4,max=25)])
    email=StringField("Email Adresi",validators=[validators.Email(message="Zəhmət olmasa düzgün email adresi qeyd edin...")])
    password=PasswordField("Parol:",validators=[
        validators.DataRequired(message="Zehmet olmasa parolu daxil edin..."),
        validators.EqualTo(fieldname="confirm",message="Parolunuz uyğunlaşmır")
    ])
    confirm=PasswordField("Parolu tesdiqleme")

class LoginForm(Form):
    username=StringField("Istifadəçi Adı")
    password=PasswordField("Parol")

app = Flask(__name__, template_folder="Temp")
app.secret_key="ybbloq"

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybbloq"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu="Select * From articles"
    result=cursor.execute(sorgu)

    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()

    sorgu="Select * From articles where author=%s"

    result=cursor.execute(sorgu,(session["username"],))

    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

# Qeydiyyat
@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)

    if request.method=="POST" and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)
        
        cursor=mysql.connection.cursor()

        sorgu="Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()

        cursor.close()

        flash("Qeydiyyatdan müvəffəqiyətlə keçdiniz...","success")
        return redirect(url_for("login"))
    
    else:
        return render_template("register.html",form=form)

#Girish Emeliyyati
@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()

        sorgu="Select * From users where username=%s"

        result=cursor.execute(sorgu,(username,))

        if result > 0:
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Müvəffəqiyətlə Daxil Oldunuz","success")

                session["logged_in"]=True
                session["username"]=username

                return redirect(url_for("index"))
            else:
                flash("Parolunuzu Səhv Yazmısınız!!!","danger")
                return redirect(url_for("login"))

        else:
            flash("Bu Istifadeci Mövcud Deyil!!!","danger")
            return redirect(url_for("login"))       

    return render_template("login.html",form=form)

#Melumat Sehifesi
@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from articles where id=%s"

    result=cursor.execute(sorgu,(id,))

    if result>0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

# Logout Prosesi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Meqale Yaratmaq
@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data

        cursor=mysql.connection.cursor()
        sorgu="Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Məqalə Elavə Olundu","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form=form)

#Meqale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from articles where author=%s and id=%s"
    result=cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2="Delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))

    else:
        flash("Bele bir meqale mövcud deyil ve ya hesabınıza daxil olmamısınız","danger")
        return redirect(url_for("index"))

#Meqale Guncelleme
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="Select * from articles where id=%s and author=%s"
        result=cursor.execute(sorgu,(id,session["username"]))

        if result==0:
            flash("Bele bir meqale mövcud deyil ve ya hesabınıza daxil olmamısınız","danger")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form=ArticleForm()
            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
    else:
        #Post Request
        form=ArticleForm(request.form)
        newTitle=form.title.data
        newContent=form.content.data

        sorgu2="Update articles Set title=%s,content=%s where id=%s"

        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Meqaleniz yenilenmisdir","success")
        return redirect(url_for("dashboard"))

#Meqale Form
class ArticleForm(Form):
    title=StringField("Meqale Başlığı",validators=[validators.Length(min=5,max=25)])
    content=TextAreaField("Meqale Məzmunu",validators=[validators.Length(min=10)])

#URL Axtarma
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")
        cursor=mysql.connection.cursor()
        sorgu="Select * from articles where title like '%" + keyword + "%'"
        result=cursor.execute(sorgu)

        if result==0:
            flash("Axtarılan sorğuya uygun bir meqale tapılmadı!..","danger")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)



if __name__ == "__main__":
    app.run(debug=True)
