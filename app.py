# Importowanie potrzebnych bibliotek
import folium
import requests
import pandas as pd
import streamlit as st
import altair as alt
import seaborn as sns
import geopandas as gpd
import matplotlib.pyplot as plt

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
# prepared_data.to_csv("prepared_data.csv")

# Wizualizacje
st.title("Wizualizacja danych demograficznych")

# Wybór płci
selected_gender = st.selectbox("Wybierz płeć", options=['Wszystkie', 'Female', 'Male'], index=0)

# Filtrowanie danych
if selected_gender == 'Wszystkie':
    gender_filtered_data = prepared_data
else:
    gender_filtered_data = prepared_data[prepared_data['Gender'] == selected_gender]

# Grupowanie danych
continent_year_data = gender_filtered_data.groupby(['Continent', 'Year', 'Gender', 'Continent_Gender'])['Wartość'].sum().reset_index()

# Interaktywna wizualizacja za pomocą Altair
selected_continents = st.multiselect(
    "Wybierz kontynenty, aby zobaczyć szczegóły", 
    options=list(continent_year_data['Continent'].unique()), 
    default=['Europe']  # Ustawienie domyślnego wyboru na Europę
)

# Suwak do dynamicznej filtracji lat
min_year = int(continent_year_data['Year'].min())
max_year = int(continent_year_data['Year'].max())
selected_year_range = st.slider("Wybierz zakres lat", min_value=min_year, max_value=max_year, value=(2000, max_year))

# Filtrowanie danych po kontynencie i zakresie lat
filtered_data = continent_year_data[(continent_year_data['Continent'].isin(selected_continents)) & 
                                    (continent_year_data['Year'] >= selected_year_range[0]) & 
                                    (continent_year_data['Year'] <= selected_year_range[1])]

# Tworzenie wykresu liniowego z kolorami dla kontynentu i płci
line_chart = alt.Chart(filtered_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Rok'),
    y=alt.Y('Wartość:Q', title='Populacja', axis=alt.Axis(format=',.0f')),
    color=alt.Color('Continent_Gender:N', title='Kontynent i Płeć'),
    tooltip=[
        'Continent', 
        'Gender', 
        'Year', 
        alt.Tooltip('Wartość:Q', title='Populacja', format=',.0f')  # Formatowanie liczb w tooltipie
    ]
).properties(
    width=800,
    height=500,
    title=f'Populacja wybranych kontynentów w poszczególnych latach - {selected_gender}'
).interactive()

if not filtered_data.empty:
    st.altair_chart(line_chart)

# Wykres słupkowy dla top 15 krajów
st.subheader(f"Top 15 krajów dla wybranych kontynentów: {', '.join(selected_continents)}")

# Filtrowanie danych dla wybranego okresu i kontynentów
top_countries_data = prepared_data[(prepared_data['Continent'].isin(selected_continents)) & 
                                   (prepared_data['Year'] >= selected_year_range[0]) & 
                                   (prepared_data['Year'] <= selected_year_range[1])]

# Filtrowanie według wybranej płci
if selected_gender != 'Wszystkie':
    top_countries_data = top_countries_data[top_countries_data['Gender'] == selected_gender]

# Obliczenie średniej populacji dla każdego kraju w wybranym okresie
top_countries_data = top_countries_data.groupby(['Country Name', 'Year'])['Wartość'].sum().reset_index()
top_countries_data = top_countries_data.groupby('Country Name')['Wartość'].mean().reset_index()
top_countries_data = top_countries_data.sort_values(by='Wartość', ascending=False).head(15)

# Formatowanie liczb dla wykresu słupkowego
bar_chart = alt.Chart(top_countries_data).mark_bar().encode(
    x=alt.X('Wartość:Q', title='Średnia populacja', axis=alt.Axis(format=',.0f')),
    y=alt.Y('Country Name:N', sort='-x', title='Kraj'),
    tooltip=[
        'Country Name', 
        alt.Tooltip('Wartość:Q', title='Populacja', format=',.0f')  # Formatowanie liczb w tooltipie
    ]
).properties(
    width=800,
    height=500,
    title=f'Top 15 krajów w wybranych kontynentach: {", ".join(selected_continents)} (średnia populacja) - {selected_gender}'
)

if not top_countries_data.empty:
    st.altair_chart(bar_chart)

#############

# Przygotowanie danych geoprzestrzennych
def prepare_geospatial_data(data):
    # Wczytanie pliku GeoJSON z internetu
    geojson_path = 'https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json'
    geojson_data = requests.get(geojson_path).json()

    # Przekształcenie GeoJSON na GeoDataFrame
    geo_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # Ustawienie CRS (układu współrzędnych)
    geo_gdf.set_crs(epsg=4326, inplace=True)

    # Grupowanie danych dla wskaźnika na poziomie krajowym
    map_data = data.groupby('Country')['Death Rate'].mean().reset_index()

    # Dopasowanie nazw krajów (dodaj więcej mapowań w razie potrzeby)
    country_name_mapping = {
        "United States": "United States of America",
        "Serbia": "Republic of Serbia",
        "Tanzania": "United Republic of Tanzania",
        "Democratic Republic of the Congo": "Republic of the Congo"
    }
    map_data['Country'] = map_data['Country'].replace(country_name_mapping)

    # Łączenie danych GeoJSON z danymi wskaźników
    geo_gdf = geo_gdf.merge(map_data, left_on='name', right_on='Country', how='left')

    # Wypełnianie brakujących wartości wskaźnika (opcjonalnie)
    geo_gdf['Death Rate'] = geo_gdf['Death Rate'].fillna(0)  # Wartość domyślna dla brakujących danych

    return geo_gdf

# Przygotowanie danych do mapy
geo_data = prepare_geospatial_data(prepared_data)
# geo_data.to_csv("geo_data.csv")
# Tworzenie mapy z folium
def create_map(geo_data):
    # Tworzenie mapy
    m = folium.Map(location=[20, 0], zoom_start=2)

    # Dodanie warstwy Choropleth
    folium.Choropleth(
        geo_data=geo_data.to_json(),
        data=geo_data,
        columns=['name', 'Death Rate'],
        key_on='feature.properties.name',
        fill_color='YlGnBu',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Death Rate'
    ).add_to(m)

    # Dodanie tooltipów z informacjami o krajach
    folium.GeoJson(
        geo_data,
        tooltip=folium.GeoJsonTooltip(
            fields=['name', 'Death Rate'],
            aliases=['Country', 'Death Rate'],
            localize=True
        )
    ).add_to(m)

    return m

# Tworzenie mapy
st.subheader("Mapa geoprzestrzenna: Śmiertelność na poziomie krajowym")
map_object = create_map(geo_data)

# Wyświetlenie mapy w Streamlit
st.components.v1.html(map_object._repr_html_(), width=800, height=600)

