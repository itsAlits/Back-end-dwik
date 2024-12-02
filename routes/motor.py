from flask import Blueprint, request, jsonify
from models.motor import Motor, db
from utils.fuzzy_logic import (
    calculate_fuzzy_score,
    calculate_kilometer_fuzzy_score,
    calculate_status_pajak_fuzzy_score,
    calculate_saw_normalization
)
from routes.auth import login_required

motor_bp = Blueprint('motor', __name__)

# Default weights jika user tidak menentukan
DEFAULT_WEIGHTS = {
    "harga": 0.4,
    "kilometer": 0.3,
    "status_pajak": 0.3
}

@motor_bp.route('/motors', methods=['GET'])
def get_all_motors():
    motors = Motor.query.all()
    result_data = [{
        "id": motor.id,
        "harga": motor.harga,
        "kilometer": motor.kilometer,
        "tahun": motor.tahun,
        "model": motor.model,
        "brand": motor.brand,
        "kapasitas_mesin": motor.kapasitas_mesin,
        "status_pajak": motor.status_pajak,
        "gambar": motor.gambar
    } for motor in motors]
    return jsonify(result_data)

@motor_bp.route('/search', methods=['POST'])
def search():
    filters = request.json

    # Mengambil weights dari request dengan format weight_
    weight_harga = filters.get('weight_harga')
    weight_kilometer = filters.get('weight_kilometer')
    weight_status_pajak = filters.get('weight_status_pajak')
    
    print(weight_harga, weight_kilometer, weight_status_pajak)

    # Jika salah satu weight ada, berarti user mengirim custom weights
    if any([weight_harga, weight_kilometer, weight_status_pajak]):
        # Validasi semua weight harus ada
        if not all([weight_harga, weight_kilometer, weight_status_pajak]):
            missing_weights = []
            if not weight_harga: missing_weights.append("weight_harga")
            if not weight_kilometer: missing_weights.append("weight_kilometer")
            if not weight_status_pajak: missing_weights.append("weight_status_pajak")
            return jsonify({
                "error": f"Weight tidak lengkap. Komponen yang kurang: {', '.join(missing_weights)}"
            }), 400

        # Membuat dictionary weights
        user_weights = {
            "harga": float(weight_harga),
            "kilometer": float(weight_kilometer),
            "status_pajak": float(weight_status_pajak)
        }
        
        # Validasi nilai weight (0-1)
        invalid_weights = [k for k, v in user_weights.items() 
                         if not isinstance(v, (int, float)) or v < 0 or v > 1]
        if invalid_weights:
            return jsonify({
                "error": f"Weight tidak valid untuk: {', '.join(invalid_weights)}. Nilai harus antara 0 dan 1"
            }), 400
        
        # Validasi total weight = 1
        total_weight = sum(user_weights.values())
        if not (0.99 <= total_weight <= 1.01):
            return jsonify({
                "error": f"Total weight harus 1, sekarang: {total_weight:.2f}"
            }), 400
        
        weights = user_weights
    else:
        weights = DEFAULT_WEIGHTS

    # Nilai default untuk filter
    harga_min = int(filters.get('harga_min', 0) or 0)
    harga_max = int(filters.get('harga_max', 1000000000) or 1000000000)
    kilometer_min = int(filters.get('kilometer_min', 0) or 0)
    kilometer_max = int(filters.get('kilometer_max', 1000000) or 1000000)
    tahun_min = int(filters.get('tahun_min', 0) or 0)
    tahun_max = int(filters.get('tahun_max', 2024) or 2024)
    kapasitas_mesin = filters.get('kapasitas_mesin', "Semua")
    brand = filters.get('brand', "Semua")
    model = filters.get('model', "Semua")
    status_pajak = filters.get('status_pajak', "Semua") 

    # Query database dengan filter
    query = Motor.query.filter(
        Motor.harga.between(harga_min, harga_max),
        Motor.kilometer.between(kilometer_min, kilometer_max),
        Motor.tahun.between(tahun_min, tahun_max)
    )

    # Menambahkan filter tambahan berdasarkan input pengguna
    if kapasitas_mesin != "Semua":
        query = query.filter(Motor.kapasitas_mesin == kapasitas_mesin)
    if brand != "Semua":
        query = query.filter(Motor.brand.ilike(f"%{brand}%"))
    if model != "Semua":
        query = query.filter(Motor.model.ilike(f"%{model}%"))
    if status_pajak != "Semua":
        query = query.filter(Motor.status_pajak.ilike(f"{status_pajak}%"))

    # Menjalankan query dan mengambil hasil
    filtered_motors = query.all()

    # Proses rekomendasi untuk motor yang telah difilter
    results = []
    
    # Kumpulkan harga_min dan harga_max untuk setiap model motor yang telah difilter
    model_prices = {}
    filtered_models = set(motor.model for motor in filtered_motors)
    for model in filtered_models:
        model_prices[model] = {
            "harga_min": db.session.query(db.func.min(Motor.harga)).filter_by(model=model).scalar(),
            "harga_max": db.session.query(db.func.max(Motor.harga)).filter_by(model=model).scalar()
        }

    # Proses fuzzy dan SAW untuk motor yang telah difilter
    for motor in filtered_motors:
        harga_min_db = model_prices[motor.model]["harga_min"]
        harga_max_db = model_prices[motor.model]["harga_max"]

        # Menghitung nilai fuzzy untuk setiap kriteria
        fuzzy_harga = calculate_fuzzy_score(motor.harga, harga_min_db, harga_max_db)
        fuzzy_kilometer = calculate_kilometer_fuzzy_score(motor.kilometer, motor.tahun)
        fuzzy_status_pajak = calculate_status_pajak_fuzzy_score(motor.status_pajak)

        results.append({
            "id": motor.id,
            "harga": motor.harga,
            "kilometer": motor.kilometer,
            "tahun": motor.tahun,
            "model": motor.model,
            "brand": motor.brand,
            "kapasitas_mesin": motor.kapasitas_mesin,
            "status_pajak": motor.status_pajak,
            "gambar": motor.gambar,
            "fuzzy_harga": fuzzy_harga,
            "fuzzy_kilometer": fuzzy_kilometer,
            "fuzzy_status_pajak": fuzzy_status_pajak
        })

    if results:
        # Normalisasi nilai untuk setiap kriteria
        harga_normalized = calculate_saw_normalization(results, "fuzzy_harga")
        kilometer_normalized = calculate_saw_normalization(results, "fuzzy_kilometer")
        status_pajak_normalized = calculate_saw_normalization(results, "fuzzy_status_pajak")

        # Menghitung skor SAW
        for i, result in enumerate(results):
            result['saw_score'] = (
                weights["harga"] * harga_normalized[i] +
                weights["kilometer"] * kilometer_normalized[i] +
                weights["status_pajak"] * status_pajak_normalized[i]
            )

        # Mengurutkan hasil berdasarkan skor SAW
        results.sort(key=lambda x: x['saw_score'], reverse=True)

    return jsonify(results)
