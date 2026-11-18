"""
app.py - Antarmuka (UI) Streamlit untuk FIS Tsukamoto: Porsi MBG (versi 2)
Output model = faktor produksi F (1,00 - 1,15); porsi dimasak = F x P.
Jalankan:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

import tsukamoto_mbg as fm

st.set_page_config(page_title="SPK Fuzzy Tsukamoto - Porsi MBG",
                   page_icon="🍱", layout="wide")


# ---------- helper format angka Indonesia ----------
def dec(x, nd=2):
    return f"{x:.{nd}f}".replace(".", ",")


def ribu(x):
    return f"{x:,.0f}".replace(",", ".")


# ---------- preset & state ----------
PRESET = {
    "Contoh hitungan manual (P=2.400, S=60, B=85)": (2400, 60, 85),
    "Ideal: banyak penerima, sisa sedikit, bahan cukup": (2900, 10, 100),
    "Ekstrem: sedikit penerima, banyak sisa, bahan terbatas": (1100, 250, 45),
    "Kustom (atur slider sendiri)": None,
}

for kunci, nilai in (("P", 2400), ("S", 60), ("B", 85)):
    st.session_state.setdefault(kunci, nilai)


def terapkan_preset():
    v = PRESET[st.session_state["preset"]]
    if v:
        st.session_state["P"], st.session_state["S"], st.session_state["B"] = v


# ---------- sidebar: input ----------
with st.sidebar:
    st.header("Input")
    st.selectbox("Skenario", list(PRESET.keys()), key="preset",
                 on_change=terapkan_preset)
    P = st.slider("Penerima manfaat hari ini (P)", fm.P_MIN, fm.P_MAX,
                  step=10, key="P", help="Jumlah orang yang dilayani SPPG")
    S = st.slider("Sisa porsi kemarin (S)", fm.S_MIN, fm.S_MAX,
                  step=5, key="S", help="Porsi yang tidak termakan kemarin")
    B = st.slider("Ketersediaan bahan baku (B, %)", fm.B_MIN, fm.B_MAX,
                  step=1, key="B", help="Persentase bahan terhadap kebutuhan")
    st.divider()
    st.caption("Simulasi akademik untuk tugas Sistem Pendukung Keputusan. "
               "Bukan penilaian terhadap programnya; keputusan akhir tetap "
               "di tangan pengambil keputusan.")

# ---------- hitung ----------
hasil = fm.hitung(P, S, B)
F = hasil["f_akhir"]
aturan = hasil["aturan"]
aktif = sum(1 for d in aturan if d["alpha"] > 0)

# ---------- header ----------
st.title("🍱 SPK Fuzzy Tsukamoto: Penentuan Porsi MBG")
st.write("Menentukan jumlah porsi yang dimasak dapur (SPPG) per hari dari "
         "**3 input** dan **8 aturan** fuzzy. Output fuzzy berupa "
         "**faktor produksi F** (1,00 sampai 1,15), lalu "
         "**porsi = F × jumlah penerima**.")

if F is None:
    st.error("Tidak ada aturan yang aktif (Σα = 0). Periksa input.")
    st.stop()

porsi = hasil["porsi"]
cadangan = porsi - P
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rekomendasi porsi dimasak", f"{ribu(porsi)} porsi")
m2.metric("Cadangan dari jumlah penerima", f"+{ribu(cadangan)} porsi",
          f"{dec((F - 1) * 100, 1)}%", delta_color="off")
m3.metric("Faktor produksi (F)", dec(F, 4))
m4.metric("Aturan aktif (α > 0)", f"{aktif} dari {len(aturan)}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Fuzzifikasi", "2. Aturan & Inferensi", "3. Defuzzifikasi",
    "4. Fungsi Keanggotaan", "5. Langkah Manual"])

nilai = {"P": P, "S": S, "B": B}

# ---------- tab 1: fuzzifikasi ----------
with tab1:
    st.subheader("Fuzzifikasi: angka input menjadi derajat keanggotaan")
    nama = {"P": "Penerima (P)", "S": "Sisa kemarin (S)", "B": "Bahan baku (B)"}
    satuan = {"P": "orang", "S": "porsi", "B": "%"}
    kolom = st.columns(3)
    for kol, kode in zip(kolom, ("P", "S", "B")):
        with kol:
            st.markdown(f"**{nama[kode]} = {ribu(nilai[kode])} {satuan[kode]}**")
            for label, mu in hasil["mu"][kode].items():
                st.progress(float(mu), text=f"{label}: {dec(mu)}")

# ---------- tab 2: aturan & inferensi ----------
with tab2:
    st.subheader("Inferensi: α-predikat = MIN dari ketiga premis")
    baris = []
    for d in aturan:
        baris.append({
            "Aturan": d["id"],
            "IF ... THEN": fm.teks_aturan(d["P"], d["S"], d["B"], d["F"]),
            "μ(P)": round(d["premis"][0], 4),
            "μ(S)": round(d["premis"][1], 4),
            "μ(B)": round(d["premis"][2], 4),
            "α = MIN": round(d["alpha"], 4),
            "F": round(d["f"], 4),
            "α × F": round(d["alpha_f"], 4),
            "Status": "aktif" if d["alpha"] > 0 else "tidak aktif",
        })
    df = pd.DataFrame(baris)
    st.dataframe(df, hide_index=True)
    st.markdown("**Kekuatan tiap aturan (α)**")
    st.bar_chart(df.set_index("Aturan")["α = MIN"])
    st.caption("Rumus F: BERKURANG → F = 1,15 − α × 0,15; "
               "BERTAMBAH → F = 1,00 + α × 0,15.")

# ---------- tab 3: defuzzifikasi ----------
with tab3:
    st.subheader("Defuzzifikasi: rata-rata terbobot")
    st.latex(r"F = \frac{\sum (\alpha_i \times F_i)}{\sum \alpha_i}")
    st.latex(rf"F = \frac{{{dec(hasil['sum_alpha_f'], 4)}}}"
             rf"{{{dec(hasil['sum_alpha'])}}} = {dec(F, 4)}")
    st.latex(rf"\text{{Porsi}} = F \times P = {dec(F, 4)} \times {P} "
             rf"= {dec(porsi, 1)}")
    st.success(f"Rekomendasi: memasak sekitar **{ribu(porsi)} porsi** untuk "
               f"**{ribu(P)} penerima** (cadangan {dec((F - 1) * 100, 1)}%).")

# ---------- tab 4: fungsi keanggotaan ----------
with tab4:
    st.subheader("Grafik fungsi keanggotaan")
    judul = {
        "P": "Penerima manfaat (orang)", "S": "Sisa porsi kemarin",
        "B": "Ketersediaan bahan baku (%)",
        "F": "Faktor produksi F (output)",
    }
    kiri, kanan = st.columns(2)
    for i, kode in enumerate(("P", "S", "B", "F")):
        xs, ys = fm.kurva(kode)
        grafik = pd.DataFrame(ys, index=xs)
        with (kiri if i % 2 == 0 else kanan):
            st.markdown(f"**{judul[kode]}**")
            st.line_chart(grafik)
            if kode != "F":
                st.caption(f"Nilai saat ini: {ribu(nilai[kode])}")
            else:
                st.caption("F = 1,00 berarti tanpa cadangan; "
                           "F = 1,15 berarti cadangan 15%.")

# ---------- tab 5: langkah manual ----------
with tab5:
    st.subheader("Langkah hitungan manual (untuk slide presentasi)")
    mu = hasil["mu"]
    st.markdown("**Langkah 1 - Fuzzifikasi**")
    st.markdown(
        f"- P SEDIKIT = (3000 − {P}) / 2000 = {dec(mu['P']['SEDIKIT'])}; "
        f"P BANYAK = ({P} − 1000) / 2000 = {dec(mu['P']['BANYAK'])}\n"
        f"- S SEDIKIT = (300 − {S}) / 300 = {dec(mu['S']['SEDIKIT'])}; "
        f"S BANYAK = {S} / 300 = {dec(mu['S']['BANYAK'])}\n"
        f"- B TERBATAS = (100 − {B}) / 60 = {dec(mu['B']['TERBATAS'])}; "
        f"B MEMADAI = ({B} − 40) / 60 = {dec(mu['B']['MEMADAI'])}")
    st.markdown("**Langkah 2 - Inferensi (α = MIN) dan F tiap aturan**")
    for d in aturan:
        p1, p2, p3 = (dec(v) for v in d["premis"])
        rumus = (f"1,15 − {dec(d['alpha'])} × 0,15" if d["F"] == "BERKURANG"
                 else f"1,00 + {dec(d['alpha'])} × 0,15")
        st.markdown(f"- {d['id']}: α = min({p1}; {p2}; {p3}) = "
                    f"{dec(d['alpha'])}; F = {rumus} = {dec(d['f'], 4)}")
    st.markdown("**Langkah 3 - Defuzzifikasi**")
    suku = " + ".join(dec(d["alpha_f"], 4) for d in aturan)
    st.markdown(f"- Σα = {dec(hasil['sum_alpha'])}\n"
                f"- Σ(α × F) = {suku} = {dec(hasil['sum_alpha_f'], 4)}\n"
                f"- F = {dec(hasil['sum_alpha_f'], 4)} / "
                f"{dec(hasil['sum_alpha'])} = **{dec(F, 4)}**")
    st.markdown("**Langkah 4 - Porsi yang dimasak**")
    st.markdown(f"- Porsi = F × P = {dec(F, 4)} × {P} = "
                f"**{dec(porsi, 1)} ≈ {ribu(porsi)} porsi**")
