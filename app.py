from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
import pyrebase
import requests
from functools import wraps
from datetime import datetime, timedelta
import time
import json
from core.attendance.class_attendance import Attendance
from core.wallet.class_wallet_os import Wallet
from core.user.class_user_wallet import User_Wallet
from core.user.class_user_attendant_wallet import User_Wallet_Attendant
from core.user.class_user import User
import pytz
from config import db, auth, storage, firebase
from collections import defaultdict
from core.cities.class_cities import Cities
from core.advanced_signature_component import AdvancedSignatureComponent
from core.financeiro.class_financeiro import Financeiro
from flask_cors import CORS
import re



app = Flask(__name__)
CORS(app)
app.secret_key = 'secret'


def datetimeformat(value, format='%d/%m/%Y %H:%M:%S'):
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    
    # Converta o timestamp para o horÃ¡rio de SÃ£o Paulo
    dt_sao_paulo = datetime.fromtimestamp(value, sao_paulo_tz)
    
    # Formate a data e hora no formato desejado
    return dt_sao_paulo.strftime(format)

def datetimeformathour(value, format='%H:%M'):
    return datetime.strptime(value, '%Y-%m-%d %H:%M').strftime(format)

# Registre o filtro no ambiente Jinja2
app.jinja_env.filters['datetimeformat'] = datetimeformat

app.jinja_env.filters['datetimeformathour'] = datetimeformathour

def normalize_search_value(value):
    if value is None:
        return ""
    return re.sub(r'\W+', '', str(value)).lower()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = user['localId']
            session['email'] = email

            user_data = db.child("users").child(user['localId']).get().val()
            session['role'] = user_data.get('role', 'user')
            session['name'] = user_data.get('name')
            
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            
            elif session['role'] == 'user':
                return redirect(url_for('dashboard'))
            
            elif session['role'] == 'tecnico':
                return redirect(url_for('dashboard_tecnico'))  
        except:
            return "Falha no login"
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.create_user_with_email_and_password(email, password)
            # Defina o nÃ­vel de acesso padrÃ£o e salve o nome do usuÃ¡rio
            db.child("users").child(user['localId']).set({
                "name": name,
                "email": email,
                "password": password,
                "role": "user",  # Define o papel padrÃ£o como 'user'
                "cities": []  # Lista de cidades vazia por padrÃ£o
            })
            return redirect(url_for('login'))
        except:
            return "Falha no cadastro"
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)
    return redirect(url_for('login'))


def check_roles(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            user_role = db.child("users").child(session['user']).get().val().get('role')  # type: ignore
            if user_role not in allowed_roles:
                return "Acesso negado"
            return f(*args, **kwargs)

        return decorated_function

    return decorator


AdvancedSignatureComponent.register_component(
    app,
    firebase.database,
    check_roles,
    report_node="relatorios",
)


@app.route("/", methods=["POST", "GET"])
def homepage():
    if 'user' not in session:
        return redirect(url_for('login'))
    else:
        if session['role'] == 'user':
            return redirect(url_for('dashboard'))
        
        elif session['role'] == 'tecnico':
            return redirect(url_for('dashboard_tecnico'))
        elif session['role'] == 'admin':
            return redirect(url_for('admin'))


@app.route('/dashboard')
@check_roles(['user', 'admin'])
def dashboard():
    user_email = session.get('email', 'UsuÃ¡rio')
    return render_template('dashboard.html', user_email=user_email)

@app.route('/dashboard_tecnico')
@check_roles(['tecnico'])
def dashboard_tecnico():
    user_email = session.get('email', 'UsuÃ¡rio')
    return render_template('dashboard_tecnico.html', user_email=user_email)


@app.route('/admin')
@check_roles('admin')
def admin():
    user_email = session.get('email', 'Admin')
    return render_template('admin.html', user_email=user_email)


@app.route('/adm_painel_os')
@check_roles(['admin'])
def adm_painel_os():
    return render_template('adm_painel_os.html')

@app.route('/attendance')
@check_roles('admin')
def attendance():
    return render_template('attendance.html')


@app.route('/add_city', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_city():
    if request.method == 'POST':
        uf_name = request.form['uf']
        city_name = request.form['city']
        phone_number = request.form['phone']

        # Verifique se a cidade jÃ¡ existe
        cities = db.child("cities").get().val() or {}
        if city_name not in cities.values():
            db.child("cities").push(city_name)

            db.child("uf").child(uf_name).child(city_name).set(phone_number)
            return redirect(url_for('add_city'))
        else:
            return "Cidade jÃ¡ existe"
        

    return render_template('add_city.html')

@app.route('/add_city_sistema', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_city_sistema():
    if request.method == 'POST':
        city_name = request.form['city']

        # Verifique se a cidade jÃ¡ existe
        cities = db.child("cities").get().val() or {}
        if city_name not in cities.values():
            db.child("cities").push(city_name)

            
            return redirect(url_for('add_city'))
        else:
            return "Cidade jÃ¡ existe"
       
    return render_template('add_city.html')

@app.route('/add_city_relatorio', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_city_relatorio():
    if request.method == 'POST':
        uf_name = request.form['uf']
        city_name = request.form['city']
        phone_number = request.form['phone']

        
        db.child("uf").child(uf_name).child(city_name).set(phone_number)
        return redirect(url_for('add_city'))

    return render_template('add_city.html')

@app.route('/list_cities')
@check_roles(['admin'])
def list_cities():
    cities = db.child("cities").get().val() or {}
    return render_template('list_cities.html', cities=cities)


@app.route('/link_user_city', methods=['GET', 'POST'])
@check_roles(['admin'])
def link_user_city():
    if request.method == 'POST':
        user_id = request.form['user_id']
        city = request.form['city']

        # Obtenha as cidades atuais do usuÃ¡rio
        user_cities = db.child("users").child(user_id).child("cities").get().val() or []

        if city not in user_cities:
            user_cities.append(city)
            db.child("users").child(user_id).update({"cities": user_cities})

        return "UsuÃ¡rio vinculado Ã  cidade com sucesso"

    # Obtenha todos os usuÃ¡rios e cidades para o formulÃ¡rio
    users = db.child("users").get().val()

    # Filtrar apenas os usuÃ¡rios com papel "user"
    user_role = 'user'
    users = {user_id: user for user_id, user in users.items() if user.get('role') == user_role}

    cities = db.child("cities").get().val() or {}

    return render_template('link_user_city.html', users=users, cities=cities)


def convert_monetary_value(value_str):
    # Verifique se o valor jÃ¡ estÃ¡ no formato desejado
    if '.' in value_str and ',' not in value_str:
        # Retorne o valor como estÃ¡, pois jÃ¡ estÃ¡ no formato correto
        return value_str

    # Se nÃ£o estiver no formato desejado, faÃ§a a substituiÃ§Ã£o necessÃ¡ria
    clean_value = value_str.replace('.', '').replace(',', '.')

    return clean_value


@app.route('/attendance_records', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def attendance_records():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']

    if request.method == 'POST':
        # Dados do formulÃ¡rio
        canal = request.form['canal']
        name = request.form['name']
        sexo = request.form['sexo']
        phone = request.form['phone']
        price = request.form['price']
        city = request.form['city']
        service = request.form['service']
        status = "Aguardando"
        details = request.form['details']

        price = convert_monetary_value(price)

        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')

        now_in_sao_paulo = datetime.now(sao_paulo_tz)

        timestamp = now_in_sao_paulo.timestamp()

        # Obter a data atual
        
        now = datetime.now(sao_paulo_tz)
        year = str(now.year)
        month = f"{now.month:02d}"  # Garantir que o mÃªs tenha dois dÃ­gitos
        day = f"{now.day:02d}"  # Garantir que o dia tenha dois dÃ­gitos

        # Criar um registro de atendimento
        attendance_record = {
            "user_id": user_id,
            "name": name,
            "sexo": sexo,
            "phone": phone,
            "price": price,
            "service": service,
            "status": status,
            "details": details,
            "canal": canal,
            "timestamp": timestamp
        }

        # Salvar o registro de atendimento sob a estrutura desejada
        db.child("attendance_records").child(city).child(year).child(month).child(day).push(attendance_record)
        return redirect(url_for('dashboard'))

    # Carregar as cidades vinculadas ao usuÃ¡rio
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    # Carregar todos os serviÃ§os disponÃ­veis
    services = db.child("services").get().val() or {}

    return render_template('attendance_records.html', cities=cities, services=services)


@app.route('/add_service', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_service():
    if request.method == 'POST':
        service_name = request.form['service']

        # Verifique se o serviÃ§o jÃ¡ existe
        services = db.child("services").get().val() or {}
        if service_name not in services.values():
            db.child("services").push(service_name)
            return "ServiÃ§o adicionado com sucesso"
        else:
            return "ServiÃ§o jÃ¡ existe"

    return render_template('add_service.html')


@app.route('/list_services')
@check_roles(['admin'])
def list_services():
    services = db.child("services").get().val() or {}
    return render_template('list_services.html', services=services)


@app.route('/consulta_atendimentos', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def consulta_atendimentos():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']

    # Carregar as cidades vinculadas ao usuÃ¡rio
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    return render_template('consulta_atendimentos.html', cities=cities)

@app.route('/adm_consulta_atendimentos', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def adm_consulta_atendimentos():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Carregar as cidades vinculadas ao usuÃ¡rio
    cities = db.child("cities").get().val().values()

    return render_template('adm_consulta_atendimentos.html', cities=cities)
    


@app.route('/view_attendance', methods=['GET'])
@check_roles(['user', 'admin'])
def view_attendance():
    city = request.args.get('city')
    date_str = request.args.get('date')

    if not city or not date_str:
        return "Cidade ou data nÃ£o fornecida."

    # Verifique se o usuÃ¡rio tem permissÃ£o para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    if city not in user_data.get('cities', []):
        return "VocÃª nÃ£o tem permissÃ£o para acessar registros desta cidade."

    # Converter a data fornecida para ano, mÃªs e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtenha todos os registros de atendimento para a cidade e data especificadas
    attendance_records = db.child("attendance_records").child(city).child(year).child(month).child(
        day).get().val() or {}

    all_users = db.child("users").get().val() or {}
    tecnicos = {uid: user for uid, user in all_users.items() if
                user['role'] == 'tecnico' and city in user.get('cities', [])}

    return render_template('view_attendance.html', records=attendance_records, city=city, date=f"{day}/{month}/{year}",
                           tecnicos=tecnicos)

@app.route('/adm_view_attendance', methods=['GET'])
@check_roles(['user', 'admin'])
def adm_view_attendance():
    city = request.args.get('city')
    date_str = request.args.get('date')

    if not city or not date_str:
        return "Cidade ou data nÃ£o fornecida."

    # Verifique se o usuÃ¡rio tem permissÃ£o para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    is_admin = user_data.get('role') == 'admin'
    has_city_permission = city in user_data.get('cities', [])

    if not (is_admin or has_city_permission):
        return "VocÃª nÃ£o tem permissÃ£o para acessar registros desta cidade."

    # Converter a data fornecida para ano, mÃªs e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtenha todos os registros de atendimento para a cidade e data especificadas
    attendance_records = db.child("attendance_records").child(city).child(year).child(month).child(
        day).get().val() or {}

    all_users = db.child("users").get().val() or {}
    tecnicos = {uid: user for uid, user in all_users.items() if
                user['role'] == 'tecnico' and city in user.get('cities', [])}

    return render_template('view_attendance.html', records=attendance_records, city=city, date=f"{day}/{month}/{year}",
                           tecnicos=tecnicos)


from collections import defaultdict

@app.route('/view_all_attendances', methods=['GET', 'POST'])
@check_roles(['admin'])
def view_all_attendances():
    if request.method == 'POST':
        selected_date = request.form.get('selected_date')

        if selected_date:
            year, month, day = selected_date.split('-')

            attendance_data = db.child("attendance_records").get().val() or {}

            # DicionÃ¡rio para agrupar atendimentos por user_id
            grouped_records = defaultdict(list)

            for city, years in attendance_data.items():
                if year in years:
                    months = years[year]
                    if month in months:
                        days = months[month]
                        if day in days:
                            attendances = days[day]
                            for attendance_id, attendance_info in attendances.items():
                                user_id = attendance_info.get('user_id')
                                
                                if user_id:
                                    # ObtÃ©m o nome do usuÃ¡rio baseado no user_id
                                    user_name = User.get_name(user_id)

                                    record = {
                                        "city": city,
                                        "date": f"{day}/{month}/{year}",
                                        **attendance_info
                                    }
                                    
                                    # Agrupa pelo nome do usuÃ¡rio
                                    grouped_records[user_name].append(record)
                                else:
                                    # Se user_id nÃ£o estiver presente, continue ou log um erro
                                    print(f"User ID ausente para o atendimento {attendance_id}")

            return render_template('view_all_attendances.html', grouped_records=grouped_records, selected_date=selected_date)
    else:
        return render_template('view_all_attendances.html', grouped_records={}, selected_date=None)


@app.route('/vincular_tecnico', methods=['GET', 'POST'])
@check_roles(['admin'])
def vincular_tecnico():
    if request.method == 'POST':
        tecnico_id = request.form['tecnico']
        novas_cidades = set(request.form.getlist('cidades'))  # Recebe lista de cidades selecionadas

        # Recuperar as cidades atualmente vinculadas ao tÃ©cnico
        tecnico_data = db.child("users").child(tecnico_id).get().val()
        cidades_atuais = set(tecnico_data.get('cities', []))

        # Combinar as cidades atuais com as novas
        cidades_atualizadas = list(cidades_atuais.union(novas_cidades))

        # Atualizar as cidades no banco de dados para o tÃ©cnico selecionado
        db.child("users").child(tecnico_id).update({"cities": cidades_atualizadas})

        return redirect(url_for('vincular_tecnico'))

    # Carregar todos os tÃ©cnicos e cidades disponÃ­veis
    all_users = db.child("users").get().val() or {}
    tecnicos = {uid: user for uid, user in all_users.items() if user['role'] == 'tecnico'}
    
    all_cities = db.child("cities").get().val() or {}

    return render_template('vincular_tecnico.html', tecnicos=tecnicos, all_cities=all_cities)


@app.route('/verifica_agenda', methods=['POST', 'GET'])
def verifica_agenda():
    data = request.json
    date = data.get('date')
    start_time = data.get('startTime')
    end_time = data.get('endTime')
    tecnico_id = data.get('technician')

    date_str = date
    date_firebase = datetime.strptime(date_str, '%Y-%m-%d')

    year = str(date_firebase.year)
    month = f"{date_firebase.month:02d}"  # Garantir que o mÃªs tenha dois dÃ­gitos
    day = f"{date_firebase.day:02d}"  # Garantir que o dia tenha dois dÃ­gitos

    # Combine date and time to create datetime objects
    start_datetime = datetime.strptime(f"{date} {start_time}", '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(f"{date} {end_time}", '%Y-%m-%d %H:%M')

    cities = db.child('users').child(tecnico_id).child('cities').get().val()

    for city in cities:

        #os_existentes = db.child("ordens_servico").order_by_child("tecnico_id").equal_to(tecnico_id).get().val() or {}
        os_existentes = db.child("ordens_servico").child(city).child(year).child(month).child(
            day).order_by_child("tecnico_id").equal_to(tecnico_id).get().val() or {}

        for os_id, os_data in os_existentes.items():
            os_start = datetime.strptime(os_data['start_datetime'], '%Y-%m-%d %H:%M')
            os_end = datetime.strptime(os_data['end_datetime'], '%Y-%m-%d %H:%M')

            # Check for overlapping times
            if not (end_datetime <= os_start or start_datetime >= os_end):
                print(f"O tÃ©cnico jÃ¡ possui uma OS agendada nesse horÃ¡rio.")
                return jsonify({'status': 'conflict', 'message': 'O tÃ©cnico jÃ¡ possui uma OS agendada nesse horÃ¡rio.'}), 400
            

    return jsonify({'status': 'success', 'message': 'HorÃ¡rio livre'}), 200

@app.route('/gerar_os', methods=['POST'])
def gerar_os():
    city = request.form.get('city')
    date_filter = request.form.get('date')
    id_attendance = request.form.get('idRecord')

    date = request.form.get('dateos')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    tecnico_id = request.form.get('tecnico')

    # Combine date and time to create datetime objects
    start_datetime = datetime.strptime(f"{date} {start_time}", '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(f"{date} {end_time}", '%Y-%m-%d %H:%M')

    try:
        if "-" in date_filter:
            data_datetime = datetime.strptime(date_filter, "%Y-%m-%d")
        else:
            data_datetime = datetime.strptime(date_filter, "%d/%m/%Y")

        data_formatada = data_datetime.strftime("%Y-%m-%d")
    except ValueError:
        return "Formato de data inválido.", 400

    # Save the new OS to the database

    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')

    now_in_sao_paulo = datetime.now(sao_paulo_tz)

    timestamp = now_in_sao_paulo.timestamp()

    newprice = request.form.get('priceservice')
    if not newprice:
        newprice = "0.00"
    else:
        newprice = convert_monetary_value(newprice)
    
    contador = db.child("contador_os").get().val()
    if contador is None:
        contador = 0

    # Incrementa
    novo_numero_os = contador + 1
    db.child("contador_os").set(novo_numero_os)


    nova_os = {
        "numero_os": novo_numero_os,
        "city": request.form.get('city'),
        "name": request.form.get('name'),
        "cpfcnpj": request.form.get('cpfcnpj'),
        "phone": request.form.get('phone'),
        "service": request.form.get('service'),
        "oldprice": request.form.get('price'),
        "newprice": newprice,
        "start_datetime": start_datetime.strftime('%Y-%m-%d %H:%M'),
        "end_datetime": end_datetime.strftime('%Y-%m-%d %H:%M'),
        "tecnico_id": tecnico_id,
        "timestamp": timestamp,
        "user_id": session['user'],
        "address": {
            "numero": request.form.get('numerocasa'),
            "rua":request.form.get('rua'),
            "bairro": request.form.get('bairro'),
            "complemento": request.form.get('enderecocomplemento'),
            "localizacao": request.form.get('localizacao')
        }
    }

    date_str = request.form.get('dateos')
    date = datetime.strptime(date_str, '%Y-%m-%d')

    year = str(date.year)
    month = f"{date.month:02d}"  # Garantir que o mÃªs tenha dois dÃ­gitos
    day = f"{date.day:02d}"  # Garantir que o dia tenha dois dÃ­gitos

    if newprice != "0.00":

        info_bonus_user = {
            "phone": request.form.get('phone'),
            "service": request.form.get('service'),
            "price": newprice,
            "timestamp": timestamp,
        }

        User_Wallet_Attendant.create_transaction_credito(id_user=session['user'], date=date, info=info_bonus_user)


    
    Attendance.update_status(id=id_attendance, city=city, date=data_formatada, timestamp=timestamp)

    db.child("ordens_servico").child(city).child(year).child(month).child(day).push(nova_os)

    return redirect(url_for('dashboard'))

@app.route('/consulta_agenda', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def consulta_agenda():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('consulta_agenda.html')

@app.route('/view_schedule', methods=['GET'])
@check_roles(['tecnico'])
def view_schedule():
    date_str = request.args.get('date')

    ordens_servico_ordenadas = {}
    costs_day = None

    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return "Formato de data invÃ¡lido."

        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"

        tecnico_id = session['user']
        cities = db.child('users').child(session['user']).child('cities').get().val()
        all_ordens_servico = {}

        for city in cities:
            path = f"ordens_servico/{city}/{year}/{month}/{day}"
            os_agendadas = db.child(path).get().val() or {}
            all_ordens_servico.update(os_agendadas)

        ordens_servico_tecnico = {
            os_id: os
            for os_id, os in all_ordens_servico.items()
            if os.get('tecnico_id') == tecnico_id
        }

        ordens_servico_ordenadas = dict(sorted(
            ordens_servico_tecnico.items(),
            key=lambda item: datetime.strptime(item[1]['start_datetime'], '%Y-%m-%d %H:%M')
        ))

        costs_day = User_Wallet.verify_costs(id=tecnico_id, date=date)

    return render_template('view_schedule.html', ordens_servico=ordens_servico_ordenadas, date=date_str, costs_day=costs_day)

@app.route('/consulta_os_atendente', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def consulta_os_atendente():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']

    # Carregar as cidades vinculadas ao usuÃ¡rio
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    return render_template('consulta_os_atendente.html', cities=cities)

@app.route('/view_schedule_atendente', methods=['GET'])
@check_roles(['user'])
def view_schedule_atendente():
    city = request.args.get('city')
    date_str = request.args.get('date')

    if not city or not date_str:
        return "Cidade ou data nÃ£o fornecida."

    # Verifique se o usuÃ¡rio tem permissÃ£o para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    if city not in user_data.get('cities', []):
        return "VocÃª nÃ£o tem permissÃ£o para acessar registros desta cidade."

    # Converter a data fornecida para ano, mÃªs e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    
    # Obtenha o ID do tÃ©cnico logado
    tecnico_id = session['user']
    
    
    ordens_servico_path = f"ordens_servico/{city}/{year}/{month}/{day}"
    os_agendadas = db.child(ordens_servico_path).get().val() or {}
    
    all_users = db.child("users").get().val() or {}
    tecnicos = {uid: user for uid, user in all_users.items() if
                user['role'] == 'tecnico' and city in user.get('cities', [])}
    
    ordens_servico_ordenadas = dict(sorted(
        os_agendadas.items(),
        key=lambda item: datetime.strptime(item[1]['start_datetime'], '%Y-%m-%d %H:%M')
    ))



    return render_template('view_schedule_atendente.html', ordens_servico=ordens_servico_ordenadas, city=city, date=date_str, tecnicos=tecnicos)

@app.route('/reagendar_os', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def reagendar_os():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']

    city = request.form.get('city')
    old_id = request.form.get("idRecord")
    old_date = request.form.get("osOldDate")
    new_date = request.form.get("dateos")
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    tecnico_id = request.form.get('tecnico')

    # Converte as datas e horas para objetos datetime
    start_datetime = datetime.strptime(f"{new_date} {start_time}", '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(f"{new_date} {end_time}", '%Y-%m-%d %H:%M')

    # Define o fuso horÃ¡rio de SÃ£o Paulo
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    now_in_sao_paulo = datetime.now(sao_paulo_tz)

    # ObtÃ©m o timestamp atual
    timestamp = now_in_sao_paulo.timestamp()

    # Tenta converter a data antiga para objetos ano, mÃªs e dia
    try:
        date = datetime.strptime(old_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obter o registro antigo
    path_old_os = f"ordens_servico/{city}/{year}/{month}/{day}"
    get_os = db.child(path_old_os).child(old_id).get().val() or {}

    if get_os:
        # Converte start_datetime e end_datetime para strings formatadas
        get_os["start_datetime"] = start_datetime.strftime('%Y-%m-%d %H:%M')
        get_os["end_datetime"] = end_datetime.strftime('%Y-%m-%d %H:%M')
        get_os["timestamp"] = timestamp
        get_os["tecnico_id"] = tecnico_id

        # Tenta converter a nova data para ano, mÃªs e dia
        try:
            date = datetime.strptime(new_date, '%Y-%m-%d')
        except ValueError:
            return "Formato de data invÃ¡lido."

        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"

        # Salva os dados no Firebase com o novo ID gerado automaticamente
        db.child("ordens_servico").child(city).child(year).child(month).child(day).push(get_os)

        db.child(path_old_os).child(old_id).remove()
        

    return redirect(url_for('consulta_os_atendente'))

@app.route('/finalizar_os', methods=['POST'])
def finalizar_os():
    # Recebe os dados enviados pelo formulÃ¡rio
    data = request.json
   
    # Inicializa as variÃ¡veis de categorizaÃ§Ã£o
    status_pagamento = None
    detalhes_pagamento = {}
    numero_os = data.get('os_numero')
    os_id = data.get('os_id')
    os_city = data.get('os_city')
    os_date = data.get('os_date')
    os_id_tecnico = data.get('os_id_tecnico')

    os_value_service = convert_monetary_value(data.get('os_value_service'))
    os_type_service = data.get('os_type_serve')
    taxa = convert_monetary_value(data.get('taxa') or "0.00")
    outros_custos_service = convert_monetary_value(data.get('outrosCustosService') or "0.00")
    observacoes_service = data.get('observacaoService') or ""
    
    create_paymment = {}

    '''# Tenta converter a nova data para ano, mÃªs e dia
    try:
            date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
            return "Formato de data invÃ¡lido."

    year = str(date_firebase.year)
    month = f"{date_firebase.month:02d}"
    day = f"{date_firebase.day:02d}"'''

    if os_type_service == 'Retorno' or os_type_service == 'retorno':

        try:

            Wallet.create_paymment_success(data=create_paymment, date=os_date, city=os_city)

            Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment="recebido")

            User_Wallet.create_transaction_success(data=create_paymment, date=os_date, city=os_city, id_tecnico=os_id_tecnico)

        except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400

    else:
        if data.get('statusPaymment') == 'received':
            
            # Filtra os dados e categoriza
            if data.get("method") in ["pix", "dinheiro"]:
                # Pagamentos recebidos
                status_pagamento = "recebido"
                detalhes_pagamento["valor"] = data.get("amount")
                detalhes_pagamento["metodo"] = data.get("method")
                name = session['name']
                method_payment = data.get("method")

                amount = "{:.2f}".format(float(convert_monetary_value(data.get('amount'))) - (float(convert_monetary_value(taxa)) + float(convert_monetary_value(outros_custos_service))))
                amount_financeiro = convert_monetary_value(data.get('amount'))
                
                create_paymment ={
                    'os_id': os_id,
                    'os_date': os_date,
                    'tecnico_id': os_id_tecnico,
                    'method': data.get('method'),
                    'amount': amount,
                    'taxa': taxa,
                    'outros_custos_service': outros_custos_service,
                    'observacoes_service': observacoes_service,
                    'numero_os': numero_os,
                    'valor_bruto': os_value_service,
                }

                try: 

                    id_create_transaction_wallet = Wallet.create_paymment_success(data=create_paymment, date=os_date, city=os_city)
                    
                    Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)

                    id_create_transaction_user = User_Wallet.create_transaction_success(data=create_paymment, date=os_date, city=os_city, id_tecnico=os_id_tecnico)

                    Financeiro.post_transaction_pendente( numero_os=numero_os, id_os=os_id, os_city=os_city, os_date=os_date, date_payment=os_date, metodo_pagamento=method_payment, valor_recebido=amount_financeiro, valor_liquido=amount, taxa=taxa, outros_custos_service=outros_custos_service,observacoes_service=observacoes_service, id_create_transaction_user=id_create_transaction_user, id_create_transaction_wallet=id_create_transaction_wallet)

                    #Financeiro.post_transaction_credito_tecnico(user=session['name'], date=os_date, amount=amount_financeiro, description=f'', method_payment=method_payment, origem=name, destinatario='', id_origem=os_id_tecnico)
                    
                    #if taxa != "0.00":
                        #taxa = "{:.2f}".format(float(taxa), 2)
                        
                        #Financeiro.post_transaction_debito(user=session['name'], date=os_date, amount=taxa, description=f'', category='financeiro', especie=f'Taxa - {method_payment}', origem=name, destinatario='', id_origem=os_id_tecnico)
                            
                except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400

            
            elif data.get("method") == "cartao":
                status_pagamento = "recebido"
                detalhes_pagamento["valor"] = data.get("cardValor")
                detalhes_pagamento["parcelas"] = data.get("installments")

                amount = "{:.2f}".format(float(convert_monetary_value(data.get('cardValor'))) - (float(convert_monetary_value(taxa)) + float(convert_monetary_value(outros_custos_service))))
                amount_financeiro = convert_monetary_value(data.get('cardValor'))
                name = session['name']
                method_payment = data.get("method")

                create_paymment ={
                    'os_id': os_id,
                    'os_date': os_date,
                    'tecnico_id': os_id_tecnico,
                    'method': data.get('method'),
                    'amount': amount,
                    'installments': data.get('installments'),
                    'taxa': taxa,
                    'outros_custos_service': outros_custos_service,
                    'observacoes_service': observacoes_service,
                    'numero_os': numero_os,
                    'valor_bruto': os_value_service,
                }

                try:

                    
                    id_create_transaction_wallet = Wallet.create_paymment_success(data=create_paymment, date=os_date, city=os_city)

                    Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)

                    id_create_transaction_user = User_Wallet.create_transaction_success(data=create_paymment, date=os_date, city=os_city, id_tecnico=os_id_tecnico)

                    Financeiro.post_transaction_pendente( numero_os=numero_os, id_os=os_id, os_city=os_city, os_date=os_date, date_payment=os_date, metodo_pagamento=method_payment, valor_recebido=amount_financeiro, valor_liquido=amount, taxa=taxa, outros_custos_service=outros_custos_service,observacoes_service=observacoes_service, id_create_transaction_user=id_create_transaction_user, id_create_transaction_wallet=id_create_transaction_wallet)

                    
                    #Financeiro.post_transaction_credito_tecnico(user=session['name'], date=os_date, amount=amount_financeiro, description=f'', method_payment=method_payment, origem=name, destinatario='', id_origem=os_id_tecnico)

                    #if taxa != "0.00":
                        #taxa = "{:.2f}".format(float(taxa), 2)

                        #Financeiro.post_transaction_debito(user=session['name'], date=os_date, amount=taxa, description=f'', category='financeiro', especie=f'Taxa - {method_payment}', origem=name, destinatario='', id_origem=os_id_tecnico)

                except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400

        if data.get('statusPaymment') == 'notreceived' or data.get("method") == "boleto":
        
            if data.get("method") == "boleto":
                # Pagamentos a receber
                status_pagamento = "pendente"
                
                create_paymment = {
                    'os_id': os_id,
                    'os_city': os_city,
                    'os_date': os_date,
                    'tecnico_id': os_id_tecnico,
                    'method': data.get('method'),
                    'amount': convert_monetary_value(data.get('boletoValor')),
                    'vencimento': data.get('boletoDate'),
                    'numero_os': numero_os,
                }

                try:
                    Wallet.create_paymment_pendding(data=create_paymment, date=os_date, city=os_city)
                    Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)
                
                except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400
                
            elif data.get("method") in ["pix", "dinheiro"]:
                # Pagamentos recebidos
                status_pagamento = "pendente"
                detalhes_pagamento["valor"] = data.get("amount")
                detalhes_pagamento["metodo"] = data.get("method")

                create_paymment ={
                    'os_id': os_id,
                    'os_date': os_date,
                    'os_city': os_city,
                    'tecnico_id': os_id_tecnico,
                    'method': data.get('method'),
                    'amount': convert_monetary_value(data.get('amount')),
                    'vencimento': os_date,
                    'numero_os': numero_os,
                }

                try: 
                    Wallet.create_paymment_pendding(data=create_paymment, date=os_date, city=os_city)
                    Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)
                    
                
                except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400

            
            elif data.get("method") == "cartao":
                status_pagamento = "pendente"
                detalhes_pagamento["valor"] = data.get("cardValor")
                detalhes_pagamento["parcelas"] = data.get("installments")

                create_paymment ={
                    'os_id': os_id,
                    'os_date': os_date,
                    'os_city': os_city,
                    'tecnico_id': os_id_tecnico,
                    'method': data.get('method'),
                    'amount': convert_monetary_value(data.get('cardValor')),
                    'installments': data.get('installments'),
                    'vencimento': os_date,
                    'numero_os': numero_os,
                }

                try:
                    Wallet.create_paymment_pendding(data=create_paymment, date=os_date, city=os_city)
                    Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)


                except:
                    return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400


@app.route('/listar_pendentes_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def listar_pendentes_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']  # ID do tÃ©cnico logado
    now = datetime.now()
    ano_atual = now.strftime("%Y")
    mes_atual = now.strftime("%m")

    # Receber ano e mÃªs do formulÃ¡rio ou usar os valores padrÃ£o (ano e mÃªs atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # MÃªs atual
    all_pendding_transactions = {}
    # Obter as cidades associadas ao tÃ©cnico
    cities = db.child('users').child(session['user']).child('cities').get().val()

    

    # Buscar ordens de serviÃ§o pendentes para cada cidade
    for city in cities:
        pendding_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_pendding = db.child(pendding_transactions_path).get().val() or {}

        # Agora, em vez de usar `update`, fazemos uma combinaÃ§Ã£o manual para nÃ£o sobrescrever
        for day, day_data in paymments_pendding.items():
            if day not in all_pendding_transactions:
                all_pendding_transactions[day] = day_data
            else:
                # Verifique se 'transactions' e 'pendding' existem antes de atualizar
                if 'transactions' in day_data and 'pendding' in day_data['transactions']:
                    if 'transactions' not in all_pendding_transactions[day]:
                        all_pendding_transactions[day]['transactions'] = {}
                    if 'pendding' not in all_pendding_transactions[day]['transactions']:
                        all_pendding_transactions[day]['transactions']['pendding'] = {}
                    # Mesclar as transaÃ§Ãµes do dia
                    all_pendding_transactions[day]['transactions']['pendding'].update(day_data['transactions']['pendding'])

    pendding_transactions = {}

    # Percorrer os dias e filtrar as transaÃ§Ãµes pendentes do tÃ©cnico logado
    for day, day_data in all_pendding_transactions.items():
        pendding = day_data.get('transactions', {}).get('pendding', {})
        for trans_id, trans_data in pendding.items():
            if trans_data.get('tecnico_id') == tecnico_id:
                pendding_transactions[trans_id] = trans_data

    # Renderizar as transaÃ§Ãµes filtradas
    return render_template('paymments_pendding_tecnico.html', transactions=pendding_transactions, ano=ano, mes=mes)

'''
@app.route('/extrato_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def extrato_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']  # ID do tÃ©cnico logado
    now = datetime.now()
    ano_atual = now.strftime("%Y")
    mes_atual = now.strftime("%m")

    # Receber ano e mÃªs do formulÃ¡rio ou usar os valores padrÃ£o (ano e mÃªs atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # MÃªs atual

    participation = User_Wallet.get_participation(id=tecnico_id)
    participation_empresa = 100 - participation
    
    # Obter as cidades associadas ao tÃ©cnico
    cities = db.child('users').child(session['user']).child('cities').get().val()

    grouped_transactions = {}

    # Buscar ordens de serviÃ§o para cada cidade
    for city in cities:
        success_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_success = db.child(success_transactions_path).get().val() or {}

        # Agrupar as transaÃ§Ãµes por dia
        for day, day_data in paymments_success.items():
            success = day_data.get('transactions', {}).get('success', {})
            if day not in grouped_transactions:
                grouped_transactions[day] = {
                    'transactions': [], 
                    'total_amount': 0.0, 
                    'costs': {'combustivel': 0.0, 'manutencao': 0.0, 'pedagio': 0.0, 'reparo': 0.0, 'outros': 0.0}, 
                    'balance': 0.0,
                    'city':city
                }
            for trans_id, trans_data in success.items():
                if trans_data.get('tecnico_id') == tecnico_id:
                    amount = float(trans_data.get('amount', 0))  # Pega o valor da transaÃ§Ã£o
                    grouped_transactions[day]['transactions'].append({
                        'trans_id': trans_id,
                        'data': trans_data,
                        'city': city
                    })
                    grouped_transactions[day]['total_amount'] += amount  # Soma o valor ao total do dia


    # Obter os custos (combustÃ­vel, manutenÃ§Ã£o, pedÃ¡gio) do mÃªs
    costs_path = f"users/{session['user']}/wallet/costs/{ano}/{mes}"
    month_costs_data = db.child(costs_path).get().val() or {}

    # Somar os custos de todos os dias do mÃªs
    for day, costs_data in month_costs_data.items():
        total_costs = 0.0
        
        # Inicializar variÃ¡veis para custos individuais
        combustivel = 0.0
        manutencao = 0.0
        pedagio = 0.0
        reparo = 0.0
        outros = 0.0
        
        # Percorrer os dados de custo para o dia especÃ­fico
        for cost_id, cost_items in costs_data.items():
            if isinstance(cost_items, dict):
                combustivel = float(cost_items.get('combustivel', '0.0'))
                manutencao = float(cost_items.get('manutencao', '0.0'))
                pedagio = float(cost_items.get('pedagio', '0.0'))
                reparo = float(cost_items.get('reparo', '0.0'))
                outros = float(cost_items.get('outros', '0.0'))
              
                # Somar ao total de custos do dia
                total_costs += combustivel + manutencao + pedagio + reparo + outros

               
        # Se houver transaÃ§Ãµes agrupadas para esse dia, atualizar com os custos


        if day in grouped_transactions:

  
            grouped_transactions[day]['combustivel'] = combustivel
            grouped_transactions[day]['manutencao'] = manutencao
            grouped_transactions[day]['pedagio'] = pedagio
            grouped_transactions[day]['reparo'] = reparo
            grouped_transactions[day]['outros'] = outros
            grouped_transactions[day]['total_costs'] = total_costs
            grouped_transactions[day]['balance'] = grouped_transactions[day]['total_amount'] - total_costs  # Calcula o saldo restante
            grouped_transactions[day]['tecnico'] = (grouped_transactions[day]['balance'] /100) * participation
            grouped_transactions[day]['tecnico_total'] = grouped_transactions[day]['tecnico']
            grouped_transactions[day]['empresa'] = ((grouped_transactions[day]['balance'] /100) * participation_empresa)


    # Renderizar as transaÃ§Ãµes agrupadas por dia, incluindo os custos e o saldo restante
    return render_template('extrato_tecnico.html', grouped_transactions=grouped_transactions, ano=ano, mes=mes)

'''

    


@app.route('/extrato_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def extrato_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']
    now = datetime.now()

    # Receber a data do formulÃ¡rio ou usar o valor padrÃ£o (dia atual)
    if request.method == 'POST':
        data = request.form.get('data', now.strftime("%Y-%m-%d"))
    else:
        data = now.strftime("%Y-%m-%d")  # Data atual como padrÃ£o

    ano, mes, dia = data.split('-')

    date = datetime.strptime(data, '%Y-%m-%d')

    participation = User_Wallet.get_participation(id=tecnico_id, data=date)
    participation_empresa = 100 - participation
    
    cities = db.child('users').child(session['user']).child('cities').get().val()

    grouped_transactions = {}

    # Buscar ordens de serviÃ§o para a data selecionada
    for city in cities:
        success_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_success = db.child(success_transactions_path).get().val() or {}

        # Filtrar transaÃ§Ãµes para o dia especÃ­fico
        if dia in paymments_success:
            day_data = paymments_success[dia]
            success = day_data.get('transactions', {}).get('success', {})
            if dia not in grouped_transactions:
                grouped_transactions[dia] = {
                    'transactions': [], 
                    'total_amount': 0.0, 
                    'costs': {'combustivel': 0.0, 'manutencao': 0.0, 'pedagio': 0.0, 'reparo': 0.0, 'outros': 0.0}, 
                    'balance': 0.0,
                    'city': city
                }
            for trans_id, trans_data in success.items():
                if trans_data.get('tecnico_id') == tecnico_id:
                    amount = float(trans_data.get('amount', 0))
                    grouped_transactions[dia]['transactions'].append({
                        'trans_id': trans_id,
                        'data': trans_data,
                        'city': city
                    })
                    grouped_transactions[dia]['total_amount'] += amount

    # Buscar os custos do dia especÃ­fico
    #costs_path = f"users/{session['user']}/wallet/costs/{ano}/{mes}"
    #month_costs_data = db.child(costs_path).get().val() or {}

    # Garantir que o dia estÃ¡ nos custos recuperados
    #costs_data = month_costs_data.get(dia, {})  # Retorna um dicionÃ¡rio vazio se o dia nÃ£o existir
    
 

    #if costs_data:
        # Acessar diretamente a Ãºnica chave no dicionÃ¡rio
        #daily_costs = list(costs_data.values())[0]  # Acessa o primeiro (e Ãºnico) valor do dicionÃ¡rio

        # Extrair os valores dos custos, assumindo 0.0 se o campo nÃ£o existir
    combustivel = 0.0
    manutencao = 0.0
    pedagio = 0.0
    reparo = 0.0
    outros = 0.0
    total_costs = combustivel + manutencao + pedagio + reparo + outros


        # Atribuir os valores ao dicionÃ¡rio de transaÃ§Ãµes agrupadas
    if dia in grouped_transactions:
            grouped_transactions[dia]['combustivel'] = combustivel
            grouped_transactions[dia]['manutencao'] = manutencao
            grouped_transactions[dia]['pedagio'] = pedagio
            grouped_transactions[dia]['reparo'] = reparo
            grouped_transactions[dia]['outros'] = outros
            grouped_transactions[dia]['total_costs'] = total_costs
            grouped_transactions[dia]['balance'] = grouped_transactions[dia]['total_amount'] - total_costs
            grouped_transactions[dia]['tecnico'] = (grouped_transactions[dia]['balance'] / 100) * participation
            grouped_transactions[dia]['tecnico_total'] = grouped_transactions[dia]['tecnico']
            grouped_transactions[dia]['empresa'] = (grouped_transactions[dia]['balance'] / 100) * participation_empresa
            # Passar a variÃ¡vel 'now' para o template

    print(grouped_transactions)
    return render_template('extrato_tecnico.html', grouped_transactions=grouped_transactions, data=data, now=now)


@app.route('/fechar_dia_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def fechar_dia_tecnico():

    date = request.form.get('date')
    name = session['name']
    user = session['name']
    participation = User_Wallet.get_participation(id=session['user'], data=date)

    '''data = {
    'manutencao': convert_monetary_value(request.form.get('manutencao') if request.form.get('manutencao') != "" else "0.00"),
    'combustivel': convert_monetary_value(request.form.get('combustivel') if request.form.get('combustivel') != "" else "0.00"),
    'pedagio': convert_monetary_value(request.form.get('pedagio') if request.form.get('pedagio') != "" else "0.00"),
    'reparo': convert_monetary_value(request.form.get('reparo') if request.form.get('reparo') != "" else "0.00"),
    'outros': convert_monetary_value(request.form.get('outros') if request.form.get('outros') != "" else "0.00"),
}'''
    data = {
    'manutencao': "0.00",
    'combustivel': "0.00",
    'pedagio': "0.00",
    'reparo': "0.00",
    'outros': "0.00",
}

    
    

    for item in data:
        
        if data[item] != "0.00":
            

            if item == 'manutencao':

                category = 'ManutenÃ§Ã£o'
                especie = 'VeÃ­culo'

            elif item == 'combustivel':
                category = 'Transporte'
                especie = 'CombustÃ­vel'
            
            elif item == 'pedagio':
                category = 'Transporte'
                especie = 'PedÃ¡gio'
            
            elif item == 'reparo':
                category = 'ManutenÃ§Ã£o'
                especie = 'Reparo'

            elif item == 'outros':
                category = 'Outros'
                especie = 'Outros'

            Financeiro.post_transaction_debito(date=date, amount=data[item], category=category, especie=especie, destinatario='', user=user, origem=name, id_origem=session['user'])

    data['porcentagemTecnico'] = participation

    User_Wallet.create_costs(id=session['user'], date=date, data=data)

    

    print('Dados salvos com sucesso!')
    return redirect(url_for('dashboard_tecnico'))

@app.route('/adm_relatorios', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_relatorios():

    return render_template('adm_relatorios.html')


@app.route('/adm_consulta_extrato', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_consulta_extrato():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('adm_consulta_extrato.html')

@app.route('/adm_extrato_tecnico', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_extrato_tecnico():
    date_str = request.args.get('date')

    # Converter a data fornecida para ano, mÃªs e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."
    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obter todos os dados de wallet do Firebase
    wallet_data = db.child("wallet").get().val() or {}

    # DicionÃ¡rio para agrupar transaÃ§Ãµes, somar os amounts e os custos por tÃ©cnico
    tecnico_transactions = defaultdict(lambda: {'transactions': [], 'total_amount': 0.0, 'costs': {'combustivel': 0.0, 'manutencao': 0.0, 'pedagio': 0.0, 'reparo': 0.0, 'outros': 0.0}, 'valor_final': 0.0})

    # Iterar sobre as cidades na estrutura do Firebase
    for city, years in wallet_data.items():
        if year in years:
            months = years[year]
            if month in months:
                days = months[month]
                if day in days:
                    # Obter as transaÃ§Ãµes do dia especÃ­fico
                    transactions = days[day].get("transactions", {}).get("success", {})

                    # Agrupar transaÃ§Ãµes pelo nome do tÃ©cnico e somar os amounts
                    for transaction_id, transaction_info in transactions.items():
                        tecnico_id = transaction_info.get('tecnico_id')
                        if tecnico_id:
                            name_tecnico = User.get_name(tecnico_id)  # Obter o nome do tÃ©cnico
                        
                            # Buscar os custos do tÃ©cnico (apenas uma vez por tÃ©cnico)
                            if 'costs_retrieved' not in tecnico_transactions[name_tecnico]:
                                costs_path = f"users/{tecnico_id}/wallet/costs/{year}/{month}/{day}"
                                day_costs_data = db.child(costs_path).get().val() or {}
                                participation = User_Wallet.get_participation(id=tecnico_id, data=date)
                                participation_empresa = 100 - participation

                                # Somar os custos se eles existirem
                                for cost_id, cost_info in day_costs_data.items():
                                    
                                    tecnico_transactions[name_tecnico]['costs']['combustivel'] += float(cost_info.get('combustivel', 0))
                                    tecnico_transactions[name_tecnico]['costs']['manutencao'] += float(cost_info.get('manutencao', 0))
                                    tecnico_transactions[name_tecnico]['costs']['pedagio'] += float(cost_info.get('pedagio', 0))
                                    tecnico_transactions[name_tecnico]['costs']['reparo'] += float(cost_info.get('reparo', 0))
                                    tecnico_transactions[name_tecnico]['costs']['outros'] += float(cost_info.get('outros', 0))
                                    
                                    
                                # Marcar que os custos foram buscados
                                tecnico_transactions[name_tecnico]['costs_retrieved'] = True
                        
                            # Somar o valor da transaÃ§Ã£o ao total do tÃ©cnico
                            amount = float(transaction_info.get('amount', 0))
                            tecnico_transactions[name_tecnico]['transactions'].append(transaction_info)
                            tecnico_transactions[name_tecnico]['total_amount'] += amount
                        transaction_info['city'] = city

    # Calcular o valor final para cada tÃ©cnico (total_amount - custos)
    for name_tecnico, data in tecnico_transactions.items():
        total_costs = data['costs']['combustivel'] + data['costs']['manutencao'] + data['costs']['pedagio'] + data['costs']['reparo'] + data['costs']['outros']
        data['valor_final'] = data['total_amount'] - total_costs
        data['tecnico'] = (data['valor_final'] /100) * participation
        data['empresa'] = (data['valor_final'] /100) * participation_empresa

    # Renderizar o template com os dados agrupados e a soma total
    return render_template('adm_extrato_tecnico.html', tecnico_transactions=tecnico_transactions, date=date_str, year=year, month=month, day=day)

@app.route('/os/<city>/<year>/<month>/<day>/<id>', methods=['GET', 'POST'])
#@check_roles(['admin', 'tecnico'])
def os(city, year, month, day, id):
    #if 'user' not in session:
    #    return redirect(url_for('login'))
    
    get_os = db.child("ordens_servico").child(city).child(year).child(month).child(day).child(id).get().val()

    print(get_os)
    return render_template('os.html', os=get_os)

@app.route('/users', methods=['GET', 'POST'])
@check_roles(['admin'])
def users():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    users_data = User.get_users()

    users_list = []
    for user_id, user_info in users_data.items():
        name = user_info.get('name')
        email = user_info.get('email')
        role = user_info.get('role')
        users_list.append({'id': user_id, 'name': name, 'email': email, 'role': role})

    return render_template('users.html', users=users_list)

@app.route('/deletar_os', methods=['GET', 'POST'])
@check_roles(['user'])
def deletar_os():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Obtendo os dados do formulÃ¡rio
    city = request.form.get('city')
    old_id = request.form.get("idRecord")
    motivo = request.form.get("deleteOsMotivo")
    date = request.form.get("deletaOsdate")
    tecnico_id = request.form.get('tecnico')

    # Verificando o formato da data
    try:
        date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."
    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtendo dados da OS do Firebase
    data = db.child("ordens_servico").child(city).child(year).child(month).child(day).child(old_id).get().val()

    if not data:
        return "Dados da OS nÃ£o encontrados."

    # Obter a data e hora atual com o fuso horÃ¡rio de SÃ£o Paulo
    fuso_horario_sp = pytz.timezone('America/Sao_Paulo')
    data_atual_sp = datetime.now(fuso_horario_sp)
    date_str = data_atual_sp.strftime('%Y-%m-%d')

    # Verificando o formato da data atual
    try:
        date_canceled = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."
    
    ano = str(date_canceled.year)
    mes = f"{date_canceled.month:02d}"
    dia = f"{date_canceled.day:02d}"

    # Atualizando o dicionÃ¡rio com o motivo do cancelamento
    data['motivo_cancelamento'] = motivo

    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    now_in_sao_paulo = datetime.now(sao_paulo_tz)
    timestamp = now_in_sao_paulo.timestamp()
    
    newprice = data['newprice']

    if newprice != "0.00":

        info_bonus_user = {
            "price": newprice,
            "timestamp": timestamp,
        }

        User_Wallet_Attendant.create_transaction_debito(id_user=data['user_id'], date=date_canceled, info=info_bonus_user)

    # Salvando os dados atualizados em canceled_services no Firebase
    db.child("canceled_services").child(city).child(ano).child(mes).child(dia).push(data)

    db.child("ordens_servico").child(city).child(year).child(month).child(day).child(old_id).remove()

    return redirect(url_for('dashboard'))

@app.route('/adm_lista_paymments_pendentes', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_lista_paymments_pendentes():
    if 'user' not in session:
        return redirect(url_for('login'))

    now = datetime.now()
    ano_atual = now.strftime("%Y")
    mes_atual = now.strftime("%m")

    # Receber ano e mÃªs do formulÃ¡rio ou usar os valores padrÃ£o (ano e mÃªs atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # MÃªs atual

    all_pendding_transactions = []

    cities = Cities.get_cities()

    # Buscar ordens de serviÃ§o pendentes para cada cidade
    for city in cities.values():
        pendding_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_pendding = db.child(pendding_transactions_path).get().val() or {}

        # Iterar sobre cada dia
        for day_data in paymments_pendding.values():
            # Verificar se hÃ¡ transaÃ§Ãµes pendentes no dia
            if 'transactions' in day_data and 'pendding' in day_data['transactions']:
                for transaction_id, transaction_data in day_data['transactions']['pendding'].items():
                    # Adicionar o ID da transaÃ§Ã£o ao dicionÃ¡rio
                    name = User.get_name(id=transaction_data['tecnico_id'])
                    transaction_data['transaction_id'] = transaction_id
                    transaction_data['name_tecnico'] = name
                    all_pendding_transactions.append(transaction_data)

    # Renderizar as transaÃ§Ãµes pendentes
    return render_template('adm_lista_pendentes.html', transactions=all_pendding_transactions, ano=ano, mes=mes)


@app.route('/update_pendding', methods=['POST', 'GET'])
def update_pendding():

    numero_os = request.form.get('numeroos')
    os_id = request.form.get('paymmentIdOs')
    os_city = request.form.get('paymmentCity')
    os_date = request.form.get('osDate')
    transaction_id = request.form.get('transactionId')
    name_tecnico = request.form.get('osnametecnico')
    amount = convert_monetary_value(request.form.get('amountAtualizado'))
    taxa = convert_monetary_value( request.form.get('taxa') or "0.00")
    outros_custos_service = convert_monetary_value( request.form.get('outrosCustosService') or "0.00")
    observacoes_service =  request.form.get('observacaoService') or ""
   
    date_paymment = request.form.get('datePaymment')

    # Tenta converter a nova data para ano, mÃªs e dia
    try:
        date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    year = str(date_firebase.year)
    month = f"{date_firebase.month:02d}"
    day = f"{date_firebase.day:02d}"

    

    paymment_pendding = dict(db.child("wallet").child(os_city).child(year).child(month).child(day).child('transactions').child('pendding').child(transaction_id).get().val())
    
    print(paymment_pendding)

    os_value_service = paymment_pendding['amount']
    method_payment = paymment_pendding['method']
    status_pagamento = "recebido"
    id_tecnico = paymment_pendding['tecnico_id']

    


    amount = "{:.2f}".format(float(convert_monetary_value(amount)) - (float(convert_monetary_value(taxa)) + float(convert_monetary_value(outros_custos_service))))
    amount_financeiro = convert_monetary_value(request.form.get('amountAtualizado'))
    

    paymment_pendding['numero_os'] = numero_os
    paymment_pendding['amount'] = amount
    paymment_pendding['taxa'] = taxa
    paymment_pendding['outros_custos_service'] = outros_custos_service
    paymment_pendding['observacoes_service'] = observacoes_service
    paymment_pendding['valor_bruto'] = os_value_service


    try:
        id_create_transaction_wallet = Wallet.create_paymment_success(data=paymment_pendding, date=date_paymment, city=os_city)
        print('1')
        Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)
        print('2')
        id_create_transaction_user = User_Wallet.create_transaction_success(data=paymment_pendding, date=date_paymment, city=os_city, id_tecnico=id_tecnico)
        print('3')
        
        Financeiro.post_transaction_pendente( numero_os=numero_os, id_os=os_id, os_city=os_city, os_date=os_date, date_payment=date_paymment, metodo_pagamento=method_payment, valor_recebido=amount_financeiro, valor_liquido=amount, taxa=taxa, outros_custos_service=outros_custos_service, observacoes_service=observacoes_service,  id_create_transaction_user=id_create_transaction_user, id_create_transaction_wallet=id_create_transaction_wallet)
        print('4')
        db.child("wallet").child(os_city).child(year).child(month).child(day).child('transactions').child('pendding').child(transaction_id).remove()
        #Financeiro.post_transaction_credito_tecnico(user=session['name'], date=os_date, amount=os_value_service, description=f'', method_payment=method_payment, origem=name_tecnico, id_origem=id_tecnico)

        #if os_value_service != amount:
            #taxa = "{:.2f}".format(round(float(os_value_service) - float(amount), 2))

            #Financeiro.post_transaction_debito(user=session['name'], date=os_date, amount=taxa, description=f'', category='financeiro', especie=f'Taxa - {method_payment}', origem=name_tecnico, id_origem=id_tecnico)

    except:
        return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400
    return redirect(url_for('adm_lista_paymments_pendentes'))


@app.route('/update_pendding_tecnico', methods=['POST', 'GET'])
def update_pendding_tecnico():

    numero_os = request.form.get('numeroos')
    os_id = request.form.get('paymmentIdOs')
    os_city = request.form.get('paymmentCity')
    os_date = request.form.get('osDate')
    transaction_id = request.form.get('transactionId')
    name_tecnico = request.form.get('osnametecnico')
    amount = convert_monetary_value(request.form.get('amountAtualizado'))
    taxa = convert_monetary_value( request.form.get('taxa') or "0.00")
    outros_custos_service = convert_monetary_value( request.form.get('outrosCustosService') or "0.00")
    observacoes_service =  request.form.get('observacaoService') or ""
   
    date_paymment = request.form.get('datePaymment')

    # Tenta converter a nova data para ano, mÃªs e dia
    try:
        date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data invÃ¡lido."

    year = str(date_firebase.year)
    month = f"{date_firebase.month:02d}"
    day = f"{date_firebase.day:02d}"

    

    paymment_pendding = dict(db.child("wallet").child(os_city).child(year).child(month).child(day).child('transactions').child('pendding').child(transaction_id).get().val())
    
    os_value_service = paymment_pendding['amount']
    method_payment = paymment_pendding['method']
    status_pagamento = "recebido"
    id_tecnico = paymment_pendding['tecnico_id']

    


    amount = "{:.2f}".format(float(convert_monetary_value(amount)) - (float(convert_monetary_value(taxa)) + float(convert_monetary_value(outros_custos_service))))
    amount_financeiro = convert_monetary_value(request.form.get('amountAtualizado'))
    

    paymment_pendding['numero_os'] = numero_os
    paymment_pendding['amount'] = amount
    paymment_pendding['taxa'] = taxa
    paymment_pendding['outros_custos_service'] = outros_custos_service
    paymment_pendding['observacoes_service'] = observacoes_service
    paymment_pendding['valor_bruto'] = os_value_service


    try:
       
        id_create_transaction_wallet = Wallet.create_paymment_success(data=paymment_pendding, date=date_paymment, city=os_city)

        Wallet.update_status_os(id=os_id, city=os_city, date=os_date, status_paymment=status_pagamento)

        id_create_transaction_user = User_Wallet.create_transaction_success(data=paymment_pendding, date=date_paymment, city=os_city, id_tecnico=id_tecnico)
        
        Financeiro.post_transaction_pendente( numero_os=numero_os, id_os=os_id, os_city=os_city, os_date=os_date, date_payment=date_paymment, metodo_pagamento=method_payment, valor_recebido=amount_financeiro, valor_liquido=amount, taxa=taxa, outros_custos_service=outros_custos_service, observacoes_service=observacoes_service,  id_create_transaction_user=id_create_transaction_user, id_create_transaction_wallet=id_create_transaction_wallet)
        
        db.child("wallet").child(os_city).child(year).child(month).child(day).child('transactions').child('pendding').child(transaction_id).remove()

    except:
        return jsonify({'status': 'conflict', 'message': 'Erro.'}), 400
    return redirect(url_for('listar_pendentes_tecnico'))


@app.route('/adm_lista_os', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_lista_os():
    if request.method == 'POST':
        selected_date = request.form.get('selected_date')

        if selected_date:
            year, month, day = selected_date.split('-')

            attendance_data = db.child("ordens_servico").get().val() or {}

            # DicionÃ¡rio para agrupar atendimentos por user_id
            grouped_records = defaultdict(list)

            for city, years in attendance_data.items():
                if year in years:
                    months = years[year]
                    if month in months:
                        days = months[month]
                        if day in days:
                            attendances = days[day]
                            for attendance_id, attendance_info in attendances.items():
                                
                                user_id = attendance_info.get('city')
                                
                                if user_id:
                                    

                                    record = {
                                        "id": attendance_id,
                                        "city": city,
                                        "date": f"{day}/{month}/{year}",
                                        **attendance_info
                                    }
                                    
                                    # Agrupa pelo nome do usuÃ¡rio
                                    grouped_records[user_id].append(record)
                                else:
                                    # Se user_id nÃ£o estiver presente, continue ou log um erro
                                    print(f"User ID ausente para o atendimento {attendance_id}")

            return render_template('adm_lista_os.html', grouped_records=grouped_records, selected_date=selected_date)
    else:
        return render_template('adm_lista_os.html', grouped_records={}, selected_date=None)


@app.route('/relatorio', methods=['GET', 'POST'])
def relatorio():
   
    return render_template('relatorio.html')

def _montar_info_tecnico():
    """Busca os dados do tÃ©cnico logado no Firebase para o relatÃ³rio."""
    tecnico_id = session['user']
    tecnico_data = db.child('users').child(tecnico_id).get().val() or {}

    return {
        "nome_relatorio": tecnico_data.get("nome_relatorio", ""),
        "cpf_cnpj": tecnico_data.get("cpf_cnpj", ""),
        "assinatura": tecnico_data.get("assinatura", None)  # caso exista imagem salva
    }


@app.route('/relatorio_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def relatorio_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Rota com assinatura digital avanÃ§ada (componente criptogrÃ¡fico)
    return render_template(
        'relatorio_tecnico.html',
        tecnico=_montar_info_tecnico(),
        signature_mode='avancada',
    )


@app.route('/relatorio_tecnico_classico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def relatorio_tecnico_classico():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Rota com o modelo de assinatura anterior (assinatura cursiva gerada)
    return render_template(
        'relatorio_tecnico.html',
        tecnico=_montar_info_tecnico(),
        signature_mode='classica',
    )


def _listar_tecnicos():
    """Retorna {uid: dados} de todos os usuÃ¡rios com papel 'tecnico'."""
    all_users = db.child("users").get().val() or {}
    return {
        uid: user
        for uid, user in all_users.items()
        if isinstance(user, dict) and user.get('role') == 'tecnico'
    }


@app.route('/relatorio_atendente', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def relatorio_atendente():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Atendente monta o relatÃ³rio e atribui a um tÃ©cnico para assinar
    return render_template(
        'relatorio_tecnico.html',
        tecnico={},
        tecnicos=_listar_tecnicos(),
        signature_mode='atribuir',
    )

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
   
    
    return render_template('orcamento.html')

@app.route('/attendance_desempenho', methods=['GET', 'POST'])
def attendance_desempenho():
    id_atendente = session.get('user')  # ID do atendente logado
    if not id_atendente:
        return redirect('/login')  # Redireciona se nÃ£o estiver logado

    # Lista de meses para o select
    meses = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "MarÃ§o"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]

    selected_month = None
    year = datetime.now(pytz.timezone('America/Sao_Paulo')).year  # Ano atual
    daily_summary = {}
    total_agendados = 0
    total_aguardando = 0
    total_atendimentos = 0

    if request.method == 'POST':
        selected_month = request.form.get('selected_month')

    if selected_month:
        # ObtÃ©m os dados de atendimentos do Firebase
        attendance_data = db.child("attendance_records").get().val() or {}

        # Filtra os registros para o atendente logado e o mÃªs selecionado
        for city, years in attendance_data.items():
            if str(year) in years:
                months = years[str(year)]
                if selected_month in months:
                    days = months[selected_month]
                    for day, attendances in days.items():
                        if day not in daily_summary:
                            daily_summary[day] = {"agendados": 0, "aguardando": 0, "total": 0}

                        for attendance_id, attendance_info in attendances.items():
                            user_id = attendance_info.get('user_id')
                            if user_id == id_atendente:  # Apenas registros do atendente logado
                                status = attendance_info.get('status')
                                if status == "Agendado":
                                    daily_summary[day]["agendados"] += 1
                                elif status == "Aguardando":
                                    daily_summary[day]["aguardando"] += 1
                                daily_summary[day]["total"] += 1

    # Atualiza os totais mensais fora do loop diÃ¡rio
    for day_summary in daily_summary.values():
        total_agendados += day_summary["agendados"]
        total_aguardando += day_summary["aguardando"]
        total_atendimentos += day_summary["total"]

    # Calcula as porcentagens
    percent_agendados = (
        round((total_agendados / total_atendimentos) * 100 if total_atendimentos else 0, 2)
    )
    percent_aguardando = (
        round((total_aguardando / total_atendimentos) * 100 if total_atendimentos else 0, 2)
    )

    # Converte o resumo diÃ¡rio para uma lista ordenada por dia
    ordered_daily_summary = [
        {"day": f"{day}/{selected_month}/{year}", **summary}
        for day, summary in sorted(daily_summary.items())
    ]

    # ObtÃ©m o nome do atendente logado
    user_name = User.get_name(id_atendente)

    return render_template(
        'attendance_desempenho.html',
        meses=meses,
        selected_month=selected_month,
        daily_summary=ordered_daily_summary,
        total_agendados=total_agendados,
        total_aguardando=total_aguardando,
        total_atendimentos=total_atendimentos,
        percent_agendados=percent_agendados,
        percent_aguardando=percent_aguardando,
        user_name=user_name
    )


@app.route('/bonus_attendant', methods=['GET', 'POST'])
@check_roles(['user'])
def bonus_attendant():
    id_user = session.get('user')
    if not id_user:
        return redirect('/login')  # Redireciona para o login se nÃ£o estiver logado

    # Lista de anos e meses para os selects
    current_year = datetime.now().year
    years = [current_year - i for i in range(5)]  # Ãšltimos 5 anos
    months = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "MarÃ§o"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]

    selected_year = None
    selected_month = None
    transactions = []
    total_balance = 0.0  # Saldo total

    if request.method == 'POST':
        selected_year = request.form.get('selected_year')
        selected_month = request.form.get('selected_month')

        if selected_year and selected_month:
            # Obtem dados do Firebase
            data = db.child('users').child(id_user).child('wallet').child('credit_for_servide').child(selected_year).child(selected_month).get().val()
            if data:
                # Converte os dados em uma lista para exibiÃ§Ã£o e ajusta a data
                for key, value in data.items():
                    timestamp = value.get('timestamp')
                    if timestamp:
                        date = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')
                        value['date'] = date

                    # Atualiza o saldo com base no tipo
                    transaction_value = float(value.get('value', 0))
                    if value.get('type') == 'c':
                        total_balance += transaction_value
                    elif value.get('type') == 'd':
                        total_balance -= transaction_value

                    transactions.append({"id": key, **value})


    total_balance = round(total_balance, 2)
    return render_template(
        'bonus_attendant.html',
        years=years,
        months=months,
        selected_year=selected_year,
        selected_month=selected_month,
        transactions=transactions,
        total_balance=total_balance # Passa o saldo formatado com 2 casas decimais
    )

@app.route("/bonus_attendant_delete", methods=["POST"])
def apagar_transacao():

    id_user = session.get('user')
    transaction_id = request.form.get("transaction_id")
    selected_month = request.form.get("selected_month")
    selected_year = request.form.get("selected_year")
    db.child("users").child(id_user).child("wallet/credit_for_servide").child(selected_year).child(selected_month).child(transaction_id).remove()
    
    # Redireciona de volta com filtros aplicados, por exemplo
    return redirect(url_for("bonus_attendant", selected_month=selected_month, selected_year=selected_year))



@app.route('/relatorio_cidade', methods=['GET', 'POST'])
@check_roles(['admin'])
def relatorio_cidade():
    id_user = session.get('user')
    if not id_user:
        return redirect('/login')  # Redireciona para o login se nÃ£o estiver logado
    
    current_year = datetime.now().year
    years = [current_year - i for i in range(5)]  # Ãšltimos 5 anos
    months = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "MarÃ§o"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]
    
    cities = db.child('cities').get().val()
    cities = list(cities.values())

    
    return render_template('relatorio_cidade.html', cities=cities,  years=years, months=months)

@app.route('/get_city_data', methods=['GET'])
@check_roles(['admin'])
def get_city_data():
    city = request.args.get('city')
    year = request.args.get('year')
    month = request.args.get('month')

    if not city or not year or not month:
        return jsonify({"error": "Invalid parameters"}), 400

    try:
        data = db.child("attendance_records").child(city).child(year).child(month).get().val()
        data_schedule = db.child("ordens_servico").child(city).child(year).child(month).get().val()

        total = 0
        total_agendado = 0
        total_retorno = 0
        service_counts = {}
        service_counts_agendado = {}
        channel_counts = {}
        channel_counts_agendado = {}
        value_total_channel = {}
        service_value_totals_agendado = {}
        service_value_averages_agendado = {}
        service_schedule_list = []

        # Processa dados de atendimento (dados gerais)
        if data:
            for day, items in data.items():
                total += len(items)
                for item in items.values():
                    service = item.get("service")
                    if service:
                        service_counts[service] = service_counts.get(service, 0) + 1

                    channel = item.get("canal")
                    if channel:
                        channel_counts[channel] = channel_counts.get(channel, 0) + 1

        # Processa dados de agendamento (ordens de serviÃ§o)
        if data_schedule:
            for day, items in data_schedule.items():
                for item_id, item in items.items():
                    total_agendado += 1

                    service = item.get("service")
                    price = float(item.get("newprice", 0))
                    date = item.get("date", day)
                    phone = item.get("phone", "")
                    obs = item.get("obs", "")

                    if service:
                        # Contagem por serviÃ§o
                        service_counts_agendado[service] = service_counts_agendado.get(service, 0) + 1

                        # Soma de valores por serviÃ§o
                        service_value_totals_agendado[service] = service_value_totals_agendado.get(service, 0) + price

                        # Lista detalhada de agendamentos
                        service_schedule_list.append({
                            "service": service,
                            "price": price,
                            "date": date,
                            "phone": phone,
                            "obs": obs
                        })

                        if service == "Retorno":
                            total_retorno += 1

        # CÃ¡lculo do valor mÃ©dio por serviÃ§o
        for service, total_value in service_value_totals_agendado.items():
            count = service_counts_agendado.get(service, 0)
            service_value_averages_agendado[service] = round(total_value / count, 2) if count else 0

        # CÃ¡lculo de porcentagens
        porcentagem_agendado = round((total_agendado / total) * 100 if total else 0, 2)

        service_percentages = {
            service: round((count / total) * 100, 2) for service, count in service_counts.items()
        }

        service_percentages_agendado = {
            service: round((count / total_agendado) * 100, 2)
            for service, count in service_counts_agendado.items()
        }

        channel_percentages = {
            channel: round((count / total) * 100, 2) for channel, count in channel_counts.items()
        }

        return jsonify({
            "total": total,
            "total_agendado": total_agendado,
            "porcentagem_agendado": porcentagem_agendado,
            "service_counts": service_counts,
            "service_percentages": service_percentages,
            "service_counts_agendado": service_counts_agendado,
            "service_percentages_agendado": service_percentages_agendado,
            "channel_counts": channel_counts,
            "channel_percentages": channel_percentages,
            "channel_counts_agendado": channel_counts_agendado,
            "total_retorno": total_retorno,
            "value_total_channel": value_total_channel,
            "service_value_totals_agendado": service_value_totals_agendado,
            "service_value_averages_agendado": service_value_averages_agendado,  # <- NOVO
            "service_schedule_list": service_schedule_list  # <- DETALHES
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/adm_schedule', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_schedule():


    return render_template('adm_schedule.html')

@app.route('/get_technician_schedules', methods=['GET'])
@check_roles(['admin'])
def get_technician_schedules():
    date_str = request.args.get('date')

    # ValidaÃ§Ã£o da data
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Formato de data invÃ¡lido."}), 400

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtenha todos os tÃ©cnicos registrados no sistema
    users = db.child("users").get().val()
    user_role = 'tecnico'
    technicians = {user_id: user for user_id, user in users.items() if user.get('role') == user_role}

    # Obtenha a lista de cidades
    cities = db.child('cities').get().val()
    if not cities:
        return jsonify({"error": "Nenhuma cidade encontrada."}), 404

    cities = list(cities.values())
    technician_schedules = {tech_id: [] for tech_id in technicians.keys()}

    try:
        for city in cities:
            # Buscar agendamentos na cidade para a data especÃ­fica
            data_schedule = db.child("ordens_servico").child(city).child(year).child(month).child(day).get().val()
            if data_schedule:
                for order_id, order_data in data_schedule.items():
                    technician_id = order_data.get('tecnico_id')
                    
                    # Verifica se o tÃ©cnico existe e acumula os dados
                    if technician_id in technician_schedules:
                        order_data['os_id'] = order_id
                        order_data['data'] = date_str
                        technician_schedules[technician_id].append(order_data)
                    else:
                        print(f"ID do tÃ©cnico {technician_id} nÃ£o encontrado em technicians.")
        
        # Substituir IDs pelo nome e retornar apenas tÃ©cnicos com agendamentos
        formatted_schedules = {}
        for tech_id, schedules in technician_schedules.items():
            if schedules:  # Apenas incluir tÃ©cnicos com agendamentos
                formatted_schedules[technicians[tech_id]['name']] = schedules
        
        return jsonify(formatted_schedules), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/orcamento_client', methods=['GET', 'POST'])
def orcamento_client():
   
    return render_template('orcamento_client.html')

@app.route('/orcamento_client_reparo', methods=['GET', 'POST'])
def orcamento_client_reparo():
   
    return render_template('orcamento_client_reparo.html')

@app.route('/adm_painel_tecnicos', methods=['GET', 'POST'])
def adm_painel_tecnicos():
    if 'user' not in session:
        return redirect(url_for('login'))

    users_data = User.get_users()

    users_list = []
    for user_id, user_info in users_data.items():
        if user_info.get('role') == 'tecnico':
            name = user_info.get('name')
            email = user_info.get('email')
            role = user_info.get('role')
            users_list.append({'id': user_id, 'name': name, 'email': email, 'role': role})

    return render_template('adm_painel_tecnicos.html',users=users_list)


@app.route('/perfil/<id>', methods=['GET', 'POST'])
def perfil(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    data_user = db.child("users").child(id).get().val()

    cities = db.child("cities").get().val() or {}

    return render_template('perfil.html', data_user=data_user, id_user=id, cities=cities)

@app.route('/user_remove_city', methods=['POST'])
def user_remove_city():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    index = data.get('index')
    city_name = data.get('city')

    if index is None or not city_name:
        return jsonify({'success': False, 'error': 'Dados invÃ¡lidos'}), 400

    user_id = data.get('id')

    try:
        cities = db.child("users").child(user_id).child('cities').get().val()

        if not cities or not isinstance(cities, list):
            return jsonify({'success': False, 'error': 'Lista de cidades nÃ£o encontrada ou invÃ¡lida'}), 404

        if 0 <= index < len(cities) and cities[index] == city_name:
            cities.pop(index)
            db.child("users").child(user_id).update({"cities": cities})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Cidade nÃ£o encontrada ou nÃ£o corresponde ao Ã­ndice'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user_add_city', methods=['POST'])
def user_add_city():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    city = data.get('city')
    user_id = data.get('id')

    if not city:
        return jsonify({'success': False, 'error': 'Cidade nÃ£o fornecida'}), 400
    if not user_id:
        return jsonify({'success': False, 'error': 'ID do usuÃ¡rio nÃ£o fornecido'}), 400

    try:
        cities = db.child("users").child(user_id).child('cities').get().val()

        if not cities:
            cities = []

        if city in cities:
            return jsonify({'success': False, 'error': 'Cidade jÃ¡ adicionada'}), 400

        cities.append(city)
        db.child("users").child(user_id).update({"cities": cities})

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/user_update_percentage', methods=['POST'])
def user_update_percentage():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    percentage = data.get('percentage')

    if not user_id or percentage is None:
        return jsonify({'success': False, 'error': 'Dados invÃ¡lidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"porcentagem": percentage})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user_update_tipo', methods=['POST'])
def user_update_tipo():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    role = data.get('role')

    if not user_id or role is None:
        return jsonify({'success': False, 'error': 'Dados invÃ¡lidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"role": role})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/user_update_cpf_cnpj', methods=['POST'])
def user_update_cpf_cnpj():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    cpf_cnpj = data.get('cpfcnpj')

    if not user_id or cpf_cnpj is None:
        return jsonify({'success': False, 'error': 'Dados invÃ¡lidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"cpf_cnpj": cpf_cnpj})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/user_update_nome_relatorio', methods=['POST'])
def user_update_nome_relatorio():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'UsuÃ¡rio nÃ£o autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    nome_relatorio = data.get('nome_relatorio')

    if not user_id or nome_relatorio is None:
        return jsonify({'success': False, 'error': 'Dados invÃ¡lidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"nome_relatorio": nome_relatorio})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/orcamentos', methods=['GET', 'POST'])
def orcamentos():
   
    return render_template('orcamentos.html')

'''@app.template_filter("datetimeformat")
def datetimeformat(value):
    if not value:
        return ""  # ou "Sem data"
    try:
        return datetime.fromtimestamp(int(value)).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(value)  # fallback


@app.route("/financeiro/pendentes")
def listar_pendentes():
    
    pendentes = {}
    data = db.child("financeiro").child("transactions_pendentes").get().val() or {}

    for ano, meses in data.items():
        for mes, dias in meses.items():
            for dia, transacoes in dias.items():
                for pendente_id, pendente in transacoes.items():
                    pendentes[pendente_id] = {
                        **pendente,
                        "ano": ano,
                        "mes": mes,
                        "dia": dia,
                        "id": pendente_id
                    }

    return render_template("pendentes.html", pendentes=pendentes) '''


@app.route("/financeiro/confirmar/<pendente_id>")
def confirmar_transacao(pendente_id):
    pendente = db.child("financeiro").child("pendentes").child(pendente_id).get().val()

    if pendente:
        # Converte timestamp para data
        #date = datetime.datetime.fromtimestamp(pendente['timestamp'])
        date = datetime.fromtimestamp(pendente['timestamp'])
        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"

        # Move para transactions
        db.child("financeiro").child("transactions").child(year).child(month).child(day).child("transactions").push(pendente)

        # Remove de pendentes
        db.child("financeiro").child("pendentes").child(pendente_id).remove()

    return redirect(url_for('listar_pendentes'))

@app.route("/cancel_transaction_pendding", methods=["POST", "GET"])
def cancel_transaction_pendding():
    data = request.get_json()
    data_mes = data.get("dataMes")
    data_ano = data.get("dataAno")
    id_transaction = data.get("idTransaction")
    date_os = data.get("dateOs")
    id_os = data.get("idOs")
    city = data.get("city")
    print(data)

    try:
        date = datetime.strptime(date_os, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Formato de data invÃ¡lido."}), 400

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    try:
        print(data)
        db.child("ordens_servico").child(city).child(year).child(month).child(day).child(id_os).child("status_paymment").remove()

        db.child("wallet").child(city).child(year).child(month).child(day).child('transactions').child('pendding').child(id_transaction).remove()
       
    except Exception as e:
        return jsonify({'status': 'conflict', 'message': 'Erro ao cancelar a transaÃ§Ã£o.'}), 400

    return redirect(url_for('listar_pendentes'))


@app.route('/data_analysis', methods=['GET', 'POST'])
def data_analysis():
   
    return render_template('data_analysis.html')

@app.route("/get_cidades")
def get_cidades():
    # pega os dados no firebase
    cidades = db.child("uf").get().val() or {}
    # retorna como JSON
    return jsonify(cidades)

@app.route("/buscar_dados", methods=["POST"])
def buscar_dados():
    dados = request.get_json()
    cidades = dados.get("cidades", [])
    data_inicio = dados.get("data_inicio")
    data_fim = dados.get("data_fim")

    if not cidades or not data_inicio or not data_fim:
        return jsonify({"erro": "ParÃ¢metros incompletos"}), 400

    # ðŸ”¹ Converte as datas em objetos datetime
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")

    resultados = {}

    # ðŸ”¹ Loop sobre as datas
    dia_atual = inicio
    while dia_atual <= fim:
        ano = str(dia_atual.year)
        mes = f"{dia_atual.month:02d}"
        dia = f"{dia_atual.day:02d}"

        for cidade in cidades:
            caminho = f"ordens_servico/{cidade}/{ano}/{mes}/{dia}"
            os_dia = db.child(caminho).get().val()

            if os_dia:
                if cidade not in resultados:
                    resultados[cidade] = {}
                resultados[cidade][f"{dia}/{mes}/{ano}"] = os_dia

        dia_atual += timedelta(days=1)

    return jsonify(resultados)


@app.route('/comissoes', methods=['GET', 'POST'])
@check_roles(['admin'])
def comissoes():
    if 'user' not in session:
        return redirect(url_for('login'))
    

    return render_template('comissoes.html')


@app.route("/buscar_ordens", methods=["POST"])
def buscar_ordens():
    data = request.get_json()
    ano = str(data.get("ano"))
    mes = f"{int(data.get('mes')):02d}"

    ordens = []
    tecnicos_cache = {} 

    try:
        # Buscar em todas as cidades (ativas)
        cidades_ativas = db.child("ordens_servico").get()
        if cidades_ativas.each():
            for cidade in cidades_ativas.each():
                cidade_nome = cidade.key()
                dados_mes = db.child("ordens_servico").child(cidade_nome).child(ano).child(mes).get()
                if dados_mes.each():
                    for dia in dados_mes.each():
                        for chave, item in dia.val().items():
                            item["status"] = item.get("status_paymment", "aguardando")
                            item["cidade"] = cidade_nome
                            item["id_os"] = chave
                            
                            tecnico_id = item.get("user_id")
                            if tecnico_id:
                                # Se ainda nÃ£o estÃ¡ no cache, busca no servidor
                                if tecnico_id not in tecnicos_cache:
                                    tecnico_data = db.child("users").child(tecnico_id).child("name").get().val()
                                    tecnicos_cache[tecnico_id] = tecnico_data
                                # adiciona o nome do tÃ©cnico ao item
                                item["tecnico_nome"] = tecnicos_cache[tecnico_id]

                            ordens.append(item)


        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

    print(ordens)
    return jsonify({"success": True, "ordens": ordens})

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():

    # Receber PDF
    file = request.files.get("pdf")
    if not file or file.filename == "":
        return jsonify({"status": "error", "message": "PDF não recebido"}), 400

    pdf_file = request.files["pdf"]

    # Receber dados do cliente
    cliente = {
        "nome": request.form.get("nome"),
        "cpf": request.form.get("cpf"),
    }

    file.stream.seek(0)

    # Identificar autor (quem enviou) e seu papel
    autor_id = session.get("user")
    autor_role = None
    if autor_id:
        autor_data = db.child("users").child(autor_id).get().val() or {}
        autor_role = autor_data.get("role")

    # TÃ©cnico responsÃ¡vel: atribuÃ­do (fluxo do atendente) ou o prÃ³prio tÃ©cnico logado
    tecnico_user_id = (request.form.get("tecnico_user_id") or "").strip() or None
    if tecnico_user_id:
        tecnico_data = db.child("users").child(tecnico_user_id).get().val() or {}
        if tecnico_data.get("role") != "tecnico":
            return jsonify({"status": "error", "message": "Técnico atribuído inválido"}), 400
        tecnico_nome = tecnico_data.get("nome_relatorio") or tecnico_data.get("name")
    else:
        tecnico_user_id = autor_id
        tecnico_nome = session.get("name")

    relatorio_data = {
        "pdf_url": None,
        "filename": f"relatorios/{int(time.time())}.pdf",
        "tecnico": tecnico_nome,
        "tecnico_user_id": tecnico_user_id,
        "cliente": cliente,
        "document_type": request.form.get("document_type") or "Relatório Técnico",
        "timestamp": int(time.time()),
        "document_hash": AdvancedSignatureComponent.hash_bytes(file.read()),
        "signature_status": "pending" if tecnico_user_id else "unsigned",
        "created_by": autor_id,
        "created_by_role": autor_role,
        "created_by_name": session.get("name"),
    }

    file.stream.seek(0)

    storage.child(relatorio_data["filename"]).put(pdf_file)
    relatorio_data["pdf_url"] = storage.child(relatorio_data["filename"]).get_url(None)

    # Salvar no Realtime Database
    relatorio_id = db.child("relatorios").push(relatorio_data)

    return jsonify(
        {
            "status": "ok",
            "url": relatorio_data["pdf_url"],
            "filename": relatorio_data["filename"],
            "relatorio_id": relatorio_id.get("name") if isinstance(relatorio_id, dict) else None,
            "document_hash": relatorio_data["document_hash"],
        }
    )


@app.route("/relatorios/<report_id>/pdf_original", methods=["GET"])
@check_roles(['tecnico', 'admin'])
def relatorio_pdf_original(report_id):
    """Proxy same-origin para o PDF original do Storage (evita CORS no carimbo)."""
    report = db.child("relatorios").child(report_id).get().val()
    if not report:
        return jsonify({"status": "error", "message": "Relatório não encontrado"}), 404

    if session.get("role") != "admin" and report.get("tecnico_user_id") != session.get("user"):
        return jsonify({"status": "error", "message": "Relatório não pertence a você"}), 403

    pdf_url = report.get("pdf_url") or report.get("url")
    if not pdf_url:
        return jsonify({"status": "error", "message": "PDF não disponível"}), 404

    try:
        upstream = requests.get(pdf_url, timeout=30)
        upstream.raise_for_status()
    except requests.RequestException as exc:
        return jsonify({"status": "error", "message": f"Falha ao obter PDF: {exc}"}), 502

    return Response(upstream.content, mimetype="application/pdf")


@app.route("/upload_signed_pdf", methods=["POST"])
@check_roles(['tecnico'])
def upload_signed_pdf():
    """Recebe o PDF jÃ¡ carimbado pelo tÃ©cnico e o publica como versÃ£o assinada."""
    report_id = (request.form.get("report_id") or "").strip()
    file = request.files.get("pdf")
    if not report_id or not file or file.filename == "":
        return jsonify({"status": "error", "message": "Dados incompletos"}), 400

    report = db.child("relatorios").child(report_id).get().val()
    if not report:
        return jsonify({"status": "error", "message": "Relatório não encontrado"}), 404

    if report.get("tecnico_user_id") != session.get("user"):
        return jsonify({"status": "error", "message": "Relatório não pertence a você"}), 403

    filename = f"relatorios/assinados/{report_id}.pdf"
    storage.child(filename).put(file)
    signed_url = storage.child(filename).get_url(None)

    db.child("relatorios").child(report_id).update({
        "signed_pdf_url": signed_url,
        "signed_pdf_filename": filename,
    })

    return jsonify({"status": "ok", "signed_pdf_url": signed_url})


@app.route('/relatorios_pendentes')
@check_roles(['tecnico'])
def relatorios_pendentes():
    uid = session.get('user')
    relatorios = db.child("relatorios").get().val() or {}

    lista = []
    for key, item in relatorios.items():
        if not isinstance(item, dict):
            continue
        if item.get("tecnico_user_id") == uid and item.get("signature_status") == "pending":
            registro = dict(item)
            registro["id"] = key
            lista.append(registro)

    lista.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return render_template("relatorios_pendentes.html", relatorios=lista)


@app.route('/relatorios_atribuidos')
@check_roles(['user', 'tecnico', 'admin'])
def relatorios_atribuidos():
    uid = session.get('user')
    role = session.get('role')
    relatorios = db.child("relatorios").get().val() or {}

    lista = []
    for key, item in relatorios.items():
        if not isinstance(item, dict):
            continue
        incluir = (
            role == 'admin'
            or (role == 'tecnico' and item.get("tecnico_user_id") == uid)
            or (role == 'user' and item.get("created_by") == uid)
        )
        if incluir:
            registro = dict(item)
            registro["id"] = key
            lista.append(registro)

    lista.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return render_template("relatorios_atribuidos.html", relatorios=lista, role=role)


@app.template_filter('datetime')
def datetime_filter(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

@app.route('/relatorios_lista_pdf')
def relatorios_lista_pdf():
    relatorios = db.child("relatorios").get().val()

    lista = []
    if relatorios:
        for key, item in relatorios.items():

            # Garante que todos os campos existam
            cliente = item.get("cliente", {})
            tecnico = item.get("tecnico", "NÃ£o informado")
            pdf_url = item.get("pdf_url") or item.get("url")  # compatÃ­vel com versÃµes antigas
            timestamp = item.get("timestamp", 0)

            lista.append({
                "id": key,
                "pdf_url": pdf_url,
                "tecnico": tecnico,
                "timestamp": timestamp,
                "cliente": {
                    "nome": cliente.get("nome", "NÃ£o informado"),
                    "cpf": cliente.get("cpf", "NÃ£o informado"),
                }
            })

    # Ordena corretamente do mais recente para o mais antigo
    lista = sorted(lista, key=lambda x: x["timestamp"], reverse=True)

    return render_template("relatorios_lista_pdf.html", relatorios=lista)

@app.route('/api/ufs')
def api_ufs():
    data = db.child("uf").get().val() or {}
    return jsonify({"ufs": list(data.keys())})

@app.route('/api/cidades/<uf>')
def api_cidades(uf):
    data = db.child("uf").child(uf).get().val() or {}
    cidades = list(data.keys())
    return jsonify({"cidades": cidades})

@app.route('/api/telefone_cidade')
def api_telefone_cidade():
    uf = request.args.get("uf")
    cidade = request.args.get("cidade")

    if not uf or not cidade:
        return jsonify({"telefone": None})

    ref = db.child("uf").child(uf).child(cidade)
    telefone = ref.get().val()

    return jsonify({"telefone": telefone})

@app.route('/post_transacao_pendente', methods=['POST', 'GET'])
def post_transacao_pendente():

    dados = request.get_json()
    print(dados)
    total_empresa = dados.get("total_empresa")
    itens = dados.get("itens", [])
    
    user = session['name']
    id_origem = itens[0]['tecnico_id']
    
    origem = itens[0]['tecnico_nome']
    
    type = "c"
    
    amount = "{:.2f}".format(total_empresa, 2)
    
    category = "ServiÃ§o"
    #especie_method = request.form.get('especie').title()
    especie = f'Remessa PIX'
    destinatario = "123 CaÃ§a Vazamentos"
    
    lista_os = [item['numero_os'] for item in itens]
    lista_numeros_os = ", ".join(lista_os)
    #taxa = request.form.get('taxa')
    description = f'Pagamento referente Ã s OSs: {lista_numeros_os}.'

    agora = datetime.now()
    
    Financeiro.post_transaction_credito_tecnico(date=agora, type=type, amount=amount, category=category, description=description, especie=especie, destinatario=destinatario, user=user, origem=origem, id_origem=id_origem)

    id_transaction = itens[0]['id_transaction']
    

     
    for item in itens:
        date = item['date_payment']
        print(date)
        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
                return "Formato de data invÃ¡lido."
                
        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
            
        get_service_pedente = db.child("financeiro").child("transactions_pendentes").child(year).child(month).child(day).child(item['id_transaction']).get().val()
        print(get_service_pedente)
        db.child("financeiro").child("transactions_confirmadas").child(year).child(month).child(day).push(get_service_pedente)
        db.child("financeiro").child("transactions_pendentes").child(year).child(month).child(day).child(item['id_transaction']).remove()

        
    return True

@app.route('/transacao_pendente_tecnico')
@check_roles(['tecnico'])
def transacao_pendente_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session.get("user")  # <-- Certifique-se que vocÃª salva o ID do tÃ©cnico na sessÃ£o

    pendentes = {}
    data = db.child("financeiro").child("transactions_pendentes").get().val() or {}

    for ano, meses in data.items():
        for mes, dias in meses.items():
            for dia, transacoes in dias.items():
                for pendente_id, pendente in transacoes.items():
                    # FILTRA APENAS AS OS DO TÃ‰CNICO LOGADO
                    if pendente.get("tecnico_id") == tecnico_id:

                        pendentes[pendente_id] = {
                            **pendente,
                            "ano": ano,
                            "mes": mes,
                            "dia": dia,
                            "id": pendente_id
                        }

    return render_template('transacao_pendente_tecnico.html', pendentes=pendentes)


@app.route("/cancel_transaction_pendding_tecnico", methods=["POST"])
def cancel_transaction_pendding_tecnico():
    data = request.get_json()
    transaction_id = data.get("id")
    date_payment = data.get("date_payment")

    try:
        date = datetime.strptime(date_payment, '%Y-%m-%d')
    except ValueError:
            return "Formato de data invÃ¡lido."
            
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    data = db.child("financeiro").child("transactions_pendentes").child(year).child(month).child(day).child(transaction_id).get().val()

    id_os = data.get("id_os")
    city_os = data.get("city_os")
    date_os = data.get("date_os")
    tecnico_id = data.get("tecnico_id")
    id_create_transaction_user = data.get("id_create_transaction_user")
    id_create_transaction_wallet = data.get("id_create_transaction_wallet")


    try:
        date = datetime.strptime(date_os, '%Y-%m-%d')
    except ValueError:
            return "Formato de data invÃ¡lido."
            
    year_os = str(date.year)
    month_os = f"{date.month:02d}"
    day_os = f"{date.day:02d}"



    try:

        db.child("ordens_servico").child(city_os).child(year_os).child(month_os).child(day_os).child(id_os).child('status_paymment').remove()

        db.child("users").child(tecnico_id).child('wallet').child('cities').child(city_os).child(year).child(month).child(day).child('transactions').child('success').child(id_create_transaction_user).remove()

        db.child("wallet").child(city_os).child(year).child(month).child(day).child('transactions').child('success').child(id_create_transaction_wallet).remove()

        db.child("financeiro").child("transactions_pendentes").child(year).child(month).child(day).child(transaction_id).remove()

        print(f"ID da transaÃ§Ã£o a ser deletada: {transaction_id}")
        print(f"Data de pagamento associada: {date_payment}")
        print(city_os)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    
@app.route('/comissao_atendimento', methods=['GET', 'POST'])
@check_roles(['admin'])
def comissao_atendimento():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('comissao_atendimento.html')

@app.route('/attendance_comissao', methods=['GET', 'POST'])
def attendance_comissao():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('attendance_comissao.html')


@app.route("/attendance_buscar_comissoes", methods=["POST"])
def attendance_buscar_comissoes():
    data = request.get_json()

    ano = str(data.get("ano"))
    mes = f"{int(data.get('mes')):02d}"

    ordens = []

    try:
        dias = (
            db.child("financeiro")
              .child("transactions_confirmadas")
              .child(ano)
              .child(mes)
              .get()
        )

        if not dias.each():
            return jsonify({"ordens": []})

        for dia in dias.each():
            dia_numero = dia.key()

            for transacao_id, item in dia.val().items():
                if session.get('user') == item['atendente_id']:
                    # 🔹 Padronização TOTAL para o front
                    item["id_transaction"] = transacao_id
                    item["dia"] = dia_numero
                    item["status"] = "recebido"   # seu filtro espera isso
                    item["city"] = item.get("city_os")
                    item["tecnico_nome"] = item.get("atendente")

                    ordens.append(item)

        return jsonify({"ordens": ordens})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/buscar_comissoes", methods=["POST"])
def buscar_comissoes():
    data = request.get_json()

    ano = str(data.get("ano"))
    mes = f"{int(data.get('mes')):02d}"

    ordens = []

    try:
        dias = (
            db.child("financeiro")
              .child("transactions_confirmadas")
              .child(ano)
              .child(mes)
              .get()
        )

        if not dias.each():
            return jsonify({"ordens": []})

        for dia in dias.each():
            dia_numero = dia.key()

            for transacao_id, item in dia.val().items():

                # ðŸ”¹ PadronizaÃ§Ã£o TOTAL para o front
                item["id_transaction"] = transacao_id
                item["dia"] = dia_numero
                item["status"] = "recebido"   # seu filtro espera isso
                item["city"] = item.get("city_os")  # âš ï¸ FRONT USA os.city
                item["tecnico_nome"] = item.get("atendente")
                if item["tecnico_nome"] == "Alexandre":
                    print(item["tecnico_nome"])
                ordens.append(item)
                

        return jsonify({"ordens": ordens})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
    
@app.route("/kanban")
def kanban():
    role = session.get("role")
    user_id = session.get("user")
    user_name = session.get("name")

    tasks = db.child("kanban").child("tasks").get().val() or {}

    lista = []

    for tid, t in tasks.items():
        t["id"] = tid

        # ===== prepara chat =====
        comentarios = t.get("comentarios", {})
        chat = []

        for c in comentarios.values():
            chat.append(c)

        chat.sort(key=lambda x: x.get("data", ""))
        t["chat"] = chat[-3:]  # Ãºltimos 3 comentÃ¡rios

        # ===== Ãºltima atualizaÃ§Ã£o =====
        historico = t.get("historico", {})
        if historico:
            ultima = list(historico.values())[-1]
            t["ultimo_status_em"] = ultima.get("data")
        else:
            t["ultimo_status_em"] = t.get("created_at")

        # ===== FILTRO (UM ÃšNICO APPEND) =====
        if role == "admin" or t.get("responsavel_id") == user_id:
            lista.append(t)


    users = db.child("users").get().val() or {}

    return render_template(
        "kanban.html",
        tasks=lista,
        users=users,
        role=role,
        user_id=user_id,
        user_name=user_name
    )


@app.route("/kanban/criar", methods=["POST"])
def criar_task():
    data = request.form

    responsavel_id = data.get("responsavel_id")
    responsavel = db.child("users").child(responsavel_id).get().val()

    payload = {
        "titulo": data.get("titulo"),
        "descricao": data.get("descricao"),
        "status": "todo",
        "prioridade": data.get("prioridade"),
        "responsavel_id": responsavel_id,
        "responsavel_nome": responsavel.get("name"),
        "role_responsavel": responsavel.get("role"),
        "criado_por_id": session.get("user"),
        "criado_por_nome": session.get("name"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    db.child("kanban").child("tasks").push(payload)
    return redirect(url_for("kanban"))

@app.route("/kanban/mover", methods=["POST"])
def mover_task():
    data = request.get_json() or {}
    task_id = data.get("id")
    novo_status = data.get("status")
    print(data)
    
    if not task_id or novo_status not in ["todo", "doing", "done"]:
        return jsonify(success=False), 400

    # Pega status anterior
    status_anterior = db.child("kanban").child("tasks").child(task_id).child("status").get().val()

    # Atualiza status
    db.child("kanban").child("tasks").child(task_id).update({"status": novo_status})

    # Registra histÃ³rico
    db.child("kanban").child("tasks").child(task_id).child("historico").push({
        "de": status_anterior,
        "para": novo_status,
        "user_id": session.get("user"),
        "user_nome": session.get("name"),
        "data": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    return jsonify(success=True)

@app.route("/kanban/comentar", methods=["POST"])
def comentar_task():
    data = request.get_json() or {}
    task_id = data.get("id")
    texto = data.get("texto", "").strip()

    if not task_id or not texto:
        return jsonify(success=False), 400

    db.child("kanban").child("tasks").child(task_id).child("comentarios").push({
        "texto": texto,
        "user_nome": session.get("name"),
        "data": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    return jsonify(success=True)

@app.route("/kanban/task/<task_id>")
def obter_task(task_id):
    task = db.child("kanban").child("tasks").child(task_id).get().val()
    return jsonify(task)

@app.route("/kanban/excluir", methods=["POST"])
def excluir_task():
    data = request.get_json() or {}
    task_id = data.get("id")

    if not task_id:
        return jsonify(success=False, error="ID invÃ¡lido"), 400

    role = session.get("role")
    user_id = session.get("user")

    task_ref = db.child("kanban").child("tasks").child(task_id)
    task = task_ref.get().val()

    if not task:
        return jsonify(success=False, error="Tarefa nÃ£o encontrada"), 404

    # PermissÃµes: admin pode excluir tudo; nÃ£o-admin sÃ³ exclui se foi o criador
    if role != "admin" and task.get("criado_por_id") != user_id:
        return jsonify(success=False, error="Sem permissÃ£o"), 403

    db.child("kanban").child("tasks").child(task_id).remove()
    return jsonify(success=True)

@app.route("/atualizar_valor_os", methods=["POST"])
def atualizar_valor_os():
    data = request.get_json()

    date = data.get("date")
    os_id = data.get("os_id")
    city = data.get("city")
    newprice_raw = data.get("newprice")

    # Converte o valor monetÃ¡rio (ex: "1.250,00" â†’ 1250.00)
    new_price = convert_monetary_value(newprice_raw)

    # Converte a data
    date = datetime.strptime(date, "%Y-%m-%d")
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Atualiza o valor da OS no Firebase
    db.child("ordens_servico").child(city).child(year).child(month).child(day).child(os_id).update({"newprice": new_price})

    return jsonify({
        "success": True,
        "newprice": new_price
    })


@app.route('/adm_desempenho_atendentes', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_desempenho_atendentes():
    meses = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "Março"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]

    now_sp = datetime.now(pytz.timezone('America/Sao_Paulo'))
    current_year = now_sp.year
    selected_month = now_sp.strftime("%m")
    selected_year = str(current_year)
    selected_attendant = "all"

    if request.method == 'POST':
        selected_month = request.form.get('selected_month', selected_month)
        selected_year = request.form.get('selected_year', selected_year)
        selected_attendant = request.form.get('selected_attendant', selected_attendant)

    years = [str(current_year - i) for i in range(5)]

    attendance_data = db.child("attendance_records").get().val() or {}
    users_data = db.child("users").get().val() or {}
    channel_labels = {}

    rows_map = defaultdict(lambda: {
        "attendant_id": "",
        "attendant_name": "",
        "day": "",
        "total": 0,
        "agendados": 0,
        "aguardando": 0,
        "channels_agendados": defaultdict(int),
        "channels_aguardando": defaultdict(int),
    })

    for city, years_data in attendance_data.items():
        if not isinstance(years_data, dict) or selected_year not in years_data:
            continue

        months_data = years_data.get(selected_year, {})
        if not isinstance(months_data, dict) or selected_month not in months_data:
            continue

        days_data = months_data.get(selected_month, {})
        if not isinstance(days_data, dict):
            continue

        for day, attendances in days_data.items():
            if not isinstance(attendances, dict):
                continue

            for attendance_info in attendances.values():
                if not isinstance(attendance_info, dict):
                    continue

                attendant_id = attendance_info.get('user_id')
                if not attendant_id:
                    continue

                attendant_data = users_data.get(attendant_id, {}) if isinstance(users_data, dict) else {}
                attendant_name = attendant_data.get('name', 'Não informado')
                row_key = (attendant_id, day)
                row = rows_map[row_key]

                row["attendant_id"] = attendant_id
                row["attendant_name"] = attendant_name
                row["day"] = day
                row["total"] += 1

                channel = str(attendance_info.get('canal', '')).strip() or "Não informado"
                channel_labels[channel.lower()] = channel
                status = str(attendance_info.get('status', '')).strip().lower()
                if status == "agendado":
                    row["agendados"] += 1
                    row["channels_agendados"][channel] += 1
                elif status == "aguardando":
                    row["aguardando"] += 1
                    row["channels_aguardando"][channel] += 1

    for row in rows_map.values():
        total = row["total"]
        row["percent_agendados"] = round((row["agendados"] / total) * 100, 2) if total else 0
        row["percent_aguardando"] = round((row["aguardando"] / total) * 100, 2) if total else 0
        row["channels_agendados"] = dict(row["channels_agendados"])
        row["channels_aguardando"] = dict(row["channels_aguardando"])

    channel_columns = sorted(channel_labels.values(), key=lambda item: item.lower())

    attendants_options = sorted(
        [
            {
                "id": attendant_id,
                "name": attendant_data.get("name", "Não informado")
            }
            for attendant_id, attendant_data in users_data.items()
            if isinstance(attendant_data, dict) and attendant_data.get("role") == "user"
        ],
        key=lambda item: item["name"].lower()
    )

    grouped_tables_map = defaultdict(lambda: {
        "attendant_id": "",
        "attendant_name": "",
        "rows": [],
    })

    sorted_rows = sorted(
        rows_map.values(),
        key=lambda item: (item["attendant_name"].lower(), int(item["day"]))
    )

    for row in sorted_rows:
        attendant_id = row["attendant_id"]
        grouped = grouped_tables_map[attendant_id]
        grouped["attendant_id"] = attendant_id
        grouped["attendant_name"] = row["attendant_name"]
        grouped["rows"].append(row)

    grouped_tables = []
    for grouped in grouped_tables_map.values():
        rows = grouped["rows"]
        total = sum(row["total"] for row in rows)
        agendados = sum(row["agendados"] for row in rows)
        aguardando = sum(row["aguardando"] for row in rows)
        percent_agendados = round((agendados / total) * 100, 2) if total else 0
        percent_aguardando = round((aguardando / total) * 100, 2) if total else 0

        chart_labels = []
        chart_agendados = []
        chart_aguardando = []
        chart_percent_agendados = []
        chart_percent_aguardando = []

        for row in rows:
            try:
                date_obj = datetime.strptime(
                    f"{selected_year}-{selected_month}-{int(row['day']):02d}",
                    "%Y-%m-%d"
                )
                weekday_map = {
                    0: "seg.",
                    1: "ter.",
                    2: "qua.",
                    3: "qui.",
                    4: "sex.",
                    5: "sab.",
                    6: "dom.",
                }
                weekday_label = weekday_map.get(date_obj.weekday(), "")
                chart_labels.append(f"{int(row['day']):02d} {weekday_label}")
            except ValueError:
                chart_labels.append(str(row["day"]))

            chart_agendados.append(row["agendados"])
            chart_aguardando.append(row["aguardando"])
            chart_percent_agendados.append(row["percent_agendados"])
            chart_percent_aguardando.append(row["percent_aguardando"])

        grouped_tables.append({
            "attendant_id": grouped["attendant_id"],
            "attendant_name": grouped["attendant_name"],
            "rows": rows,
            "total_atendimentos": total,
            "total_agendados": agendados,
            "total_aguardando": aguardando,
            "percent_agendados": percent_agendados,
            "percent_aguardando": percent_aguardando,
            "chart_labels": chart_labels,
            "chart_agendados": chart_agendados,
            "chart_aguardando": chart_aguardando,
            "chart_percent_agendados": chart_percent_agendados,
            "chart_percent_aguardando": chart_percent_aguardando,
        })

    grouped_tables.sort(key=lambda item: item["attendant_name"].lower())

    if selected_attendant != "all":
        grouped_tables = [
            table for table in grouped_tables
            if table["attendant_id"] == selected_attendant
        ]

    total_atendimentos = sum(table["total_atendimentos"] for table in grouped_tables)
    total_agendados = sum(table["total_agendados"] for table in grouped_tables)
    total_aguardando = sum(table["total_aguardando"] for table in grouped_tables)
    total_atendentes = len(grouped_tables)
    selected_month_name = next(
        (mes["name"] for mes in meses if mes["value"] == selected_month),
        selected_month
    )

    return render_template(
        'adm_desempenho_atendentes.html',
        meses=meses,
        years=years,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_attendant=selected_attendant,
        selected_month_name=selected_month_name,
        attendants_options=attendants_options,
        channel_columns=channel_columns,
        grouped_tables=grouped_tables,
        total_atendimentos=total_atendimentos,
        total_agendados=total_agendados,
        total_aguardando=total_aguardando,
        total_atendentes=total_atendentes,
    )


@app.route('/adm_desempenho_agendamentos', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_desempenho_agendamentos():
    meses = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "Março"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]

    now_sp = datetime.now(pytz.timezone('America/Sao_Paulo'))
    current_year = now_sp.year
    selected_month = now_sp.strftime("%m")
    selected_year = str(current_year)
    selected_attendant = "all"

    if request.method == 'POST':
        selected_month = request.form.get('selected_month', selected_month)
        selected_year = request.form.get('selected_year', selected_year)
        selected_attendant = request.form.get('selected_attendant', selected_attendant)

    years = [str(current_year - i) for i in range(5)]

    attendance_data = db.child("attendance_records").get().val() or {}
    orders_data = db.child("ordens_servico").get().val() or {}
    users_data = db.child("users").get().val() or {}

    rows_map = defaultdict(lambda: {
        "attendant_id": "",
        "attendant_name": "",
        "day": "",
        "total_atendimentos": 0,
        "agendados_os": 0,
        "percent_agendados": 0,
    })

    for city, years_data in attendance_data.items():
        if not isinstance(years_data, dict) or selected_year not in years_data:
            continue

        months_data = years_data.get(selected_year, {})
        if not isinstance(months_data, dict) or selected_month not in months_data:
            continue

        days_data = months_data.get(selected_month, {})
        if not isinstance(days_data, dict):
            continue

        for day, attendances in days_data.items():
            if not isinstance(attendances, dict):
                continue

            for attendance_info in attendances.values():
                if not isinstance(attendance_info, dict):
                    continue

                attendant_id = attendance_info.get('user_id')
                if not attendant_id:
                    continue

                attendant_data = users_data.get(attendant_id, {}) if isinstance(users_data, dict) else {}
                attendant_name = attendant_data.get('name', 'Não informado')
                row_key = (attendant_id, day)
                row = rows_map[row_key]

                row["attendant_id"] = attendant_id
                row["attendant_name"] = attendant_name
                row["day"] = day
                row["total_atendimentos"] += 1

    for city, years_data in orders_data.items():
        if not isinstance(years_data, dict) or selected_year not in years_data:
            continue

        months_data = years_data.get(selected_year, {})
        if not isinstance(months_data, dict) or selected_month not in months_data:
            continue

        days_data = months_data.get(selected_month, {})
        if not isinstance(days_data, dict):
            continue

        for day, orders in days_data.items():
            if not isinstance(orders, dict):
                continue

            for order_info in orders.values():
                if not isinstance(order_info, dict):
                    continue

                attendant_id = order_info.get('user_id')
                if not attendant_id:
                    continue

                attendant_data = users_data.get(attendant_id, {}) if isinstance(users_data, dict) else {}
                attendant_name = attendant_data.get('name', 'Não informado')
                row_key = (attendant_id, day)
                row = rows_map[row_key]

                row["attendant_id"] = attendant_id
                row["attendant_name"] = attendant_name
                row["day"] = day
                row["agendados_os"] += 1

    for row in rows_map.values():
        total_atendimentos = row["total_atendimentos"]
        row["percent_agendados"] = (
            round((row["agendados_os"] / total_atendimentos) * 100, 2)
            if total_atendimentos else 0
        )

    attendants_options = sorted(
        [
            {
                "id": attendant_id,
                "name": attendant_data.get("name", "Não informado")
            }
            for attendant_id, attendant_data in users_data.items()
            if isinstance(attendant_data, dict) and attendant_data.get("role") == "user"
        ],
        key=lambda item: item["name"].lower()
    )

    grouped_tables_map = defaultdict(lambda: {
        "attendant_id": "",
        "attendant_name": "",
        "rows": [],
    })

    sorted_rows = sorted(
        rows_map.values(),
        key=lambda item: (item["attendant_name"].lower(), int(item["day"]))
    )

    for row in sorted_rows:
        attendant_id = row["attendant_id"]
        grouped = grouped_tables_map[attendant_id]
        grouped["attendant_id"] = attendant_id
        grouped["attendant_name"] = row["attendant_name"]
        grouped["rows"].append(row)

    grouped_tables = []
    for grouped in grouped_tables_map.values():
        rows = grouped["rows"]
        total_atendimentos = sum(row["total_atendimentos"] for row in rows)
        total_agendados = sum(row["agendados_os"] for row in rows)
        percent_agendados = round(
            (total_agendados / total_atendimentos) * 100 if total_atendimentos else 0,
            2
        )

        chart_labels = []
        chart_totais = []
        chart_agendados = []
        chart_percent_agendados = []

        for row in rows:
            try:
                date_obj = datetime.strptime(
                    f"{selected_year}-{selected_month}-{int(row['day']):02d}",
                    "%Y-%m-%d"
                )
                weekday_map = {
                    0: "seg.",
                    1: "ter.",
                    2: "qua.",
                    3: "qui.",
                    4: "sex.",
                    5: "sab.",
                    6: "dom.",
                }
                weekday_label = weekday_map.get(date_obj.weekday(), "")
                chart_labels.append(f"{int(row['day']):02d} {weekday_label}")
            except ValueError:
                chart_labels.append(str(row["day"]))

            chart_totais.append(row["total_atendimentos"])
            chart_agendados.append(row["agendados_os"])
            chart_percent_agendados.append(row["percent_agendados"])

        grouped_tables.append({
            "attendant_id": grouped["attendant_id"],
            "attendant_name": grouped["attendant_name"],
            "rows": rows,
            "total_atendimentos": total_atendimentos,
            "total_agendados": total_agendados,
            "percent_agendados": percent_agendados,
            "chart_labels": chart_labels,
            "chart_totais": chart_totais,
            "chart_agendados": chart_agendados,
            "chart_percent_agendados": chart_percent_agendados,
        })

    grouped_tables.sort(key=lambda item: item["attendant_name"].lower())

    if selected_attendant != "all":
        grouped_tables = [
            table for table in grouped_tables
            if table["attendant_id"] == selected_attendant
        ]

    total_atendimentos = sum(table["total_atendimentos"] for table in grouped_tables)
    total_agendados = sum(table["total_agendados"] for table in grouped_tables)
    total_atendentes = len(grouped_tables)
    percent_agendados_geral = round(
        (total_agendados / total_atendimentos) * 100 if total_atendimentos else 0,
        2
    )
    selected_month_name = next(
        (mes["name"] for mes in meses if mes["value"] == selected_month),
        selected_month
    )

    return render_template(
        'adm_desempenho_agendamentos.html',
        meses=meses,
        years=years,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_attendant=selected_attendant,
        selected_month_name=selected_month_name,
        attendants_options=attendants_options,
        grouped_tables=grouped_tables,
        total_atendimentos=total_atendimentos,
        total_agendados=total_agendados,
        total_atendentes=total_atendentes,
        percent_agendados_geral=percent_agendados_geral,
    )


@app.route('/adm_servicos_tecnicos', methods=['GET', 'POST'])
@check_roles(['admin'])
def adm_servicos_tecnicos():
    meses = [
        {"value": "01", "name": "Janeiro"},
        {"value": "02", "name": "Fevereiro"},
        {"value": "03", "name": "MarÃ§o"},
        {"value": "04", "name": "Abril"},
        {"value": "05", "name": "Maio"},
        {"value": "06", "name": "Junho"},
        {"value": "07", "name": "Julho"},
        {"value": "08", "name": "Agosto"},
        {"value": "09", "name": "Setembro"},
        {"value": "10", "name": "Outubro"},
        {"value": "11", "name": "Novembro"},
        {"value": "12", "name": "Dezembro"},
    ]

    def format_currency_brl(value):
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    now_sp = datetime.now(pytz.timezone('America/Sao_Paulo'))
    current_year = now_sp.year
    selected_month = now_sp.strftime("%m")
    selected_year = str(current_year)
    selected_technician = "all"

    if request.method == 'POST':
        selected_month = request.form.get('selected_month', selected_month)
        selected_year = request.form.get('selected_year', selected_year)
        selected_technician = request.form.get('selected_technician', selected_technician)

    years = [str(current_year - i) for i in range(5)]

    orders_data = db.child("ordens_servico").get().val() or {}
    users_data = db.child("users").get().val() or {}

    technician_rows = defaultdict(lambda: {
        "technician_id": "",
        "technician_name": "",
        "total_retornos": 0,
        "services": defaultdict(lambda: {
            "service": "",
            "total_services": 0,
            "total_amount": 0.0,
            "average_amount": 0.0,
            "total_amount_display": "",
            "average_amount_display": "",
        }),
    })
    total_retornos_geral = 0

    for city, years_data in orders_data.items():
        if not isinstance(years_data, dict) or selected_year not in years_data:
            continue

        months_data = years_data.get(selected_year, {})
        if not isinstance(months_data, dict) or selected_month not in months_data:
            continue

        days_data = months_data.get(selected_month, {})
        if not isinstance(days_data, dict):
            continue

        for orders in days_data.values():
            if not isinstance(orders, dict):
                continue

            for order_info in orders.values():
                if not isinstance(order_info, dict):
                    continue

                technician_id = order_info.get('tecnico_id')
                if not technician_id:
                    continue

                technician_data = users_data.get(technician_id, {}) if isinstance(users_data, dict) else {}
                technician_name = technician_data.get('name', 'NÃ£o informado')
                service_name = str(order_info.get('service', '')).strip() or "NÃ£o informado"
                raw_amount = str(order_info.get('newprice', '0')).strip() or "0"

                try:
                    amount = float(convert_monetary_value(raw_amount))
                except (TypeError, ValueError, AttributeError):
                    amount = 0.0

                technician_group = technician_rows[technician_id]
                technician_group["technician_id"] = technician_id
                technician_group["technician_name"] = technician_name

                if service_name.lower() == "retorno":
                    technician_group["total_retornos"] += 1
                    total_retornos_geral += 1
                    continue

                service_group = technician_group["services"][service_name]
                service_group["service"] = service_name
                service_group["total_services"] += 1
                service_group["total_amount"] += amount

    technician_options = sorted(
        [
            {
                "id": user_id,
                "name": user_info.get("name", "NÃ£o informado")
            }
            for user_id, user_info in users_data.items()
            if isinstance(user_info, dict) and user_info.get("role") == "tecnico"
        ],
        key=lambda item: item["name"].lower()
    )

    technician_tables = []
    for technician in technician_rows.values():
        if selected_technician != "all" and technician["technician_id"] != selected_technician:
            continue

        services = []
        total_services = 0
        total_amount = 0.0

        for service in technician["services"].values():
            service["average_amount"] = round(
                service["total_amount"] / service["total_services"], 2
            ) if service["total_services"] else 0
            service["total_amount_display"] = format_currency_brl(service["total_amount"])
            service["average_amount_display"] = format_currency_brl(service["average_amount"])
            services.append(service)
            total_services += service["total_services"]
            total_amount += service["total_amount"]

        services.sort(key=lambda item: (-item["total_services"], item["service"].lower()))

        average_ticket = round(total_amount / total_services, 2) if total_services else 0

        technician_tables.append({
            "technician_id": technician["technician_id"],
            "technician_name": technician["technician_name"],
            "total_retornos": technician["total_retornos"],
            "services": services,
            "total_services": total_services,
            "total_amount": total_amount,
            "average_ticket": average_ticket,
            "total_amount_display": format_currency_brl(total_amount),
            "average_ticket_display": format_currency_brl(average_ticket),
        })

    technician_tables.sort(key=lambda item: item["technician_name"].lower())

    summary_service_totals = defaultdict(int)
    technician_summary_rows = []

    for technician in technician_tables:
        service_totals = {}
        for service in technician["services"]:
            service_name = service["service"]
            total_services = service["total_services"]
            service_totals[service_name] = total_services
            summary_service_totals[service_name] += total_services

        technician_summary_rows.append({
            "technician_name": technician["technician_name"],
            "total_services": technician["total_services"],
            "total_retornos": technician["total_retornos"],
            "service_totals": service_totals,
        })

    summary_service_columns = sorted(
        summary_service_totals.keys(),
        key=lambda item: (-summary_service_totals[item], item.lower())
    )

    total_technicians = len(technician_tables)
    total_services_geral = sum(item["total_services"] for item in technician_tables)
    total_amount_geral = sum(item["total_amount"] for item in technician_tables)
    average_ticket_geral = round(
        total_amount_geral / total_services_geral, 2
    ) if total_services_geral else 0

    selected_month_name = next(
        (mes["name"] for mes in meses if mes["value"] == selected_month),
        selected_month
    )

    return render_template(
        'adm_servicos_tecnicos.html',
        meses=meses,
        years=years,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_technician=selected_technician,
        selected_month_name=selected_month_name,
        technician_options=technician_options,
        technician_tables=technician_tables,
        technician_summary_rows=technician_summary_rows,
        summary_service_columns=summary_service_columns,
        total_technicians=total_technicians,
        total_retornos_geral=total_retornos_geral,
        total_services_geral=total_services_geral,
        total_amount_geral_display=format_currency_brl(total_amount_geral),
        average_ticket_geral_display=format_currency_brl(average_ticket_geral),
    )

@app.route('/buscar_os')
@check_roles(['user', 'admin'])
def buscar_os():
    return render_template('buscar_os.html', resultados=[], termo="")

@app.route('/resultado_busca_os', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def resultado_busca_os():
    termo = (request.form.get('termo') or request.args.get('termo') or '').strip()
    resultados = []

    if not termo:
        return render_template('buscar_os.html', resultados=[], termo=termo)

    termo_normalizado = normalize_search_value(termo)

    # Dados do usuário logado
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val() or {}
    role = user_data.get("role", "")
    cidades_permitidas = user_data.get("cities", []) or []

    ordens_servico = db.child("ordens_servico").get().val() or {}

    for city, years in ordens_servico.items():
        if not isinstance(years, dict):
            continue

        # Restrição por permissão
        if role != 'admin' and city not in cidades_permitidas:
            continue

        for year, months in years.items():
            if not isinstance(months, dict):
                continue

            for month, days in months.items():
                if not isinstance(days, dict):
                    continue

                for day, os_items in days.items():
                    if not isinstance(os_items, dict):
                        continue

                    for os_id, os_data in os_items.items():
                        if not isinstance(os_data, dict):
                            continue

                        numero_os = str(os_data.get("numero_os", "")).strip()
                        cpfcnpj = str(os_data.get("cpfcnpj", "")).strip()
                        phone = str(os_data.get("phone", "")).strip()
                        name = str(os_data.get("name", "")).strip()

                        numero_os_normalizado = normalize_search_value(numero_os)
                        cpfcnpj_normalizado = normalize_search_value(cpfcnpj)
                        phone_normalizado = normalize_search_value(phone)
                        name_normalizado = normalize_search_value(name)

                        encontrou = False

                        # Busca exata por número da OS
                        if termo_normalizado == numero_os_normalizado:
                            encontrou = True

                        # Busca exata por CPF/CNPJ
                        elif termo_normalizado == cpfcnpj_normalizado:
                            encontrou = True

                        # Busca exata por telefone
                        elif termo_normalizado == phone_normalizado:
                            encontrou = True

                        # Busca parcial por nome
                        elif termo_normalizado in name_normalizado and termo_normalizado != "":
                            encontrou = True

                        if encontrou:
                            resultados.append({
                                "os_id": os_id,
                                "city": city,
                                "year": year,
                                "month": month,
                                "day": day,
                                "numero_os": os_data.get("numero_os", ""),
                                "name": os_data.get("name", ""),
                                "cpfcnpj": os_data.get("cpfcnpj", ""),
                                "phone": os_data.get("phone", ""),
                                "service": os_data.get("service", ""),
                                "newprice": os_data.get("newprice", ""),
                                "start_datetime": os_data.get("start_datetime", ""),
                                "end_datetime": os_data.get("end_datetime", ""),
                                "status_paymment": os_data.get("status_paymment", ""),
                                "address": os_data.get("address", {})
                            })

    resultados.sort(
        key=lambda x: f"{x['year']}-{x['month']}-{x['day']} {x['start_datetime']}",
        reverse=True
    )

    return render_template('buscar_os.html', resultados=resultados, termo=termo)

@app.route('/os_atendente/<city>/<year>/<month>/<day>/<id>', methods=['GET', 'POST'])
#@check_roles(['admin', 'tecnico'])
def os_atendente(city, year, month, day, id):
    get_os = db.child("ordens_servico").child(city).child(year).child(month).child(day).child(id).get().val()

    all_users = db.child("users").get().val() or {}
    tecnicos = {
        uid: user for uid, user in all_users.items()
        if user.get('role') == 'tecnico' and city in user.get('cities', [])
    }

    date_str = f"{year}-{month}-{day}"

    return render_template(
        'os_atendente.html',
        os=get_os,
        os_id=id,
        date=date_str,
        tecnicos=tecnicos
    )

@app.route('/buscar_atendimento')
@check_roles(['user', 'admin'])
def buscar_atendimento():
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val() or {}
    role = user_data.get("role", "")
    cidades_permitidas = user_data.get("cities", []) or []

    all_users = db.child("users").get().val() or {}

    if role == "admin":
        tecnicos = {
            uid: user for uid, user in all_users.items()
            if user.get("role") == "tecnico"
        }
    else:
        tecnicos = {
            uid: user for uid, user in all_users.items()
            if user.get("role") == "tecnico"
            and any(c in user.get("cities", []) for c in cidades_permitidas)
        }

    return render_template(
        'buscar_atendimento.html',
        resultados=[],
        termo="",
        tecnicos=tecnicos
    )

@app.route('/resultado_busca_atendimento', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def resultado_busca_atendimento():
    termo = (request.form.get('termo') or request.args.get('termo') or '').strip()
    resultados = []

    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val() or {}
    role = user_data.get("role", "")
    cidades_permitidas = user_data.get("cities", []) or []

    all_users = db.child("users").get().val() or {}

    if role == "admin":
        tecnicos = {
            uid: user for uid, user in all_users.items()
            if user.get("role") == "tecnico"
        }
    else:
        tecnicos = {
            uid: user for uid, user in all_users.items()
            if user.get("role") == "tecnico"
            and any(c in user.get("cities", []) for c in cidades_permitidas)
        }

    if not termo:
        return render_template(
            'buscar_atendimento.html',
            resultados=[],
            termo=termo,
            tecnicos=tecnicos
        )

    termo_normalizado = normalize_search_value(termo)

    attendance_data = db.child("attendance_records").get().val() or {}

    for city, years in attendance_data.items():
        if not isinstance(years, dict):
            continue

        # Restrição por permissão
        if role != 'admin' and city not in cidades_permitidas:
            continue

        for year, months in years.items():
            if not isinstance(months, dict):
                continue

            for month, days in months.items():
                if not isinstance(days, dict):
                    continue

                for day, registros in days.items():
                    if not isinstance(registros, dict):
                        continue

                    for attendance_id, attendance in registros.items():
                        if not isinstance(attendance, dict):
                            continue

                        name = str(attendance.get("name", "")).strip()
                        phone = str(attendance.get("phone", "")).strip()
                        service = str(attendance.get("service", "")).strip()
                        canal = str(attendance.get("canal", "")).strip()
                        status = str(attendance.get("status", "")).strip()
                        details = str(attendance.get("details", "")).strip()
                        price = str(attendance.get("price", "")).strip()
                        sexo = str(attendance.get("sexo", "")).strip()

                        name_normalizado = normalize_search_value(name)
                        phone_normalizado = normalize_search_value(phone)
                        service_normalizado = normalize_search_value(service)
                        canal_normalizado = normalize_search_value(canal)
                        status_normalizado = normalize_search_value(status)

                        encontrou = False

                        # Nome - parcial
                        if termo_normalizado in name_normalizado and termo_normalizado != "":
                            encontrou = True

                        # Telefone - exato normalizado
                        elif termo_normalizado == phone_normalizado:
                            encontrou = True

                        # Serviço - parcial
                        elif termo_normalizado in service_normalizado and termo_normalizado != "":
                            encontrou = True

                        # Canal - parcial
                        elif termo_normalizado in canal_normalizado and termo_normalizado != "":
                            encontrou = True

                        # Status - parcial
                        elif termo_normalizado in status_normalizado and termo_normalizado != "":
                            encontrou = True

                        if encontrou:
                            resultados.append({
                                "attendance_id": attendance_id,
                                "city": city,
                                "year": year,
                                "month": month,
                                "day": day,
                                "name": name,
                                "phone": phone,
                                "price": price,
                                "service": service,
                                "canal": canal,
                                "sexo": sexo,
                                "status": status,
                                "details": details,
                                "timestamp": attendance.get("timestamp", ""),
                            })

    resultados.sort(
        key=lambda x: f"{x['year']}-{x['month']}-{x['day']}",
        reverse=True
    )

    return render_template(
        'buscar_atendimento.html',
        resultados=resultados,
        termo=termo,
        tecnicos=tecnicos
    )



if __name__ == '__main__':
    app.run(debug=True, port=5037)

