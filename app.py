# Importowanie potrzebnych bibliotek
import folium
import requests
import pandas as pd
import streamlit as st
import altair as alt
import geopandas as gpd

# Wczytanie danych
countries_and_continents_path = 'countries_and_continents.csv'
death_rate_path = 'death rate.xlsx'
population_female_path = 'populacja_female.xlsx'
population_male_path = 'populacja_male.xlsx'
birth_rate_path = 'Birth rate.xlsx'

# Wczytanie danych do Pandas DataFrames
countries_and_continents = pd.read_csv(countries_and_continents_path)
death_rate = pd.read_excel(death_rate_path, sheet_name='death_rate')
population_female = pd.read_excel(population_female_path, sheet_name=0)
population_male = pd.read_excel(population_male_path, sheet_name=0)
birth_rate = pd.read_excel(birth_rate_path, sheet_name='Birth_rate')

# Usuwanie agregacji, pozostawienie tylko nazw krajów
valid_countries = countries_and_continents['Country'].unique()
population_female = population_female[population_female['Country Name'].isin(valid_countries)]
population_male = population_male[population_male['Country Name'].isin(valid_countries)]

# Przygotowanie danych
def prepare_data():
    # Sprawdzenie i zmiana nazw kolumn w birth_rate i death_rate
    if 'Country Name' in birth_rate.columns:
        birth_rate.rename(columns={'Country Name': 'Country'}, inplace=True)
    if 'Country Name' in death_rate.columns:
        death_rate.rename(columns={'Country Name': 'Country'}, inplace=True)

    death_rate['Year'] = death_rate['Atrybut']  # Zakładamy, że 'Atrybut' zawiera rok
    birth_rate['Year'] = birth_rate['Atrybut']

    population_female['Year'] = population_female['Atrybut']
    population_male['Year'] = population_male['Atrybut']

    # Dodanie kolumny Gender
    population_female['Gender'] = 'Female'
    population_male['Gender'] = 'Male'

    # Połączenie danych o populacji mężczyzn i kobiet
    population_data = pd.concat([population_female, population_male]).reset_index(drop=True)

    # Łączenie danych z kontynentami
    population_data = population_data.merge(countries_and_continents, 
                                            left_on='Country Name', 
                                            right_on='Country', 
                                            how='inner')

    # Dodanie danych o narodzinach i zgonach
    birth_rate.rename(columns={'Wartość': 'Birth Rate'}, inplace=True)
    death_rate.rename(columns={'Wartość': 'Death Rate'}, inplace=True)

    # Scalanie narodzin i zgonów z danymi populacyjnymi
    combined_data = population_data.merge(birth_rate[['Country', 'Year', 'Birth Rate']], 
                                          on=['Country', 'Year'], how='left')
    combined_data = combined_data.merge(death_rate[['Country', 'Year', 'Death Rate']], 
                                        on=['Country', 'Year'], how='left')

    # Dodanie kolumny Continent_Gender
    combined_data['Continent_Gender'] = combined_data['Continent'] + '-' + combined_data['Gender']

    return combined_data

prepared_data = prepare_data()

# Wizualizacje
st.title("Wizualizacja danych demograficznych")

# Wybór płci
selected_gender = st.selectbox("Wybierz płeć", options=['Wszystkie', 'Female', 'Male'], index=0)

# Suwak do dynamicznej filtracji lat
st.subheader("Filtrowanie zakresu lat dla wszystkich wizualizacji")
min_year = int(prepared_data['Year'].min())
max_year = int(prepared_data['Year'].max())
selected_year_range = st.slider(
    "Wybierz zakres lat", 
    min_value=min_year, 
    max_value=max_year, 
    value=(2000, max_year), 
    key="global_year_slider"  # Unikalny klucz dla suwaka
)

# Filtrowanie danych po zakresie lat i płci
filtered_data = prepared_data[
    (prepared_data['Year'] >= selected_year_range[0]) & 
    (prepared_data['Year'] <= selected_year_range[1])
]
if selected_gender != 'Wszystkie':
    filtered_data = filtered_data[filtered_data['Gender'] == selected_gender]

# Grupowanie danych
continent_year_data = filtered_data.groupby(['Continent', 'Year', 'Gender', 'Continent_Gender'])['Wartość'].sum().reset_index()

# Interaktywna wizualizacja za pomocą Altair
selected_continents = st.multiselect(
    "Wybierz kontynenty, aby zobaczyć szczegóły", 
    options=list(continent_year_data['Continent'].unique()), 
    default=['Europe']  # Ustawienie domyślnego wyboru na Europę
)

# Filtrowanie danych po kontynencie
continent_year_data = continent_year_data[continent_year_data['Continent'].isin(selected_continents)]

# Tworzenie wykresu liniowego
line_chart = alt.Chart(continent_year_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Rok'),
    y=alt.Y('Wartość:Q', title='Populacja', axis=alt.Axis(format=',.0f')),
    color=alt.Color('Continent_Gender:N', title='Kontynent i Płeć'),
    tooltip=[
        'Continent', 
        'Gender', 
        'Year', 
        alt.Tooltip('Wartość:Q', title='Populacja', format=',.0f')
    ]
).properties(
    width=800,
    height=500,
    title=f'Populacja wybranych kontynentów w poszczególnych latach - {selected_gender}'
).interactive()

if not continent_year_data.empty:
    st.altair_chart(line_chart)

# Przygotowanie map geoprzestrzennych
def prepare_geospatial_data(data):
    geojson_path = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json'
    geojson_data = requests.get(geojson_path).json()
    geo_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    geo_gdf.set_crs(epsg=4326, inplace=True)

    # Grupowanie danych dla wskaźników na poziomie krajowym
    map_data = data.groupby('Country')[['Death Rate', 'Birth Rate']].mean().reset_index()

    # Dopasowanie nazw krajów
    country_name_mapping = {
        "United States": "United States of America",
        "Serbia": "Republic of Serbia",
        "Tanzania": "United Republic of Tanzania",
        "Czechia": "Czech Republic",
        "Democratic Republic of the Congo": "Democratic Republic of the Congo"
    }
    map_data['Country'] = map_data['Country'].replace(country_name_mapping)

    # Łączenie danych GeoJSON z danymi wskaźników
    geo_gdf = geo_gdf.merge(map_data, left_on='name', right_on='Country', how='left')
    geo_gdf['Death Rate'] = geo_gdf['Death Rate'].fillna(0)
    geo_gdf['Birth Rate'] = geo_gdf['Birth Rate'].fillna(0)

    return geo_gdf

geo_data = prepare_geospatial_data(filtered_data)

# Mapa dla Death Rate
st.subheader("Mapa geoprzestrzenna: Śmiertelność na poziomie krajowym")
death_rate_map = folium.Map(location=[20, 0], zoom_start=2)
folium.Choropleth(
    geo_data=geo_data.to_json(),
    data=geo_data,
    columns=['name', 'Death Rate'],
    key_on='feature.properties.name',
    fill_color='YlGnBu',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Death Rate'
).add_to(death_rate_map)
folium.GeoJson(
    geo_data,
    tooltip=folium.GeoJsonTooltip(
        fields=['name', 'Death Rate'],
        aliases=['Country', 'Death Rate'],
        localize=True
    )
).add_to(death_rate_map)
st.components.v1.html(death_rate_map._repr_html_(), width=800, height=600)

# Mapa dla Birth Rate
st.subheader("Mapa geoprzestrzenna: Liczba urodzeń na poziomie krajowym")
birth_rate_map = folium.Map(location=[20, 0], zoom_start=2)
folium.Choropleth(
    geo_data=geo_data.to_json(),
    data=geo_data,
    columns=['name', 'Birth Rate'],
    key_on='feature.properties.name',
    fill_color='YlGn',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Birth Rate'
).add_to(birth_rate_map)
folium.GeoJson(
    geo_data,
    tooltip=folium.GeoJsonTooltip(
        fields=['name', 'Birth Rate'],
        aliases=['Country', 'Birth Rate'],
        localize=True
    )
).add_to(birth_rate_map)
st.components.v1.html(birth_rate_map._repr_html_(), width=800, height=600)

# Przygotowanie danych dla mapy porównawczej
def prepare_comparison_map_data(data, year_range):
    # Filtrowanie danych na podstawie zakresu lat
    filtered_data = data[(data['Year'] >= year_range[0]) & (data['Year'] <= year_range[1])]

    geojson_path = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json'
    geojson_data = requests.get(geojson_path).json()
    geo_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    geo_gdf.set_crs(epsg=4326, inplace=True)

    # Grupowanie danych dla wskaźników na poziomie krajowym
    map_data = filtered_data.groupby('Country')[['Death Rate', 'Birth Rate']].mean().reset_index()

    # Dopasowanie nazw krajów
    country_name_mapping = {
        "United States": "United States of America",
        "Serbia": "Republic of Serbia",
        "Tanzania": "United Republic of Tanzania",
        "Czechia": "Czech Republic",
        "Democratic Republic of the Congo": "Democratic Republic of the Congo"
    }
    map_data['Country'] = map_data['Country'].replace(country_name_mapping)

    # Łączenie danych GeoJSON z danymi wskaźników
    geo_gdf = geo_gdf.merge(map_data, left_on='name', right_on='Country', how='left')

    # Tworzenie kolumny dla porównania: Birth Rate > Death Rate
    geo_gdf['Comparison'] = geo_gdf['Birth Rate'] > geo_gdf['Death Rate']

    return geo_gdf

comparison_geo_data = prepare_comparison_map_data(prepared_data, selected_year_range)

# Funkcja do tworzenia mapy porównawczej
def create_comparison_map(geo_data):
    m = folium.Map(location=[20, 0], zoom_start=2)

    # Definiowanie funkcji stylu dla mapy
    def style_function(feature):
        comparison = feature['properties'].get('Comparison', None)
        if comparison is None or pd.isna(comparison):  # Sprawdzenie na brak danych
            return {'fillColor': 'white', 'color': 'black', 'fillOpacity': 0.6, 'weight': 0.5}
        elif comparison:
            return {'fillColor': 'green', 'color': 'green', 'fillOpacity': 0.6, 'weight': 0.5}
        else:
            return {'fillColor': 'red', 'color': 'red', 'fillOpacity': 0.6, 'weight': 0.5}

    # Dodanie warstwy GeoJson
    folium.GeoJson(
        geo_data,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['name', 'Birth Rate', 'Death Rate'],
            aliases=['Country', 'Birth Rate', 'Death Rate'],
            localize=True
        )
    ).add_to(m)

    return m


# Tworzenie mapy porównawczej
st.subheader("Mapa geoprzestrzenna: Kraje z większą liczbą urodzeń niż zgonów")
comparison_map = create_comparison_map(comparison_geo_data)

# Wyświetlenie mapy w Streamlit
st.components.v1.html(comparison_map._repr_html_(), width=800, height=600)
