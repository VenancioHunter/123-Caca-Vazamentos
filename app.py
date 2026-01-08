from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyrebase
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
from config import db, auth, storage
from collections import defaultdict
from core.cities.class_cities import Cities
from core.financeiro.class_financeiro import Financeiro
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.secret_key = 'secret'


def datetimeformat(value, format='%d/%m/%Y %H:%M:%S'):
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    
    # Converta o timestamp para o horário de São Paulo
    dt_sao_paulo = datetime.fromtimestamp(value, sao_paulo_tz)
    
    # Formate a data e hora no formato desejado
    return dt_sao_paulo.strftime(format)

def datetimeformathour(value, format='%H:%M'):
    return datetime.strptime(value, '%Y-%m-%d %H:%M').strftime(format)

# Registre o filtro no ambiente Jinja2
app.jinja_env.filters['datetimeformat'] = datetimeformat

app.jinja_env.filters['datetimeformathour'] = datetimeformathour

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
            # Defina o nível de acesso padrão e salve o nome do usuário
            db.child("users").child(user['localId']).set({
                "name": name,
                "email": email,
                "password": password,
                "role": "user",  # Define o papel padrão como 'user'
                "cities": []  # Lista de cidades vazia por padrão
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
    user_email = session.get('email', 'Usuário')
    return render_template('dashboard.html', user_email=user_email)

@app.route('/dashboard_tecnico')
@check_roles(['tecnico'])
def dashboard_tecnico():
    user_email = session.get('email', 'Usuário')
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

        # Verifique se a cidade já existe
        cities = db.child("cities").get().val() or {}
        if city_name not in cities.values():
            db.child("cities").push(city_name)

            db.child("uf").child(uf_name).child(city_name).set(phone_number)
            return redirect(url_for('add_city'))
        else:
            return "Cidade já existe"
        

    return render_template('add_city.html')

@app.route('/add_city_sistema', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_city_sistema():
    if request.method == 'POST':
        city_name = request.form['city']

        # Verifique se a cidade já existe
        cities = db.child("cities").get().val() or {}
        if city_name not in cities.values():
            db.child("cities").push(city_name)

            
            return redirect(url_for('add_city'))
        else:
            return "Cidade já existe"
       
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

        # Obtenha as cidades atuais do usuário
        user_cities = db.child("users").child(user_id).child("cities").get().val() or []

        if city not in user_cities:
            user_cities.append(city)
            db.child("users").child(user_id).update({"cities": user_cities})

        return "Usuário vinculado à cidade com sucesso"

    # Obtenha todos os usuários e cidades para o formulário
    users = db.child("users").get().val()

    # Filtrar apenas os usuários com papel "user"
    user_role = 'user'
    users = {user_id: user for user_id, user in users.items() if user.get('role') == user_role}

    cities = db.child("cities").get().val() or {}

    return render_template('link_user_city.html', users=users, cities=cities)


def convert_monetary_value(value_str):
    # Verifique se o valor já está no formato desejado
    if '.' in value_str and ',' not in value_str:
        # Retorne o valor como está, pois já está no formato correto
        return value_str

    # Se não estiver no formato desejado, faça a substituição necessária
    clean_value = value_str.replace('.', '').replace(',', '.')

    return clean_value


@app.route('/attendance_records', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def attendance_records():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']

    if request.method == 'POST':
        # Dados do formulário
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
        month = f"{now.month:02d}"  # Garantir que o mês tenha dois dígitos
        day = f"{now.day:02d}"  # Garantir que o dia tenha dois dígitos

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

    # Carregar as cidades vinculadas ao usuário
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    # Carregar todos os serviços disponíveis
    services = db.child("services").get().val() or {}

    return render_template('attendance_records.html', cities=cities, services=services)


@app.route('/add_service', methods=['GET', 'POST'])
@check_roles(['admin'])
def add_service():
    if request.method == 'POST':
        service_name = request.form['service']

        # Verifique se o serviço já existe
        services = db.child("services").get().val() or {}
        if service_name not in services.values():
            db.child("services").push(service_name)
            return "Serviço adicionado com sucesso"
        else:
            return "Serviço já existe"

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

    # Carregar as cidades vinculadas ao usuário
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    return render_template('consulta_atendimentos.html', cities=cities)

@app.route('/adm_consulta_atendimentos', methods=['GET', 'POST'])
@check_roles(['user', 'admin'])
def adm_consulta_atendimentos():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Carregar as cidades vinculadas ao usuário
    cities = db.child("cities").get().val().values()

    return render_template('adm_consulta_atendimentos.html', cities=cities)
    


@app.route('/view_attendance', methods=['GET'])
@check_roles(['user', 'admin'])
def view_attendance():
    city = request.args.get('city')
    date_str = request.args.get('date')

    if not city or not date_str:
        return "Cidade ou data não fornecida."

    # Verifique se o usuário tem permissão para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    if city not in user_data.get('cities', []):
        return "Você não tem permissão para acessar registros desta cidade."

    # Converter a data fornecida para ano, mês e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

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
        return "Cidade ou data não fornecida."

    # Verifique se o usuário tem permissão para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    is_admin = user_data.get('role') == 'admin'
    has_city_permission = city in user_data.get('cities', [])

    if not (is_admin or has_city_permission):
        return "Você não tem permissão para acessar registros desta cidade."

    # Converter a data fornecida para ano, mês e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

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

            # Dicionário para agrupar atendimentos por user_id
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
                                    # Obtém o nome do usuário baseado no user_id
                                    user_name = User.get_name(user_id)

                                    record = {
                                        "city": city,
                                        "date": f"{day}/{month}/{year}",
                                        **attendance_info
                                    }
                                    
                                    # Agrupa pelo nome do usuário
                                    grouped_records[user_name].append(record)
                                else:
                                    # Se user_id não estiver presente, continue ou log um erro
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

        # Recuperar as cidades atualmente vinculadas ao técnico
        tecnico_data = db.child("users").child(tecnico_id).get().val()
        cidades_atuais = set(tecnico_data.get('cities', []))

        # Combinar as cidades atuais com as novas
        cidades_atualizadas = list(cidades_atuais.union(novas_cidades))

        # Atualizar as cidades no banco de dados para o técnico selecionado
        db.child("users").child(tecnico_id).update({"cities": cidades_atualizadas})

        return redirect(url_for('vincular_tecnico'))

    # Carregar todos os técnicos e cidades disponíveis
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
    month = f"{date_firebase.month:02d}"  # Garantir que o mês tenha dois dígitos
    day = f"{date_firebase.day:02d}"  # Garantir que o dia tenha dois dígitos

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
                print(f"O técnico já possui uma OS agendada nesse horário.")
                return jsonify({'status': 'conflict', 'message': 'O técnico já possui uma OS agendada nesse horário.'}), 400
            

    return jsonify({'status': 'success', 'message': 'Horário livre'}), 200

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

    data_datetime = datetime.strptime(date_filter, '%d/%m/%Y')
    # Formatar o objeto datetime no formato desejado aaaa-mm-dd
    data_formatada = data_datetime.strftime('%Y-%m-%d')
    # Check availability for each selected technician

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
    month = f"{date.month:02d}"  # Garantir que o mês tenha dois dígitos
    day = f"{date.day:02d}"  # Garantir que o dia tenha dois dígitos

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
            return "Formato de data inválido."

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

    # Carregar as cidades vinculadas ao usuário
    user_data = db.child("users").child(user_id).get().val()
    cities = user_data.get('cities', [])

    return render_template('consulta_os_atendente.html', cities=cities)

@app.route('/view_schedule_atendente', methods=['GET'])
@check_roles(['user'])
def view_schedule_atendente():
    city = request.args.get('city')
    date_str = request.args.get('date')

    if not city or not date_str:
        return "Cidade ou data não fornecida."

    # Verifique se o usuário tem permissão para acessar esta cidade
    user_id = session['user']
    user_data = db.child("users").child(user_id).get().val()

    if city not in user_data.get('cities', []):
        return "Você não tem permissão para acessar registros desta cidade."

    # Converter a data fornecida para ano, mês e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"
    
    # Obtenha o ID do técnico logado
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

    # Define o fuso horário de São Paulo
    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    now_in_sao_paulo = datetime.now(sao_paulo_tz)

    # Obtém o timestamp atual
    timestamp = now_in_sao_paulo.timestamp()

    # Tenta converter a data antiga para objetos ano, mês e dia
    try:
        date = datetime.strptime(old_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

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

        # Tenta converter a nova data para ano, mês e dia
        try:
            date = datetime.strptime(new_date, '%Y-%m-%d')
        except ValueError:
            return "Formato de data inválido."

        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"

        # Salva os dados no Firebase com o novo ID gerado automaticamente
        db.child("ordens_servico").child(city).child(year).child(month).child(day).push(get_os)

        db.child(path_old_os).child(old_id).remove()
        

    return redirect(url_for('consulta_os_atendente'))

@app.route('/finalizar_os', methods=['POST'])
def finalizar_os():
    # Recebe os dados enviados pelo formulário
    data = request.json
   
    # Inicializa as variáveis de categorização
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

    '''# Tenta converter a nova data para ano, mês e dia
    try:
            date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
            return "Formato de data inválido."

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

    tecnico_id = session['user']  # ID do técnico logado
    now = datetime.now()
    ano_atual = now.strftime("%Y")
    mes_atual = now.strftime("%m")

    # Receber ano e mês do formulário ou usar os valores padrão (ano e mês atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # Mês atual
    all_pendding_transactions = {}
    # Obter as cidades associadas ao técnico
    cities = db.child('users').child(session['user']).child('cities').get().val()

    

    # Buscar ordens de serviço pendentes para cada cidade
    for city in cities:
        pendding_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_pendding = db.child(pendding_transactions_path).get().val() or {}

        # Agora, em vez de usar `update`, fazemos uma combinação manual para não sobrescrever
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
                    # Mesclar as transações do dia
                    all_pendding_transactions[day]['transactions']['pendding'].update(day_data['transactions']['pendding'])

    pendding_transactions = {}

    # Percorrer os dias e filtrar as transações pendentes do técnico logado
    for day, day_data in all_pendding_transactions.items():
        pendding = day_data.get('transactions', {}).get('pendding', {})
        for trans_id, trans_data in pendding.items():
            if trans_data.get('tecnico_id') == tecnico_id:
                pendding_transactions[trans_id] = trans_data

    # Renderizar as transações filtradas
    return render_template('paymments_pendding_tecnico.html', transactions=pendding_transactions, ano=ano, mes=mes)

'''
@app.route('/extrato_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def extrato_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']  # ID do técnico logado
    now = datetime.now()
    ano_atual = now.strftime("%Y")
    mes_atual = now.strftime("%m")

    # Receber ano e mês do formulário ou usar os valores padrão (ano e mês atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # Mês atual

    participation = User_Wallet.get_participation(id=tecnico_id)
    participation_empresa = 100 - participation
    
    # Obter as cidades associadas ao técnico
    cities = db.child('users').child(session['user']).child('cities').get().val()

    grouped_transactions = {}

    # Buscar ordens de serviço para cada cidade
    for city in cities:
        success_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_success = db.child(success_transactions_path).get().val() or {}

        # Agrupar as transações por dia
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
                    amount = float(trans_data.get('amount', 0))  # Pega o valor da transação
                    grouped_transactions[day]['transactions'].append({
                        'trans_id': trans_id,
                        'data': trans_data,
                        'city': city
                    })
                    grouped_transactions[day]['total_amount'] += amount  # Soma o valor ao total do dia


    # Obter os custos (combustível, manutenção, pedágio) do mês
    costs_path = f"users/{session['user']}/wallet/costs/{ano}/{mes}"
    month_costs_data = db.child(costs_path).get().val() or {}

    # Somar os custos de todos os dias do mês
    for day, costs_data in month_costs_data.items():
        total_costs = 0.0
        
        # Inicializar variáveis para custos individuais
        combustivel = 0.0
        manutencao = 0.0
        pedagio = 0.0
        reparo = 0.0
        outros = 0.0
        
        # Percorrer os dados de custo para o dia específico
        for cost_id, cost_items in costs_data.items():
            if isinstance(cost_items, dict):
                combustivel = float(cost_items.get('combustivel', '0.0'))
                manutencao = float(cost_items.get('manutencao', '0.0'))
                pedagio = float(cost_items.get('pedagio', '0.0'))
                reparo = float(cost_items.get('reparo', '0.0'))
                outros = float(cost_items.get('outros', '0.0'))
              
                # Somar ao total de custos do dia
                total_costs += combustivel + manutencao + pedagio + reparo + outros

               
        # Se houver transações agrupadas para esse dia, atualizar com os custos


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


    # Renderizar as transações agrupadas por dia, incluindo os custos e o saldo restante
    return render_template('extrato_tecnico.html', grouped_transactions=grouped_transactions, ano=ano, mes=mes)

'''

    


@app.route('/extrato_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def extrato_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']
    now = datetime.now()

    # Receber a data do formulário ou usar o valor padrão (dia atual)
    if request.method == 'POST':
        data = request.form.get('data', now.strftime("%Y-%m-%d"))
    else:
        data = now.strftime("%Y-%m-%d")  # Data atual como padrão

    ano, mes, dia = data.split('-')

    date = datetime.strptime(data, '%Y-%m-%d')

    participation = User_Wallet.get_participation(id=tecnico_id, data=date)
    participation_empresa = 100 - participation
    
    cities = db.child('users').child(session['user']).child('cities').get().val()

    grouped_transactions = {}

    # Buscar ordens de serviço para a data selecionada
    for city in cities:
        success_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_success = db.child(success_transactions_path).get().val() or {}

        # Filtrar transações para o dia específico
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

    # Buscar os custos do dia específico
    #costs_path = f"users/{session['user']}/wallet/costs/{ano}/{mes}"
    #month_costs_data = db.child(costs_path).get().val() or {}

    # Garantir que o dia está nos custos recuperados
    #costs_data = month_costs_data.get(dia, {})  # Retorna um dicionário vazio se o dia não existir
    
 

    #if costs_data:
        # Acessar diretamente a única chave no dicionário
        #daily_costs = list(costs_data.values())[0]  # Acessa o primeiro (e único) valor do dicionário

        # Extrair os valores dos custos, assumindo 0.0 se o campo não existir
    combustivel = 0.0
    manutencao = 0.0
    pedagio = 0.0
    reparo = 0.0
    outros = 0.0
    total_costs = combustivel + manutencao + pedagio + reparo + outros


        # Atribuir os valores ao dicionário de transações agrupadas
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
            # Passar a variável 'now' para o template

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

                category = 'Manutenção'
                especie = 'Veículo'

            elif item == 'combustivel':
                category = 'Transporte'
                especie = 'Combustível'
            
            elif item == 'pedagio':
                category = 'Transporte'
                especie = 'Pedágio'
            
            elif item == 'reparo':
                category = 'Manutenção'
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

    # Converter a data fornecida para ano, mês e dia
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."
    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obter todos os dados de wallet do Firebase
    wallet_data = db.child("wallet").get().val() or {}

    # Dicionário para agrupar transações, somar os amounts e os custos por técnico
    tecnico_transactions = defaultdict(lambda: {'transactions': [], 'total_amount': 0.0, 'costs': {'combustivel': 0.0, 'manutencao': 0.0, 'pedagio': 0.0, 'reparo': 0.0, 'outros': 0.0}, 'valor_final': 0.0})

    # Iterar sobre as cidades na estrutura do Firebase
    for city, years in wallet_data.items():
        if year in years:
            months = years[year]
            if month in months:
                days = months[month]
                if day in days:
                    # Obter as transações do dia específico
                    transactions = days[day].get("transactions", {}).get("success", {})

                    # Agrupar transações pelo nome do técnico e somar os amounts
                    for transaction_id, transaction_info in transactions.items():
                        tecnico_id = transaction_info.get('tecnico_id')
                        if tecnico_id:
                            name_tecnico = User.get_name(tecnico_id)  # Obter o nome do técnico
                        
                            # Buscar os custos do técnico (apenas uma vez por técnico)
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
                        
                            # Somar o valor da transação ao total do técnico
                            amount = float(transaction_info.get('amount', 0))
                            tecnico_transactions[name_tecnico]['transactions'].append(transaction_info)
                            tecnico_transactions[name_tecnico]['total_amount'] += amount
                        transaction_info['city'] = city

    # Calcular o valor final para cada técnico (total_amount - custos)
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
    
    # Obtendo os dados do formulário
    city = request.form.get('city')
    old_id = request.form.get("idRecord")
    motivo = request.form.get("deleteOsMotivo")
    date = request.form.get("deletaOsdate")
    tecnico_id = request.form.get('tecnico')

    # Verificando o formato da data
    try:
        date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."
    
    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtendo dados da OS do Firebase
    data = db.child("ordens_servico").child(city).child(year).child(month).child(day).child(old_id).get().val()

    if not data:
        return "Dados da OS não encontrados."

    # Obter a data e hora atual com o fuso horário de São Paulo
    fuso_horario_sp = pytz.timezone('America/Sao_Paulo')
    data_atual_sp = datetime.now(fuso_horario_sp)
    date_str = data_atual_sp.strftime('%Y-%m-%d')

    # Verificando o formato da data atual
    try:
        date_canceled = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."
    
    ano = str(date_canceled.year)
    mes = f"{date_canceled.month:02d}"
    dia = f"{date_canceled.day:02d}"

    # Atualizando o dicionário com o motivo do cancelamento
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

    # Receber ano e mês do formulário ou usar os valores padrão (ano e mês atuais)
    if request.method == 'POST':
        ano = request.form.get('ano', ano_atual)
        mes = request.form.get('mes', mes_atual)
    else:
        ano = ano_atual  # Ano atual
        mes = mes_atual  # Mês atual

    all_pendding_transactions = []

    cities = Cities.get_cities()

    # Buscar ordens de serviço pendentes para cada cidade
    for city in cities.values():
        pendding_transactions_path = f"wallet/{city}/{ano}/{mes}"
        paymments_pendding = db.child(pendding_transactions_path).get().val() or {}

        # Iterar sobre cada dia
        for day_data in paymments_pendding.values():
            # Verificar se há transações pendentes no dia
            if 'transactions' in day_data and 'pendding' in day_data['transactions']:
                for transaction_id, transaction_data in day_data['transactions']['pendding'].items():
                    # Adicionar o ID da transação ao dicionário
                    name = User.get_name(id=transaction_data['tecnico_id'])
                    transaction_data['transaction_id'] = transaction_id
                    transaction_data['name_tecnico'] = name
                    all_pendding_transactions.append(transaction_data)

    # Renderizar as transações pendentes
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

    # Tenta converter a nova data para ano, mês e dia
    try:
        date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

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

    # Tenta converter a nova data para ano, mês e dia
    try:
        date_firebase = datetime.strptime(os_date, '%Y-%m-%d')
    except ValueError:
        return "Formato de data inválido."

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

            # Dicionário para agrupar atendimentos por user_id
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
                                    
                                    # Agrupa pelo nome do usuário
                                    grouped_records[user_id].append(record)
                                else:
                                    # Se user_id não estiver presente, continue ou log um erro
                                    print(f"User ID ausente para o atendimento {attendance_id}")

            return render_template('adm_lista_os.html', grouped_records=grouped_records, selected_date=selected_date)
    else:
        return render_template('adm_lista_os.html', grouped_records={}, selected_date=None)


@app.route('/relatorio', methods=['GET', 'POST'])
def relatorio():
   
    return render_template('relatorio.html')

@app.route('/relatorio_tecnico', methods=['GET', 'POST'])
@check_roles(['tecnico'])
def relatorio_tecnico():
    if 'user' not in session:
        return redirect(url_for('login'))

    tecnico_id = session['user']

    # Buscar dados do técnico no Firebase
    tecnico_data = db.child('users').child(tecnico_id).get().val()

    tecnico_info = {
        "nome_relatorio": tecnico_data.get("nome_relatorio", ""),
        "cpf_cnpj": tecnico_data.get("cpf_cnpj", ""),
        "assinatura": tecnico_data.get("assinatura", None)  # caso exista imagem salva
    }
   
    return render_template('relatorio_tecnico.html', tecnico=tecnico_info)

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
   
    
    return render_template('orcamento.html')

@app.route('/attendance_desempenho', methods=['GET', 'POST'])
def attendance_desempenho():
    id_atendente = session.get('user')  # ID do atendente logado
    if not id_atendente:
        return redirect('/login')  # Redireciona se não estiver logado

    # Lista de meses para o select
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

    selected_month = None
    year = datetime.now(pytz.timezone('America/Sao_Paulo')).year  # Ano atual
    daily_summary = {}
    total_agendados = 0
    total_aguardando = 0
    total_atendimentos = 0

    if request.method == 'POST':
        selected_month = request.form.get('selected_month')

    if selected_month:
        # Obtém os dados de atendimentos do Firebase
        attendance_data = db.child("attendance_records").get().val() or {}

        # Filtra os registros para o atendente logado e o mês selecionado
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

    # Atualiza os totais mensais fora do loop diário
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

    # Converte o resumo diário para uma lista ordenada por dia
    ordered_daily_summary = [
        {"day": f"{day}/{selected_month}/{year}", **summary}
        for day, summary in sorted(daily_summary.items())
    ]

    # Obtém o nome do atendente logado
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
        return redirect('/login')  # Redireciona para o login se não estiver logado

    # Lista de anos e meses para os selects
    current_year = datetime.now().year
    years = [current_year - i for i in range(5)]  # Últimos 5 anos
    months = [
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
                # Converte os dados em uma lista para exibição e ajusta a data
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
        return redirect('/login')  # Redireciona para o login se não estiver logado
    
    current_year = datetime.now().year
    years = [current_year - i for i in range(5)]  # Últimos 5 anos
    months = [
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

        # Processa dados de agendamento (ordens de serviço)
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
                        # Contagem por serviço
                        service_counts_agendado[service] = service_counts_agendado.get(service, 0) + 1

                        # Soma de valores por serviço
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

        # Cálculo do valor médio por serviço
        for service, total_value in service_value_totals_agendado.items():
            count = service_counts_agendado.get(service, 0)
            service_value_averages_agendado[service] = round(total_value / count, 2) if count else 0

        # Cálculo de porcentagens
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

    # Validação da data
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Formato de data inválido."}), 400

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    # Obtenha todos os técnicos registrados no sistema
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
            # Buscar agendamentos na cidade para a data específica
            data_schedule = db.child("ordens_servico").child(city).child(year).child(month).child(day).get().val()
            if data_schedule:
                for order_id, order_data in data_schedule.items():
                    technician_id = order_data.get('tecnico_id')
                    
                    # Verifica se o técnico existe e acumula os dados
                    if technician_id in technician_schedules:
                        order_data['os_id'] = order_id
                        order_data['data'] = date_str
                        technician_schedules[technician_id].append(order_data)
                    else:
                        print(f"ID do técnico {technician_id} não encontrado em technicians.")
        
        # Substituir IDs pelo nome e retornar apenas técnicos com agendamentos
        formatted_schedules = {}
        for tech_id, schedules in technician_schedules.items():
            if schedules:  # Apenas incluir técnicos com agendamentos
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
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    index = data.get('index')
    city_name = data.get('city')

    if index is None or not city_name:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

    user_id = data.get('id')

    try:
        cities = db.child("users").child(user_id).child('cities').get().val()

        if not cities or not isinstance(cities, list):
            return jsonify({'success': False, 'error': 'Lista de cidades não encontrada ou inválida'}), 404

        if 0 <= index < len(cities) and cities[index] == city_name:
            cities.pop(index)
            db.child("users").child(user_id).update({"cities": cities})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Cidade não encontrada ou não corresponde ao índice'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user_add_city', methods=['POST'])
def user_add_city():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    city = data.get('city')
    user_id = data.get('id')

    if not city:
        return jsonify({'success': False, 'error': 'Cidade não fornecida'}), 400
    if not user_id:
        return jsonify({'success': False, 'error': 'ID do usuário não fornecido'}), 400

    try:
        cities = db.child("users").child(user_id).child('cities').get().val()

        if not cities:
            cities = []

        if city in cities:
            return jsonify({'success': False, 'error': 'Cidade já adicionada'}), 400

        cities.append(city)
        db.child("users").child(user_id).update({"cities": cities})

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/user_update_percentage', methods=['POST'])
def user_update_percentage():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    percentage = data.get('percentage')

    if not user_id or percentage is None:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"porcentagem": percentage})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user_update_tipo', methods=['POST'])
def user_update_tipo():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    role = data.get('role')

    if not user_id or role is None:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"role": role})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/user_update_cpf_cnpj', methods=['POST'])
def user_update_cpf_cnpj():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    cpf_cnpj = data.get('cpfcnpj')

    if not user_id or cpf_cnpj is None:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

    try:
        # Atualiza ou cria o campo 'percentage'
        db.child("users").child(user_id).update({"cpf_cnpj": cpf_cnpj})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/user_update_nome_relatorio', methods=['POST'])
def user_update_nome_relatorio():
    if 'user' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401

    data = request.get_json()
    user_id = data.get('id')
    nome_relatorio = data.get('nome_relatorio')

    if not user_id or nome_relatorio is None:
        return jsonify({'success': False, 'error': 'Dados inválidos'}), 400

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
        return jsonify({"error": "Formato de data inválido."}), 400

    year = str(date.year)
    month = f"{date.month:02d}"
    day = f"{date.day:02d}"

    try:
        print(data)
        db.child("ordens_servico").child(city).child(year).child(month).child(day).child(id_os).child("status_paymment").remove()

        db.child("wallet").child(city).child(year).child(month).child(day).child('transactions').child('pendding').child(id_transaction).remove()
       
    except Exception as e:
        return jsonify({'status': 'conflict', 'message': 'Erro ao cancelar a transação.'}), 400

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
        return jsonify({"erro": "Parâmetros incompletos"}), 400

    # 🔹 Converte as datas em objetos datetime
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(data_fim, "%Y-%m-%d")

    resultados = {}

    # 🔹 Loop sobre as datas
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
                                # Se ainda não está no cache, busca no servidor
                                if tecnico_id not in tecnicos_cache:
                                    tecnico_data = db.child("users").child(tecnico_id).child("name").get().val()
                                    tecnicos_cache[tecnico_id] = tecnico_data
                                # adiciona o nome do técnico ao item
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

    # Salvar PDF no Storage
    filename = f"relatorios/{int(time.time())}.pdf"
    storage.child(filename).put(pdf_file)
    pdf_url = storage.child(filename).get_url(None)

    # Identificar técnico logado
    tecnico_id = session.get("name")

    relatorio_data = {
        "pdf_url": pdf_url,
        "filename": filename,
        "tecnico": tecnico_id,
        "cliente": cliente,
        "timestamp": int(time.time())
    }

    # Salvar no Realtime Database
    relatorio_id = db.child("relatorios").push(relatorio_data)

    return jsonify({"status": "ok", "url": pdf_url})


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
            tecnico = item.get("tecnico", "Não informado")
            pdf_url = item.get("pdf_url") or item.get("url")  # compatível com versões antigas
            timestamp = item.get("timestamp", 0)

            lista.append({
                "id": key,
                "pdf_url": pdf_url,
                "tecnico": tecnico,
                "timestamp": timestamp,
                "cliente": {
                    "nome": cliente.get("nome", "Não informado"),
                    "cpf": cliente.get("cpf", "Não informado"),
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
    
    category = "Serviço"
    #especie_method = request.form.get('especie').title()
    especie = f'Remessa PIX'
    destinatario = "Central Vazamentos"
    
    lista_os = [item['numero_os'] for item in itens]
    lista_numeros_os = ", ".join(lista_os)
    #taxa = request.form.get('taxa')
    description = f'Pagamento referente às OSs: {lista_numeros_os}.'

    agora = datetime.now()
    
    Financeiro.post_transaction_credito_tecnico(date=agora, type=type, amount=amount, category=category, description=description, especie=especie, destinatario=destinatario, user=user, origem=origem, id_origem=id_origem)

    id_transaction = itens[0]['id_transaction']
    

     
    for item in itens:
        date = item['date_payment']
        print(date)
        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
                return "Formato de data inválido."
                
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

    tecnico_id = session.get("user")  # <-- Certifique-se que você salva o ID do técnico na sessão

    pendentes = {}
    data = db.child("financeiro").child("transactions_pendentes").get().val() or {}

    for ano, meses in data.items():
        for mes, dias in meses.items():
            for dia, transacoes in dias.items():
                for pendente_id, pendente in transacoes.items():
                    # FILTRA APENAS AS OS DO TÉCNICO LOGADO
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
            return "Formato de data inválido."
            
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
            return "Formato de data inválido."
            
    year_os = str(date.year)
    month_os = f"{date.month:02d}"
    day_os = f"{date.day:02d}"



    try:

        db.child("ordens_servico").child(city_os).child(year_os).child(month_os).child(day_os).child(id_os).child('status_paymment').remove()

        db.child("users").child(tecnico_id).child('wallet').child('cities').child(city_os).child(year).child(month).child(day).child('transactions').child('success').child(id_create_transaction_user).remove()

        db.child("wallet").child(city_os).child(year).child(month).child(day).child('transactions').child('success').child(id_create_transaction_wallet).remove()

        db.child("financeiro").child("transactions_pendentes").child(year).child(month).child(day).child(transaction_id).remove()

        print(f"ID da transação a ser deletada: {transaction_id}")
        print(f"Data de pagamento associada: {date_payment}")
        print(city_os)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5037)
