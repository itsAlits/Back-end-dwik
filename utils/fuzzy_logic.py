# Fungsi untuk menghitung fuzzy score harga
def calculate_fuzzy_score(harga, harga_min, harga_max):
    if harga <= harga_min + 0.2 * (harga_max - harga_min):
        return 1  # Sangat Bagus
    elif harga <= harga_min + 0.4 * (harga_max - harga_min):
        return 0.8  # Bagus
    elif harga <= harga_min + 0.6 * (harga_max - harga_min):
        return 0.6  # Normal
    elif harga <= harga_min + 0.8 * (harga_max - harga_min):
        return 0.4  # Kurang
    else:
        return 0.2  # Sangat Kurang

def calculate_kilometer_fuzzy_score(kilometer, tahun_pembuatan, tahun_sekarang=2024):
    tahun_selisih = tahun_sekarang - tahun_pembuatan
    nilai_normal = tahun_selisih * 10000  # Normal per tahun

    if kilometer <= nilai_normal - 10000:
        return 1  # Sangat Bagus
    elif kilometer < nilai_normal:
        return 0.8  # Bagus
    elif kilometer == nilai_normal:
        return 0.6  # Normal
    elif kilometer < nilai_normal + 10000:
        return 0.4  # Kurang
    else:
        return 0.2  # Sangat Kurang

def calculate_status_pajak_fuzzy_score(status_pajak):
    if "Tidak Aktif ≥ 3 tahun" in status_pajak:
        return 0.2  # Sangat Kurang
    elif "Tidak Aktif 2 tahun sampai < 3 tahun" in status_pajak:
        return 0.4  # Kurang   
    elif "Tidak Aktif 1 tahun sampai < 2 tahun" in status_pajak:
        return 0.6  # Normal
    elif "Tidak Aktif < 1 tahun" in status_pajak:
        return 0.8  # Bagus
    elif "Aktif" in status_pajak:
        return 1  # Sangat Bagus

def calculate_saw_normalization(data, key):
    values = [item[key] for item in data]
    max_value = max(values)
    
    normalized_values = []
    for value in values:
        normalized_values.append(value / max_value if max_value != 0 else 0)
    
    return normalized_values
