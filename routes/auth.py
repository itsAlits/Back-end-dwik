from flask import Blueprint, request, jsonify
from models.user import User, db
import jwt
import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = "RAHASIAA"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'message': 'Token tidak diberikan'}), 401

        try:
            # Remove 'Bearer ' prefix if present
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
            decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = decoded_token.get('user_id')
            
            current_user = User.query.get(user_id)
            if current_user is None:
                return jsonify({'message': 'Pengguna tidak ditemukan'}), 401

            return f(current_user, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token telah kedaluwarsa'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid'}), 401
        except Exception as e:
            return jsonify({'message': f'Error: {str(e)}'}), 401

    return decorated_function

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({'message': 'Username atau password salah'}), 401

    token = jwt.encode(
        {
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        },
        SECRET_KEY,
        algorithm='HS256'
    )

    return jsonify({'token': token}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Semua field harus diisi'}), 400

    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        return jsonify({'message': 'Username atau email sudah terdaftar'}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Registrasi berhasil!'}), 201

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user(current_user):
    # current_user sudah tersedia dari decorator login_required
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    })

@auth_bp.route('/user/<int:user_id>', methods=['GET'])
@login_required
def get_user(current_user, user_id):
    # Memastikan user hanya bisa mengakses data dirinya sendiri
    if current_user.id != user_id:
        return jsonify({'message': 'Tidak diizinkan mengakses data user lain'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User tidak ditemukan'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    })
