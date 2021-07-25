import os
from flask import request
from flask_cors import cross_origin
import smtplib
import random
import jwt
import datetime
from functools import wraps
from api import flaskApp
from api.model.Usuario import *
from api.model.Comentario import *
from api.model.Notificacoes import *
from api.model.Postagem import *
from api.model.Formulario_Socioeconomico import *

app = flaskApp.app

def token_required(f):
   @wraps(f)
   def decorator(*args, **kwargs):
        token = None
        try:
            token = request.headers['Authorization'].split("Bearer ")[1]
        except:
            return {'message': 'a valid token is missing'}

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], issuer=os.environ.get('ME', 'plasmedis-api-local'), algorithms=["HS256"], options={"require": ["exp", "sub", "iss", "aud"], "verify_aud": False, "verify_iat": False, "verify_nbf": False})
        except jwt.exceptions.InvalidKeyError:
            return {'message': 'Secret Key is not in the proper format'}
        except jwt.exceptions.InvalidAlgorithmError:
            return {'message': 'Algorithm is not recognized by PyJWT'}
        except jwt.exceptions.ExpiredSignatureError:
            return {'message': 'Token is expired'}
        except jwt.exceptions.InvalidIssuerError:
            return {'message': 'Token has a different issuer'}
        except jwt.exceptions.MissingRequiredClaimError:
            return {'message': 'Token is missing a required claim'}
        except jwt.exceptions.DecodeError:
            return {'message': 'Token failed validation'}
        except Exception as ex:
            return {'message': 'There was a error decoding the token'}

        return f(*args, **kwargs)
   return decorator

def toDict(user: Usuario):
    return {
        "id": user.id,
        "real_name": user.real_name,
        "verificado": user.verificado,
        "user_name": user.user_name,
        "user_type": user.user_type,
        "email": user.email
    }

@app.route('/')
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def hello():
	return "This API Works! [" + os.environ.get("ENV", "DEV") + "]"

@app.route('/users/<id>/notificacoes_conf', methods=['PUT', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def handle_user_notificacao(id):
    user_not = Notificacoes_Conf.query.filter_by(usuario=id).first()

    if request.method == 'GET':
        response = {
            "sistema":user_not.sistema,
            "selo_postagem":user_not.selo_postagem,
            "comentario_postagem":user_not.comentario_postagem,
            "saude":user_not.saude,
            "lazer":user_not.lazer,
            "trocas":user_not.trocas
        }
        return {"message": "success", "user_not": response}
    elif request.method == 'PUT':
        data = request.get_json()
        user_not.sistema = data['sistema']
        user_not.selo_postagem = data['selo_postagem']
        user_not.comentario_postagem = data['comentario_postagem']
        user_not.saude = data['saude']
        user_not.lazer = data['lazer']
        user_not.trocas = data['trocas']
        db.session.add(user_not)
        db.session.commit()
        return {"message": f"Configurações de notificação atualizadas"}



@app.route('/form_socio/<id>', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def form_socio(id):
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_form = Form_Socioeconomico(nome_rep_familia=data['nome_rep_familia'], pessoa=data['pessoa'], qtd_pessoas_familia=data['qtd_pessoas_familia'],
            pessoa_amamenta=data['pessoa_amamenta'], qtd_criancas=data['qtd_criancas'], gestante=data['gestante'], qtd_amamentando=data['qtd_amamentando'], qtd_criancas_deficiencia=data['qtd_criancas_deficiencia'], qtd_gestantes=data['qtd_gestantes'])
            db.session.add(new_form)
            db.session.commit()

            return {"message": f"Formulário enviado!"}
        else:
            return {"error": "O envio não foi feita no formato esperado"}

    elif request.method == 'GET':
        forms = Form_Socioeconomico.query.filter_by(pessoa=id).all()
        results = []
        for form in forms:
            if form.preenchido:
                results.append({
                    "preenchido": form.preenchido,
                    "nome_rep": form.nome_rep_familia,
                    "qtd_pessoas": form.qtd_pessoas_familia,
                    "qtd_criancas": form.qtd_criancas,
                    "gestante": form.gestante,
                    "qtd_amamentando": form.qtd_amamentando,
                    "qtd_criancas_deficiencia": form.qtd_criancas_deficiencia,
                    "pessoa_amamenta": form.pessoa_amamenta,
                    "qtd_gestantes": form.qtd_gestantes
                })

        return {"count": len(results), "users": results}

@app.route('/users', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def users():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_user = Usuario(real_name=data['real_name'], password=data['password'], user_name=data['user_name'], user_type=data['user_type'], bairro=data['bairro'])
            if "email" in data:
                new_user.email = data['email']
            db.session.add(new_user)
            db.session.commit()
            
            new_user = Usuario.query.filter_by(user_name=data['user_name'],real_name=data['real_name']).first()
            new_user_not = Notificacoes_Conf(usuario=new_user.id, sistema=False, selo_postagem=False, comentario_postagem=False, saude=False, lazer=False, trocas=False)
            db.session.add(new_user_not)
            db.session.commit()

            return {"message": f"Usuario criado", "user": new_user.id}
        else:
            return {"error": "A requisição não foi feita no formato esperado"}

    elif request.method == 'GET':
        users = Usuario.query.all()
        results = [
            {
                "user_name": user.user_name,
                "email": user.email
            } for user in users]

        return {"count": len(results), "users": results, "message": "success"}

@app.route('/login', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def login():
    AUTH_VERSION = os.environ.get("AUTH_VERSION", 0.2)

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            user = Usuario.query.filter_by(user_name=data['username']).first()
            if user is None:
                user = Usuario.query.filter_by(email=data['username']).first()
            if user:
                if user.password == data['password']:
                    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=7)
                    issuedAt = datetime.datetime.utcnow()
                    token = jwt.encode({'auth': AUTH_VERSION, 'exp': expiration, 'iat': issuedAt, 'sub': user.id, 'iss': os.environ.get('ME', 'plasmedis-api-local'), 'aud': request.args.get('aud', 'unknown')}, app.config['SECRET_KEY'], algorithm="HS256")
                    return {"status": 1000, "user": toDict(user), "token": token, "verificado": str(user.verificado)} #Valido
                else:
                    return {"status": 1010} #Invalido
            else:
                return {"status": 1010} #Invalido
        else:
            return {"error": "A requisição não foi feita no formato esperado"}
    elif request.method == 'GET':
        # retorna um marcador de versão, para quando as mudanças no token forem tão significativas que o único
        # jeito de atualizar algo no front vai ser matando a sessão atual do usuário
        return {'version': AUTH_VERSION}



@app.route('/privileges', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def privileges():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_privilege = Privilegio(user_type=data['user_type'])

            db.session.add(new_privilege)
            db.session.commit()

            return {"message": f"Privilégio criado com sucesso"}
        else:
            return {"error": "A requisição não foi feita no formato esperado"}

    elif request.method == 'GET':
        privileges = Privilegio.query.all()
        results = [
            {
                "user_type": privilege.user_type
            } for privilege in privileges]

        return {"count": len(results), "Privileges": results, "message": "success"}

@app.route('/bairros', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def bairros():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_bairro = Bairro(nome=data['nome'])

            db.session.add(new_bairro)
            db.session.commit()

            return {"message": f"Privilégio criado com sucesso"}
        else:
            return {"error": "A requisição não foi feita no formato esperado"}

    elif request.method == 'GET':
        bairros = Bairro.query.all()
        results = [
            {
                "nome": bairro.nome,
                "id": bairro.id
            } for bairro in bairros]

        return {"count": len(results), "Bairros": results, "message": "success"}

@app.route('/categorias', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def categorias():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_categoria = Categoria(nome=data['nome'])

            db.session.add(new_categoria)
            db.session.commit()

            return {"message": f"Categoria criado com sucesso"}
        else:
            return {"error": "A requisição não foi feita no formato esperado"}

    elif request.method == 'GET':
        categorias = Categoria.query.all()
        results = [
            {
                "nome": categoria.nome,
                "id": categoria.id
            } for categoria in categorias]

        return {"count": len(results), "Categorias": results, "message": "success"}

@app.route('/users/<id>', methods=['GET', 'PUT', 'DELETE'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def handle_user(id):
    user = Usuario.query.get_or_404(id)

    if request.method == 'GET':
        response = {
            "email": user.email,
            "privilegio": user.user_type,
            "nome": user.real_name,
            "sexo": user.sexo,
            "nascimento": user.nascimento,
            "cor": user.cor,
            "telefone": user.telefone,
            "rua": user.rua,
            "numero_casa": user.numero_casa
        }
        return {"message": "success", "user": response}

    elif request.method == 'PUT':
        data = request.get_json()
        #user.email = data['email']
        #user.real_name = data['real_name']
        #user.password = data['password']
        user.verificado = True
        user.sexo = data['sexo']
        user.nascimento = data['nascimento']
        user.cor = data['cor']
        user.telefone = data['telefone']
        user.rua = data['rua']
        user.numero_casa = data['numero_casa']

        db.session.add(user)
        db.session.commit()

        return {"message": f"Dados de {user.user_name} atualizados"}

    elif request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()

        return {"message": f"Dados de {user.user_name} removidos"}

@app.route('/selo/<id>', methods=['PUT'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def selo(id):
    postagem = Postagem.query.get_or_404(id)
    if request.method == 'PUT':
        data = request.get_json()
        postagem.selo = True

        db.session.add(postagem)
        db.session.commit()

        return {"message": f"Selo emitido!"}

@app.route('/postagens', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def postagens():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_post = Postagem(texto=data['texto'], criador=data['criador'], titulo=data['titulo'], categoria=data['categoria'])

            db.session.add(new_post)
            db.session.commit()

            return {"message": f"Postagem criada"}
        else:
            return {"error": "A requisição não está no formato esperado"}
    elif request.method == 'GET':
        postagensWithCriador = Postagem.query.join(Usuario, Postagem.criador == Usuario.id, isouter=True).add_columns(Usuario.real_name, Usuario.bairro)

        # filtros gerais
        bairro = request.args.get('bairro', None)
        categoria = request.args.get('categoria', None)

        if categoria is not None:
            postagensWithCriador = postagensWithCriador.filter(Postagem.categoria.in_(map(int, categoria.split(','))))

        if bairro is not None:
            postagensWithCriador = postagensWithCriador.filter(Usuario.bairro.in_(map(int, bairro.split(','))))

        postagens = postagensWithCriador.all()
        results = []
        for post in postagens:
            results.append({"id": post.Postagem.id, "titulo": post.Postagem.titulo,"texto": post.Postagem.texto,"criador": post.real_name,"bairro": post.bairro,"selo":post.Postagem.selo,"categoria":post.Postagem.categoria,"data":post.Postagem.data})

        return {"count": len(results), "post": results, "message": "success"}

@app.route('/recomendados', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def recomendados():
    if request.method == 'GET':
        postagens = Postagem.query.filter_by(selo=True).all()
        results = []
        for post in postagens:
            user = Usuario.query.get_or_404(post.criador)
            results.append({"id": post.id, "titulo": post.titulo,"texto": post.texto,"criador": user.real_name,"selo":post.selo,"categoria":post.categoria})

        return {"count": len(results), "post": results, "message": "success"}

@app.route('/postagens/categorias/<id_categoria>', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def filtros(id_categoria):
    postagens = Postagem.query.join(Categoria, id_categoria == Postagem.categoria)
    print(postagens)
    results = []
    for post in postagens:
        user = Usuario.query.get_or_404(post.criador)
        results.append({"id": post.id, "titulo": post.titulo,"texto": post.texto,"criador": user.real_name,"selo":post.selo,"categoria":post.categoria, "data": post.data})

    return {"count": len(results), "post": results, "message": "success"}

@app.route('/postagens/<id>', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def postagensId(id):
    post = Postagem.query.filter_by(id=id).first()
    #TODO: Criar uma estrutura com 'services' com funções para facilitar a vida (e evitar ter que fazer encode decode do json)
    import json
    comments = comentarios_postagem(post.id).response[0].decode('utf-8')
    comments = json.loads(comments)
    post_user = Usuario.query.get_or_404(id)
    result = {
        "id": post.id,
        "titulo": post.titulo,
        "texto": post.texto,
        "criador": {
            "id": post_user.id,
            "name": post_user.real_name
        },
        "selo":post.selo,
        "categoria":post.categoria,
        "data": post.data,
        "comentarios": comments['comments']
    }
    return result

@app.route('/lista_postagens/<id>', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def lista_postagens(id):
    if request.method == 'GET':
        try :
            postagens = Postagem.query.all()
            user = Usuario.query.get_or_404(id)
            results = []
            for post in postagens:
                if post.criador == user.id:
                    results.append({"titulo": post.titulo,"texto": post.texto,"criador": user.real_name})

            return {"count": len(results), "post": results, "message": "success"}
        except:
            return {"error": 404, "message": "Usuário não encontrado"}

@app.route('/comentarios', methods=['POST', 'GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def comentarios():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_comment = Comentario(texto=data['texto'], criador=data['criador'], resposta=data['resposta'], postagem=data["postagem"])

            db.session.add(new_comment)
            db.session.commit()

            return {"message": f"Comentário registrado"}
        else:
            return {"error": "A requisição não está no formato esperado"}

    elif request.method == 'GET':
        comments = Comentario.query.all()
        results = [
            {
                "texto": comment.texto,
                "criador": comment.criador,
                "postagem": comment.postagem,
                "resposta": comment.resposta,
                "data": comment.data
            } for comment in comments]

        return {"count": len(results), "comments": results, "message": "success"}

@app.route('/comentarios/<postagem_id>', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def comentarios_postagem(postagem_id):
    if request.method == 'GET':
        comments = Comentario.query.filter_by(postagem=postagem_id).all()
        users_id = [ comment.criador for comment in comments ]
        users = Usuario.query.filter(Usuario.id.in_(users_id)).all()
        results = [
        {
            "texto": comment.texto,
            "criador":
                {
                    "id": comment.criador,
                    "name": next(filter(lambda user: user.id == comment.criador, users)).real_name
                },
            "resposta": comment.resposta,
            "data": comment.data
        } for comment in comments]
        return {"user": 1,"count": len(results), "comments": results, "message": "success"}


@app.route('/esqueci_senha', methods=['Get', 'Post'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def esqueci_senha():
     if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            usuario = data["id"]
            usuario = int(usuario)
            row = Usuario.query.filter_by(id=usuario).one()

            #Conecta e inicia o serviço de email
            smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
            res = smtpObj.starttls()

            #Criei essa conta para mandar o email
            smtpObj.login('codelabtesteesquecisenha@gmail.com', '44D6DDAAC9C660F72D6490D7CC44731BEA7C236A9241B387D3E9AF0C66B30D49')

            #Gera uma hash que servirá como senha temporaria
            hash = str(random.getrandbits(128))
            email =  row.email
            row.password = hash
            db.session.add(row)
            db.session.commit()
            msg = "\n\nSua nova senha e " +hash
            smtpObj.sendmail('codelabtesteesquecisenha@gmail.com',email,  msg )

            return("A senha temporaria foi enviada para o email " + row.email)

        else:
            return {"error": "A requisição não está no formato esperado"}

@app.route('/users/username/verify/<username>', methods=['GET'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@token_required
def verify_username(username):
    user = Usuario.query.filter_by(user_name=username).first()
    if user:
        return { "success": False, "message": "User with username '" + str(username) + "' already exists." }
    else:
        return { "success": True, "message": "Username '" + str(username) + "' is available."}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)