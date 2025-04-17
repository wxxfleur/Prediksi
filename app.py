import streamlit as st
import pandas as pd
import joblib
import datetime
import plotly.express as px
import plotly.graph_objects as go
import json

# Load model dan label encoder
model = joblib.load('model_rf_harga.pkl')
le_dict = joblib.load('label_encoder_dict.pkl')

# Load daftar nilai unik dari label encoder
provinsi_list = le_dict["Provinsi"].classes_
kota_list = le_dict["Kabupaten Kota"].classes_
pasar_list = le_dict["Nama Pasar"].classes_
variant_list = le_dict["Nama Variant"].classes_

# Judul aplikasi
st.title("📈 Prediksi Harga Komoditas & Arah Perubahan")
st.write("Prediksi harga bahan pokok harian dan arah perubahannya untuk hari berikutnya.")

# Load data
df = pd.read_excel("Data Harga Komoditas.xlsx")
with open("prov 37.geojson", "r") as f:
    geojson = json.load(f)

# Dropdown bahan pokok
bahan_list = df["Nama Variant"].unique()
selected_bahan = st.selectbox("Pilih Bahan Pokok", bahan_list)

# Dropdown agregasi
agregasi_opsi = {
    "Harga Terendah": "min",
    "Harga Tertinggi": "max"
}
selected_agregasi_label = st.selectbox("Pilih Metode Agregasi Harga", list(agregasi_opsi.keys()))
agregasi_func = agregasi_opsi[selected_agregasi_label]

# Kolom tanggal terakhir = kolom paling kanan
tanggal_terakhir = df.columns[-1]

# Filter berdasarkan bahan pokok
filtered_df = df[df["Nama Variant"] == selected_bahan]

# Ambil kolom harga dari kolom tanggal terakhir dan beri nama 'harga'
filtered_df = filtered_df[["Provinsi", "Nama Variant", tanggal_terakhir]].copy()
filtered_df.rename(columns={tanggal_terakhir: "harga"}, inplace=True)
filtered_df["Provinsi"] = filtered_df["Provinsi"].str.upper().str.strip()

# Agregasi per provinsi
agg_df = filtered_df.groupby("Provinsi").agg({"harga": agregasi_func}).reset_index()

# Plotly Choropleth (Peta)
fig_map = px.choropleth(
    agg_df,
    geojson=geojson,
    featureidkey="properties.prov_name",
    locations="Provinsi",
    color="harga",
    color_continuous_scale="YlOrRd",
    hover_name="Provinsi",
    hover_data={"harga": True}
)

fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(
    title=f"Peta Harga {selected_bahan} ({selected_agregasi_label}) per Provinsi - {tanggal_terakhir}",
    margin={"r":0,"t":30,"l":0,"b":0}
)

st.plotly_chart(fig_map, use_container_width=True)

# Grafik Perbandingan Harga (Bar Chart)
bar_fig = px.bar(
    agg_df,
    x="Provinsi",
    y="harga",
    title=f"Perbandingan Harga {selected_bahan} per Provinsi ({selected_agregasi_label}) - {tanggal_terakhir}",
    labels={"harga": "Harga", "Provinsi": "Provinsi"},
    color="harga",
    color_continuous_scale="YlOrRd"
)
st.plotly_chart(bar_fig, use_container_width=True)

# Pastikan kolom tanggal adalah string dan mengandung '/'
date_columns = [col for col in df.columns if isinstance(col, str) and '/' in col]

# Filter data berdasarkan bahan pokok yang dipilih
filtered_df = df[df["Nama Variant"] == selected_bahan]

# Menghitung rata-rata harga per tanggal untuk bahan pokok yang dipilih
df_avg = filtered_df[["Nama Variant"] + date_columns]
df_avg = df_avg.drop(columns=["Nama Variant"])  # Hapus kolom Nama Variant setelah filter
df_avg = df_avg.mean()  # Hitung rata-rata harga untuk setiap tanggal

# Ubah hasil rata-rata menjadi DataFrame dengan index sebagai tanggal
df_avg = pd.DataFrame(df_avg).reset_index()
df_avg.columns = ["Tanggal", "Harga Rata-rata Nasional"]

# Ubah kolom tanggal menjadi datetime
df_avg["Tanggal"] = pd.to_datetime(df_avg["Tanggal"], format="%d/%m/%y")

# Plot perkembangan harga rata-rata nasional untuk bahan pokok yang dipilih
fig_line = px.line(
    df_avg,
    x="Tanggal",
    y="Harga Rata-rata Nasional",
    title=f"Perkembangan Harga Nasional {selected_bahan} (Rata-rata Harga per Tanggal)",
    labels={"Harga Rata-rata Nasional": "Harga", "Tanggal": "Tanggal"},
    line_shape="linear"
)
st.plotly_chart(fig_line, use_container_width=True)


# Inputan pengguna
provinsi = st.selectbox("Pilih Provinsi", provinsi_list)
kab_kota = st.selectbox("Pilih Kabupaten/Kota", kota_list)
nama_pasar = st.selectbox("Pilih Nama Pasar", pasar_list)
nama_variant = st.selectbox("Pilih Komoditas", variant_list)
tanggal = st.date_input("Tanggal", value=datetime.date.today())

# Prediksi
if st.button("Prediksi"):
    # Fitur waktu
    day = tanggal.day
    month = tanggal.month
    dayofweek = tanggal.weekday()

    # Encode input
    input_dict = {
        "Provinsi": le_dict["Provinsi"].transform([provinsi])[0],
        "Kabupaten Kota": le_dict["Kabupaten Kota"].transform([kab_kota])[0],
        "Nama Pasar": le_dict["Nama Pasar"].transform([nama_pasar])[0],
        "Nama Variant": le_dict["Nama Variant"].transform([nama_variant])[0],
        "day": day,
        "month": month,
        "dayofweek": dayofweek
    }

    input_df = pd.DataFrame([input_dict])
    pred_hari_ini = model.predict(input_df)[0]

    # Prediksi untuk besok
    tanggal_besok = tanggal + datetime.timedelta(days=1)
    besok_dict = input_dict.copy()
    besok_dict["day"] = tanggal_besok.day
    besok_dict["month"] = tanggal_besok.month
    besok_dict["dayofweek"] = tanggal_besok.weekday()
    input_df_besok = pd.DataFrame([besok_dict])
    pred_besok = model.predict(input_df_besok)[0]

    # Tampilkan hasil prediksi
    st.markdown(f"📅 **Harga Hari Ini ({tanggal}):** Rp {pred_hari_ini:,.2f}")
    st.markdown(f"📅 **Harga Besok ({tanggal_besok}):** Rp {pred_besok:,.2f}")

    # Tampilkan arah perubahan
    if pred_besok > pred_hari_ini:
        st.markdown("### 🔺 Harga Diprediksi **Naik**", unsafe_allow_html=True)
        st.markdown("<h2 style='color:red'>⬆️</h2>", unsafe_allow_html=True)
    elif pred_besok < pred_hari_ini:
        st.markdown("### 🔻 Harga Diprediksi **Turun**", unsafe_allow_html=True)
        st.markdown("<h2 style='color:green'>⬇️</h2>", unsafe_allow_html=True)
    else:
        st.markdown("### ➡️ Harga Diprediksi **Stabil**", unsafe_allow_html=True)

 # Bar chart untuk perbandingan harga hari ini dan besok
    bar_chart_data = {
        "Hari": ["Hari Ini", "Besok"],
        "Harga": [pred_hari_ini, pred_besok]
    }
    bar_df = pd.DataFrame(bar_chart_data)

    fig_bar = go.Figure([go.Bar(x=bar_df["Hari"], y=bar_df["Harga"], marker_color=["blue", "red"])])
    fig_bar.update_layout(
        title="Perbandingan Harga Hari Ini dan Besok",
        xaxis_title="Hari",
        yaxis_title="Harga",
        yaxis_tickprefix="Rp ",
        plot_bgcolor="white"
    )

    st.plotly_chart(fig_bar, use_container_width=True)