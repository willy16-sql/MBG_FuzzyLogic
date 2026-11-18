"""
tsukamoto_mbg.py  (versi 2: output = faktor produksi)
=====================================================
Fuzzy Inference System (FIS) metode Tsukamoto.
Kasus : penentuan jumlah porsi MBG yang dimasak dapur (SPPG) per hari.

Input : P = penerima manfaat hari ini   (SEDIKIT, BANYAK)
        S = sisa porsi kemarin          (SEDIKIT, BANYAK)
        B = ketersediaan bahan baku (%) (TERBATAS, MEMADAI)
Output: F = faktor produksi             (BERKURANG, BERTAMBAH)
        Porsi dimasak = F x P

Faktor produksi F berada di rentang 1,00 sampai 1,15:
    F = 1,00 -> memasak tepat sebanyak penerima (tanpa cadangan)
    F = 1,15 -> memasak penerima + cadangan 15%
Dengan begitu porsi tidak pernah di bawah jumlah penerima, dan hasilnya
selalu proporsional terhadap P (tidak lagi memakai semesta output tetap).

3 input x 2 himpunan = 2 x 2 x 2 = 8 aturan.
Catatan: simulasi akademik, bukan penilaian terhadap programnya.

Jalankan file ini langsung untuk melihat contoh hitungan manual:
    python tsukamoto_mbg.py
"""

# ---------------------------------------------------------------
# 1. Semesta pembicaraan
# ---------------------------------------------------------------
P_MIN, P_MAX = 1000, 3000     # penerima manfaat (orang)
S_MIN, S_MAX = 0, 300         # sisa porsi kemarin
B_MIN, B_MAX = 40, 100        # ketersediaan bahan baku (% dari kebutuhan)
F_MIN, F_MAX = 1.00, 1.15     # faktor produksi (porsi dimasak / penerima)


# ---------------------------------------------------------------
# 2. Fungsi keanggotaan linear
# ---------------------------------------------------------------
def turun(x, a, b):
    """Garis turun: derajat 1 jika x <= a, 0 jika x >= b."""
    if x <= a:
        return 1.0
    if x >= b:
        return 0.0
    return (b - x) / (b - a)


def naik(x, a, b):
    """Garis naik: derajat 0 jika x <= a, 1 jika x >= b."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return (x - a) / (b - a)


# Konfigurasi variabel: (label_turun, label_naik, batas_bawah, batas_atas)
VARIABEL = {
    "P": ("SEDIKIT", "BANYAK", P_MIN, P_MAX),
    "S": ("SEDIKIT", "BANYAK", S_MIN, S_MAX),
    "B": ("TERBATAS", "MEMADAI", B_MIN, B_MAX),
    "F": ("BERKURANG", "BERTAMBAH", F_MIN, F_MAX),
}


def derajat(kode, label, x):
    """Derajat keanggotaan x pada himpunan `label` milik variabel `kode`."""
    lab_turun, _, a, b = VARIABEL[kode]
    return turun(x, a, b) if label == lab_turun else naik(x, a, b)


# ---------------------------------------------------------------
# 3. Fuzzifikasi
# ---------------------------------------------------------------
def fuzzifikasi(p, s, b):
    """Ubah angka crisp menjadi derajat keanggotaan tiap himpunan."""
    hasil = {}
    for kode, x in (("P", p), ("S", s), ("B", b)):
        lab_turun, lab_naik, _, _ = VARIABEL[kode]
        hasil[kode] = {
            lab_turun: derajat(kode, lab_turun, x),
            lab_naik: derajat(kode, lab_naik, x),
        }
    return hasil


# ---------------------------------------------------------------
# 4. Basis aturan (8 aturan)
# ---------------------------------------------------------------
# (id, P, S, B, F)
ATURAN = [
    ("R1", "SEDIKIT", "SEDIKIT", "TERBATAS", "BERKURANG"),
    ("R2", "SEDIKIT", "SEDIKIT", "MEMADAI",  "BERKURANG"),
    ("R3", "SEDIKIT", "BANYAK",  "TERBATAS", "BERKURANG"),
    ("R4", "SEDIKIT", "BANYAK",  "MEMADAI",  "BERKURANG"),
    ("R5", "BANYAK",  "SEDIKIT", "TERBATAS", "BERKURANG"),
    ("R6", "BANYAK",  "SEDIKIT", "MEMADAI",  "BERTAMBAH"),
    ("R7", "BANYAK",  "BANYAK",  "TERBATAS", "BERKURANG"),
    ("R8", "BANYAK",  "BANYAK",  "MEMADAI",  "BERKURANG"),
]


def teks_aturan(p, s, b, f):
    return f"IF Penerima {p} AND Sisa {s} AND Bahan {b} THEN Faktor {f}"


# ---------------------------------------------------------------
# 5. Inferensi Tsukamoto
# ---------------------------------------------------------------
def f_dari_alpha(alpha, label):
    """Fungsi keanggotaan output monoton -> F dihitung langsung dari alpha."""
    rentang = F_MAX - F_MIN
    if label == "BERKURANG":              # garis turun
        return F_MAX - alpha * rentang
    return F_MIN + alpha * rentang        # BERTAMBAH: garis naik


def hitung(p, s, b):
    """Jalankan seluruh proses FIS Tsukamoto dan kembalikan detail hitungan."""
    mu = fuzzifikasi(p, s, b)
    detail = []
    for id_, lp, ls, lb, lf in ATURAN:
        premis = (mu["P"][lp], mu["S"][ls], mu["B"][lb])
        alpha = min(premis)                       # operator Zadeh (AND = MIN)
        f = f_dari_alpha(alpha, lf)
        detail.append({
            "id": id_, "P": lp, "S": ls, "B": lb, "F": lf,
            "premis": premis, "alpha": alpha, "f": f, "alpha_f": alpha * f,
        })

    sum_alpha = sum(d["alpha"] for d in detail)
    sum_alpha_f = sum(d["alpha_f"] for d in detail)
    f_akhir = sum_alpha_f / sum_alpha if sum_alpha > 0 else None  # rata-rata terbobot
    porsi = f_akhir * p if f_akhir is not None else None

    return {
        "input": {"P": p, "S": s, "B": b},
        "mu": mu,
        "aturan": detail,
        "sum_alpha": sum_alpha,
        "sum_alpha_f": sum_alpha_f,
        "f_akhir": f_akhir,
        "porsi": porsi,
    }


# ---------------------------------------------------------------
# 6. Data kurva keanggotaan (untuk grafik)
# ---------------------------------------------------------------
def kurva(kode, titik=101):
    """Kembalikan (daftar_x, {label: [derajat,...]}) untuk satu variabel."""
    lab_turun, lab_naik, a, b = VARIABEL[kode]
    xs = [a + (b - a) * i / (titik - 1) for i in range(titik)]
    return xs, {
        lab_turun: [turun(x, a, b) for x in xs],
        lab_naik: [naik(x, a, b) for x in xs],
    }


# ---------------------------------------------------------------
# Contoh hitungan manual (cocok dengan dokumen: P=2400, S=60, B=85)
# ---------------------------------------------------------------
if __name__ == "__main__":
    h = hitung(2400, 60, 85)
    print("Input      :", h["input"])
    print("Fuzzifikasi:")
    for k, v in h["mu"].items():
        print(" ", k, {lab: round(d, 4) for lab, d in v.items()})
    print("\nAturan  alpha   F        alpha*F")
    for d in h["aturan"]:
        print(f"{d['id']:<7} {d['alpha']:.2f}   {d['f']:.4f}   {d['alpha_f']:.4f}   -> {d['F']}")
    print(f"\nSum alpha    = {h['sum_alpha']:.2f}")
    print(f"Sum alpha*F  = {h['sum_alpha_f']:.5f}")
    print(f"F akhir      = {h['f_akhir']:.4f}")
    print(f"Porsi        = F x P = {h['f_akhir']:.4f} x 2400 = {h['porsi']:.1f} porsi")
