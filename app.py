import streamlit as st
import requests
import pandas as pd
from io import StringIO
import json
import geopandas as gpd
import matplotlib.pyplot as plt

STATISTIKAAMETI_API_URL = "https://andmed.stat.ee/api/v1/et/stat/RV032"

geojson = "maakonnad.geojson"

JSON_PAYLOAD_STR = """{
  "query": [
    {"code": "Aasta", "selection": {"filter": "item", "values": ["2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]}},
    {"code": "Maakond", "selection": {"filter": "item", "values": ["37", "39", "44", "49", "51", "57", "59", "65", "67", "70", "74", "78", "82", "84", "86"]}},
    {"code": "Sugu", "selection": {"filter": "item", "values": ["2", "3"]}}
  ],
  "response": {"format": "csv"}
}"""

def import_data():
    headers = {'Content-Type': 'application/json'}
    parsed_payload = json.loads(JSON_PAYLOAD_STR)
    response = requests.post(STATISTIKAAMETI_API_URL, json=parsed_payload, headers=headers)
    if response.status_code == 200:
        text = response.content.decode('utf-8-sig')
        df = pd.read_csv(StringIO(text))
        return df
    else:
        st.error(f"Failed to fetch data: {response.status_code}")
        st.stop()

def import_geojson():
    gdf = gpd.read_file(geojson)
    gdf["MNIMI"] = gdf["MNIMI"].str.replace(" maakond", "", regex=False)
    return gdf

def get_data_for_year(df, year):
    year_data = df[df.Aasta == year]
    return year_data

def plot(merged_data, year, selected_region=None, cmap_choice='plasma'):
    fig, ax = plt.subplots(figsize=(12, 8))
    vmin = merged_data['Loomulik iive'].min()
    vmax = merged_data['Loomulik iive'].max()
    if selected_region and selected_region != "Kõik maakonnad":
        merged_data = merged_data[merged_data["MNIMI"] == selected_region]

    if merged_data.empty:
        st.warning("Valitud piirkonnal puuduvad andmed.")
        return

    merged_data.plot(
        column='Loomulik iive', 
        ax=ax, 
        legend=True, 
        cmap=cmap_choice,
        vmin=vmin,
        vmax=vmax,
        legend_kwds={'label': "Loomulik iive"}
    )

    title = f'Loomulik iive {"maakonnas " + selected_region if selected_region and selected_region != "Kõik maakonnad" else "maakonniti"} aastal {year}'
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()

    try:
        ax.set_aspect('equal')
    except Exception:
        pass

    st.pyplot(fig)

st.title("Loomulik iive Eesti maakondades (2014-2023)")

with st.spinner("Laen andmeid..."):
    df = import_data()
    gdf = import_geojson()

st.success("Andmed edukalt laetud!")

year = st.selectbox("Vali aasta", sorted(df["Aasta"].unique()))
df_year = get_data_for_year(df, year)

# PARANDUS: puhasta Maakonna nimed API andmetes
df_year["Maakond"] = df_year["Maakond"].str.replace(" maakond", "", regex=False)

merged_data = gdf.merge(df_year, left_on='MNIMI', right_on='Maakond')

if "Mehed Loomulik iive" in merged_data.columns and "Naised Loomulik iive" in merged_data.columns:
    merged_data["Loomulik iive"] = merged_data["Mehed Loomulik iive"] + merged_data["Naised Loomulik iive"]

    st.subheader("Andmetabel ja kaart")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(
            merged_data[["MNIMI", "Loomulik iive"]]
            .rename(columns={"MNIMI": "Maakond"})
            .sort_values("Maakond")
            .reset_index(drop=True)
            .rename(lambda x: x + 1)
            .style.set_table_styles([{'selector': 'th', 'props': [('text-align', 'left')]}])
        )
    with col2:
        region_options = ["Kõik maakonnad"] + sorted(merged_data["MNIMI"].unique())
        selected_region = st.selectbox("Vali maakond", region_options, key="region_select")

        cmap_choice = st.selectbox("Vali kaardi värviskeem", ["viridis", "plasma"], index=1, key="cmap_select")

        plot(merged_data, year, selected_region, cmap_choice=cmap_choice)

    region_options = ["Kõik maakonnad"] + sorted(merged_data["MNIMI"].unique())
    selected_region = st.selectbox("Vali maakond", region_options)

    cmap_choice = st.selectbox("Vali kaardi värviskeem", ["viridis", "plasma"], index=1)
    plot(merged_data, year, selected_region, cmap_choice=cmap_choice)
else:
    st.error("Puuduvad vajalikud veerud 'Mehed Loomulik iive' ja 'Naised Loomulik iive'.")

st.caption("Andmeallikas: Statistikaamet")
