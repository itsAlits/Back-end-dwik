from extensions import db

class Motor(db.Model):
    __tablename__ = 'motor'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    brand = db.Column(db.String(255), nullable=False)
    model = db.Column(db.String(255), nullable=False)
    tahun = db.Column(db.Integer, nullable=False)
    kilometer = db.Column(db.Integer, nullable=False)
    kapasitas_mesin = db.Column(db.String(255), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    gambar = db.Column(db.String(255))
    status_pajak = db.Column(db.String(255), nullable=False)
