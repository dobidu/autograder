"""Tests for authentication flows."""


def test_login_page(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "Entrar" in r.text


def test_register_page(client):
    r = client.get("/register")
    assert r.status_code == 200
    assert "Cadastrar" in r.text


def test_register_and_login(client):
    # Register
    r = client.post("/register", data={
        "name": "Novo Aluno",
        "email": "novo@test.com",
        "password": "senha123",
        "password_confirm": "senha123",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "session" in str(r.headers.get("set-cookie", ""))

    # Login
    r = client.post("/login", data={
        "email": "novo@test.com",
        "password": "senha123",
    }, follow_redirects=False)
    assert r.status_code == 303


def test_register_duplicate_email(client):
    data = {
        "name": "A", "email": "dup@test.com",
        "password": "senha123", "password_confirm": "senha123",
    }
    client.post("/register", data=data, follow_redirects=False)
    r = client.post("/register", data=data)
    assert r.status_code == 400
    assert "já cadastrado" in r.text


def test_register_password_mismatch(client):
    r = client.post("/register", data={
        "name": "A", "email": "a@t.com",
        "password": "senha123", "password_confirm": "outra456",
    })
    assert r.status_code == 400
    assert "não coincidem" in r.text


def test_login_wrong_password(client, student):
    r = client.post("/login", data={
        "email": "student@test.com",
        "password": "wrong",
    })
    assert r.status_code == 400
    assert "incorretos" in r.text


def test_logout(client, stu_cookies):
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_dashboard_redirect_to_login(client):
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers.get("location", "")


def test_student_dashboard(client, stu_cookies):
    r = client.get("/dashboard", cookies=stu_cookies)
    assert r.status_code == 200
    assert "Trabalhos" in r.text


def test_professor_dashboard(client, prof_cookies):
    r = client.get("/admin/dashboard", cookies=prof_cookies)
    assert r.status_code == 200
    assert "Painel" in r.text


def test_student_cannot_access_admin(client, stu_cookies):
    r = client.get("/admin/dashboard", cookies=stu_cookies)
    assert r.status_code == 403
