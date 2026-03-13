from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessao'

import os

# Isso descobre automaticamente a pasta onde o app.py está guardado
base_dir = os.path.abspath(os.path.dirname(__file__))

# Isso cria o link perfeito para o banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'hospital.db')
db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

class Paciente(db.Model):#essa classe estava mais simples antes mas eu a subistitui por uma que fara o código calculara a idade dos pacientes pela data de nascimento 
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True) # Verifique se está 'cpf' minúsculo
    data_nascimento = db.Column(db.Date) # Mudamos de Integer para Date
    comorbidades = db.Column(db.Text)
    medicamentos = db.Column(db.Text)
    operacoes = db.Column(db.Text)
    nova_consulta = db.relationship('Consulta', backref='paciente', lazy=True)#isso liga o campo Hitórico a classe colsulta


    # Esta função calcula a idade automaticamente
    def calcular_idade(self):
        if self.data_nascimento:
            hoje = datetime.today()
            return hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
        return 

class Consulta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Verifique se escreveu data_consulta (correto) e não data_counsulta
    data_consulta = db.Column(db.DateTime, default=datetime.utcnow) 
    informacoes = db.Column(db.Text, nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)

with app.app_context():
    db.create_all()

def criar_admin_inicial(): #cria um usuario mestre, um usuario que sempre existira e tera acesso a todas a funções
    if Usuario.query.first() is None:
        login_messtre = "admin"
        senha_mestre = "FEEU$2026createall"
        senha_hash = generate_password_hash(senha_mestre)
        novo_admin = Usuario(login=login_messtre, senha=senha_hash)
        db.session.add(novo_admin)
        db.session.commit()
        print("Usuario mestre criado com susseso")

with app.app_context():
    db.create_all()
    criar_admin_inicial()

class LoteMedicamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_remedio = db.Column(db.String(100), nullable=False)
    numero_lote = db.Column(db.String(50), nullable=False)
    quantidade_inicial = db.Column(db.Integer, nullable=False)
    quantidade_atual = db.Column(db.Integer, nullable=False)
    validade = db.Column(db.Date, nullable=False)
    # Relacionamento para ver quem pegou os remédios deste lote
    movimentacoes = db.relationship('MovimentacaoEstoque', backref='lote', lazy=True)


class MovimentacaoEstoque(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lote_medicamento.id'), nullable=False)
    paciente_nome = db.Column(db.String(100), nullable=False) # Nome de quem recebeu
    quantidade_saida = db.Column(db.Integer, nullable=False)
    data_entrega = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/inventario')
def inventario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    lotes = LoteMedicamento.query.all()
    return render_template('inventario.html', lotes=lotes)

@app.route('/', methods=['GET', 'POST'])#e a primeira página do site e também e a página de login
def login():
    if request.method == 'POST':
        login_digitado = request.form.get('login')
        senha_digitada = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(login=login_digitado).first()
        
        if usuario and check_password_hash(usuario.senha, senha_digitada):
            session['usuario_id'] = usuario.id
            return redirect(url_for('lista_pacientes'))
        
        return "Login ou senha incorretos"
    
    return render_template('login.html')

@app.route('/pacientes')#página com a lista de pacientes
def lista_pacientes():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    busca = request.args.get('q', '')
    
    if busca:
        termo = f"%{busca}%"
        pacientes = Paciente.query.filter(
            or_(
                Paciente.nome.ilike(termo),
                Paciente.medicamentos.ilike(termo),
                Paciente.comorbidades.ilike(termo)
            )
        ).order_by(Paciente.nome).all()
    else:
        pacientes = Paciente.query.order_by(Paciente.nome).all()
        
    return render_template('lista.html', pacientes=pacientes, busca=busca, total=len(pacientes))

@app.route('/paciente/<int:id>')#ordena as informaoes sobre consultas por data 
def detalhes_paciente(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    p = Paciente.query.get_or_404(id)
    # Use data_consulta aqui também
    consultas = Consulta.query.filter_by(paciente_id=id).order_by(Consulta.data_consulta.desc()).all()
    
    return render_template('detalhes.html', paciente=p, historico_consultas=consultas)

@app.route('/cadastrar', methods=['GET', 'POST'])#serve para cadastrar novos pacientes no sisteme. Esse app fou alterado para poder calcular a idade pela data de nascimento
def cadastrar_paciente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Convertemos a string que vem do HTML em um objeto de data do Python
        data_str = request.form.get('data_nascimento')
        data_dt = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None

        novo_p = Paciente(
            nome=request.form.get('nome'),
            cpf=request.form.get('cpf'),
            data_nascimento=data_dt, # Salvando a data
            comorbidades=request.form.get('comorbidades'),
            medicamentos=request.form.get('medicamentos'),
            operacoes=request.form.get('operacoes')
        )
        db.session.add(novo_p)
        db.session.commit()
        return redirect(url_for('lista_pacientes'))
        
    return render_template('cadastrar.html')

@app.route('/paciente/<int:id>/nova_consulta', methods=['POST'])#serve para adicionar informação de nova consulta no banco de dados
def nova_consulta(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Pegamos o texto do formulário
    texto = request.form.get('informacoes')
    
    if texto:
        # Criamos a consulta garantindo que o paciente_id seja o 'id' da rota
        nova = Consulta(informacoes=texto, paciente_id=id)
        db.session.add(nova)
        db.session.commit()
        print(f"DEBUG: Consulta salva para o paciente {id}") # Isso aparecerá no seu terminal
    
    return redirect(url_for('detalhes_paciente', id=id))

@app.route('/excluir/<int:id>')#esse app serve para o úsuario poder excluir itens da lista paciente se ele quiser, isso pelo site
def excluir_paciente(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    paciente = Paciente.query.get_or_404(id)
    db.session.delete(paciente)
    db.session.commit() # Confirma a exclusão no arquivo hospital.db
    return redirect(url_for('lista_pacientes'))

@app.route('/cadastrar_lote', methods=['GET', 'POST'])#redireciona a página de cadastrar lote
def cadastrar_lote():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Pegamos a data e convertemos para o formato que o banco entende
        val_str = request.form.get('validade')
        val_dt = datetime.strptime(val_str, '%Y-%m-%d').date() if val_str else None
        
        quantidade = int(request.form.get('quantidade'))
        
        novo_lote = LoteMedicamento(
            nome_remedio=request.form.get('nome_remedio'),
            numero_lote=request.form.get('numero_lote'),
            quantidade_inicial=quantidade,
            quantidade_atual=quantidade, # No cadastro, a atual é igual a inicial
            validade=val_dt
        )
        db.session.add(novo_lote)
        db.session.commit()
        return redirect(url_for('inventario'))
        
    return render_template('cadastrar_lote.html')

@app.route('/inventario/lote/<int:id>')#essa rota e a de baixo são para as páinas individuais com detalhes de informações sobre os lotes da fármacia
def detalhes_lote(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Busca o lote específico pelo ID
    lote = LoteMedicamento.query.get_or_404(id)
    return render_template('detalhes_lote.html', lote=lote)

@app.route('/inventario/lote/<int:id>/saida', methods=['POST'])
def registrar_saida(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    lote = LoteMedicamento.query.get_or_404(id)
    paciente_nome = request.form.get('paciente_nome')
    qtd_saida = int(request.form.get('quantidade_saida'))

    # Verifica se tem remédio suficiente no estoque
    if qtd_saida <= lote.quantidade_atual:
        # Diminui a quantidade do lote
        lote.quantidade_atual -= qtd_saida
        
        # Cria o registro de quem pegou
        nova_mov = MovimentacaoEstoque(
            lote_id=lote.id,
            paciente_nome=paciente_nome,
            quantidade_saida=qtd_saida
        )
        
        db.session.add(nova_mov)
        db.session.commit()
        return redirect(url_for('detalhes_lote', id=id))
    else:
        return "Erro: Quantidade insuficiente em estoque!", 400
    
@app.route('/usuarios', methods=['GET', 'POST'])
def gerenciar_usuarios():
    # Segurança: Apenas o admin pode acessar esta página
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario_logado = Usuario.query.get(session['usuario_id'])
    if usuario_logado.login != 'admin':
        return "Acesso negado! Apenas o administrador mestre pode criar usuários.", 403

    if request.method == 'POST':
        novo_login = request.form.get('login')
        nova_senha = request.form.get('senha')
        
        # Verifica se o login já existe
        if Usuario.query.filter_by(login=novo_login).first():
            return "Este nome de usuário já existe!", 400
            
        # Cria o novo usuário com senha protegida (hash)
        senha_protegida = generate_password_hash(nova_senha)
        novo_usuario = Usuario(login=novo_login, senha=senha_protegida)
        
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('gerenciar_usuarios'))

    todos_usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=todos_usuarios)

@app.route('/excluir_usuario/<int:id>')
def excluir_usuario(id):
    # Segurança: Apenas o admin mestre pode excluir
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    usuario_logado = Usuario.query.get(session['usuario_id'])
    if usuario_logado.login != 'admin':
        return "Acesso negado!", 403

    usuario_para_excluir = Usuario.query.get_or_404(id)

    # Impede que o admin mestre seja excluído
    if usuario_para_excluir.login == 'admin':
        return "O usuário mestre não pode ser excluído!", 400

    db.session.delete(usuario_para_excluir)
    db.session.commit()
    return redirect(url_for('gerenciar_usuarios'))

if __name__ =='__main__':
    app.run(debug=True)