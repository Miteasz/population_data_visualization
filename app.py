# Importowanie potrzebnych bibliotek
import pandas as pd
import streamlit as st
import altair as alt

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
    death_rate['Year'] = death_rate['Atrybut']
    population_female['Year'] = population_female['Atrybut']
    population_male['Year'] = population_male['Atrybut']
    birth_rate['Year'] = birth_rate['Atrybut']

    # Łączenie danych o populacji mężczyzn i kobiet oraz dodanie 'Total'
    population_total = population_female.copy()
    population_total['Wartość'] = population_female['Wartość'] + population_male['Wartość']
    population_total['Gender'] = 'Total'
    population_female['Gender'] = 'Female'
    population_male['Gender'] = 'Male'

    # Połączenie wszystkich danych populacyjnych
    population_with_continent = pd.concat([population_female, population_male, population_total]).reset_index(drop=True)
    population_with_continent = population_with_continent.merge(countries_and_continents, 
                                                                left_on='Country Name', 
                                                                right_on='Country', 
                                                                how='inner')
    return population_with_continent

prepared_data = prepare_data()

# Wizualizacje
st.title("Wizualizacja danych demograficznych")

# Wykres liniowy populacji dla każdego kontynentu - interaktywny
st.subheader("Populacja dla każdego kontynentu w poszczególnych latach")

# Wybór płci
selected_gender = st.selectbox("Wybierz płeć", options=['Total', 'Female', 'Male'], index=0)

# Filtrowanie danych po płci
gender_filtered_data = prepared_data[prepared_data['Gender'] == selected_gender]

# Filtruj tylko dane dla wybranego kontynentu
continent_year_data = gender_filtered_data.groupby(['Continent', 'Year'])['Wartość'].sum().reset_index()

# Interaktywna wizualizacja za pomocą Altair
selected_continents = st.multiselect("Wybierz kontynenty, aby zobaczyć szczegóły", 
                                     options=list(continent_year_data['Continent'].unique()), 
                                     default=list(continent_year_data['Continent'].unique()))

# Suwak do dynamicznej filtracji lat
min_year = int(continent_year_data['Year'].min())
max_year = int(continent_year_data['Year'].max())
selected_year_range = st.slider("Wybierz zakres lat", min_value=min_year, max_value=max_year, value=(2000, max_year))

# Filtrowanie danych po kontynencie i zakresie lat
filtered_data = continent_year_data[(continent_year_data['Continent'].isin(selected_continents)) & 
                                    (continent_year_data['Year'] >= selected_year_range[0]) & 
                                    (continent_year_data['Year'] <= selected_year_range[1])]

# Tworzenie wykresu liniowego
line_chart = alt.Chart(filtered_data).mark_line(point=True).encode(
    x=alt.X('Year:O', title='Rok'),
    y=alt.Y('Wartość:Q', title='Populacja'),
    color=alt.Color('Continent:N', title='Kontynent'),
    tooltip=['Continent', 'Year', 'Wartość']
).properties(
    width=800,
    height=500,
    title=f'Populacja wybranych kontynentów w poszczególnych latach - {selected_gender}'
).interactive()

if not filtered_data.empty:
    st.altair_chart(line_chart)

# Wykres słupkowy dla top 15 krajów
st.subheader(f"Top 15 krajów dla wybranych kontynentów: {', '.join(selected_continents)}")
top_countries_data = gender_filtered_data[(gender_filtered_data['Continent'].isin(selected_continents)) & 
                                          (gender_filtered_data['Year'] >= selected_year_range[0]) & 
                                          (gender_filtered_data['Year'] <= selected_year_range[1])]

# Obliczenie średniej populacji dla każdego kraju
top_countries_data = top_countries_data.groupby('Country Name')['Wartość'].mean().reset_index()
top_countries_data = top_countries_data.sort_values(by='Wartość', ascending=False).head(15)

# Wykres słupkowy
bar_chart = alt.Chart(top_countries_data).mark_bar().encode(
    x=alt.X('Wartość:Q', title='Populacja', axis=alt.Axis(format=',.0f')),
    y=alt.Y('Country Name:N', sort='-x', title='Kraj'),
    tooltip=['Country Name', 'Wartość']
).properties(
    width=800,
    height=500,
    title=f'Top 15 krajów w wybranych kontynentach: {", ".join(selected_continents)} (populacja) - {selected_gender}'
)

if not top_countries_data.empty:
    st.altair_chart(bar_chart)
