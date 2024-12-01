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
    "harga": 0.5,
    "kilometer": 0.5,
    "status_pajak": 0.5
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

    # Get basic search parameters
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

    # Build base query with filters
    query = Motor.query.filter(
        Motor.harga.between(harga_min, harga_max),
        Motor.kilometer.between(kilometer_min, kilometer_max),
        Motor.tahun.between(tahun_min, tahun_max)
    )

    if kapasitas_mesin != "Semua":
        query = query.filter(Motor.kapasitas_mesin == kapasitas_mesin)
    if brand != "Semua":
        query = query.filter(Motor.brand.ilike(f"{brand}%"))
    if model != "Semua":
        query = query.filter(Motor.model.ilike(f"{model}%"))
    if status_pajak != "Semua":
        query = query.filter(Motor.status_pajak.ilike(f"{status_pajak}%"))

    motors = query.all()
    
    # Check if weights are provided for recommendations
    has_weights = any(key in filters for key in ['weight_harga', 'weight_kilometer', 'weight_status_pajak'])
    
    if not has_weights:
        # Return basic search results
        return jsonify([{
            "id": motor.id,
            "harga": motor.harga,
            "kilometer": motor.kilometer,
            "tahun": motor.tahun,
            "model": motor.model,
            "brand": motor.brand,
            "kapasitas_mesin": motor.kapasitas_mesin,
            "status_pajak": motor.status_pajak,
            "gambar": motor.gambar
        } for motor in motors])

    # Process recommendations with weights
    weights = {
        "harga": float(filters.get('weight_harga', DEFAULT_WEIGHTS["harga"])),
        "kilometer": float(filters.get('weight_kilometer', DEFAULT_WEIGHTS["kilometer"])),
        "status_pajak": float(filters.get('weight_status_pajak', DEFAULT_WEIGHTS["status_pajak"]))
    }

    # Normalize weights
    total_weight = sum(weights.values())
    if total_weight != 0:
        weights = {k: v/total_weight for k, v in weights.items()}

    # Calculate model price ranges
    model_prices = {}
    models = db.session.query(Motor.model).distinct()
    for model in models:
        model_prices[model[0]] = {
            "harga_min": db.session.query(db.func.min(Motor.harga)).filter_by(model=model[0]).scalar(),
            "harga_max": db.session.query(db.func.max(Motor.harga)).filter_by(model=model[0]).scalar()
        }

    # Calculate fuzzy scores for each motor
    results = []
    for motor in motors:
        harga_min_db = model_prices[motor.model]["harga_min"]
        harga_max_db = model_prices[motor.model]["harga_max"]

        fuzzy_harga = calculate_fuzzy_score(motor.harga, harga_min_db, harga_max_db)
        fuzzy_kilometer = calculate_kilometer_fuzzy_score(motor.kilometer, motor.tahun)
        fuzzy_status_pajak = calculate_status_pajak_fuzzy_score(motor.status_pajak)

        results.append({
            "id": motor.id,
            "motor": motor.model,
            "harga": motor.harga,
            "tahun": motor.tahun,
            "gambar": motor.gambar,
            "kilometer": motor.kilometer,
            "status_pajak": motor.status_pajak,
            "brand": motor.brand,
            "kapasitas_mesin": motor.kapasitas_mesin,
            "fuzzy_harga": fuzzy_harga,
            "fuzzy_kilometer": fuzzy_kilometer,
            "fuzzy_status_pajak": fuzzy_status_pajak
        })

    if not results:
        return jsonify({
            "message": "Tidak ada motor yang memenuhi kriteria pencarian",
            "filters": {
                "harga": f"Rp {harga_min:,} - Rp {harga_max:,}",
                "tahun": f"{tahun_min} - {tahun_max}",
                "kilometer": f"{kilometer_min:,} - {kilometer_max:,} km"
            }
        })

    # Calculate SAW scores
    harga_normalized = calculate_saw_normalization(results, "fuzzy_harga")
    kilometer_normalized = calculate_saw_normalization(results, "fuzzy_kilometer")
    status_pajak_normalized = calculate_saw_normalization(results, "fuzzy_status_pajak")

    # Calculate final scores and sort
    for i, result in enumerate(results):
        saw_score = (
            weights["harga"] * harga_normalized[i] +
            weights["kilometer"] * kilometer_normalized[i] +
            weights["status_pajak"] * status_pajak_normalized[i]
        )
        result["saw_score"] = saw_score

    results.sort(key=lambda x: x["saw_score"], reverse=True)
    return jsonify(results)
